"""
Intelligence Center Page
========================
Streamlit UI for managing utility, market, and industry intelligence.
Central hub for proprietary knowledge that powers triage and diagnosis.
"""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, Optional, List

from .models import TriageVerdict, TimelineRisk
from .engine import research_utility, get_market_snapshot, call_gemini_structured
from .enrichment import UTILITY_LOOKUP, STATE_ISO_DEFAULT


# =============================================================================
# UTILITY INTELLIGENCE PAGE
# =============================================================================

def show_intelligence_center():
    """Main Intelligence Center page."""
    
    st.title("🔍 Intelligence Center")
    st.markdown("""
    Manage proprietary intelligence on utilities, markets, and industry dynamics.
    This knowledge powers triage accuracy and diagnosis depth.
    """)
    
    # Tab navigation
    tab1, tab2, tab3, tab4 = st.tabs([
        "⚡ Utility Intelligence",
        "🗺️ Market Snapshots", 
        "🏭 Industry Intel",
        "📊 Coverage Dashboard"
    ])
    
    with tab1:
        show_utility_intelligence_tab()
    
    with tab2:
        show_market_snapshots_tab()
    
    with tab3:
        show_industry_intel_tab()
    
    with tab4:
        show_coverage_dashboard_tab()


# =============================================================================
# UTILITY INTELLIGENCE TAB
# =============================================================================

def show_utility_intelligence_tab():
    """Utility intelligence management."""
    
    st.subheader("⚡ Utility Intelligence")
    st.markdown("Track utility appetite, capacity, timelines, and relationships.")
    
    # Initialize session state
    if 'utility_intel_db' not in st.session_state:
        st.session_state.utility_intel_db = _load_utility_intel()
    
    # Two columns: list and detail
    col_list, col_detail = st.columns([1, 2])
    
    with col_list:
        st.markdown("### Utilities")
        
        # Add new utility button
        if st.button("➕ Research New Utility", use_container_width=True):
            st.session_state.show_utility_form = True
        
        # List existing utilities
        for utility_id, intel in st.session_state.utility_intel_db.items():
            appetite = intel.get('appetite_rating', 'unknown')
            appetite_icon = {'aggressive': '🟢', 'moderate': '🟡', 'defensive': '🔴'}.get(appetite, '⚪')
            
            if st.button(
                f"{appetite_icon} {intel.get('utility_name', utility_id)}",
                key=f"util_{utility_id}",
                use_container_width=True,
            ):
                st.session_state.selected_utility = utility_id
    
    with col_detail:
        # New utility research form
        if st.session_state.get('show_utility_form'):
            _show_utility_research_form()
        
        # Selected utility detail
        elif st.session_state.get('selected_utility'):
            utility_id = st.session_state.selected_utility
            intel = st.session_state.utility_intel_db.get(utility_id, {})
            _show_utility_detail(utility_id, intel)
        
        else:
            st.info("Select a utility from the list or research a new one.")


def _show_utility_research_form():
    """Form to research a new utility."""
    
    st.markdown("### 🔬 Research New Utility")
    
    with st.form("utility_research_form"):
        utility_name = st.text_input(
            "Utility Name *",
            placeholder="e.g., PSO, OG&E, Oncor"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            parent_company = st.text_input(
                "Parent Company",
                placeholder="e.g., AEP, Sempra"
            )
        with col2:
            iso = st.selectbox(
                "ISO/RTO",
                options=['SPP', 'ERCOT', 'MISO', 'PJM', 'CAISO', 'NYISO', 'ISO-NE', 'WECC', 'SERC']
            )
        
        service_territory = st.text_input(
            "Service Territory",
            placeholder="e.g., Eastern Oklahoma, Dallas-Fort Worth"
        )
        
        submitted = st.form_submit_button("🚀 Research Utility", type="primary")
        
        if submitted:
            if not utility_name:
                st.error("Utility name is required")
            else:
                with st.spinner(f"Researching {utility_name}..."):
                    intel, error = research_utility(
                        utility_name=utility_name,
                        parent_company=parent_company,
                        service_territory=service_territory,
                        iso=iso,
                    )
                    
                    if error:
                        st.error(f"Research failed: {error}")
                    else:
                        # Save to session state
                        utility_id = utility_name.lower().replace(' ', '_').replace('/', '_')
                        intel['last_updated'] = datetime.now().isoformat()
                        st.session_state.utility_intel_db[utility_id] = intel
                        st.session_state.selected_utility = utility_id
                        st.session_state.show_utility_form = False
                        st.success(f"Research complete for {utility_name}")
                        st.rerun()
    
    if st.button("Cancel"):
        st.session_state.show_utility_form = False
        st.rerun()


def _show_utility_detail(utility_id: str, intel: Dict):
    """Show detailed utility intelligence."""
    
    utility_name = intel.get('utility_name', utility_id)
    
    st.markdown(f"### {utility_name}")
    st.caption(f"Parent: {intel.get('parent_company', 'Unknown')} | ISO: {intel.get('iso', 'Unknown')}")
    
    # Appetite rating
    appetite = intel.get('appetite_rating', 'unknown')
    appetite_colors = {'aggressive': 'green', 'moderate': 'orange', 'defensive': 'red'}
    st.markdown(f"**Appetite:** :{appetite_colors.get(appetite, 'gray')}[{appetite.upper()}]")
    
    if intel.get('appetite_explanation'):
        st.info(intel['appetite_explanation'])
    
    st.divider()
    
    # Capacity position
    st.markdown("#### 📊 Capacity Position")
    cap = intel.get('capacity_position', {})
    if isinstance(cap, dict):
        col1, col2 = st.columns(2)
        with col1:
            deficit = cap.get('current_deficit_surplus_mw', 'Unknown')
            st.metric("Current Position (MW)", deficit)
        with col2:
            year = cap.get('deficit_year', 'Unknown')
            st.metric("By Year", year)
        
        if cap.get('notes'):
            st.markdown(f"*{cap['notes']}*")
    else:
        st.markdown(f"{cap}")
    
    st.divider()
    
    # Timeline intel
    st.markdown("#### ⏱️ Interconnection Timeline")
    timeline = intel.get('timeline_intel', {})
    if isinstance(timeline, dict):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Screening", f"{timeline.get('typical_screening_months', '?')} mo")
        with col2:
            st.metric("Impact Study", f"{timeline.get('typical_impact_study_months', '?')} mo")
        with col3:
            st.metric("Facilities", f"{timeline.get('typical_facilities_study_months', '?')} mo")
        with col4:
            st.metric("IA Negotiation", f"{timeline.get('typical_ia_negotiation_months', '?')} mo")
        
        total = timeline.get('realistic_total_months')
        if total:
            st.markdown(f"**Realistic Total:** {total} months")
        
        expedited = timeline.get('expedited_pathways', [])
        if expedited:
            st.markdown("**Expedited Pathways:**")
            for path in expedited:
                st.markdown(f"- {path}")
    
    st.divider()
    
    # Queue status
    st.markdown("#### 📋 Queue Status")
    queue = intel.get('queue_status', {})
    if isinstance(queue, dict):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Backlog (MW)", queue.get('backlog_mw', 'Unknown'))
        with col2:
            st.metric("Projects", queue.get('backlog_projects', 'Unknown'))
        with col3:
            st.metric("Avg Wait", f"{queue.get('average_wait_months', '?')} mo")
        
        if queue.get('notes'):
            st.markdown(f"*{queue['notes']}*")
    
    st.divider()
    
    # Recent activity
    st.markdown("#### 📰 Recent Activity")
    activities = intel.get('recent_activity', [])
    if activities:
        for activity in activities:
            if isinstance(activity, dict):
                st.markdown(f"- **{activity.get('date', '')}** [{activity.get('type', '')}]: {activity.get('summary', '')}")
            else:
                st.markdown(f"- {activity}")
    else:
        st.markdown("*No recent activity recorded*")
    
    st.divider()
    
    # Validated overrides (proprietary intel)
    st.markdown("#### 🔐 Validated Overrides")
    st.markdown("*Proprietary intelligence that supersedes public research*")
    
    overrides = intel.get('validated_overrides', [])
    
    # Add new override
    with st.expander("➕ Add Override"):
        with st.form("add_override_form"):
            field = st.selectbox(
                "Field to Override",
                options=['energization_timeline', 'capacity_position', 'appetite', 'queue_status', 'other']
            )
            public_value = st.text_input("Public/Research Value")
            validated_value = st.text_input("Validated Value (from proprietary intel)")
            confidence = st.select_slider("Confidence", options=['Low', 'Medium', 'High'])
            source = st.text_input("Source", placeholder="e.g., Direct conversation 2025-11-15")
            
            if st.form_submit_button("Save Override"):
                new_override = {
                    'field': field,
                    'public_value': public_value,
                    'validated_value': validated_value,
                    'confidence': confidence,
                    'source': source,
                    'date_added': datetime.now().isoformat(),
                }
                if 'validated_overrides' not in intel:
                    intel['validated_overrides'] = []
                intel['validated_overrides'].append(new_override)
                st.session_state.utility_intel_db[utility_id] = intel
                st.success("Override saved")
                st.rerun()
    
    # Show existing overrides
    for i, override in enumerate(overrides):
        st.markdown(f"""
        **{override.get('field', 'Unknown')}**
        - Public: {override.get('public_value', 'N/A')}
        - **Validated: {override.get('validated_value', 'N/A')}**
        - Confidence: {override.get('confidence', 'Unknown')}
        - Source: {override.get('source', 'Unknown')}
        """)
    
    st.divider()
    
    # Actions
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Refresh Research", use_container_width=True):
            with st.spinner("Re-researching..."):
                new_intel, error = research_utility(
                    utility_name=utility_name,
                    parent_company=intel.get('parent_company'),
                    service_territory=intel.get('service_territory', utility_name),
                    iso=intel.get('iso'),
                )
                if not error:
                    # Preserve validated overrides
                    new_intel['validated_overrides'] = intel.get('validated_overrides', [])
                    new_intel['last_updated'] = datetime.now().isoformat()
                    st.session_state.utility_intel_db[utility_id] = new_intel
                    st.success("Research refreshed")
                    st.rerun()
    
    with col2:
        if st.button("📋 Export JSON", use_container_width=True):
            st.download_button(
                label="Download",
                data=json.dumps(intel, indent=2),
                file_name=f"utility_intel_{utility_id}.json",
                mime="application/json",
            )
    
    with col3:
        st.caption(f"Updated: {intel.get('last_updated', 'Unknown')}")


def _load_utility_intel() -> Dict:
    """Load utility intelligence from storage or return defaults."""
    # In production, this would load from Google Sheets Utility_Intelligence tab
    # For now, return example data
    return {
        'pso': {
            'utility_name': 'PSO',
            'parent_company': 'AEP',
            'iso': 'SPP',
            'appetite_rating': 'aggressive',
            'appetite_explanation': 'AEP subsidiary actively seeking large load growth. Has announced capacity expansion plans.',
            'capacity_position': {
                'current_deficit_surplus_mw': -200,
                'deficit_year': '2028',
                'trend': 'growing_deficit',
                'notes': 'Eastern Oklahoma load growth exceeding projections'
            },
            'timeline_intel': {
                'typical_screening_months': 3,
                'typical_impact_study_months': 9,
                'typical_facilities_study_months': 6,
                'typical_ia_negotiation_months': 3,
                'realistic_total_months': 24,
                'expedited_pathways': ['Surplus Interconnection Service', 'Behind-the-meter generation']
            },
            'queue_status': {
                'backlog_mw': 1500,
                'backlog_projects': 45,
                'average_wait_months': 18,
                'notes': 'Queue moving but significant backlog'
            },
            'recent_activity': [
                {'date': '2025-09', 'type': 'IRP', 'summary': 'Filed 2025 IRP showing 500MW deficit by 2030'},
                {'date': '2025-07', 'type': 'announcement', 'summary': 'Announced interest in data center load'}
            ],
            'validated_overrides': [
                {
                    'field': 'energization_timeline',
                    'public_value': '2028-2029 (from IRP)',
                    'validated_value': '2031+',
                    'confidence': 'High',
                    'source': 'Direct conversation with PSO planning team, 2025-11-15',
                    'date_added': '2025-11-15',
                }
            ],
            'last_updated': '2025-12-01T12:00:00',
        },
        'oge': {
            'utility_name': 'OG&E',
            'parent_company': 'OGE Energy',
            'iso': 'SPP',
            'appetite_rating': 'moderate',
            'appetite_explanation': 'Focused on reliability and transmission. Open to large loads but not aggressively pursuing.',
            'capacity_position': {
                'current_deficit_surplus_mw': 100,
                'deficit_year': '2030',
                'trend': 'stable',
            },
            'timeline_intel': {
                'realistic_total_months': 30,
            },
            'last_updated': '2025-11-15T12:00:00',
        },
    }


# =============================================================================
# MARKET SNAPSHOTS TAB
# =============================================================================

def show_market_snapshots_tab():
    """Market snapshots management."""
    
    st.subheader("🗺️ Market Snapshots")
    st.markdown("Regional market intelligence for competitive positioning.")
    
    # Initialize session state
    if 'market_snapshots' not in st.session_state:
        st.session_state.market_snapshots = {}
    
    # Generate new snapshot
    st.markdown("### Generate Market Snapshot")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        state = st.selectbox(
            "State",
            options=['OK', 'TX', 'KS', 'AR', 'MO', 'LA', 'NM'],
        )
    with col2:
        iso = st.selectbox(
            "ISO",
            options=['SPP', 'ERCOT', 'MISO', 'PJM'],
        )
    with col3:
        utility = st.text_input(
            "Utility (optional)",
            placeholder="e.g., PSO"
        )
    
    if st.button("🚀 Generate Snapshot", type="primary"):
        with st.spinner(f"Generating market snapshot for {state} - {iso}..."):
            snapshot, error = get_market_snapshot(state, iso, utility or None)
            
            if error:
                st.error(f"Snapshot generation failed: {error}")
            else:
                snapshot_id = f"{state}_{iso}_{datetime.now().strftime('%Y%m%d')}"
                snapshot['generated_date'] = datetime.now().isoformat()
                st.session_state.market_snapshots[snapshot_id] = snapshot
                st.success("Snapshot generated!")
    
    st.divider()
    
    # Display existing snapshots
    st.markdown("### Saved Snapshots")
    
    for snapshot_id, snapshot in st.session_state.market_snapshots.items():
        with st.expander(f"📊 {snapshot_id}", expanded=False):
            _display_market_snapshot(snapshot)


def _display_market_snapshot(snapshot: Dict):
    """Display a market snapshot."""
    
    st.markdown(f"**Region:** {snapshot.get('region', 'Unknown')}")
    st.caption(f"Generated: {snapshot.get('generated_date', snapshot.get('snapshot_date', 'Unknown'))}")
    
    # Active projects
    projects = snapshot.get('active_projects', [])
    if projects:
        st.markdown("#### Active Projects")
        for proj in projects:
            if isinstance(proj, dict):
                status_icon = {'announced': '📢', 'construction': '🏗️', 'operational': '✅'}.get(proj.get('status', ''), '•')
                st.markdown(f"- {status_icon} **{proj.get('name', 'Unknown')}** - {proj.get('developer', 'Unknown')} - {proj.get('capacity_mw', '?')} MW ({proj.get('status', 'unknown')})")
    
    # Developer activity
    dev = snapshot.get('developer_activity', {})
    if dev:
        st.markdown("#### Developer Activity")
        if dev.get('hyperscalers_active'):
            st.markdown(f"**Hyperscalers:** {', '.join(dev['hyperscalers_active'])}")
        if dev.get('developers_active'):
            st.markdown(f"**Developers:** {', '.join(dev['developers_active'])}")
    
    # Market metrics
    metrics = snapshot.get('market_metrics', {})
    if metrics:
        st.markdown("#### Market Metrics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Inventory (MW)", metrics.get('estimated_inventory_mw', 'Unknown'))
        with col2:
            st.metric("Pipeline (MW)", metrics.get('estimated_pipeline_mw', 'Unknown'))
        with col3:
            st.metric("Demand Outlook", metrics.get('demand_outlook', 'Unknown').title())
    
    # Competitive insights
    insights = snapshot.get('competitive_insights', {})
    if insights:
        st.markdown("#### Competitive Insights")
        if insights.get('key_differentiators'):
            st.markdown(f"**Key Differentiators:** {', '.join(insights['key_differentiators'])}")
        if insights.get('common_challenges'):
            st.markdown(f"**Common Challenges:** {', '.join(insights['common_challenges'])}")
        st.markdown(f"**Market Saturation:** {insights.get('market_saturation', 'Unknown').title()}")
    
    # Overall assessment
    if snapshot.get('overall_assessment'):
        st.info(f"**Assessment:** {snapshot['overall_assessment']}")


# =============================================================================
# INDUSTRY INTEL TAB
# =============================================================================

def show_industry_intel_tab():
    """Industry-wide intelligence."""
    
    st.subheader("🏭 Industry Intelligence")
    st.markdown("Supply chain, lead times, and industry benchmarks.")
    
    # Hardcoded industry intel (would be stored in Google Sheets in production)
    industry_data = {
        'supply_chain': {
            'transformers': {
                'lead_time_months': '24-36',
                'trend': 'increasing',
                'notes': 'Global shortage continues. Order 24+ months ahead.',
            },
            'switchgear': {
                'lead_time_months': '18-24',
                'trend': 'stable',
                'notes': 'Medium voltage more available than high voltage.',
            },
            'generators': {
                'lead_time_months': '12-18',
                'trend': 'stable',
                'notes': 'Natural gas gensets more available than diesel.',
            },
        },
        'permitting_benchmarks': {
            'conditional_use_permit': '3-6 months',
            'building_permit': '2-4 months',
            'environmental_review': '6-18 months',
            'water_permit': '3-12 months',
        },
        'cost_benchmarks': {
            'land_per_acre': '$50,000 - $500,000',
            'site_development_per_mw': '$500,000 - $1,500,000',
            'substation_per_mw': '$100,000 - $300,000',
            'transmission_per_mile': '$1,000,000 - $3,000,000',
        },
    }
    
    # Display supply chain
    st.markdown("### 📦 Supply Chain Lead Times")
    for item, data in industry_data['supply_chain'].items():
        trend_icon = {'increasing': '📈', 'decreasing': '📉', 'stable': '➡️'}.get(data['trend'], '•')
        st.markdown(f"**{item.title()}:** {data['lead_time_months']} months {trend_icon}")
        st.caption(data['notes'])
    
    st.divider()
    
    # Display permitting benchmarks
    st.markdown("### 📋 Permitting Benchmarks")
    for permit, timeline in industry_data['permitting_benchmarks'].items():
        st.markdown(f"- **{permit.replace('_', ' ').title()}:** {timeline}")
    
    st.divider()
    
    # Display cost benchmarks
    st.markdown("### 💰 Cost Benchmarks")
    for item, cost in industry_data['cost_benchmarks'].items():
        st.markdown(f"- **{item.replace('_', ' ').title()}:** {cost}")
    
    st.divider()
    
    # Key industry insights
    st.markdown("### 💡 Key Insights")
    st.info("""
    **Supply-Demand Gap:** Persistent deficit extending through 2037, not 2033 as initially modeled.
    
    **CoWoS Bottleneck:** Packaging capacity, not wafer fabrication, is the primary bottleneck for AI chip production through 2027.
    
    **Utility Timelines:** Power delivery timelines have slipped 3+ years across major markets. What was 2028 is now 2031+.
    """)


# =============================================================================
# COVERAGE DASHBOARD TAB
# =============================================================================

def show_coverage_dashboard_tab():
    """Intelligence coverage dashboard."""
    
    st.subheader("📊 Intelligence Coverage")
    st.markdown("Track research coverage across your portfolio and target markets.")
    
    # Coverage metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Utilities Researched",
            len(st.session_state.get('utility_intel_db', {})),
            help="Number of utilities with intelligence profiles"
        )
    
    with col2:
        st.metric(
            "Market Snapshots",
            len(st.session_state.get('market_snapshots', {})),
            help="Number of market snapshots generated"
        )
    
    with col3:
        # Would calculate from actual site data
        st.metric(
            "Sites Diagnosed",
            "8/12",
            help="Sites with full diagnosis vs total sites"
        )
    
    with col4:
        st.metric(
            "Validated Overrides",
            sum(len(u.get('validated_overrides', [])) for u in st.session_state.get('utility_intel_db', {}).values()),
            help="Proprietary intel overriding public research"
        )
    
    st.divider()
    
    # Coverage gaps
    st.markdown("### ⚠️ Coverage Gaps")
    
    # Would calculate from actual data
    gaps = [
        "Rogers County, OK - No diagnosis, high-value prospect",
        "West Texas market - No market snapshot",
        "Oncor utility - Intel is 60+ days old",
    ]
    
    for gap in gaps:
        st.warning(f"• {gap}")
    
    st.divider()
    
    # Research queue
    st.markdown("### 📋 Research Queue")
    st.markdown("*Suggested research tasks based on portfolio needs*")
    
    tasks = [
        ("🔴 High", "Research Entergy Arkansas utility position"),
        ("🟡 Medium", "Update PSO intel (30+ days old)"),
        ("🟡 Medium", "Generate SPP market snapshot"),
        ("🟢 Low", "Research Empire/Liberty utility"),
    ]
    
    for priority, task in tasks:
        st.checkbox(f"{priority}: {task}")
