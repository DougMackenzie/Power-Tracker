# Powered Land Portfolio Manager

A comprehensive Streamlit application for evaluating and managing data center development sites with integrated state-level analysis and utility research capabilities.

## Features

### 📊 Dashboard
- Portfolio-wide metrics (total sites, pipeline MW, average score)
- Pipeline breakdown by development stage
- MW distribution by state
- Top sites ranked by composite score

### 🏭 Site Database
- Full CRUD operations for site management
- Multi-filter views (state, stage, minimum score)
- Detailed site profiles with score breakdowns
- State context integration showing tier, ISO, regulatory structure

### 🏆 Custom Rankings
- **Adjustable scoring weights** for each component:
  - State Score (default 20%)
  - Power Pathway (default 25%)
  - Relationship Capital (default 20%)
  - Execution Capability (default 15%)
  - Site Fundamentals (default 10%)
  - Financial (default 10%)
- Real-time re-ranking as weights change
- Score vs. Scale visualization

### 🗺️ State Analysis
- **10 pre-built state profiles** with scoring across:
  - Regulatory Environment (25% weight)
  - Transmission Capacity (20%)
  - Power Cost & Availability (20%)
  - Water Availability (15%)
  - Business Climate (10%)
  - DC Ecosystem (10%)
- Radar chart comparisons
- SWOT analysis for each state
- National state rankings

### 🔍 Utility Research
- Auto-generated research queries for:
  - Interconnection queue data
  - IRP and capacity announcements
  - RFP for new generation
  - Rate cases and tariffs
  - Data center partnerships
  - Transmission projects
- ISO-specific research queries (SPP, ERCOT, PJM, MISO, etc.)

## Installation

```bash
# Install dependencies
pip install streamlit pandas plotly

# Run the app
streamlit run streamlit_app.py
```

## File Structure

```
portfolio_manager/
├── streamlit_app.py      # Main Streamlit application
├── state_analysis.py     # State profiles and analysis module
├── site_database.json    # Persistent site database
└── README.md             # This file
```

## Scoring Methodology

### Site Score Components

**Power Pathway (0-100 points)**
- Study Status: SIS requested (8) → IA executed (40)
- Utility Commitment: None (0) → Committed (25)
- Timeline: ≤24 months (20) → ≤60 months (5)
- Infrastructure: +5 each for transmission adjacent, substation nearby, BTM viable

**Relationship Capital (0-100 points)**
- End-User Status: None (0) → Term Sheet (60)
- Community Support: Opposition (0) → Champion (25)
- Political Support: Opposition (0) → Strong (15)

**Execution Capability (0-100 points)**
- Developer Track Record: None (5) → Extensive (40)
- Utility Relationships: None (0) → Strong (30)
- BTM Capability: None (0) → Multiple Sources (30)

**Site Fundamentals (0-100 points)**
- Land Control: None (0) → Owned (35)
- Site Density: Adequate density adds up to 20 points
- Water Status: Unknown (5) → Secured (25)
- Fiber Status: Unknown (5) → Lit (20)

**Financial (0-100 points)**
- Capital Access: Limited (5) → Strong (50)
- Development Budget Allocated: +25 points
- Partnership Structure: None (0) → JV Active (25)

### Development Stages

Sites are automatically classified into:
1. **Pre-Development** - No queue position
2. **Queue Only** - Queue position but no other progress
3. **Early Real** - Land control + utility engagement + early studies
4. **Study In Progress** - SIS/FS active or complete
5. **Utility Commitment** - Committed utility service
6. **Fully Entitled** - FA/IA executed + zoning + land control
7. **End-User Attached** - LOI or Term Sheet with customer

### State Tiers

- **Tier 1** (Score 80+): OK, TX, WY - Optimal regulatory and cost environment
- **Tier 2** (Score 65-79): GA, IN, OH, PA - Strong fundamentals with some constraints
- **Tier 3** (Score 50-64): VA, NV - Moderate challenges
- **Tier 4** (Score <50): CA - Significant barriers

## State Profiles Included

| State | Tier | Score | ISO | Ind. Rate | Key Strength |
|-------|------|-------|-----|-----------|--------------|
| OK | 1 | 88 | SPP | $0.055 | Pro-business PSC |
| WY | 1 | 82 | SPP | $0.048 | No corporate tax |
| TX | 1 | 80 | ERCOT | $0.065 | Existing ecosystem |
| IN | 2 | 72 | MISO | $0.062 | MISO/PJM flexibility |
| OH | 2 | 70 | PJM | $0.068 | Great Lakes water |
| GA | 2 | 70 | SERC | $0.072 | Georgia Power partnership |
| PA | 2 | 68 | PJM | $0.075 | Nuclear fleet |
| VA | 3 | 58 | PJM | $0.078 | Largest DC cluster |
| NV | 3 | 55 | WECC | $0.072 | Strong incentives |
| CA | 4 | 25 | CAISO | $0.180 | Tech proximity only |

## Usage

### Adding a Site

1. Navigate to "➕ Add/Edit Site"
2. Fill in required fields (Site Name, State, Utility, Target MW)
3. Complete power pathway details (study status, utility commitment)
4. Add relationship capital info (end-user status, community support)
5. Enter site fundamentals (land control, water, fiber)
6. Save the site

### Comparing Sites

1. Go to "🏆 Rankings"
2. Adjust weights in the sidebar to reflect your priorities
3. View re-ranked sites in real-time
4. Use the Score vs. Scale chart to identify outliers

### State Research

1. Navigate to "🔍 Utility Research"
2. Enter utility name and state
3. Generate research queries
4. Use queries with web search to gather current data

### Exporting Data

1. Go to "⚙️ Settings"
2. Click "📥 Export Database"
3. Download JSON file with all site data

## Integration with Diagnostic Tool

This portfolio manager complements the Site Diagnostic Tool:

1. **Use Portfolio Manager** for ongoing pipeline tracking and ranking
2. **Use Diagnostic Tool** for deep-dive critical path analysis on priority sites
3. **State context** from this app flows into diagnostic reports

## Customization

### Adding New States

Edit `state_analysis.py` and add to the `STATE_PROFILES` dictionary:

```python
"NC": StateProfile(
    state_code="NC",
    state_name="North Carolina",
    tier=2,
    overall_score=72,
    # ... complete all fields
)
```

### Modifying Scoring Weights

Default weights can be changed in `streamlit_app.py`:

```python
if 'weights' not in st.session_state:
    st.session_state.weights = {
        'state': 0.15,      # Reduce state importance
        'power': 0.30,      # Increase power importance
        'relationship': 0.25,
        # ...
    }
```

## Data Persistence

Site data is stored in `site_database.json` and persists between sessions. The database includes:
- All site attributes
- Metadata (created date, last updated, version)
- Full export/import capability

## License

Internal use only - Confidential
