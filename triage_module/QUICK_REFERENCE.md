# Quick Reference - Triage & Intelligence System

## 🚀 Quick Start

### 1. Copy Module
```bash
cp -r triage/ /path/to/portfolio_manager/
```

### 2. Add Navigation (streamlit_app.py)
```python
from triage import show_quick_triage, show_full_diagnosis, show_intelligence_center

# In your nav routing:
if page == "triage":
    show_quick_triage()
elif page == "diagnosis":
    show_full_diagnosis()
elif page == "intelligence":
    show_intelligence_center()
```

### 3. Add Google Sheets Columns
**Sites sheet - add columns:**
```
phase, triage_date, triage_verdict, triage_red_flags_json, claimed_timeline,
triage_source, triage_contact, triage_power_story, diagnosis_date, diagnosis_json,
validated_timeline, timeline_risk, claim_validation_json, diagnosis_recommendation,
diagnosis_top_risks, diagnosis_follow_ups, research_summary, last_research_date
```

**Create new sheet: Triage_Log**

---

## 📋 Key Imports

```python
# Everything from one import
from triage import (
    # Core functions
    run_triage,
    run_diagnosis,
    research_utility,
    
    # Pages
    show_quick_triage,
    show_full_diagnosis,
    show_intelligence_center,
    
    # Data classes
    TriageIntake,
    TriageResult,
    DiagnosisResult,
    
    # Tracker integration
    render_intelligence_summary,
    show_intel_summary_widget,
    
    # PPTX integration
    add_all_intelligence_slides,
)
```

---

## 🔧 Core Functions

### run_triage()
```python
intake = TriageIntake(
    county="Tulsa",
    state="OK",
    claimed_mw=200,
    claimed_timeline="Q4 2028",
    power_story="Developer says utility confirmed capacity",  # optional
)
result = run_triage(intake)

# Result contains:
result.verdict        # KILL, CONDITIONAL, or PASS
result.recommendation # One sentence summary
result.red_flags      # List of RedFlag objects
result.enrichment     # Auto-detected utility, ISO, etc.
result.next_steps     # Suggested actions
```

### run_diagnosis()
```python
site_data = {
    'name': 'Tulsa Metro Hub',
    'county': 'Tulsa',
    'state': 'OK',
    'utility': 'PSO',
    'iso': 'SPP',
    'target_mw': 200,
    'claimed_timeline': 'Q4 2028',
}

result = run_diagnosis(
    site_data=site_data,
    developer_claims=["Utility confirmed capacity", "24-month timeline"],
)

# Result contains:
result.recommendation       # GO, CONDITIONAL_GO, or NO_GO
result.validated_timeline   # Realistic timeline
result.timeline_risk        # on_track, at_risk, not_credible
result.claim_validations    # List of validated claims
result.utility_assessment   # Utility position analysis
result.competitive_context  # Market landscape
result.top_risks           # Key risks
result.follow_up_actions   # Required next steps
```

---

## 📊 Verdicts & Recommendations

### Triage Verdicts
| Verdict | Meaning | Action |
|---------|---------|--------|
| 🔴 KILL | Fatal flaw found | Archive, document pattern |
| 🟡 CONDITIONAL | Concerns exist | Validate before proceeding |
| 🟢 PASS | No major issues | Advance to Phase 2 |

### Diagnosis Recommendations
| Recommendation | Meaning |
|---------------|---------|
| 🟢 GO | Proceed with deal |
| 🟡 CONDITIONAL_GO | Proceed with specific conditions |
| 🔴 NO_GO | Do not proceed |

### Timeline Risk
| Risk | Meaning |
|------|---------|
| ✅ on_track | Claimed timeline achievable |
| ⚠️ at_risk | Timeline aggressive but possible |
| ❌ not_credible | Timeline not realistic |

---

## 🗺️ Utility Lookup Coverage

### States with full county coverage:
- **OK** - PSO (eastern), OG&E (central/western), Xcel/SPS (panhandle)
- **TX** - Oncor, CenterPoint, AEP Texas, Xcel/SPS, Austin Energy, CPS Energy
- **KS** - Evergy
- **AR** - SWEPCO, OGE, Entergy
- **MO** - Evergy, Ameren, Empire/Liberty

### To add more utilities:
Edit `triage/enrichment.py` → `UTILITY_LOOKUP` dict

---

## 📑 PPTX Integration

```python
from triage import add_all_intelligence_slides

# In your export function:
add_all_intelligence_slides(
    prs=prs,
    site_data=site_data,
    include_utility_detail=True,
    include_competitive=True,
)
```

Adds slides:
1. **Intelligence Assessment** - Timeline, recommendation, risks, actions
2. **Utility Assessment** - Appetite, capacity, timeline intel
3. **Competitive Landscape** - Projects, competitors, differentiation

---

## 📊 Program Tracker Integration

```python
from triage import render_intelligence_summary, show_intel_summary_widget

# In Portfolio Summary:
render_intelligence_summary(db.get('sites', {}))

# In sidebar:
show_intel_summary_widget(db.get('sites', {}))
```

Shows:
- Research coverage bar
- Timeline risk distribution
- Attention required alerts
- Triage funnel metrics

---

## 🔐 Validated Overrides

The key competitive advantage - when your proprietary intel contradicts public research:

```python
# In Intelligence Center → Utility Intel → Add Override

{
    "field": "energization_timeline",
    "public_value": "2028-2029 (from IRP)",
    "validated_value": "2031+",
    "confidence": "High",
    "source": "Direct conversation 2025-11-15"
}
```

These overrides feed into triage/diagnosis to give you the real story, not the public narrative.

---

## 📁 Files Reference

```
triage/
├── __init__.py           # All exports
├── models.py             # Data classes, enums
├── enrichment.py         # Utility lookup, auto-enrichment
├── prompts.py            # Gemini prompts
├── engine.py             # Core triage/diagnosis logic
├── page.py               # Quick Triage UI
├── diagnosis_page.py     # Full Diagnosis UI
├── intelligence_page.py  # Intelligence Center UI
├── tracker_integration.py # Program Tracker components
├── pptx_integration.py   # PPTX slide functions
└── storage.py            # Google Sheets operations
```

---

## ⚡ Session State Keys

```python
st.session_state.triage_result      # Last triage result
st.session_state.triage_intake      # Last intake data
st.session_state.diagnosis_result   # Last diagnosis result
st.session_state.utility_intel_db   # Utility intel cache
st.session_state.market_snapshots   # Market snapshot cache
st.session_state.selected_utility   # Selected utility in Intel Center
```
