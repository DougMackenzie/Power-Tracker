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
# Based on Power Research Framework.pdf
# Scenario A (Acceleration):
# - Global: 2030 ~150 GW -> 2035 400 GW (Aggressive scaling)
# - US Stack: 2030 115 GW -> 2035 290 GW
# - US Located: ~70% of US Stack
# Scenario B (Plateau):
# - Global: 2030 ~80 GW -> 2035 180 GW
# - US Stack: 2030 85 GW -> 2035 110 GW
DEMAND_DATA = {
    DemandScenario.ACCELERATION: {
        'description': "**Scenario A (Acceleration)**: AI business case scales. Reasoning inference drives exponential compute. Model sizes 10x/2yr.",
        'global_demand': {
            2024: 14, 2025: 28, 2026: 48, 2027: 75, 2028: 100, 2029: 125, 
            2030: 150, 2031: 190, 2032: 235, 2033: 285, 2034: 340, 2035: 400
        },
        'us_tech_demand': {
            2024: 12, 2025: 21, 2026: 35, 2027: 55, 2028: 75, 2029: 95, 
            2030: 115, 2031: 145, 2032: 175, 2033: 210, 2034: 250, 2035: 290
        },
        'us_located_demand': {
            2024: 10, 2025: 15, 2026: 25, 2027: 39, 2028: 53, 2029: 67, 
            2030: 81, 2031: 102, 2032: 123, 2033: 147, 2034: 175, 2035: 203
        },
    },
    DemandScenario.PLATEAU: {
        'description': "**Scenario B (Plateau)**: AI business case fails to materialize. Efficiency gains outpace demand. ROI skepticism.",
        'global_demand': {
            2024: 14, 2025: 24, 2026: 35, 2027: 45, 2028: 55, 2029: 65, 
            2030: 80, 2031: 95, 2032: 115, 2033: 135, 2034: 155, 2035: 180
        },
        'us_tech_demand': {
            2024: 12, 2025: 18, 2026: 24, 2027: 30, 2028: 45, 2029: 65, 
            2030: 85, 2031: 90, 2032: 95, 2033: 100, 2034: 105, 2035: 110
        },
        'us_located_demand': {
            2024: 10, 2025: 13, 2026: 17, 2027: 21, 2028: 32, 2029: 46, 
            2030: 60, 2031: 63, 2032: 67, 2033: 70, 2034: 74, 2035: 77
        },
    }
}

# Supply Trajectories (GW) - US Deliverable
# Low Scenario matches "Most Likely" deficit analysis:
# 2030 Supply ~50 GW (vs 115 GW Stack Demand = -65 GW Gap)
# 2035 Supply ~140 GW (vs 230 GW Stack Demand = -90 GW Gap)
SUPPLY_DATA = {
    SupplyScenario.LOW: {
        'description': "**Most Likely**: Utility delivery slippage, minimal GETs/SMR. Queue backlogs persist.",
        'trajectory': {
            2024: 10, 2025: 15, 2026: 22, 2027: 30, 2028: 36, 2029: 43, 
            2030: 50, 2031: 65, 2032: 80, 2033: 100, 2034: 120, 2035: 140
        }
    },
    SupplyScenario.MEDIUM: {
        'description': "Moderate reform impact, some GETs adoption. Queue completion rates improve slightly.",
        'trajectory': {
            2024: 10, 2025: 18, 2026: 28, 2027: 40, 2028: 55, 2029: 70, 
            2030: 90, 2031: 115, 2032: 145, 2033: 180, 2034: 220, 2035: 257
        }
    },
    SupplyScenario.HIGH: {
        'description': "Aggressive reforms + GETs + SMR deployment. Major policy shifts unlock capacity.",
        'trajectory': {
            2024: 10, 2025: 22, 2026: 38, 2027: 55, 2028: 80, 2029: 110, 
            2030: 150, 2031: 190, 2032: 240, 2033: 290, 2034: 350, 2035: 418
        }
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
    st.title("🔬 Power Research Framework (v2.4)")
    st.markdown("Dynamic analysis of AI power demand vs. utility supply constraints.")

    # ... (rest of function) ...

    with tab_demand_build:
        show_bottoms_up_build()

# ... (skip to show_bottoms_up_build) ...

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
    
    # Visual Sankey-like flow
    st.markdown("---")
    st.markdown(f"""
    **Calculation Path:**
    1. **{cowos_wpm:,}** Wafers/Month × 12 = **{annual_wafers:,}** Wafers/Year
    2. × **{CONVERSION_FACTORS['dies_per_wafer']}** Dies/Wafer × **{CONVERSION_FACTORS['yield']*100}%** Yield = **{good_dies:,.0f}** AI Accelerators
    3. × **{tdp}** kW/Chip = **{annual_chip_power_gw*1e6:,.0f}** kW IT Load
    4. × **{pue}** PUE = **{annual_dc_power_gw:.2f}** GW Total Facility Load
    """)

    st.markdown("---")
    with st.expander("📚 Methodology & Definitions (Grounded in Research)", expanded=True):
        st.markdown("""
        ### Methodology: Wafer → Package → TDP → GW
        Explicit modeling through CoWoS constraints, chip TDP mix, server overhead (1.45x), utilization (60-80%), and PUE (1.12-1.4).
        
        **Why this analysis is higher than others:**
        - Explicit wafer-to-power conversion through packaging constraints rather than extrapolating historical DC growth trends.
        - Accounts for chip TDP increases (700W → 1,400W+) and AI-specific infrastructure scaling.
        
        ### Geographic Definitions
        
        **1. U.S. Technology Stack (~75-80% of Global)**
        - Chips designed by U.S. companies regardless of manufacturing location.
        - **Scope**: NVIDIA, AMD, Google, Amazon, Microsoft, Meta, Broadcom, Marvell, Intel, Qualcomm.
        - **Taiwan Concentration Risk**: 55% of U.S. AI chip capacity is fabbed in Taiwan.
        
        **2. U.S. Domestic Deployment (~70% of US Stack)**
        - Power demand that materializes within U.S. borders.
        - **Drivers**: Training concentration (IP security), North American inference market, ecosystem depth.
        
        **3. International Overspill (~30%)**
        - Demand forced overseas by U.S. power constraints (5-9 year queues).
        - **Destinations**: Middle East (10-15%), Europe (8-12%), Asia-Pacific (5-8%).
        - **Critical Insight**: International sites face identical equipment bottlenecks (gas turbines, transformers). Overspill does not relieve global pressure; it queues behind it.
        """)
