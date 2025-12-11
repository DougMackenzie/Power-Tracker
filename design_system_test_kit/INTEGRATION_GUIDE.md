# Design System Module Integration Guide

## Quick Start

### 1. Add Module to Your App

Copy `design_system_module.py` to your `portfolio_manager/` folder.

### 2. Import in Your Main App

```python
# In streamlit_app.py, add to imports:
from design_system_module import (
    DesignSystemAnalyzer, 
    DesignSystem, 
    StyleEnforcer,
    render_design_system_page  # Optional: adds a full management page
)
```

### 3. Add Navigation (Optional Full Page)

```python
# In your navigation/sidebar:
pages = ["Sites", "Portfolio", "Design System"]  # Add "Design System"

# In your page router:
if page == "Design System":
    render_design_system_page(st)
```

### 4. Use in Your PPTX Export

Replace your current styling with enforced styling:

```python
# Load your design system (do this once at app start)
if 'design_system' not in st.session_state:
    try:
        st.session_state['design_system'] = DesignSystem.load("design_system.json")
    except:
        # Use defaults if no design system trained yet
        st.session_state['design_system'] = DesignSystem(name="Default")

# In your PPTX export function:
def export_site_pptx(site_data):
    from pptx import Presentation
    from pptx.util import Inches, Pt
    
    ds = st.session_state['design_system']
    enforcer = StyleEnforcer(ds)
    
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Title - uses enforced styling
    title_box = slide.shapes.add_textbox(
        Inches(ds.margin_left), 
        Inches(ds.margin_top),
        Inches(12), 
        Inches(1)
    )
    enforcer.set_text_with_style(
        title_box.text_frame, 
        site_data['name'], 
        "title"  # Uses design system's title style
    )
    
    # Content - enforced body style
    content_box = slide.shapes.add_textbox(...)
    enforcer.set_text_with_style(content_box.text_frame, "...", "body")
    
    return prs
```

---

## Training a Design System

### From Code:

```python
analyzer = DesignSystemAnalyzer(verbose=True)
ds = analyzer.analyze([
    "path/to/presentation1.pptx",
    "path/to/presentation2.pptx",
    # ... more files
], name="My Organization")

ds.save("design_system.json")
```

### From Streamlit UI:

Use `render_design_system_page(st)` which provides:
- Upload multiple PPTX files
- Automatic analysis
- Preview extracted colors/fonts
- Save to JSON

---

## Available Typography Styles

| Style | Typical Use |
|-------|-------------|
| `title` | Slide titles (large, bold) |
| `h1` | Section headers |
| `h2` | Subsection headers |
| `body` | Regular content text |
| `caption` | Footnotes, small text |
| `metric` | Large KPI numbers |

---

## Files Included

| File | Purpose |
|------|---------|
| `design_system_module.py` | Drop-in module (all-in-one) |
| `sample_site_profile.pptx` | Test file - site profile |
| `sample_portfolio_summary.pptx` | Test file - portfolio |
| `sample_market_analysis.pptx` | Test file - market analysis |
| `test_design_system.json` | Pre-extracted design system |
| `generate_samples.py` | Script that created samples |

---

## Testing

1. Upload all 3 sample PPTX files to the Design System page
2. Click "Analyze & Train"
3. Verify it extracts:
   - Primary color: #1A2B4A (Navy)
   - Font: Arial
   - Title: 28pt bold
4. Save the design system
5. Generate a test presentation to verify styling

---

## Integration with Existing PPTX Export

If you have existing `pptx_export.py`, here's how to integrate:

```python
# At the top of pptx_export.py:
from design_system_module import DesignSystem, StyleEnforcer

# In your export function:
def generate_site_profile(site: dict, design_system: DesignSystem = None):
    if design_system is None:
        design_system = DesignSystem()  # Uses defaults
    
    enforcer = StyleEnforcer(design_system)
    
    # Replace hardcoded styling:
    # OLD: run.font.name = "Arial"
    # OLD: run.font.size = Pt(28)
    # OLD: run.font.bold = True
    
    # NEW:
    enforcer.set_text_with_style(text_frame, "Title", "title")
```

This ensures ONE consistent style across all presentations!
