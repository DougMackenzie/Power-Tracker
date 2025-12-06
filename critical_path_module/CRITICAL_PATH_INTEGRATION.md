# Critical Path Module - Integration Instructions

## Files to Add

Copy these two files to your `portfolio_manager` folder:

1. **`critical_path.py`** - Core engine with all data models, templates, and logic
2. **`critical_path_page.py`** - Streamlit UI page

---

## Step 1: Add Google Sheets Column

Add this column to your `SHEET_COLUMNS` in `google_integration.py`:

```python
SHEET_COLUMNS = {
    # ... existing columns ...
    'critical_path_json': 'AK',  # Or next available column
}
```

Also add to `COLUMN_ORDER`:

```python
COLUMN_ORDER = [
    # ... existing columns ...
    'critical_path_json',
]
```

---

## Step 2: Update streamlit_app.py

### Add Import (near top with other imports):

```python
# Critical Path integration
try:
    from .critical_path_page import show_critical_path_page, get_critical_path_summary
    CRITICAL_PATH_AVAILABLE = True
except ImportError as e:
    CRITICAL_PATH_AVAILABLE = False
    print(f"Critical path not available: {e}")
```

### Add Navigation Option:

Find the navigation section and add:

```python
# In the sidebar navigation
pages = [
    "📊 Dashboard",
    "📈 Program Tracker",
    "🏭 Site Database",
    "⚡ Critical Path",     # ADD THIS
    "🗺️ State Analysis",
    "🔍 Research",
    # ... other pages
]

page = st.sidebar.radio("Navigation", pages)
```

### Add Page Router:

```python
# In the page routing section
if page == "⚡ Critical Path":
    if CRITICAL_PATH_AVAILABLE:
        show_critical_path_page()
    else:
        st.error("Critical Path module not available")
```

---

## Step 3: Update load_database() Function

In your `load_database()` function, add the new column to the headers list:

```python
headers = [
    # ... existing headers ...
    'critical_path_json',  # ADD THIS
]
```

And in the row parsing:

```python
for row in all_rows:
    # ... existing parsing ...
    
    # Add critical path data
    site['critical_path_json'] = row.get('critical_path_json', '')
```

---

## Step 4: Update save_database() Function

In your `save_database()` function, add the column to the row:

```python
row = [
    # ... existing fields ...
    site.get('critical_path_json', ''),  # ADD THIS
]
```

---

## Features Included

### Pre-Sale Phase (Seller Responsibilities):
- Site Control (LOI, PSA, Title, Survey)
- Power Studies (Screening, SIS, FS)
- Interconnection Agreement (IA/FA)
- Zoning Approval
- Environmental (Phase I ESA, Wetlands)
- Water Will-Serve
- Marketing/End User
- Transaction Close

### Post-Sale Phase (Buyer/Developer Responsibilities):
- Equipment Procurement
  - Transformers (2.5-5 year lead times)
  - Breakers (2.5-4 year lead times)
  - Switchgear
- BTM Generation (if applicable)
  - Gas Turbines (3-4 year lead times)
  - Gas Service
- Utility Construction
- Construction Financing
- Building Construction
- Energization

### Dynamic Configuration:
- Lead time overrides per site
- ISO-specific study durations
- Voltage-adjusted transformer lead times
- BTM on/off toggle
- Customer-provides-breakers option

### What-If Scenarios:
- Customer Conveys Breakers
- Utility Fast-Track Studies
- Early Transformer Procurement
- Bridge Power Strategy
- EaaS Provider for BTM

### Document Parsing:
- Parse emails/meeting minutes for updates
- Auto-detect milestone completions
- Extract lead time changes

---

## Data Storage

All critical path data is stored as JSON in a single column (`critical_path_json`).

This keeps your existing schema intact while adding all the new functionality.

The JSON structure includes:
- Configuration (MW, voltage, ISO, options)
- All milestone instances with dates/status
- Saved scenarios
- Calculated critical path
- Analysis results

---

## Usage Tips

1. **Initialize**: Select a site, click "Initialize Critical Path"
2. **Configure**: Adjust lead times in the Lead Times tab
3. **Track**: Update milestone status as things progress
4. **Analyze**: Use What-If scenarios to model acceleration options
5. **Document**: Paste emails to auto-detect updates

---

## Customization

### Add Custom Milestones

Edit `get_milestone_templates()` in `critical_path.py`:

```python
MilestoneTemplate(
    id="CUSTOM-01",
    name="My Custom Milestone",
    workstream=Workstream.POWER,
    phase=Phase.PRE_SALE,
    owner=Owner.CUSTOMER,
    duration_typical=8,
    predecessors=["PS-PWR-05"],
    description="Custom milestone description"
),
```

### Add Custom Scenarios

Edit `get_predefined_scenarios()` in `critical_path.py`:

```python
{
    'name': "My Custom Scenario",
    'description': "What if we do X?",
    'overrides': [
        {'milestone_id': 'POST-EQ-02', 'field': 'duration', 'new_value': 100},
    ]
}
```

### Adjust Default Lead Times

Edit `DEFAULT_LEAD_TIMES` in `critical_path.py`:

```python
DEFAULT_LEAD_TIMES = {
    'transformer_345kv': {'min': 130, 'typical': 156, 'max': 234},
    # ... adjust as needed
}
```
