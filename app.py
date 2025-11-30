import streamlit as st
import pandas as pd
import altair as alt
import gspread
from google.oauth2.service_account import Credentials
import json
from forecast_tracker import ForecastTracker, DemandScenario, SupplyScenario

# Page Config
st.set_page_config(page_title="Antigravity Power Tracker", layout="wide")

# Secrets
if "gcp_service_account" in st.secrets:
    creds_dict = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
else:
    st.error("Secrets not found.")
    st.stop()

@st.cache_resource
def get_data():
    client = gspread.authorize(credentials)
    try:
        sh = client.open("LiveProjection")
    except:
        sh = client.open("Power Tracker")
    return sh

sh = get_data()

# Tabs
tab1, tab2 = st.tabs(["Live Tracker", "Forecast Framework"])

with tab1:
    st.title("Live Power Supply vs Demand Tracker")
    try:
        ws = sh.worksheet("Sheet1")
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        # Chart
        chart = alt.Chart(df).mark_line(point=True).encode(
            x='Year:O',
            y='Capacity (GW):Q',
            color='Type:N',
            tooltip=['Year', 'Type', 'Capacity (GW)']
        ).properties(title="US Power Supply vs Demand Gap")
        
        st.altair_chart(chart, use_container_width=True)
        
        # Data Table
        st.dataframe(df)
        
    except Exception as e:
        st.error(f"Error loading live data: {e}")

with tab2:
    
    # Scenario Selectors
    col1, col2 = st.sidebar.columns(2)
    with col1:
        demand_scenario = st.selectbox("Demand Scenario", ["Low", "Mid", "High"], index=1)
    with col2:
        supply_scenario = st.selectbox("Supply Scenario", ["Low", "Mid", "High"], index=0) # Default to Low (Conservative)
        
    params = SCENARIOS[demand_scenario]
    
    # Sliders (initialized with scenario defaults)
    if 'last_demand_scenario' not in st.session_state or st.session_state.last_demand_scenario != demand_scenario:
        st.session_state.chip_mult = params['Chips_M_Multiplier']
        st.session_state.tdp_mult = params['TDP_Multiplier']
        st.session_state.pue_target = params['PUE_Target']
        st.session_state.last_demand_scenario = demand_scenario

    chip_mult = st.sidebar.slider("Chip Volume Multiplier", 0.5, 2.0, st.session_state.chip_mult, 0.1)
    tdp_mult = st.sidebar.slider("TDP Multiplier", 0.8, 1.5, st.session_state.tdp_mult, 0.05)
    pue_target = st.sidebar.slider("2030 PUE Target", 1.0, 1.5, st.session_state.pue_target, 0.01)

    # Calculate Projections
    research_rows = []
    for row in BASE_CASE_DATA:
        year = row['Year']
        
        # 1. Calculate Base Case Raw (to derive calibration factor)
        base_raw_global = (row['Chips_M'] * 1e6 * row['TDP'] * row['Util'] * row['PUE']) / 1e9
        base_raw_us = base_raw_global * row['US_Share']
        
        # Calibration Factor
        calibration_factor = row['US_GW_Base'] / base_raw_us if base_raw_us > 0 else 1.0
        
        # 2. Calculate User Scenario
        base_pue_2030 = 1.16
        pue_scale = pue_target / base_pue_2030
        
        # Apply multipliers
        chips = row['Chips_M'] * chip_mult
        tdp = row['TDP'] * tdp_mult
        util = row['Util']
        pue = row['PUE'] * pue_scale
        
        # Calculate User Raw
        user_raw_global = (chips * 1e6 * tdp * util * pue) / 1e9
        user_raw_us = user_raw_global * row['US_Share']
        
        # Apply Calibration
        final_us_gw = user_raw_us * calibration_factor
        
        # Calculate Domestic Demand (70% of Stack, per Page 27)
        domestic_gw = final_us_gw * 0.70
        
        research_rows.append({
            "Year": year,
            "Total Stack Demand": final_us_gw,
            "Domestic Demand (70%)": domestic_gw
        })
        
    df_research = pd.DataFrame(research_rows)
    
    # Merge with Selected Supply Scenario
    df_supply_res = pd.DataFrame(SUPPLY_SCENARIOS[supply_scenario])
    df_combined = pd.merge(df_research, df_supply_res, on='Year', how='left')
    
    # Plot Research Chart
    df_res_melted = df_combined.melt('Year', value_vars=['Total Stack Demand', 'Domestic Demand (70%)', 'Supply_GW'], 
                                     var_name='Metric', value_name='Capacity ({GW})')
    
    # Rename Supply_GW for legend
    df_res_melted['Metric'] = df_res_melted['Metric'].replace('Supply_GW', f'US Supply ({supply_scenario})')
    
    # Colors: Orange (Stack), Green (Domestic), Blue (Supply)
    domain = ['Total Stack Demand', 'Domestic Demand (70%)', f'US Supply ({supply_scenario})']
    range_ = ['orange', 'green', 'blue']
    
    chart_res = alt.Chart(df_res_melted).mark_line(interpolate='monotone').encode(
        x=alt.X('Year:O'),
        y=alt.Y('Capacity ({GW}):Q'),
        color=alt.Color('Metric:N', scale=alt.Scale(domain=domain, range=range_)),
        tooltip=['Year', 'Metric', 'Capacity ({GW})']
    ).properties(title=f"Supply vs Demand ({demand_scenario} Demand / {supply_scenario} Supply)", height=400).interactive()
    
    st.altair_chart(chart_res, use_container_width=True)
    
    # Company Breakdown (2030 Snapshot)
    st.subheader("2030 US Stack Breakdown (Estimated)")
    
    # Get 2030 total from our calculation
    row_2030 = df_research[df_research['Year'] == 2030]
    if not row_2030.empty:
        total_2030 = row_2030.iloc[0]['Total Stack Demand']
        
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
