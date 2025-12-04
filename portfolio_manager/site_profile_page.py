"""
Site Profile Builder Page
==========================
Streamlit page for building complete Site Profiles using:
1. Auto-mapped data from existing app fields
2. AI research using lat/lon coordinates
3. Human input for site-specific knowledge

Integrates with pptx_export for Site Profile slide generation.
"""

import streamlit as st
import json
from typing import Dict, Optional
from datetime import datetime

# Import profile builder
try:
    from .site_profile_builder import (
        SiteProfileBuilder, 
        SiteProfileData,
        get_human_input_form_fields,
        map_app_to_profile,
        AI_RESEARCHABLE_FIELDS,
        HUMAN_INPUT_FIELDS,
    )
    from .pptx_export import export_site_to_pptx, ExportConfig
    PROFILE_BUILDER_AVAILABLE = True
except ImportError as e:
    PROFILE_BUILDER_AVAILABLE = False
    print(f"Profile builder not available: {e}")

# LLM integration for AI research
try:
    from .llm_integration import get_chat_client
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_profile_state():
    """Initialize session state for profile builder."""
    if 'profile_builder' not in st.session_state:
        st.session_state.profile_builder = None
    if 'profile_site_id' not in st.session_state:
        st.session_state.profile_site_id = None
    if 'ai_research_results' not in st.session_state:
        st.session_state.ai_research_results = {}
    if 'human_inputs' not in st.session_state:
        st.session_state.human_inputs = {}
    if 'profile_expanded_sections' not in st.session_state:
        st.session_state.profile_expanded_sections = set()


# =============================================================================
# COMPLETION STATUS DISPLAY
# =============================================================================

def show_completion_status(builder: SiteProfileBuilder):
    """Display profile completion metrics."""
    status = builder.get_completion_status()
    
    # Overall progress
    st.markdown(f"### Profile Completion: {status['overall']}%")
    st.progress(status['overall'] / 100)
    
    # Category breakdown
    cols = st.columns(4)
    
    with cols[0]:
        st.metric("📍 Location", f"{status['location']}%")
    with cols[1]:
        st.metric("🏠 Ownership", f"{status['ownership']}%")
    with cols[2]:
        st.metric("⚡ Infrastructure", f"{status['infrastructure']}%")
    with cols[3]:
        st.metric("⚠️ Risk", f"{status['risk']}%")
    
    # Show filled fields count
    st.caption(f"{status['filled_count']} of {status['total_count']} fields populated")


def show_field_status(builder: SiteProfileBuilder):
    """Show what's filled vs missing."""
    filled = builder.get_filled_fields()
    missing = builder.get_missing_fields()
    
    with st.expander(f"✅ Filled Fields ({len(filled)})", expanded=False):
        if filled:
            cols = st.columns(3)
            for i, field in enumerate(sorted(filled)):
                value = getattr(builder.profile, field)
                if value and str(value) not in ['TBD', '', '0', '0.0']:
                    with cols[i % 3]:
                        display_val = str(value)[:30] + "..." if len(str(value)) > 30 else str(value)
                        st.markdown(f"**{field}**: {display_val}")
        else:
            st.info("No fields filled yet")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander(f"🔍 Needs AI Research ({len(missing['ai_research'])})", expanded=False):
            for field, desc in missing['ai_research']:
                st.markdown(f"• **{field}**: _{desc}_")
    
    with col2:
        with st.expander(f"✍️ Needs Human Input ({len(missing['human_input'])})", expanded=False):
            for field, desc in missing['human_input']:
                st.markdown(f"• **{field}**: _{desc}_")


# =============================================================================
# AI RESEARCH SECTION
# =============================================================================

def show_ai_research_section(builder: SiteProfileBuilder, site_data: Dict, site_id: str):
    """Section for AI-powered location research."""
    st.markdown("---")
    st.subheader("🔍 AI Location Research")
    
    lat = site_data.get('latitude')
    lon = site_data.get('longitude')
    
    if not (lat and lon):
        st.warning("""
        **Coordinates Required**
        
        To use AI research, add latitude and longitude to this site.
        You can get coordinates from:
        - Google Maps (right-click → "What's here?")
        - PACES GIS analysis
        - Site documentation
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            new_lat = st.number_input("Latitude", value=0.0, format="%.6f", key="new_lat")
        with col2:
            new_lon = st.number_input("Longitude", value=0.0, format="%.6f", key="new_lon")
        
        if st.button("Save Coordinates"):
            if new_lat and new_lon:
                # Save to Google Sheets database
                try:
                    if hasattr(st.session_state, 'db') and 'sites' in st.session_state.db:
                        db = st.session_state.db
                        
                        if site_id in db['sites']:
                            # Update coordinates in database
                            db['sites'][site_id]['latitude'] = new_lat
                            db['sites'][site_id]['longitude'] = new_lon
                            
                            # Save to Google Sheets
                            from .streamlit_app import save_database
                            save_database(db)
                            
                            st.success(f"✅ Coordinates saved to Google Sheets! Latitude: {new_lat}, Longitude: {new_lon}")
                            st.info("🔄 Click the Refresh button above to reload with coordinates and enable AI research.")
                        else:
                            st.error(f"Site {site_id} not found in database")
                    else:
                        st.error("No database connection available. Please visit Portfolio Manager first.")
                except Exception as e:
                    st.error(f"Failed to save coordinates: {e}")
                    import traceback
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())
        return
    
    st.success(f"📍 Coordinates: {lat}, {lon}")
    
    # Show what AI can research
    with st.expander("What AI Will Research", expanded=False):
        st.markdown("""
        Using the site coordinates, AI will research:
        
        **Distance Calculations**
        - Nearest town/city and distance
        - Nearest commercial airport
        - Nearest highway interchange
        - Rail access
        
        **Natural Hazards** (FEMA, USGS)
        - Flood zone designation
        - Seismic risk level
        - Hurricane/tornado risk
        
        **Demographics** (Census, BLS)
        - Population within 30 miles
        - Unemployment rate
        
        **Utilities**
        - Electric utility territory
        - Gas/water providers
        - Current zoning (if public)
        """)
    
    # Research button
    col1, col2 = st.columns([1, 2])
    
    with col1:
        research_clicked = st.button("🚀 Research with AI", type="primary", use_container_width=True)
    
    with col2:
        if st.session_state.ai_research_results:
            st.success(f"✅ Research complete - {len(st.session_state.ai_research_results)} fields found")
    
    if research_clicked:
        with st.spinner("Researching location data..."):
            prompt = builder.get_research_prompt()
            
            # Try to use LLM integration
            if LLM_AVAILABLE:
                try:
                    # Use direct Gemini call for location research
                    # PortfolioChat is designed for general queries, not structured research
                    import google.generativeai as genai
                    import os
                    
                    # Get API key
                    api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
                    
                    if api_key:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel("models/gemini-2.0-flash-exp")
                        
                        # Build research-specific prompt
                        research_prompt = f"""You are a location research assistant. Research this data center site location and return ONLY a JSON object with the following fields:

{prompt}

CRITICAL: Return ONLY valid JSON with no explanation, no markdown, no additional text. Just the JSON object starting with {{ and ending with }}.

Example format:
{{
  "nearest_town": "City Name",
  "distance_to_town": "X miles",
  "airport_name": "Airport Name (CODE)",
  ...
}}"""
                        
                        response = model.generate_content(research_prompt)
                        response_text = response.text
                        
                        
                        # Parse JSON from response
                        try:
                            # Multiple strategies to extract JSON
                            json_str = response_text.strip()
                            
                            # Strategy 1: Look for ```json blocks
                            if "```json" in response_text:
                                json_str = response_text.split("```json")[1].split("```")[0].strip()
                            # Strategy 2: Look for generic ``` blocks
                            elif "```" in response_text:
                                json_str = response_text.split("```")[1].split("```")[0].strip()
                            # Strategy 3: Look for { } braces
                            elif "{" in response_text and "}" in response_text:
                                import re
                                match = re.search(r'\{.*\}', response_text, re.DOTALL)
                                if match:
                                    json_str = match.group(0)
                            
                            # Try to parse
                            results = json.loads(json_str)
                            
                            # Validate it's a dict
                            if not isinstance(results, dict):
                                raise ValueError("Parsed JSON is not a dictionary")
                            
                            st.session_state.ai_research_results = results
                            builder.apply_ai_research(results)
                            
                            # Auto-save to Google Sheets
                            try:
                                profile = builder.profile
                                profile_dict = {
                                    field: getattr(profile, field) 
                                    for field in SiteProfileData.__dataclass_fields__
                                    if getattr(profile, field) and str(getattr(profile, field)) not in ['', 'TBD', '0', '0.0']
                                }
                                
                                if hasattr(st.session_state, 'db') and 'sites' in st.session_state.db:
                                    db = st.session_state.db
                                    if site_id in db['sites']:
                                        db['sites'][site_id]['profile_json'] = json.dumps(profile_dict)
                                        from .streamlit_app import save_database
                                        save_database(db)
                                        st.success(f"✅ Research complete! {len(results)} fields populated and saved to Google Sheets.")
                                    else:
                                        st.success("Research complete!")
                                else:
                                    st.success("Research complete!")
                            except Exception as save_err:
                                st.warning(f"Research complete but auto-save failed: {save_err}")
                            
                            st.rerun()
                        except (json.JSONDecodeError, ValueError) as e:
                            st.error(f"Could not parse AI response as JSON: {e}")
                            st.info("The AI might have returned text instead of JSON. Try the manual paste option below.")
                            with st.expander("Raw Response (click to see what AI returned)", expanded=True):
                                st.code(response_text if response_text else "Empty response")
                                
                            # Show manual input option
                            st.markdown("---")
                            st.markdown("**Manual Fix: Paste Valid JSON**")
                            manual_json = st.text_area("Paste corrected JSON here:", height=200, key="fix_ai_json")
                            if st.button("Apply Manual JSON"):
                                try:
                                    results = json.loads(manual_json)
                                    st.session_state.ai_research_results = results
                                    builder.apply_ai_research(results)
                                    st.success("Research applied!")
                                    st.rerun()
                                except json.JSONDecodeError as e2:
                                    st.error(f"Invalid JSON: {e2}")
                    else:
                        st.error("Gemini API key not configured. Please add GEMINI_API_KEY to secrets.toml")
                except Exception as e:
                    st.error(f"AI research failed: {e}")
            else:
                # Show prompt for manual research
                st.info("LLM not configured. Copy this prompt to use with Claude or ChatGPT:")
                with st.expander("Research Prompt", expanded=True):
                    st.code(prompt)
                
                # Manual JSON input
                st.markdown("**Paste AI Response (JSON):**")
                manual_json = st.text_area("JSON Response", height=200, key="manual_ai_json")
                if st.button("Apply Research Results"):
                    try:
                        results = json.loads(manual_json)
                        st.session_state.ai_research_results = results
                        builder.apply_ai_research(results)
                        st.success("Research applied!")
                        st.rerun()
                    except json.JSONDecodeError as e:
                        st.error(f"Invalid JSON: {e}")
    
    # Show current AI research results
    if st.session_state.ai_research_results:
        with st.expander("📊 AI Research Results", expanded=True):
            results = st.session_state.ai_research_results
            
            cols = st.columns(2)
            items = list(results.items())
            mid = len(items) // 2
            
            with cols[0]:
                for key, value in items[:mid]:
                    st.markdown(f"**{key}**: {value}")
            
            with cols[1]:
                for key, value in items[mid:]:
                    st.markdown(f"**{key}**: {value}")


# =============================================================================
# HUMAN INPUT FORMS
# =============================================================================

def show_human_input_section(builder: SiteProfileBuilder):
    """Section for human input forms."""
    st.markdown("---")
    st.subheader("✍️ Site-Specific Information")
    
    st.info("""
    These fields require site-specific knowledge from:
    - Property owner negotiations
    - Site visits and surveys
    - Environmental studies
    - Utility consultations
    """)
    
    form_sections = get_human_input_form_fields()
    
    # Initialize human inputs from session state
    inputs = st.session_state.human_inputs.copy()
    
    # Also pull any existing values from the profile
    for field in HUMAN_INPUT_FIELDS.keys():
        if field not in inputs:
            existing = getattr(builder.profile, field, None)
            if existing and str(existing) not in ['', 'TBD', '0', '0.0', 'False']:
                inputs[field] = existing
    
    # Create form
    with st.form("human_input_form"):
        for section in form_sections:
            with st.expander(f"📋 {section['section']}", expanded=section['section'] in ['Ownership & Price', 'Utility Details']):
                cols = st.columns(2)
                
                for i, field_def in enumerate(section['fields']):
                    with cols[i % 2]:
                        field_name = field_def['name']
                        label = field_def['label']
                        field_type = field_def['type']
                        help_text = field_def.get('help', '')
                        current_value = inputs.get(field_name, '')
                        
                        if field_type == 'text':
                            inputs[field_name] = st.text_input(
                                label, 
                                value=str(current_value) if current_value else '',
                                help=help_text,
                                key=f"hi_{field_name}"
                            )
                        
                        elif field_type == 'number':
                            try:
                                default_val = float(current_value) if current_value else 0.0
                            except (ValueError, TypeError):
                                default_val = 0.0
                            inputs[field_name] = st.number_input(
                                label,
                                value=default_val,
                                help=help_text,
                                key=f"hi_{field_name}"
                            )
                        
                        elif field_type == 'select':
                            options = field_def.get('options', ['TBD'])
                            try:
                                idx = options.index(str(current_value)) if current_value in options else 0
                            except (ValueError, IndexError):
                                idx = 0
                            inputs[field_name] = st.selectbox(
                                label,
                                options=options,
                                index=idx,
                                help=help_text,
                                key=f"hi_{field_name}"
                            )
        
        submitted = st.form_submit_button("💾 Save Site Information", type="primary", use_container_width=True)
        
        if submitted:
            # Filter out empty values
            filtered_inputs = {k: v for k, v in inputs.items() if v and str(v) not in ['', 'TBD', '0', '0.0', 'Unknown']}
            st.session_state.human_inputs = filtered_inputs
            builder.apply_human_inputs(filtered_inputs)
            st.success(f"Saved {len(filtered_inputs)} fields!")
            st.rerun()


# =============================================================================
# PREVIEW & EXPORT
# =============================================================================

def show_preview_section(builder: SiteProfileBuilder, site_data: Dict):
    """Preview the Site Profile and export options."""
    st.markdown("---")
    st.subheader("📄 Site Profile Preview")
    
    profile = builder.profile
    descriptions = profile.to_description_dict()
    
    # Preview table
    preview_data = []
    for item, desc in descriptions.items():
        # Truncate for display
        display_desc = desc[:100] + "..." if len(desc) > 100 else desc
        status = "✅" if desc and desc != "TBD" and not desc.startswith("TBD") else "⚠️"
        preview_data.append({
            "Status": status,
            "Item": item,
            "Description": display_desc
        })
    
    st.dataframe(preview_data, use_container_width=True, hide_index=True)
    
    # Export section
    st.markdown("---")
    st.subheader("📥 Export to PowerPoint")
    
    st.info("""💡 **Template Setup:** Place your PowerPoint template with the 17-row Site Profile table in your project folder and enter the path below. 
    If you don't have a template yet, you can skip this section and export once you create one.""")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Check if Sample Site Profile Template exists
        import os
        default_template = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Sample Site Profile Template.pptx')
        if os.path.exists(default_template):
            default_path = default_template
        else:
            default_path = st.session_state.get('export_template_path', '')
        
        template_path = st.text_input(
            "Template Path (Optional)",
            value=default_path,
            help="Path to your PowerPoint template with Site Profile table",
            placeholder="Leave empty to skip for now"
        )
    
    with col2:
        output_name = st.text_input(
            "Output Filename",
            value=f"{site_data.get('name', 'Site').replace(' ', '_')}_Profile.pptx"
        )
    
    # Export options
    st.markdown("**Include Slides:**")
    cols = st.columns(4)
    with cols[0]:
        inc_trajectory = st.checkbox("Capacity Trajectory", value=True)
    with cols[1]:
        inc_infrastructure = st.checkbox("Infrastructure", value=True)
    with cols[2]:
        inc_scores = st.checkbox("Score Analysis", value=True)
    with cols[3]:
        inc_market = st.checkbox("Market Analysis", value=True)
    
    if st.button("📤 Export PPTX", type="primary", use_container_width=True):
        import os
        
        if not template_path or template_path.strip() == '':
            st.warning("⚠️ No template path provided. Please add a template path to export to PowerPoint.")
            st.info("""To use PowerPoint export:
            1. Create or obtain a PowerPoint template with the Site Profile table structure
            2. Save it as `Sample Site Profile Template.pptx` in your project root, OR
            3. Enter the path to your template in the field above""")
        elif not os.path.exists(template_path):
            st.error(f"Template not found: {template_path}")
            st.info("Please check the path and make sure the file exists.")
        else:
            try:
                # Build export data
                export_data = site_data.copy()
                export_data['profile'] = profile
                
                config = ExportConfig(
                    include_capacity_trajectory=inc_trajectory,
                    include_infrastructure=inc_infrastructure,
                    include_score_analysis=inc_scores,
                    include_market_analysis=inc_market,
                )
                
                output_path = f"/tmp/{output_name}"
                result = export_site_to_pptx(export_data, template_path, output_path, config)
                
                with open(result, 'rb') as f:
                    st.download_button(
                        "⬇️ Download PPTX",
                        f,
                        file_name=output_name,
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )
                
                st.success(f"✅ Export complete: {output_name}")
                
            except Exception as e:
                st.error(f"Export failed: {e}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())


# =============================================================================
# SAVE TO DATABASE
# =============================================================================

def show_save_section(builder: SiteProfileBuilder, site_id: str, data_layer):
    """Save enriched profile data back to database."""
    st.markdown("---")
    st.subheader("💾 Save Enriched Data")
    
    st.info("""
    Save the researched and input data back to the portfolio database.
    This will update the site record with all the new information.
    """)
    
    # Show what will be saved
    profile = builder.profile
    save_fields = {}
    
    # Map profile fields back to app fields
    if profile.electric_utility:
        save_fields['utility'] = profile.electric_utility
    if profile.total_acres:
        save_fields['acreage'] = profile.total_acres
    if profile.voltage_kv:
        save_fields['voltage_kv'] = profile.voltage_kv
    if profile.coordinates:
        parts = profile.coordinates.split(',')
        if len(parts) == 2:
            try:
                save_fields['latitude'] = float(parts[0].strip())
                save_fields['longitude'] = float(parts[1].strip())
            except ValueError:
                pass
    
    # Store full profile as JSON
    profile_dict = {
        field: getattr(profile, field) 
        for field in SiteProfileData.__dataclass_fields__
        if getattr(profile, field) and str(getattr(profile, field)) not in ['', 'TBD', '0', '0.0']
    }
    save_fields['profile_json'] = json.dumps(profile_dict)
    
    with st.expander(f"Fields to Save ({len(save_fields)})", expanded=False):
        for key, value in save_fields.items():
            if key != 'profile_json':
                st.markdown(f"**{key}**: {value}")
            else:
                st.markdown(f"**{key}**: _{len(profile_dict)} profile fields_")
    
    if st.button("💾 Save to Portfolio", type="primary"):
        from datetime import datetime
        
        try:
            # Try first to use Portfolio Manager's Google Sheets database
            if hasattr(st.session_state, 'db') and 'sites' in st.session_state.db:
                db = st.session_state.db
                
                if site_id in db['sites']:
                    # Merge with new data
                    db['sites'][site_id].update(save_fields)
                    db['sites'][site_id]['last_updated'] = datetime.now().isoformat()
                    
                    # Save back to Google Sheets
                    from .streamlit_app import save_database
                    save_database(db)
                    
                    st.success(f"✅ Saved {len(save_fields)} fields to {site_id} (Google Sheets)")
                    st.balloons()
                else:
                    st.error(f"Site {site_id} not found in database")
            else:
                # Fallback to JSON file
                import os
                db_path = os.path.join(os.path.dirname(__file__), 'site_database.json')
                
                if os.path.exists(db_path):
                    with open(db_path, 'r') as f:
                        db_data = json.load(f)
                    
                    # Get the sites dict
                    sites = db_data.get('sites', db_data)
                    
                    if site_id in sites:
                        # Merge with new data
                        sites[site_id].update(save_fields)
                        sites[site_id]['last_updated'] = datetime.now().isoformat()
                        
                        # Save back to database
                        db_data['sites'] = sites
                        with open(db_path, 'w') as f:
                            json.dump(db_data, f, indent=2)
                        
                        st.success(f"✅ Saved {len(save_fields)} fields to {site_id} (JSON file)")
                        st.balloons()
                    else:
                        st.error(f"Site {site_id} not found in database")
                else:
                    st.error(f"Database not found: {db_path}")
                    
        except Exception as e:
            st.error(f"Save failed: {e}")
            import traceback
            with st.expander("Error Details"):
                st.code(traceback.format_exc())


# =============================================================================
# MAIN PAGE
# =============================================================================

def show_site_profile_builder(sites: Dict, data_layer=None):
    """Main page for Site Profile Builder."""
    st.title("📋 Site Profile Builder")
    
    if not PROFILE_BUILDER_AVAILABLE:
        st.error("Site Profile Builder module not available. Check imports.")
        return
    
    init_profile_state()
    
    # Site selector
    if not sites:
        st.warning("No sites in portfolio. Add sites first.")
        return
    
    site_options = {f"{s.get('name', sid)} ({s.get('state', 'N/A')})": sid for sid, s in sites.items()}
    
    col1, col2 = st.columns([3, 1])
    with col1:
        selected = st.selectbox(
            "Select Site",
            options=list(site_options.keys()),
            key="profile_site_select"
        )
    
    site_id = site_options[selected]
    site_data = sites[site_id]
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh"):
            st.session_state.profile_builder = None
            st.session_state.ai_research_results = {}
            st.session_state.human_inputs = {}
            st.rerun()
    
    # Check if site changed
    if st.session_state.profile_site_id != site_id:
        st.session_state.profile_site_id = site_id
        st.session_state.profile_builder = None
        st.session_state.ai_research_results = {}
        st.session_state.human_inputs = {}
    
    # Create or get builder
    if st.session_state.profile_builder is None:
        st.session_state.profile_builder = SiteProfileBuilder(site_data)
    
    builder = st.session_state.profile_builder
    
    # Apply any stored AI research or human inputs
    if st.session_state.ai_research_results:
        builder.apply_ai_research(st.session_state.ai_research_results)
    if st.session_state.human_inputs:
        builder.apply_human_inputs(st.session_state.human_inputs)
    
    # Show site summary
    st.markdown(f"""
    **Site:** {site_data.get('name', 'Unknown')}  
    **State:** {site_data.get('state', 'N/A')} | **Utility:** {site_data.get('utility', 'N/A')} | **Target:** {site_data.get('target_mw', 0)} MW
    """)
    
    # Tabs for workflow
    tabs = st.tabs(["📊 Status", "🔍 AI Research", "✍️ Human Input", "📄 Preview & Export"])
    
    with tabs[0]:
        show_completion_status(builder)
        show_field_status(builder)
    
    with tabs[1]:
        show_ai_research_section(builder, site_data, site_id)
    
    with tabs[2]:
        show_human_input_section(builder)
    
    with tabs[3]:
        show_preview_section(builder, site_data)
        show_save_section(builder, site_id, data_layer)


# =============================================================================
# STANDALONE MODE
# =============================================================================

if __name__ == "__main__":
    st.set_page_config(page_title="Site Profile Builder", layout="wide")
    
    # Demo data
    demo_sites = {
        'tulsa_metro': {
            'name': 'Tulsa Metro Hub',
            'state': 'Oklahoma',
            'county': 'Tulsa',
            'utility': 'OG&E',
            'target_mw': 600,
            'acreage': 300,
            'latitude': 36.1234,
            'longitude': -95.9876,
            'zoning_stage': 2,
            'power_stage': 3,
        }
    }
    
    show_site_profile_builder(demo_sites)
