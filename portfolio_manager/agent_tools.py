"""
Agent Tools for Portfolio Manager
=================================
This module defines the tools (functions) that the AI agent can call
to interact with the application state.
"""

import streamlit as st
from datetime import datetime
import json

def get_site_id_by_name(name: str) -> str:
    """Helper to find site ID by fuzzy name match."""
    sites = st.session_state.db.get('sites', {})
    name_lower = name.lower()
    
    # Exact match
    for site_id, site in sites.items():
        if site.get('name', '').lower() == name_lower:
            return site_id
            
    # Fuzzy match (substring)
    for site_id, site in sites.items():
        site_name_lower = site.get('name', '').lower()
        if name_lower in site_name_lower:
            return site_id
            
    # Token-based match (all words in search term must be in site name)
    search_tokens = name_lower.split()
    if search_tokens:
        for site_id, site in sites.items():
            site_name_lower = site.get('name', '').lower()
            if all(token in site_name_lower for token in search_tokens):
                return site_id
    
    return None

# --- Site Management Tools ---

def update_site_field(site_name: str, field: str, value: str):
    """
    Update a specific field for a site in the database.
    
    Args:
        site_name: Name of the site to update
        field: Field to update (e.g., 'target_mw', 'utility', 'state', 'zoning_status')
        value: New value for the field
    """
    site_id = get_site_id_by_name(site_name)
    if not site_id:
        return f"Error: Could not find site named '{site_name}'"
    
    site = st.session_state.db['sites'][site_id]
    
    # Normalize field name
    field_key = field.lower().replace(' ', '_')
    
    # Define top-level fields
    TOP_LEVEL_FIELDS = {
        'name', 'state', 'utility', 'target_mw', 'acreage', 'iso', 'county', 
        'developer', 'land_status', 'community_support', 'political_support',
        'dev_experience', 'capital_status', 'financial_status', 'last_updated',
        'client', 'total_fee_potential', 'contract_status',
        'site_control_stage', 'power_stage', 'marketing_stage', 'buyer_stage',
        'zoning_stage', 'water_stage', 'incentives_stage',
        'probability', 'weighted_fee', 'tracker_notes',
        'latitude', 'longitude', 'voltage_kv'
    }

    # Handle nested fields and special logic
    
    # 1. Voltage / Interconnection
    if field_key in ['voltage', 'voltage_kv', 'interconnection_voltage']:
        # Update top level
        site['voltage_kv'] = value
        # Update all phases if they exist
        if 'phases' in site and isinstance(site['phases'], list):
            for phase in site['phases']:
                if isinstance(phase, dict):
                    phase['voltage'] = value
                    phase['voltage_kv'] = value
        
        # Also update profile_json
        if 'profile_json' not in site: site['profile_json'] = {}
        site['profile_json']['voltage_kv'] = value
        site['profile_json']['interconnection_voltage'] = value
                    
    # 2. Environmental / ESA Status
    elif field_key in ['environmental_status', 'esa_status', 'phase_1_esa_status']:
        site['environmental_status'] = value
        # Update boolean flag based on string value
        if 'complete' in str(value).lower():
            site['environmental_complete'] = True
        elif 'progress' in str(value).lower() or 'started' in str(value).lower():
            site['environmental_complete'] = False
            
        # Also update profile_json
        if 'profile_json' not in site: site['profile_json'] = {}
        site['profile_json']['environmental_status'] = value
            
    # 3. Zoning Status
    elif field_key in ['zoning_status', 'zoning']:
        if 'non_power' not in site: site['non_power'] = {}
        site['non_power']['zoning_status'] = value
        # Map to zoning_stage int if possible
        val_lower = str(value).lower()
        if 'approved' in val_lower:
            site['zoning_stage'] = 3
        elif 'progress' in val_lower or 'submitted' in val_lower:
            site['zoning_stage'] = 2
        else:
            site['zoning_stage'] = 1
            
        # Also update profile_json
        if 'profile_json' not in site: site['profile_json'] = {}
        site['profile_json']['current_zoning'] = value
            
    # 4. Non-Power Infrastructure (Water, Fiber, Gas)
    elif field_key in ['water_source', 'water_provider', 'fiber_status', 'fiber_provider', 'gas_provider']:
        if 'non_power' not in site: site['non_power'] = {}
        site['non_power'][field_key] = value
        
        # Also update profile_json
        if 'profile_json' not in site: site['profile_json'] = {}
        site['profile_json'][field_key] = value
        
    # 5. Top Level Fields
    elif field_key in TOP_LEVEL_FIELDS:
        site[field_key] = value
        
    # 6. Fallback: Update profile_json (for Willing to Sell, Asking Price, etc.)
    else:
        if 'profile_json' not in site: site['profile_json'] = {}
        site['profile_json'][field_key] = value
        
    # Save to session state
    st.session_state.db['sites'][site_id] = site
    
    # Trigger persistence to Google Sheets
    if 'save_database_func' in st.session_state:
        try:
            st.session_state.save_database_func(st.session_state.db)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            st.error(f"Tool Error: {error_details}")
            return f"Updated in memory, but failed to save to Sheets: {str(e)}. Details: {error_details}"
            
    return f"Successfully updated {field} to '{value}' for {site.get('name')}"

def create_new_site(name: str, state: str, target_mw: int, acres: int = 0, voltage_kv: int = 0, latitude: float = 0.0, longitude: float = 0.0, status: str = "Prospect", schedule_json: str = "{}"):
    """
    Create a new site in the database.
    
    Args:
        name: Name of the new site
        state: State code (e.g., 'OK', 'TX')
        target_mw: Target capacity in MW
        acres: Total acreage (optional)
        voltage_kv: Interconnection voltage in kV (optional)
        latitude: Latitude coordinate (optional)
        longitude: Longitude coordinate (optional)
        status: Project status (optional)
        schedule_json: JSON string of schedule dict {year: mw} (optional)
    """
    import uuid
    new_id = str(uuid.uuid4())
    
    # Parse schedule if provided
    try:
        schedule = json.loads(schedule_json) if schedule_json else {}
    except:
        schedule = {}

    new_site = {
        'name': name,
        'state': state,
        'target_mw': target_mw,
        'acreage': acres,
        'voltage_kv': voltage_kv,
        'latitude': latitude,
        'longitude': longitude,
        'land_status': status,
        'utility': 'TBD',
        'last_updated': datetime.now().strftime("%Y-%m-%d"),
        'phases': [],
        'schedule': schedule,
        'profile_json': {
            'voltage_kv': voltage_kv,
            'interconnection_voltage': voltage_kv,
            'land_status': status
        }
    }
    
    if 'sites' not in st.session_state.db:
        st.session_state.db['sites'] = {}
        
    st.session_state.db['sites'][new_id] = new_site
    
    # Trigger persistence
    if 'save_database_func' in st.session_state:
        try:
            st.session_state.save_database_func(st.session_state.db)
        except Exception as e:
            return f"Created in memory, but failed to save to Sheets: {e}"
            
    return f"Created new site '{name}' in {state} with {target_mw}MW"

# --- Critical Path Tools ---

def add_milestone(site_name: str, task_name: str, start_date: str, end_date: str, status: str = "Not Started"):
    """
    Add a critical path milestone to a site.
    
    Args:
        site_name: Name of the site
        task_name: Name of the task/milestone
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        status: 'Not Started', 'In Progress', 'Complete'
    """
    site_id = get_site_id_by_name(site_name)
    if not site_id:
        return f"Error: Could not find site named '{site_name}'"
        
    site = st.session_state.db['sites'][site_id]
    
    # Initialize schedule if needed
    if 'critical_path' not in site:
        site['critical_path'] = []
        
    # Add milestone
    milestone = {
        'Task': task_name,
        'Start': start_date,
        'Finish': end_date,
        'Status': status,
        'Phase': 'Custom', # Default
        'Workstream': 'General' # Default
    }
    
    # If critical_path is a list (legacy/simple) or we need a specific structure
    # For now, let's assume we append to a list in the site object
    # Note: The actual app uses 'schedule' dict for capacity and 'phases' for major milestones
    # But we might have a 'custom_milestones' list
    
    if 'custom_milestones' not in site:
        site['custom_milestones'] = []
        
    site['custom_milestones'].append(milestone)
    
    # Save
    st.session_state.db['sites'][site_id] = site
    if 'save_database_func' in st.session_state:
        st.session_state.save_database_func(st.session_state.db)
        
    return f"Added milestone '{task_name}' to {site_name}"

# --- Navigation Tools ---

def navigate_to_page(page_name: str):
    """
    Navigate the user to a specific page in the application.
    
    Args:
        page_name: Name of the page to navigate to. 
                   Options: 'Dashboard', 'Site Database', 'Critical Path', 'Research Framework', 'NOC'
    """
    # Map friendly names to actual page keys
    page_map = {
        'dashboard': '📊 Dashboard',
        'database': '🏭 Site Database',
        'sites': '🏭 Site Database',
        'critical path': '⚡ Critical Path',
        'gantt': '⚡ Critical Path',
        'research': '🔬 Research Framework',
        'noc': '🧩 Network Operations Center (NOC)',
        'program': '📊 Program Tracker',
        'vdr': '📁 VDR Upload'
    }
    
    target = page_map.get(page_name.lower())
    if target:
        st.session_state.navigation_target = target
        st.rerun()
        return f"Navigating to {target}..."
    else:
        return f"Page '{page_name}' not found. Available: {', '.join(page_map.keys())}"

def select_site(site_name: str):
    """
    Selects a specific site in the application context.
    
    Args:
        site_name: The name of the site to select (must match exactly or be a close match).
    """
    if 'sites' not in st.session_state:
        return "Error: Site database not loaded."
    
    sites = st.session_state.db.get('sites', {})
    
    # Try exact match
    if site_name in sites:
        st.session_state.selected_site = site_name
        return f"Successfully selected site: {site_name}"
    
    # Try case-insensitive match
    for name in sites.keys():
        if name.lower() == site_name.lower():
            st.session_state.selected_site = name
            return f"Successfully selected site: {name}"
            
    # Try by name field
    for site_id, site in sites.items():
        if site.get('name', '').lower() == site_name.lower():
            st.session_state.selected_site = site_id # Use ID
            return f"Successfully selected site: {site.get('name')}"

    return f"Error: Site '{site_name}' not found."

# --- Tool Registry ---

# Function map for execution
TOOL_FUNCTIONS = {
    "update_site_field": update_site_field,
    "create_new_site": create_new_site,
    "navigate_to_page": navigate_to_page,
    "select_site": select_site,
    "add_milestone": add_milestone
}

# Tool Definitions for Gemini
AGENT_TOOLS = [
    {
        "function_declarations": [
            {
                "name": "update_site_field",
                "description": "Update a specific field for a site. Use this for attributes like 'Willing to Sell', 'Asking Price', 'Zoning', 'Utility', etc.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "site_name": {"type": "STRING", "description": "Name of the site to update"},
                        "field": {"type": "STRING", "description": "Field to update (e.g., 'willing_to_sell', 'asking_price', 'zoning_status')"},
                        "value": {"type": "STRING", "description": "New value for the field (accepts any text, e.g., 'In Negotiation', 'Yes', '$10M')"}
                    },
                    "required": ["site_name", "field", "value"]
                }
            },
            {
                "name": "create_new_site",
                "description": "Create a new site in the database.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING", "description": "Name of the new site"},
                        "state": {"type": "STRING", "description": "State code (e.g., 'OK', 'TX')"},
                        "target_mw": {"type": "INTEGER", "description": "Target capacity in MW"},
                        "acres": {"type": "INTEGER", "description": "Total acreage (optional)"},
                        "voltage_kv": {"type": "INTEGER", "description": "Interconnection voltage in kV (optional)"},
                        "latitude": {"type": "NUMBER", "description": "Latitude coordinate (optional)"},
                        "longitude": {"type": "NUMBER", "description": "Longitude coordinate (optional)"},
                        "status": {"type": "STRING", "description": "Project status (optional)"},
                        "schedule_json": {"type": "STRING", "description": "JSON string of schedule dict {year: mw} (optional)"}
                    },
                    "required": ["name", "state", "target_mw"]
                }
            },
            {
                "name": "navigate_to_page",
                "description": "Navigate the user to a specific page.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "page_name": {"type": "STRING", "description": "Name of the page (Dashboard, Site Database, Critical Path, Research)"}
                    },
                    "required": ["page_name"]
                }
            },
            {
                "name": "select_site",
                "description": "Select a site to view details.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "site_name": {"type": "STRING", "description": "Name of the site to select"}
                    },
                    "required": ["site_name"]
                }
            },
            {
                "name": "add_milestone",
                "description": "Add a critical path milestone.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "site_name": {"type": "STRING", "description": "Name of the site"},
                        "task_name": {"type": "STRING", "description": "Name of the task"},
                        "start_date": {"type": "STRING", "description": "Start date (YYYY-MM-DD)"},
                        "end_date": {"type": "STRING", "description": "End date (YYYY-MM-DD)"},
                        "status": {"type": "STRING", "description": "Status (Not Started, In Progress, Complete)"}
                    },
                    "required": ["site_name", "task_name", "start_date", "end_date"]
                }
            }
        ]
    }
]
