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
from fpdf import FPDF

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
    """Calculate power pathway score (0-100) based on detailed phasing."""
    score = 0
    phases = site.get('phases', [])
    if not phases: return 0
    
    # Score based on most advanced phase
    max_phase_score = 0
    for p in phases:
        p_score = 0
        if p.get('ia_status') == 'Executed': p_score = 100
        elif p.get('fa_status') == 'Executed': p_score = 80
        elif p.get('fs_status') == 'Complete': p_score = 60
        elif p.get('sis_status') == 'Complete': p_score = 40
        elif p.get('sis_status') == 'In Progress': p_score = 20
        max_phase_score = max(max_phase_score, p_score)
    
    score += max_phase_score * 0.7  # 70% weight on study status
    
    # Timeline score
    timeline_months = site.get('power_timeline_months', 60)
    if timeline_months <= 36: score += 30
    elif timeline_months <= 48: score += 20
    elif timeline_months <= 60: score += 10
    
    return min(score, 100)

def calculate_relationship_score(site: Dict) -> float:
    """Calculate relationship capital score (0-100)."""
    # Default to 50 (Neutral) if not specified, as these fields are less emphasized in new form
    score = 50
    if site.get('community_support') == 'champion': score += 25
    elif site.get('community_support') == 'opposition': score -= 25
    
    if site.get('political_support') == 'strong': score += 25
    elif site.get('political_support') == 'opposition': score -= 25
    
    return min(max(score, 0), 100)

def calculate_execution_score(site: Dict) -> float:
    """Calculate execution capability score (0-100)."""
    score = 0
    np = site.get('non_power', {})
    
    # Zoning (40 pts)
    zoning = np.get('zoning_status', 'Not Started')
    if zoning == 'Approved': score += 40
    elif zoning == 'Submitted': score += 20
    elif zoning == 'Pre-App': score += 10
    
    # Onsite Gen Status (30 pts)
    gen = site.get('onsite_gen', {})
    if gen.get('gas_status') or gen.get('solar_mw', 0) > 0:
        score += 30
    
    # Developer Track Record (30 pts) - Legacy field, default to mid
    score += 30 
    
    return min(score, 100)

def calculate_fundamentals_score(site: Dict) -> float:
    """Calculate site fundamentals score (0-100)."""
    score = 0
    np = site.get('non_power', {})
    phases = site.get('phases', [])
    
    # Water (30 pts)
    if np.get('water_cap'): score += 30
    elif np.get('water_source'): score += 15
    
    # Fiber (20 pts)
    fiber = np.get('fiber_status', 'Unknown')
    if fiber == 'Lit Building': score += 20
    elif fiber == 'Nearby': score += 10
    
    # Transmission Distance (30 pts)
    min_dist = 999
    for p in phases:
        min_dist = min(min_dist, p.get('trans_dist', 999))
    
    if min_dist <= 1: score += 30
    elif min_dist <= 5: score += 20
    elif min_dist <= 10: score += 10
    
    # Acreage/Density (20 pts)
    target_mw = site.get('target_mw', 0)
    acreage = site.get('acreage', 0)
    if acreage > 0 and target_mw/acreage <= 5: score += 20
    
    return min(score, 100)

def calculate_financial_score(site: Dict) -> float:
    """Calculate financial capability score (0-100)."""
    return 70 # Default placeholder as financial inputs are removed

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
        pdf_bytes = generate_site_report_pdf(site, scores, stage, state_context)
        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_bytes,
            file_name=f"{site.get('name', 'site').replace(' ', '_')}_Report.pdf",
            mime="application/pdf"
        )
    with col3:
        if st.button("🗑️ Delete Site", type="secondary"):
            delete_site(st.session_state.db, site_id)
            st.success("Site deleted")
            st.rerun()

def generate_site_report_pdf(site: Dict, scores: Dict, stage: str, state_context: Dict) -> bytes:
    """Generate a PDF report matching the Site Diagnostic Report template."""
    class PDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 10)
            self.set_text_color(100, 100, 100)
            self.cell(0, 10, 'Site Diagnostic Report | Critical Path to Power', new_x="LMARGIN", new_y="NEXT", align='L')
            self.ln(2)
            self.line(10, 20, 200, 20)
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, f'Confidential | Page {self.page_no()}/{{nb}}', align='R')

    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # --- Title Block ---
    pdf.set_font("Helvetica", 'B', 24)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 15, f"{site.get('name', 'Unnamed Site')}", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 8, f"{site.get('target_mw', 0)} MW Target Capacity | {site.get('acreage', 0)} Acres", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, f"Utility: {site.get('utility', 'N/A')} | State: {site.get('state', 'N/A')} | Assessment Date: {datetime.now().strftime('%b %Y')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # --- Executive Summary ---
    pdf.set_font("Helvetica", 'B', 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, "Executive Summary", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)
    
    pdf.set_font("Helvetica", size=10)
    summary_text = (
        f"This diagnostic analyzes the critical path to power for {site.get('name')}, a {site.get('target_mw')} MW development "
        f"in {site.get('state')} served by {site.get('utility')}. The project is currently in the '{stage}' stage with an "
        f"overall score of {scores['overall_score']}/100. Key strengths include {', '.join(state_context['swot']['strengths'][:2])}."
    )
    pdf.multi_cell(0, 5, summary_text)
    pdf.ln(5)

    # --- Power Phasing Summary ---
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, "Power Phasing Summary", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)
    
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_fill_color(220, 220, 220)
    headers = ["Phase", "Interconnect", "Voltage", "Target Date", "Study Status"]
    col_widths = [20, 40, 30, 40, 60]
    
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, fill=True)
    pdf.ln()
    
    pdf.set_font("Helvetica", size=9)
    phases = site.get('phases', [])
    for i, p in enumerate(phases):
        if not p.get('mw'): continue # Skip empty phases
        row = [str(i+1), f"{p.get('mw')} MW", p.get('voltage', 'N/A'), p.get('target_date', 'N/A'), p.get('sis_status', 'N/A')]
        for j, r in enumerate(row):
            pdf.cell(col_widths[j], 8, str(r), border=1)
        pdf.ln()
    pdf.ln(10)

    # --- Capacity Trajectory ---
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, "Capacity Trajectory", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)
    
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_fill_color(220, 220, 220)
    headers = ["Year", "Interconnect", "Generation", "Limiting Factor"]
    col_widths = [30, 50, 50, 60]
    
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, fill=True)
    pdf.ln()
    
    pdf.set_font("Helvetica", size=9)
    schedule = site.get('schedule', {})
    for year in range(2025, 2036):
        y_data = schedule.get(str(year), {})
        ic = y_data.get('ic_mw', 0)
        gen = y_data.get('gen_mw', 0)
        if ic == 0 and gen == 0: continue
        
        limit = "Interconnection" if ic < gen else "Generation"
        row = [str(year), f"{ic} MW", f"{gen} MW", limit]
        for j, r in enumerate(row):
            pdf.cell(col_widths[j], 8, str(r), border=1)
        pdf.ln()
    pdf.ln(10)

    # --- Critical Path & Risks ---
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, "Risk Assessment & Bottlenecks", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)
    
    pdf.set_font("Helvetica", size=10)
    
    risks = site.get('risks', [])
    if not risks: risks.append("No critical risks identified.")
    
    for r in risks:
        pdf.set_text_color(200, 0, 0) if "[HIGH]" in r else pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, f"- {r}", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(5)
    pdf.set_text_color(0, 0, 0)
    
    # --- Non-Power Items ---
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, "Non-Power Items", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)
    
    pdf.set_font("Helvetica", size=10)
    np = site.get('non_power', {})
    items = [
        f"Zoning Status: {np.get('zoning_status', 'N/A')}",
        f"Water Source: {np.get('water_source', 'N/A')} ({np.get('water_cap', 'N/A')} GPD)",
        f"Fiber Status: {np.get('fiber_status', 'N/A')} ({np.get('fiber_provider', 'N/A')})",
        f"Environmental: {np.get('env_issues', 'None Reported')}"
    ]
    for item in items:
        pdf.cell(0, 6, f"- {item}", new_x="LMARGIN", new_y="NEXT")
        
    return bytes(pdf.output())


def show_add_edit_site():
    """Form for adding or editing sites with detailed diagnostic data."""
    st.title("➕ Add/Edit Site Diagnostic")
    
    editing = hasattr(st.session_state, 'edit_site_id') and st.session_state.edit_site_id
    site = st.session_state.db['sites'].get(st.session_state.edit_site_id, {}) if editing else {}
    
    if editing:
        st.info(f"Editing: {site.get('name', st.session_state.edit_site_id)}")
        if st.button("Cancel Edit"):
            del st.session_state.edit_site_id
            st.rerun()
    
    with st.form("site_form"):
        # Tabs for organized data entry
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "Basic Info", "Phasing & Studies", "Infrastructure", 
            "Onsite Gen", "Schedule", "Non-Power", "Analysis"
        ])
        
        # --- Tab 1: Basic Info ---
        with tab1:
            st.subheader("Site Overview")
            col1, col2, col3 = st.columns(3)
            with col1:
                name = st.text_input("Site Name*", value=site.get('name', ''))
                state = st.selectbox("State*", options=[''] + list(STATE_PROFILES.keys()),
                    index=([''] + list(STATE_PROFILES.keys())).index(site.get('state', '')) if site.get('state', '') in STATE_PROFILES else 0)
                utility = st.text_input("Utility Name*", value=site.get('utility', ''))
            with col2:
                target_mw = st.number_input("Target Capacity (MW)*", min_value=0, value=site.get('target_mw', 0))
                acreage = st.number_input("Acreage", min_value=0, value=site.get('acreage', 0))
                iso = st.selectbox("ISO/RTO", options=['', 'SPP', 'ERCOT', 'PJM', 'MISO', 'CAISO', 'WECC', 'SERC'],
                    index=['', 'SPP', 'ERCOT', 'PJM', 'MISO', 'CAISO', 'WECC', 'SERC'].index(site.get('iso', '')) if site.get('iso', '') else 0)
            with col3:
                county = st.text_input("County", value=site.get('county', ''))
                developer = st.text_input("Developer", value=site.get('developer', ''))
                assessment_date = st.date_input("Assessment Date", value=datetime.now())

        # --- Tab 2: Phasing & Studies ---
        with tab2:
            st.subheader("Power System Studies & Approvals")
            phases = site.get('phases', [{}, {}, {}, {}]) # Ensure 4 phases exist
            updated_phases = []
            
            for i in range(4):
                with st.expander(f"Phase {i+1}", expanded=(i==0)):
                    p = phases[i] if i < len(phases) else {}
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        sis_status = st.selectbox(f"P{i+1} SIS Status", options=['Not Started', 'In Progress', 'Complete'], key=f"p{i}_sis", index=['Not Started', 'In Progress', 'Complete'].index(p.get('sis_status', 'Not Started')))
                        sis_date = st.text_input(f"P{i+1} SIS Date", value=p.get('sis_date', ''), key=f"p{i}_sis_d")
                    with col2:
                        fs_status = st.selectbox(f"P{i+1} FS Status", options=['Not Started', 'In Progress', 'Complete'], key=f"p{i}_fs", index=['Not Started', 'In Progress', 'Complete'].index(p.get('fs_status', 'Not Started')))
                        fs_date = st.text_input(f"P{i+1} FS Date", value=p.get('fs_date', ''), key=f"p{i}_fs_d")
                    with col3:
                        fa_status = st.selectbox(f"P{i+1} FA Status", options=['Not Started', 'Draft', 'Executed'], key=f"p{i}_fa", index=['Not Started', 'Draft', 'Executed'].index(p.get('fa_status', 'Not Started')))
                        fa_date = st.text_input(f"P{i+1} FA Date", value=p.get('fa_date', ''), key=f"p{i}_fa_d")
                    with col4:
                        ia_status = st.selectbox(f"P{i+1} IA Status", options=['Not Started', 'Draft', 'Executed'], key=f"p{i}_ia", index=['Not Started', 'Draft', 'Executed'].index(p.get('ia_status', 'Not Started')))
                        ia_date = st.text_input(f"P{i+1} IA Date", value=p.get('ia_date', ''), key=f"p{i}_ia_d")
                    
                    updated_phases.append({
                        'sis_status': sis_status, 'sis_date': sis_date,
                        'fs_status': fs_status, 'fs_date': fs_date,
                        'fa_status': fa_status, 'fa_date': fa_date,
                        'ia_status': ia_status, 'ia_date': ia_date
                    })

        # --- Tab 3: Infrastructure ---
        with tab3:
            st.subheader("Interconnection Details")
            # We reuse the updated_phases list to add infrastructure details
            for i in range(4):
                with st.expander(f"Phase {i+1} Infrastructure", expanded=(i==0)):
                    p = phases[i] if i < len(phases) else {}
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        updated_phases[i]['mw'] = st.number_input(f"P{i+1} Capacity (MW)", value=p.get('mw', 0), key=f"p{i}_mw")
                        updated_phases[i]['voltage'] = st.selectbox(f"P{i+1} Voltage", options=['12.5kV', '69kV', '115kV', '138kV', '230kV', '345kV', '500kV'], key=f"p{i}_v", index=['12.5kV', '69kV', '115kV', '138kV', '230kV', '345kV', '500kV'].index(p.get('voltage', '138kV')))
                    with col2:
                        updated_phases[i]['service_type'] = st.selectbox(f"P{i+1} Service", options=['Radial', 'Loop', 'Switching Station', 'Network'], key=f"p{i}_svc", index=['Radial', 'Loop', 'Switching Station', 'Network'].index(p.get('service_type', 'Radial')))
                        updated_phases[i]['substation_status'] = st.selectbox(f"P{i+1} Substation", options=['Existing', 'Upgrade Required', 'New Build'], key=f"p{i}_sub", index=['Existing', 'Upgrade Required', 'New Build'].index(p.get('substation_status', 'Existing')))
                    with col3:
                        updated_phases[i]['trans_dist'] = st.number_input(f"P{i+1} Trans. Dist (mi)", value=p.get('trans_dist', 0.0), key=f"p{i}_dist")
                        updated_phases[i]['target_date'] = st.text_input(f"P{i+1} Target Date", value=p.get('target_date', ''), key=f"p{i}_tgt")

        # --- Tab 4: Onsite Generation ---
        with tab4:
            st.subheader("Onsite / BTM Generation")
            gen = site.get('onsite_gen', {})
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Natural Gas**")
                gas_mw = st.number_input("Gas Capacity (MW)", value=gen.get('gas_mw', 0))
                gas_pipe_dist = st.number_input("Pipeline Distance (mi)", value=gen.get('gas_pipe_dist', 0.0))
                gas_status = st.text_input("Gas Status", value=gen.get('gas_status', ''))
            
            with col2:
                st.markdown("**Solar / Battery**")
                solar_mw = st.number_input("Solar Capacity (MW)", value=gen.get('solar_mw', 0))
                batt_mw = st.number_input("Battery Capacity (MW)", value=gen.get('batt_mw', 0))
                batt_mwh = st.number_input("Battery Energy (MWh)", value=gen.get('batt_mwh', 0))

        # --- Tab 5: Schedule ---
        with tab5:
            st.subheader("Year-by-Year Capacity Trajectory")
            st.caption("Enter available MW for each year (Interconnection vs Generation)")
            
            schedule = site.get('schedule', {})
            updated_schedule = {}
            
            col1, col2 = st.columns(2)
            years = range(2025, 2036)
            mid_point = len(years) // 2
            
            for i, year in enumerate(years):
                with (col1 if i < mid_point else col2):
                    st.markdown(f"**{year}**")
                    c1, c2 = st.columns(2)
                    y_data = schedule.get(str(year), {})
                    ic_mw = c1.number_input(f"Interconnect MW", value=y_data.get('ic_mw', 0), key=f"y{year}_ic")
                    gen_mw = c2.number_input(f"Generation MW", value=y_data.get('gen_mw', 0), key=f"y{year}_gen")
                    updated_schedule[str(year)] = {'ic_mw': ic_mw, 'gen_mw': gen_mw}

        # --- Tab 6: Non-Power ---
        with tab6:
            st.subheader("Non-Power Infrastructure")
            np = site.get('non_power', {})
            
            col1, col2 = st.columns(2)
            with col1:
                zoning_status = st.selectbox("Zoning Status", options=['Not Started', 'Pre-App', 'Submitted', 'Approved'], index=['Not Started', 'Pre-App', 'Submitted', 'Approved'].index(np.get('zoning_status', 'Not Started')))
                water_source = st.text_input("Water Source", value=np.get('water_source', ''))
                water_cap = st.text_input("Water Capacity (GPD)", value=np.get('water_cap', ''))
            with col2:
                fiber_status = st.selectbox("Fiber Status", options=['Unknown', 'Nearby', 'Lit Building'], index=['Unknown', 'Nearby', 'Lit Building'].index(np.get('fiber_status', 'Unknown')))
                fiber_provider = st.text_input("Fiber Provider", value=np.get('fiber_provider', ''))
                env_issues = st.text_area("Environmental Issues", value=np.get('env_issues', ''))

        # --- Tab 7: Analysis ---
        with tab7:
            st.subheader("Diagnostic Analysis")
            risks = st.text_area("Key Risks (One per line)", value="\n".join(site.get('risks', [])), height=150)
            opps = st.text_area("Acceleration Opportunities", value="\n".join(site.get('opps', [])), height=150)
            questions = st.text_area("Open Questions", value="\n".join(site.get('questions', [])), height=150)

        st.markdown("---")
        submitted = st.form_submit_button("💾 Save Site Diagnostic", type="primary")
        
        if submitted:
            if not name or not state or not utility:
                st.error("Please fill in required fields (Site Name, State, Utility)")
            else:
                # Construct the complex site object
                site_data = {
                    'name': name, 'state': state, 'utility': utility, 'target_mw': target_mw, 
                    'acreage': acreage, 'iso': iso, 'county': county, 'developer': developer,
                    'phases': updated_phases,
                    'onsite_gen': {
                        'gas_mw': gas_mw, 'gas_pipe_dist': gas_pipe_dist, 'gas_status': gas_status,
                        'solar_mw': solar_mw, 'batt_mw': batt_mw, 'batt_mwh': batt_mwh
                    },
                    'schedule': updated_schedule,
                    'non_power': {
                        'zoning_status': zoning_status, 'water_source': water_source, 
                        'water_cap': water_cap, 'fiber_status': fiber_status, 
                        'fiber_provider': fiber_provider, 'env_issues': env_issues
                    },
                    'risks': risks.split('\n') if risks else [],
                    'opps': opps.split('\n') if opps else [],
                    'questions': questions.split('\n') if questions else [],
                    # Maintain legacy fields for compatibility
                    'study_status': updated_phases[0]['sis_status'],
                    'utility_commitment': 'committed' if updated_phases[0]['ia_status'] == 'Executed' else 'none',
                    'power_timeline_months': 48, # Default, should calculate from dates
                }
                
                site_id = st.session_state.edit_site_id if editing else name.lower().replace(' ', '_')
                add_site(st.session_state.db, site_id, site_data)
                
                if editing: del st.session_state.edit_site_id
                
                st.success(f"Site diagnostic {'updated' if editing else 'added'} successfully!")
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
