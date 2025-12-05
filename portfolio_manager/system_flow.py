import streamlit as st
import graphviz

def show_system_flow():
    """
    Displays a comprehensive interactive flow diagram of the application's logic and architecture.
    """
    st.title("🧩 System Architecture & Logic Flow")
    st.markdown("""
    This module visualizes the complex logic flow of the Antigravity Power Tracker, 
    from deep research to portfolio management and agentic capabilities.
    **Click on the buttons below the diagram to explore the complexity of each module.**
    """)

    with st.expander("📋 Comprehensive System Assessment", expanded=True):
        st.markdown("""
        ### Current State Assessment
        The **Antigravity Power Tracker** has evolved into a sophisticated decision-support platform that integrates macro-economic research with micro-level site execution.
        
        **Key Strengths:**
        -   **Vertical Integration**: Connects global supply chain constraints (CoWoS/Chips) directly to local site feasibility.
        -   **Agentic Automation**: Utilizes LLMs to automate labor-intensive tasks like VDR analysis and utility research.
        -   **Dynamic Scoring**: The multi-dimensional scoring engine (`State * Power * Execution`) allows for nuanced portfolio ranking.
        -   **Data Flexibility**: Hybrid schema (Structured Columns + JSON Blobs) enables rapid iteration without database migrations.
        
        **System Maturity:**
        -   **Research Layer**: 🟢 Mature. Detailed bottom-up build and scenario modeling.
        -   **Data Layer**: 🟢 Mature. Robust Google Sheets integration with caching.
        -   **Agent Layer**: 🟡 Evolving. VDR processing and Utility Agents are functional but improving.
        -   **UI/UX**: 🟡 Good. Navigation is expanding; this Flow Module helps manage complexity.
        """)

    # 1. Visual Flow Diagram using Graphviz
    st.subheader("High-Level Logic Flow")
    
    # Create a graphviz directed graph
    graph = graphviz.Digraph()
    graph.attr(rankdir='LR')
    graph.attr('node', shape='box', style='filled', fillcolor='#f0f2f6', fontname='Helvetica')
    
    # Define Nodes
    graph.node('Research', 'Deep Research\nFramework', fillcolor='#e1f5fe')
    graph.node('SupplyDemand', 'Supply vs Demand\nAnalysis', fillcolor='#e1f5fe')
    graph.node('Agents', 'Agentic\nCapabilities', fillcolor='#fff9c4')
    graph.node('Sites', 'Site Database\n(Core)', fillcolor='#e8f5e9')
    graph.node('Scoring', 'State & Site\nScoring', fillcolor='#f3e5f5')
    graph.node('Portfolio', 'Portfolio\nManagement', fillcolor='#fff3e0')
    
    # Define Edges
    graph.edge('Research', 'SupplyDemand', label=' informs')
    graph.edge('SupplyDemand', 'Scoring', label=' context')
    graph.edge('Agents', 'Sites', label=' enriches')
    graph.edge('Agents', 'Research', label=' automates')
    graph.edge('Sites', 'Scoring', label=' data')
    graph.edge('Scoring', 'Portfolio', label=' ranks')
    graph.edge('Sites', 'Portfolio', label=' feeds')
    
    st.graphviz_chart(graph, use_container_width=True)

    st.divider()

    # 2. Interactive Module Explorer
    st.subheader("🔍 Explore Module Complexity")
    
    # Layout for buttons
    col1, col2, col3 = st.columns(3)
    
    selected_module = None
    
    with col1:
        if st.button("🔬 Deep Research Framework", use_container_width=True):
            selected_module = "Research"
        if st.button("⚖️ Supply vs Demand Analysis", use_container_width=True):
            selected_module = "SupplyDemand"
            
    with col2:
        if st.button("🤖 Agentic Capabilities", use_container_width=True):
            selected_module = "Agents"
        if st.button("🏭 Site Database", use_container_width=True):
            selected_module = "Sites"
            
    with col3:
        if st.button("⭐ State & Site Scoring", use_container_width=True):
            selected_module = "Scoring"
        if st.button("📊 Portfolio Management", use_container_width=True):
            selected_module = "Portfolio"

    # Display Details based on selection
    if selected_module:
        display_module_details(selected_module)
    else:
        st.info("Select a module above to view its internal logic and complexity.")

def display_module_details(module_key):
    """Displays detailed information about the selected module."""
    
    if module_key == "Research":
        st.markdown("### 🔬 Deep Research Framework")
        st.info("The foundational layer that drives market assumptions.")
        
        tab1, tab2, tab3 = st.tabs(["Logic Flow", "Key Files", "Capabilities"])
        
        with tab1:
            st.markdown("""
            **Logic Flow:**
            1.  **Macro Analysis**: Aggregates global data (e.g., CoWoS capacity, Chip production).
            2.  **Bottom-Up Build**: Converts chip supply -> Server racks -> MW demand.
            3.  **Regional Allocation**: Distributes global demand to US regions based on market share.
            4.  **Forecasting**: Projects demand curves (Linear, Exponential, S-Curve) to 2030+.
            """)
            
        with tab2:
            st.code("""
            portfolio_manager/research_module.py
            portfolio_manager/research_data.py
            """, language="text")
            
        with tab3:
            st.markdown("""
            -   **CoWoS Capacity Tracking**: TSMC/Intel/Samsung wafer capacity.
            -   **H100/Blackwell Conversion**: Chips per rack, KW per rack calculations.
            -   **Scenario Modeling**: Conservative vs Aggressive adoption rates.
            """)

    elif module_key == "SupplyDemand":
        st.markdown("### ⚖️ Supply vs Demand Analysis")
        st.info("Matches projected AI power demand against available utility supply.")
        
        tab1, tab2 = st.tabs(["Logic Flow", "Key Metrics"])
        
        with tab1:
            st.markdown("""
            **Logic Flow:**
            1.  **Demand Input**: Takes outputs from the Research Framework.
            2.  **Supply Input**: Ingests utility IRPs (Integrated Resource Plans) and queue data.
            3.  **Gap Analysis**: Identifies regions with power deficits vs surplus.
            4.  **Constraint Modeling**: Factors in transmission congestion and timeline risks.
            """)
            
        with tab2:
            st.markdown("""
            -   **Demand/Supply Gap (GW)**
            -   **Time-to-Power (Months)**
            -   **Interconnection Queue Depth**
            """)

    elif module_key == "Agents":
        st.markdown("### 🤖 Agentic Capabilities")
        st.info("AI-driven automation for data gathering and processing.")
        
        tab1, tab2, tab3 = st.tabs(["Agents", "Workflows", "Files"])
        
        with tab1:
            st.markdown("""
            -   **Utility Research Agent**: Scrapes utility websites for tariffs, IRPs, and queue data.
            -   **VDR Processor**: Ingests PDFs/Excel files from Virtual Data Rooms and extracts structured site data.
            -   **Site Profiler**: Auto-generates site descriptions and SWOT analyses using LLMs.
            """)
            
        with tab2:
            st.markdown("""
            **VDR Workflow:**
            1.  Upload PDF/Doc.
            2.  OCR & Text Extraction.
            3.  LLM Extraction (JSON Schema).
            4.  Validation & DB Insert.
            """)
            
        with tab3:
            st.code("""
            portfolio_manager/utility_agent.py
            portfolio_manager/llm_integration.py
            portfolio_manager/vdr_processor.py
            """, language="text")

    elif module_key == "Sites":
        st.markdown("### 🏭 Site Database (Core)")
        st.info("The central repository for all site-specific data.")
        
        tab1, tab2 = st.tabs(["Data Structure", "Features"])
        
        with tab1:
            st.markdown("""
            **Schema:**
            -   **Core**: ID, Name, Location (Lat/Lon), Acreage.
            -   **Power**: Target MW, Utility, Voltage, Distance to Sub.
            -   **Commercial**: Land Status, Price, Contract Terms.
            -   **JSON Blobs**: Flexible storage for Phases, Risks, Opportunities.
            """)
            
        with tab2:
            st.markdown("""
            -   **Google Sheets Integration**: Two-way sync for easy editing.
            -   **Geospatial Indexing**: Lat/Lon support for mapping.
            -   **Document Linking**: Association with VDR files.
            """)

    elif module_key == "Scoring":
        st.markdown("### ⭐ State & Site Scoring")
        st.info("Multi-dimensional ranking engine to prioritize opportunities.")
        
        tab1, tab2, tab3 = st.tabs(["Scoring Logic", "Weights", "Files"])
        
        with tab1:
            st.markdown("""
            **Algorithm:**
            `Score = (State * W1) + (Power * W2) + (Relationship * W3) + ...`
            
            -   **State Score**: Policy, Energy Cost, Tax Incentives.
            -   **Power Score**: Timeline, Voltage, Queue Position.
            -   **Execution Score**: Developer experience, Capital status.
            """)
            
        with tab2:
            st.markdown("""
            **Adjustable Weights:**
            -   State Market: 20%
            -   Power Pathway: 25%
            -   Relationship: 20%
            -   Execution: 15%
            """)
            
        with tab3:
            st.code("""
            portfolio_manager/state_analysis.py
            portfolio_manager/streamlit_app.py (calculate_site_score)
            """, language="text")

    elif module_key == "Portfolio":
        st.markdown("### 📊 Portfolio Management")
        st.info("High-level tracking of program health, fees, and probability.")
        
        tab1, tab2 = st.tabs(["Metrics", "Logic"])
        
        with tab1:
            st.markdown("""
            -   **Total Fee Potential**: Sum of all potential fees.
            -   **Weighted Fee**: Fee * Probability.
            -   **MW Pipeline**: Total capacity in various stages.
            """)
            
        with tab2:
            st.markdown("""
            **Stage Gates:**
            1.  Site Control
            2.  Power Secured
            3.  Zoning/Permitting
            4.  Marketing/Sales
            
            **Probability Calculation**:
            Derived from stage completion and risk factors.
            """)
