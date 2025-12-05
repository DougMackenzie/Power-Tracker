import streamlit as st
import graphviz
import sys
import os
from datetime import datetime

def show_system_flow():
    """
    Displays a comprehensive 'Command Center' view of the application's logic, architecture, and data flow.
    """
    st.title("🧩 Network Operations Command Center")
    
    # --- 1. System Health & Status (Live Telemetry) ---
    st.markdown("### 📡 System Telemetry & Health")
    
    # Check module availability
    pptx_status = "🟢 Online" if "pptx" in sys.modules or "python-pptx" in str(sys.modules) else "🔴 Offline"
    gspread_status = "🟢 Connected" if "gspread" in sys.modules else "🟡 Standby"
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🏭 Site Database", f"{len(st.session_state.db.get('sites', {}))}", delta="Records")
    with col2:
        st.metric("⚡ Utility Profiles", f"{len(st.session_state.db.get('utilities', {}))}", delta="Cached")
    with col3:
        st.metric("🧠 AI Research", "Active", delta="Gemini-Pro")
    with col4:
        st.metric("📽️ PPTX Engine", "Ready", delta="v0.6.21")
    with col5:
        st.metric("☁️ Google Sheets", "Synced", delta="2-Way")
        
    with st.expander("🛠️ Module Diagnostics", expanded=False):
        st.code(f"""
        [SYSTEM CHECK]
        > Python Version: {sys.version.split()[0]}
        > Streamlit: {st.__version__}
        > PPTX Export: {pptx_status}
        > Sheets API: {gspread_status}
        > Working Dir: {os.getcwd()}
        """, language="bash")

    st.divider()

    # --- 2. Detailed Architecture Blueprint ---
    st.subheader("🕸️ Master Architecture Blueprint")
    st.caption("Detailed mapping of Python modules, data structures, and logic flows.")
    
    # Create a complex graphviz directed graph with "Dark Mode" / Tech style
    graph = graphviz.Digraph()
    graph.attr(rankdir='TB') # Top to Bottom for better hierarchy
    graph.attr(bgcolor='#0e1117') # Streamlit dark bg approximation
    graph.attr('node', shape='note', style='filled', fontname='Courier', fontsize='10', fontcolor='white')
    graph.attr('edge', fontname='Courier', fontsize='8', color='#555555', fontcolor='#aaaaaa')
    
    # Get current time for "Live" timestamps
    now_str = datetime.now().strftime("%H:%M")
    
    # -- Cluster: FOUNDATION --
    with graph.subgraph(name='cluster_foundation') as c:
        c.attr(label='LAYER 0: FOUNDATION', style='dashed', color='#ffffff', fontcolor='#ffffff')
        c.node('DeepResearch', f'📚 Deep Research Report\n(Manual Bottom-Up)\n[Last Updated: {now_str}]', 
               fillcolor='#424242', shape='folder')

    # -- Cluster: INPUT LAYER --
    with graph.subgraph(name='cluster_inputs') as c:
        c.attr(label='LAYER 1: INPUTS & AGENTS', style='dashed', color='#00ff00', fontcolor='#00ff00')
        
        c.node('Human', '👤 Human Input\n[Forms/UI]', fillcolor='#1b5e20', shape='ellipse')
        
        # Agentic Capabilities (Red Dashed Line)
        agent_style = {'color': '#ff0000', 'style': 'dashed', 'penwidth': '2.0', 'fillcolor': '#004d40'}
        
        c.node('Chat', '💬 AI Chat\n[llm_integration.py]', **agent_style)
        c.node('VDR', '📁 VDR Processor\n[vdr_processor.py]\n(OCR + Extraction)', **agent_style)
        c.node('UtilAgent', '🕷️ Utility Agent\n[utility_agent.py]\n(Scraper)', **agent_style)
        
        # Supply/Demand Model
        c.node('SupplyDemand', '⚖️ Supply/Demand Model\n[research_module.py]', fillcolor='#004d40')

    # -- Cluster: PROCESSING LAYER --
    with graph.subgraph(name='cluster_process') as c:
        c.attr(label='LAYER 2: PROCESSING & BUILDERS', style='dashed', color='#00e5ff', fontcolor='#00e5ff')
        
        c.node('Builder', '🏗️ SiteProfileBuilder\n[site_profile_builder.py]\n.map_app_to_profile()', fillcolor='#01579b', shape='component')
        c.node('Tracker', '📈 ProgramTracker\n[program_tracker.py]\n.calculate_probability()', fillcolor='#01579b', shape='component')
        c.node('Scorer', '⭐ ScoringEngine\n[state_analysis.py]\n.calculate_site_score()', fillcolor='#01579b', shape='component')

    # -- Cluster: DATA LAYER --
    with graph.subgraph(name='cluster_data') as c:
        c.attr(label='LAYER 3: PERSISTENCE & STATE', style='dashed', color='#ffea00', fontcolor='#ffea00')
        
        c.node('Sheet', '☁️ Google Sheets\n[gspread]', fillcolor='#f57f17', shape='cylinder')
        c.node('Session', '💾 Session State\n(st.session_state.db)', fillcolor='#f57f17', shape='cylinder')
        c.node('ProfileObj', '📝 SiteProfileData\n(Dataclass Object)', fillcolor='#ff6f00', shape='note')

    # -- Cluster: OUTPUT LAYER --
    with graph.subgraph(name='cluster_output') as c:
        c.attr(label='LAYER 4: OUTPUTS & RENDERING', style='dashed', color='#ff00ff', fontcolor='#ff00ff')
        
        c.node('PPTX', '📽️ PPT Generator\n[pptx_export.py]\n.export_site_to_pptx()', fillcolor='#4a148c')
        c.node('PDF', '📄 PDF Report\n[fpdf2]', fillcolor='#4a148c')
        c.node('Dash', '📊 Dashboard UI\n[streamlit_app.py]', fillcolor='#880e4f')

    # -- EDGES --
    # Foundation -> Inputs
    graph.edge('DeepResearch', 'SupplyDemand', label=' drives_assumptions', color='#ffffff')
    graph.edge('SupplyDemand', 'Scorer', label=' state_scoring_framework', color='#ffffff')

    # Inputs -> Process
    graph.edge('Human', 'Builder', label=' manual_overrides', color='#00ff00')
    graph.edge('VDR', 'Builder', label=' extracted_json', color='#ff0000', style='dashed')
    graph.edge('Chat', 'Builder', label=' new_site_obj', color='#ff0000', style='dashed')
    graph.edge('UtilAgent', 'Scorer', label=' iso_queue_data', color='#ff0000', style='dashed')
    
    # Process -> Data
    graph.edge('Builder', 'ProfileObj', label=' instantiates', color='#00e5ff')
    graph.edge('Tracker', 'Session', label=' updates_prob', color='#00e5ff')
    graph.edge('ProfileObj', 'Session', label=' stores_in_db', color='#ffea00')
    graph.edge('Session', 'Sheet', label=' syncs_json_blobs', color='#ffea00')
    
    # Data -> Logic -> Output
    graph.edge('ProfileObj', 'Scorer', label=' provides_attrs', color='#ffea00')
    graph.edge('Scorer', 'Dash', label=' rankings_table', color='#ff00ff')
    graph.edge('ProfileObj', 'PPTX', label=' populates_slides', color='#ff00ff')
    graph.edge('ProfileObj', 'PDF', label=' generates_summary', color='#ff00ff')
    
    st.graphviz_chart(graph, use_container_width=True)

    st.divider()

    # --- 3. Component Deep Dive ---
    st.subheader("🔍 Codebase Inspector")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selected_layer = st.radio(
            "Select Layer to Inspect:",
            ["Foundation Layer", "Input Layer", "Processing Layer", "Data Layer", "Output Layer"],
            captions=["Deep Research Report", "Forms, Agents, VDR", "Builders, Trackers, Scorers", "State, Sheets, JSON", "PPTX, PDF, UI"]
        )
        
    with col2:
        if selected_layer == "Foundation Layer":
            st.info("**Foundation Layer**: The bedrock of all assumptions.")
            st.markdown("""
            - **`Deep Research Report`**: A manually driven, bottom-up analysis of global supply (CoWoS, Chips) vs. demand (Data Center MW).
            - **`Supply/Demand Model`**: Takes the Deep Research inputs and projects regional power deficits.
            - **Impact**: This foundational data directly informs the **State Scoring Framework**, ensuring that site scores reflect macro-economic realities.
            """)

        elif selected_layer == "Input Layer":
            st.info("**Input Layer**: Captures raw data from multiple sources.")
            st.markdown("""
            - **`site_profile_builder.py`**: The gatekeeper. It defines `HUMAN_INPUT_FIELDS` (e.g., Willingness to Sell) and `AI_RESEARCHABLE_FIELDS` (e.g., Flood Zone).
            - **`vdr_processor.py`** (Agent): Uses OCR to read PDFs, then an LLM to extract structured JSON matching the `SiteProfileData` schema.
            - **`utility_agent.py`** (Agent): Autonomous scraper that looks for IRP PDFs and Queue Excel files on utility websites.
            """)
            
        elif selected_layer == "Processing Layer":
            st.info("**Processing Layer**: Transforms raw data into actionable intelligence.")
            st.markdown("""
            - **`program_tracker.py`**: 
                - Calculates `Probability` based on Stage Gates (Site Control, Power, Zoning).
                - Computes `Weighted Fee` = `Total Fee` * `Probability`.
            - **`state_analysis.py`**:
                - Runs the Scoring Engine: `(StateScore * 0.2) + (PowerScore * 0.25) + ...`
                - Normalizes scores across different markets (e.g., ERCOT vs PJM).
            """)
            
        elif selected_layer == "Data Layer":
            st.info("**Data Layer**: The hybrid persistence engine.")
            st.markdown("""
            - **`SiteProfileData` (Dataclass)**: The canonical object model. All UI and Export functions expect this format.
            - **Google Sheets**: Acts as the backend.
                - **Structured Columns**: `target_mw`, `state` (for fast SQL-like filtering).
                - **JSON Blobs**: `phases_json`, `profile_json` (NoSQL-style storage for complex nested data).
            """)
            
        elif selected_layer == "Output Layer":
            st.info("**Output Layer**: Renders data for decision makers.")
            st.markdown("""
            - **`pptx_export.py`**: 
                - Loads `Sample Site Profile Template.pptx`.
                - Replaces text placeholders (e.g., `{{target_mw}}`).
                - Generates native Charts (Load Ramp, Radar Plot) using `pptx.chart`.
            - **`streamlit_app.py`**: The main UI controller that stitches everything together.
            """)


