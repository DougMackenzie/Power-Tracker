"""
Program Management Streamlit Page
==================================
Add this to your streamlit_llm.py or import as a module.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional
from datetime import datetime

# Import save function from streamlit_app
from . import streamlit_app

# Import program tracker
from .program_tracker import (
    ProgramTrackerData,
    CONTRACT_MULTIPLIERS,
    PROBABILITY_DRIVERS,
    STAGE_LABELS,
    TRACKER_COLUMNS,
    TRACKER_COLUMN_ORDER,
    calculate_portfolio_summary,
    get_stage_label,
    get_stage_color,
    format_currency,
    format_percentage,
    FeeCalculationMethod,
    calculate_fee_potential,
    extend_site_with_tracker,
)


# =============================================================================
# PROGRAM TRACKER PAGE
# =============================================================================

def show_program_tracker():
    """Program Management Dashboard."""
    st.header("📊 Program Tracker")
    
    # Get all sites from session state
    db = st.session_state.db
    sites = db.get('sites', {})
    
    if not sites:
        st.info("No sites in database. Add sites to begin tracking.")
        return
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Portfolio Summary",
        "📋 Deal Status",
        "✏️ Edit Tracker",
        "💰 Fee Settings",
        "📥 Portfolio Export"
    ])
    
    # =========================================================================
    # TAB 1: Portfolio Summary Dashboard
    # =========================================================================
    with tab1:
        show_portfolio_summary(sites)
    
    # =========================================================================
    # TAB 2: Deal Status Overview
    # =========================================================================
    with tab2:
        show_deal_status(sites)
    
    # =========================================================================
    # TAB 3: Edit Tracker Data
    # =========================================================================
    with tab3:
        show_tracker_editor(sites)
    
    # =========================================================================
    # TAB 4: Fee Calculation Settings
    # =========================================================================
    with tab4:
        show_fee_settings(sites)

    # =========================================================================
    # TAB 5: Portfolio Export
    # =========================================================================
    with tab5:
        show_portfolio_export(sites)


def show_portfolio_summary(sites: Dict):
    """Portfolio summary dashboard with charts."""
    
    # Convert to list for summary calculation
    site_list = []
    for site_id, site in sites.items():
        site_data = site.copy()
        site_data['site_id'] = site_id
        site_list.append(site_data)
    
    # Calculate summary
    summary = calculate_portfolio_summary(site_list)
    
    # Top-level metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Sites", summary['site_count'])
    with col2:
        st.metric("Total Fee Potential", format_currency(summary['total_potential']))
    with col3:
        st.metric("Weighted Pipeline", format_currency(summary['total_weighted']))
    with col4:
        st.metric("Avg Probability", format_percentage(summary['avg_probability']))
    
    st.divider()
    
    # Charts Row
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Pipeline by Stage")
        
        stage_data = []
        for stage_name, stage_sites in summary['by_stage'].items():
            stage_data.append({
                'Stage': stage_name.title(),
                'Count': len(stage_sites),
                'Weighted Value': sum(s['weighted'] for s in stage_sites),
                'Potential Value': sum(s['potential'] for s in stage_sites),
            })
        
        if stage_data:
            df_stage = pd.DataFrame(stage_data)
            fig = px.bar(
                df_stage,
                x='Stage',
                y='Weighted Value',
                color='Stage',
                color_discrete_map={
                    'Early': '#ef4444',
                    'Developing': '#f59e0b',
                    'Advanced': '#3b82f6',
                    'Closing': '#22c55e'
                },
                text='Count',
            )
            fig.update_layout(showlegend=False, height=300)
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Pipeline by Client/Partner")
        
        client_data = []
        for client, data in summary['by_client'].items():
            client_data.append({
                'Client': client,
                'Sites': data['count'],
                'Potential': data['potential'],
                'Weighted': data['weighted'],
            })
        
        if client_data:
            df_client = pd.DataFrame(client_data)
            fig = px.pie(
                df_client,
                values='Weighted',
                names='Client',
                hole=0.4,
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    # Detailed Site Table
    st.subheader("Site Details")
    
    table_data = []
    for site_id, site in sites.items():
        tracker = ProgramTrackerData.from_dict({**site, 'site_id': site_id})
        
        table_data.append({
            'Site': site.get('name', site_id),
            'Client': tracker.client or '-',
            'State': site.get('state', '-'),
            'MW': site.get('target_mw', 0),
            'Contract': tracker.contract_status,
            'Probability': tracker.probability,
            'Fee Potential': tracker.total_fee_potential,
            'Weighted Fee': tracker.weighted_fee,
        })
    
    if table_data:
        df = pd.DataFrame(table_data)
        df['Probability'] = df['Probability'].apply(lambda x: f"{x*100:.1f}%")
        df['Fee Potential'] = df['Fee Potential'].apply(lambda x: f"${x:,.0f}")
        df['Weighted Fee'] = df['Weighted Fee'].apply(lambda x: f"${x:,.0f}")
        
        st.dataframe(df, use_container_width=True, hide_index=True)


def show_deal_status(sites: Dict):
    """Visual deal status board."""
    st.subheader("Deal Progress Overview")
    
    for site_id, site in sites.items():
        tracker = ProgramTrackerData.from_dict({**site, 'site_id': site_id})
        
        with st.expander(f"**{site.get('name', site_id)}** - {tracker.client or 'No Client'} | {format_percentage(tracker.probability)} | {format_currency(tracker.weighted_fee)}", expanded=False):
            
            # Contract Status (Gatekeeper)
            contract_col, prob_col = st.columns([2, 1])
            with contract_col:
                contract_color = {
                    'No': '🔴', 'Verbal': '🟠', 'MOU': '🟡', 'Definitive': '🟢'
                }.get(tracker.contract_status, '⚪')
                st.write(f"**Contract:** {contract_color} {tracker.contract_status} (×{CONTRACT_MULTIPLIERS.get(tracker.contract_status, 0):.0%})")
            
            with prob_col:
                st.metric("Probability", format_percentage(tracker.probability))
            
            st.divider()
            
            # Progress Bars for Each Driver
            drivers = [
                ('Buyer', 'buyer', tracker.buyer_stage, 4, 30),
                ('Site Control', 'site_control', tracker.site_control_stage, 4, 20),
                ('Power', 'power', tracker.power_stage, 4, 20),
                ('Zoning', 'zoning', tracker.zoning_stage, 3, 20),
                ('Incentives', 'incentives', tracker.incentives_stage, 4, 10),
            ]
            
            col1, col2 = st.columns(2)
            
            for i, (label, driver, stage, max_stage, weight) in enumerate(drivers):
                col = col1 if i % 2 == 0 else col2
                with col:
                    progress = (stage - 1) / (max_stage - 1) if max_stage > 1 else 0
                    stage_label = get_stage_label(driver, stage)
                    color = get_stage_color(stage, max_stage)
                    
                    st.write(f"**{label}** ({weight}%): {color} {stage_label}")
                    st.progress(progress)
            
            # Additional info row
            col1, col2, col3 = st.columns(3)
            with col1:
                marketing_label = get_stage_label('marketing', tracker.marketing_stage)
                st.write(f"📣 Marketing: {marketing_label}")
            with col2:
                water_label = get_stage_label('water', tracker.water_stage)
                st.write(f"💧 Water: {water_label}")
            with col3:
                st.write(f"📝 Notes: {tracker.tracker_notes or 'None'}")


def show_tracker_editor(sites: Dict):
    """Editor for updating tracker status."""
    st.subheader("Edit Site Tracker Status")
    
    site_options = {f"{s.get('name', sid)} ({sid})": sid for sid, s in sites.items()}
    selected = st.selectbox("Select Site to Edit", options=list(site_options.keys()))
    
    if not selected:
        return
    
    site_id = site_options[selected]
    site = sites[site_id]
    tracker = ProgramTrackerData.from_dict({**site, 'site_id': site_id})
    
    st.divider()
    
    with st.form("tracker_edit_form"):
        st.write("### Deal Information")
        
        col1, col2 = st.columns(2)
        with col1:
            client = st.text_input("Client/Partner", value=tracker.client)
            
            contract_options = ['No', 'Verbal', 'MOU', 'Definitive']
            contract_idx = contract_options.index(tracker.contract_status) if tracker.contract_status in contract_options else 0
            contract_status = st.selectbox("Contract Status", contract_options, index=contract_idx)
        
        with col2:
            total_fee = st.number_input(
                "Total Fee Potential ($)",
                value=float(tracker.total_fee_potential),
                min_value=0.0,
                step=100000.0,
                format="%.0f"
            )
            
            tracker_notes = st.text_area("Notes", value=tracker.tracker_notes, height=68)
        
        st.write("### Progress Stages")
        st.caption("Stage 1 = Not Started, Stage 4 = Complete (Zoning has 3 stages)")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.write("**Buyer** (30%)")
            for i in range(1, 5):
                st.caption(f"{i}: {get_stage_label('buyer', i)}")
            buyer_stage = st.selectbox("Buyer Stage", [1, 2, 3, 4], 
                                       index=tracker.buyer_stage - 1,
                                       label_visibility="collapsed",
                                       key="buyer")
        
        with col2:
            st.write("**Site Control** (20%)")
            for i in range(1, 5):
                st.caption(f"{i}: {get_stage_label('site_control', i)}")
            site_control_stage = st.selectbox("Site Control", [1, 2, 3, 4],
                                              index=tracker.site_control_stage - 1,
                                              label_visibility="collapsed",
                                              key="site_control")
        
        with col3:
            st.write("**Power** (20%)")
            for i in range(1, 5):
                st.caption(f"{i}: {get_stage_label('power', i)}")
            power_stage = st.selectbox("Power Stage", [1, 2, 3, 4],
                                       index=tracker.power_stage - 1,
                                       label_visibility="collapsed",
                                       key="power")
        
        with col4:
            st.write("**Zoning** (20%)")
            for i in range(1, 4):
                st.caption(f"{i}: {get_stage_label('zoning', i)}")
            zoning_stage = st.selectbox("Zoning Stage", [1, 2, 3],
                                        index=min(tracker.zoning_stage - 1, 2),
                                        label_visibility="collapsed",
                                        key="zoning")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.write("**Incentives** (10%)")
            for i in range(1, 5):
                st.caption(f"{i}: {get_stage_label('incentives', i)}")
            incentives_stage = st.selectbox("Incentives", [1, 2, 3, 4],
                                            index=tracker.incentives_stage - 1,
                                            label_visibility="collapsed",
                                            key="incentives")
        
        with col2:
            st.write("**Marketing** (info only)")
            for i in range(1, 5):
                st.caption(f"{i}: {get_stage_label('marketing', i)}")
            marketing_stage = st.selectbox("Marketing", [1, 2, 3, 4],
                                           index=tracker.marketing_stage - 1,
                                           label_visibility="collapsed",
                                           key="marketing")
        
        with col3:
            st.write("**Water** (info only)")
            for i in range(1, 5):
                st.caption(f"{i}: {get_stage_label('water', i)}")
            water_stage = st.selectbox("Water", [1, 2, 3, 4],
                                       index=tracker.water_stage - 1,
                                       label_visibility="collapsed",
                                       key="water")
        
        st.divider()
        
        # Preview calculation
        preview_tracker = ProgramTrackerData(
            site_id=site_id,
            client=client,
            total_fee_potential=total_fee,
            contract_status=contract_status,
            site_control_stage=site_control_stage,
            power_stage=power_stage,
            marketing_stage=marketing_stage,
            buyer_stage=buyer_stage,
            zoning_stage=zoning_stage,
            water_stage=water_stage,
            incentives_stage=incentives_stage,
            tracker_notes=tracker_notes,
        )
        preview_tracker.update_calculations()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Calculated Probability", format_percentage(preview_tracker.probability))
        with col2:
            st.metric("Weighted Fee", format_currency(preview_tracker.weighted_fee))
        with col3:
            change = preview_tracker.weighted_fee - tracker.weighted_fee
            st.metric("Change from Current", format_currency(change),
                     delta=format_currency(change) if change != 0 else None)
        
        submitted = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
        
        if submitted:
            # Update site data with tracker fields
            updated_site = site.copy()
            updated_site.update({
                'client': client,
                'total_fee_potential': total_fee,
                'contract_status': contract_status,
                'site_control_stage': site_control_stage,
                'power_stage': power_stage,
                'marketing_stage': marketing_stage,
                'buyer_stage': buyer_stage,
                'zoning_stage': zoning_stage,
                'water_stage': water_stage,
                'incentives_stage': incentives_stage,
                'probability': preview_tracker.probability,
                'weighted_fee': preview_tracker.weighted_fee,
                'tracker_notes': tracker_notes,
            })
            
            # Save to database via session state
            db = st.session_state.db
            db['sites'][site_id] = updated_site
            
            # Save to Google Sheets
            streamlit_app.add_site(db, site_id, updated_site)
            
            st.success("✅ Tracker updated successfully!")
            st.rerun()


def show_fee_settings(sites: Dict):
    """Fee calculation methodology settings."""
    st.subheader("Fee Calculation Settings")
    
    st.info("""
    **Fee Calculation Methods:**
    - **Manual**: Enter fee potential directly for each site
    - **Per MW**: Fee = Target MW × Rate per MW
    - **% of Transaction Value**: Fee = Transaction Value × Percentage
    - **Fixed + MW Bonus**: Fee = Fixed Fee + (MW × Bonus Rate)
    """)
    
    # Global settings
    st.write("### Default Calculation Parameters")
    
    col1, col2 = st.columns(2)
    with col1:
        per_mw_rate = st.number_input(
            "Default Rate per MW ($)",
            value=25000,
            step=1000,
            format="%d"
        )
        fixed_fee = st.number_input(
            "Default Fixed Fee ($)",
            value=500000,
            step=50000,
            format="%d"
        )
    with col2:
        pct_rate = st.number_input(
            "Default % of Transaction",
            value=1.5,
            step=0.1,
            format="%.1f"
        ) / 100
        mw_bonus = st.number_input(
            "Default MW Bonus Rate ($)",
            value=10000,
            step=1000,
            format="%d"
        )
    
    st.divider()
    
    # Batch update
    st.write("### Batch Update Fee Potential")
    
    method = st.selectbox(
        "Calculation Method",
        ["manual", "per_mw", "pct_value", "fixed_plus_mw"],
        format_func=lambda x: {
            "manual": "Manual (no change)",
            "per_mw": f"Per MW (${per_mw_rate:,}/MW)",
            "pct_value": f"% of Transaction ({pct_rate:.1%})",
            "fixed_plus_mw": f"Fixed + Bonus (${fixed_fee:,} + ${mw_bonus:,}/MW)"
        }.get(x, x)
    )
    
    if method != "manual":
        st.warning("This will recalculate fee potential for ALL sites based on the selected method.")
        
        # Preview
        st.write("**Preview:**")
        preview_data = []
        for site_id, site in sites.items():
            target_mw = site.get('target_mw', 0) or 0
            current_fee = site.get('total_fee_potential', 0) or 0
            
            new_fee = calculate_fee_potential(
                method=method,
                target_mw=target_mw,
                params={
                    'per_mw_rate': per_mw_rate,
                    'percentage_rate': pct_rate,
                    'fixed_fee': fixed_fee,
                    'mw_bonus_rate': mw_bonus,
                }
            )
            
            preview_data.append({
                'Site': site.get('name', site_id),
                'MW': target_mw,
                'Current Fee': f"${current_fee:,.0f}",
                'New Fee': f"${new_fee:,.0f}",
                'Change': f"${new_fee - current_fee:+,.0f}"
            })
        
        
        df_preview = pd.DataFrame(preview_data)
        st.dataframe(df_preview, use_container_width=True, hide_index=True)
        
        if st.button("🔄 Apply to All Sites", type="primary"):
            # Save using session state
            db = st.session_state.db
            
            success_count = 0
            for site_id, site in sites.items():
                target_mw = site.get('target_mw', 0) or 0
                
                new_fee = calculate_fee_potential(
                    method=method,
                    target_mw=target_mw,
                    params={
                        'per_mw_rate': per_mw_rate,
                        'percentage_rate': pct_rate,
                        'fixed_fee': fixed_fee,
                        'mw_bonus_rate': mw_bonus,
                    }
                )
                
                updated_site = site.copy()
                updated_site['total_fee_potential'] = new_fee
                
                # Recalculate weighted fee
                tracker = ProgramTrackerData.from_dict({**updated_site, 'site_id': site_id})
                tracker.total_fee_potential = new_fee
                tracker.update_calculations()
                updated_site['probability'] = tracker.probability
                updated_site['weighted_fee'] = tracker.weighted_fee
                
                streamlit_app.add_site(db, site_id, updated_site)
                success_count += 1
            
            st.success(f"✅ Updated {success_count} sites")
            st.rerun()
    
    st.divider()
    
    # Probability formula explanation
    st.write("### Probability Calculation Formula")
    
    st.latex(r"\text{Weighted Fee} = \text{Total Fee} \times \text{Base Probability} \times \text{Contract Multiplier}")
    
    st.write("**Contract Multiplier (Gatekeeper):**")
    mult_df = pd.DataFrame([
        {"Status": "No", "Multiplier": "0×", "Effect": "Kills probability"},
        {"Status": "Verbal", "Multiplier": "0.33×", "Effect": "Reduces to 33%"},
        {"Status": "MOU", "Multiplier": "0.66×", "Effect": "Reduces to 66%"},
        {"Status": "Definitive", "Multiplier": "0.90×", "Effect": "Deal risk cap"},
    ])
    st.dataframe(mult_df, use_container_width=True, hide_index=True)
    
    st.write("**Base Probability Drivers:**")
    driver_df = pd.DataFrame([
        {"Driver": "Buyer Progress", "Weight": "30%", "Stages": "4"},
        {"Driver": "Site Control", "Weight": "20%", "Stages": "4"},
        {"Driver": "Power Confirmation", "Weight": "20%", "Stages": "4"},
        {"Driver": "Zoning", "Weight": "20%", "Stages": "3"},
        {"Driver": "Incentives", "Weight": "10%", "Stages": "4"},
    ])
    st.dataframe(driver_df, use_container_width=True, hide_index=True)




# =============================================================================
# GOOGLE SHEETS COLUMN EXTENSION
# =============================================================================

def get_extended_column_mapping():
    """Get full column mapping including tracker columns."""
    from google_integration import SHEET_COLUMNS
    
    # Original columns A-W
    extended = SHEET_COLUMNS.copy()
    
    # Add tracker columns X-AJ
    extended.update(TRACKER_COLUMNS)
    
    return extended


def get_extended_column_order():
    """Get full column order including tracker fields."""
    from google_integration import COLUMN_ORDER
    
    return COLUMN_ORDER + TRACKER_COLUMN_ORDER


def show_portfolio_export(sites: Dict):
    """UI for generating portfolio export."""
    from .portfolio_export import generate_portfolio_export
    from .pptx_export import ExportConfig
    import tempfile
    import os
    
    st.subheader("📥 Portfolio PowerPoint Export")
    st.write("Generate a comprehensive master deck including portfolio summary, rankings, and individual site profiles.")
    
    # Selection
    st.write("### 1. Select Sites")
    
    # Filter by Client
    clients = sorted(list(set(s.get('client', '') for s in sites.values() if s.get('client'))))
    selected_client = st.selectbox("Filter by Client (Optional)", ["All"] + clients)
    
    filtered_sites = sites
    if selected_client != "All":
        filtered_sites = {k: v for k, v in sites.items() if v.get('client') == selected_client}
    
    # Multiselect
    site_options = {f"{s.get('name', sid)} ({sid})": sid for sid, s in filtered_sites.items()}
    selected_ids = st.multiselect(
        "Select Sites to Include",
        options=list(site_options.keys()),
        default=list(site_options.keys())
    )
    
    selected_sites = {site_options[k]: sites[site_options[k]] for k in selected_ids}
    
    st.write(f"Selected **{len(selected_sites)}** sites for export.")
    
    # Configuration
    st.write("### 2. Export Settings")
    
    col1, col2 = st.columns(2)
    with col1:
        include_market = st.checkbox("Include Market Analysis", value=True)
        include_trajectory = st.checkbox("Include Capacity Trajectory", value=True)
        include_infra = st.checkbox("Include Infrastructure", value=True)
    with col2:
        include_boundary = st.checkbox("Include Site Boundary", value=True)
        include_topo = st.checkbox("Include Topography", value=True)
        include_score = st.checkbox("Include Score Analysis", value=True)
        
    st.divider()
    
    # Generate Button
    if st.button("🚀 Generate Portfolio Deck", type="primary", disabled=len(selected_sites) == 0):
        with st.spinner("Generating comprehensive portfolio deck... this may take a minute..."):
            try:
                # Create config
                config = ExportConfig(
                    include_market_analysis=include_market,
                    include_capacity_trajectory=include_trajectory,
                    include_infrastructure=include_infra,
                    include_site_boundary=include_boundary,
                    include_topography=include_topo,
                    include_score_analysis=include_score,
                    contact_name="Douglas Mackenzie", # Default
                    contact_email="douglas.mackenzie@jll.com"
                )
                
                # Temp file for output
                with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
                    output_path = tmp.name
                
                # Template path
                template_path = "Sample Site Profile Template.pptx" # Located in root
                if not os.path.exists(template_path):
                    # Fallback or error
                    st.error(f"Template file '{template_path}' not found in root directory.")
                    return
                
                # Generate
                generate_portfolio_export(selected_sites, template_path, output_path, config)
                
                # Read for download
                with open(output_path, "rb") as f:
                    file_data = f.read()
                
                st.success("✅ Portfolio Deck Generated Successfully!")
                
                st.download_button(
                    label="📥 Download Portfolio Deck (.pptx)",
                    data=file_data,
                    file_name=f"Portfolio_Export_{datetime.now().strftime('%Y%m%d')}.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                )
                
                # Cleanup
                os.unlink(output_path)
                
            except Exception as e:
                st.error(f"Export failed: {str(e)}")
                st.exception(e)


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    'show_program_tracker',
    'show_portfolio_summary',
    'show_deal_status',
    'show_tracker_editor',
    'show_fee_settings',
    'show_portfolio_export',
    'get_extended_column_mapping',
    'get_extended_column_order',
]
