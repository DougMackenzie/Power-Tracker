"""
Critical Path Streamlit Page - MS Project Style
=================================================
Enhanced Gantt chart with hierarchical grouping, dependency arrows,
and toggleable detail levels.
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


def sync_site_data_to_critical_path(site: Dict, cp_data: CriticalPathData) -> bool:
    """
    Synchronize site database values to Critical Path configuration and milestones.
    Returns True if any changes were made.
    """
    changes_made = False
    
    # 1. Sync Configuration
    # ---------------------
    # Target MW
    new_mw = site.get('target_mw', 0)
    if cp_data.config.target_mw != new_mw:
        cp_data.config.target_mw = new_mw
        changes_made = True
        
    # ISO
    new_iso = site.get('iso', 'SPP')
    if cp_data.config.iso != new_iso:
        cp_data.config.iso = new_iso
        changes_made = True
        
    # Voltage - find max from phases
    phases = site.get('phases', [])
    max_volts = 138
    if phases:
        for p in phases:
            try:
                v = int(p.get('voltage', 0))
                if v > max_volts:
                    max_volts = v
            except (ValueError, TypeError):
                pass
    
    if cp_data.config.voltage_kv != max_volts:
        cp_data.config.voltage_kv = max_volts
        changes_made = True

    # 2. Sync Milestones Status
    # -------------------------
    status_map = {
        "Not Started": MilestoneStatus.NOT_STARTED,
        "Initiated": MilestoneStatus.IN_PROGRESS,
        "Drafted": MilestoneStatus.IN_PROGRESS,
        "Submitted": MilestoneStatus.IN_PROGRESS,
        "Study": MilestoneStatus.IN_PROGRESS,
        "Complete": MilestoneStatus.COMPLETE,
        "Executed": MilestoneStatus.COMPLETE,
        "Approved": MilestoneStatus.COMPLETE,
        "Secured": MilestoneStatus.COMPLETE,
        "Option": MilestoneStatus.IN_PROGRESS,
        "Owned": MilestoneStatus.COMPLETE
    }
    
    def update_ms(ms_id, site_status_val):
        nonlocal changes_made
        if ms_id in cp_data.milestones and site_status_val:
            new_status = status_map.get(site_status_val, MilestoneStatus.NOT_STARTED)
            
            # Update status if changed
            if cp_data.milestones[ms_id].status != new_status:
                cp_data.milestones[ms_id].status = new_status
                changes_made = True
            
            # Ensure actual_end is set if COMPLETE (even if status didn't change)
            if new_status == MilestoneStatus.COMPLETE and not cp_data.milestones[ms_id].actual_end:
                cp_data.milestones[ms_id].actual_end = date.today().isoformat()
                changes_made = True

    # --- Power / Interconnection ---
    best_study_status = "Not Started"
    best_sis_status = "Not Started"
    best_loa_status = "Not Started"
    best_screening_status = "Not Started"
    
    for phase in phases:
        # Screening
        p_screen = phase.get('screening_status', 'Not Started')
        if p_screen == "Complete":
            best_screening_status = "Complete"
        elif p_screen == "Initiated" and best_screening_status != "Complete":
            best_screening_status = "Initiated"

        # Contract Study
        p_study = phase.get('contract_study_status', 'Not Started')
        if p_study == "Complete":
            best_study_status = "Complete"
        elif p_study == "Initiated" and best_study_status != "Complete":
            best_study_status = "Initiated"
            
        # SIS Status (if available)
        p_sis = phase.get('sis_status', 'Not Started')
        if p_sis == "Complete":
            best_sis_status = "Complete"
        elif p_sis == "Initiated" and best_sis_status != "Complete":
            best_sis_status = "Initiated"
            
        p_loa = phase.get('loa_status', 'Not Started')
        if p_loa == "Executed":
            best_loa_status = "Executed"
        elif p_loa == "Drafted" and best_loa_status != "Executed":
            best_loa_status = "Drafted"

    if best_study_status in ["Initiated", "Complete"] or best_sis_status in ["Initiated", "Complete"]:
        update_ms("PS-PWR-02", "Complete") # Application
        update_ms("PS-PWR-03", "Complete") # Queue Position
    
    update_ms("PS-PWR-04", best_screening_status) # Screening Study
    
    # Map Contract Study to Facilities Study (PS-PWR-06)
    update_ms("PS-PWR-06", best_study_status) 
    
    # Map SIS (PS-PWR-05)
    # If Contract Study is initiated/complete, assume SIS is done
    if best_study_status in ["Initiated", "Complete"]:
        update_ms("PS-PWR-05", "Complete")
    else:
        update_ms("PS-PWR-05", best_sis_status)

    update_ms("PS-PWR-09", best_loa_status)   # IA/FA

    # --- Land / Site Control ---
    land_status = site.get('land_status', 'Not Started')
    if land_status == "Option":
        update_ms("PS-SC-02", "Executed")
    elif land_status == "Owned":
        update_ms("PS-SC-02", "Executed")
        update_ms("PS-SC-03", "Executed")
        update_ms("PS-TXN-03", "Executed")
        
    # --- Marketing / Transaction ---
    # If developer is assigned, assume Buyer Identified
    if site.get('developer'):
        update_ms("PS-MKT-02", "Complete") # Buyer Identified
        update_ms("PS-MKT-03", "Complete") # Buyer LOI
        
    # If capital status is Secured, assume Transaction Closed or near closing
    cap_status = site.get('capital_status', '')
    if cap_status == "Secured":
         update_ms("PS-TXN-03", "Complete") # Transaction Closed

    # --- Zoning ---
    zoning = site.get('non_power', {}).get('zoning_status', 'Not Started')
    update_ms("PS-ZN-03", zoning)
    if zoning == "Approved":
        update_ms("PS-ZN-06", "Approved")

    return changes_made


def analyze_procurement_risk(site: Dict, cp_data: CriticalPathData) -> Dict:
    """
    Analyze schedule risk by comparing Utility Schedule vs. Procurement Schedule.
    """
    # 1. Get Utility Power Schedule
    schedule = site.get('schedule', {})
    utility_target_date = None
    
    for year in sorted(schedule.keys()):
        try:
            if schedule[year].get('ic_mw', 0) > 0:
                utility_target_date = date(int(year), 1, 1)
                break
        except (ValueError, TypeError):
            continue
            
    if not utility_target_date:
        return {"has_risk": False, "msg": "No utility schedule defined"}

    # 2. Get Calculated Energization
    if not cp_data.calculated_energization:
        return {"has_risk": False, "msg": "No calculated energization"}
        
    calc_date = date.fromisoformat(cp_data.calculated_energization)

    # 3. Compare
    # If calculated date is significantly later than utility date, we have a risk
    risk_delta_days = (calc_date - utility_target_date).days
    
    # Check if procurement (Transformer Manufacturing) is the driver
    # POST-EQ-02 is Transformer Manufacturing
    is_procurement_driver = False
    if cp_data.primary_driver == "POST-EQ-02":
        is_procurement_driver = True
    
    if risk_delta_days > 90:
        return {
            "has_risk": True,
            "level": "HIGH",
            "msg": f"Procurement lags Utility by {risk_delta_days} days",
            "delta_days": risk_delta_days,
            "utility_date": utility_target_date,
            "calc_date": calc_date,
            "is_procurement_issue": is_procurement_driver
        }
    elif risk_delta_days > 0:
         return {
            "has_risk": True,
            "level": "MEDIUM",
            "msg": f"Procurement lags Utility by {risk_delta_days} days",
            "delta_days": risk_delta_days,
            "utility_date": utility_target_date,
            "calc_date": calc_date,
            "is_procurement_issue": is_procurement_driver
        }
        
    return {"has_risk": False, "msg": "Schedule aligned"}


def create_gantt_chart(data: CriticalPathData, group_by: str = "owner", show_detail: str = "all", audience: str = "buyer") -> go.Figure:
    """Create MS Project-style Gantt chart with dependencies and hierarchy."""
    
    templates = get_milestone_templates()
    tasks = []
    
    # Filter based on detail level
    for ms_id, instance in data.milestones.items():
        if not instance.is_active:
            continue
        
        tmpl = templates.get(ms_id)
        if not tmpl:
            continue
        
        # Filter by Audience
        should_include = True
        force_show = False  # Flag to bypass detail filter for specific audience views
        
        # Helper to get string value safely
        def get_val(enum_or_str):
            return enum_or_str.value if hasattr(enum_or_str, 'value') else str(enum_or_str)

        phase_val = get_val(tmpl.phase)
        ws_val = get_val(tmpl.workstream)
        
        if audience == "developer":
            # Developer only cares about Pre-Sale
            if phase_val != "Pre-Sale":
                should_include = False
        elif audience == "community":
            # Community cares about Zoning, Environmental, Water, and Pre-Sale Power
            relevant_workstreams = ["Zoning & Permitting", "Environmental", "Water"]
            is_relevant_power = (ws_val == "Power/Interconnection" and phase_val == "Pre-Sale")
            
            if ws_val not in relevant_workstreams and not is_relevant_power:
                should_include = False
            else:
                # If it is a community milestone, show it regardless of "Major Only" setting
                force_show = True
        
        if not should_include:
            continue
        
        # Filter by detail level (unless forced)
        if not force_show:
            if show_detail == "critical_only" and not instance.on_critical_path:
                continue
            elif show_detail == "major_only" and not tmpl.is_critical_default:
                continue
        
        start = instance.target_start or instance.actual_start
        end = instance.target_end or instance.actual_end
        if not start or not end:
            continue
        
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
        duration_days = (end_date - start_date).days
        
        if group_by == "owner":
            group = (instance.owner_override or tmpl.owner.value)
            subgroup = tmpl.workstream.value
        elif group_by == "phase":
            group = tmpl.phase.value
            subgroup = tmpl.workstream.value
        else:
            group = tmpl.workstream.value
            subgroup = tmpl.owner.value
        
        # Color by control level (who can influence this)
        owner = Owner(instance.owner_override) if instance.owner_override else tmpl.owner
        
        # Control level mapping
        if owner in [Owner.CUSTOMER, Owner.END_USER, Owner.BUYER]:
            color = "#10b981"  # Green - You control
        elif owner in [Owner.SELLER, Owner.CONSULTANT, Owner.CONTRACTOR, Owner.VENDOR]:
            color = "#fbbf24"  # Yellow - Partial control (you manage these parties)
        elif owner in [Owner.UTILITY, Owner.ISO, Owner.COUNTY, Owner.MUNICIPAL, Owner.STATE, Owner.FEDERAL, Owner.GAS_UTILITY]:
            color = "#ef4444"  # Red - No control (external parties)
        else:
            color = "#64748b"  # Gray - Unknown
        
        tasks.append({
            'id': ms_id,
            'name': tmpl.name,
            'start': start_date,
            'end': end_date,
            'duration_days': duration_days,
            'group': group,
            'subgroup': subgroup,
            'color': color,
            'status': instance.status.value,
            'owner': instance.owner_override or tmpl.owner.value,
            'phase': tmpl.phase.value,
            'critical': instance.on_critical_path,
            'workstream': tmpl.workstream.value,
            'predecessors': tmpl.predecessors,
            'is_milestone': tmpl.is_critical_default,
        })
    
    if not tasks:
        fig = go.Figure()
        fig.add_annotation(text="No milestones to display", x=0.5, y=0.5, 
                          xref="paper", yref="paper", showarrow=False)
        return fig
    
    # Sort chronologically (earliest at top) for natural top-down flow
    # This makes dependency arrows flow downward, easier to follow
    df = pd.DataFrame(tasks).sort_values(['start', 'group', 'subgroup'])
    
    fig = go.Figure()
    y_pos = 0
    y_labels = []
    task_positions = {}  # Track y-position for each task ID (for arrows)
    current_group = None
    current_subgroup = None
    group_positions = []
    
    # Build hierarchical structure
    for _, row in df.iterrows():
        # Major group header
        if row['group'] != current_group:
            if current_group is not None:
                y_pos += 1.2  # Extra space between major groups
            current_group = row['group']
            current_subgroup = None
            
            # Add group header
            group_positions.append({
                'group': current_group, 
                'y': y_pos,
                'is_header': True
            })
            y_labels.append({
                'y': y_pos,
                'label': f"▼ {current_group}",
                'is_header': True
            })
            y_pos += 1
        
        # Sub-group (workstream/owner)
        if row['subgroup'] != current_subgroup:
            current_subgroup = row['subgroup']
            y_labels.append({
                'y': y_pos,
                'label': f"  ▸ {current_subgroup}",
                'is_subheader': True
            })
            y_pos += 0.8
        
        # Task bar as rectangle shape (more reliable than Bar for date axis)
        # Critical path items get orange border
        border_width = 3 if row['critical'] else 1
        border_color = '#ff8c00' if row['critical'] else row['color']
        
        # Add orange dot for critical path items
        if row['critical']:
            fig.add_trace(go.Scatter(
                x=[row['start'] - timedelta(days=10)],  # Position dot to left of bar
                y=[y_pos],
                mode='markers',
                marker=dict(
                    size=12,
                    color='#ff8c00',  # Orange
                    symbol='circle',
                    line=dict(color='white', width=1)
                ),
                showlegend=False,
                hoverinfo='skip'
            ))
        
        # Add rectangle for task duration
        fig.add_shape(
            type="rect",
            x0=row['start'], x1=row['end'],
            y0=y_pos - 0.3, y1=y_pos + 0.3,
            fillcolor=row['color'],
            opacity=0.85,
            line=dict(color=border_color, width=border_width)
        )

        
        # Add invisible scatter point for hover info
        fig.add_trace(go.Scatter(
            x=[(row['start'] + timedelta(days=row['duration_days']//2))],  # Middle of bar
            y=[y_pos],
            mode='markers',
            marker=dict(size=0.1, opacity=0),  # Invisible
            hovertemplate=(
                f"<b>{row['name']}</b><br>"
                f"Start: {row['start'].strftime('%Y-%m-%d')}<br>"
                f"End: {row['end'].strftime('%Y-%m-%d')}<br>"
                f"Duration: {row['duration_days']} days<br>"
                f"Owner: {row['owner']}<br>"
                f"Status: {row['status']}<br>"
                f"{'🔴 CRITICAL PATH' if row['critical'] else ''}"
                "<extra></extra>"
            ),
            showlegend=False,
        ))
        
        # Add diamond marker for major milestones
        if row['is_milestone']:
            fig.add_trace(go.Scatter(
                x=[row['end']],
                y=[y_pos],
                mode='markers',
                marker=dict(
                    symbol='diamond',
                    size=12,
                    color=row['color'],
                    line=dict(color='#1f2937', width=2)
                ),
                showlegend=False,
                hoverinfo='skip'
            ))
        
        # Track position for dependency arrows
        task_positions[row['id']] = {'y': y_pos, 'start': row['start'], 'end': row['end']}
        
        y_labels.append({
            'y': y_pos,
            'label': f"    {row['name'][:35]}{'...' if len(row['name']) > 35 else ''}",
            'owner': row['owner'],
            'is_header': False,
            'is_subheader': False
        })
        y_pos += 1
    
    # Add dependency arrows with MS Project-style orthogonal routing
    for task_id, pos_info in task_positions.items():
        task = df[df['id'] == task_id].iloc[0] if len(df[df['id'] == task_id]) > 0 else None
        if task is None:
            continue
        
        for pred_id in task['predecessors']:
            if pred_id in task_positions:
                pred_pos = task_positions[pred_id]
                
                # MS Project style: Horizontal from pred end, then vertical drop, then horizontal to task start
                # Calculate intermediate points for right-angle routing
                pred_end_x = pred_pos['end']
                pred_y = pred_pos['y']
                task_start_x = pos_info['start']
                task_y = pos_info['y']
                
                # Mid-point for the horizontal segment (extend a bit from predecessor)
                mid_x = pred_end_x + timedelta(days=7)  # Small extension
                
                # Draw three connected lines for orthogonal routing:
                # 1. Horizontal line extending from predecessor end
                fig.add_shape(
                    type="line",
                    x0=pred_end_x, y0=pred_y,
                    x1=mid_x, y1=pred_y,
                    line=dict(color="#94a3b8", width=1.5),
                    opacity=0.6
                )
                
                # 2. Vertical drop line
                fig.add_shape(
                    type="line",
                    x0=mid_x, y0=pred_y,
                    x1=mid_x, y1=task_y,
                    line=dict(color="#94a3b8", width=1.5),
                    opacity=0.6
                )
                
                # 3. Horizontal line to task start
                fig.add_shape(
                    type="line",
                    x0=mid_x, y0=task_y,
                    x1=task_start_x, y1=task_y,
                    line=dict(color="#94a3b8", width=1.5),
                    opacity=0.6
                )
                
                # Add arrowhead at the end
                fig.add_annotation(
                    x=task_start_x, y=task_y,
                    ax=mid_x, ay=task_y,
                    xref="x", yref="y",
                    axref="x", ayref="y",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=1.5,
                    arrowcolor="#94a3b8",
                    opacity=0.6
                )
    
    # Calculate date range
    all_dates = [row['start'] for _, row in df.iterrows()] + [row['end'] for _, row in df.iterrows()]
    min_date = min(all_dates)
    max_date = max(all_dates)
    
    # Enhanced layout with better spacing for readability
    fig.update_layout(
        title={
            'text': f"Critical Path to Energization - {show_detail.replace('_', ' ').title()} View",
            'font': {'size': 18, 'color': '#1f2937', 'family': 'Arial, sans-serif'},
            'x': 0.5,
            'xanchor': 'center',
            'y': 0.98,  # Move title up slightly to avoid overlap
            'yanchor': 'top'
        },
        barmode='overlay',
        height=max(800, len(y_labels) * 38),  # Moderate spacing - balance between views
        margin=dict(l=220, r=100, t=100, b=50),
        paper_bgcolor='white',
        plot_bgcolor='#f9fafb',
        xaxis=dict(
            type='date',
            tickformat='%b %Y',
            tickmode='auto',
            nticks=24,
            tickangle=-45,
            tickfont=dict(size=10, color='#374151'),
            title=None,  # Remove "Timeline" text to avoid overlap
            gridcolor='#e5e7eb',
            gridwidth=1,
            showgrid=True,
            range=[min_date - timedelta(days=30), max_date + timedelta(days=30)],
            side='top'  # Timeline at top
        ),
        yaxis=dict(
            tickmode='array',
            tickvals=[l['y'] for l in y_labels],
            ticktext=[
                f"<b>{l['label']}</b>" if l.get('is_header') 
                else f"<i>{l['label']}</i>" if l.get('is_subheader')
                else f"{l['label']} [{l.get('owner', '')}]"  # Add owner after task name
                for l in y_labels
            ],
            tickfont=dict(size=9, color='#1f2937'),
            autorange='reversed',
            showgrid=False
        ),
    )
    
    # Add group separators
    for gp in group_positions:
        if gp.get('is_header'):
            # Major group separator
            fig.add_shape(
                type="rect",
                x0=0, x1=1, xref="paper",
                y0=gp['y'] - 0.3, y1=gp['y'] + 0.5,
                fillcolor="#e5e7eb",
                opacity=0.3,
                line_width=0
            )
    
    # Add "Today" marker
    today_str = date.today().isoformat()
    fig.add_shape(
        type="line",
        x0=today_str, x1=today_str,
        y0=0, y1=1,
        yref="paper",
        line=dict(color="#6b7280", width=2, dash="dash")
    )
    fig.add_annotation(
        x=today_str, y=-0.05, yref="paper",  # Move below chart
        text="<b>Today</b>", showarrow=False,
        font=dict(size=10, color="#374151"),
        bgcolor="white",
        bordercolor="#6b7280",
        borderwidth=1.5,
        borderpad=3
    )
    
    # Add "Energization" marker
    if data.calculated_energization:
        fig.add_shape(
            type="line",
            x0=data.calculated_energization, x1=data.calculated_energization,
            y0=0, y1=1,
            yref="paper",
            line=dict(color="#f59e0b", width=3)
        )
        fig.add_annotation(
            x=data.calculated_energization, y=-0.05, yref="paper",  # Move below chart
            text="<b>⚡ Energization</b>", showarrow=False,
            font=dict(size=10, color="#f59e0b", weight="bold"),
            bgcolor="white",
            bordercolor="#f59e0b",
            borderwidth=2,
            borderpad=3
        )
    
    return fig


def show_critical_path_page():
    """Main Critical Path page with MS Project-style Gantt chart."""
    
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
    
    if cp_data:
        # Reconcile missing milestones (e.g. new Utility Breakers)
        for tmpl_id, tmpl in templates.items():
            if tmpl_id not in cp_data.milestones:
                # Add missing milestone
                duration = tmpl.duration_typical
                # Adjust duration if needed (simplified)
                if tmpl.lead_time_key:
                    duration = engine._get_adjusted_duration(tmpl, cp_data.config)
                
                cp_data.milestones[tmpl_id] = MilestoneInstance(
                    template_id=tmpl_id,
                    duration_override=duration if duration != tmpl.duration_typical else None,
                    is_active=True,
                    on_critical_path=tmpl.is_critical_default,
                )
                st.toast(f"Added new milestone: {tmpl.name}")
    
    if cp_data is None:
        st.sidebar.info("Critical path not initialized")
        if st.sidebar.button("🚀 Initialize Critical Path"):
            cp_data = initialize_critical_path_for_site(site)
            site = save_critical_path_to_site(site, cp_data)
            sites[selected_site_id] = site
            # Save to Google Sheets
            from .streamlit_app import save_database
            save_database(db)
            st.success("Initialized and saved!")
            st.rerun()
        return
    
    # Auto-sync with Site Database
    if sync_site_data_to_critical_path(site, cp_data):
        # Recalculate if changes were made
        for ms in cp_data.milestones.values():
            ms.target_start = ms.target_end = None
        cp_data = engine.calculate_schedule(cp_data)
        cp_data.critical_path = engine.identify_critical_path(cp_data)
        
        # Save updates
        site = save_critical_path_to_site(site, cp_data)
        sites[selected_site_id] = site
        from .streamlit_app import save_database
        save_database(db)
        st.toast("✅ Synced with Site Database", icon="🔄")
        # No rerun needed, we just use the updated cp_data

    
    
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
        # Save to Google Sheets
        from .streamlit_app import save_database
        save_database(db)
        st.rerun()

    if st.sidebar.button("⚠️ Force Sync from Site DB"):
        if sync_site_data_to_critical_path(site, cp_data):
            st.toast("Sync found changes!", icon="✅")
        else:
            st.toast("No changes found during sync.", icon="ℹ️")
            
        # Always recalculate on force sync
        for ms in cp_data.milestones.values():
            ms.target_start = ms.target_end = None
        cp_data = engine.calculate_schedule(cp_data)
        cp_data.critical_path = engine.identify_critical_path(cp_data)
        site = save_critical_path_to_site(site, cp_data)
        sites[selected_site_id] = site
        from .streamlit_app import save_database
        save_database(db)
        st.rerun()
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Gantt", "🔍 Analysis", "✏️ Milestones", "⚙️ Lead Times", "🎯 What-If"
    ])
    
    with tab1:
        # Controls for Gantt chart
        col1, col2, col3 = st.columns(3)
        with col1:
            group_by = st.radio(
                "Group By", 
                ["owner", "phase", "workstream"], 
                horizontal=True,
                help="Organize milestones by responsible party, project phase, or workstream"
            )
        with col2:
            show_detail = st.radio(
                "Detail Level",
                ["all", "major_only", "critical_only"],
                format_func=lambda x: {
                    "all": "📋 All Tasks",
                    "major_only": "◆ Major Milestones",
                    "critical_only": "🔴 Critical Path Only"
                }[x],
                horizontal=True,
                help="Toggle between detailed and simplified views"
            )
        with col3:
            audience = st.radio(
                "Audience View",
                ["buyer", "developer", "community"],
                format_func=lambda x: {
                    "buyer": "🏗️ Buyer (Full)",
                    "developer": "💰 Developer (Pre-Sale)",
                    "community": "🏘️ Community (Approvals)"
                }[x],
                horizontal=True,
                help="Filter milestones relevant to specific stakeholders"
            )
            
        # ====================================================================
        # PROFESSIONAL HEADER & METRICS
        # ====================================================================
        
        # Extract target energization from capacity trajectory
        # Extract target energization from capacity trajectory
        target_energization = None
        if site.get('capacity_trajectory'):
            for year in sorted(site['capacity_trajectory'].keys()):
                mw = site['capacity_trajectory'][year]
                if mw and mw > 0:
                    target_energization = f"Q4 {year}"  # Simplified - assume Q4
                    break
        
        # Extract Voltage from phases (max voltage)
        voltage_display = site.get('voltage_kv', 'N/A')
        if voltage_display == 'N/A' and site.get('phases'):
            try:
                # Get max voltage from phases
                voltages = [float(p.get('voltage', 0)) for p in site['phases'] if p.get('voltage')]
                if voltages:
                    voltage_display = f"{int(max(voltages))}"
            except:
                pass

        # Header section with dark background
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e3a5f 0%, #2d5a8a 100%); padding: 24px; border-radius: 8px; margin-bottom: 20px;">
            <h2 style="color: white; margin: 0 0 12px 0;">⚡ Critical Path to Energization</h2>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px;">
                <div>
                    <div style="color: #b0c4de; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">SITE</div>
                    <div style="color: #ffa500; font-size: 18px; font-weight: 700; margin-top: 4px;">{site.get('name', 'Unknown')}</div>
                </div>
                <div>
                    <div style="color: #b0c4de; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">ISO</div>
                    <div style="color: #ffa500; font-size: 18px; font-weight: 700; margin-top: 4px;">{site.get('iso', site.get('ISO', 'N/A'))}</div>
                </div>
                <div>
                    <div style="color: #b0c4de; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">TARGET CAPACITY</div>
                    <div style="color: #ffa500; font-size: 18px; font-weight: 700; margin-top: 4px;">{site.get('target_mw', 0)} MW @ {voltage_display}kV</div>
                </div>
                <div>
                    <div style="color: #b0c4de; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">TARGET ENERGIZATION</div>
                    <div style="color: #ffa500; font-size: 18px; font-weight: 700; margin-top: 4px;">{target_energization or 'TBD'}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Metrics Panel
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if cp_data.calculated_energization:
                energization_date = date.fromisoformat(cp_data.calculated_energization)
                days_to_energization = (energization_date - date.today()).days
                st.metric(
                    "DAYS TO ENERGIZATION", 
                    f"{days_to_energization:,}",
                    delta=f"~{days_to_energization//365} years from today",
                    delta_color="off"
                )
            else:
                st.metric("DAYS TO ENERGIZATION", "N/A")
        
        with col2:
            # Schedule risk assessment
            # Schedule risk assessment
            procurement_risk = analyze_procurement_risk(site, cp_data)
            
            if procurement_risk['has_risk']:
                risk_level = procurement_risk.get('level', 'HIGH')
                risk_color = "🔴" if risk_level == "HIGH" else "🟡"
                delta_msg = procurement_risk['msg']
            else:
                # Fallback to duration-based risk
                if cp_data.total_duration_weeks > 200:
                    risk_level = "HIGH"
                    risk_color = "🔴"
                elif cp_data.total_duration_weeks > 150:
                    risk_level = "MEDIUM"
                    risk_color = "🟡"
                else:
                    risk_level = "LOW"
                    risk_color = "🟢"
                delta_msg = "Equipment lead times"
            
            st.metric(
                "SCHEDULE RISK",
                f"{risk_color} {risk_level}",
                delta=delta_msg,
                delta_color="off" if not procurement_risk['has_risk'] else "inverse"
            )
        
        with col3:
            critical_count = sum(1 for ms in cp_data.milestones.values() if ms.on_critical_path and ms.is_active)
            total_count = sum(1 for ms in cp_data.milestones.values() if ms.is_active)
            st.metric(
                "CRITICAL PATH ITEMS",
                f"{critical_count}",
                delta=f"of {total_count} total milestones",
                delta_color="off"
            )
        
        with col4:
            # Find primary driver (longest critical path milestone)
            primary_driver = "Unknown"
            max_duration = 0
            templates = get_milestone_templates()
            for ms_id, instance in cp_data.milestones.items():
                if instance.on_critical_path and instance.is_active:
                    tmpl = templates.get(ms_id)
                    if tmpl:
                        duration = instance.duration_override or tmpl.duration_typical
                        if duration > max_duration:
                            max_duration = duration
                            primary_driver = tmpl.name
            
            st.metric(
                "PRIMARY DRIVER",
                primary_driver.split(' - ')[0] if ' - ' in primary_driver else primary_driver,
                delta=f"{max_duration} weeks lead time",
                delta_color="off"
            )
        
        # Timeline Driver Callout
        procurement_risk = analyze_procurement_risk(site, cp_data)
        if procurement_risk['has_risk']:
            st.markdown(f"""
            <div style="background: #fff3cd; border-left: 4px solid #ff8c00; padding: 16px; border-radius: 4px; margin: 20px 0;">
                <div style="color: #856404; font-weight: 700; font-size: 14px; margin-bottom: 8px;">
                    ⚠️ Schedule Risk: {procurement_risk['msg']}
                </div>
                <div style="color: #333; font-size: 13px; line-height: 1.6;">
                    <strong>Utility Ready:</strong> {procurement_risk['utility_date']}<br>
                    <strong>Project Ready:</strong> {procurement_risk['calc_date']}<br>
                    <strong>Driver:</strong> {cp_data.primary_driver}<br>
                    <strong>Recommendation:</strong> Explore early procurement or customer-conveyed equipment to bridge the {procurement_risk['delta_days']}-day gap.
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: #d1fae5; border-left: 4px solid #10b981; padding: 16px; border-radius: 4px; margin: 20px 0;">
                <div style="color: #065f46; font-weight: 700; font-size: 14px; margin-bottom: 8px;">
                    ✅ Schedule Aligned
                </div>
                <div style="color: #333; font-size: 13px; line-height: 1.6;">
                    Project schedule aligns with utility interconnection capacity availability.
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Updated Legend
        st.markdown("""
        **Control Level (Bar Color):** 🟢 You Control | 🟡 Partial Control | 🔴 No Control  
        **Critical Path:** <span style="color: #ff8c00;">⬤</span> Orange dot + border = On Critical Path  
        **Timeline Markers:** ┃ Today | ⚡ Target Energization
        """, unsafe_allow_html=True)
        
        fig = create_gantt_chart(cp_data, group_by, show_detail, audience=audience)
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
                    # Save to Google Sheets
                    from .streamlit_app import save_database
                    save_database(db)
                    st.success("Updated and saved!")
    
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
            # Save to Google Sheets
            from .streamlit_app import save_database
            save_database(db)
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
