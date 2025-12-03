"""
Powered Land Portfolio Manager - LLM Enhanced
==============================================
Uses Google Sheets as backend + LLM-powered diagnostic chat.

Setup:
1. pip install streamlit pandas plotly google-api-python-client google-auth google-generativeai anthropic PyPDF2 python-docx openpyxl
2. Configure .streamlit/secrets.toml (see GOOGLE_SETUP.md)
3. streamlit run streamlit_llm.py
"""

import streamlit as st
import pandas as pd
import json
import os
import tempfile
import re
from datetime import datetime
from typing import Dict, List, Optional
import plotly.express as px
import plotly.graph_objects as go

# Import modules
from state_analysis import (
    STATE_PROFILES, get_state_profile, generate_state_context_section,
    compare_states, generate_utility_research_queries
)
from document_extraction import (
    process_vdr_upload, extraction_result_to_site_data, parse_conversational_input
)

# Google integration
try:
    from google_integration import (
        GoogleSheetsClient, get_google_client, 
        map_app_to_sheet, map_sheet_to_app,
        GOOGLE_APIS_AVAILABLE
    )
except ImportError:
    GOOGLE_APIS_AVAILABLE = False

# LLM integration
try:
    from llm_integration import PortfolioChat, get_chat_client, refresh_chat_context
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


# =============================================================================
# DATA LAYER
# =============================================================================

class DataLayer:
    """Unified data access layer."""
    
    def __init__(self):
        self.use_google = False
        self.google_client = None
        self.local_db = {'sites': {}, 'metadata': {}}
        
        if GOOGLE_APIS_AVAILABLE:
            try:
                self.google_client = GoogleSheetsClient()
                self.use_google = True
            except Exception as e:
                st.sidebar.warning(f"⚠️ Local mode: {str(e)[:40]}")
    
    def get_all_sites(self) -> Dict[str, Dict]:
        if self.use_google:
            sites_list = self.google_client.get_all_sites()
            return {s.get('site_id', f'site_{i}'): map_sheet_to_app(s) for i, s in enumerate(sites_list)}
        return self.local_db.get('sites', {})
    
    def get_site(self, site_id: str) -> Optional[Dict]:
        if self.use_google:
            sheet_site = self.google_client.get_site(site_id)
            return map_sheet_to_app(sheet_site) if sheet_site else None
        return self.local_db.get('sites', {}).get(site_id)
    
    def save_site(self, site_id: str, site_data: Dict) -> bool:
        site_data['site_id'] = site_id
        if self.use_google:
            sheet_data = map_app_to_sheet(site_data)
            sheet_data['site_id'] = site_id
            existing = self.google_client.find_site_row(site_id)
            if existing:
                return self.google_client.update_site(site_id, sheet_data)
            return self.google_client.add_site(sheet_data)
        else:
            site_data['last_updated'] = datetime.now().isoformat()
            self.local_db.setdefault('sites', {})[site_id] = site_data
            return True
    
    def delete_site(self, site_id: str) -> bool:
        if self.use_google:
            return self.google_client.delete_site(site_id)
        if site_id in self.local_db.get('sites', {}):
            del self.local_db['sites'][site_id]
            return True
        return False
    
    def upload_vdr(self, zip_content: bytes, site_id: str, site_name: str) -> Dict:
        if self.use_google:
            return self.google_client.upload_vdr_zip(zip_content, site_id, site_name)
        return {'info': 'Files processed locally only'}
    
    def get_site_files(self, site_id: str, site_name: str) -> List[Dict]:
        if self.use_google:
            folder_id = self.google_client.get_or_create_site_folder(site_id, site_name)
            if folder_id:
                return self.google_client.list_site_files(folder_id)
        return []


# =============================================================================
# SCORING
# =============================================================================

def calculate_site_score(site: Dict, weights: Dict) -> Dict:
    state_profile = get_state_profile(site.get('state', ''))
    state_score = state_profile.overall_score if state_profile else 50
    
    power_score = 0
    study_scores = {'ia_executed': 40, 'fa_executed': 35, 'fs_complete': 28, 'sis_complete': 20, 'sis_in_progress': 12, 'sis_requested': 8, 'not_started': 0}
    power_score += study_scores.get(site.get('study_status', 'not_started'), 0)
    commitment_scores = {'committed': 25, 'verbal': 18, 'engaged': 12, 'initial': 5, 'none': 0}
    power_score += commitment_scores.get(site.get('utility_commitment', 'none'), 0)
    timeline = site.get('power_timeline_months', 60)
    if timeline <= 24: power_score += 20
    elif timeline <= 36: power_score += 15
    elif timeline <= 48: power_score += 10
    power_score = min(power_score + 15, 100)
    
    rel_score = 0
    community_scores = {'champion': 40, 'Strong Support': 35, 'supportive': 30, 'Partial': 20, 'neutral': 15, 'concerns': 5, 'opposition': 0}
    rel_score += community_scores.get(site.get('community_support', 'neutral'), 15)
    political_scores = {'strong': 30, 'Strong Support': 30, 'supportive': 25, 'Partial': 15, 'neutral': 10, 'concerns': 5, 'opposition': 0}
    rel_score += political_scores.get(site.get('political_support', 'neutral'), 10)
    dev_scores = {'extensive': 30, 'High': 30, 'proven': 25, 'Medium': 20, 'limited': 10, 'Low': 5, 'none': 0}
    rel_score += dev_scores.get(site.get('developer_track_record', 'none'), 0)
    rel_score = min(rel_score, 100)
    
    fund_score = 0
    land_scores = {'owned': 35, 'Secured': 35, 'option': 28, 'Development On Partial': 20, 'loi': 18, 'negotiating': 8, 'none': 0}
    fund_score += land_scores.get(site.get('land_control', 'none'), 0)
    capital_scores = {'strong': 35, 'Strong': 35, 'committed': 28, 'Partial': 20, 'available': 18, 'Moderate': 15, 'developing': 8, 'limited': 0}
    fund_score += capital_scores.get(site.get('capital_access', 'limited'), 0)
    fund_score = min(fund_score + 30, 100)
    
    weighted = (
        state_score * weights.get('state', 0.20) +
        power_score * weights.get('power', 0.25) +
        rel_score * weights.get('relationship', 0.25) +
        fund_score * weights.get('fundamentals', 0.30)
    )
    
    return {
        'overall_score': round(weighted, 1),
        'state_score': state_score,
        'power_score': round(power_score, 1),
        'relationship_score': round(rel_score, 1),
        'fundamentals_score': round(fund_score, 1)
    }


def determine_stage(site: Dict) -> str:
    financial = site.get('financial_status', site.get('end_user_status', ''))
    if financial in ['term_sheet', 'loi', 'Strong']: return 'End-User Attached'
    study = site.get('study_status', '')
    if study in ['ia_executed', 'fa_executed']: return 'Fully Entitled'
    commitment = site.get('utility_commitment', '')
    if commitment == 'committed': return 'Utility Commitment'
    if study in ['sis_in_progress', 'sis_complete', 'fs_complete']: return 'Study In Progress'
    land = site.get('land_control', '')
    if land in ['owned', 'option', 'Secured', 'Development On Partial']: return 'Early Real'
    return 'Pre-Development'


# =============================================================================
# MAIN APP
# =============================================================================

def main():
    st.set_page_config(page_title="Powered Land Portfolio Manager", page_icon="⚡", layout="wide")
    
    # Initialize
    if 'data' not in st.session_state:
        st.session_state.data = DataLayer()
    if 'weights' not in st.session_state:
        st.session_state.weights = {'state': 0.20, 'power': 0.25, 'relationship': 0.25, 'fundamentals': 0.30}
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    if 'pending_site' not in st.session_state:
        st.session_state.pending_site = None
    
    # Sidebar
    st.sidebar.title("⚡ Portfolio Manager")
    
    # Connection status
    if st.session_state.data.use_google:
        st.sidebar.success("✅ Google Sheets")
    else:
        st.sidebar.info("📁 Local Mode")
    
    # LLM status
    if LLM_AVAILABLE:
        try:
            provider = st.secrets.get("LLM_PROVIDER", "gemini")
            st.sidebar.success(f"🤖 {provider.title()} AI")
        except:
            st.sidebar.warning("🤖 LLM: No API key")
    else:
        st.sidebar.warning("🤖 LLM: Not installed")
    
    page = st.sidebar.radio(
        "Navigation",
        ["📊 Dashboard", "💬 AI Chat", "📁 VDR Upload", "🏭 Site Database",
         "➕ Add/Edit Site", "🏆 Rankings", "🗺️ State Analysis", "⚙️ Settings"]
    )
    
    if page == "📊 Dashboard": show_dashboard()
    elif page == "💬 AI Chat": show_ai_chat()
    elif page == "📁 VDR Upload": show_vdr_upload()
    elif page == "🏭 Site Database": show_site_database()
    elif page == "➕ Add/Edit Site": show_add_edit_site()
    elif page == "🏆 Rankings": show_rankings()
    elif page == "🗺️ State Analysis": show_state_analysis()
    elif page == "⚙️ Settings": show_settings()


# =============================================================================
# AI CHAT PAGE
# =============================================================================

def show_ai_chat():
    """LLM-powered diagnostic chat."""
    st.title("💬 AI Site Diagnostic Chat")
    
    # Check LLM availability
    if not LLM_AVAILABLE:
        st.error("LLM integration not available. Install: `pip install google-generativeai anthropic`")
        return
    
    # Initialize chat client
    try:
        provider = st.secrets.get("LLM_PROVIDER", "gemini")
        api_key = st.secrets.get(f"{'GEMINI' if provider == 'gemini' else 'ANTHROPIC'}_API_KEY")
        
        if not api_key:
            st.error(f"No API key found. Add {'GEMINI_API_KEY' if provider == 'gemini' else 'ANTHROPIC_API_KEY'} to secrets.toml")
            st.markdown("""
            ```toml
            LLM_PROVIDER = "gemini"  # or "claude"
            GEMINI_API_KEY = "your-key-here"
            ```
            """)
            return
        
        if 'chat_client' not in st.session_state:
            st.session_state.chat_client = PortfolioChat(provider=provider, api_key=api_key)
            # Load portfolio context
            sites = st.session_state.data.get_all_sites()
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
        - Help you populate the database
        
        **Commands:**
        - "Save this site" - Extract data and add to database
        - "Compare to [site name]" - Compare against existing site
        - "What's missing?" - Identify information gaps
        """)
    
    # Chat interface
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
                    
                    # Check if response suggests saving a site
                    if "save" in prompt.lower() or "add to database" in prompt.lower():
                        # Try to extract site data
                        extracted = extract_site_from_conversation(st.session_state.chat_messages)
                        if extracted:
                            st.session_state.pending_site = extracted
                            
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    # Sidebar controls
    st.sidebar.markdown("---")
    st.sidebar.subheader("Chat Controls")
    
    if st.sidebar.button("🔄 Refresh Context"):
        sites = st.session_state.data.get_all_sites()
        st.session_state.chat_client.set_portfolio_context(sites)
        st.sidebar.success("Context refreshed!")
    
    if st.sidebar.button("🗑️ Clear History"):
        st.session_state.chat_messages = []
        st.session_state.chat_client.clear_history()
        st.rerun()
    
    # Pending site save
    if st.session_state.pending_site:
        st.markdown("---")
        st.subheader("📋 Save Extracted Site")
        show_site_save_form(st.session_state.pending_site)


def extract_site_from_conversation(messages: List[Dict]) -> Optional[Dict]:
    """Extract site data from conversation history."""
    # Combine all messages
    full_text = " ".join([m["content"] for m in messages])
    
    extracted = {}
    
    # State
    state_match = re.search(r'\b(OK|TX|GA|VA|OH|IN|PA|NV|CA|WY|Oklahoma|Texas|Georgia|Virginia|Ohio|Indiana|Pennsylvania|Nevada|California|Wyoming)\b', full_text, re.IGNORECASE)
    if state_match:
        state = state_match.group(1).upper()
        state_map = {'OKLAHOMA': 'OK', 'TEXAS': 'TX', 'GEORGIA': 'GA', 'VIRGINIA': 'VA', 
                     'OHIO': 'OH', 'INDIANA': 'IN', 'PENNSYLVANIA': 'PA', 'NEVADA': 'NV',
                     'CALIFORNIA': 'CA', 'WYOMING': 'WY'}
        extracted['state'] = state_map.get(state, state)
    
    # MW
    mw_match = re.search(r'(\d+)\s*MW', full_text, re.IGNORECASE)
    if mw_match:
        extracted['target_mw'] = int(mw_match.group(1))
    
    # Utility
    utilities = ['PSO', 'AEP', 'OG&E', 'ONCOR', 'Georgia Power', 'Dominion', 'Duke', 'AES']
    for util in utilities:
        if util.lower() in full_text.lower():
            extracted['utility'] = util
            break
    
    # Study status
    if 'ia executed' in full_text.lower() or 'interconnection agreement' in full_text.lower():
        extracted['study_status'] = 'ia_executed'
    elif 'fa executed' in full_text.lower() or 'facilities agreement' in full_text.lower():
        extracted['study_status'] = 'fa_executed'
    elif 'fs complete' in full_text.lower() or 'facilities study complete' in full_text.lower():
        extracted['study_status'] = 'fs_complete'
    elif 'sis complete' in full_text.lower():
        extracted['study_status'] = 'sis_complete'
    elif 'sis in progress' in full_text.lower() or 'sis underway' in full_text.lower():
        extracted['study_status'] = 'sis_in_progress'
    
    # Land control
    if 'owned' in full_text.lower() or 'own the land' in full_text.lower():
        extracted['land_control'] = 'owned'
    elif 'option' in full_text.lower() or 'under option' in full_text.lower():
        extracted['land_control'] = 'option'
    elif 'loi' in full_text.lower():
        extracted['land_control'] = 'loi'
    
    return extracted if extracted else None


def show_site_save_form(extracted: Dict):
    """Show form to save extracted site data."""
    col1, col2 = st.columns(2)
    
    with col1:
        name = st.text_input("Site Name*", key="save_name")
        state = st.selectbox("State", [''] + list(STATE_PROFILES.keys()),
            index=([''] + list(STATE_PROFILES.keys())).index(extracted.get('state', '')) if extracted.get('state') in STATE_PROFILES else 0,
            key="save_state")
        utility = st.text_input("Utility", value=extracted.get('utility', ''), key="save_util")
        target_mw = st.number_input("Target MW", value=extracted.get('target_mw', 0), key="save_mw")
    
    with col2:
        study_options = ['not_started', 'sis_requested', 'sis_in_progress', 'sis_complete', 'fs_complete', 'fa_executed', 'ia_executed']
        study = st.selectbox("Study Status", study_options,
            index=study_options.index(extracted.get('study_status', 'not_started')) if extracted.get('study_status') in study_options else 0,
            key="save_study")
        land_options = ['none', 'negotiating', 'loi', 'option', 'owned']
        land = st.selectbox("Land Control", land_options,
            index=land_options.index(extracted.get('land_control', 'none')) if extracted.get('land_control') in land_options else 0,
            key="save_land")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💾 Save Site", type="primary"):
            if name and state:
                site_id = name.lower().replace(' ', '_').replace('-', '_')
                site_data = {
                    'name': name, 'state': state, 'utility': utility, 'target_mw': target_mw,
                    'study_status': study, 'land_control': land, 'source': 'ai_chat'
                }
                if st.session_state.data.save_site(site_id, site_data):
                    st.success(f"✅ Saved '{name}'!")
                    st.session_state.pending_site = None
                    # Refresh chat context
                    sites = st.session_state.data.get_all_sites()
                    st.session_state.chat_client.set_portfolio_context(sites)
                    st.rerun()
            else:
                st.error("Name and State required")
    with col2:
        if st.button("❌ Cancel"):
            st.session_state.pending_site = None
            st.rerun()


# =============================================================================
# OTHER PAGES (Same as before, condensed)
# =============================================================================

def show_dashboard():
    st.title("📊 Portfolio Dashboard")
    sites = st.session_state.data.get_all_sites()
    
    if not sites:
        st.info("No sites yet. Use **AI Chat** or **VDR Upload** to add sites.")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    total_mw = sum(s.get('target_mw', 0) for s in sites.values())
    avg_score = sum(calculate_site_score(s, st.session_state.weights)['overall_score'] for s in sites.values()) / len(sites)
    col1.metric("Sites", len(sites))
    col2.metric("Pipeline MW", f"{total_mw:,}")
    col3.metric("Avg Score", f"{avg_score:.1f}")
    col4.metric("States", len(set(s.get('state') for s in sites.values() if s.get('state'))))
    
    st.markdown("---")
    
    data = []
    for site_id, site in sites.items():
        scores = calculate_site_score(site, st.session_state.weights)
        data.append({
            'Site': site.get('name', site_id), 'State': site.get('state', ''),
            'Utility': site.get('utility', ''), 'MW': site.get('target_mw', 0),
            'Stage': determine_stage(site), 'Score': scores['overall_score']
        })
    
    df = pd.DataFrame(sorted(data, key=lambda x: x['Score'], reverse=True))
    st.dataframe(df, column_config={'Score': st.column_config.ProgressColumn(min_value=0, max_value=100)},
                 hide_index=True, use_container_width=True)


def show_vdr_upload():
    st.title("📁 VDR Document Upload")
    
    if st.session_state.data.use_google:
        st.success("✅ Files upload to Google Drive")
    
    uploaded = st.file_uploader("Upload VDR (zip)", type=['zip'])
    
    if uploaded and st.button("🔍 Process"):
        with st.spinner("Processing..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
                tmp.write(uploaded.getvalue())
                tmp_path = tmp.name
            try:
                result = process_vdr_upload(tmp_path)
                st.session_state.vdr_result = result
                st.success(f"✅ Processed {result.processed_files} files")
            finally:
                os.unlink(tmp_path)
    
    if 'vdr_result' in st.session_state and st.session_state.vdr_result:
        result = st.session_state.vdr_result
        st.write(f"**State:** {result.state} | **Utility:** {result.utility} | **MW:** {result.target_mw}")
        
        name = st.text_input("Site Name", "VDR Import")
        if st.button("💾 Save"):
            site_id = name.lower().replace(' ', '_')
            site_data = {'name': name, 'state': result.state, 'utility': result.utility,
                        'target_mw': result.target_mw, 'source': 'vdr_import'}
            if st.session_state.data.save_site(site_id, site_data):
                st.success("Saved!")
                st.session_state.vdr_result = None


def show_site_database():
    st.title("🏭 Site Database")
    sites = st.session_state.data.get_all_sites()
    
    if not sites:
        st.info("No sites")
        return
    
    data = []
    for site_id, site in sites.items():
        scores = calculate_site_score(site, st.session_state.weights)
        data.append({'id': site_id, 'Site': site.get('name', site_id), 'State': site.get('state', ''),
                     'MW': site.get('target_mw', 0), 'Stage': determine_stage(site), 'Score': scores['overall_score']})
    
    st.dataframe(pd.DataFrame(data)[['Site', 'State', 'MW', 'Stage', 'Score']],
                 column_config={'Score': st.column_config.ProgressColumn(min_value=0, max_value=100)},
                 hide_index=True, use_container_width=True)


def show_add_edit_site():
    st.title("➕ Add/Edit Site")
    
    with st.form("site_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input("Site Name*")
            state = st.selectbox("State*", [''] + list(STATE_PROFILES.keys()))
            utility = st.text_input("Utility*")
        with col2:
            target_mw = st.number_input("Target MW*", value=0)
            study = st.selectbox("Study Status", ['not_started', 'sis_requested', 'sis_in_progress', 'sis_complete', 'fs_complete', 'fa_executed', 'ia_executed'])
            land = st.selectbox("Land Control", ['none', 'negotiating', 'loi', 'option', 'owned'])
        with col3:
            community = st.selectbox("Community Support", ['opposition', 'concerns', 'neutral', 'supportive', 'champion'])
            capital = st.selectbox("Capital Status", ['limited', 'developing', 'available', 'committed', 'strong'])
        
        if st.form_submit_button("💾 Save", type="primary"):
            if name and state:
                site_id = name.lower().replace(' ', '_')
                site_data = {'name': name, 'state': state, 'utility': utility, 'target_mw': target_mw,
                            'study_status': study, 'land_control': land, 'community_support': community,
                            'capital_access': capital, 'source': 'manual'}
                if st.session_state.data.save_site(site_id, site_data):
                    st.success(f"Saved '{name}'!")


def show_rankings():
    st.title("🏆 Rankings")
    sites = st.session_state.data.get_all_sites()
    if not sites:
        st.info("No sites")
        return
    
    rankings = []
    for site_id, site in sites.items():
        scores = calculate_site_score(site, st.session_state.weights)
        rankings.append({'Rank': 0, 'Site': site.get('name', site_id), 'State': site.get('state', ''),
                        'MW': site.get('target_mw', 0), 'Score': scores['overall_score']})
    
    rankings.sort(key=lambda x: x['Score'], reverse=True)
    for i, r in enumerate(rankings):
        r['Rank'] = i + 1
    
    st.dataframe(pd.DataFrame(rankings), column_config={'Score': st.column_config.ProgressColumn(min_value=0, max_value=100)},
                 hide_index=True, use_container_width=True)


def show_state_analysis():
    st.title("🗺️ State Analysis")
    selected = st.multiselect("Compare States", list(STATE_PROFILES.keys()), default=['OK', 'TX', 'GA'])
    
    if selected:
        comparisons = compare_states(selected)
        cats = ['Regulatory', 'Transmission', 'Power', 'Water', 'Business', 'Ecosystem']
        fig = go.Figure()
        for s in comparisons:
            vals = [s['regulatory'], s['transmission'], s['power'], s['water'], s['business'], s['ecosystem'], s['regulatory']]
            fig.add_trace(go.Scatterpolar(r=vals, theta=cats + [cats[0]], name=s['name']))
        fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100])), height=500)
        st.plotly_chart(fig, use_container_width=True)


def show_settings():
    st.title("⚙️ Settings")
    
    st.subheader("Connection Status")
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.data.use_google:
            st.success("✅ Google Sheets connected")
        else:
            st.warning("⚠️ Local mode")
    with col2:
        if LLM_AVAILABLE:
            try:
                provider = st.secrets.get("LLM_PROVIDER", "gemini")
                st.success(f"✅ {provider.title()} AI connected")
            except:
                st.warning("⚠️ No LLM API key")
        else:
            st.warning("⚠️ LLM not installed")
    
    st.subheader("Configuration")
    st.markdown("""
    **Required secrets** (`.streamlit/secrets.toml`):
    ```toml
    # Google Sheets
    GOOGLE_SHEET_ID = "your-sheet-id"
    GOOGLE_VDR_FOLDER_ID = "your-folder-id"
    GOOGLE_CREDENTIALS_JSON = '''{"type": "service_account", ...}'''
    
    # LLM (choose one)
    LLM_PROVIDER = "gemini"  # or "claude"
    GEMINI_API_KEY = "your-gemini-key"
    # ANTHROPIC_API_KEY = "your-claude-key"
    ```
    """)
    
    if st.button("🔄 Refresh"):
        st.session_state.data = DataLayer()
        st.rerun()


if __name__ == "__main__":
    main()
