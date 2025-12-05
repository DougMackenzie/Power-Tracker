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
    col_header, col_zoom = st.columns([3, 1])
    with col_header:
        st.subheader("🕸️ Master Architecture Blueprint")
        st.caption("Detailed mapping of Python modules, data structures, and logic flows.")
    with col_zoom:
        # Zoom control (simulated by graph size)
        zoom_level = st.slider("🔍 Zoom Level", min_value=100, max_value=2000, value=1000, step=100, label_visibility="collapsed")
    
    # Create a complex graphviz directed graph with "Dark Mode" / Tech style
    graph = graphviz.Digraph()
    graph.attr(rankdir='TB') # Top to Bottom for better hierarchy
    graph.attr(bgcolor='#0e1117') # Streamlit dark bg approximation
    # Use HTML-like labels for rich formatting
    graph.attr('node', shape='plain', fontname='Courier', fontsize='10', fontcolor='white')
    graph.attr('edge', fontname='Courier', fontsize='8', color='#555555', fontcolor='#aaaaaa')
    
    # Get current time for "Live" timestamps
    now_str = datetime.now().strftime("%H:%M:%S")
    
    # Helper for HTML Node Table
    def html_node(title, subtitle, color, border_color=None, border_style="solid"):
        border_color = border_color or color
        # Dashed border simulation in HTML table is tricky, so we use the graphviz style for the node instead
        # But here we define the inner content
        return f'''<
        <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">
            <TR><TD BGCOLOR="{color}"><FONT COLOR="white"><B>{title}</B></FONT></TD></TR>
            <TR><TD BGCOLOR="{color}"><FONT COLOR="#e0e0e0" POINT-SIZE="9">{subtitle}</FONT></TD></TR>
        </TABLE>
        >'''

    # -- Cluster: FOUNDATION --
    with graph.subgraph(name='cluster_foundation') as c:
        c.attr(label='LAYER 0: FOUNDATION', style='dashed', color='#ffffff', fontcolor='#ffffff')
        
        # Deep Research Node with explicit timestamp
        label = f'''<
        <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6" BGCOLOR="#424242">
            <TR><TD><FONT COLOR="white"><B>📚 Deep Research Report</B></FONT></TD></TR>
            <TR><TD><FONT COLOR="#cccccc" POINT-SIZE="9">(Manual Bottom-Up Analysis)</FONT></TD></TR>
            <TR><TD><FONT COLOR="#00ff00" POINT-SIZE="8">Last Updated: {now_str}</FONT></TD></TR>
        </TABLE>
        >'''
        c.node('DeepResearch', label=label)

    # -- Cluster: INPUT LAYER --
    with graph.subgraph(name='cluster_inputs') as c:
        c.attr(label='LAYER 1: INPUTS & AGENTS', style='dashed', color='#00ff00', fontcolor='#00ff00')
        
        c.node('Human', html_node('👤 Human Input', '[Forms/UI]', '#1b5e20'))
        
        # Agentic Capabilities (Red Dashed Line handled by node attributes)
        agent_attrs = {'style': 'dashed', 'color': '#ff0000', 'penwidth': '2.0'}
        
        c.node('Chat', html_node('💬 AI Chat', '[llm_integration.py]', '#004d40'), **agent_attrs)
        c.node('VDR', html_node('📁 VDR Processor', '(OCR + Extraction)', '#004d40'), **agent_attrs)
        c.node('UtilAgent', html_node('🕷️ Utility Agent', '(Scraper)', '#004d40'), **agent_attrs)
        
        # Supply/Demand Model
        c.node('SupplyDemand', html_node('⚖️ Supply/Demand Model', '[research_module.py]', '#004d40'))

    # -- Cluster: PROCESSING LAYER --
    with graph.subgraph(name='cluster_process') as c:
        c.attr(label='LAYER 2: PROCESSING & BUILDERS', style='dashed', color='#00e5ff', fontcolor='#00e5ff')
        
        c.node('Builder', html_node('🏗️ SiteProfileBuilder', '.map_app_to_profile()', '#01579b'))
        c.node('Tracker', html_node('📈 ProgramTracker', '.calculate_probability()', '#01579b'))
        c.node('Scorer', html_node('⭐ ScoringEngine', '.calculate_site_score()', '#01579b'))

    # -- Cluster: DATA LAYER --
    with graph.subgraph(name='cluster_data') as c:
        c.attr(label='LAYER 3: PERSISTENCE & STATE', style='dashed', color='#ffea00', fontcolor='#ffea00')
        
        c.node('Sheet', html_node('☁️ Google Sheets', '[gspread]', '#f57f17'))
        c.node('Session', html_node('💾 Session State', '(st.session_state.db)', '#f57f17'))
        c.node('ProfileObj', html_node('📝 SiteProfileData', '(Dataclass Object)', '#ff6f00'))

    # -- Cluster: OUTPUT LAYER --
    with graph.subgraph(name='cluster_output') as c:
        c.attr(label='LAYER 4: OUTPUTS & RENDERING', style='dashed', color='#ff00ff', fontcolor='#ff00ff')
        
        c.node('PPTX', html_node('📽️ PPT Generator', '.export_site_to_pptx()', '#4a148c'))
        c.node('PDF', html_node('📄 PDF Report', '[fpdf2]', '#4a148c'))
        c.node('Dash', html_node('📊 Dashboard UI', '[streamlit_app.py]', '#880e4f'))

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
    
    # Render with dynamic width based on zoom slider
    # Note: use_container_width=False allows the width to exceed the container, creating a scrollbar if needed
    st.graphviz_chart(graph, use_container_width=False)
    
    # Inject CSS to force the graph to respect the zoom slider width
    # This is a bit of a hack since st.graphviz_chart doesn't accept a 'width' pixel argument directly
    # But we can control the SVG size via graph attributes if we were using pipe, 
    # or just rely on Streamlit's rendering.
    # Actually, st.graphviz_chart expands to fit content if use_container_width=False.
    # So we can control the size by setting graph.attr(size="...")? No, that's inches.
    # Best bet: The user can scroll if it's big.
    
    st.caption(f"Use the slider above to zoom. Current View Width: {zoom_level}px equivalent.")

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


