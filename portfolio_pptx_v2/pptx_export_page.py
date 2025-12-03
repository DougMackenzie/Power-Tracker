"""
PPTX Export Streamlit Page
==========================
UI for exporting site profiles to branded PowerPoint presentations.
"""

import streamlit as st
import os
import io
import tempfile
from datetime import datetime
from typing import Dict, Optional

# Import export module
try:
    from pptx_export import (
        export_site_to_pptx,
        export_multiple_sites,
        analyze_template,
        CapacityTrajectory,
        PhaseData,
        ExportConfig,
        generate_capacity_trajectory_chart,
        JLL_COLORS,
        MATPLOTLIB_AVAILABLE,
    )
    EXPORT_AVAILABLE = True
except ImportError as e:
    EXPORT_AVAILABLE = False
    EXPORT_ERROR = str(e)


# =============================================================================
# CONSTANTS
# =============================================================================

DEFAULT_TEMPLATE_PATH = "/mnt/user-data/uploads/Sample_Site_Profile_Template.pptx"
TEMPLATE_STORAGE_KEY = "pptx_template_path"


# =============================================================================
# SESSION STATE
# =============================================================================

def init_export_session_state():
    """Initialize session state for export page."""
    if 'export_template_path' not in st.session_state:
        st.session_state.export_template_path = DEFAULT_TEMPLATE_PATH
    if 'export_config' not in st.session_state:
        st.session_state.export_config = ExportConfig()
    if 'template_analysis' not in st.session_state:
        st.session_state.template_analysis = None


# =============================================================================
# MAIN PAGE
# =============================================================================

def show_pptx_export(data_layer):
    """PPTX Export page."""
    st.header("📊 PowerPoint Export")
    
    init_export_session_state()
    
    if not EXPORT_AVAILABLE:
        st.error(f"Export module not available: {EXPORT_ERROR}")
        st.info("Install required packages: `pip install python-pptx matplotlib`")
        return
    
    if not PPTX_AVAILABLE:
        st.error("python-pptx library not installed. Run: `pip install python-pptx`")
        return
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📤 Export Site",
        "📋 Batch Export",
        "📁 Template Settings",
        "📈 Preview Charts"
    ])
    
    # Get sites
    sites = data_layer.get_all_sites()
    
    # ==========================================================================
    # TAB 1: Export Single Site
    # ==========================================================================
    with tab1:
        show_single_export(sites)
    
    # ==========================================================================
    # TAB 2: Batch Export
    # ==========================================================================
    with tab2:
        show_batch_export(sites)
    
    # ==========================================================================
    # TAB 3: Template Settings
    # ==========================================================================
    with tab3:
        show_template_settings()
    
    # ==========================================================================
    # TAB 4: Preview Charts
    # ==========================================================================
    with tab4:
        show_chart_preview(sites)


# =============================================================================
# SINGLE EXPORT TAB
# =============================================================================

def show_single_export(sites: Dict):
    """Single site export interface."""
    st.subheader("Export Site Profile")
    
    if not sites:
        st.warning("No sites available. Add sites first.")
        return
    
    # Site selector
    site_options = {f"{s.get('name', sid)} ({sid})": sid for sid, s in sites.items()}
    selected = st.selectbox("Select Site", options=list(site_options.keys()))
    site_id = site_options[selected]
    site_data = sites[site_id]
    
    st.divider()
    
    # Export options
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Include Slides:**")
        include_capacity_trajectory = st.checkbox("Capacity Trajectory", value=True)
        include_infrastructure = st.checkbox("Infrastructure & Critical Path", value=True)
        include_score_analysis = st.checkbox("Score Analysis", value=True)
        include_market_analysis = st.checkbox("Market Analysis", value=True)
    
    with col2:
        st.write("**Contact Information:**")
        contact_name = st.text_input("Name", value=st.session_state.export_config.contact_name or "")
        contact_title = st.text_input("Title", value=st.session_state.export_config.contact_title or "")
        contact_phone = st.text_input("Phone", value=st.session_state.export_config.contact_phone or "")
        contact_email = st.text_input("Email", value=st.session_state.export_config.contact_email or "")
    
    st.divider()
    
    # Preview site data
    with st.expander("Preview Site Data"):
        preview_cols = ['name', 'state', 'target_mw', 'utility', 'total_acres', 'county']
        for col in preview_cols:
            if col in site_data:
                st.write(f"**{col.replace('_', ' ').title()}:** {site_data[col]}")
    
    # Export button
    if st.button("🚀 Generate PowerPoint", type="primary", use_container_width=True):
        template_path = st.session_state.export_template_path
        
        if not os.path.exists(template_path):
            st.error(f"Template not found: {template_path}")
            st.info("Upload a template in the Template Settings tab.")
            return
        
        # Build config
        config = ExportConfig(
            include_capacity_trajectory=include_capacity_trajectory,
            include_infrastructure=include_infrastructure,
            include_score_analysis=include_score_analysis,
            include_market_analysis=include_market_analysis,
            contact_name=contact_name,
            contact_title=contact_title,
            contact_phone=contact_phone,
            contact_email=contact_email,
        )
        
        # Save config for next time
        st.session_state.export_config = config
        
        with st.spinner("Generating PowerPoint..."):
            try:
                # Create temp output
                output_filename = f"{site_id}_profile_{datetime.now().strftime('%Y%m%d')}.pptx"
                output_path = f"/mnt/user-data/outputs/{output_filename}"
                
                # Export
                result_path = export_site_to_pptx(
                    site_data=site_data,
                    template_path=template_path,
                    output_path=output_path,
                    config=config,
                )
                
                st.success("✅ PowerPoint generated successfully!")
                
                # Download link
                with open(result_path, 'rb') as f:
                    st.download_button(
                        "📥 Download PowerPoint",
                        f,
                        file_name=output_filename,
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        use_container_width=True,
                    )
                
                # Also provide direct link
                st.markdown(f"[View file](computer://{result_path})")
            
            except Exception as e:
                st.error(f"Export failed: {str(e)}")
                import traceback
                st.code(traceback.format_exc())


# =============================================================================
# BATCH EXPORT TAB
# =============================================================================

def show_batch_export(sites: Dict):
    """Batch export multiple sites."""
    st.subheader("Batch Export")
    
    if not sites:
        st.warning("No sites available.")
        return
    
    st.info("Export multiple site profiles at once. Each site generates a separate PPTX file.")
    
    # Site multi-select
    site_options = {f"{s.get('name', sid)}": sid for sid, s in sites.items()}
    selected_names = st.multiselect(
        "Select Sites to Export",
        options=list(site_options.keys()),
        default=list(site_options.keys())[:3] if len(site_options) >= 3 else list(site_options.keys())
    )
    
    selected_ids = [site_options[name] for name in selected_names]
    
    st.write(f"**{len(selected_ids)} site(s) selected**")
    
    # Export options (simplified)
    col1, col2 = st.columns(2)
    with col1:
        include_capacity_trajectory = st.checkbox("Include Capacity Trajectory", value=True, key="batch_traj")
        include_infrastructure = st.checkbox("Include Infrastructure", value=True, key="batch_infra")
        include_score_analysis = st.checkbox("Include Score Analysis", value=True, key="batch_score")
        include_market_analysis = st.checkbox("Include Market Analysis", value=True, key="batch_market")
    
    with col2:
        contact_name = st.text_input("Contact Name", key="batch_contact")
        contact_email = st.text_input("Contact Email", key="batch_email")
    
    if st.button("🚀 Export All Selected", type="primary", disabled=len(selected_ids) == 0):
        template_path = st.session_state.export_template_path
        
        if not os.path.exists(template_path):
            st.error("Template not found. Configure in Template Settings tab.")
            return
        
        config = ExportConfig(
            include_capacity_trajectory=include_capacity_trajectory,
            include_infrastructure=include_infrastructure,
            include_score_analysis=include_score_analysis,
            include_market_analysis=include_market_analysis,
            contact_name=contact_name,
            contact_email=contact_email,
        )
        
        progress = st.progress(0)
        status = st.empty()
        
        output_dir = "/mnt/user-data/outputs/batch_export"
        os.makedirs(output_dir, exist_ok=True)
        
        successful = []
        failed = []
        
        for i, site_id in enumerate(selected_ids):
            status.text(f"Exporting {site_id}...")
            progress.progress((i + 1) / len(selected_ids))
            
            try:
                site_data = sites[site_id]
                output_path = os.path.join(output_dir, f"{site_id}_profile.pptx")
                
                export_site_to_pptx(
                    site_data=site_data,
                    template_path=template_path,
                    output_path=output_path,
                    config=config,
                )
                successful.append(site_id)
            except Exception as e:
                failed.append((site_id, str(e)))
        
        progress.empty()
        status.empty()
        
        # Results
        if successful:
            st.success(f"✅ Successfully exported {len(successful)} site(s)")
            st.markdown(f"[View exports](computer://{output_dir})")
        
        if failed:
            st.error(f"❌ Failed to export {len(failed)} site(s)")
            for site_id, error in failed:
                st.write(f"- {site_id}: {error}")


# =============================================================================
# TEMPLATE SETTINGS TAB
# =============================================================================

def show_template_settings():
    """Template configuration interface."""
    st.subheader("Template Settings")
    
    # Current template
    current_template = st.session_state.export_template_path
    st.write(f"**Current Template:** `{current_template}`")
    
    template_exists = os.path.exists(current_template)
    if template_exists:
        st.success("✅ Template file found")
    else:
        st.warning("⚠️ Template file not found")
    
    st.divider()
    
    # Upload new template
    st.write("**Upload New Template**")
    uploaded = st.file_uploader(
        "Upload .pptx template",
        type=['pptx'],
        help="Upload your branded PowerPoint template"
    )
    
    if uploaded:
        # Save to uploads
        save_path = f"/mnt/user-data/uploads/{uploaded.name}"
        with open(save_path, 'wb') as f:
            f.write(uploaded.getvalue())
        
        st.session_state.export_template_path = save_path
        st.success(f"Template saved: {save_path}")
        st.rerun()
    
    st.divider()
    
    # Template analysis
    st.write("**Template Analysis**")
    
    if template_exists:
        if st.button("🔍 Analyze Template"):
            with st.spinner("Analyzing..."):
                try:
                    analysis = analyze_template(current_template)
                    st.session_state.template_analysis = analysis
                except Exception as e:
                    st.error(f"Analysis failed: {e}")
        
        if st.session_state.template_analysis:
            analysis = st.session_state.template_analysis
            
            st.write(f"**Slides:** {analysis['slide_count']}")
            
            for slide in analysis['slides']:
                with st.expander(f"Slide {slide['index']}"):
                    if slide['shapes']:
                        st.write("**Text shapes:**")
                        for shape in slide['shapes']:
                            st.text(shape['text'][:100])
                    
                    if slide['tables']:
                        st.write("**Tables:**")
                        for table in slide['tables']:
                            st.write(f"- {table['rows']} rows × {table['cols']} columns")
    
    st.divider()
    
    # Placeholder mapping
    st.write("**Field Mapping**")
    st.info("""
    The export system automatically maps these app fields to template placeholders:
    
    | App Field | Template Text |
    |-----------|---------------|
    | `name` | "SITE NAME" |
    | `state` | "[STATE]" |
    | `target_mw` | "1GW+" |
    | `utility` | "OG&E 345kV line" |
    | `total_acres` | "1,250 acres" |
    | `coordinates` | "[Coordinates linked]" |
    | Contact fields | "NAME", "TITLE", "Phone", "Email" |
    """)


# =============================================================================
# CHART PREVIEW TAB
# =============================================================================

def show_chart_preview(sites: Dict):
    """Preview generated charts."""
    st.subheader("Chart Preview")
    
    if not MATPLOTLIB_AVAILABLE:
        st.error("matplotlib not available. Install with: `pip install matplotlib`")
        return
    
    # Site selector
    if not sites:
        st.warning("No sites available")
        return
    
    site_options = {f"{s.get('name', sid)}": sid for sid, s in sites.items()}
    selected = st.selectbox("Select Site", options=list(site_options.keys()), key="chart_preview_site")
    site_id = site_options[selected]
    site_data = sites[site_id]
    
    st.divider()
    
    # Tab selection for different chart types
    chart_tab = st.radio("Chart Type", ["Capacity Trajectory", "Market Analysis"], horizontal=True)
    
    if chart_tab == "Capacity Trajectory":
        st.write("**Capacity Trajectory Parameters**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            target_mw = st.number_input(
                "Target MW",
                value=int(site_data.get('target_mw', 600)),
                min_value=100,
                max_value=5000,
                step=100
            )
        with col2:
            start_year = st.number_input(
                "Start Year",
                value=2028,
                min_value=2025,
                max_value=2035
            )
        with col3:
            phase1_pct = st.slider(
                "Phase 1 (%)",
                min_value=10,
                max_value=50,
                value=20,
                help="Phase 1 as percentage of total capacity"
            )
        
        if st.button("Generate Preview", type="primary"):
            with st.spinner("Generating chart..."):
                try:
                    trajectory = CapacityTrajectory.generate_default(
                        target_mw=target_mw,
                        phase1_mw=target_mw * phase1_pct / 100,
                        start_year=start_year,
                    )
                    
                    chart_path = "/tmp/capacity_trajectory_preview.png"
                    generate_capacity_trajectory_chart(
                        trajectory,
                        site_data.get('name', 'Site'),
                        chart_path,
                    )
                    
                    st.image(chart_path, use_container_width=True)
                    
                    with open(chart_path, 'rb') as f:
                        st.download_button(
                            "Download Chart Image",
                            f,
                            file_name="capacity_trajectory_chart.png",
                            mime="image/png"
                        )
                
                except Exception as e:
                    st.error(f"Chart generation failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    
    else:  # Market Analysis
        st.write("**Market Analysis Preview**")
        st.info("""
        Market Analysis uses the State Analysis framework to compare:
        - **Timeline to Power**: Queue times and power costs across states
        - **Competitive Landscape**: Existing DC capacity, hyperscaler presence
        - **ISO & Utility Profile**: Regulatory structure, rates, renewable mix
        - **SWOT Summary**: State-specific strengths, weaknesses, opportunities, threats
        """)
        
        # State selection for comparison
        state_code = site_data.get('state_code', site_data.get('state', 'OK')[:2].upper())
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Site State:** {state_code}")
        with col2:
            comparison_states = st.multiselect(
                "Compare to States",
                options=['TX', 'GA', 'OH', 'VA', 'IN', 'WY', 'AZ'],
                default=['TX', 'GA'],
                max_selections=3
            )
        
        if st.button("Generate Market Preview", type="primary"):
            st.info("Market Analysis chart will be generated during PPTX export using state analysis data.")
    
    st.divider()
    
    # Data documentation
    st.write("**Data Sources**")
    st.markdown("""
    **Capacity Trajectory Data Format:**
    ```json
    {
        "2028": {"interconnection_mw": 100, "generation_mw": 100},
        "2029": {"interconnection_mw": 600, "generation_mw": 300},
    }
    ```
    
    **Market Analysis Data** is sourced from the State Analysis framework (`state_analysis.py`):
    - State profiles with scores across 6 dimensions
    - ISO/utility characteristics
    - Competitive landscape data
    - SWOT analysis per state
    
    To customize market data for a site, add a `market_analysis` field:
    ```json
    {
        "market_analysis": {
            "state_code": "OK",
            "primary_iso": "SPP",
            "utility_name": "OG&E",
            "avg_queue_time_months": 30,
            "avg_industrial_rate": 0.055,
            "comparison_states": {
                "TX": {"queue_months": 36, "rate": 0.065, "score": 80}
            }
        }
    }
    ```
    """)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'show_pptx_export',
    'init_export_session_state',
]
