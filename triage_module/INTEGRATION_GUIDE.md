# Triage & Intelligence System Integration Guide

## Overview

This guide covers integrating the Phase 1 (Quick Triage) and Phase 2 (Full Diagnosis) intelligence system into your existing Antigravity portfolio app.

## File Structure

```
portfolio_manager/
├── streamlit_app.py           # Main app - UPDATE navigation
├── triage/                    # NEW - Copy this entire folder
│   ├── __init__.py           # Package exports
│   ├── models.py             # Data classes & enums
│   ├── enrichment.py         # Utility lookup & auto-enrichment
│   ├── prompts.py            # Gemini prompt templates
│   ├── engine.py             # Core triage/diagnosis logic
│   ├── page.py               # Quick Triage Streamlit page
│   ├── diagnosis_page.py     # Full Diagnosis Streamlit page
│   ├── intelligence_page.py  # Intelligence Center page
│   ├── pptx_integration.py   # PPTX export functions
│   ├── tracker_integration.py # Program Tracker integration
│   └── storage.py            # Google Sheets operations
├── site_profile_builder.py    # MINOR UPDATE - add intel tab
├── program_tracker.py         # MINOR UPDATE - add intel summary
├── pptx_export.py            # MINOR UPDATE - add intel slides
└── google_integration.py      # NO CHANGES
```

---

## Step 1: Copy the Triage Module

Copy the entire `triage/` folder to your `portfolio_manager/` directory.

```bash
cp -r triage/ /path/to/portfolio_manager/triage/
```

---

## Step 2: Update Main App Navigation

In your `streamlit_app.py`, add the new navigation items and imports.

### Add Imports (top of file)

```python
# Add these imports
from triage import (
    show_quick_triage,
    show_triage_log,
)
from triage.diagnosis_page import show_full_diagnosis, show_site_intelligence
from triage.intelligence_page import show_intelligence_center
from triage.tracker_integration import render_intelligence_summary, show_intel_summary_widget
```

### Update Navigation (in your nav section)

Replace or add to your existing navigation:

```python
# In your navigation/sidebar section
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔬 Intelligence")

# Navigation options
pages = {
    "🏠 Home": "home",
    "📊 Program Tracker": "tracker",
    "🏗️ Site Database": "sites",
    "📑 Presentations": "presentations",
    "---": None,  # Separator
    "🚦 Quick Triage": "triage",
    "🔬 Full Diagnosis": "diagnosis",
    "🔍 Intelligence Center": "intelligence",
    "📋 Triage Log": "triage_log",
}

selected_page = st.sidebar.radio(
    "Navigation",
    options=list(pages.keys()),
    label_visibility="collapsed"
)

# Route to pages
page_key = pages.get(selected_page)

if page_key == "triage":
    show_quick_triage()
elif page_key == "diagnosis":
    show_full_diagnosis()
elif page_key == "intelligence":
    show_intelligence_center()
elif page_key == "triage_log":
    show_triage_log()
# ... your existing page routing
```

---

## Step 3: Update Google Sheets Schema

### Add Columns to Sites Sheet

Add these columns to your existing Sites sheet (can be done manually or via the schema migration function):

**Triage Columns:**
- `phase` - Site lifecycle phase ('0_prospect', '1_triage', '2_diagnosis', 'active', 'dead')
- `triage_date` - ISO datetime
- `triage_verdict` - 'KILL', 'CONDITIONAL', or 'PASS'
- `triage_red_flags_json` - JSON array of red flags
- `claimed_timeline` - Developer's claimed timeline
- `triage_source` - Source of opportunity
- `triage_contact` - Contact name
- `triage_power_story` - Developer's power narrative

**Diagnosis Columns:**
- `diagnosis_date` - ISO datetime
- `diagnosis_json` - Full diagnosis result as JSON
- `validated_timeline` - Assessed realistic timeline
- `timeline_risk` - 'on_track', 'at_risk', 'not_credible'
- `claim_validation_json` - JSON array of claim validations
- `diagnosis_recommendation` - 'GO', 'CONDITIONAL_GO', 'NO_GO'
- `diagnosis_top_risks` - Comma-separated top risks
- `diagnosis_follow_ups` - Comma-separated actions
- `research_summary` - Text summary

**Intelligence Columns:**
- `utility_intel_json` - Cached utility intelligence
- `market_intel_json` - Cached market intelligence
- `research_reports_json` - Array of research reports
- `last_research_date` - ISO datetime

### Create Triage_Log Sheet

Create a new sheet tab named `Triage_Log` with these columns:

```
triage_id | created_date | county | state | claimed_mw | claimed_timeline | 
power_story | source | contact_name | contact_info | detected_utility | 
detected_iso | jurisdiction_type | verdict | red_flags_json | 
enrichment_json | notes | advanced_to_phase2 | phase2_site_id | archived_reason
```

### Create Utility_Intelligence Sheet (Optional)

For persistent utility intelligence storage:

```
utility_id | utility_name | parent_company | iso | state | capacity_deficit_mw |
deficit_year | appetite_rating | realistic_timeline | timeline_rationale |
validated_overrides_json | pipeline_intel_json | relationship_status_json |
last_conversation_date | notes | last_updated
```

---

## Step 4: Update Site Profile Builder

In your `site_profile_builder.py`, add an Intelligence tab to the site detail view.

### Add Import

```python
from triage.diagnosis_page import show_site_intelligence
```

### Add Tab to Site Detail

```python
# In your site detail tabs section
tabs = st.tabs([
    "Overview",
    "Phases", 
    "Scores",
    "AI Research",
    "📊 Intelligence",  # NEW TAB
    "Critical Path"
])

# ... existing tab content ...

with tabs[4]:  # Intelligence tab
    show_site_intelligence(site_id, site_data)
```

---

## Step 5: Update Program Tracker

In your `program_tracker.py`, add the intelligence summary.

### Add Import

```python
from triage.tracker_integration import (
    render_intelligence_summary,
    show_intel_summary_widget,
    get_portfolio_intel_metrics,
)
```

### Add to Portfolio Summary Tab

```python
# In your Portfolio Summary tab, after existing content
def show_portfolio_summary(db):
    # ... existing portfolio summary code ...
    
    # Add intelligence summary section
    st.markdown("---")
    render_intelligence_summary(db.get('sites', {}))
```

### Add to Sidebar (Optional)

```python
# In sidebar
with st.sidebar:
    show_intel_summary_widget(db.get('sites', {}))
```

---

## Step 6: Update PPTX Export

In your `pptx_export.py`, add the intelligence slides.

### Add Import

```python
from triage.pptx_integration import (
    add_all_intelligence_slides,
    add_intelligence_slide,
)
```

### Add to Export Function

```python
def export_site_presentation(site_data, template_path=None):
    # ... existing slide creation ...
    
    # After your existing slides, add intelligence slides
    # Only if site has diagnosis data
    if site_data.get('diagnosis_json') or site_data.get('diagnosis_date'):
        add_all_intelligence_slides(
            prs=prs,
            site_data=site_data,
            utility_intel=None,  # Pass utility intel if available
            market_snapshot=None,  # Pass market snapshot if available
            include_utility_detail=True,
            include_competitive=True,
        )
    
    # ... rest of export ...
```

---

## Step 7: Update Requirements

Add any missing packages to your `requirements.txt`:

```txt
# You likely already have these
streamlit
google-generativeai
gspread
google-auth
python-pptx
pydantic

# No new packages required for triage module
```

---

## Step 8: Verify Gemini API Key

Ensure your `.streamlit/secrets.toml` has the Gemini API key:

```toml
GEMINI_API_KEY = "your-gemini-api-key-here"
```

---

## Usage Guide

### Quick Triage Workflow

1. Navigate to **🚦 Quick Triage**
2. Enter minimal opportunity details:
   - County, State
   - Claimed MW
   - Claimed timeline
   - Optional: Power story, acreage, source
3. Click **Run Triage**
4. Review results:
   - Verdict: KILL / CONDITIONAL / PASS
   - Red flags identified
   - Auto-enriched utility/ISO info
5. Actions:
   - KILL → Archive with reason
   - CONDITIONAL/PASS → Advance to Phase 2

### Full Diagnosis Workflow

1. Navigate to **🔬 Full Diagnosis**
2. Select a site from the dropdown
3. Add developer claims to validate
4. Click **Run Full Diagnosis**
5. Review comprehensive results:
   - Timeline validation
   - Claim validations
   - Utility assessment
   - Competitive landscape
   - Top risks & required actions
6. Save to site record

### Intelligence Center

1. Navigate to **🔍 Intelligence Center**
2. **Utility Intelligence tab:**
   - Research new utilities
   - Add validated overrides (proprietary intel)
   - Refresh stale research
3. **Market Snapshots tab:**
   - Generate regional market snapshots
   - Track competitive landscape
4. **Industry Intel tab:**
   - Reference supply chain lead times
   - Permitting benchmarks
   - Cost benchmarks
5. **Coverage Dashboard tab:**
   - Monitor research coverage
   - Identify gaps
   - Prioritize research tasks

---

## Key Integration Points

### Session State

The module uses these session state keys:
- `st.session_state.triage_result` - Last triage result
- `st.session_state.triage_intake` - Last triage intake
- `st.session_state.diagnosis_result` - Last diagnosis result
- `st.session_state.utility_intel_db` - Utility intelligence cache
- `st.session_state.market_snapshots` - Market snapshots cache

### Database Integration

The module expects your database to be in `st.session_state.db` with structure:
```python
{
    'sites': {
        'site_id': {...site_data...},
    },
    # other collections
}
```

If your structure differs, update the `_get_available_sites()` function in `diagnosis_page.py`.

---

## Customization

### Add More Utilities to Lookup

Edit `triage/enrichment.py` and expand the `UTILITY_LOOKUP` dictionary:

```python
UTILITY_LOOKUP = {
    'STATE_CODE': {
        'county_name': {
            'utility': 'Utility Name',
            'iso': 'ISO_CODE',
            'parent': 'Parent Company',
            'type': 'vertically_integrated',
        },
        # Add more counties...
    },
}
```

### Customize Prompts

Edit `triage/prompts.py` to adjust AI prompts:
- `TRIAGE_PROMPT` - Quick triage analysis
- `DIAGNOSIS_PROMPT` - Full diagnosis
- `UTILITY_INTEL_PROMPT` - Utility research
- `MARKET_SNAPSHOT_PROMPT` - Market analysis

### Add Custom Red Flag Categories

Edit `triage/models.py` to add new categories:

```python
class RedFlagCategory(Enum):
    POWER = "power"
    LAND = "land"
    EXECUTION = "execution"
    COMMERCIAL = "commercial"
    TIMELINE = "timeline"
    WATER = "water"  # Add new category
    # etc.
```

---

## Troubleshooting

### "GEMINI_API_KEY not found"
Add the key to `.streamlit/secrets.toml`

### "Module not found: triage"
Ensure the `triage/` folder is in your app directory and has `__init__.py`

### JSON Parse Errors
The Gemini responses sometimes include markdown. The engine has fallback parsing, but if issues persist, check `engine.py` `call_gemini_structured()` function.

### Google Sheets Permission Errors
Ensure your service account has edit access to the spreadsheet.

---

## What's Included

✅ **Phase 1: Quick Triage**
- Minimal intake form (county, state, MW, timeline)
- Auto-enrichment from county/state lookup
- Gemini-powered red flag analysis
- Verdict determination (KILL/CONDITIONAL/PASS)
- Triage log for pattern analysis

✅ **Phase 2: Full Diagnosis**
- Site selection from database
- Developer claim validation
- Comprehensive research via Gemini
- Timeline validation
- Utility assessment
- Competitive landscape analysis
- Actionable recommendations

✅ **Intelligence Center**
- Utility intelligence management
- Validated overrides (proprietary intel)
- Market snapshots
- Industry benchmarks
- Coverage dashboard

✅ **Integration Points**
- Program Tracker intelligence summary
- Site Database intelligence tab
- PPTX export intelligence slides
- Google Sheets persistence

---

## Next Steps After Integration

1. **Test the triage flow** with a known opportunity
2. **Populate utility lookup** for your focus markets
3. **Add validated overrides** from utility conversations
4. **Run diagnosis** on existing sites to populate intelligence
5. **Generate market snapshots** for target regions
6. **Review intelligence coverage** dashboard regularly
