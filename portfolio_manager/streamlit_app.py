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
from .program_tracker import (
    ProgramTrackerData, TRACKER_COLUMN_ORDER, TRACKER_COLUMNS,
    calculate_portfolio_summary
)
from .program_management_page import show_program_tracker

# =============================================================================
# DATABASE MANAGEMENT - Google Sheets Integration
# =============================================================================

SHEET_NAME = "Sites Tracker - App"

@st.cache_resource
def get_sheets_client():
    """Get authenticated Google Sheets client."""
    import gspread
    from google.oauth2.service_account import Credentials
    
    # Use Streamlit secrets for credentials
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    
    return gspread.authorize(credentials)

def load_database() -> Dict:
    """Load site database from Google Sheets."""
    import time
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client = get_sheets_client()
            sheet = client.open(SHEET_NAME)
            
            # Try to get Sites worksheet, create if doesn't exist
            try:
                sites_ws = sheet.worksheet("Sites")
            except:
                sites_ws = sheet.add_worksheet(title="Sites", rows=1000, cols=50)
                # Add headers
                headers = [
                    "site_id", "name", "state", "utility", "target_mw", "acreage", "iso", "county",
                    "developer", "land_status", "community_support", "political_support",
                    "dev_experience", "capital_status", "financial_status", "last_updated",
                    "phases_json", "onsite_gen_json", "schedule_json", "non_power_json",
                    "risks_json", "opps_json", "questions_json",
                    # Program tracker columns
                    "client", "total_fee_potential", "contract_status",
                    "site_control_stage", "power_stage", "marketing_stage", "buyer_stage",
                    "zoning_stage", "water_stage", "incentives_stage",
                    "probability", "weighted_fee", "tracker_notes"
                ]
                sites_ws.append_row(headers)
            
            # Load all site data with retry
            try:
                all_rows = sites_ws.get_all_records()
            except Exception as e:
                st.warning(f"Error fetching data (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    raise
            
            sites = {}
            
            for row in all_rows:
                if not row.get('site_id'):
                    continue
                    
                site_id = row['site_id']
                
                # Safe conversion helper for numeric fields
                def safe_int(value, default=0):
                    if not value or value == '':
                        return default
                    try:
                        return int(float(value))  # Handle float strings like "100.0"
                    except (ValueError, TypeError):
                        return default
                
                # Reconstruct site dictionary
                site = {
                    'name': str(row.get('name', '')),
                    'state': str(row.get('state', '')),
                    'utility': str(row.get('utility', '')),
                    'target_mw': safe_int(row.get('target_mw'), 0),
                    'acreage': safe_int(row.get('acreage'), 0),
                    'iso': str(row.get('iso', '')),
                    'county': str(row.get('county', '')),
                    'developer': str(row.get('developer', '')),
                    'land_status': str(row.get('land_status', '')),
                    'community_support': str(row.get('community_support', '')),
                    'political_support': str(row.get('political_support', '')),
                    'dev_experience': str(row.get('dev_experience', '')),
                    'capital_status': str(row.get('capital_status', '')),
                    'financial_status': str(row.get('financial_status', '')),
                    'last_updated': str(row.get('last_updated', '')),
                }
                
                # Parse JSON fields with better error handling
                for json_field in ['phases', 'onsite_gen', 'schedule', 'non_power', 'risks', 'opps', 'questions']:
                    json_key = f'{json_field}_json'
                    default_value = [] if json_field in ['risks', 'opps', 'questions', 'phases'] else {}
                    
                    json_str = row.get(json_key, '')
                    if json_str and json_str.strip():
                        try:
                            parsed = json.loads(json_str)
                            # Validate the parsed data type
                            if json_field in ['risks', 'opps', 'questions', 'phases']:
                                site[json_field] = parsed if isinstance(parsed, list) else default_value
                            else:
                                site[json_field] = parsed if isinstance(parsed, dict) else default_value
                        except json.JSONDecodeError:
                            site[json_field] = default_value
                    else:
                        site[json_field] = default_value
                
                # Load program tracker fields
                site['client'] = str(row.get('client', ''))
                site['total_fee_potential'] = safe_int(row.get('total_fee_potential'), 0)
                site['contract_status'] = str(row.get('contract_status', 'No'))
                site['site_control_stage'] = safe_int(row.get('site_control_stage'), 1)
                site['power_stage'] = safe_int(row.get('power_stage'), 1)
                site['marketing_stage'] = safe_int(row.get('marketing_stage'), 1)
                site['buyer_stage'] = safe_int(row.get('buyer_stage'), 1)
                site['zoning_stage'] = safe_int(row.get('zoning_stage'), 1)
                site['water_stage'] = safe_int(row.get('water_stage'), 1)
                site['incentives_stage'] = safe_int(row.get('incentives_stage'), 1)
                
                # These are calculated, but we load them in case they exist
                try:
                    site['probability'] = float(row.get('probability', 0))
                except (TypeError, ValueError):
                    site['probability'] = 0.0
                try:
                    site['weighted_fee'] = float(row.get('weighted_fee', 0))
                except (TypeError, ValueError):
                    site['weighted_fee'] = 0.0
                    
                site['tracker_notes'] = str(row.get('tracker_notes', ''))
                
                sites[site_id] = site
            
            # Try to get metadata
            try:
                meta_ws = sheet.worksheet("Metadata")
                meta_rows = meta_ws.get_all_records()
                metadata = meta_rows[0] if meta_rows else {
                    'created': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat(),
                    'version': '1.0'
                }
            except:
                meta_ws = sheet.add_worksheet(title="Metadata", rows=10, cols=5)
                meta_ws.append_row(['created', 'last_updated', 'version'])
                metadata = {
                    'created': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat(),
                    'version': '1.0'
                }
                meta_ws.append_row([metadata['created'], metadata['last_updated'], metadata['version']])
            
            return {
                'sites': sites,
                'metadata': metadata
            }
            
        except Exception as e:
            st.error(f"Error loading from Google Sheets: {type(e).__name__}: {e}")
            if attempt < max_retries - 1:
                st.warning(f"Retrying... (attempt {attempt + 2}/{max_retries})")
                time.sleep(2 ** attempt)
                continue
            else:
                # Return empty database as fallback
                return {
                    'sites': {},
                    'metadata': {
                        'created': datetime.now().isoformat(),
                        'last_updated': datetime.now().isoformat(),
                        'version': '1.0'
                    }
                }

def save_database(db: Dict):
    """Save site database to Google Sheets."""
    try:
        client = get_sheets_client()
        sheet = client.open(SHEET_NAME)
        sites_ws = sheet.worksheet("Sites")
        
        # Update metadata
        db['metadata']['last_updated'] = datetime.now().isoformat()
        
        # Clear existing data (except headers)
        sites_ws.clear()
        
        # Re-add headers
        headers = [
            "site_id", "name", "state", "utility", "target_mw", "acreage", "iso", "county",
            "developer", "land_status", "community_support", "political_support",
            "dev_experience", "capital_status", "financial_status", "last_updated",
            "phases_json", "onsite_gen_json", "schedule_json", "non_power_json",
            "risks_json", "opps_json", "questions_json",
            # Program tracker columns
            "client", "total_fee_potential", "contract_status",
            "site_control_stage", "power_stage", "marketing_stage", "buyer_stage",
            "zoning_stage", "water_stage", "incentives_stage",
            "probability", "weighted_fee", "tracker_notes"
        ]
        sites_ws.append_row(headers)
        
        # Add all sites
        for site_id, site in db['sites'].items():
            # Recalculate tracker probabilities before saving
            tracker_data = ProgramTrackerData.from_dict({**site, 'site_id': site_id})
            tracker_data.update_calculations()
            
            row = [
                site_id,
                site.get('name', ''),
                site.get('state', ''),
                site.get('utility', ''),
                site.get('target_mw', 0),
                site.get('acreage', 0),
                site.get('iso', ''),
                site.get('county', ''),
                site.get('developer', ''),
                site.get('land_status', ''),
                site.get('community_support', ''),
                site.get('political_support', ''),
                site.get('dev_experience', ''),
                site.get('capital_status', ''),
                site.get('financial_status', ''),
                site.get('last_updated', ''),
                json.dumps(site.get('phases', [])),
                json.dumps(site.get('onsite_gen', {})),
                json.dumps(site.get('schedule', {})),
                json.dumps(site.get('non_power', {})),
                json.dumps(site.get('risks', [])),
                json.dumps(site.get('opps', [])),
                json.dumps(site.get('questions', [])),
                # Program tracker columns
                tracker_data.client,
                tracker_data.total_fee_potential,
                tracker_data.contract_status,
                tracker_data.site_control_stage,
                tracker_data.power_stage,
                tracker_data.marketing_stage,
                tracker_data.buyer_stage,
                tracker_data.zoning_stage,
                tracker_data.water_stage,
                tracker_data.incentives_stage,
                tracker_data.probability,
                tracker_data.weighted_fee,
                tracker_data.tracker_notes
            ]
            sites_ws.append_row(row)
        
        # Update metadata sheet
        try:
            meta_ws = sheet.worksheet("Metadata")
            meta_ws.clear()
            meta_ws.append_row(['created', 'last_updated', 'version'])
            meta_ws.append_row([
                db['metadata']['created'],
                db['metadata']['last_updated'],
                db['metadata']['version']
            ])
        except:
            pass
            
    except Exception as e:
        st.error(f"Error saving to Google Sheets: {e}")

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
    
    # Ensure phases is a list
    if not isinstance(phases, list):
        phases = []
    
    if not phases: return 0
    
    # Score based on most advanced phase
    max_phase_score = 0
    for p in phases:
        # Ensure each phase is a dictionary
        if not isinstance(p, dict):
            continue
            
        p_score = 0
        if p.get('energy_contract_status') == 'Executed': p_score = 100
        elif p.get('loa_status') == 'Executed': p_score = 75
        elif p.get('contract_study_status') == 'Complete': p_score = 50
        elif p.get('screening_status') == 'Complete': p_score = 25
        elif p.get('screening_status') == 'Initiated': p_score = 10
        max_phase_score = max(max_phase_score, p_score)
    
    score += max_phase_score * 0.7  # 70% weight on study status
    
    # Timeline score
    try:
        timeline_months = int(site.get('power_timeline_months', 60))
        if timeline_months <= 36: score += 30
        elif timeline_months <= 48: score += 20
        elif timeline_months <= 60: score += 10
    except (TypeError, ValueError):
        pass
    
    return min(score, 100)

def calculate_relationship_score(site: Dict) -> float:
    """Calculate relationship capital score (0-100)."""
    score = 50 # Base score
    
    # Community Support (40 pts range)
    comm = site.get('community_support', 'Neutral')
    if comm == 'Strong Support': score += 20
    elif comm == 'Opposition': score -= 20
    
    # Political Support (40 pts range)
    pol = site.get('political_support', 'Neutral')
    if pol == 'High': score += 20
    elif pol == 'Low': score -= 20
    
    # Landowner Relations (20 pts range)
    land = site.get('land_status', 'None')
    if land in ['Owned', 'Leased']: score += 10
    elif land == 'Option': score += 5
    
    return min(max(score, 0), 100)

def calculate_execution_score(site: Dict) -> float:
    """Calculate execution capability score (0-100)."""
    score = 0
    
    # Developer Experience (30 pts)
    exp = site.get('dev_experience', 'Medium')
    if exp == 'High': score += 30
    elif exp == 'Medium': score += 15
    
    # Capital Secured (30 pts)
    cap = site.get('capital_status', 'None')
    if cap == 'Secured': score += 30
    elif cap == 'Partial': score += 15
    
    # Permitting/Zoning (40 pts)
    np = site.get('non_power', {})
    
    # Ensure np is a dict
    if not isinstance(np, dict):
        np = {}
    
    zoning = np.get('zoning_status', 'Not Started')
    if zoning == 'Approved': score += 40
    elif zoning == 'Submitted': score += 20
    elif zoning == 'Pre-App': score += 10
    
    return min(score, 100)

def calculate_fundamentals_score(site: Dict) -> float:
    """Calculate site fundamentals score (0-100)."""
    score = 0
    np = site.get('non_power', {})
    
    # Ensure np is a dict
    if not isinstance(np, dict):
        np = {}
    
    phases = site.get('phases', [])
    
    # Ensure phases is a list
    if not isinstance(phases, list):
        phases = []
    
    # Land Control (20 pts)
    land = site.get('land_status', 'None')
    if land in ['Owned', 'Leased']: score += 20
    elif land == 'Option': score += 10
    
    # Water (20 pts)
    if np.get('water_cap'): score += 20
    elif np.get('water_source'): score += 10
    
    # Fiber (10 pts)
    fiber = np.get('fiber_status', 'Unknown')
    if fiber == 'Lit Building' or fiber == 'At Site': score += 10
    elif fiber == 'Nearby': score += 5
    
    # Transmission Distance (30 pts)
    min_dist = 999
    for p in phases:
        # Ensure each phase is a dictionary
        if isinstance(p, dict) and 'trans_dist' in p:
            try:
                trans_dist = float(p.get('trans_dist', 999))
                min_dist = min(min_dist, trans_dist)
            except (TypeError, ValueError):
                continue
    
    if min_dist <= 1: score += 30
    elif min_dist <= 5: score += 20
    elif min_dist <= 10: score += 10
    
    # Acreage/Density (20 pts)
    try:
        target_mw = float(site.get('target_mw', 0))
        acreage = float(site.get('acreage', 0))
        if acreage > 0 and target_mw > 0 and (target_mw / acreage) <= 5:
            score += 20
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    
    return min(score, 100)

def calculate_financial_score(site: Dict) -> float:
    """Calculate financial capability score (0-100)."""
    status = site.get('financial_status', 'Moderate')
    if status == 'Strong': return 90
    elif status == 'Moderate': return 60
    elif status == 'Weak': return 30
    return 50

# ... (skipping unchanged functions) ...

def show_rankings():
    """Show site rankings with custom weighting."""
    st.title("🏆 Site Rankings")
    
    db = st.session_state.db
    sites = db.get('sites', {})
    
    if not sites:
        st.info("No sites in database to rank.")
        return
    
    st.sidebar.subheader("Adjust Weights")
    weights = {
        'state': st.sidebar.slider("State Market", 0.0, 1.0, 0.20),
        'power': st.sidebar.slider("Power Pathway", 0.0, 1.0, 0.25),
        'relationship': st.sidebar.slider("Relationship", 0.0, 1.0, 0.20),
        'execution': st.sidebar.slider("Execution", 0.0, 1.0, 0.15),
        'fundamentals': st.sidebar.slider("Fundamentals", 0.0, 1.0, 0.10),
        'financial': st.sidebar.slider("Financial", 0.0, 1.0, 0.10)
    }
    
    # Normalize weights
    total_weight = sum(weights.values())
    if total_weight > 0:
        weights = {k: v/total_weight for k, v in weights.items()}
    
    site_data = []
    for site_id, site in sites.items():
        scores = calculate_site_score(site, weights)
        stage = determine_stage(site)
        state_context = generate_state_context_section(site.get('state', ''))
        
        site_data.append({
            'id': site_id,
            'State Tier': state_context['summary']['tier'],
            'MW': site.get('target_mw', 0),
            'Stage': stage,
            'Overall': scores['overall_score'],
            'State Score': scores['state_score'],
            'Power': scores['power_score'],
            'Relationship': scores['relationship_score'],
            'Execution': scores['execution_score'],
            'Fundamentals': scores['fundamentals_score'],
            'Financial': scores['financial_score']
        })
    
    df = pd.DataFrame(site_data).sort_values('Overall', ascending=False)
    
    st.dataframe(df.drop(columns=['id']), column_config={
        'Overall': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
        'State Score': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
        'Power': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
        'Relationship': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
        'Execution': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
        'Fundamentals': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
        'Financial': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
        'MW': st.column_config.NumberColumn(format="%d MW")
    }, hide_index=True, use_container_width=True)




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
        
    # Initialize page state if not present
    if 'page' not in st.session_state:
        st.session_state.page = "📊 Dashboard"
    
    st.sidebar.title("⚡ Portfolio Manager")
    
    # Check if we need to navigate (from Edit Site button)
    if 'navigation_target' in st.session_state:
        target_page = st.session_state.navigation_target
        del st.session_state.navigation_target
        st.session_state.page = target_page
    
    # Use session state for navigation
    page = st.sidebar.radio(
        "Navigation",
        ["📊 Dashboard", "🏭 Site Database", "💬 AI Chat", "📁 VDR Upload", "➕ Add/Edit Site", 
         "🏆 Rankings", "📊 Program Tracker", "🗺️ State Analysis", "🔍 Utility Research", "⚙️ Settings"],
        key="page"
    )
    
    if page == "📊 Dashboard": show_dashboard()
    elif page == "🏭 Site Database": show_site_database()
    elif page == "💬 AI Chat": show_ai_chat()
    elif page == "📁 VDR Upload": show_vdr_upload()
    elif page == "➕ Add/Edit Site": show_add_edit_site()
    elif page == "🏆 Rankings": show_rankings()
    elif page == "📊 Program Tracker": show_program_tracker()
    elif page == "🗺️ State Analysis": show_state_analysis()
    elif page == "🔍 Utility Research": show_utility_research()
    elif page == "⚙️ Settings": show_settings()


# ... (skipping unchanged functions) ...

def show_site_details(site_id: str):
    # ... (start of function remains same) ...
    site = st.session_state.db['sites'].get(site_id, {})
    scores = calculate_site_score(site, st.session_state.weights)
    state_context = generate_state_context_section(site.get('state', ''))
    stage = determine_stage(site)
    
    # ... (UI code) ...
    
    # Actions
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✏️ Edit Site", key=f"edit_{site_id}"):
            st.session_state.edit_site_id = site_id
            st.session_state.navigation_target = "➕ Add/Edit Site"
            st.rerun()
    with col2:
        pdf_bytes = generate_site_report_pdf(site, scores, stage, state_context)
        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_bytes,
            file_name=f"{site.get('name', 'site').replace(' ', '_')}_Report.pdf",
            mime="application/pdf",
            key=f"download_{site_id}"
        )
    with col3:
        if st.button("🗑️ Delete Site", type="secondary", key=f"delete_{site_id}"):
            delete_site(st.session_state.db, site_id)
            st.rerun()


def generate_site_report_pdf(site: Dict, scores: Dict, stage: str, state_context: Dict) -> bytes:
    """Generate comprehensive PDF report with visualizations and market research."""
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
            
        def draw_spider_graph(self, x, y, radius, data, labels):
            """Draw a spider graph at (x,y) with given radius."""
            import math
            
            # Draw background (5 concentric webs)
            self.set_line_width(0.1)
            self.set_draw_color(200, 200, 200)
            self.set_text_color(100, 100, 100)
            self.set_font('Helvetica', size=8)
            
            n_points = len(data)
            angle_step = 2 * math.pi / n_points
            
            # Draw axes and labels
            for i in range(n_points):
                angle = i * angle_step - math.pi / 2  # Start at top
                ax_x = x + radius * math.cos(angle)
                ax_y = y + radius * math.sin(angle)
                self.line(x, y, ax_x, ax_y)
                
                # Labels
                lbl_x = x + (radius + 5) * math.cos(angle)
                lbl_y = y + (radius + 5) * math.sin(angle)
                
                # Adjust label alignment
                align = 'C'
                if lbl_x < x - 5: align = 'R'
                elif lbl_x > x + 5: align = 'L'
                
                self.set_xy(lbl_x - 10, lbl_y - 3)
                self.cell(20, 6, labels[i], align=align)
            
            # Draw concentric polygons
            for r_step in [0.2, 0.4, 0.6, 0.8, 1.0]:
                curr_r = radius * r_step
                for i in range(n_points):
                    angle1 = i * angle_step - math.pi / 2
                    angle2 = ((i + 1) % n_points) * angle_step - math.pi / 2
                    x1 = x + curr_r * math.cos(angle1)
                    y1 = y + curr_r * math.sin(angle1)
                    x2 = x + curr_r * math.cos(angle2)
                    y2 = y + curr_r * math.sin(angle2)
                    self.line(x1, y1, x2, y2)
            
            # Draw Data Polygon
            self.set_line_width(0.5)
            self.set_draw_color(0, 102, 204)  # Blue
            self.set_fill_color(0, 102, 204)
            
            # Calculate points
            points = []
            for i, val in enumerate(data):
                angle = i * angle_step - math.pi / 2
                r_val = radius * (val / 100.0)
                px = x + r_val * math.cos(angle)
                py = y + r_val * math.sin(angle)
                points.append((px, py))
            
            with self.local_context(fill_opacity=0.2):
                self.polygon(points, style='DF')
                
            # Draw markers
            for px, py in points:
                self.circle(px, py, 1, style='F')
        
        def draw_line_chart(self, x, y, width, height, years, ic_data, gen_data, max_val):
            """Draw a line chart for capacity trajectory."""
            # Draw axes
            self.set_line_width(0.3)
            self.set_draw_color(0, 0, 0)
            self.line(x, y + height, x + width, y + height)  # X-axis
            self.line(x, y, x, y + height)  # Y-axis
            
            # Calculate scaling
            y_scale = height / max_val if max_val > 0 else 1
            x_step = width / len(years)
            
            # Draw grid lines and Y labels
            self.set_line_width(0.1)
            self.set_draw_color(220, 220, 220)
            self.set_font('Helvetica', size=7)
            for i in range(5):
                val = int((max_val / 4) * i)
                y_pos = y + height - (val * y_scale)
                self.line(x, y_pos, x + width, y_pos)
                self.set_xy(x - 15, y_pos - 2)
                self.cell(12, 4, str(val), align='R')
            
            # Draw IC line (light blue)
            self.set_line_width(0.8)
            self.set_draw_color(135, 206, 250)  # Light blue
            for i in range(len(years) - 1):
                x1 = x + i * x_step
                y1 = y + height - (ic_data[i] * y_scale)
                x2 = x + (i + 1) * x_step
                y2 = y + height - (ic_data[i + 1] * y_scale)
                self.line(x1, y1, x2, y2)
            
            # Draw Gen line (dark blue)
            self.set_draw_color(0, 51, 102)  # Dark blue
            for i in range(len(years) - 1):
                x1 = x + i * x_step
                y1 = y + height - (gen_data[i] * y_scale)
                x2 = x + (i + 1) * x_step
                y2 = y + height - (gen_data[i + 1] * y_scale)
                self.line(x1, y1, x2, y2)
            
            # Draw X labels
            self.set_font('Helvetica', size=7)
            for i, year in enumerate(years):
                if i % 2 == 0:  # Show every other year
                    x_pos = x + i * x_step
                    self.set_xy(x_pos - 5, y + height + 2)
                    self.cell(10, 4, str(year), align='C')
            
            # Legend
            legend_y = y - 8
            self.set_font('Helvetica', size=8)
            self.set_draw_color(135, 206, 250)
            self.line(x + width - 80, legend_y, x + width - 70, legend_y)
            self.set_xy(x + width - 68, legend_y - 2)
            self.cell(30, 4, "Interconnect MW")
            
            self.set_draw_color(0, 51, 102)
            self.line(x + width - 80, legend_y + 5, x + width - 70, legend_y + 5)
            self.set_xy(x + width - 68, legend_y + 3)
            self.cell(30, 4, "Generation MW")

    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # --- Title Block ---
    pdf.set_font("Helvetica", 'B', 24)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 15, f"{site.get('name', 'Unnamed Site')}", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"State: {site.get('state', 'N/A')} | Utility: {site.get('utility', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Target Capacity: {site.get('target_mw', 0)} MW | Acreage: {site.get('acreage', 0)} acres", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Stage: {stage}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # --- Score Analysis with Strengths/Risks ---
    pdf.set_font("Helvetica", 'B', 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "Score Analysis", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)
    
    # Overall Score - Large and prominent
    pdf.set_font("Helvetica", 'B', 36)
    pdf.set_xy(140, pdf.get_y())
    pdf.cell(60, 15, f"{scores['overall_score']:.1f}/100", align='C')
    
    # Spider Graph on left
    graph_y = pdf.get_y()
    labels = ["State", "Power", "Relationship", "Execution", "Fundamentals", "Financial"]
    values = [
        scores['state_score'], scores['power_score'], scores['relationship_score'],
        scores['execution_score'], scores['fundamentals_score'], scores['financial_score']
    ]
    pdf.draw_spider_graph(50, graph_y + 35, 25, values, labels)
    
    # Key Strengths (right side)
    pdf.set_xy(110, graph_y + 15)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.set_fill_color(220, 255, 220)  # Light green
    pdf.cell(85, 7, "Key Strengths", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_xy(110, pdf.get_y())
    
    pdf.set_font("Helvetica", size=9)
    # Identify top scoring categories
    strengths = []
    if scores['state_score'] >= 70:
        strengths.append(f"Strong State Market ({scores['state_score']:.0f})")
    if scores['power_score'] >= 70:
        strengths.append(f"Advanced Power Path ({scores['power_score']:.0f})")
    if scores['fundamentals_score'] >= 70:
        strengths.append(f"Solid Fundamentals ({scores['fundamentals_score']:.0f})")
    
    for strength in strengths[:3]:
        pdf.set_xy(110, pdf.get_y())
        pdf.multi_cell(85, 5, f"- {strength}")
    
    pdf.ln(5)
    
    # Key Risks (right side, below strengths)
    pdf.set_xy(110, pdf.get_y())
    pdf.set_font("Helvetica", 'B', 12)
    pdf.set_fill_color(255, 220, 220)  # Light red
    pdf.cell(85, 7, "Key Risks", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_xy(110, pdf.get_y())
    
    pdf.set_font("Helvetica", size=9)
    risks = site.get('risks', [])
    for risk in risks[:3]:
        pdf.set_xy(110, pdf.get_y())
        pdf.multi_cell(85, 5, f"- {risk}")
    
    pdf.ln(80)  # Move past the spider graph
    
    # --- Capacity Trajectory Chart ---
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, "Capacity Trajectory", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(5)
    
    schedule = site.get('schedule', {})
    if schedule:
        years = list(range(2025, 2036))
        ic_data = [schedule.get(str(y), {}).get('ic_mw', 0) for y in years]
        gen_data = [schedule.get(str(y), {}).get('gen_mw', 0) for y in years]
        max_val = max(max(ic_data), max(gen_data)) if ic_data and gen_data else 100
        max_val = int(max_val * 1.1)  # Add 10% headroom
        
        # Draw the chart
        chart_y = pdf.get_y()
        pdf.draw_line_chart(25, chart_y, 160, 60, years, ic_data, gen_data, max_val)
        pdf.ln(70)
        
        # Add table below chart
        pdf.set_font("Helvetica", 'B', 9)
        pdf.cell(30, 6, "Year", border=1)
        pdf.cell(60, 6, "Interconnection MW", border=1)
        pdf.cell(60, 6, "Generation MW", border=1)
        pdf.cell(40, 6, "Available MW", border=1)
        pdf.ln()
        
        pdf.set_font("Helvetica", size=8)
        for y in years:
            yd = schedule.get(str(y), {})
            ic_mw = yd.get('ic_mw', 0)
            gen_mw = yd.get('gen_mw', 0)
            pdf.cell(30, 5, str(y), border=1)
            pdf.cell(60, 5, str(ic_mw), border=1)
            pdf.cell(60, 5, str(gen_mw), border=1)
            pdf.cell(40, 5, str(min(ic_mw, gen_mw)), border=1)
            pdf.ln()
    
    pdf.ln(10)
    
    # --- Critical Path to Power ---
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, "Critical Path to Power", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)
    
    phases = site.get('phases', [])
    if phases:
        for i, p in enumerate(phases):
            pdf.set_font("Helvetica", 'B', 11)
            pdf.cell(0, 7, f"Phase {i+1}: {p.get('mw', 0)} MW @ {p.get('voltage', 'N/A')} kV", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", size=9)
            pdf.cell(0, 5, f"  Target Online: {p.get('target_date', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 5, f"  Screening Study: {p.get('screening_status', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 5, f"  Contract Study: {p.get('contract_study_status', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 5, f"  Letter of Agreement: {p.get('loa_status', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 5, f"  Energy Contract: {p.get('energy_contract_status', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
    
    pdf.ln(5)
    
    # --- Comprehensive Site Overview ---
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, "Site Overview", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)
    
    # Infrastructure
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 7, "Infrastructure", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    for i, p in enumerate(phases):
        pdf.cell(0, 5, f"Phase {i+1}: {p.get('service_type', 'N/A')} service, {p.get('substation_status', 'N/A')} substation, {p.get('trans_dist', 'N/A')} mi to transmission", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    
    # Onsite Generation
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 7, "Onsite Generation", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    gen = site.get('onsite_gen', {})
    pdf.cell(0, 5, f"Natural Gas: {gen.get('gas_mw', 0)} MW ({gen.get('gas_status', 'N/A')}), {gen.get('gas_dist', 'N/A')} mi to pipeline", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Solar: {gen.get('solar_mw', 0)} MW on {gen.get('solar_acres', 0)} acres", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Battery Storage: {gen.get('batt_mw', 0)} MW / {gen.get('batt_mwh', 0)} MWh", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    
    # Non-Power Items
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 7, "Non-Power Items", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    np = site.get('non_power', {})
    pdf.cell(0, 5, f"Zoning: {np.get('zoning_status', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
    # Safe water capacity conversion
    water_cap_raw = np.get('water_cap', 0)
    try:
        water_cap = float(water_cap_raw) if water_cap_raw else 0
    except (ValueError, TypeError):
        water_cap = 0
    pdf.cell(0, 5, f"Water: {np.get('water_source', 'N/A')} - {water_cap:,.0f} GPD capacity", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Fiber: {np.get('fiber_status', 'N/A')} ({np.get('fiber_provider', 'N/A')})", new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 5, f"Environmental: {np.get('env_issues', 'None identified')}")
    pdf.ln(5)
    
    # --- State & Market Analysis ---
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, f"{site.get('state', 'State')} Market Analysis", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)
    
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 7, f"Market Tier: {state_context.get('summary', {}).get('tier_label', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    
    # Create a description from available data
    description = f"{state_context.get('summary', {}).get('state', site.get('state', 'This state'))} is classified as a {state_context.get('summary', {}).get('tier_label', 'moderate market')} for data center development. "
    description += f"Primary ISO: {state_context.get('summary', {}).get('primary_iso', 'N/A')}. "
    description += f"Regulatory Structure: {state_context.get('summary', {}).get('regulatory_structure', 'N/A')}."
    
    pdf.multi_cell(0, 5, description)
    pdf.ln(3)
    
    # SWOT Analysis - Temporarily disabled due to rendering issues
    # Will be re-enabled with simpler text rendering
    # swot = state_context.get('swot', {})
    
    pdf.ln(5)
    
    # --- Risk & Opportunity Analysis ---
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, "Site-Specific Risk & Opportunity Analysis", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)
    
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 7, "Key Risks", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    for r in site.get('risks', [])[:5]:
        # Use cell() instead of multi_cell() to avoid rendering issues
        clean_text = str(r).strip()[:120]
        pdf.cell(0, 5, f"- {clean_text}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 7, "Acceleration Opportunities", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    for o in site.get('opps', [])[:5]:
        clean_text = str(o).strip()[:120]
        pdf.cell(0, 5, f"- {clean_text}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 7, "Open Questions", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    for q in site.get('questions', [])[:5]:
        clean_text = str(q).strip()[:120]
        pdf.cell(0, 5, f"- {clean_text}", new_x="LMARGIN", new_y="NEXT")
    
    return bytes(pdf.output())


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
        'Score': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
        'Power': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
        'Relationship': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
        'MW': st.column_config.NumberColumn(format="%d MW")
    }, hide_index=True, use_container_width=True)





# Helper functions for AI Chat site extraction and saving

def extract_site_from_conversation(messages):
    """Extract site data from conversation history using LLM for smart extraction."""
    import json
    import google.generativeai as genai
    import streamlit as st
    
    # Combine all messages into context
    conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    
    # Create comprehensive extraction prompt
    extraction_prompt = f"""Analyze this conversation about a data center site and extract ALL available structured data.

Conversation:
{conversation_text}

You must return a valid JSON object with this structure:

{{
  "state": "2-letter state code or null",
  "utility": "Utility name or null",
  "target_mw": 1200,
  "acreage": 200,
  "county": "County name or null",
  "developer": "Developer name or null",
  "location_hint": "City/region for site name or null",
  "land_status": "None/Option/Leased/Owned or null",
  "community_support": "Strong/Neutral/Opposition or null",
  "political_support": "High/Neutral/Low or null",
  "iso": "ISO name or null",
  "dev_experience": "High/Medium/Low or null",
  "capital_status": "Secured/Partial/None or null",
  "financial_status": "Strong/Moderate/Weak or null",
  
  "phases": [
    {{
      "mw": 1200,
      "screening_status": "Not Started",
      "contract_study_status": "Complete",
      "loa_status": "Executed",
      "energy_contract_status": "Not Started",
      "target_date": "2028-01-01",
      "voltage": "345",
      "service_type": "Transmission",
      "substation_status": "Existing",
      "trans_dist": 5.0,
      "ic_capacity": 1200
    }}
  ],
  
  "schedule": {{
    "2028": {{"ic_mw": 1200, "gen_mw": 250}},
    "2029": {{"ic_mw": 1200, "gen_mw": 500}},
    "2030": {{"ic_mw": 1200, "gen_mw": 750}}
  }},
  
  "onsite_gen": {{
    "gas_mw": 0,
    "gas_dist": 0,
    "gas_status": "None",
    "solar_mw": 0,
    "solar_acres": 0,
    "batt_mw": 0,
    "batt_mwh": 0
  }},
  
  "non_power": {{
    "zoning_status": "Not Started",
    "water_source": "Municipal",
    "water_cap": "10000",
    "fiber_status": "Unknown",
    "fiber_provider": null,
    "env_issues": null
  }},
  
  "risks": ["Risk 1", "Risk 2"],
  "opps": ["Opportunity 1"],
  "questions": ["Question 1"]
}}

CRITICAL RULES FOR SCHEDULE EXTRACTION:

1. "Full interconnect rating" means IC capacity is at full target immediately
2. "Ramps XMW/year via generation" means generation STARTS at X and ADDS X each year
3. Values must be integers or floats, NOT strings
4. ALWAYS populate schedule through year 2035, even after reaching target

EXAMPLE INTERPRETATION:
Input: "1.2GW site, full interconnect Jan 1 2028, ramps 250MW/year generation"
Should extract:
- IC reaches 1200 immediately in 2028 and stays at 1200
- Generation starts at 250 in 2028, adds 250 each year until reaching 1200
- After reaching 1200, MAINTAIN that level through 2035

Complete schedule extraction:
{{
  "2025": {{"ic_mw": 0, "gen_mw": 0}},
  "2026": {{"ic_mw": 0, "gen_mw": 0}},
  "2027": {{"ic_mw": 0, "gen_mw": 0}},
  "2028": {{"ic_mw": 1200, "gen_mw": 250}},
  "2029": {{"ic_mw": 1200, "gen_mw": 500}},
  "2030": {{"ic_mw": 1200, "gen_mw": 750}},
  "2031": {{"ic_mw": 1200, "gen_mw": 1000}},
  "2032": {{"ic_mw": 1200, "gen_mw": 1200}},
  "2033": {{"ic_mw": 1200, "gen_mw": 1200}},
  "2034": {{"ic_mw": 1200, "gen_mw": 1200}},
  "2035": {{"ic_mw": 1200, "gen_mw": 1200}}
}}

Return ONLY valid JSON with proper number types (not strings)."""


    try:
        # Use Gemini API directly for extraction
        api_key = st.secrets.get("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
        
        response = model.generate_content(
            extraction_prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        extracted = json.loads(response.text)
        
        # Handle if Gemini returns a list instead of dict
        if isinstance(extracted, list):
            extracted = extracted[0] if extracted else {}
        
        # Ensure it's a dict
        if not isinstance(extracted, dict):
            raise ValueError(f"Expected dict, got {type(extracted)}")
        
        # Clean up null values and generate suggested name
        extracted = {k: v for k, v in extracted.items() if v is not None and v != "null"}
        
        # Generate suggested name
        if 'location_hint' in extracted and extracted.get('state'):
            extracted['suggested_name'] = f"{extracted['location_hint']} {extracted['state']}"
        elif extracted.get('state') and extracted.get('utility'):
            extracted['suggested_name'] = f"{extracted['state']} {extracted['utility']}"
        
        # Remove location_hint (it was just for name generation)
        extracted.pop('location_hint', None)
        
        return extracted if extracted else None
        
    except Exception as e:
        st.warning(f"LLM extraction failed: {str(e)}. Using fallback extraction.")
        # Improved fallback extraction
        import re
        context = " ".join([m["content"] for m in messages])
        extracted = {}
        
        # State extraction
        state_match = re.search(r'\b(TX|OK|GA|IN|OH|VA|PA|WY|NV|CA)\b', context, re.IGNORECASE)
        if state_match:
            extracted['state'] = state_match.group(1).upper()
        
        # Utility extraction - expanded list
        utilities = ['Oncor', 'PSO', 'AEP', 'Duke', 'Georgia Power', 'Dominion', 'OVEC']
        for util in utilities:
            if util.lower() in context.lower():
                extracted['utility'] = util
                break
        
        # MW extraction
        mw_match = re.search(r'(\d+)\s*MW', context, re.IGNORECASE)
        if mw_match:
            extracted['target_mw'] = int(mw_match.group(1))
        
        # Acreage extraction
        acre_match = re.search(r'(\d+)\s*acres?', context, re.IGNORECASE)
        if acre_match:
            extracted['acreage'] = int(acre_match.group(1))
        
        # Study status extraction
        if 'FS complete' in context or 'FS Complete' in context or 'Facilities Study' in context:
            extracted['study_status'] = 'fs_complete'
        elif 'SIS complete' in context or 'SIS Complete' in context:
            extracted['study_status'] = 'sis_complete'
        
        # Land control extraction
        if 'option' in context.lower():
            extracted['land_control'] = 'option'
        
        # Generate name
        if extracted.get('utility') and extracted.get('state'):
            extracted['suggested_name'] = f"{extracted['utility']} {extracted['state']} Site"
        
        return extracted if extracted else None



def show_extracted_site_form(extracted_data):
    """Show form to edit and confirm extracted site data."""
    st.info("I've extracted the following details from our conversation. Please review and edit as needed:")
    
    with st.form("save_extracted_site"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Check both site_name (from VDR) and suggested_name (from chat)
            default_name = extracted_data.get('site_name') or extracted_data.get('suggested_name', '')
            name = st.text_input("Site Name *", value=default_name, 
                                help="Give this site a memorable name")
            state = st.selectbox("State *", 
                                options=['', 'OK', 'TX', 'WY', 'GA', 'VA', 'OH', 'IN', 'PA', 'NV', 'CA'],
                                index=(['', 'OK', 'TX', 'WY', 'GA', 'VA', 'OH', 'IN', 'PA', 'NV', 'CA'].index(extracted_data.get('state', '')) 
                                      if extracted_data.get('state') in ['OK', 'TX', 'WY', 'GA', 'VA', 'OH', 'IN', 'PA', 'NV', 'CA'] else 0))
            
            utility = st.text_input("Utility *", value=extracted_data.get('utility', ''))
            
            # Safely handle target_mw which might be None
            extracted_mw = extracted_data.get('target_mw')
            default_mw = int(extracted_mw) if extracted_mw and str(extracted_mw).replace('.','').isdigit() else 500
            target_mw = st.number_input("Target MW *", min_value=1, value=max(1, default_mw), step=50)
        
        with col2:
            # Safely handle acreage which might be None
            extracted_acreage = extracted_data.get('acreage')
            default_acreage = int(extracted_acreage) if extracted_acreage and str(extracted_acreage).replace('.','').isdigit() else 0
            acreage = st.number_input("Acreage", min_value=0, value=max(0, default_acreage))
            
            # New phasing terminology
            study_status_options = ['not_started', 'screening_study', 'contract_study', 'loa', 'energy_contract']
            study_status_labels = ['Not Started', 'Screening Study', 'Contract Study', 'Letter of Agreement', 'Energy Contract']
            
            # Map old terminology to new if needed
            old_status = extracted_data.get('study_status', 'not_started')
            mapped_status = {
                'sis_in_progress': 'screening_study',
                'sis_complete': 'screening_study',
                'fs_in_progress': 'contract_study',
                'fs_complete': 'contract_study',
                'fa_executed': 'loa',
                'ia_executed': 'energy_contract'
            }.get(old_status, old_status)
            
            study_index = study_status_options.index(mapped_status) if mapped_status in study_status_options else 0
            study_status = st.selectbox("Study Status", options=study_status_options, format_func=lambda x: study_status_labels[study_status_options.index(x)], index=study_index)
            
            land_options = ['', 'owned', 'option', 'loi', 'negotiating', 'none']
            land_index = land_options.index(extracted_data.get('land_control', '')) if extracted_data.get('land_control') in land_options else 0
            land_control = st.selectbox("Land Control", options=land_options, index=land_index)
            
            power_date = st.date_input("Target Power Date", value=None)
        
        col1_submit, col2_submit = st.columns([1, 1])
        with col1_submit:
            submitted = st.form_submit_button("💾 Save to Database", use_container_width=True, type="primary")
        with col2_submit:
            cancelled = st.form_submit_button("❌ Cancel", use_container_width=True)
        
        if submitted:
            if not name or not state or not utility:
                st.error("Please fill in required fields: Name, State, and Utility")
            else:
                try:
                    # Create site data
                    import hashlib
                    import datetime
                    
                    site_id = hashlib.md5(name.encode()).hexdigest()[:12]
                    
                    # Parse COD date from extracted data or calculate from timeline
                    cod_date = None
                    timeline_info = extracted_data.get('timeline_to_cod', '')
                    
                    # Try explicit COD date first
                    if extracted_data.get('cod_date'):
                        try:
                            cod_date = datetime.datetime.strptime(extracted_data['cod_date'], '%Y-%m-%d').date()
                        except:
                            pass
                    
                    # Calculate from timeline if available (e.g., "36 months from agreement execution")
                    if not cod_date and timeline_info:
                        import re
                        months_match = re.search(r'(\d+)\s*months?', timeline_info.lower())
                        if months_match:
                            months = int(months_match.group(1))
                            
                            # Check if we have the trigger event date (agreement execution, approval, etc.)
                            reference_date = None
                            agreement_date = extracted_data.get('agreement_execution_date')
                            
                            # Look for common agreement terminology in timeline
                            if agreement_date and any(term in timeline_info.lower() for term in ['ia', 'agreement', 'fa', 'gia', 'lgia', 'execution', 'approval']):
                                try:
                                    reference_date = datetime.datetime.strptime(agreement_date, '%Y-%m-%d').date()
                                except:
                                    pass
                            
                            # Use reference date if found, otherwise estimate from today
                            if reference_date:
                                cod_date = reference_date + datetime.timedelta(days=months * 30)
                                st.info(f"📅 Calculated COD: {months} months from agreement execution ({reference_date.isoformat()}) = {cod_date.isoformat()}")
                            else:
                                today = datetime.date.today()
                                cod_date = today + datetime.timedelta(days=months * 30)
                                st.warning(f"⚠️ Agreement execution date not found in documents. Estimating COD as {months} months from today ({today.isoformat()}) = {cod_date.isoformat()}")
                    
                    # Fallback to form input
                    if not cod_date and power_date:
                        cod_date = power_date
                    
                    # Get generation mix from extracted data
                    generation = extracted_data.get('generation', {})
                    gas_mw = generation.get('gas_mw', 0) if generation else 0
                    solar_mw = generation.get('solar_mw', 0) if generation else 0
                    battery_mw = generation.get('battery_mw', 0) if generation else 0
                    battery_mwh = generation.get('battery_mwh', 0) if generation else 0
                    
                    # Use schedule data directly from extraction if available
                    schedule_data = extracted_data.get('schedule', {})
                    if not isinstance(schedule_data, dict):
                        schedule_data = {}
                    
                    # Use phases data from extraction if available
                    phases_list = extracted_data.get('phases', [])
                    if not isinstance(phases_list, list):
                        phases_list = []
                    
                    # If no phases from extraction, create a default phase
                    if not phases_list:
                        phases_list = [{
                            'mw': target_mw,
                            'voltage': extracted_data.get('voltage', ''),
                            'service_type': extracted_data.get('service_type', ''),
                            'substation_status': extracted_data.get('substation', ''),
                            'trans_dist': extracted_data.get('transmission_distance', ''),
                            'screening_status': 'Not Started',
                            'contract_study_status': 'Not Started',
                            'loa_status': 'Not Started',
                            'energy_contract_status': 'Not Started',
                            'target_date': power_date.isoformat() if power_date else '',
                            'ic_capacity': target_mw
                        }]
                    
                    # Determine study completion dates based on current status
                    today = datetime.date.today()
                    study_dates = {}
                    if study_status in ['screening_study', 'contract_study', 'loa', 'energy_contract']:
                        study_dates['screening_study'] = (today - datetime.timedelta(days=180)).isoformat()
                    if study_status in ['contract_study', 'loa', 'energy_contract']:
                        study_dates['contract_study'] = (today - datetime.timedelta(days=90)).isoformat()
                    if study_status in ['loa', 'energy_contract']:
                        study_dates['loa'] = (today - datetime.timedelta(days=30)).isoformat()
                    if study_status == 'energy_contract':
                        study_dates['energy_contract'] = today.isoformat()
                    
                    # Build complete site profile from extracted data
                    new_site = {
                        # Basic Info
                        'name': name,
                        'state': state,
                        'utility': utility,
                        'target_mw': target_mw,
                        'acreage': acreage,
                        'study_status': study_status,
                        'land_status': land_control if land_control else 'None',
                        'power_date': power_date.isoformat() if power_date else '',
                        'community_support': extracted_data.get('community_support', 'Neutral'),
                        'political_support': extracted_data.get('political_support', 'Neutral'),
                        'county': extracted_data.get('county', ''),
                        'developer': extracted_data.get('developer', ''),
                        'dev_experience': extracted_data.get('dev_experience', 'Medium'),
                        'capital_status': extracted_data.get('capital_status', 'None'),
                        'financial_status': extracted_data.get('financial_status', 'Moderate'),
                        'iso': extracted_data.get('iso', ''),
                        'last_updated': datetime.datetime.now().isoformat(),
                        
                        # Phases - Use extracted phases data
                        'phases': phases_list,
                        
                        # Capacity Schedule - Use extracted schedule in year-keyed dictionary format
                        'schedule': schedule_data,
                        
                        # Onsite Generation - Use extracted onsite_gen if available
                        'onsite_gen': extracted_data.get('onsite_gen', {
                            'gas_mw': gas_mw or 0,
                            'gas_status': 'Planned' if (gas_mw and gas_mw > 0) else 'None',
                            'solar_mw': solar_mw or 0,
                            'batt_mw': battery_mw or 0,
                            'batt_mwh': battery_mwh or 0
                        }),
                        
                        # Non-Power Infrastructure
                        'non_power': extracted_data.get('non_power', {}),
                        
                        # Strategic Analysis
                        'risks': extracted_data.get('risks', []),
                        'opps': extracted_data.get('opps', []),
                        'questions': extracted_data.get('questions', []),
                        
                        # Notes (comprehensive from all extracted info)
                        'notes': extracted_data.get('notes', f"Created from VDR Upload on {datetime.date.today().isoformat()}"),
                        
                        # Metadata
                        'created_from': 'VDR Upload',
                        'created_date': datetime.date.today().isoformat(),
                        'source_files': extracted_data.get('_source_file', '')
                    }
                    
                    # Debug: Show what we're trying to save
                    st.info(f"Saving site with ID: {site_id}")
                    
                    # Save to Google Sheets database
                    db = load_database()  # Reload from Sheets to get latest
                    db['sites'][site_id] = new_site
                    save_database(db)
                    
                    # Reload session state
                    st.session_state.db = load_database()
                    
                    # Mark as saved but keep form visible
                    st.session_state.save_successful = True
                    
                    st.success(f"✅ Site '{name}' saved to Google Sheets database!")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ Save failed: {str(e)}")
                    st.exception(e)  # Show full traceback
        
        if cancelled:
            st.session_state.pending_site_save = None
            st.rerun()
    
    # Show Done button outside the form after successful save
    if st.session_state.get('save_successful'):
        if st.button("✅ Done - Upload More Documents"):
            st.session_state.pending_site_save = None
            st.session_state.save_successful = False
            st.rerun()

# =============================================================================
# AI CHAT PAGE
# =============================================================================

def show_ai_chat():
    """AI-powered site diagnostic chat."""
    st.title("💬 AI Site Diagnostic Chat")
    
    # Check if LLM is available
    try:
        from .llm_integration import PortfolioChat
    except ImportError as e:
        st.error(f"LLM integration not available. Error: {str(e)}")
        st.code("pip install google-generativeai", language="bash")
        st.info("If the issue persists, check Streamlit Cloud logs for deployment errors.")
        return
    except Exception as e:
        st.error(f"Unexpected error loading LLM integration: {str(e)}")
        return
    
    # Initialize chat messages
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    
    # Initialize chat client with Gemini
    try:
        if 'chat_client' not in st.session_state:
            # Get API key from secrets
            api_key = st.secrets.get("GEMINI_API_KEY")
            if not api_key:
                st.error("No Gemini API key found.")
                st.markdown("""
                Add to `.streamlit/secrets.toml`:
                ```toml
                GEMINI_API_KEY = "your-key-here"
                ```
                """)
                return
            
            st.session_state.chat_client = PortfolioChat(provider="gemini", api_key=api_key)
            # Load portfolio context
            sites = st.session_state.db['sites']
            st.session_state.chat_client.set_portfolio_context(sites)
            
    except Exception as e:
        st.error(f"Failed to initialize chat: {str(e)}")
        return
    
    # Info box
    with st.expander("ℹ️ How to use AI Chat", expanded=False):
        st.markdown("""
        **This chat understands your full portfolio context.** Describe sites naturally:
        
        *"We're evaluating a 750MW opportunity in Oklahoma, about 5 miles from a 345kV 
        PSO substation. Land is under option, and we've had initial conversations with 
        the utility but haven't filed for queue yet."*
        
        The AI will:
        - Assess the site against your scoring framework
        - Ask targeted diagnostic questions
        - Compare to your existing portfolio
        - Identify critical path items
        - Help you evaluate the opportunity
        
        **Example questions:**
        - "How does this compare to our other OK sites?"
        - "What's the typical queue time for PSO?"
        - "What should I ask the utility next?"
        - "What are the risks with this site?"
        """)
    
    st.markdown("---")
    
    # Display chat history
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # Chat input
    if prompt := st.chat_input("Describe a site or ask a question..."):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = st.session_state.chat_client.chat(prompt)
                    st.markdown(response)
                    st.session_state.chat_messages.append({"role": "assistant", "content": response})
                    
                    # Check if user wants to save the site
                    prompt_lower = prompt.lower().strip()
                    
                    # Explicit save requests (contain "save" or "add")
                    explicit_save_keywords = ['save the site', 'add to database', 'save it', 'add it', 'can you save', 'please save', 'add this']
                    
                    # Short confirmations (only if message is short to avoid false positives)
                    short_confirmations = ['yes', 'yep', 'yeah', 'ye', 'ok', 'okay', 'sure', 'proceed']
                    
                    should_save = False
                    
                    # Check for explicit save request
                    if any(keyword in prompt_lower for keyword in explicit_save_keywords):
                        should_save = True
                    # Check for short confirmation (only if message is short)
                    elif any(prompt_lower == keyword or prompt_lower.startswith(keyword + ' ') for keyword in short_confirmations) and len(prompt_lower) < 30:
                        should_save = True
                    
                    if should_save:
                        # Extract site data from conversation
                        with st.spinner("Extracting site data..."):
                            extracted_data = extract_site_from_conversation(st.session_state.chat_messages)
                            if extracted_data:
                                st.session_state.pending_site_save = extracted_data
                                st.rerun()  # Force rerun to show the form immediately
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    # Show save form if site data was extracted
    if 'pending_site_save' in st.session_state and st.session_state.pending_site_save:
        st.markdown("---")
        st.subheader("💾 Save Site to Database")
        show_extracted_site_form(st.session_state.pending_site_save)
    
    # Sidebar controls
    st.sidebar.markdown("---")
    st.sidebar.subheader("Chat Controls")
    
    if st.sidebar.button("🔄 Refresh Portfolio Context"):
        sites = st.session_state.db['sites']
        st.session_state.chat_client.set_portfolio_context(sites)
        st.sidebar.success("Context refreshed!")
    
    if st.sidebar.button("🗑️ Clear Chat History"):
        st.session_state.chat_messages = []
        if 'chat_client' in st.session_state:
            st.session_state.chat_client.clear_history()
        st.rerun()


# =============================================================================
# VDR UPLOAD PAGE
# =============================================================================

def show_vdr_upload():
    """Upload and process VDR documents for site data extraction."""
    st.title("📁 VDR Upload")
    
    st.write("""
    Upload site-related documents (PDFs, Word, Excel) for automated data extraction.
    Files will be saved to Google Drive and analyzed using AI.
    """)
    
    # Check if VDR folder ID is configured
    vdr_folder_id = st.secrets.get("VDR_FOLDER_ID")
    if not vdr_folder_id:
        st.error("VDR_FOLDER_ID not configured in secrets. Please add it to continue.")
        st.code('VDR_FOLDER_ID = "your-folder-id"')
        return
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Upload Documents",
        type=['pdf', 'docx', 'xlsx', 'xls', 'txt', 'csv'],
        accept_multiple_files=True,
        help="Upload interconnection studies, agreements, reports, spreadsheets, or text files"
    )
    
    if uploaded_files:
        st.success(f"📤 {len(uploaded_files)} file(s) uploaded")
        
        # Process button
        if st.button("🔍 Process Documents", type="primary"):
            from .vdr_processor import (
                process_uploaded_file,
                extract_site_data_from_text,
                upload_to_google_drive
            )
            
            all_extracted_data = {}
            
            for uploaded_file in uploaded_files:
                with st.expander(f"📄 {uploaded_file.name}", expanded=True):
                    try:
                        # Extract text
                        with st.spinner(f"Extracting text from {uploaded_file.name}..."):
                            text = process_uploaded_file(uploaded_file)
                            st.write(f"✅ Extracted {len(text)} characters")
                            
                            # Show preview
                            with st.expander("Text Preview"):
                                st.text(text[:1000] + "..." if len(text) > 1000 else text)
                        
                        # Upload to Google Drive
                        with st.spinner(f"Uploading to Google Drive..."):
                            uploaded_file.seek(0)  # Reset file pointer
                            file_bytes = uploaded_file.read()
                            drive_link = upload_to_google_drive(
                                file_bytes,
                                uploaded_file.name,
                                vdr_folder_id
                            )
                            
                            if drive_link:
                                st.success(f"✅ [Uploaded to Drive]({drive_link})")
                            else:
                                st.warning("⚠️ Drive upload failed, continuing with extraction")
                        
                        # Extract structured data using LLM
                        with st.spinner(f"Extracting site data with AI..."):
                            extracted = extract_site_data_from_text(text, uploaded_file.name)
                            
                            if extracted:
                                st.write("**Extracted Data:**")
                                st.json(extracted)
                                
                                # Merge with combined data
                                for key, value in extracted.items():
                                    if key not in all_extracted_data or not all_extracted_data[key]:
                                        all_extracted_data[key] = value
                            else:
                                st.info("No structured data extracted")
                    
                    except Exception as e:
                        st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")
            
            # Store extracted data in session state for the form
            if all_extracted_data:
                st.session_state.pending_site_save = all_extracted_data
                st.rerun()  # Rerun to show the form outside the button block
    
    # Show the save form if we have pending data (OUTSIDE the button block!)
    if st.session_state.get('pending_site_save'):
        st.markdown("---")
        st.subheader("💾 Save Consolidated Data to Database")
        st.info("Review the combined data extracted from all documents")
        show_extracted_site_form(st.session_state.pending_site_save)

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
            'Acreage': site.get('acreage', 0),
            'Stage': stage, 'Score': scores['overall_score'], 'State Score': scores['state_score'],
            'Power Score': scores['power_score'], 'Relationship': scores['relationship_score'],
            'Last Updated': site.get('last_updated', '')[:10] if site.get('last_updated') else ''
        })
    
    if filtered_sites:
        df = pd.DataFrame(filtered_sites)
        st.dataframe(df.drop(columns=['id']), column_config={
            'Score': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            'State Score': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            'Power Score': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            'Relationship': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            'Target MW': st.column_config.NumberColumn(format="%d"),
            'Acreage': st.column_config.NumberColumn(format="%d")
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
    
    # Header
    st.title(f"📍 {site.get('name', 'Unnamed Site')}")
    st.markdown(f"**State:** {site.get('state', 'N/A')} | **Utility:** {site.get('utility', 'N/A')}")
    st.markdown(f"**Target Capacity:** {site.get('target_mw', 0)} MW | **Acreage:** {site.get('acreage', 0)} acres")
    st.markdown(f"**Stage:** {stage}")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Score Analysis")
        
        # Spider Graph
        categories = ['State', 'Power', 'Relationship', 'Execution', 'Fundamentals', 'Financial']
        values = [
            scores['state_score'], scores['power_score'], scores['relationship_score'],
            scores['execution_score'], scores['fundamentals_score'], scores['financial_score']
        ]
        
        fig = go.Figure(data=go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=site.get('name', 'Site')
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False,
            margin=dict(l=40, r=40, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.metric("Overall Score", f"{scores['overall_score']}/100")
        st.markdown("### Key Strengths")
        if scores['state_score'] > 70: st.success(f"Strong State Market ({scores['state_score']})")
        if scores['power_score'] > 70: st.success(f"Advanced Power Path ({scores['power_score']})")
        if scores['fundamentals_score'] > 70: st.success(f"Solid Fundamentals ({scores['fundamentals_score']})")
        
        st.markdown("### Key Risks")
        for r in site.get('risks', [])[:3]:
            st.error(r)

    # --- Detailed Data View ---
    st.markdown("---")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚡ Power Pathway", "🏗️ Infrastructure", "📅 Schedule", "🌍 Non-Power", "🗺️ State Context"])
    
    with tab1:
        st.subheader("Power System Studies & Approvals")
        phases = site.get('phases', [])
        if phases:
            cols = st.columns(len(phases))
            for i, p in enumerate(phases):
                with cols[i]:
                    st.markdown(f"**Phase {i+1}**")
                    st.caption(f"{p.get('mw', 0)} MW @ {p.get('voltage', 'N/A')}")
                    st.write(f"**Screening:** {p.get('screening_status', 'N/A')}")
                    st.write(f"**Contract Study:** {p.get('contract_study_status', 'N/A')}")
                    st.write(f"**LOA:** {p.get('loa_status', 'N/A')}")
                    st.write(f"**Energy Contract:** {p.get('energy_contract_status', 'N/A')}")
        else:
            st.info("No phasing data available.")
            
    with tab2:
        st.subheader("Interconnection & Onsite Generation")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Interconnection**")
            # Show Phase 1 details as primary
            p1 = phases[0] if phases else {}
            st.write(f"**Service Type:** {p1.get('service_type', 'N/A')}")
            st.write(f"**Substation:** {p1.get('substation_status', 'N/A')}")
            st.write(f"**Dist. to Trans:** {p1.get('trans_dist', 'N/A')} miles")
        with col2:
            st.markdown("**Onsite Generation**")
            gen = site.get('onsite_gen', {})
            # Ensure gen is a dict
            if not isinstance(gen, dict):
                gen = {}
            st.write(f"**Gas:** {gen.get('gas_mw', 0)} MW ({gen.get('gas_status', 'N/A')})")
            st.write(f"**Solar:** {gen.get('solar_mw', 0)} MW")
            st.write(f"**Battery:** {gen.get('batt_mw', 0)} MW / {gen.get('batt_mwh', 0)} MWh")

    with tab3:
        st.subheader("Capacity Trajectory")
        schedule = site.get('schedule', {})
        # Ensure schedule is a dict
        if not isinstance(schedule, dict):
            schedule = {}
        
        if schedule:
            sched_data = []
            for y in range(2025, 2036):
                yd = schedule.get(str(y), {})
                # Ensure yd is a dict
                if not isinstance(yd, dict):
                    yd = {}
                sched_data.append({
                    'Year': str(y),
                    'Interconnect MW': yd.get('ic_mw', 0),
                    'Generation MW': yd.get('gen_mw', 0)
                })
            st.dataframe(pd.DataFrame(sched_data), hide_index=True, use_container_width=True)
            
            # Simple line chart
            chart_data = pd.DataFrame(sched_data).set_index('Year')
            st.line_chart(chart_data)
        else:
            st.info("No schedule data available.")

    with tab4:
        st.subheader("Non-Power Items")
        np = site.get('non_power', {})
        # Ensure np is a dict
        if not isinstance(np, dict):
            np = {}
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Zoning:** {np.get('zoning_status', 'N/A')}")
            st.write(f"**Water Source:** {np.get('water_source', 'N/A')}")
            st.write(f"**Water Cap:** {np.get('water_cap', 'N/A')} GPD")
        with col2:
            st.write(f"**Fiber Status:** {np.get('fiber_status', 'N/A')}")
            st.write(f"**Provider:** {np.get('fiber_provider', 'N/A')}")
            st.write(f"**Env Issues:** {np.get('env_issues', 'None')}")
            
        st.subheader("Analysis")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Risks**")
            for r in site.get('risks', []): st.write(f"- {r}")
        with col2:
            st.markdown("**Opportunities**")
            for o in site.get('opps', []): st.write(f"- {o}")

    with tab5:
        if 'error' not in state_context:
            col1, col2, col3 = st.columns(3)
            col1.write(f"**Tier:** {state_context['summary']['tier_label']}")
            col2.write(f"**ISO:** {state_context['summary']['primary_iso']}")
            col3.write(f"**Regulatory:** {state_context['summary']['regulatory_structure']}")
            
            st.write("**Strengths:**")
            for s in state_context['swot']['strengths'][:3]: st.write(f"  ✅ {s}")
            
            st.write("**Risks:**")
            for w in state_context['swot']['weaknesses'][:3]: st.write(f"  ⚠️ {w}")
            
            st.metric("State Score", f"{state_context['summary']['overall_score']}/100")
        else:
            st.warning(state_context['error'])

    # Actions
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✏️ Edit Site", key=f"edit_{site_id}"):
            st.session_state.edit_site_id = site_id
            st.session_state.navigation_target = "➕ Add/Edit Site"
            st.rerun()
    with col2:
        pdf_bytes = generate_site_report_pdf(site, scores, stage, state_context)
        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_bytes,
            file_name=f"{site.get('name', 'site').replace(' ', '_')}_Report.pdf",
            mime="application/pdf",
            key=f"download_{site_id}"
        )
    with col3:
        if st.button("🗑️ Delete Site", type="secondary", key=f"delete_{site_id}"):
            delete_site(st.session_state.db, site_id)
            st.rerun()
    



def show_add_edit_site():
    """Form for adding or editing sites with detailed diagnostic data."""
    st.title("➕ Add/Edit Site Diagnostic")
    
    editing = hasattr(st.session_state, 'edit_site_id') and st.session_state.edit_site_id
    site = st.session_state.db['sites'].get(st.session_state.edit_site_id, {}) if editing else {}
    
    if editing:
        st.info(f"Editing: {site.get('name', st.session_state.edit_site_id)}")
        if st.button("Cancel Edit"):
            if 'processing_save' in st.session_state:
                del st.session_state.processing_save
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
                                   index=list(STATE_PROFILES.keys()).index(site.get('state')) + 1 if site.get('state') in STATE_PROFILES else 0)
                utility = st.text_input("Utility*", value=site.get('utility', ''))
            with col2:
                # Safe numeric values
                def safe_number(val, default=0):
                    try:
                        num = int(float(val)) if val else default
                        return max(0, min(num, 100000))  # Reasonable cap for MW/acreage
                    except (ValueError, TypeError):
                        return default
                
                target_mw = st.number_input("Target Capacity (MW)*", value=safe_number(site.get('target_mw', 0)), min_value=0, max_value=100000)
                acreage = st.number_input("Acreage*", value=safe_number(site.get('acreage', 0)), min_value=0, max_value=100000)
                iso = st.selectbox("ISO/RTO", options=['SPP', 'ERCOT', 'PJM', 'MISO', 'CAISO', 'WECC', 'SERC', 'NYISO', 'ISO-NE'],
                                 index=['SPP', 'ERCOT', 'PJM', 'MISO', 'CAISO', 'WECC', 'SERC', 'NYISO', 'ISO-NE'].index(site.get('iso')) if site.get('iso') in ['SPP', 'ERCOT', 'PJM', 'MISO', 'CAISO', 'WECC', 'SERC', 'NYISO', 'ISO-NE'] else 0)
            with col3:
                county = st.text_input("County", value=site.get('county', ''))
                developer = st.text_input("Developer", value=site.get('developer', ''))
                land_status_options = ['None', 'Option', 'Leased', 'Owned']
                current_land_status = str(site.get('land_status', 'None'))
                # Ensure the current value is in the options list
                if current_land_status not in land_status_options:
                    current_land_status = 'None'
                land_status = st.selectbox("Land Status", options=land_status_options,
                                          index=land_status_options.index(current_land_status))
                date_str = st.date_input("Assessment Date", value=datetime.now())

        # --- Tab 2: Phasing & Studies ---
        with tab2:
            st.subheader("Power System Studies")
            
            # Dynamic Phase Count
            current_phases = site.get('phases', [])
            num_phases = st.number_input("Number of Phases", min_value=1, max_value=10, value=len(current_phases) if current_phases else 2)
            
            phases = []
            cols = st.columns(num_phases)
            for i in range(num_phases):
                p_data = current_phases[i] if i < len(current_phases) else {}
                with cols[i]:
                    st.markdown(f"**Phase {i+1}**")
                    # Safe MW value - cap at JavaScript safe integer limit
                    raw_mw = p_data.get('mw', 0)
                    try:
                        safe_mw = int(float(raw_mw)) if raw_mw else 0
                        safe_mw = max(0, min(safe_mw, 9007199254740991))  # JS Number.MAX_SAFE_INTEGER
                    except (ValueError, TypeError):
                        safe_mw = 0
                    mw = st.number_input(f"MW", key=f"p{i}_mw", value=safe_mw, min_value=0, max_value=100000)
                    
                    scr = st.selectbox(f"Screening Study", options=['Not Started', 'Initiated', 'Complete'], key=f"p{i}_scr",
                                     index=['Not Started', 'Initiated', 'Complete'].index(p_data.get('screening_status', 'Not Started')))
                    
                    con = st.selectbox(f"Contract Study", options=['Not Started', 'Initiated', 'Complete'], key=f"p{i}_con",
                                     index=['Not Started', 'Initiated', 'Complete'].index(p_data.get('contract_study_status', 'Not Started')))
                    
                    loa = st.selectbox(f"Letter of Agreement", options=['Not Started', 'Drafted', 'Executed'], key=f"p{i}_loa",
                                     index=['Not Started', 'Drafted', 'Executed'].index(p_data.get('loa_status', 'Not Started')))
                    
                    enc = st.selectbox(f"Energy Contract", options=['Not Started', 'Drafted', 'Executed'], key=f"p{i}_enc",
                                     index=['Not Started', 'Drafted', 'Executed'].index(p_data.get('energy_contract_status', 'Not Started')))
                    
                    target_date = st.date_input(f"Target Online", key=f"p{i}_date", 
                                              value=datetime.strptime(p_data.get('target_date'), '%Y-%m-%d') if p_data.get('target_date') else datetime.today())
                    
                    phases.append({
                        'mw': mw, 'screening_status': scr, 'contract_study_status': con, 
                        'loa_status': loa, 'energy_contract_status': enc,
                        'target_date': target_date.strftime('%Y-%m-%d')
                    })

        # --- Tab 3: Infrastructure ---
        with tab3:
            st.subheader("Interconnection Details")
            # We'll just use the same number of phases for infrastructure details
            infra_phases = []
            cols = st.columns(num_phases)
            for i in range(num_phases):
                p_data = current_phases[i] if i < len(current_phases) else {}
                # Merge with existing phase data if available
                p_base = phases[i]
                with cols[i]:
                    st.markdown(f"**Phase {i+1} Infra**")
                    
                    # Safe IC capacity value
                    raw_ic = p_data.get('ic_capacity', 0)
                    try:
                        safe_ic = int(float(raw_ic)) if raw_ic else 0
                        safe_ic = max(0, min(safe_ic, 100000))
                    except (ValueError, TypeError):
                        safe_ic = 0
                    ic_cap = st.number_input(f"IC Capacity (MW)", key=f"p{i}_ic", value=safe_ic, min_value=0, max_value=100000)
                    
                    voltage = st.selectbox(f"Voltage (kV)", options=['13.8', '34.5', '69', '115', '138', '230', '345', '500'], key=f"p{i}_v",
                                         index=['13.8', '34.5', '69', '115', '138', '230', '345', '500'].index(p_data.get('voltage', '138')) if p_data.get('voltage') in ['13.8', '34.5', '69', '115', '138', '230', '345', '500'] else 4)
                    
                    # Safe service type
                    service_options = ['Transmission', 'Distribution']
                    current_service = p_data.get('service_type', 'Transmission')
                    if current_service not in service_options:
                        current_service = 'Transmission'
                    service = st.selectbox(f"Service Type", options=service_options, key=f"p{i}_svc",
                                         index=service_options.index(current_service))
                    
                    # Safe substation status
                    sub_options = ['Existing', 'Upgrade Needed', 'New Build']
                    current_sub = p_data.get('substation_status', 'New Build')
                    if current_sub not in sub_options:
                        current_sub = 'New Build'
                    sub_status = st.selectbox(f"Substation", options=sub_options, key=f"p{i}_sub",
                                            index=sub_options.index(current_sub))
                    
                    # Safe distance value
                    raw_dist = p_data.get('trans_dist', 0.0)
                    try:
                        safe_dist = float(raw_dist) if raw_dist else 0.0
                        safe_dist = max(0.0, min(safe_dist, 1000.0))
                    except (ValueError, TypeError):
                        safe_dist = 0.0
                    dist = st.number_input(f"Dist. to Trans (mi)", key=f"p{i}_dist", value=safe_dist, min_value=0.0, max_value=1000.0)
                    
                    p_base.update({
                        'ic_capacity': ic_cap, 'voltage': voltage, 'service_type': service,
                        'substation_status': sub_status, 'trans_dist': dist
                    })
                    infra_phases.append(p_base)
            
            # Update the main phases list with infra data
            phases = infra_phases

        # --- Tab 4: Onsite Gen ---
        with tab4:
            st.subheader("Onsite Generation")
            gen = site.get('onsite_gen', {})
            # Ensure gen is a dict
            if not isinstance(gen, dict):
                gen = {}
            
            # Safe number helper - always returns float
            def safe_gen_number(val, default=0.0):
                try:
                    num = float(val) if val else float(default)
                    return float(max(0.0, min(num, 100000.0)))
                except (ValueError, TypeError):
                    return float(default)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("🔥 **Natural Gas**")
                gas_mw = st.number_input("Gas Capacity (MW)", value=safe_gen_number(gen.get('gas_mw', 0)), min_value=0.0, max_value=10000.0)
                gas_dist = st.number_input("Dist. to Pipeline (mi)", value=safe_gen_number(gen.get('gas_dist', 0.0)), min_value=0.0, max_value=1000.0)
                
                # Safe gas status
                gas_options = ['None', 'Study', 'Permitting', 'Construction', 'Operational']
                current_gas_status = str(gen.get('gas_status', 'None'))
                if current_gas_status not in gas_options:
                    current_gas_status = 'None'
                gas_status = st.selectbox("Gas Status", options=gas_options,
                                        index=gas_options.index(current_gas_status))
            with col2:
                st.markdown("☀️ **Solar**")
                solar_mw = st.number_input("Solar Capacity (MW)", value=safe_gen_number(gen.get('solar_mw', 0)), min_value=0.0, max_value=10000.0)
                solar_acres = st.number_input("Solar Acres", value=safe_gen_number(gen.get('solar_acres', 0)), min_value=0.0, max_value=100000.0)
            with col3:
                st.markdown("🔋 **Battery Storage**")
                batt_mw = st.number_input("BESS Power (MW)", value=safe_gen_number(gen.get('batt_mw', 0)), min_value=0.0, max_value=10000.0)
                batt_mwh = st.number_input("BESS Energy (MWh)", value=safe_gen_number(gen.get('batt_mwh', 0)), min_value=0.0, max_value=100000.0)
            
            onsite_gen = {
                'gas_mw': gas_mw, 'gas_dist': gas_dist, 'gas_status': gas_status,
                'solar_mw': solar_mw, 'solar_acres': solar_acres,
                'batt_mw': batt_mw, 'batt_mwh': batt_mwh
            }

        # --- Tab 5: Schedule ---
        with tab5:
            st.subheader("Capacity Trajectory (2025-2035)")
            schedule = site.get('schedule', {})
            sched_data = {}
            
            # Table header
            cols = st.columns([1, 2, 2, 2])
            cols[0].markdown("**Year**")
            cols[1].markdown("**Interconnection (MW)**")
            cols[2].markdown("**Generation (MW)**")
            cols[3].markdown("**Total Available (MW)**")
            
            for y in range(2025, 2036):
                yd = schedule.get(str(y), {})
                c1, c2, c3, c4 = st.columns([1, 2, 2, 2])
                c1.write(str(y))
                ic = c2.number_input(f"IC {y}", key=f"ic_{y}", value=yd.get('ic_mw', 0), label_visibility="collapsed")
                gen_val = c3.number_input(f"Gen {y}", key=f"gen_{y}", value=yd.get('gen_mw', 0), label_visibility="collapsed")
                
                total = min(ic, gen_val)
                c4.write(f"{total} MW")
                
                sched_data[str(y)] = {'ic_mw': ic, 'gen_mw': gen_val}

        # --- Tab 6: Non-Power ---
        with tab6:
            st.subheader("Site Fundamentals")
            np = site.get('non_power', {})
            col1, col2 = st.columns(2)
            with col1:
                zoning = st.selectbox("Zoning Status", options=['Not Started', 'Pre-App', 'Submitted', 'Approved'],
                                    index=['Not Started', 'Pre-App', 'Submitted', 'Approved'].index(np.get('zoning_status', 'Not Started')))
                water_src = st.text_input("Water Source", value=np.get('water_source', ''))
                # Safe water capacity conversion
                raw_water_cap = np.get('water_cap', 0)
                try:
                    safe_water_cap = int(float(raw_water_cap)) if raw_water_cap else 0
                    safe_water_cap = max(0, min(safe_water_cap, 1000000))
                except (ValueError, TypeError):
                    safe_water_cap = 0
                water_cap = st.number_input("Water Capacity (GPD)", value=safe_water_cap, min_value=0, max_value=1000000)
            with col2:
                fiber_stat = st.selectbox("Fiber Status", options=['Unknown', 'Nearby', 'At Site', 'Lit Building'],
                                        index=['Unknown', 'Nearby', 'At Site', 'Lit Building'].index(np.get('fiber_status', 'Unknown')))
                fiber_prov = st.text_input("Fiber Provider", value=np.get('fiber_provider', ''))
                env_issues = st.text_area("Environmental Issues", value=np.get('env_issues', ''))
            
            non_power = {
                'zoning_status': zoning, 'water_source': water_src, 'water_cap': water_cap,
                'fiber_status': fiber_stat, 'fiber_provider': fiber_prov, 'env_issues': env_issues
            }

        # --- Tab 7: Analysis & Scoring ---
        with tab7:
            st.subheader("Scoring Factors")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**Relationship**")
                
                # Safe mapping for Community Support
                c_val = site.get('community_support', 'Neutral')
                if c_val == 'champion': c_val = 'Strong Support'
                elif c_val == 'opposition': c_val = 'Opposition'
                if c_val not in ['Strong Support', 'Neutral', 'Opposition']: c_val = 'Neutral'
                
                comm_supp = st.selectbox("Community Support", options=['Strong Support', 'Neutral', 'Opposition'],
                                       index=['Strong Support', 'Neutral', 'Opposition'].index(c_val))
                
                # Safe mapping for Political Support
                p_val = site.get('political_support', 'Neutral')
                if p_val == 'strong': p_val = 'High'
                elif p_val == 'opposition': p_val = 'Low'
                if p_val not in ['High', 'Neutral', 'Low']: p_val = 'Neutral'
                
                pol_supp = st.selectbox("Political Support", options=['High', 'Neutral', 'Low'],
                                      index=['High', 'Neutral', 'Low'].index(p_val))
            with col2:
                st.markdown("**Execution**")
                
                d_val = site.get('dev_experience', 'Medium')
                if d_val not in ['High', 'Medium', 'Low']: d_val = 'Medium'
                dev_exp = st.selectbox("Developer Experience", options=['High', 'Medium', 'Low'],
                                     index=['High', 'Medium', 'Low'].index(d_val))
                
                cap_val = site.get('capital_status', 'None')
                if cap_val not in ['Secured', 'Partial', 'None']: cap_val = 'None'
                cap_stat = st.selectbox("Capital Status", options=['Secured', 'Partial', 'None'],
                                      index=['Secured', 'Partial', 'None'].index(cap_val))
            with col3:
                st.markdown("**Financial**")
                
                f_val = site.get('financial_status', 'Moderate')
                if f_val not in ['Strong', 'Moderate', 'Weak']: f_val = 'Moderate'
                fin_stat = st.selectbox("Financial Strength", options=['Strong', 'Moderate', 'Weak'],
                                      index=['Strong', 'Moderate', 'Weak'].index(f_val))
            
            st.markdown("---")
            st.subheader("Strategic Analysis")
            risks_txt = st.text_area("Key Risks (one per line)", value='\n'.join(site.get('risks', [])))
            opps_txt = st.text_area("Acceleration Opportunities", value='\n'.join(site.get('opps', [])))
            questions_txt = st.text_area("Open Questions", value='\n'.join(site.get('questions', [])))
        
        submitted = st.form_submit_button("💾 Save Site Diagnostic")
        
        if submitted:
            # Check if we're already processing a submission
            if st.session_state.get('processing_save', False):
                st.warning("Save in progress, please wait...")
                return
            
            # Set processing flag
            st.session_state.processing_save = True
            
            if not name or not state:
                st.error("Name and State are required.")
            else:
                new_site = {
                    'name': name, 'state': state, 'utility': utility, 'target_mw': target_mw,
                    'acreage': acreage, 'iso': iso, 'county': county, 'developer': developer,
                    'land_status': land_status,
                    'community_support': comm_supp, 'political_support': pol_supp,
                    'dev_experience': dev_exp, 'capital_status': cap_stat,
                    'financial_status': fin_stat,
                    'last_updated': datetime.now().isoformat(),
                    'phases': phases,
                    'onsite_gen': onsite_gen,
                    'schedule': sched_data,
                    'non_power': non_power,
                    'risks': [r.strip() for r in risks_txt.split('\n') if r.strip()],
                    'opps': [o.strip() for o in opps_txt.split('\n') if o.strip()],
                    'questions': [q.strip() for q in questions_txt.split('\n') if q.strip()],
                    # Legacy fields for backward compatibility
                    'study_status': phases[0].get('screening_status', 'Not Started') if phases else 'Not Started',
                    'utility_commitment': 'Committed' if phases and phases[0].get('energy_contract_status') == 'Executed' else 'None',
                    'power_timeline_months': 36 # Placeholder
                }
                
                # Generate deterministic site_id based on name
                if editing:
                    site_id = st.session_state.edit_site_id
                else:
                    # Reload database to get latest data from Google Sheets before checking duplicates
                    fresh_db = load_database()
                    
                    site_id = name.lower().replace(' ', '_').replace('-', '_')
                    # Ensure unique ID by checking against fresh data from Sheets
                    base_id = site_id
                    counter = 1
                    while site_id in fresh_db['sites']:
                        site_id = f"{base_id}_{counter}"
                        counter += 1
                    
                    # Update session state with fresh data
                    st.session_state.db = fresh_db
                
                st.session_state.db['sites'][site_id] = new_site
                save_database(st.session_state.db)
                
                # Reload database from Google Sheets to ensure fresh data
                st.session_state.db = load_database()
                
                # Set edit_site_id so subsequent saves update this site instead of creating new ones
                if not editing:
                    st.session_state.edit_site_id = site_id
                
                # Clear processing flag
                st.session_state.processing_save = False
                
                st.success(f"✅ Site diagnostic  {'updated' if editing else 'added'} successfully!")
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
