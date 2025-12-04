import streamlit as st
# Force reload
import pandas as pd
import altair as alt
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import sys

# Add current directory to path so we can import modules
sys.path.append(os.path.dirname(__file__))

from forecast_tracker import ForecastTracker, DemandScenario, SupplyScenario
import portfolio_manager.streamlit_app as pm

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

# Navigation
st.sidebar.title("Antigravity")
app_mode = st.sidebar.radio("Select Module", ["Live Tracker", "Forecast Framework", "Portfolio Manager", "Site Profile Builder"])
st.sidebar.markdown("---")

if app_mode == "Live Tracker":
    st.title("Live Power Supply vs Demand Tracker")
    try:
        ws = sh.worksheet("LiveProjection")
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        # Check for Wide Format (Year, Demand, Supply columns)
        wide_cols = {'Year', 'Live Total Demand', 'Live Domestic Demand', 'Live Supply'}
        if wide_cols.issubset(df.columns):
            # Melt to Long Format
            df = df.melt('Year', value_vars=['Live Total Demand', 'Live Domestic Demand', 'Live Supply'], 
                         var_name='Type', value_name='Capacity (GW)')
        
        if df.empty:
            st.warning("The 'LiveProjection' sheet is empty. Please add data to visualize it.")
        elif not {'Year', 'Capacity (GW)', 'Type'}.issubset(df.columns):
            st.warning(f"The 'LiveProjection' sheet is missing required columns. Found: {df.columns.tolist()}. Expected: ['Year', 'Capacity (GW)', 'Type'] OR ['Year', 'Live Total Demand', 'Live Domestic Demand', 'Live Supply']")
        else:
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

elif app_mode == "Forecast Framework":
    st.title("AI Data Center Forecast Framework (v2.0)")
    st.markdown("Physics-based model driven by CoWoS constraints and Supply Chain bottlenecks.")
    
    # Initialize Tracker
    tracker = ForecastTracker()
    
    # Load Signals from Sheet
    try:
        ws_research = sh.worksheet("WeeklyResearch")
        signals_data = ws_research.get_all_records()
        
        st.info(f"Loaded {len(signals_data)} signals from Weekly Research.")
        
        # Replay Signals
        for s in signals_data:
            try:
                data = json.loads(s['Data_JSON'])
                if s['Type'] == 'cowos_capacity':
                    tracker.process_cowos_signal(data['year'], data['capacity'], s['Source'])
                elif s['Type'] == 'hyperscaler_capex':
                    tracker.process_capex_signal(data['quarterly_capex_bn'], s['Source'])
                elif s['Type'] == 'queue_update':
                    tracker.process_queue_signal(data['iso'], data['active_gw'], None, s['Source'])
            except Exception as e:
                pass # Skip malformed signals
                
    except Exception as e:
        st.warning("No research signals found yet. Using baseline.")

    # Sidebar Controls
    st.sidebar.header("Scenario Overrides")
    
    # Display Current State
    state = tracker.get_state_summary()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Demand Scenario (Acceleration)", f"{state['demand_probabilities']['scenario_a']*100:.0f}%")
    with col2:
        st.metric("Supply Scenario", state['supply_scenario'].upper())
    with col3:
        gap_2027 = state['forecast_2027']['gap_gw']
        st.metric("2027 Gap Forecast", f"{gap_2027:+.1f} GW", delta_color="normal" if gap_2027 >=0 else "inverse")

    # Generate Forecast Data for Chart
    forecast_data = []
    for year in range(2024, 2031):
        f = tracker.get_gap_forecast(year)
        forecast_data.append({"Year": year, "GW": f['demand_gw'], "Type": "Demand (Live)"})
        forecast_data.append({"Year": year, "GW": f['supply_gw'], "Type": "Supply (Live)"})
        
    df_forecast = pd.DataFrame(forecast_data)
    
    # Chart
    chart_forecast = alt.Chart(df_forecast).mark_line(point=True).encode(
        x='Year:O',
        y='GW:Q',
        color=alt.Color('Type:N', scale=alt.Scale(domain=['Demand (Live)', 'Supply (Live)'], range=['#FF4B4B', '#0068C9'])),
        tooltip=['Year', 'Type', 'GW']
    ).properties(title="Live Trajectory: Supply vs Demand")
    
    st.altair_chart(chart_forecast, use_container_width=True)
    
    # Signal Log
    st.subheader("Signal Log (Factors driving this forecast)")
    log_data = []
    for s in tracker.export_signal_log():
        log_data.append({
            "Date": s['timestamp'][:10],
            "Type": s['type'],
            "Signal": s['data'],
            "Analysis": s['analysis'].get('recommendation', '') if s['analysis'] else ''
        })
    if log_data:
        st.dataframe(pd.DataFrame(log_data))
    else:
        st.write("No signals logged yet.")

elif app_mode == "Portfolio Manager":
    pm.run()

elif app_mode == "Site Profile Builder":
    from portfolio_manager.site_profile_page import show_site_profile_builder
    
    st.title("📋 Site Profile Builder")
    
    try:
        # Load sites from portfolio manager
        # Priority 1: Portfolio Manager's Google Sheets database (session state)
        if hasattr(st, 'session_state') and hasattr(st.session_state, 'db') and 'sites' in st.session_state.db:
            sites = st.session_state.db['sites']
            st.success(f"✅ Loaded {len(sites)} sites from Portfolio Manager database")
        else:
            # Try to initialize database connection directly
            try:
                from portfolio_manager.streamlit_app import load_database
                with st.spinner("Connecting to Google Sheets database..."):
                    db = load_database()
                    if db and 'sites' in db:
                        st.session_state.db = db
                        sites = db['sites']
                        st.success(f"✅ Connected to Google Sheets: Loaded {len(sites)} sites")
                    else:
                        sites = {}
            except Exception as e:
                st.warning(f"Could not connect to Google Sheets: {e}")
                # Fallback to session state or JSON
                if 'sites' in st.session_state:
                    sites = st.session_state.sites
                    st.success(f"✅ Loaded {len(sites)} sites from session (Offline)")
                else:
                    sites = {}
            # Priority 3: Try to load from site_database.json as fallback
            import json
            import os
            db_path = os.path.join(os.path.dirname(__file__), 'portfolio_manager', 'site_database.json')
            if os.path.exists(db_path):
                with open(db_path, 'r') as f:
                    db_data = json.load(f)
                
                # Extract sites from nested structure
                if 'sites' in db_data:
                    sites = db_data['sites']
                else:
                    sites = db_data
                    
                st.info(f"📁 Loaded {len(sites)} sites from JSON file (visit Portfolio Manager to load all sites from Google Sheets)")
            else:
                sites = {}
                st.warning("⚠️ No sites found. Please visit Portfolio Manager first to load your sites from Google Sheets.")
        
        if sites:
            show_site_profile_builder(sites)
        else:
            st.warning("No sites available.")
            st.info("👉 Visit **Portfolio Manager** first to load your sites, then return here to build profiles.")
            if st.button("Go to Portfolio Manager"):
                st.session_state.app_mode = "Portfolio Manager"
                st.rerun()
    
    except Exception as e:
        st.error(f"Error loading Site Profile Builder: {e}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())
