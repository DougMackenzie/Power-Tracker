"""
Research Module
===============
Dynamic research framework merging the Live Tracker and Forecast Framework.
Allows toggling scenarios, viewing bottoms-up builds, and analyzing supply/demand gaps.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Any
from enum import Enum

# =============================================================================
# DATA STRUCTURES & CONSTANTS
# =============================================================================

class DemandScenario(Enum):
    ACCELERATION = "Scenario A: Acceleration"
    PLATEAU = "Scenario B: Plateau"

class SupplyScenario(Enum):
    LOW = "Low Supply (Status Quo)"
    MEDIUM = "Medium Supply (Reform Success)"
    HIGH = "High Supply (Aggressive)"

# Demand Trajectories (GW)
# Based on ai_dc_forecast_tracking_v2.md and forecast_tracker.py
DEMAND_DATA = {
    DemandScenario.ACCELERATION: {
        'description': "**Most Likely**: AI business case continues to scale. Reasoning inference drives exponential compute. Model sizes continue 10x/2yr scaling.",
        'global_demand': {2024: 30, 2025: 55, 2026: 85, 2027: 120, 2028: 160, 2029: 210, 2030: 270, 2035: 500},
        'us_tech_demand': {2024: 12, 2025: 25, 2026: 38, 2027: 50, 2028: 70, 2029: 90, 2030: 115, 2035: 230}, # From forecast_tracker.py
        'us_located_demand': {2024: 10, 2025: 20, 2026: 30, 2027: 40, 2028: 55, 2029: 70, 2030: 90, 2035: 180}, # Assumed ~80% of US Tech initially, dropping slightly
    },
    DemandScenario.PLATEAU: {
        'description': "**Bear Case**: AI business case fails to materialize. Efficiency gains outpace demand. ROI skepticism reduces investment.",
        'global_demand': {2024: 30, 2025: 45, 2026: 60, 2027: 75, 2028: 90, 2029: 105, 2030: 120, 2035: 150},
        'us_tech_demand': {2024: 12, 2025: 20, 2026: 28, 2027: 35, 2028: 50, 2029: 65, 2030: 85, 2035: 95},
        'us_located_demand': {2024: 10, 2025: 16, 2026: 22, 2027: 28, 2028: 40, 2029: 50, 2030: 65, 2035: 75},
    }
}

# Supply Trajectories (GW) - US Deliverable
SUPPLY_DATA = {
    SupplyScenario.LOW: {
        'description': "**Most Likely**: Utility delivery slippage, minimal GETs/SMR. Queue backlogs persist.",
        'trajectory': {2024: 10, 2025: 15, 2026: 20, 2027: 25, 2028: 32, 2029: 40, 2030: 50, 2035: 140}
    },
    SupplyScenario.MEDIUM: {
        'description': "Moderate reform impact, some GETs adoption. Queue completion rates improve slightly.",
        'trajectory': {2024: 10, 2025: 18, 2026: 26, 2027: 35, 2028: 48, 2029: 62, 2030: 75, 2035: 257}
    },
    SupplyScenario.HIGH: {
        'description': "Aggressive reforms + GETs + SMR deployment. Major policy shifts unlock capacity.",
        'trajectory': {2024: 10, 2025: 20, 2026: 32, 2027: 45, 2028: 62, 2029: 80, 2030: 100, 2035: 418}
    }
}

# Bottoms-Up Demand Build Data (CoWoS -> GW)
COWOS_BASELINE = {
    2024: 35000,
    2025: 60000,
    2026: 80000,
    2027: 100000
}

CONVERSION_FACTORS = {
    'dies_per_wafer': 65, # Avg of 60-73
    'yield': 0.75, # Blended
    'utilization': 0.70, # Blended
    'tdp_kw': 1.0, # B200 baseline
    'pue': 1.3
}

# ISO Queue Data (Supply Analysis)
ISO_DATA = [
    {'iso': 'PJM', 'queue_gw': 90, 'completion_rate': 0.19, 'notes': 'High volume, slow processing'},
    {'iso': 'ERCOT', 'queue_gw': 100, 'completion_rate': 0.25, 'notes': 'Faster, but transmission constrained'},
    {'iso': 'SPP', 'queue_gw': 25, 'completion_rate': 0.35, 'notes': 'Good resource, limited load'},
    {'iso': 'MISO', 'queue_gw': 45, 'completion_rate': 0.22, 'notes': 'Mixed bag, reforms pending'},
    {'iso': 'WECC', 'queue_gw': 60, 'completion_rate': 0.15, 'notes': 'Very slow, environmental constraints'},
    {'iso': 'SERC', 'queue_gw': 35, 'completion_rate': 0.28, 'notes': 'Vertical utilities, bilateral markets'}
]

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_bottoms_up_demand(year, cowos_wpm):
    """Calculate GW demand from CoWoS capacity."""
    annual_wafers = cowos_wpm * 12
    total_dies = annual_wafers * CONVERSION_FACTORS['dies_per_wafer']
    good_dies = total_dies * CONVERSION_FACTORS['yield']
    
    # Power calculation
    # Chips * TDP * PUE / 1e6 (for GW)
    # Note: This is a simplified "new capacity" add, not cumulative installed base
    # For cumulative, we'd need to integrate over time. 
    # For this view, we'll estimate the *active* fleet power.
    
    # Let's assume this year's production adds to the fleet.
    # Simplified model: 
    # Total AI Power = (Cumulative Chips * TDP * PUE)
    
    # But for the "Build" tab, let's show the flow for a single year's production
    annual_chip_power_gw = (good_dies * CONVERSION_FACTORS['tdp_kw']) / 1e6
    annual_dc_power_gw = annual_chip_power_gw * CONVERSION_FACTORS['pue']
    
    return {
        'wafers': annual_wafers,
        'dies': total_dies,
        'good_dies': good_dies,
        'chip_power_gw': annual_chip_power_gw,
        'dc_power_gw': annual_dc_power_gw
    }

# =============================================================================
# UI COMPONENTS
# =============================================================================

def show_research_module():
    st.title("🔬 Power Research Framework")
    st.markdown("Dynamic analysis of AI power demand vs. utility supply constraints.")

    # --- Sidebar Controls ---
    st.sidebar.header("Scenario Configuration")
    
    selected_demand_scenario = st.sidebar.selectbox(
        "Demand Scenario",
        options=list(DemandScenario),
        format_func=lambda x: x.value
    )
    
    selected_supply_scenario = st.sidebar.selectbox(
        "Supply Scenario",
        options=list(SupplyScenario),
        format_func=lambda x: x.value
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### View Settings")
    show_global = st.sidebar.checkbox("Show Global Demand", value=True)
    show_us_tech = st.sidebar.checkbox("Show US Tech Demand", value=True)
    show_us_located = st.sidebar.checkbox("Show US Located Demand", value=True)
    
    # --- Main Content ---
    
    # Scenario Description
    st.info(f"**Current Outlook**: {DEMAND_DATA[selected_demand_scenario]['description']}")
    if selected_supply_scenario == SupplyScenario.LOW:
        st.warning(f"**Supply Constraint**: {SUPPLY_DATA[selected_supply_scenario]['description']}")
    else:
        st.success(f"**Supply Outlook**: {SUPPLY_DATA[selected_supply_scenario]['description']}")

    # Tabs
    tab_summary, tab_supply, tab_demand_build = st.tabs(["📊 Gap Analysis", "⚡ Supply Analysis", "🏗️ Bottoms-Up Demand"])
    
    with tab_summary:
        show_gap_analysis(selected_demand_scenario, selected_supply_scenario, show_global, show_us_tech, show_us_located)
        
    with tab_supply:
        show_supply_analysis(selected_supply_scenario)
        
    with tab_demand_build:
        show_bottoms_up_build()

def show_gap_analysis(demand_scen, supply_scen, show_global, show_us_tech, show_us_located):
    st.subheader("Supply vs. Demand Gap Analysis")
    
    # Prepare Data
    years = list(range(2024, 2036))
    
    # Get Demand Curves
    d_data = DEMAND_DATA[demand_scen]
    
    # Get Supply Curve
    s_data = SUPPLY_DATA[supply_scen]['trajectory']
    
    # Create DataFrame for Plotting
    plot_data = []
    for y in years:
        if y in s_data:
            row = {'Year': y, 'Supply (US Available)': s_data[y]}
            if show_global: row['Global Demand'] = d_data['global_demand'].get(y)
            if show_us_tech: row['US Tech Demand'] = d_data['us_tech_demand'].get(y)
            if show_us_located: row['US Located Demand'] = d_data['us_located_demand'].get(y)
            plot_data.append(row)
            
    df = pd.DataFrame(plot_data)
    
    # Plot
    fig = go.Figure()
    
    # Supply Area
    fig.add_trace(go.Scatter(
        x=df['Year'], y=df['Supply (US Available)'],
        mode='lines', name='US Supply Capacity',
        line=dict(width=3, color='green'),
        fill='tozeroy'
    ))
    
    # Demand Lines
    if show_us_located:
        fig.add_trace(go.Scatter(
            x=df['Year'], y=df['US Located Demand'],
            mode='lines+markers', name='US Located Demand',
            line=dict(width=3, color='blue')
        ))
        
    if show_us_tech:
        fig.add_trace(go.Scatter(
            x=df['Year'], y=df['US Tech Demand'],
            mode='lines', name='US Tech Stack Demand',
            line=dict(width=2, dash='dash', color='orange')
        ))
        
    if show_global:
        fig.add_trace(go.Scatter(
            x=df['Year'], y=df['Global Demand'],
            mode='lines', name='Global Demand',
            line=dict(width=2, dash='dot', color='gray')
        ))
        
    fig.update_layout(
        title="Power Supply vs. Demand Trajectories (GW)",
        xaxis_title="Year",
        yaxis_title="Gigawatts (GW)",
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Gap Metrics
    st.markdown("### 📉 Gap Metrics (US Located Demand vs. Supply)")
    cols = st.columns(3)
    
    target_years = [2027, 2030, 2035]
    for i, year in enumerate(target_years):
        demand = d_data['us_located_demand'].get(year, 0)
        supply = s_data.get(year, 0)
        gap = supply - demand
        color = "red" if gap < 0 else "green"
        
        cols[i].metric(
            label=f"{year} Gap",
            value=f"{gap:+.1f} GW",
            delta=f"Supply: {supply}GW | Demand: {demand}GW",
            delta_color="off"
        )
        if gap < 0:
            cols[i].markdown(f":red[**Deficit**: {abs(gap):.1f} GW]")
        else:
            cols[i].markdown(f":green[**Surplus**: {gap:.1f} GW]")

def show_supply_analysis(supply_scen):
    st.subheader("Regional Supply Analysis")
    
    st.markdown("""
    **Supply Constraint Methodology**:
    Supply is constrained by interconnection queue throughput, transmission lead times, and generation retirement schedules.
    The table below shows the current status of major ISO queues.
    """)
    
    # ISO Table
    df_iso = pd.DataFrame(ISO_DATA)
    df_iso['Effective Capacity (GW)'] = df_iso['queue_gw'] * df_iso['completion_rate']
    
    st.dataframe(
        df_iso,
        column_config={
            "queue_gw": st.column_config.NumberColumn("Queue Size (GW)", format="%d GW"),
            "completion_rate": st.column_config.ProgressColumn("Completion Rate", format="%.0f%%", min_value=0, max_value=1),
            "Effective Capacity (GW)": st.column_config.NumberColumn("Est. Deliverable (GW)", format="%.1f GW"),
        },
        use_container_width=True,
        hide_index=True
    )
    
    # Chart
    fig = px.bar(
        df_iso, 
        x='iso', 
        y=['Effective Capacity (GW)', 'queue_gw'],
        title="Queue Size vs. Deliverable Capacity by ISO",
        barmode='overlay',
        labels={'value': 'Gigawatts (GW)', 'variable': 'Metric'}
    )
    st.plotly_chart(fig, use_container_width=True)

def show_bottoms_up_build():
    st.subheader("🏗️ Bottoms-Up Demand Build")
    st.markdown("Deriving power demand from physical semiconductor supply chain constraints (CoWoS).")
    
    # Controls
    col1, col2 = st.columns(2)
    with col1:
        year = st.slider("Select Year", 2024, 2030, 2027)
        cowos_wpm = st.number_input("CoWoS Capacity (Wafers/Month)", value=COWOS_BASELINE.get(year, 100000))
    
    with col2:
        tdp = st.number_input("Avg Chip TDP (kW)", value=1.0, step=0.1)
        pue = st.number_input("Avg Data Center PUE", value=1.3, step=0.1)
    
    # Calculate
    # Recalculate with user inputs
    annual_wafers = cowos_wpm * 12
    total_dies = annual_wafers * CONVERSION_FACTORS['dies_per_wafer']
    good_dies = total_dies * CONVERSION_FACTORS['yield']
    annual_chip_power_gw = (good_dies * tdp) / 1e6
    annual_dc_power_gw = annual_chip_power_gw * pue
    
    # Display Flow
    st.markdown("### Conversion Logic")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("1. Wafer Supply", f"{annual_wafers/1e3:.1f}K", "Annual Wafers")
    c2.metric("2. Chip Yield", f"{good_dies/1e6:.1f}M", f"Good Dies (@{CONVERSION_FACTORS['yield']*100:.0f}%)")
    c3.metric("3. Chip Power", f"{annual_chip_power_gw:.1f} GW", f"@{tdp} kW/chip")
    c4.metric("4. Facility Power", f"{annual_dc_power_gw:.1f} GW", f"PUE {pue}")
    
    st.info(f"**Insight**: In {year}, based on {cowos_wpm:,} WPM CoWoS capacity, the industry can physically deploy **{annual_dc_power_gw:.1f} GW** of new AI data center capacity globally.")
    
    # Visual Sankey-like flow (using metrics for now)
    st.markdown("---")
    st.markdown(f"""
    **Calculation Path:**
    1. **{cowos_wpm:,}** Wafers/Month × 12 = **{annual_wafers:,}** Wafers/Year
    2. × **{CONVERSION_FACTORS['dies_per_wafer']}** Dies/Wafer × **{CONVERSION_FACTORS['yield']*100}%** Yield = **{good_dies:,.0f}** AI Accelerators
    3. × **{tdp}** kW/Chip = **{annual_chip_power_gw*1e6:,.0f}** kW IT Load
    4. × **{pue}** PUE = **{annual_dc_power_gw:.2f}** GW Total Facility Load
    """)
