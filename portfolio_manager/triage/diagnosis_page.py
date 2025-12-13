"""
Full Diagnosis Page
===================
Streamlit UI for Phase 2 Full Diagnosis.
Comprehensive research and claim validation.
"""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, Optional, List

from .models import (
    DiagnosisResult, TriageResult, ClaimValidation,
    DiagnosisRecommendation, TimelineRisk, ClaimValidationStatus,
)
from .engine import run_diagnosis, apply_diagnosis_to_site


# =============================================================================
# UI HELPERS
# =============================================================================

def recommendation_badge(rec: DiagnosisRecommendation) -> str:
    """Return styled recommendation badge."""
    badges = {
        DiagnosisRecommendation.GO: "🟢 **GO**",
        DiagnosisRecommendation.CONDITIONAL_GO: "🟡 **CONDITIONAL GO**",
        DiagnosisRecommendation.NO_GO: "🔴 **NO GO**",
    }
    return badges.get(rec, "⚪ Unknown")


def timeline_risk_badge(risk: TimelineRisk) -> str:
    """Return styled timeline risk badge."""
    badges = {
        TimelineRisk.ON_TRACK: "🟢 On Track",
        TimelineRisk.AT_RISK: "🟡 At Risk",
        TimelineRisk.NOT_CREDIBLE: "🔴 Not Credible",
    }
    return badges.get(risk, "⚪ Unknown")


def validation_status_icon(status: ClaimValidationStatus) -> str:
    """Return icon for validation status."""
    icons = {
        ClaimValidationStatus.VERIFIED: "✅",
        ClaimValidationStatus.PARTIALLY_VERIFIED: "🟡",
        ClaimValidationStatus.NOT_VERIFIED: "❓",
        ClaimValidationStatus.CONTRADICTED: "❌",
    }
    return icons.get(status, "•")


def appetite_badge(appetite: str) -> str:
    """Return styled appetite badge."""
    badges = {
        'aggressive': "🟢 Aggressive",
        'moderate': "🟡 Moderate",
        'defensive': "🔴 Defensive",
    }
    return badges.get(appetite.lower(), f"⚪ {appetite}")


# =============================================================================
# MAIN PAGE
# =============================================================================

def show_full_diagnosis():
    """Main Full Diagnosis page."""
    
    st.title("🔬 Full Diagnosis")
    st.markdown("""
    **Phase 2: Comprehensive Research & Claim Validation**
    
    Deep-dive analysis including utility position, timeline validation,
    competitive landscape, and developer claim verification.
    """)
    
    # Initialize session state
    if 'diagnosis_result' not in st.session_state:
        st.session_state.diagnosis_result = None
    if 'selected_site' not in st.session_state:
        st.session_state.selected_site = None
    
    # Site Selection
    st.subheader("📍 Select Site")
    
    # Get sites from database (placeholder)
    sites = _get_available_sites()
    
    if not sites:
        st.warning("No sites available for diagnosis. Add sites through Quick Triage or Site Management.")
        return
    
    # Site selector
    site_options = [(sid, f"{s.get('name', sid)} ({s.get('state', '?')})") for sid, s in sites.items()]
    selected = st.selectbox(
        "Select Site",
        options=site_options,
        format_func=lambda x: x[1],
    )
    
    if selected:
        site_id = selected[0]
        site_data = sites.get(site_id, {})
        st.session_state.selected_site = site_data
        
        # Show site summary
        with st.expander("📋 Site Summary", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Target MW", site_data.get('target_mw', 'N/A'))
            with col2:
                st.metric("Utility", site_data.get('utility', 'N/A'))
            with col3:
                st.metric("ISO", site_data.get('iso', 'N/A'))
            with col4:
                st.metric("Claimed Timeline", site_data.get('claimed_timeline', 'N/A'))
            
            # Triage status if available
            if site_data.get('triage_verdict'):
                st.info(f"**Triage Verdict:** {site_data['triage_verdict']}")
    
    st.divider()
    
    # Developer Claims Input
    st.subheader("📝 Developer Claims to Validate")
    st.markdown("*Enter claims made by the developer/landowner that need verification:*")
    
    # Dynamic claim input
    if 'developer_claims' not in st.session_state:
        st.session_state.developer_claims = []
    
    # Show existing claims
    claims_to_remove = []
    for i, claim in enumerate(st.session_state.developer_claims):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.text(f"{i+1}. {claim}")
        with col2:
            if st.button("🗑️", key=f"remove_claim_{i}"):
                claims_to_remove.append(i)
    
    # Remove marked claims
    for i in sorted(claims_to_remove, reverse=True):
        st.session_state.developer_claims.pop(i)
    
    # Add new claim
    col1, col2 = st.columns([5, 1])
    with col1:
        new_claim = st.text_input(
            "Add Claim",
            placeholder="e.g., 'Utility has confirmed 200MW capacity by 2028'",
            key="new_claim_input",
            label_visibility="collapsed",
        )
    with col2:
        if st.button("➕ Add", use_container_width=True):
            if new_claim:
                st.session_state.developer_claims.append(new_claim)
                st.rerun()
    
    # Quick claim templates
    with st.expander("💡 Common Claims to Validate"):
        templates = [
            "Utility has confirmed capacity availability",
            "Interconnection timeline is X months",
            "Zoning is already approved / will be easy",
            "No environmental concerns on site",
            "Water availability is confirmed",
            "They have relationships with utility leadership",
            "Other projects in area are proof of feasibility",
        ]
        for template in templates:
            if st.button(template, key=f"template_{template[:20]}"):
                st.session_state.developer_claims.append(template)
                st.rerun()
    
    st.divider()
    
    # Run Diagnosis
    if st.button("🚀 Run Full Diagnosis", type="primary", use_container_width=True):
        if not st.session_state.selected_site:
            st.error("Please select a site first")
        else:
            site = st.session_state.selected_site
            claims = st.session_state.developer_claims
            
            # Build triage result if available
            triage_result = None
            if site.get('triage_red_flags_json'):
                # Would reconstruct TriageResult from stored data
                pass
            
            with st.spinner("Running comprehensive diagnosis... This may take 30-60 seconds."):
                try:
                    result = run_diagnosis(
                        site_data=site,
                        triage_result=triage_result,
                        developer_claims=claims if claims else None,
                    )
                    st.session_state.diagnosis_result = result
                except Exception as e:
                    st.error(f"Diagnosis failed: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
    
    # Display Results
    if st.session_state.diagnosis_result:
        st.divider()
        _display_diagnosis_result(st.session_state.diagnosis_result)


def _display_diagnosis_result(result: DiagnosisResult):
    """Display diagnosis results."""
    
    st.header("📊 Diagnosis Results")
    
    # Main recommendation
    st.markdown(f"## {recommendation_badge(result.recommendation)}")
    
    # Timeline comparison
    st.subheader("📅 Timeline Assessment")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Claimed", result.claimed_timeline)
    with col2:
        st.metric("Validated", result.validated_timeline)
    with col3:
        delta_str = f"+{result.timeline_delta_months} months" if result.timeline_delta_months > 0 else f"{result.timeline_delta_months} months"
        st.metric("Delta", delta_str)
    
    st.markdown(f"**Timeline Risk:** {timeline_risk_badge(result.timeline_risk)}")
    
    st.divider()
    
    # Utility Assessment
    st.subheader("⚡ Utility Assessment")
    ua = result.utility_assessment
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Appetite:** {appetite_badge(ua.appetite)}")
        st.markdown(f"**Capacity Position:** {ua.capacity_position}")
        st.markdown(f"**Realistic Timeline:** {ua.realistic_timeline}")
    with col2:
        if ua.queue_status:
            st.markdown(f"**Queue Status:** {ua.queue_status}")
        if ua.recent_activity:
            st.markdown(f"**Recent Activity:** {ua.recent_activity}")
    
    if ua.key_insight:
        st.info(f"💡 **Key Insight:** {ua.key_insight}")
    
    st.divider()
    
    # Claim Validations
    if result.claim_validations:
        st.subheader("✓ Claim Validations")
        
        for cv in result.claim_validations:
            with st.container():
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.markdown(f"### {validation_status_icon(cv.status)}")
                    st.caption(cv.status.value.replace('_', ' ').title())
                with col2:
                    st.markdown(f"**Claim:** {cv.claim}")
                    st.markdown(f"**Evidence:** {cv.evidence}")
                    st.caption(f"Confidence: {cv.confidence}")
                    if cv.follow_up:
                        st.warning(f"❓ Follow-up: {cv.follow_up}")
                st.divider()
    
    # Competitive Context
    st.subheader("🏆 Competitive Landscape")
    cc = result.competitive_context
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Regional Projects", cc.regional_projects)
        if cc.market_saturation:
            st.markdown(f"**Market Saturation:** {cc.market_saturation.title()}")
    with col2:
        if cc.key_competitors:
            st.markdown("**Key Competitors:**")
            for comp in cc.key_competitors:
                st.markdown(f"- {comp}")
    
    if cc.differentiation_required:
        st.info(f"🎯 **Differentiation Required:** {cc.differentiation_required}")
    
    st.divider()
    
    # Risks and Actions
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚠️ Top Risks")
        for i, risk in enumerate(result.top_risks, 1):
            st.markdown(f"{i}. {risk}")
    
    with col2:
        st.subheader("✅ Follow-Up Actions")
        for action in result.follow_up_actions:
            st.checkbox(action, key=f"action_{action[:20]}")
    
    st.divider()
    
    # Research Summary
    st.subheader("📝 Research Summary")
    st.markdown(result.research_summary)
    
    # Actions
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save to Site Record", type="primary", use_container_width=True):
            # Would save to database
            st.success("Diagnosis saved to site record")
    
    with col2:
        if st.button("📋 Export Report", use_container_width=True):
            st.download_button(
                label="Download JSON",
                data=result.to_json(),
                file_name=f"diagnosis_{result.diagnosis_id}.json",
                mime="application/json",
            )
    
    with col3:
        if st.button("📧 Share Summary", use_container_width=True):
            # Would generate shareable summary
            st.info("Email summary feature coming soon")
    
    # Metadata
    with st.expander("🔧 Metadata"):
        st.markdown(f"""
        - **Diagnosis ID:** {result.diagnosis_id}
        - **Date:** {result.diagnosis_date}
        - **Model:** {result.model_used}
        """)


# =============================================================================
# DATA HELPERS
# =============================================================================

def _get_available_sites() -> Dict:
    """
    Get sites available for diagnosis.
    In production, this would load from Google Sheets.
    """
    # Try to get from session state (main app's database)
    if hasattr(st.session_state, 'db') and 'sites' in st.session_state.db:
        return st.session_state.db['sites']
    
    # Return example data for standalone testing
    return {
        'tulsa_metro_hub': {
            'name': 'Tulsa Metro Hub',
            'state': 'OK',
            'county': 'Tulsa',
            'utility': 'PSO',
            'iso': 'SPP',
            'target_mw': 200,
            'acreage': 500,
            'claimed_timeline': 'Q4 2028',
            'triage_verdict': 'CONDITIONAL',
        },
        'dallas_north': {
            'name': 'Dallas North Site',
            'state': 'TX',
            'county': 'Collin',
            'utility': 'Oncor',
            'iso': 'ERCOT',
            'target_mw': 500,
            'acreage': 1000,
            'claimed_timeline': '2027',
            'triage_verdict': 'PASS',
        },
    }


# =============================================================================
# SITE INTELLIGENCE TAB
# =============================================================================

def show_site_intelligence(site_id: str, site: Dict):
    """
    Display intelligence summary for a site.
    This can be embedded in the main site detail view.
    """
    
    st.subheader("🔍 Intelligence Summary")
    
    # Triage status
    triage_verdict = site.get('triage_verdict')
    if triage_verdict:
        verdict_color = {'KILL': '🔴', 'CONDITIONAL': '🟡', 'PASS': '🟢'}.get(triage_verdict, '⚪')
        st.metric("Triage Verdict", f"{verdict_color} {triage_verdict}")
    
    # Timeline comparison
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Claimed Timeline", site.get('claimed_timeline', 'N/A'))
    with col2:
        st.metric("Validated Timeline", site.get('validated_timeline', 'N/A'))
    with col3:
        timeline_risk = site.get('timeline_risk', 'not_assessed')
        risk_color = {'on_track': '🟢', 'at_risk': '🟡', 'not_credible': '🔴'}.get(timeline_risk, '⚪')
        st.metric("Timeline Risk", f"{risk_color} {timeline_risk.replace('_', ' ').title()}")
    
    # Diagnosis summary
    if site.get('diagnosis_json'):
        try:
            diagnosis = json.loads(site['diagnosis_json']) if isinstance(site['diagnosis_json'], str) else site['diagnosis_json']
            
            st.markdown(f"**Recommendation:** {diagnosis.get('recommendation')}")
            
            # Top risks
            if diagnosis.get('top_risks'):
                st.markdown("**Top Risks:**")
                for risk in diagnosis['top_risks']:
                    st.markdown(f"- ⚠️ {risk}")
            
            # Follow-up actions
            if diagnosis.get('follow_up_actions'):
                st.markdown("**Required Actions:**")
                for action in diagnosis['follow_up_actions']:
                    st.markdown(f"- [ ] {action}")
        except (json.JSONDecodeError, TypeError):
            st.warning("Could not parse diagnosis data")
    
    # Research reports
    if site.get('research_reports_json'):
        try:
            reports = json.loads(site['research_reports_json']) if isinstance(site['research_reports_json'], str) else site['research_reports_json']
            st.subheader("📄 Research Reports")
            for report in reports:
                st.markdown(f"- 📄 {report.get('type', 'Report')} ({report.get('date', 'N/A')})")
        except (json.JSONDecodeError, TypeError):
            pass
    
    # Actions
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Refresh Research", key=f"refresh_{site_id}"):
            st.info("Research refresh would trigger here")
    with col2:
        if st.button("🏥 Re-run Diagnosis", key=f"rerun_{site_id}"):
            st.info("Diagnosis re-run would trigger here")
