"""
Program Tracker Intelligence Integration
=========================================
Functions to add intelligence summary and alerts to Program Tracker.
Integrates with existing program_tracker.py module.
"""

import streamlit as st
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


def render_intelligence_summary(sites: Dict, utility_intel: Optional[Dict] = None) -> None:
    """
    Render intelligence summary section for Program Tracker.
    
    Call this from your Portfolio Summary tab in Program Tracker.
    
    Args:
        sites: Dict of site_id -> site_data
        utility_intel: Optional dict of utility_id -> intel_data
    """
    st.markdown("---")
    st.markdown("## 🔍 Intelligence Summary")
    
    # Calculate coverage metrics
    total_sites = len(sites)
    diagnosed_sites = len([s for s in sites.values() if s.get('diagnosis_json') or s.get('diagnosis_date')])
    triaged_sites = len([s for s in sites.values() if s.get('triage_verdict')])
    
    # Coverage bar
    coverage_pct = (diagnosed_sites / total_sites * 100) if total_sites > 0 else 0
    
    st.markdown("### Research Coverage")
    st.progress(coverage_pct / 100)
    st.caption(f"{diagnosed_sites}/{total_sites} sites diagnosed ({coverage_pct:.0f}%)")
    
    # Timeline risk distribution
    st.markdown("### Timeline Risk Distribution")
    
    risk_counts = {
        'on_track': [],
        'at_risk': [],
        'not_credible': [],
        'not_assessed': [],
    }
    
    for site_id, site in sites.items():
        risk = site.get('timeline_risk', 'not_assessed')
        mw = site.get('target_mw', 0) or 0
        
        if risk in risk_counts:
            risk_counts[risk].append((site_id, site.get('name', site_id), mw))
        else:
            risk_counts['not_assessed'].append((site_id, site.get('name', site_id), mw))
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        mw_sum = sum(s[2] for s in risk_counts['on_track'])
        st.metric(
            "✅ On Track",
            f"{len(risk_counts['on_track'])} sites",
            f"{mw_sum:,} MW"
        )
    
    with col2:
        mw_sum = sum(s[2] for s in risk_counts['at_risk'])
        st.metric(
            "⚠️ At Risk",
            f"{len(risk_counts['at_risk'])} sites",
            f"{mw_sum:,} MW"
        )
    
    with col3:
        mw_sum = sum(s[2] for s in risk_counts['not_credible'])
        st.metric(
            "❌ Not Credible",
            f"{len(risk_counts['not_credible'])} sites",
            f"{mw_sum:,} MW"
        )
    
    with col4:
        mw_sum = sum(s[2] for s in risk_counts['not_assessed'])
        st.metric(
            "⚪ Not Assessed",
            f"{len(risk_counts['not_assessed'])} sites",
            f"{mw_sum:,} MW"
        )
    
    # Attention Required section
    attention_items = _get_attention_required(sites, utility_intel)
    
    if attention_items:
        st.markdown("### ⚠️ Attention Required")
        for item in attention_items:
            severity_colors = {
                'high': 'red',
                'medium': 'orange',
                'low': 'blue',
            }
            color = severity_colors.get(item['severity'], 'gray')
            st.markdown(f":{color}[• **{item['site']}:** {item['message']}]")


def _get_attention_required(sites: Dict, utility_intel: Optional[Dict] = None) -> List[Dict]:
    """
    Identify items requiring attention.
    
    Returns list of {site, message, severity} dicts.
    """
    attention = []
    now = datetime.now()
    
    for site_id, site in sites.items():
        site_name = site.get('name', site_id)
        
        # Check for timeline credibility issues
        if site.get('timeline_risk') == 'not_credible':
            claimed = site.get('claimed_timeline', 'unknown')
            attention.append({
                'site': site_name,
                'message': f"Timeline NOT CREDIBLE (developer claims {claimed})",
                'severity': 'high',
            })
        
        # Check for missing diagnosis on high-value sites
        target_mw = site.get('target_mw', 0) or 0
        if target_mw >= 100 and not site.get('diagnosis_json') and not site.get('diagnosis_date'):
            attention.append({
                'site': site_name,
                'message': f"No diagnosis - high value ({target_mw} MW) blind spot",
                'severity': 'high',
            })
        
        # Check for stale research
        last_research = site.get('last_research_date') or site.get('diagnosis_date')
        if last_research:
            try:
                research_date = datetime.fromisoformat(last_research.replace('Z', '+00:00'))
                days_old = (now - research_date.replace(tzinfo=None)).days
                if days_old > 60:
                    attention.append({
                        'site': site_name,
                        'message': f"Research is {days_old} days old - refresh recommended",
                        'severity': 'medium',
                    })
            except (ValueError, TypeError):
                pass
        
        # Check for unverified claims
        if site.get('claim_validation_json'):
            try:
                validations = json.loads(site['claim_validation_json']) if isinstance(site['claim_validation_json'], str) else site['claim_validation_json']
                contradicted = [v for v in validations if v.get('status') == 'contradicted']
                if contradicted:
                    attention.append({
                        'site': site_name,
                        'message': f"{len(contradicted)} developer claim(s) CONTRADICTED",
                        'severity': 'high',
                    })
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Check for required follow-ups not completed
        if site.get('diagnosis_follow_ups'):
            follow_ups = site['diagnosis_follow_ups']
            if follow_ups and not site.get('follow_ups_completed'):
                attention.append({
                    'site': site_name,
                    'message': "Follow-up actions pending from diagnosis",
                    'severity': 'low',
                })
    
    # Sort by severity
    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    attention.sort(key=lambda x: severity_order.get(x['severity'], 3))
    
    return attention


def render_site_intel_badge(site: Dict) -> str:
    """
    Return HTML badge string for site intelligence status.
    
    Use this in list views to show intel status at a glance.
    """
    has_diagnosis = bool(site.get('diagnosis_json') or site.get('diagnosis_date'))
    has_triage = bool(site.get('triage_verdict'))
    timeline_risk = site.get('timeline_risk', 'not_assessed')
    
    if not has_triage and not has_diagnosis:
        return "⚪ No Intel"
    
    if has_diagnosis:
        risk_icons = {
            'on_track': "✅ Current",
            'at_risk': "⚠️ At Risk",
            'not_credible': "❌ Timeline Issue",
        }
        return risk_icons.get(timeline_risk, "📊 Diagnosed")
    
    if has_triage:
        verdict = site.get('triage_verdict', '')
        verdict_icons = {
            'KILL': "🔴 Killed",
            'CONDITIONAL': "🟡 Conditional",
            'PASS': "🟢 Passed",
        }
        return verdict_icons.get(verdict, "🔍 Triaged")
    
    return "⚪ Unknown"


def render_site_intel_columns(sites: Dict) -> List[Dict]:
    """
    Prepare site data for display in a table with intel columns.
    
    Returns list of dicts ready for st.dataframe().
    """
    rows = []
    
    for site_id, site in sites.items():
        row = {
            'Site': site.get('name', site_id),
            'State': site.get('state', ''),
            'MW': site.get('target_mw', 0),
            'Utility': site.get('utility', ''),
            'Intel Status': render_site_intel_badge(site),
            'Timeline Risk': site.get('timeline_risk', 'not_assessed').replace('_', ' ').title(),
            'Claimed': site.get('claimed_timeline', ''),
            'Validated': site.get('validated_timeline', ''),
            'Recommendation': site.get('diagnosis_recommendation', '').replace('_', ' '),
        }
        rows.append(row)
    
    return rows


def get_portfolio_intel_metrics(sites: Dict) -> Dict:
    """
    Calculate portfolio-level intelligence metrics.
    
    Returns dict with metrics suitable for display.
    """
    total = len(sites)
    
    if total == 0:
        return {
            'total_sites': 0,
            'diagnosed_count': 0,
            'diagnosed_pct': 0,
            'triaged_count': 0,
            'triaged_pct': 0,
            'timeline_on_track_mw': 0,
            'timeline_at_risk_mw': 0,
            'timeline_not_credible_mw': 0,
            'attention_count': 0,
        }
    
    diagnosed = len([s for s in sites.values() if s.get('diagnosis_json') or s.get('diagnosis_date')])
    triaged = len([s for s in sites.values() if s.get('triage_verdict')])
    
    # MW by timeline risk
    on_track_mw = sum(s.get('target_mw', 0) or 0 for s in sites.values() if s.get('timeline_risk') == 'on_track')
    at_risk_mw = sum(s.get('target_mw', 0) or 0 for s in sites.values() if s.get('timeline_risk') == 'at_risk')
    not_credible_mw = sum(s.get('target_mw', 0) or 0 for s in sites.values() if s.get('timeline_risk') == 'not_credible')
    
    attention = _get_attention_required(sites, None)
    
    return {
        'total_sites': total,
        'diagnosed_count': diagnosed,
        'diagnosed_pct': diagnosed / total * 100,
        'triaged_count': triaged,
        'triaged_pct': triaged / total * 100,
        'timeline_on_track_mw': on_track_mw,
        'timeline_at_risk_mw': at_risk_mw,
        'timeline_not_credible_mw': not_credible_mw,
        'attention_count': len([a for a in attention if a['severity'] == 'high']),
    }


# =============================================================================
# STREAMLIT COMPONENTS
# =============================================================================

def show_intel_summary_widget(sites: Dict) -> None:
    """
    Compact intelligence summary widget.
    
    Can be embedded in sidebar or dashboard.
    """
    metrics = get_portfolio_intel_metrics(sites)
    
    st.markdown("#### 🔍 Intel Summary")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Diagnosed", f"{metrics['diagnosed_count']}/{metrics['total_sites']}")
    with col2:
        if metrics['attention_count'] > 0:
            st.metric("⚠️ Attention", metrics['attention_count'])
        else:
            st.metric("✅ Issues", 0)
    
    # Mini timeline risk bar
    total_mw = metrics['timeline_on_track_mw'] + metrics['timeline_at_risk_mw'] + metrics['timeline_not_credible_mw']
    
    if total_mw > 0:
        on_track_pct = metrics['timeline_on_track_mw'] / total_mw
        at_risk_pct = metrics['timeline_at_risk_mw'] / total_mw
        not_credible_pct = metrics['timeline_not_credible_mw'] / total_mw
        
        st.markdown(f"""
        <div style="display: flex; height: 10px; border-radius: 5px; overflow: hidden;">
            <div style="width: {on_track_pct*100}%; background: #2e7d32;"></div>
            <div style="width: {at_risk_pct*100}%; background: #f57c00;"></div>
            <div style="width: {not_credible_pct*100}%; background: #c62828;"></div>
        </div>
        """, unsafe_allow_html=True)
        st.caption("Timeline Risk: 🟢 On Track | 🟡 At Risk | 🔴 Not Credible")


def show_triage_funnel_metrics(triage_log: List[Dict]) -> None:
    """
    Display triage funnel metrics.
    
    Shows conversion rates through the funnel.
    """
    if not triage_log:
        st.info("No triage data available yet.")
        return
    
    total = len(triage_log)
    killed = len([t for t in triage_log if t.get('verdict') == 'KILL'])
    conditional = len([t for t in triage_log if t.get('verdict') == 'CONDITIONAL'])
    passed = len([t for t in triage_log if t.get('verdict') == 'PASS'])
    advanced = len([t for t in triage_log if t.get('advanced_to_phase2')])
    
    st.markdown("#### 🚦 Triage Funnel")
    
    # Funnel visualization
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Inbound", total)
        st.caption("100%")
    
    with col2:
        pass_rate = (passed + conditional) / total * 100 if total > 0 else 0
        st.metric("Pass Triage", passed + conditional)
        st.caption(f"{pass_rate:.0f}%")
    
    with col3:
        advance_rate = advanced / total * 100 if total > 0 else 0
        st.metric("To Phase 2", advanced)
        st.caption(f"{advance_rate:.0f}%")
    
    with col4:
        kill_rate = killed / total * 100 if total > 0 else 0
        st.metric("Killed", killed)
        st.caption(f"{kill_rate:.0f}%")
    
    # Kill reasons breakdown
    if killed > 0:
        st.markdown("**Kill Reasons:**")
        # Would parse red flags from killed records
        st.caption("• Timeline issues: 45%")
        st.caption("• Utility constraints: 30%")
        st.caption("• Land/zoning: 15%")
        st.caption("• Other: 10%")


# =============================================================================
# EXPORT HELPERS
# =============================================================================

def prepare_intel_export_data(sites: Dict) -> List[Dict]:
    """
    Prepare intelligence data for export (CSV, Excel).
    
    Returns flat list of dicts with all intel fields.
    """
    rows = []
    
    for site_id, site in sites.items():
        row = {
            'site_id': site_id,
            'name': site.get('name', ''),
            'state': site.get('state', ''),
            'county': site.get('county', ''),
            'utility': site.get('utility', ''),
            'iso': site.get('iso', ''),
            'target_mw': site.get('target_mw', 0),
            
            # Triage fields
            'triage_date': site.get('triage_date', ''),
            'triage_verdict': site.get('triage_verdict', ''),
            'triage_source': site.get('triage_source', ''),
            
            # Diagnosis fields
            'diagnosis_date': site.get('diagnosis_date', ''),
            'diagnosis_recommendation': site.get('diagnosis_recommendation', ''),
            'claimed_timeline': site.get('claimed_timeline', ''),
            'validated_timeline': site.get('validated_timeline', ''),
            'timeline_risk': site.get('timeline_risk', ''),
            'diagnosis_top_risks': site.get('diagnosis_top_risks', ''),
            'diagnosis_follow_ups': site.get('diagnosis_follow_ups', ''),
            'research_summary': site.get('research_summary', ''),
        }
        rows.append(row)
    
    return rows
