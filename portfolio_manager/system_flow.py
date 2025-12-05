import streamlit as st
import graphviz
import sys
import os
import streamlit.components.v1 as components
from datetime import datetime, timedelta, timezone
import json

# Try to import pytz for accurate EST handling, fallback to fixed offset if missing
try:
    import pytz
    EST = pytz.timezone('US/Eastern')
except ImportError:
    # Fallback to fixed offset (UTC-5)
    EST = timezone(timedelta(hours=-5))

def get_est_time():
    """Returns current time in EST format."""
    if isinstance(EST, timezone):
        now = datetime.now(EST)
    else:
        now = datetime.now(EST)
    return now.strftime("%Y-%m-%d %H:%M:%S EST")

def show_system_flow():
    """
    Displays a comprehensive 'Command Center' view of the application's logic, architecture, and data flow.
    """
    st.title("🧩 Network Operations Command Center")
    
    # --- 0. Initialize Telemetry State ---
    if 'node_updates' not in st.session_state:
        # Simulate initial "boot" times
        initial_time = get_est_time()
        st.session_state.node_updates = {
            'DeepResearch': initial_time,
            'Human': initial_time,
            'Chat': initial_time,
            'VDR': initial_time,
            'UtilAgent': initial_time,
            'LocAgent': initial_time,  # New Location Agent
            'SupplyDemand': initial_time,
            'Builder': initial_time,
            'Tracker': initial_time,
            'Scorer': initial_time,
            'Sheet': initial_time,
            'Session': initial_time,
            'ProfileObj': initial_time,
            'PPTX': initial_time,
            'PDF': initial_time,
            'Dash': initial_time,
        }

    # --- 1. System Health & Status (Live Telemetry) ---
    st.markdown("### 📡 System Telemetry & Health")
    
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
        
    st.divider()

    # --- 2. Detailed Architecture Blueprint (Viz.js) ---
    st.subheader("🕸️ Master Architecture Blueprint")
    st.caption("Interactive Zoom/Pan Enabled. Live EST Timestamps on all nodes.")
    
    # Create Graphviz Object (for DOT generation only)
    graph = graphviz.Digraph()
    graph.attr(rankdir='TB')
    graph.attr(bgcolor='#0e1117')
    graph.attr('node', shape='plain', fontname='Courier', fontsize='10', fontcolor='white')
    graph.attr('edge', fontname='Courier', fontsize='8', color='#555555', fontcolor='#aaaaaa')
    
    # Helper for HTML Node Table with Timestamp
    def html_node(key, title, subtitle, color):
        timestamp = st.session_state.node_updates.get(key, "N/A")
        return f'''<
        <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">
            <TR><TD BGCOLOR="{color}"><FONT COLOR="white"><B>{title}</B></FONT></TD></TR>
            <TR><TD BGCOLOR="{color}"><FONT COLOR="#e0e0e0" POINT-SIZE="9">{subtitle}</FONT></TD></TR>
            <TR><TD BGCOLOR="{color}"><FONT COLOR="#00ff00" POINT-SIZE="8">Updated: {timestamp}</FONT></TD></TR>
        </TABLE>
        >'''

    # -- Cluster: FOUNDATION --
    with graph.subgraph(name='cluster_foundation') as c:
        c.attr(label='LAYER 0: FOUNDATION', style='dashed', color='#ffffff', fontcolor='#ffffff')
        c.node('DeepResearch', html_node('DeepResearch', '📚 Deep Research Report', '(Manual Bottom-Up)', '#424242'))

    # -- Cluster: INPUT LAYER --
    with graph.subgraph(name='cluster_inputs') as c:
        c.attr(label='LAYER 1: INPUTS & AGENTS', style='dashed', color='#00ff00', fontcolor='#00ff00')
        
        c.node('Human', html_node('Human', '👤 Human Input', '[Forms/UI]', '#1b5e20'))
        
        # Agent Styling (Red Dashed)
        agent_attrs = {'style': 'dashed', 'color': '#ff0000', 'penwidth': '2.0'}
        
        c.node('Chat', html_node('Chat', '💬 AI Chat', '[llm_integration.py]', '#004d40'), **agent_attrs)
        c.node('VDR', html_node('VDR', '📁 VDR Processor', '(OCR + Extraction)', '#004d40'), **agent_attrs)
        c.node('UtilAgent', html_node('UtilAgent', '🕷️ Utility Agent', '(Scraper)', '#004d40'), **agent_attrs)
        c.node('LocAgent', html_node('LocAgent', '🌐 AI Location Research', '(Lat/Lon Analysis)', '#004d40'), **agent_attrs)
        
        c.node('SupplyDemand', html_node('SupplyDemand', '⚖️ Supply/Demand Model', '[research_module.py]', '#004d40'))

    # -- Cluster: PROCESSING LAYER --
    with graph.subgraph(name='cluster_process') as c:
        c.attr(label='LAYER 2: PROCESSING & BUILDERS', style='dashed', color='#00e5ff', fontcolor='#00e5ff')
        
        c.node('Builder', html_node('Builder', '🏗️ SiteProfileBuilder', '.map_app_to_profile()', '#01579b'))
        c.node('Tracker', html_node('Tracker', '📈 ProgramTracker', '.calculate_probability()', '#01579b'))
        c.node('Scorer', html_node('Scorer', '⭐ ScoringEngine', '.calculate_site_score()', '#01579b'))

    # -- Cluster: DATA LAYER --
    with graph.subgraph(name='cluster_data') as c:
        c.attr(label='LAYER 3: PERSISTENCE & STATE', style='dashed', color='#ffea00', fontcolor='#ffea00')
        
        c.node('Sheet', html_node('Sheet', '☁️ Google Sheets', '[gspread]', '#f57f17'))
        c.node('Session', html_node('Session', '💾 Session State', '(st.session_state.db)', '#f57f17'))
        c.node('ProfileObj', html_node('ProfileObj', '📝 SiteProfileData', '(Dataclass Object)', '#ff6f00'))

    # -- Cluster: OUTPUT LAYER --
    with graph.subgraph(name='cluster_output') as c:
        c.attr(label='LAYER 4: OUTPUTS & RENDERING', style='dashed', color='#ff00ff', fontcolor='#ff00ff')
        
        c.node('PPTX', html_node('PPTX', '📽️ PPT Generator', '.export_site_to_pptx()', '#4a148c'))
        c.node('PDF', html_node('PDF', '📄 PDF Report', '[fpdf2]', '#4a148c'))
        c.node('Dash', html_node('Dash', '📊 Dashboard UI', '[streamlit_app.py]', '#880e4f'))

    # -- EDGES --
    graph.edge('DeepResearch', 'SupplyDemand', label=' drives_assumptions', color='#ffffff')
    graph.edge('SupplyDemand', 'Scorer', label=' state_scoring_framework', color='#ffffff')
    
    graph.edge('Human', 'Builder', label=' manual_overrides', color='#00ff00')
    graph.edge('VDR', 'Builder', label=' extracted_json', color='#ff0000', style='dashed')
    graph.edge('Chat', 'Builder', label=' new_site_obj', color='#ff0000', style='dashed')
    graph.edge('LocAgent', 'Builder', label=' fills_gaps', color='#ff0000', style='dashed')
    graph.edge('UtilAgent', 'Scorer', label=' iso_queue_data', color='#ff0000', style='dashed')
    
    graph.edge('Builder', 'ProfileObj', label=' instantiates', color='#00e5ff')
    graph.edge('Tracker', 'Session', label=' updates_prob', color='#00e5ff')
    
    # Clarify Data Flow: ProfileObj carries all data to Session/Sheet
    graph.edge('ProfileObj', 'Session', label=' stores_full_state', color='#ffea00')
    graph.edge('Session', 'Sheet', label=' syncs_json_blobs', color='#ffea00')
    
    # Logic -> Object Loops
    graph.edge('ProfileObj', 'Scorer', label=' provides_attrs', color='#ffea00')
    graph.edge('Scorer', 'ProfileObj', label=' updates_score', color='#00e5ff') # Closing the loop
    
    graph.edge('Scorer', 'Dash', label=' rankings_table', color='#ff00ff')
    graph.edge('ProfileObj', 'PPTX', label=' populates_slides', color='#ff00ff')
    graph.edge('ProfileObj', 'PDF', label=' generates_summary', color='#ff00ff')

    # --- Render with Viz.js (Client-Side) ---
    # We use a custom HTML component to load viz.js and svg-pan-zoom
    dot_source = graph.source
    
    # Escape backticks and newlines for JS string
    dot_source_js = dot_source.replace('\n', '\\n').replace('"', '\\"')
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/viz.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/full.render.js"></script>
        <!-- Switch to jsdelivr for better reliability -->
        <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
        <style>
            #graph-container {{
                width: 100%;
                height: 600px;
                border: 1px solid #333;
                background-color: #0e1117;
                overflow: hidden;
                position: relative;
            }}
            svg {{
                width: 100%;
                height: 100%;
            }}
        </style>
    </head>
    <body>
        <div id="graph-container"></div>
        <script>
            // Wait for libraries to load
            window.onload = function() {{
                try {{
                    var viz = new Viz();
                    var dotSource = "{dot_source_js}";
                    
                    viz.renderSVGElement(dotSource)
                        .then(function(element) {{
                            document.getElementById('graph-container').appendChild(element);
                            
                            // Check if svgPanZoom is loaded
                            if (typeof svgPanZoom === 'undefined') {{
                                console.error("svg-pan-zoom library not loaded!");
                                document.getElementById('graph-container').innerHTML += '<p style="color:red; position:absolute; top:10px; left:10px;">Error: Zoom library failed to load.</p>';
                                return;
                            }}
                            
                            // Enable Pan/Zoom
                            svgPanZoom(element, {{
                                zoomEnabled: true,
                                controlIconsEnabled: true,
                                fit: true,
                                center: true,
                                minZoom: 0.1,
                                maxZoom: 10
                            }});
                        }})
                        .catch(error => {{
                            console.error(error);
                            document.getElementById('graph-container').innerHTML = '<p style="color:red">Error rendering graph: ' + error + '</p>';
                        }});
                }} catch (e) {{
                    console.error(e);
                    document.getElementById('graph-container').innerHTML = '<p style="color:red">Critical Error: ' + e + '</p>';
                }}
            }};
        </script>
    </body>
    </html>
    """
    
    components.html(html_code, height=620)

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
            - **`AI Location Research`** (Agent): Triggered via "Re-run Research", this uses Lat/Lon to query LLMs for specific site details (nearest town, flood zone, etc.).
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


