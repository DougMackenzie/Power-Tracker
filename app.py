import streamlit as st
import pandas as pd
import altair as alt
import gspread
from google.oauth2.service_account import Credentials

# Page Configuration
st.set_page_config(
    page_title="US Power Supply vs. Demand",
    layout="wide"
)

st.title("US Power Supply vs. Demand Gap")

# Function to connect to Google Sheets
@st.cache_resource
def get_data():
    # Define the scope
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    # Authenticate using secrets
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=scope
        )
        client = gspread.authorize(credentials)

        # Let's try to find a spreadsheet named 'LiveProjection' first.
        
        # However, to be safe and standard, I will assume the user puts the Spreadsheet Name or Key in secrets 
        # or I will try to open a spreadsheet named "US Power Data" (generic) and look for 'LiveProjection' tab?
        # No, "pull data from a sheet named 'LiveProjection'" likely means the TAB name.
        # I will assume the spreadsheet name is also 'LiveProjection' or provided in secrets.
        # Let's check secrets for 'spreadsheet_name'. If not, default to 'LiveProjection'.
        
        spreadsheet_name = st.secrets.get("spreadsheet_name", "LiveProjection")
        st.write(f"Attempting to open spreadsheet: '{spreadsheet_name}'...")
        sh = client.open(spreadsheet_name)
        
        # Select the worksheet
        worksheet = sh.worksheet("LiveProjection")
        
        # Get all values
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        return df
        
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

# Load data
df = get_data()

# Create Tabs
tab1, tab2 = st.tabs(["Live Tracker", "Research Framework"])

with tab1:
    if df is not None:
        # Ensure numeric columns
        cols_to_numeric = ['Year', 'Live Total Demand', 'Live Domestic Demand', 'Live Supply']
        for col in cols_to_numeric:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Filter out rows where Year is NaN
        df_live = df.dropna(subset=['Year'])

        # Reshape for Altair (Long format)
        value_vars = ['Live Total Demand', 'Live Domestic Demand', 'Live Supply']
        
        # Check if columns exist
        missing_cols = [c for c in value_vars if c not in df_live.columns]
        if missing_cols:
            st.error(f"Missing columns in data: {missing_cols}")
        else:
            df_melted = df_live.melt('Year', value_vars=value_vars, var_name='Category', value_name='Capacity (GW)')

            # Define colors
            domain = ['Live Total Demand', 'Live Domestic Demand', 'Live Supply']
            range_ = ['orange', 'green', 'blue']

            # Create Chart
            chart = alt.Chart(df_melted).mark_line().encode(
                x=alt.X('Year:O', title='Year'),
                y=alt.Y('Capacity (GW):Q', title='Capacity (GW)'),
                color=alt.Color('Category:N', scale=alt.Scale(domain=domain, range=range_), legend=alt.Legend(title="Metric")),
                tooltip=['Year', 'Category', 'Capacity (GW)']
            ).properties(
                title='Power Supply vs Demand Projection',
                height=500
            ).interactive()

            st.altair_chart(chart, use_container_width=True)

            with st.expander("View Raw Data"):
                st.dataframe(df_live)
    else:
        st.warning("Please configure your `.streamlit/secrets.toml` with `gcp_service_account` and `spreadsheet_name`.")

with tab2:
    st.header("Research Framework Modeling")
    st.markdown("Adjust assumptions based on the **Power Research Framework**.")

    from research_data import BASE_CASE_DATA, SCENARIOS, COMPANY_SPLIT_2030
    
    # Sidebar for Research Controls
    st.sidebar.header("Research Assumptions")
    
    # Scenario Selector
    scenario = st.sidebar.selectbox("Select Scenario", ["Base", "Conservative", "Aggressive"], index=0)
    params = SCENARIOS[scenario]
    
    # Sliders (initialized with scenario defaults)
    # We use session state to allow updates from selectbox but also manual override
    if 'last_scenario' not in st.session_state or st.session_state.last_scenario != scenario:
        st.session_state.chip_mult = params['Chips_M_Multiplier']
        st.session_state.tdp_mult = params['TDP_Multiplier']
        st.session_state.pue_target = params['PUE_Target']
        st.session_state.last_scenario = scenario

    chip_mult = st.sidebar.slider("Chip Volume Multiplier", 0.5, 2.0, st.session_state.chip_mult, 0.1)
    tdp_mult = st.sidebar.slider("TDP Multiplier", 0.8, 1.5, st.session_state.tdp_mult, 0.05)
    pue_target = st.sidebar.slider("2030 PUE Target", 1.0, 1.5, st.session_state.pue_target, 0.01)

    # Calculate Projections
    research_rows = []
    for row in BASE_CASE_DATA:
        year = row['Year']
        
        # Interpolate PUE (Linear decay to target by 2030, then flat or continued trend)
        # Simple approach: Scale the base PUE by the ratio of (Target / Base_2030)
        # But only for years >= 2024.
        base_pue_2030 = 1.16 # From App D
        pue_scale = pue_target / base_pue_2030
        
        # Apply multipliers
        chips = row['Chips_M'] * chip_mult
        tdp = row['TDP'] * tdp_mult
        util = row['Util'] # Keep util as base for now, or add slider
        pue = row['PUE'] * pue_scale
        
        # Formula: Global GW = [Chips(M) * TDP(W) * Util * 1.45 * PUE] / 1e9
        global_gw = (chips * 1e6 * tdp * util * 1.45 * pue) / 1e9
        us_gw = global_gw * row['US_Share']
        
        research_rows.append({
            "Year": year,
            "Projected US Demand (Research)": us_gw,
            "Global Demand": global_gw
        })
        
    df_research = pd.DataFrame(research_rows)
    
    # Merge with Live Supply for comparison
    if df is not None:
        df_supply = df[['Year', 'Live Supply']].copy()
        # Ensure numeric
        df_supply['Live Supply'] = pd.to_numeric(df_supply['Live Supply'], errors='coerce')
        df_combined = pd.merge(df_research, df_supply, on='Year', how='left')
    else:
        df_combined = df_research

    # Plot Research Chart
    df_res_melted = df_combined.melt('Year', value_vars=['Projected US Demand (Research)', 'Live Supply'], 
                                     var_name='Metric', value_name='Capacity (GW)')
    
    chart_res = alt.Chart(df_res_melted).mark_line().encode(
        x=alt.X('Year:O'),
        y=alt.Y('Capacity (GW):Q'),
        color=alt.Color('Metric:N', scale=alt.Scale(domain=['Projected US Demand (Research)', 'Live Supply'], range=['red', 'blue'])),
        tooltip=['Year', 'Metric', 'Capacity (GW)']
    ).properties(title="Research Projection vs Live Supply", height=400).interactive()
    
    st.altair_chart(chart_res, use_container_width=True)
    
    # Company Breakdown (2030 Snapshot)
    st.subheader("2030 US Stack Breakdown (Estimated)")
    
    # Get 2030 total from our calculation
    row_2030 = df_research[df_research['Year'] == 2030]
    if not row_2030.empty:
        total_2030 = row_2030.iloc[0]['Projected US Demand (Research)']
        
        breakdown_data = []
        for company, share in COMPANY_SPLIT_2030.items():
            breakdown_data.append({
                "Company": company,
                "Capacity (GW)": total_2030 * share
            })
        
        df_breakdown = pd.DataFrame(breakdown_data)
        
        chart_breakdown = alt.Chart(df_breakdown).mark_bar().encode(
            x=alt.X('Capacity (GW):Q'),
            y=alt.Y('Company:N', sort='-x'),
            color=alt.Color('Company:N', legend=None),
            tooltip=['Company', 'Capacity (GW)']
        ).properties(height=300)
        
        st.altair_chart(chart_breakdown, use_container_width=True)
