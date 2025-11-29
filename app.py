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
# @st.cache_resource
def get_data():
    # Define the scope
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    # Authenticate using secrets
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("Secret 'gcp_service_account' not found in secrets. Available keys: " + str(list(st.secrets.keys())))
            return None

        credentials_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=scope
        )
        client = gspread.authorize(credentials)

        # Open the spreadsheet (assuming the first one or by name if provided in secrets, 
        # but user asked to connect to a sheet named 'LiveProjection'. 
        # Usually this means a tab within a spreadsheet, or the spreadsheet name itself.
        # I'll assume 'LiveProjection' is the worksheet name, and we need a spreadsheet name or ID.
        # Since the prompt says "pull data from a sheet named 'LiveProjection'", I'll assume it's a worksheet.
        # I will try to open a spreadsheet defined in secrets or just a default one if not specified.
        # Wait, the prompt implies "Connect to a Google Sheet... pull data from a sheet named 'LiveProjection'".
        # I'll assume the spreadsheet URL or name is also in secrets or I'll just use a placeholder 
        # that the user can update. 
        # Actually, often 'sheet' refers to the spreadsheet. Let's assume the spreadsheet is named 'LiveProjection' 
        # OR there is a specific spreadsheet and we need the tab 'LiveProjection'.
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

if df is not None:
    # Ensure numeric columns
    cols_to_numeric = ['Year', 'Live Total Demand', 'Live Domestic Demand', 'Live Supply']
    for col in cols_to_numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Filter out rows where Year is NaN
    df = df.dropna(subset=['Year'])

    # Reshape for Altair (Long format)
    # We want 3 lines: 'Live Total Demand', 'Live Domestic Demand', 'Live Supply'
    # We can melt the dataframe
    value_vars = ['Live Total Demand', 'Live Domestic Demand', 'Live Supply']
    
    # Check if columns exist
    missing_cols = [c for c in value_vars if c not in df.columns]
    if missing_cols:
        st.error(f"Missing columns in data: {missing_cols}")
    else:
        df_melted = df.melt('Year', value_vars=value_vars, var_name='Category', value_name='Capacity (GW)')

        # Define colors
        # Orange for Total Demand, Green for Domestic, Blue for Supply
        domain = ['Live Total Demand', 'Live Domestic Demand', 'Live Supply']
        range_ = ['orange', 'green', 'blue']

        # Create Chart
        chart = alt.Chart(df_melted).mark_line().encode(
            x=alt.X('Year:O', title='Year'), # Ordinal or Quantitative? Year is usually temporal or ordinal. Let's use Ordinal for discrete years or Quantitative if continuous.
            y=alt.Y('Capacity (GW):Q', title='Capacity (GW)'),
            color=alt.Color('Category:N', scale=alt.Scale(domain=domain, range=range_), legend=alt.Legend(title="Metric")),
            tooltip=['Year', 'Category', 'Capacity (GW)']
        ).properties(
            title='Power Supply vs Demand Projection',
            height=500
        ).interactive()

        st.altair_chart(chart, use_container_width=True)

        # Show raw data (optional, good for debugging)
        with st.expander("View Raw Data"):
            st.dataframe(df)

else:
    st.warning("Please configure your `.streamlit/secrets.toml` with `gcp_service_account` and `spreadsheet_name`.")
