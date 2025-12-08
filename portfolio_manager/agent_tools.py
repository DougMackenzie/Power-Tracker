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
            
    # Fuzzy match
    for site_id, site in sites.items():
        if name_lower in site.get('name', '').lower():
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
    
    # Handle nested fields (e.g., non_power.zoning_status)
    if field in ['zoning_status', 'water_source', 'fiber_status']:
        if 'non_power' not in site: site['non_power'] = {}
        site['non_power'][field] = value
    elif field in ['ic_capacity', 'voltage']:
        # For simplicity, update first phase or main infra
        # This is a simplification for the agent
        pass 
    else:
        # Top level fields
        site[field] = value
        
    # Save
    st.session_state.db['sites'][site_id] = site
    return f"Successfully updated {field} to '{value}' for {site.get('name')}"

def create_new_site(name: str, state: str, target_mw: int):
    """
    Create a new site in the database.
    
    Args:
        name: Name of the new site
        state: State code (e.g., 'OK', 'TX')
        target_mw: Target capacity in MW
    """
    import uuid
    new_id = str(uuid.uuid4())
    
    new_site = {
        'name': name,
        'state': state,
        'target_mw': target_mw,
        'utility': 'TBD',
        'last_updated': datetime.now().strftime("%Y-%m-%d"),
        'phases': [],
        'schedule': {}
    }
    
    if 'sites' not in st.session_state.db:
        st.session_state.db['sites'] = {}
        
    st.session_state.db['sites'][new_id] = new_site
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
    
    sites = st.session_state.sites
    
    # Try exact match
    if site_name in sites:
        st.session_state.selected_site = site_name
        return f"Successfully selected site: {site_name}"
    
    # Try case-insensitive match
    for name in sites.keys():
        if name.lower() == site_name.lower():
            st.session_state.selected_site = name
            return f"Successfully selected site: {name}"
            
    return f"Error: Site '{site_name}' not found."

# --- Tool Registry ---

# Function map for execution
TOOL_FUNCTIONS = {
    "update_site_field": update_site_field,
    "create_new_site": create_new_site,
    "navigate_to_page": navigate_to_page
}
