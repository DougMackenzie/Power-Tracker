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
                "risks_json", "opps_json", "questions_json"
            ]
            sites_ws.append_row(headers)
        
        # Load all site data
        all_rows = sites_ws.get_all_records()
        sites = {}
        
        for row in all_rows:
            if not row.get('site_id'):
                continue
                
            site_id = row['site_id']
            
            # Reconstruct site dictionary
            site = {
                'name': row.get('name', ''),
                'state': row.get('state', ''),
                'utility': row.get('utility', ''),
                'target_mw': int(row.get('target_mw', 0)) if row.get('target_mw') else 0,
                'acreage': int(row.get('acreage', 0)) if row.get('acreage') else 0,
                'iso': row.get('iso', ''),
                'county': row.get('county', ''),
                'developer': row.get('developer', ''),
                'land_status': row.get('land_status', ''),
                'community_support': row.get('community_support', ''),
                'political_support': row.get('political_support', ''),
                'dev_experience': row.get('dev_experience', ''),
                'capital_status': row.get('capital_status', ''),
                'financial_status': row.get('financial_status', ''),
                'last_updated': row.get('last_updated', ''),
            }
            
            # Parse JSON fields
            for json_field in ['phases', 'onsite_gen', 'schedule', 'non_power', 'risks', 'opps', 'questions']:
                json_key = f'{json_field}_json'
                if row.get(json_key):
                    try:
                        site[json_field] = json.loads(row[json_key])
                    except:
                        site[json_field] = [] if json_field in ['risks', 'opps', 'questions'] else {}
                else:
                    site[json_field] = [] if json_field in ['risks', 'opps', 'questions'] else {}
            
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
        st.error(f"Error loading from Google Sheets: {e}")
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
            "risks_json", "opps_json", "questions_json"
        ]
        sites_ws.append_row(headers)
        
        # Add all sites
        for site_id, site in db['sites'].items():
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
                json.dumps(site.get('questions', []))
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
    if not phases: return 0
    
    # Score based on most advanced phase
    max_phase_score = 0
    for p in phases:
        p_score = 0
        if p.get('energy_contract_status') == 'Executed': p_score = 100
        elif p.get('loa_status') == 'Executed': p_score = 75
        elif p.get('contract_study_status') == 'Complete': p_score = 50
        elif p.get('screening_status') == 'Complete': p_score = 25
        elif p.get('screening_status') == 'Initiated': p_score = 10
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
    zoning = np.get('zoning_status', 'Not Started')
    if zoning == 'Approved': score += 40
    elif zoning == 'Submitted': score += 20
    elif zoning == 'Pre-App': score += 10
    
    return min(score, 100)

def calculate_fundamentals_score(site: Dict) -> float:
    """Calculate site fundamentals score (0-100)."""
    score = 0
    np = site.get('non_power', {})
    phases = site.get('phases', [])
    
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
    
    # Use session state for navigation
    page = st.sidebar.radio(
        "Navigation",
        ["📊 Dashboard", "🏭 Site Database", "➕ Add/Edit Site", 
         "🏆 Rankings", "🗺️ State Analysis", "🔍 Utility Research", "⚙️ Settings"],
        key="page"
    )
    
    if page == "📊 Dashboard": show_dashboard()
    elif page == "🏭 Site Database": show_site_database()
    elif page == "➕ Add/Edit Site": show_add_edit_site()
    elif page == "🏆 Rankings": show_rankings()
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
            st.session_state.page = "➕ Add/Edit Site" # Force navigation
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
    pdf.cell(0, 5, f"Water: {np.get('water_source', 'N/A')} - {np.get('water_cap', 0):,.0f} GPD capacity", new_x="LMARGIN", new_y="NEXT")
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
            st.write(f"**Gas:** {gen.get('gas_mw', 0)} MW ({gen.get('gas_status', 'N/A')})")
            st.write(f"**Solar:** {gen.get('solar_mw', 0)} MW")
            st.write(f"**Battery:** {gen.get('batt_mw', 0)} MW / {gen.get('batt_mwh', 0)} MWh")

    with tab3:
        st.subheader("Capacity Trajectory")
        schedule = site.get('schedule', {})
        if schedule:
            sched_data = []
            for y in range(2025, 2036):
                yd = schedule.get(str(y), {})
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
            st.session_state['page'] = "➕ Add/Edit Site"  # Force navigation
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
                target_mw = st.number_input("Target Capacity (MW)*", value=site.get('target_mw', 0))
                acreage = st.number_input("Acreage*", value=site.get('acreage', 0))
                iso = st.selectbox("ISO/RTO", options=['SPP', 'ERCOT', 'PJM', 'MISO', 'CAISO', 'WECC', 'SERC', 'NYISO', 'ISO-NE'],
                                 index=['SPP', 'ERCOT', 'PJM', 'MISO', 'CAISO', 'WECC', 'SERC', 'NYISO', 'ISO-NE'].index(site.get('iso')) if site.get('iso') in ['SPP', 'ERCOT', 'PJM', 'MISO', 'CAISO', 'WECC', 'SERC', 'NYISO', 'ISO-NE'] else 0)
            with col3:
                county = st.text_input("County", value=site.get('county', ''))
                developer = st.text_input("Developer", value=site.get('developer', ''))
                land_status = st.selectbox("Land Status", options=['None', 'Option', 'Leased', 'Owned'],
                                         index=['None', 'Option', 'Leased', 'Owned'].index(site.get('land_status', 'None')))
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
                    mw = st.number_input(f"MW", key=f"p{i}_mw", value=p_data.get('mw', 0))
                    
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
                    ic_cap = st.number_input(f"IC Capacity (MW)", key=f"p{i}_ic", value=p_data.get('ic_capacity', 0))
                    voltage = st.selectbox(f"Voltage (kV)", options=['13.8', '34.5', '69', '115', '138', '230', '345', '500'], key=f"p{i}_v",
                                         index=['13.8', '34.5', '69', '115', '138', '230', '345', '500'].index(p_data.get('voltage', '138')) if p_data.get('voltage') in ['13.8', '34.5', '69', '115', '138', '230', '345', '500'] else 4)
                    service = st.selectbox(f"Service Type", options=['Transmission', 'Distribution'], key=f"p{i}_svc",
                                         index=['Transmission', 'Distribution'].index(p_data.get('service_type', 'Transmission')))
                    sub_status = st.selectbox(f"Substation", options=['Existing', 'Upgrade Needed', 'New Build'], key=f"p{i}_sub",
                                            index=['Existing', 'Upgrade Needed', 'New Build'].index(p_data.get('substation_status', 'New Build')))
                    dist = st.number_input(f"Dist. to Trans (mi)", key=f"p{i}_dist", value=p_data.get('trans_dist', 0.0))
                    
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
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("🔥 **Natural Gas**")
                gas_mw = st.number_input("Gas Capacity (MW)", value=gen.get('gas_mw', 0))
                gas_dist = st.number_input("Dist. to Pipeline (mi)", value=gen.get('gas_dist', 0.0))
                gas_status = st.selectbox("Gas Status", options=['None', 'Study', 'Permitting', 'Construction', 'Operational'],
                                        index=['None', 'Study', 'Permitting', 'Construction', 'Operational'].index(gen.get('gas_status', 'None')))
            with col2:
                st.markdown("☀️ **Solar**")
                solar_mw = st.number_input("Solar Capacity (MW)", value=gen.get('solar_mw', 0))
                solar_acres = st.number_input("Solar Acres", value=gen.get('solar_acres', 0))
            with col3:
                st.markdown("🔋 **Battery Storage**")
                batt_mw = st.number_input("BESS Power (MW)", value=gen.get('batt_mw', 0))
                batt_mwh = st.number_input("BESS Energy (MWh)", value=gen.get('batt_mwh', 0))
            
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
                water_cap = st.number_input("Water Capacity (GPD)", value=np.get('water_cap', 0))
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
