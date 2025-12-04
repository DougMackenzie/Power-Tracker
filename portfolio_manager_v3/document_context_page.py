"""
Document Context Streamlit Page
================================
UI for document monitoring, status inference, and approval workflow.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Import document context system
try:
    from document_context import (
        SiteContextManager,
        SiteDocumentManager,
        ProcessedDocument,
        StatusChangeProposal,
        DocumentIndex,
        STATUS_DETECTION_CONFIG,
    )
    CONTEXT_AVAILABLE = True
except ImportError as e:
    CONTEXT_AVAILABLE = False
    CONTEXT_ERROR = str(e)

# Import program tracker for stage labels
try:
    from program_tracker import (
        STAGE_LABELS,
        get_stage_label,
        get_stage_color,
        format_currency,
    )
except ImportError:
    STAGE_LABELS = {}
    def get_stage_label(driver, stage): return f"Stage {stage}"
    def get_stage_color(stage, max_stages=4): return "⚪"


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_context_session_state():
    """Initialize session state for document context."""
    if 'context_manager' not in st.session_state:
        st.session_state.context_manager = None
    if 'pending_proposals' not in st.session_state:
        st.session_state.pending_proposals = []
    if 'last_scan_results' not in st.session_state:
        st.session_state.last_scan_results = None
    if 'processed_docs' not in st.session_state:
        st.session_state.processed_docs = []


def get_context_manager(data_layer) -> Optional[SiteContextManager]:
    """Get or create context manager."""
    if st.session_state.context_manager is not None:
        return st.session_state.context_manager
    
    try:
        # Get credentials from secrets
        credentials_json = st.secrets.get("GOOGLE_CREDENTIALS_JSON")
        documents_folder_id = st.secrets.get("GOOGLE_DOCUMENTS_FOLDER_ID")
        
        if not credentials_json or not documents_folder_id:
            return None
        
        # Get LLM client
        llm_client = None
        use_claude = True
        
        llm_provider = st.secrets.get("LLM_PROVIDER", "gemini")
        
        if llm_provider == "claude":
            try:
                import anthropic
                api_key = st.secrets.get("ANTHROPIC_API_KEY")
                if api_key:
                    llm_client = anthropic.Anthropic(api_key=api_key)
                    use_claude = True
            except ImportError:
                pass
        else:
            try:
                import google.generativeai as genai
                api_key = st.secrets.get("GEMINI_API_KEY")
                if api_key:
                    genai.configure(api_key=api_key)
                    llm_client = genai.GenerativeModel('gemini-2.0-flash')
                    use_claude = False
            except ImportError:
                pass
        
        manager = SiteContextManager(
            credentials_json=credentials_json,
            documents_folder_id=documents_folder_id,
            llm_client=llm_client,
            use_claude=use_claude,
        )
        
        st.session_state.context_manager = manager
        return manager
    
    except Exception as e:
        st.error(f"Failed to initialize context manager: {str(e)}")
        return None


# =============================================================================
# MAIN PAGE
# =============================================================================

def show_document_context(data_layer):
    """Document Context & Status Inference page."""
    st.header("📄 Document Context")
    
    init_context_session_state()
    
    if not CONTEXT_AVAILABLE:
        st.error(f"Document context module not available: {CONTEXT_ERROR}")
        return
    
    # Check for required secrets
    has_docs_folder = bool(st.secrets.get("GOOGLE_DOCUMENTS_FOLDER_ID"))
    
    if not has_docs_folder:
        st.warning("""
        **Setup Required**
        
        To use Document Context, add these to your `.streamlit/secrets.toml`:
        
        ```toml
        # Google Drive folder for site documents
        GOOGLE_DOCUMENTS_FOLDER_ID = "your-folder-id"
        ```
        
        **Folder Structure:**
        Create a "Site Documents" folder in Google Drive, then create subfolders for each site:
        ```
        Site Documents/
        ├── rogers_county_ok/
        │   ├── meeting_notes/
        │   ├── correspondence/
        │   ├── studies/
        │   └── contracts/
        └── tulsa_metro_ok/
            └── ...
        ```
        
        Share the folder with your service account email.
        """)
        return
    
    # Get context manager
    context_manager = get_context_manager(data_layer)
    
    if not context_manager:
        st.error("Could not initialize document context manager. Check your Google credentials.")
        return
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📥 Scan & Process",
        "✅ Review Changes",
        "📁 Document Browser",
        "🔍 Site Context"
    ])
    
    # Get sites data
    sites = data_layer.get_all_sites()
    
    # =========================================================================
    # TAB 1: Scan & Process
    # =========================================================================
    with tab1:
        show_scan_tab(context_manager, sites)
    
    # =========================================================================
    # TAB 2: Review Changes (Approval Workflow)
    # =========================================================================
    with tab2:
        show_review_tab(context_manager, sites, data_layer)
    
    # =========================================================================
    # TAB 3: Document Browser
    # =========================================================================
    with tab3:
        show_browser_tab(context_manager, sites)
    
    # =========================================================================
    # TAB 4: Site Context View
    # =========================================================================
    with tab4:
        show_context_tab(context_manager, sites)


# =============================================================================
# TAB: SCAN & PROCESS
# =============================================================================

def show_scan_tab(context_manager: SiteContextManager, sites: Dict):
    """Scan for new documents and process them."""
    st.subheader("Scan for Document Changes")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        hours = st.slider(
            "Look back period (hours)",
            min_value=1,
            max_value=168,  # 1 week
            value=24,
            help="Scan for documents modified within this time period"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")
        scan_button = st.button("🔄 Scan Now", type="primary", use_container_width=True)
    
    if scan_button:
        with st.spinner("Scanning for document changes..."):
            results = context_manager.scan_and_process(
                sites_data=sites,
                since_hours=hours
            )
            st.session_state.last_scan_results = results
    
    # Show results
    if st.session_state.last_scan_results:
        results = st.session_state.last_scan_results
        
        st.divider()
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Sites Scanned", results['sites_scanned'])
        with col2:
            st.metric("Documents Found", results['documents_found'])
        with col3:
            st.metric("Processed", results['documents_processed'])
        with col4:
            st.metric("Proposals Generated", results['proposals_generated'])
        
        # Errors
        if results.get('errors'):
            st.error(f"⚠️ {len(results['errors'])} errors occurred")
            with st.expander("View Errors"):
                for err in results['errors']:
                    st.write(f"- {err}")
        
        # Details
        if results.get('details'):
            st.subheader("Processing Details")
            
            for detail in results['details']:
                with st.expander(f"📄 {detail['site_id']} / {detail['file']}"):
                    st.write(f"**Summary:** {detail.get('summary', 'No summary')}")
                    
                    if detail.get('proposals'):
                        st.success(f"✨ {detail['proposals']} status change(s) proposed")
                    
                    if detail.get('action_items'):
                        st.write("**Action Items:**")
                        for item in detail['action_items']:
                            st.write(f"  - {item}")


# =============================================================================
# TAB: REVIEW CHANGES
# =============================================================================

def show_review_tab(context_manager: SiteContextManager, sites: Dict, data_layer):
    """Review and approve/reject status change proposals."""
    st.subheader("Review Proposed Changes")
    
    pending = context_manager.get_pending_proposals()
    
    if not pending:
        st.info("No pending proposals. Run a scan to detect document changes.")
        return
    
    st.write(f"**{len(pending)} pending proposal(s)**")
    
    # Group by site
    by_site = {}
    for p in pending:
        if p.site_id not in by_site:
            by_site[p.site_id] = []
        by_site[p.site_id].append(p)
    
    for site_id, proposals in by_site.items():
        site_name = sites.get(site_id, {}).get('name', site_id)
        
        st.divider()
        st.write(f"### {site_name}")
        
        for proposal in proposals:
            show_proposal_card(proposal, context_manager, data_layer, sites)


def show_proposal_card(
    proposal: StatusChangeProposal,
    context_manager: SiteContextManager,
    data_layer,
    sites: Dict
):
    """Display a single proposal with approve/reject buttons."""
    
    # Get field display info
    field_config = STATUS_DETECTION_CONFIG.get(proposal.field, {})
    field_name = field_config.get('field_name', proposal.field)
    
    # Get stage labels
    if proposal.field == 'contract_status':
        current_label = proposal.current_value
        proposed_label = proposal.proposed_value
    else:
        current_label = get_stage_label(proposal.field.replace('_stage', ''), proposal.current_value)
        proposed_label = get_stage_label(proposal.field.replace('_stage', ''), proposal.proposed_value)
    
    # Confidence badge
    conf = proposal.confidence
    if conf >= 0.8:
        conf_badge = "🟢 High"
    elif conf >= 0.5:
        conf_badge = "🟡 Medium"
    else:
        conf_badge = "🔴 Low"
    
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.write(f"**{field_name}**: {current_label} → **{proposed_label}**")
            st.caption(f"Confidence: {conf_badge} ({conf:.0%}) | Source: {proposal.source_document} ({proposal.source_date})")
            
            with st.expander("View Evidence"):
                st.write(f"_{proposal.evidence}_")
        
        with col2:
            col_a, col_b = st.columns(2)
            
            with col_a:
                if st.button("✅", key=f"approve_{proposal.proposal_id}", help="Approve"):
                    # Approve and apply change
                    change = context_manager.approve_proposal(proposal.proposal_id)
                    if change:
                        # Update site data
                        site_data = sites.get(change['site_id'], {}).copy()
                        site_data[change['field']] = change['value']
                        
                        if data_layer.save_site(change['site_id'], site_data):
                            st.success(f"Updated {field_name}")
                            st.rerun()
                        else:
                            st.error("Failed to save")
            
            with col_b:
                if st.button("❌", key=f"reject_{proposal.proposal_id}", help="Reject"):
                    context_manager.reject_proposal(proposal.proposal_id)
                    st.rerun()


# =============================================================================
# TAB: DOCUMENT BROWSER
# =============================================================================

def show_browser_tab(context_manager: SiteContextManager, sites: Dict):
    """Browse documents by site."""
    st.subheader("Document Browser")
    
    # Site selector
    site_options = {f"{s.get('name', sid)} ({sid})": sid for sid, s in sites.items()}
    site_options = {"All Sites": None, **site_options}
    
    selected = st.selectbox("Select Site", options=list(site_options.keys()))
    site_id = site_options[selected]
    
    # Get documents
    if site_id:
        docs = context_manager.doc_index.get_site_documents(site_id)
    else:
        docs = list(context_manager.doc_index.documents.values())
    
    if not docs:
        st.info("No documents indexed yet. Run a scan to process documents.")
        return
    
    st.write(f"**{len(docs)} document(s)**")
    
    # Sort options
    sort_by = st.radio("Sort by", ["Date (newest)", "Date (oldest)", "Name"], horizontal=True)
    
    if sort_by == "Date (newest)":
        docs.sort(key=lambda d: d.modified_time or "", reverse=True)
    elif sort_by == "Date (oldest)":
        docs.sort(key=lambda d: d.modified_time or "")
    else:
        docs.sort(key=lambda d: d.file_name)
    
    # Document list
    for doc in docs:
        doc_type_icon = {
            'meeting_notes': '📝',
            'correspondence': '📧',
            'studies': '📊',
            'contracts': '📜',
            'other': '📄',
        }.get(doc.doc_type, '📄')
        
        with st.expander(f"{doc_type_icon} {doc.file_name} ({doc.modified_time[:10] if doc.modified_time else 'Unknown'})"):
            st.write(f"**Site:** {doc.site_id}")
            st.write(f"**Type:** {doc.doc_type}")
            st.write(f"**Path:** {doc.file_path}")
            st.write(f"**Processed:** {doc.processed_time[:19] if doc.processed_time else 'N/A'}")
            
            if doc.summary:
                st.write(f"**Summary:** {doc.summary}")
            
            st.divider()
            st.write("**Content Preview:**")
            st.text(doc.content_text[:2000] + ("..." if len(doc.content_text) > 2000 else ""))


# =============================================================================
# TAB: SITE CONTEXT
# =============================================================================

def show_context_tab(context_manager: SiteContextManager, sites: Dict):
    """View combined context for a site (useful for chat)."""
    st.subheader("Site Context View")
    
    st.info("This shows the combined document context that would be injected into AI chat for a site.")
    
    # Site selector
    site_options = {f"{s.get('name', sid)} ({sid})": sid for sid, s in sites.items()}
    
    if not site_options:
        st.warning("No sites available")
        return
    
    selected = st.selectbox("Select Site", options=list(site_options.keys()), key="context_site")
    site_id = site_options[selected]
    
    # Options
    max_docs = st.slider("Max documents to include", 1, 20, 5)
    
    # Get context
    context = context_manager.get_site_context(site_id, max_docs=max_docs)
    
    if not context.strip():
        st.info("No documents indexed for this site yet.")
        return
    
    # Display
    st.write(f"**Context length:** {len(context):,} characters")
    
    with st.expander("View Full Context", expanded=True):
        st.text(context)
    
    # Copy button
    st.download_button(
        "📋 Download Context",
        context,
        file_name=f"{site_id}_context.txt",
        mime="text/plain"
    )


# =============================================================================
# SETUP INSTRUCTIONS
# =============================================================================

def show_setup_instructions():
    """Show setup instructions for document context."""
    st.markdown("""
    ## Document Context Setup
    
    ### 1. Create Google Drive Folder Structure
    
    Create a folder called "Site Documents" in Google Drive with this structure:
    
    ```
    Site Documents/
    ├── rogers_county_ok/          ← Use site_id as folder name
    │   ├── meeting_notes/
    │   ├── correspondence/
    │   ├── studies/
    │   ├── contracts/
    │   └── other/
    ├── tulsa_metro_ok/
    │   └── ...
    └── ...
    ```
    
    ### 2. Share with Service Account
    
    Share the "Site Documents" folder with your service account email (Editor access).
    
    ### 3. Get Folder ID
    
    Open the folder in Google Drive and copy the ID from the URL:
    ```
    https://drive.google.com/drive/folders/[FOLDER_ID_HERE]
    ```
    
    ### 4. Add to Secrets
    
    Add to `.streamlit/secrets.toml`:
    
    ```toml
    GOOGLE_DOCUMENTS_FOLDER_ID = "your-folder-id-here"
    ```
    
    ### 5. (Recommended) Use Claude Opus for Inference
    
    For best status inference results, add Claude API key:
    
    ```toml
    LLM_PROVIDER = "claude"
    ANTHROPIC_API_KEY = "your-anthropic-api-key"
    ```
    
    ### How It Works
    
    1. **Upload documents** to site folders in Google Drive
    2. **Run a scan** from this page to detect new/modified files
    3. **AI analyzes** each document for status signals
    4. **Review proposals** and approve/reject changes
    5. **Approved changes** automatically update the tracker
    
    ### Document Types Supported
    
    - PDF (.pdf)
    - Word (.docx)
    - Text (.txt, .md)
    - CSV (.csv)
    
    ### Best Practices
    
    - Use descriptive file names: `2024-12-01_PSO_SIS_Results.pdf`
    - Put files in appropriate subfolders (meeting_notes, correspondence, etc.)
    - Run scans regularly (daily or weekly)
    - Review proposals promptly to keep tracker current
    """)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'show_document_context',
    'init_context_session_state',
    'get_context_manager',
]
