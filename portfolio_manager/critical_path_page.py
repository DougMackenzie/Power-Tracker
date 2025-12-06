"""
Critical Path Streamlit Page
============================
Add this file to your portfolio_manager folder.

Usage in streamlit_app.py:
    from .critical_path_page import show_critical_path_page
    
    # In navigation:
    if page == "⚡ Critical Path":
        show_critical_path_page()
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

# Import critical path module (same folder)
from .critical_path import (
    CriticalPathEngine,
    CriticalPathData,
    MilestoneInstance,
    MilestoneStatus,
    Owner,
    Phase,
    Workstream,
    OWNER_COLORS,
    DEFAULT_LEAD_TIMES,
    get_milestone_templates,
    get_predefined_scenarios,
    serialize_critical_path,
    deserialize_critical_path,
    get_critical_path_for_site,
    save_critical_path_to_site,
    initialize_critical_path_for_site,
    parse_document_for_updates,
)


def create_gantt_chart(data: CriticalPathData, group_by: str = "owner") -> go.Figure:
    """Create interactive Gantt chart with swimlanes."""
    
    templates = get_milestone_templates()
    tasks = []
    
    for ms_id, instance in data.milestones.items():
        if not instance.is_active:
            continue
        
        tmpl = templates.get(ms_id)
        if not tmpl:
            continue
        
        start = instance.target_start or instance.actual_start
        end = instance.target_end or instance.actual_end
        if not start or not end:
            continue
        
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
        duration = (end_date - start_date).days
        
        if group_by == "owner":
            group = (instance.owner_override or tmpl.owner.value)
        elif group_by == "phase":
            group = tmpl.phase.value
        else:
            group = tmpl.workstream.value
        
        # Color by status
        if instance.status == MilestoneStatus.COMPLETE:
            color = "#22c55e"
        elif instance.status == MilestoneStatus.IN_PROGRESS:
            color = "#3b82f6"
        elif instance.status == MilestoneStatus.BLOCKED:
            color = "#ef4444"
        else:
            owner = Owner(instance.owner_override) if instance.owner_override else tmpl.owner
            color = OWNER_COLORS.get(owner, "#888888")
        
        tasks.append({
            'id': ms_id, 'name': tmpl.name, 'start': start_date, 'end': end_date,
            'duration': duration, 'group': group, 'color': color,
            'status': instance.status.value, 'owner': instance.owner_override or tmpl.owner.value,
            'phase': tmpl.phase.value, 'critical': instance.on_critical_path,
            'workstream': tmpl.workstream.value,
        })
    
    if not tasks:
        fig = go.Figure()
        fig.add_annotation(text="No milestones scheduled", x=0.5, y=0.5, 
                          xref="paper", yref="paper", showarrow=False)
        return fig
    
    df = pd.DataFrame(tasks).sort_values(['group', 'start'])
    
    fig = go.Figure()
    y_pos = 0
    y_labels = []
    current_group = None
    
    for _, row in df.iterrows():
        if row['group'] != current_group:
            if current_group is not None:
                y_pos += 0.5
            current_group = row['group']
        
        border_color = '#f97316' if row['critical'] else row['color']
        border_width = 3 if row['critical'] else 1
        
        fig.add_trace(go.Bar(
            x=[row['duration']], y=[y_pos], base=[row['start']], orientation='h',
            marker=dict(color=row['color'], line=dict(color=border_color, width=border_width), opacity=0.85),
            hovertemplate=f"<b>{row['name']}</b><br>Owner: {row['owner']}<br>Status: {row['status']}<br>{'🔴 CRITICAL PATH' if row['critical'] else ''}<extra></extra>",
            showlegend=False,
        ))
        
        y_labels.append({'y': y_pos, 'label': row['name'][:25] + '...' if len(row['name']) > 25 else row['name']})
        y_pos += 1
    
    fig.update_layout(
        title="Critical Path to Energization", barmode='overlay',
        height=max(600, len(y_labels) * 24), margin=dict(l=200, r=50, t=50, b=50),
        xaxis=dict(type='date', tickformat='%b %Y'),
        yaxis=dict(tickmode='array', tickvals=[l['y'] for l in y_labels], 
                   ticktext=[l['label'] for l in y_labels], autorange='reversed'),
    )
    
    # Add vertical line for today (convert date to datetime for plotly)
    today = datetime.combine(date.today(), datetime.min.time())
    fig.add_vline(x=today, line_dash="dash", line_color="gray", annotation_text="Today")
    
    # Add vertical line for energization date
    if data.calculated_energization:
        energization_date = datetime.combine(
            date.fromisoformat(data.calculated_energization), 
            datetime.min.time()
        )
        fig.add_vline(x=energization_date, line_dash="solid", line_color="#fbbf24",
                     line_width=3, annotation_text="⚡ Energization")
    
    return fig


def show_critical_path_page():
    """Main Critical Path page."""
    
    st.header("⚡ Critical Path to Energization")
    
    if 'db' not in st.session_state:
        st.warning("No database loaded")
        return
    
    db = st.session_state.db
    sites = db.get('sites', {})
    
    if not sites:
        st.info("No sites in database. Add sites first.")
        return
    
    if 'cp_engine' not in st.session_state:
        st.session_state.cp_engine = CriticalPathEngine()
    engine = st.session_state.cp_engine
    templates = get_milestone_templates()
    
    # Site selector
    site_options = {s.get('name', sid): sid for sid, s in sites.items()}
    selected_name = st.sidebar.selectbox("Select Site", list(site_options.keys()))
    selected_site_id = site_options.get(selected_name)
    
    if not selected_site_id:
        return
    
    site = sites[selected_site_id]
    cp_data = get_critical_path_for_site(site)
    
    if cp_data is None:
        st.sidebar.info("Critical path not initialized")
        if st.sidebar.button("🚀 Initialize Critical Path"):
            cp_data = initialize_critical_path_for_site(site)
            site = save_critical_path_to_site(site, cp_data)
            sites[selected_site_id] = site
            st.success("Initialized!")
            st.rerun()
        return
    
    # Sidebar info
    st.sidebar.markdown("---")
    st.sidebar.metric("Target MW", cp_data.config.target_mw)
    st.sidebar.metric("Voltage", f"{cp_data.config.voltage_kv} kV")
    st.sidebar.write(f"**ISO:** {cp_data.config.iso}")
    
    if st.sidebar.button("🔄 Recalculate"):
        for ms in cp_data.milestones.values():
            ms.target_start = ms.target_end = None
        cp_data = engine.calculate_schedule(cp_data)
        cp_data.critical_path = engine.identify_critical_path(cp_data)
        site = save_critical_path_to_site(site, cp_data)
        sites[selected_site_id] = site
        st.rerun()
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Gantt", "🔍 Analysis", "✏️ Milestones", "⚙️ Lead Times", "🎯 What-If"
    ])
    
    with tab1:
        group_by = st.radio("Group By", ["owner", "phase", "workstream"], horizontal=True)
        fig = create_gantt_chart(cp_data, group_by)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if cp_data.calculated_energization:
                days = (date.fromisoformat(cp_data.calculated_energization) - date.today()).days
                st.metric("Days to ⚡", f"{days:,}")
        with col2:
            st.metric("Duration", f"{cp_data.total_duration_weeks} wks")
        with col3:
            st.metric("Critical Items", len(cp_data.critical_path))
        with col4:
            st.metric("Risk", cp_data.schedule_risk.upper())
        
        if cp_data.primary_driver:
            driver_tmpl = templates.get(cp_data.primary_driver)
            if driver_tmpl:
                st.subheader("🎯 Primary Driver")
                st.write(f"**{driver_tmpl.name}** ({driver_tmpl.owner.value})")
                if driver_tmpl.acceleration_options:
                    st.info("Acceleration: " + ", ".join(driver_tmpl.acceleration_options))
        
        st.subheader("Critical Path")
        for ms_id in cp_data.critical_path[:15]:
            tmpl = templates.get(ms_id)
            instance = cp_data.milestones.get(ms_id)
            if tmpl:
                icon = {"Complete": "✅", "In Progress": "🔄", "Blocked": "🚫"}.get(instance.status.value, "⬜")
                st.write(f"{icon} {tmpl.name} ({tmpl.owner.value})")
    
    with tab3:
        phase_filter = st.selectbox("Phase", ["All"] + [p.value for p in Phase])
        
        for ms_id, instance in cp_data.milestones.items():
            tmpl = templates.get(ms_id)
            if not tmpl or (phase_filter != "All" and tmpl.phase.value != phase_filter):
                continue
            
            with st.expander(f"{'🔴' if instance.on_critical_path else '⬜'} {tmpl.name}"):
                col1, col2 = st.columns(2)
                with col1:
                    new_status = st.selectbox("Status", [s.value for s in MilestoneStatus],
                        index=[s.value for s in MilestoneStatus].index(instance.status.value), key=f"s_{ms_id}")
                with col2:
                    new_dur = st.number_input("Duration (wks)", value=instance.duration_override or tmpl.duration_typical, key=f"d_{ms_id}")
                
                if st.button("Update", key=f"u_{ms_id}"):
                    instance.status = MilestoneStatus(new_status)
                    instance.duration_override = new_dur if new_dur != tmpl.duration_typical else None
                    site = save_critical_path_to_site(site, cp_data)
                    sites[selected_site_id] = site
                    st.success("Updated")
    
    with tab4:
        st.subheader("Equipment Lead Times")
        
        for key in ['transformer_345kv', 'transformer_138kv', 'breakers_hv', 'gas_turbine']:
            defaults = DEFAULT_LEAD_TIMES.get(key, {'min': 50, 'typical': 100, 'max': 200})
            current = cp_data.config.lead_time_overrides.get(key, defaults['typical'])
            
            new_val = st.slider(f"{key.replace('_', ' ').title()} (weeks)",
                defaults['min'], defaults['max'], current, key=f"lt_{key}")
            
            if new_val != defaults['typical']:
                cp_data.config.lead_time_overrides[key] = new_val
        
        if st.button("Save & Recalculate"):
            for ms in cp_data.milestones.values():
                ms.target_start = ms.target_end = None
            cp_data = engine.calculate_schedule(cp_data)
            cp_data.critical_path = engine.identify_critical_path(cp_data)
            site = save_critical_path_to_site(site, cp_data)
            sites[selected_site_id] = site
            st.rerun()
    
    with tab5:
        st.subheader("What-If Scenarios")
        
        for scenario_def in get_predefined_scenarios():
            with st.expander(f"💡 {scenario_def['name']}"):
                st.write(scenario_def['description'])
                
                if st.button(f"Test", key=f"test_{scenario_def['name']}"):
                    scenario = engine.create_scenario(scenario_def['name'], scenario_def['description'], scenario_def['overrides'])
                    scenario_data = engine.apply_scenario(cp_data, scenario)
                    delta = cp_data.total_duration_weeks - scenario_data.total_duration_weeks
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Current", f"{cp_data.total_duration_weeks} wks")
                    with col2:
                        st.metric("With Scenario", f"{scenario_data.total_duration_weeks} wks", delta=f"-{delta} wks")


def get_critical_path_summary(site: Dict) -> Optional[Dict]:
    """Get summary for use in other modules."""
    cp_data = get_critical_path_for_site(site)
    if not cp_data:
        return None
    return {
        'total_weeks': cp_data.total_duration_weeks,
        'energization_date': cp_data.calculated_energization,
        'primary_driver': cp_data.primary_driver,
        'critical_path_count': len(cp_data.critical_path),
        'schedule_risk': cp_data.schedule_risk,
    }
