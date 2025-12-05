import streamlit as st
import graphviz

def show_system_flow():
    """
    Displays a comprehensive 'Command Center' view of the application's logic, architecture, and data flow.
    """
    st.title("🧩 Network Operations Command Center")
    st.markdown("### System Architecture & Logic Flow")
    
    # --- 1. System Status Dashboard (Command Center Feel) ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🏭 Active Sites", f"{len(st.session_state.db.get('sites', {}))}", delta="Live Database")
    with col2:
        st.metric("🤖 AI Agents", "3 Active", delta="Research, VDR, Profiler")
    with col3:
        st.metric("📊 Program Tracker", "Integrated", delta="Fee & Prob. Logic")
    with col4:
        st.metric("📤 Export Modules", "PPTX / PDF", delta="Ready")
        
    st.divider()

    # --- 2. Comprehensive Network Diagram ---
    st.subheader("🕸️ Structural Framework & Data Flow")
    
    # Create a complex graphviz directed graph
    graph = graphviz.Digraph()
    graph.attr(rankdir='LR')
    graph.attr('node', shape='box', style='filled, rounded', fontname='Helvetica', fontsize='10')
    graph.attr('edge', fontname='Helvetica', fontsize='9')
    
    # -- Cluster: INPUTS --
    with graph.subgraph(name='cluster_inputs') as c:
        c.attr(label='INPUT SOURCES', style='dashed', color='#90caf9', bgcolor='#e3f2fd')
        c.node('HumanInput', '👤 Human Input\n(Forms & Knowledge)', fillcolor='#bbdefb')
        c.node('AIChat', '💬 AI Chat\n(New Site Gen)', fillcolor='#bbdefb')
        c.node('VDR', '📁 VDR Upload\n(PDF/Excel Parsing)', fillcolor='#bbdefb')
        c.node('UtilityAgent', '🕷️ Utility Agent\n(Web Scraping)', fillcolor='#bbdefb')
        c.node('MacroResearch', '🔬 Macro Research\n(Supply/Demand)', fillcolor='#bbdefb')

    # -- Cluster: CORE DATA --
    with graph.subgraph(name='cluster_data') as c:
        c.attr(label='CORE DATA LAYER', style='dashed', color='#a5d6a7', bgcolor='#e8f5e9')
        c.node('SiteDB', '🏭 Site Database\n(Google Sheets)', fillcolor='#c8e6c9', shape='cylinder')
        c.node('StateDB', '🗺️ State Database\n(Policy/Tax/Cost)', fillcolor='#c8e6c9', shape='cylinder')
        c.node('ProfileData', '📝 Site Profile\n(Structured + JSON)', fillcolor='#c8e6c9')

    # -- Cluster: LOGIC ENGINE --
    with graph.subgraph(name='cluster_logic') as c:
        c.attr(label='LOGIC & PROCESSING', style='dashed', color='#ffe082', bgcolor='#fff8e1')
        c.node('Scoring', '⭐ Scoring Engine\n(State*Power*Exec)', fillcolor='#ffecb3')
        c.node('ProgramLogic', '📈 Program Tracker\n(Prob. & Fees)', fillcolor='#ffecb3')
        c.node('GapAnalysis', '⚖️ Gap Analysis\n(Supply vs Demand)', fillcolor='#ffecb3')
        c.node('ProfileBuilder', '🏗️ Profile Builder\n(Merge Sources)', fillcolor='#ffecb3')

    # -- Cluster: OUTPUTS --
    with graph.subgraph(name='cluster_outputs') as c:
        c.attr(label='OUTPUTS & VISUALIZATION', style='dashed', color='#f48fb1', bgcolor='#fce4ec')
        c.node('Dashboard', '📊 Main Dashboard\n(KPIs & Maps)', fillcolor='#f8bbd0')
        c.node('PPTX', '📽️ PPT Export\n(Slide Generation)', fillcolor='#f8bbd0')
        c.node('Rankings', '🏆 Rankings View\n(Weighted Lists)', fillcolor='#f8bbd0')
        c.node('PDFReport', '📄 PDF Reports\n(Site Summaries)', fillcolor='#f8bbd0')

    # -- EDGES (Connections) --
    # Inputs -> Logic/Data
    graph.edge('HumanInput', 'SiteDB', label=' manual entry')
    graph.edge('AIChat', 'SiteDB', label=' creates sites')
    graph.edge('VDR', 'ProfileBuilder', label=' extracts data')
    graph.edge('UtilityAgent', 'StateDB', label=' updates IRPs')
    graph.edge('MacroResearch', 'GapAnalysis', label=' demand curves')
    
    # Logic <-> Data
    graph.edge('SiteDB', 'ProfileBuilder', label=' raw data')
    graph.edge('ProfileBuilder', 'ProfileData', label=' structured obj')
    graph.edge('ProfileData', 'Scoring', label=' attributes')
    graph.edge('StateDB', 'Scoring', label=' multipliers')
    graph.edge('SiteDB', 'ProgramLogic', label=' stage gates')
    graph.edge('ProgramLogic', 'SiteDB', label=' probability')
    
    # Logic -> Outputs
    graph.edge('Scoring', 'Rankings', label=' scores')
    graph.edge('GapAnalysis', 'Dashboard', label=' market context')
    graph.edge('ProfileData', 'PPTX', label=' slide content')
    graph.edge('ProfileData', 'PDFReport', label=' report content')
    graph.edge('ProgramLogic', 'Dashboard', label=' portfolio stats')
    
    st.graphviz_chart(graph, use_container_width=True)

    st.divider()

    # --- 3. Interactive Deep Dive (Command Center Controls) ---
    st.subheader("🔍 System Component Inspector")
    
    tabs = st.tabs([
        "👤 Human & AI Inputs", 
        "💾 Core Data Architecture", 
        "⚙️ Logic & Processing", 
        "📤 Outputs & Reporting"
    ])

    with tabs[0]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 👤 Human Input")
            st.info("""
            **Role**: The primary source of truth for deal-specific nuances.
            - **Forms**: `site_profile_builder.py` generates dynamic forms for Ownership, Utilities, and Risks.
            - **Overrides**: Human input always takes precedence over AI/Scraped data.
            - **Fields**: Captures soft data like "Willingness to Sell" or "Political Support".
            """)
        with col2:
            st.markdown("#### 🤖 AI & VDR Agents")
            st.info("""
            **Role**: Automation of data entry and research.
            - **VDR Processor**: Ingests PDFs, uses OCR + LLM to extract 40+ fields (Phases, CapEx).
            - **Utility Agent**: Scrapes ISO/Utility sites for Queue data and Tariffs.
            - **Chat Bot**: Can instantiate new site objects directly from conversation.
            """)

    with tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🏭 Site Database")
            st.info("""
            **Architecture**: Hybrid SQL-like + NoSQL.
            - **Storage**: Google Sheets (for easy access/backup).
            - **Schema**: 
                - Fixed Columns: ID, Name, MW, State (for fast filtering).
                - JSON Blobs: `phases_json`, `risks_json` (for flexible, nested data).
            """)
        with col2:
            st.markdown("#### 📝 Site Profile Object")
            st.info("""
            **Role**: The unified data model (`SiteProfileData`).
            - **Purpose**: Decouples the UI/Export logic from the raw database storage.
            - **Builder Pattern**: `SiteProfileBuilder` merges DB data + AI Research + Human Input into this single object.
            """)

    with tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### ⭐ Scoring Engine")
            st.info("""
            **Logic**: Multi-factor weighted algorithm.
            - **Formula**: `(State * 20%) + (Power * 25%) + (Exec * 15%) ...`
            - **Dynamic**: Weights can be adjusted in real-time via the Rankings page.
            - **Context**: Pulls state-level data (Tax, Energy Cost) to baseline the site score.
            """)
        with col2:
            st.markdown("#### 📈 Program Tracker")
            st.info("""
            **Logic**: Probability & Fee Management.
            - **Probability**: Calculated based on completed "Stage Gates" (Site Control, Power, Zoning).
            - **Weighted Fee**: `Total Fee Potential * Probability`.
            - **Drivers**: Configurable weights for each stage (e.g., Power > Zoning).
            """)

    with tabs[3]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 📽️ PPT Export")
            st.info("""
            **Engine**: `python-pptx` based generator.
            - **Template**: Uses a corporate master slide deck.
            - **Mapping**: Maps `SiteProfileData` fields to specific placeholders on Slides 2, 6, 8.
            - **Charts**: Generates native PowerPoint charts for Load Ramps and Scoring Radar.
            """)
        with col2:
            st.markdown("#### 📊 Dashboard & Reports")
            st.info("""
            **Visualization**: Streamlit + Plotly.
            - **Maps**: Geospatial scatter plots of sites vs. substations.
            - **PDFs**: `fpdf2` generates quick 1-pagers for internal review.
            - **Rankings**: Interactive data tables with progress bars for scores.
            """)

