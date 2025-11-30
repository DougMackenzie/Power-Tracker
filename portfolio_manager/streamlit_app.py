"""
Powered Land Portfolio Manager
==============================
Streamlit application for managing and evaluating data center development sites.

Features:
- Master site database with full diagnostic data
- State-level context integration
- Utility research via web search
- Site ranking with custom weighting
- Critical path visualization
- Report generation
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import date, datetime
from typing import Dict, List, Optional
import plotly.express as px
import plotly.graph_objects as go

# Import our modules
from .state_analysis import (
    STATE_PROFILES, get_state_profile, calculate_state_score,
    generate_state_context_section, rank_all_states, compare_states,
    generate_utility_research_queries, get_iso_research_queries
)

# =============================================================================
# DATABASE MANAGEMENT
# =============================================================================

DATABASE_FILE = os.path.join(os.path.dirname(__file__), "site_database.json")

def load_database() -> Dict:
    """Load site database from JSON file."""
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r') as f:
            return json.load(f)
    return {
        'sites': {},
        'metadata': {
            'created': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'version': '1.0'
        }
    }

def save_database(db: Dict):
    """Save site database to JSON file."""
    db['metadata']['last_updated'] = datetime.now().isoformat()
    with open(DATABASE_FILE, 'w') as f:
        json.dump(db, f, indent=2, default=str)

def add_site(db: Dict, site_id: str, site_data: Dict):
    """Add or update a site in the database."""
    site_data['last_updated'] = datetime.now().isoformat()
    db['sites'][site_id] = site_data
    save_database(db)

def delete_site(db: Dict, site_id: str):
    """Delete a site from the database."""
    if site_id in db['sites']:
        del db['sites'][site_id]
        save_database(db)

# =============================================================================
# SCORING ENGINE
# =============================================================================

def calculate_site_score(site: Dict, weights: Dict) -> Dict:
    """Calculate comprehensive site score with custom weights."""
    
    state_profile = get_state_profile(site.get('state', ''))
    state_score = state_profile.overall_score if state_profile else 50
    
    power_score = calculate_power_pathway_score(site)
    relationship_score = calculate_relationship_score(site)
    execution_score = calculate_execution_score(site)
    fundamentals_score = calculate_fundamentals_score(site)
    financial_score = calculate_financial_score(site)
    
    weighted_score = (
        state_score * weights.get('state', 0.20) +
        power_score * weights.get('power', 0.25) +
        relationship_score * weights.get('relationship', 0.20) +
        execution_score * weights.get('execution', 0.15) +
        fundamentals_score * weights.get('fundamentals', 0.10) +
        financial_score * weights.get('financial', 0.10)
    )
    
    return {
        'overall_score': round(weighted_score, 1),
        'state_score': state_score,
        'power_score': round(power_score, 1),
        'relationship_score': round(relationship_score, 1),
        'execution_score': round(execution_score, 1),
        'fundamentals_score': round(fundamentals_score, 1),
        'financial_score': round(financial_score, 1),
        'weights': weights
    }

def calculate_power_pathway_score(site: Dict) -> float:
    """Calculate power pathway score (0-100)."""
    score = 0
    
    study_status = site.get('study_status', 'not_started')
    study_scores = {
        'ia_executed': 40, 'fa_executed': 35, 'fs_complete': 28,
        'sis_complete': 20, 'sis_in_progress': 12, 'sis_requested': 8, 'not_started': 0
    }
    score += study_scores.get(study_status, 0)
    
    utility_commitment = site.get('utility_commitment', 'none')
    commitment_scores = {'committed': 25, 'verbal': 18, 'engaged': 12, 'initial': 5, 'none': 0}
    score += commitment_scores.get(utility_commitment, 0)
    
    power_timeline_months = site.get('power_timeline_months', 60)
    if power_timeline_months <= 24: score += 20
    elif power_timeline_months <= 36: score += 15
    elif power_timeline_months <= 48: score += 10
    elif power_timeline_months <= 60: score += 5
    
    if site.get('transmission_adjacent', False): score += 5
    if site.get('substation_nearby', False): score += 5
    if site.get('btm_viable', False): score += 5
    
    return min(score, 100)

def calculate_relationship_score(site: Dict) -> float:
    """Calculate relationship capital score (0-100)."""
    score = 0
    
    end_user_status = site.get('end_user_status', 'none')
    end_user_scores = {
        'term_sheet': 60, 'loi': 50, 'nda_active': 35, 'nda_signed': 25,
        'tours_completed': 15, 'interest_expressed': 8, 'none': 0
    }
    score += end_user_scores.get(end_user_status, 0)
    
    community = site.get('community_support', 'neutral')
    community_scores = {'champion': 25, 'supportive': 20, 'neutral': 12, 'concerns': 5, 'opposition': 0}
    score += community_scores.get(community, 12)
    
    political = site.get('political_support', 'neutral')
    political_scores = {'strong': 15, 'supportive': 12, 'neutral': 8, 'concerns': 3, 'opposition': 0}
    score += political_scores.get(political, 8)
    
    return min(score, 100)

def calculate_execution_score(site: Dict) -> float:
    """Calculate execution capability score (0-100)."""
    score = 0
    
    track_record = site.get('developer_track_record', 'none')
    track_scores = {'extensive': 40, 'proven': 32, 'limited': 18, 'none': 5}
    score += track_scores.get(track_record, 5)
    
    utility_rel = site.get('utility_relationships', 'none')
    utility_scores = {'strong': 30, 'established': 22, 'developing': 12, 'none': 0}
    score += utility_scores.get(utility_rel, 0)
    
    btm = site.get('btm_capability', 'none')
    btm_scores = {'multiple_sources': 30, 'viable': 22, 'potential': 12, 'none': 0}
    score += btm_scores.get(btm, 0)
    
    return min(score, 100)

def calculate_fundamentals_score(site: Dict) -> float:
    """Calculate site fundamentals score (0-100)."""
    score = 0
    
    land_control = site.get('land_control', 'none')
    land_scores = {'owned': 35, 'option': 28, 'loi': 18, 'negotiating': 8, 'none': 0}
    score += land_scores.get(land_control, 0)
    
    target_mw = site.get('target_mw', 0)
    acreage = site.get('acreage', 0)
    if acreage > 0 and target_mw > 0:
        mw_per_acre = target_mw / acreage
        if mw_per_acre <= 3: score += 20
        elif mw_per_acre <= 5: score += 15
        elif mw_per_acre <= 8: score += 10
        else: score += 5
    
    water_status = site.get('water_status', 'unknown')
    water_scores = {'secured': 25, 'available': 18, 'identified': 10, 'constrained': 3, 'unknown': 5}
    score += water_scores.get(water_status, 5)
    
    fiber_status = site.get('fiber_status', 'unknown')
    fiber_scores = {'lit': 20, 'adjacent': 15, 'nearby': 10, 'distant': 5, 'unknown': 5}
    score += fiber_scores.get(fiber_status, 5)
    
    return min(score, 100)

def calculate_financial_score(site: Dict) -> float:
    """Calculate financial capability score (0-100)."""
    score = 0
    
    capital = site.get('capital_access', 'limited')
    capital_scores = {'strong': 50, 'committed': 42, 'available': 30, 'developing': 18, 'limited': 5}
    score += capital_scores.get(capital, 5)
    
    if site.get('development_budget_allocated', False): score += 25
    
    partnership = site.get('partnership_structure', 'none')
    partnership_scores = {'jv_active': 25, 'jv_negotiating': 18, 'lp_identified': 12, 'seeking': 5, 'none': 0}
    score += partnership_scores.get(partnership, 0)
    
    return min(score, 100)

def determine_stage(site: Dict) -> str:
    """Determine development stage based on site attributes."""
    
    if site.get('end_user_status') in ['term_sheet', 'loi']:
        return 'End-User Attached'
    
    if (site.get('study_status') in ['ia_executed', 'fa_executed'] and
        site.get('zoning_approved', False) and
        site.get('land_control') in ['owned', 'option']):
        return 'Fully Entitled'
    
    if site.get('utility_commitment') == 'committed':
        return 'Utility Commitment'
    
    if site.get('study_status') in ['sis_in_progress', 'sis_complete', 'fs_complete']:
        return 'Study In Progress'
    
    if (site.get('land_control') in ['owned', 'option', 'loi'] and
        site.get('study_status') in ['sis_requested', 'not_started'] and
        site.get('utility_commitment') != 'none'):
        return 'Early Real'
    
    if site.get('queue_position', False):
        return 'Queue Only'
    
    return 'Pre-Development'

# =============================================================================
# STREAMLIT APP
# =============================================================================

def run():
    # st.set_page_config() is handled by the main app
    
    if 'db' not in st.session_state:
        st.session_state.db = load_database()
    
    if 'weights' not in st.session_state:
        st.session_state.weights = {
            'state': 0.20, 'power': 0.25, 'relationship': 0.20,
            'execution': 0.15, 'fundamentals': 0.10, 'financial': 0.10
        }
    
    st.sidebar.title("⚡ Portfolio Manager")
    
    page = st.sidebar.radio(
        "Navigation",
        ["📊 Dashboard", "🏭 Site Database", "➕ Add/Edit Site", 
         "🏆 Rankings", "🗺️ State Analysis", "🔍 Utility Research", "⚙️ Settings"]
    )
    
    if page == "📊 Dashboard": show_dashboard()
    elif page == "🏭 Site Database": show_site_database()
    elif page == "➕ Add/Edit Site": show_add_edit_site()
    elif page == "🏆 Rankings": show_rankings()
    elif page == "🗺️ State Analysis": show_state_analysis()
    elif page == "🔍 Utility Research": show_utility_research()
    elif page == "⚙️ Settings": show_settings()


def show_dashboard():
    """Main dashboard with portfolio overview."""
    st.title("📊 Portfolio Dashboard")
    
    db = st.session_state.db
    sites = db.get('sites', {})
    
    if not sites:
        st.info("No sites in database. Add sites to see portfolio overview.")
        return
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_sites = len(sites)
    total_mw = sum(s.get('target_mw', 0) for s in sites.values())
    avg_score = sum(calculate_site_score(s, st.session_state.weights)['overall_score'] for s in sites.values()) / total_sites
    stages = [determine_stage(s) for s in sites.values()]
    
    col1.metric("Total Sites", total_sites)
    col2.metric("Total Pipeline MW", f"{total_mw:,.0f}")
    col3.metric("Avg Score", f"{avg_score:.1f}")
    col4.metric("Entitled+", sum(1 for s in stages if s in ['Fully Entitled', 'End-User Attached']))
    col5.metric("Active Studies", sum(1 for s in stages if s == 'Study In Progress'))
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Pipeline by Stage")
        stage_counts = pd.Series(stages).value_counts()
        fig = px.pie(values=stage_counts.values, names=stage_counts.index, color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("MW by State")
        state_mw = {}
        for s in sites.values():
            state = s.get('state', 'Unknown')
            state_mw[state] = state_mw.get(state, 0) + s.get('target_mw', 0)
        fig = px.bar(x=list(state_mw.keys()), y=list(state_mw.values()), labels={'x': 'State', 'y': 'MW'})
        st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Top Sites by Score")
    
    site_data = []
    for site_id, site in sites.items():
        scores = calculate_site_score(site, st.session_state.weights)
        stage = determine_stage(site)
        site_data.append({
            'Site': site.get('name', site_id), 'State': site.get('state', ''),
            'MW': site.get('target_mw', 0), 'Stage': stage,
            'Score': scores['overall_score'], 'Power': scores['power_score'],
            'Relationship': scores['relationship_score'], 'Utility': site.get('utility', '')
        })
    
    df = pd.DataFrame(site_data).sort_values('Score', ascending=False)
    
    st.dataframe(df, column_config={
        'Score': st.column_config.ProgressColumn(min_value=0, max_value=100),
        'Power': st.column_config.ProgressColumn(min_value=0, max_value=100),
        'Relationship': st.column_config.ProgressColumn(min_value=0, max_value=100),
        'MW': st.column_config.NumberColumn(format="%d MW")
    }, hide_index=True, use_container_width=True)


def show_site_database():
    """View and manage site database."""
    st.title("🏭 Site Database")
    
    db = st.session_state.db
    sites = db.get('sites', {})
    
    if not sites:
        st.info("No sites in database. Use 'Add/Edit Site' to create entries.")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        state_filter = st.multiselect("Filter by State", options=list(set(s.get('state', '') for s in sites.values())))
    with col2:
        stage_filter = st.multiselect("Filter by Stage", options=['Pre-Development', 'Queue Only', 'Early Real', 'Study In Progress', 'Utility Commitment', 'Fully Entitled', 'End-User Attached'])
    with col3:
        min_score = st.slider("Minimum Score", 0, 100, 0)
    
    filtered_sites = []
    for site_id, site in sites.items():
        scores = calculate_site_score(site, st.session_state.weights)
        stage = determine_stage(site)
        
        if state_filter and site.get('state', '') not in state_filter: continue
        if stage_filter and stage not in stage_filter: continue
        if scores['overall_score'] < min_score: continue
        
        filtered_sites.append({
            'id': site_id, 'Site Name': site.get('name', site_id), 'State': site.get('state', ''),
            'Utility': site.get('utility', ''), 'Target MW': site.get('target_mw', 0),
            'Stage': stage, 'Score': scores['overall_score'], 'State Score': scores['state_score'],
            'Power Score': scores['power_score'], 'Relationship': scores['relationship_score'],
            'Last Updated': site.get('last_updated', '')[:10] if site.get('last_updated') else ''
        })
    
    if filtered_sites:
        df = pd.DataFrame(filtered_sites)
        st.dataframe(df.drop(columns=['id']), column_config={
            'Score': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            'State Score': st.column_config.ProgressColumn(min_value=0, max_value=100),
            'Power Score': st.column_config.ProgressColumn(min_value=0, max_value=100),
            'Relationship': st.column_config.ProgressColumn(min_value=0, max_value=100),
            'Target MW': st.column_config.NumberColumn(format="%d")
        }, hide_index=True, use_container_width=True)
        
        st.markdown("---")
        selected_site = st.selectbox("Select site for details", options=[s['id'] for s in filtered_sites], format_func=lambda x: sites[x].get('name', x))
        
        if selected_site:
            show_site_details(selected_site)
    else:
        st.warning("No sites match the selected filters.")


def show_site_details(site_id: str):
    """Show detailed view of a single site."""
    site = st.session_state.db['sites'].get(site_id, {})
    scores = calculate_site_score(site, st.session_state.weights)
    stage = determine_stage(site)
    state_context = generate_state_context_section(site.get('state', ''))
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📍 {site.get('name', site_id)}")
        st.write(f"**State:** {site.get('state', 'N/A')} | **Utility:** {site.get('utility', 'N/A')}")
        st.write(f"**Target Capacity:** {site.get('target_mw', 0):,} MW | **Acreage:** {site.get('acreage', 0):,} acres")
        st.write(f"**Stage:** {stage}")
    
    with col2:
        st.metric("Overall Score", f"{scores['overall_score']:.1f}/100")
    
    st.markdown("#### Score Breakdown")
    score_df = pd.DataFrame({
        'Component': ['State', 'Power Pathway', 'Relationship', 'Execution', 'Fundamentals', 'Financial'],
        'Score': [scores['state_score'], scores['power_score'], scores['relationship_score'],
                 scores['execution_score'], scores['fundamentals_score'], scores['financial_score']],
        'Weight': [20, 25, 20, 15, 10, 10]
    })
    
    fig = px.bar(score_df, x='Component', y='Score', color='Score', color_continuous_scale='RdYlGn', range_color=[0, 100])
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)
    
    if 'error' not in state_context:
        with st.expander("🗺️ State Context", expanded=False):
            col1, col2, col3 = st.columns(3)
            col1.write(f"**Tier:** {state_context['summary']['tier_label']}")
            col2.write(f"**ISO:** {state_context['summary']['primary_iso']}")
            col3.write(f"**Regulatory:** {state_context['summary']['regulatory_structure']}")
            
            st.write("**Strengths:**")
            for s in state_context['swot']['strengths'][:3]: st.write(f"  ✅ {s}")
            
            st.write("**Risks:**")
            for w in state_context['swot']['weaknesses'][:3]: st.write(f"  ⚠️ {w}")
    
    with st.expander("⚡ Power Pathway Details", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Study Status:** {site.get('study_status', 'N/A').replace('_', ' ').title()}")
            st.write(f"**Utility Commitment:** {site.get('utility_commitment', 'N/A').replace('_', ' ').title()}")
            st.write(f"**Timeline to Power:** {site.get('power_timeline_months', 'N/A')} months")
        with col2:
            st.write(f"**Queue Position:** {'Yes' if site.get('queue_position') else 'No'}")
            st.write(f"**BTM Viable:** {'Yes' if site.get('btm_viable') else 'No'}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✏️ Edit Site"):
            st.session_state.edit_site_id = site_id
            st.rerun()
    with col2:
        report_md = generate_site_report_markdown(site, scores, stage, state_context)
        st.download_button(
            label="📄 Download Report",
            data=report_md,
            file_name=f"{site.get('name', 'site').replace(' ', '_')}_Report.md",
            mime="text/markdown"
        )

def generate_site_report_markdown(site: Dict, scores: Dict, stage: str, state_context: Dict) -> str:
    """Generate a Markdown report for a site."""
    return f"""# Site Investment Memo: {site.get('name', 'Unnamed Site')}
**Date:** {datetime.now().strftime('%Y-%m-%d')}
**Stage:** {stage}
**Overall Score:** {scores['overall_score']}/100

## Executive Summary
**State:** {site.get('state', 'N/A')} ({state_context['summary']['tier_label']})
**Utility:** {site.get('utility', 'N/A')}
**Target Capacity:** {site.get('target_mw', 0)} MW
**Acreage:** {site.get('acreage', 0)} acres

## Score Breakdown
| Component | Score | Weight |
|-----------|-------|--------|
| **Overall** | **{scores['overall_score']}** | **100%** |
| State | {scores['state_score']} | {scores['weights']['state']*100:.0f}% |
| Power Pathway | {scores['power_score']} | {scores['weights']['power']*100:.0f}% |
| Relationship | {scores['relationship_score']} | {scores['weights']['relationship']*100:.0f}% |
| Execution | {scores['execution_score']} | {scores['weights']['execution']*100:.0f}% |
| Fundamentals | {scores['fundamentals_score']} | {scores['weights']['fundamentals']*100:.0f}% |
| Financial | {scores['financial_score']} | {scores['weights']['financial']*100:.0f}% |

## State Context: {site.get('state', 'N/A')}
**ISO:** {state_context['summary']['primary_iso']}
**Regulatory Environment:** {state_context['summary']['regulatory_structure']}

**Strengths:**
{chr(10).join([f"- {s}" for s in state_context['swot']['strengths']])}

**Risks:**
{chr(10).join([f"- {w}" for w in state_context['swot']['weaknesses']])}

## Critical Path Analysis
### Power Pathway
- **Study Status:** {site.get('study_status', 'N/A').replace('_', ' ').title()}
- **Utility Commitment:** {site.get('utility_commitment', 'N/A').replace('_', ' ').title()}
- **Timeline:** {site.get('power_timeline_months', 'N/A')} months
- **Queue Position:** {'Yes' if site.get('queue_position') else 'No'}

### Relationship Capital
- **End-User:** {site.get('end_user_status', 'N/A').replace('_', ' ').title()}
- **Community:** {site.get('community_support', 'N/A').title()}
- **Political:** {site.get('political_support', 'N/A').title()}

### Execution & Fundamentals
- **Land Control:** {site.get('land_control', 'N/A').title()}
- **Water Status:** {site.get('water_status', 'N/A').title()}
- **Fiber Status:** {site.get('fiber_status', 'N/A').title()}
- **Developer Track Record:** {site.get('developer_track_record', 'N/A').title()}

## Notes
{site.get('notes', 'No notes added.')}
"""
    with col3:
        if st.button("🗑️ Delete Site", type="secondary"):
            delete_site(st.session_state.db, site_id)
            st.success("Site deleted")
            st.rerun()


def show_add_edit_site():
    """Form for adding or editing sites."""
    st.title("➕ Add/Edit Site")
    
    editing = hasattr(st.session_state, 'edit_site_id') and st.session_state.edit_site_id
    site = st.session_state.db['sites'].get(st.session_state.edit_site_id, {}) if editing else {}
    
    if editing:
        st.info(f"Editing: {site.get('name', st.session_state.edit_site_id)}")
        if st.button("Cancel Edit"):
            del st.session_state.edit_site_id
            st.rerun()
    
    with st.form("site_form"):
        st.subheader("Basic Information")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            name = st.text_input("Site Name*", value=site.get('name', ''))
            state = st.selectbox("State*", options=[''] + list(STATE_PROFILES.keys()),
                index=([''] + list(STATE_PROFILES.keys())).index(site.get('state', '')) if site.get('state', '') in STATE_PROFILES else 0)
            utility = st.text_input("Utility Name*", value=site.get('utility', ''))
        with col2:
            target_mw = st.number_input("Target MW*", min_value=0, value=site.get('target_mw', 0))
            acreage = st.number_input("Acreage", min_value=0, value=site.get('acreage', 0))
            iso = st.selectbox("ISO/RTO", options=['', 'SPP', 'ERCOT', 'PJM', 'MISO', 'CAISO', 'WECC', 'SERC'],
                index=['', 'SPP', 'ERCOT', 'PJM', 'MISO', 'CAISO', 'WECC', 'SERC'].index(site.get('iso', '')) if site.get('iso', '') else 0)
        with col3:
            county = st.text_input("County", value=site.get('county', ''))
            developer = st.text_input("Developer", value=site.get('developer', ''))
        
        st.markdown("---")
        st.subheader("Power Pathway")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            study_status = st.selectbox("Study Status",
                options=['not_started', 'sis_requested', 'sis_in_progress', 'sis_complete', 'fs_complete', 'fa_executed', 'ia_executed'],
                format_func=lambda x: x.replace('_', ' ').title(),
                index=['not_started', 'sis_requested', 'sis_in_progress', 'sis_complete', 'fs_complete', 'fa_executed', 'ia_executed'].index(site.get('study_status', 'not_started')))
            utility_commitment = st.selectbox("Utility Commitment",
                options=['none', 'initial', 'engaged', 'verbal', 'committed'], format_func=lambda x: x.title(),
                index=['none', 'initial', 'engaged', 'verbal', 'committed'].index(site.get('utility_commitment', 'none')))
        with col2:
            power_timeline_months = st.number_input("Timeline to Power (months)", min_value=0, max_value=120, value=site.get('power_timeline_months', 48))
            queue_position = st.checkbox("Has Queue Position", value=site.get('queue_position', False))
        with col3:
            btm_viable = st.checkbox("BTM Generation Viable", value=site.get('btm_viable', False))
            transmission_adjacent = st.checkbox("Adjacent to Transmission", value=site.get('transmission_adjacent', False))
            substation_nearby = st.checkbox("Substation Nearby", value=site.get('substation_nearby', False))
        
        st.markdown("---")
        st.subheader("Relationship Capital")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            end_user_status = st.selectbox("End-User Status",
                options=['none', 'interest_expressed', 'tours_completed', 'nda_signed', 'nda_active', 'loi', 'term_sheet'],
                format_func=lambda x: x.replace('_', ' ').title(),
                index=['none', 'interest_expressed', 'tours_completed', 'nda_signed', 'nda_active', 'loi', 'term_sheet'].index(site.get('end_user_status', 'none')))
        with col2:
            community_support = st.selectbox("Community Support",
                options=['opposition', 'concerns', 'neutral', 'supportive', 'champion'], format_func=lambda x: x.title(),
                index=['opposition', 'concerns', 'neutral', 'supportive', 'champion'].index(site.get('community_support', 'neutral')))
        with col3:
            political_support = st.selectbox("Political Support",
                options=['opposition', 'concerns', 'neutral', 'supportive', 'strong'], format_func=lambda x: x.title(),
                index=['opposition', 'concerns', 'neutral', 'supportive', 'strong'].index(site.get('political_support', 'neutral')))
        
        st.markdown("---")
        st.subheader("Site Fundamentals & Execution")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            land_control = st.selectbox("Land Control", options=['none', 'negotiating', 'loi', 'option', 'owned'], format_func=lambda x: x.title(),
                index=['none', 'negotiating', 'loi', 'option', 'owned'].index(site.get('land_control', 'none')))
            water_status = st.selectbox("Water Status", options=['unknown', 'constrained', 'identified', 'available', 'secured'], format_func=lambda x: x.title(),
                index=['unknown', 'constrained', 'identified', 'available', 'secured'].index(site.get('water_status', 'unknown')))
        with col2:
            fiber_status = st.selectbox("Fiber Status", options=['unknown', 'distant', 'nearby', 'adjacent', 'lit'], format_func=lambda x: x.title(),
                index=['unknown', 'distant', 'nearby', 'adjacent', 'lit'].index(site.get('fiber_status', 'unknown')))
            zoning_approved = st.checkbox("Zoning Approved", value=site.get('zoning_approved', False))
        with col3:
            developer_track_record = st.selectbox("Developer Track Record", options=['none', 'limited', 'proven', 'extensive'], format_func=lambda x: x.title(),
                index=['none', 'limited', 'proven', 'extensive'].index(site.get('developer_track_record', 'none')))
            utility_relationships = st.selectbox("Utility Relationships", options=['none', 'developing', 'established', 'strong'], format_func=lambda x: x.title(),
                index=['none', 'developing', 'established', 'strong'].index(site.get('utility_relationships', 'none')))
        
        st.markdown("---")
        st.subheader("Financial")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            capital_access = st.selectbox("Capital Access", options=['limited', 'developing', 'available', 'committed', 'strong'], format_func=lambda x: x.title(),
                index=['limited', 'developing', 'available', 'committed', 'strong'].index(site.get('capital_access', 'limited')))
        with col2:
            btm_capability = st.selectbox("BTM Capability", options=['none', 'potential', 'viable', 'multiple_sources'], format_func=lambda x: x.replace('_', ' ').title(),
                index=['none', 'potential', 'viable', 'multiple_sources'].index(site.get('btm_capability', 'none')))
        with col3:
            development_budget = st.checkbox("Development Budget Allocated", value=site.get('development_budget_allocated', False))
        
        st.markdown("---")
        notes = st.text_area("Notes", value=site.get('notes', ''))
        
        submitted = st.form_submit_button("💾 Save Site", type="primary")
        
        if submitted:
            if not name or not state or not utility:
                st.error("Please fill in required fields (Site Name, State, Utility)")
            else:
                site_data = {
                    'name': name, 'state': state, 'utility': utility, 'target_mw': target_mw, 'acreage': acreage,
                    'iso': iso, 'county': county, 'developer': developer, 'study_status': study_status,
                    'utility_commitment': utility_commitment, 'power_timeline_months': power_timeline_months,
                    'queue_position': queue_position, 'btm_viable': btm_viable, 'transmission_adjacent': transmission_adjacent,
                    'substation_nearby': substation_nearby, 'end_user_status': end_user_status,
                    'community_support': community_support, 'political_support': political_support,
                    'land_control': land_control, 'water_status': water_status, 'fiber_status': fiber_status,
                    'zoning_approved': zoning_approved, 'developer_track_record': developer_track_record,
                    'utility_relationships': utility_relationships, 'btm_capability': btm_capability,
                    'capital_access': capital_access, 'development_budget_allocated': development_budget, 'notes': notes
                }
                
                site_id = st.session_state.edit_site_id if editing else name.lower().replace(' ', '_')
                add_site(st.session_state.db, site_id, site_data)
                
                if editing: del st.session_state.edit_site_id
                
                st.success(f"Site {'updated' if editing else 'added'} successfully!")
                st.rerun()


def show_rankings():
    """Show site rankings with custom weighting."""
    st.title("🏆 Site Rankings")
    
    db = st.session_state.db
    sites = db.get('sites', {})
    
    if not sites:
        st.info("No sites in database to rank.")
        return
    
    st.sidebar.subheader("Adjust Weights")
    st.sidebar.caption("Weights must sum to 100%")
    
    weights = {}
    weights['state'] = st.sidebar.slider("State Score", 0, 50, int(st.session_state.weights['state'] * 100)) / 100
    weights['power'] = st.sidebar.slider("Power Pathway", 0, 50, int(st.session_state.weights['power'] * 100)) / 100
    weights['relationship'] = st.sidebar.slider("Relationship Capital", 0, 50, int(st.session_state.weights['relationship'] * 100)) / 100
    weights['execution'] = st.sidebar.slider("Execution", 0, 50, int(st.session_state.weights['execution'] * 100)) / 100
    weights['fundamentals'] = st.sidebar.slider("Fundamentals", 0, 50, int(st.session_state.weights['fundamentals'] * 100)) / 100
    weights['financial'] = st.sidebar.slider("Financial", 0, 50, int(st.session_state.weights['financial'] * 100)) / 100
    
    total_weight = sum(weights.values())
    if abs(total_weight - 1.0) > 0.01:
        st.sidebar.warning(f"Weights sum to {total_weight*100:.0f}% (should be 100%)")
    else:
        st.session_state.weights = weights
    
    rankings = []
    for site_id, site in sites.items():
        scores = calculate_site_score(site, weights)
        stage = determine_stage(site)
        state_profile = get_state_profile(site.get('state', ''))
        
        rankings.append({
            'Site': site.get('name', site_id), 'State': site.get('state', ''),
            'State Tier': state_profile.tier if state_profile else 'N/A',
            'MW': site.get('target_mw', 0), 'Stage': stage,
            'Overall': scores['overall_score'], 'State Score': scores['state_score'],
            'Power': scores['power_score'], 'Relationship': scores['relationship_score'],
            'Execution': scores['execution_score'], 'Fundamentals': scores['fundamentals_score'],
            'Financial': scores['financial_score']
        })
    
    rankings.sort(key=lambda x: x['Overall'], reverse=True)
    for i, r in enumerate(rankings): r['Rank'] = i + 1
    
    df = pd.DataFrame(rankings)
    df = df[['Rank', 'Site', 'State', 'State Tier', 'MW', 'Stage', 'Overall', 'State Score', 'Power', 'Relationship', 'Execution', 'Fundamentals', 'Financial']]
    
    st.dataframe(df, column_config={
        'Overall': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
        'State Score': st.column_config.ProgressColumn(min_value=0, max_value=100),
        'Power': st.column_config.ProgressColumn(min_value=0, max_value=100),
        'Relationship': st.column_config.ProgressColumn(min_value=0, max_value=100),
        'Execution': st.column_config.ProgressColumn(min_value=0, max_value=100),
        'Fundamentals': st.column_config.ProgressColumn(min_value=0, max_value=100),
        'Financial': st.column_config.ProgressColumn(min_value=0, max_value=100),
        'MW': st.column_config.NumberColumn(format="%d")
    }, hide_index=True, use_container_width=True)
    
    st.subheader("Score vs. Scale")
    fig = px.scatter(df, x='MW', y='Overall', color='Stage', size='MW', hover_name='Site', color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)


def show_state_analysis():
    """State-level analysis view."""
    st.title("🗺️ State Analysis")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_states = st.multiselect("Select States to Compare", options=list(STATE_PROFILES.keys()), default=['OK', 'TX', 'GA'])
    with col2:
        show_all = st.checkbox("Show All States Ranked")
    
    if show_all:
        st.subheader("National State Rankings")
        rankings = rank_all_states()
        df = pd.DataFrame(rankings)
        st.dataframe(df[['rank', 'state', 'name', 'tier', 'overall_score', 'regulatory', 'transmission', 'power', 'water', 'business', 'ecosystem', 'iso', 'industrial_rate']],
            column_config={
                'overall_score': st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f"),
                'industrial_rate': st.column_config.NumberColumn("Ind. Rate", format="$%.3f")
            }, hide_index=True, use_container_width=True)
    
    if selected_states:
        st.subheader("State Comparison")
        comparisons = compare_states(selected_states)
        
        categories = ['Regulatory', 'Transmission', 'Power', 'Water', 'Business', 'Ecosystem']
        fig = go.Figure()
        
        for state_data in comparisons:
            values = [state_data['regulatory'], state_data['transmission'], state_data['power'], state_data['water'], state_data['business'], state_data['ecosystem']]
            values.append(values[0])
            fig.add_trace(go.Scatterpolar(r=values, theta=categories + [categories[0]], name=state_data['name']))
        
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True, height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        for state_data in comparisons:
            with st.expander(f"📍 {state_data['name']} (Tier {state_data['tier']})", expanded=True):
                col1, col2, col3 = st.columns(3)
                col1.metric("Overall Score", f"{state_data['overall_score']:.1f}")
                col2.metric("ISO", state_data['primary_iso'])
                col3.metric("Avg Queue", f"{state_data['avg_queue_months']} mo")
                
                st.write("**Strengths:**")
                for s in state_data['strengths']: st.write(f"  ✅ {s}")
                st.write("**Weaknesses:**")
                for w in state_data['weaknesses']: st.write(f"  ⚠️ {w}")


def show_utility_research():
    """Utility research query generator."""
    st.title("🔍 Utility Research")
    st.write("Generate research queries for utility-specific information.")
    
    col1, col2 = st.columns(2)
    with col1:
        utility_name = st.text_input("Utility Name", placeholder="e.g., PSO, Georgia Power")
        state = st.selectbox("State", options=[''] + list(STATE_PROFILES.keys()))
    with col2:
        iso = st.selectbox("ISO/RTO", options=['', 'SPP', 'ERCOT', 'PJM', 'MISO', 'CAISO', 'WECC', 'SERC'])
    
    if st.button("🔍 Generate Research Queries"):
        if utility_name:
            st.subheader("Utility Research Queries")
            queries = generate_utility_research_queries(utility_name, state)
            for category, query_list in queries.items():
                with st.expander(category.replace('_', ' ').title()):
                    for q in query_list: st.code(q)
        
        if iso:
            st.subheader("ISO Research Queries")
            iso_queries = get_iso_research_queries(iso)
            for category, query_list in iso_queries.items():
                with st.expander(category.replace('_', ' ').title()):
                    for q in query_list: st.code(q)


def show_settings():
    """Settings and configuration."""
    st.title("⚙️ Settings")
    
    st.subheader("Scoring Weights")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Current Weights:**")
        for key, value in st.session_state.weights.items():
            st.write(f"  - {key.title()}: {value*100:.0f}%")
    
    with col2:
        if st.button("Reset to Defaults"):
            st.session_state.weights = {'state': 0.20, 'power': 0.25, 'relationship': 0.20, 'execution': 0.15, 'fundamentals': 0.10, 'financial': 0.10}
            st.success("Weights reset to defaults")
            st.rerun()
    
    st.markdown("---")
    st.subheader("Database Management")
    col1, col2, col3 = st.columns(3)
    
    col1.metric("Total Sites", len(st.session_state.db.get('sites', {})))
    
    with col2:
        if st.button("📥 Export Database"):
            db_json = json.dumps(st.session_state.db, indent=2, default=str)
            st.download_button("Download JSON", db_json, file_name="site_database.json", mime="application/json")
    
    with col3:
        uploaded_file = st.file_uploader("Import Database", type=['json'])
        if uploaded_file:
            try:
                imported_db = json.load(uploaded_file)
                st.session_state.db = imported_db
                save_database(imported_db)
                st.success("Database imported successfully")
                st.rerun()
            except Exception as e:
                st.error(f"Error importing database: {e}")


if __name__ == "__main__":
    main()
