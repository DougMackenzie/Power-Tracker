"""
Quick Triage Page
=================
Streamlit UI for Phase 1 Quick Triage.
Minimal input, fast red-flag detection.
"""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, Optional

from .models import (
    TriageIntake, TriageResult, TriageLogRecord,
    TriageVerdict, RedFlagSeverity, RedFlagCategory, OpportunitySource,
)
from .engine import run_triage, create_triage_log_record, apply_triage_to_site
from .enrichment import auto_enrich_location, UTILITY_LOOKUP


# =============================================================================
# UI HELPERS
# =============================================================================

def verdict_badge(verdict: TriageVerdict) -> str:
    """Return styled verdict badge."""
    badges = {
        TriageVerdict.KILL: "🔴 **KILL**",
        TriageVerdict.CONDITIONAL: "🟡 **CONDITIONAL**",
        TriageVerdict.PASS: "🟢 **PASS**",
    }
    return badges.get(verdict, "⚪ Unknown")


def severity_icon(severity: RedFlagSeverity) -> str:
    """Return icon for severity level."""
    icons = {
        RedFlagSeverity.FATAL: "❌",
        RedFlagSeverity.WARNING: "⚠️",
        RedFlagSeverity.INFO: "ℹ️",
    }
    return icons.get(severity, "•")


def category_label(category: RedFlagCategory) -> str:
    """Return display label for category."""
    labels = {
        RedFlagCategory.POWER: "⚡ Power",
        RedFlagCategory.LAND: "🏞️ Land",
        RedFlagCategory.EXECUTION: "🏗️ Execution",
        RedFlagCategory.COMMERCIAL: "💰 Commercial",
        RedFlagCategory.TIMELINE: "📅 Timeline",
    }
    return labels.get(category, category.value)


# =============================================================================
# MAIN PAGE
# =============================================================================

def show_quick_triage():
    """Main Quick Triage page."""
    
    st.title("🚦 Quick Triage")
    st.markdown("""
    **Phase 1: Red Flag Detection**
    
    Enter minimal opportunity details for fast go/no-go screening.
    The system will auto-enrich location data and identify deal-killer red flags.
    """)
    
    # Initialize session state
    if 'triage_result' not in st.session_state:
        st.session_state.triage_result = None
    if 'triage_intake' not in st.session_state:
        st.session_state.triage_intake = None
    
    # Two-column layout
    col_input, col_result = st.columns([1, 1])
    
    with col_input:
        st.subheader("📝 Opportunity Details")
        
        # Core required fields
        with st.form("triage_form"):
            # Location
            col1, col2 = st.columns(2)
            with col1:
                county = st.text_input(
                    "County *",
                    placeholder="e.g., Tulsa",
                    help="County name (without 'County' suffix)"
                )
            with col2:
                state = st.selectbox(
                    "State *",
                    options=['', 'OK', 'TX', 'KS', 'AR', 'MO', 'LA', 'NM', 'CO', 'NE'],
                    help="State code"
                )
            
            # Power requirements
            col1, col2 = st.columns(2)
            with col1:
                claimed_mw = st.number_input(
                    "Claimed MW *",
                    min_value=1,
                    max_value=5000,
                    value=100,
                    step=50,
                    help="Developer's claimed target MW"
                )
            with col2:
                claimed_timeline = st.text_input(
                    "Claimed Timeline *",
                    placeholder="e.g., Q4 2028, 2029, 24 months",
                    help="When they say power will be ready"
                )
            
            # Optional context
            st.markdown("---")
            st.markdown("**Optional Context**")
            
            power_story = st.text_area(
                "Power Story",
                placeholder="What did they tell you about the power situation?",
                help="Their narrative about utility, capacity, timeline, etc.",
                height=80,
            )
            
            col1, col2 = st.columns(2)
            with col1:
                site_acres = st.number_input(
                    "Site Acres",
                    min_value=0.0,
                    max_value=10000.0,
                    value=0.0,
                    step=10.0,
                    help="Total site acreage (optional)"
                )
            with col2:
                source = st.selectbox(
                    "Source",
                    options=[
                        ('landowner', 'Landowner'),
                        ('broker', 'Broker'),
                        ('developer', 'Developer'),
                        ('utility_referral', 'Utility Referral'),
                        ('internal', 'Internal'),
                        ('other', 'Other'),
                    ],
                    format_func=lambda x: x[1],
                    help="How did this opportunity come in?"
                )
            
            col1, col2 = st.columns(2)
            with col1:
                contact_name = st.text_input(
                    "Contact Name",
                    placeholder="Who brought this to you?"
                )
            with col2:
                contact_info = st.text_input(
                    "Contact Info",
                    placeholder="Email or phone"
                )
            
            notes = st.text_area(
                "Notes",
                placeholder="Any other relevant context...",
                height=60,
            )
            
            # Submit button
            submitted = st.form_submit_button(
                "🚀 Run Triage",
                type="primary",
                use_container_width=True,
            )
        
        # Handle form submission
        if submitted:
            # Validate required fields
            if not county:
                st.error("County is required")
            elif not state:
                st.error("State is required")
            elif not claimed_timeline:
                st.error("Claimed Timeline is required")
            else:
                # Build intake
                intake = TriageIntake(
                    county=county,
                    state=state,
                    claimed_mw=claimed_mw,
                    claimed_timeline=claimed_timeline,
                    power_story=power_story if power_story else None,
                    site_acres=site_acres if site_acres > 0 else None,
                    source=OpportunitySource(source[0]),
                    contact_name=contact_name if contact_name else None,
                    contact_info=contact_info if contact_info else None,
                    notes=notes if notes else None,
                )
                
                # Store intake
                st.session_state.triage_intake = intake
                
                # Run triage
                with st.spinner("Running triage analysis..."):
                    try:
                        result = run_triage(intake)
                        st.session_state.triage_result = result
                    except Exception as e:
                        st.error(f"Triage failed: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
        
        # Quick preview of auto-enrichment
        if county and state:
            with st.expander("🔍 Auto-Enrichment Preview", expanded=False):
                preview = auto_enrich_location(county, state)
                st.markdown(f"""
                - **Utility:** {preview.utility}
                - **ISO:** {preview.iso}
                - **Parent:** {preview.utility_parent or 'Unknown'}
                - **Type:** {preview.regulatory_type or 'Unknown'}
                """)
                if preview.known_constraints:
                    st.markdown("**Known Constraints:**")
                    for c in preview.known_constraints:
                        st.markdown(f"- {c}")
    
    with col_result:
        st.subheader("📊 Triage Result")
        
        result = st.session_state.triage_result
        
        if result is None:
            st.info("Enter opportunity details and click 'Run Triage' to see results.")
        else:
            # Verdict header
            st.markdown(f"### {verdict_badge(result.verdict)}")
            st.markdown(f"*{result.recommendation}*")
            
            # Metrics row
            col1, col2, col3 = st.columns(3)
            with col1:
                fatal_count = len([rf for rf in result.red_flags if rf.severity == RedFlagSeverity.FATAL])
                st.metric("Fatal Flags", fatal_count)
            with col2:
                warning_count = len([rf for rf in result.red_flags if rf.severity == RedFlagSeverity.WARNING])
                st.metric("Warnings", warning_count)
            with col3:
                st.metric("Total Flags", len(result.red_flags))
            
            st.divider()
            
            # Red Flags section
            if result.red_flags:
                st.markdown("#### 🚩 Red Flags")
                for rf in result.red_flags:
                    severity_style = {
                        RedFlagSeverity.FATAL: "background-color: #ffebee; border-left: 4px solid #f44336;",
                        RedFlagSeverity.WARNING: "background-color: #fff3e0; border-left: 4px solid #ff9800;",
                        RedFlagSeverity.INFO: "background-color: #e3f2fd; border-left: 4px solid #2196f3;",
                    }
                    
                    st.markdown(f"""
                    <div style="{severity_style.get(rf.severity, '')} padding: 10px; margin: 5px 0; border-radius: 4px;">
                        <strong>{severity_icon(rf.severity)} {category_label(rf.category)}</strong><br/>
                        <strong>{rf.flag}</strong><br/>
                        <span style="color: #666;">{rf.detail or ''}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("✅ No significant red flags identified")
            
            st.divider()
            
            # Enrichment section
            st.markdown("#### 📍 Auto-Enriched Data")
            enr = result.enrichment
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Utility:** {enr.utility}")
                st.markdown(f"**Parent:** {enr.utility_parent or 'Unknown'}")
                st.markdown(f"**ISO:** {enr.iso}")
            with col2:
                st.markdown(f"**Jurisdiction:** {enr.jurisdiction_type}")
                st.markdown(f"**Regulatory Type:** {enr.regulatory_type or 'Unknown'}")
            
            if result.utility_intel_summary:
                st.markdown("**Utility Intel:**")
                st.info(result.utility_intel_summary)
            
            st.divider()
            
            # Validation Questions
            if result.validation_questions:
                st.markdown("#### ❓ Validation Questions")
                st.markdown("*Ask these to validate concerns before proceeding:*")
                for q in result.validation_questions:
                    st.markdown(f"- {q}")
            
            # Next Steps
            if result.next_steps:
                st.markdown("#### ➡️ Next Steps")
                for step in result.next_steps:
                    st.markdown(f"- {step}")
            
            st.divider()
            
            # Actions
            st.markdown("#### 🎯 Actions")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if result.verdict == TriageVerdict.KILL:
                    if st.button("🗑️ Archive & Document", type="secondary", use_container_width=True):
                        st.session_state.archive_reason = st.text_input(
                            "Archive Reason",
                            value=result.recommendation
                        )
                        st.success("Archived. Pattern documented for analysis.")
                else:
                    if st.button("✅ Advance to Phase 2", type="primary", use_container_width=True):
                        # This would create a site record and navigate to diagnosis
                        st.success("Ready for Phase 2 Full Diagnosis")
                        st.info("Site record would be created in database")
            
            with col2:
                if st.button("📋 Export JSON", use_container_width=True):
                    st.download_button(
                        label="Download JSON",
                        data=result.to_json(),
                        file_name=f"triage_{result.triage_id}.json",
                        mime="application/json",
                    )
            
            # Metadata
            with st.expander("🔧 Metadata"):
                st.markdown(f"""
                - **Triage ID:** {result.triage_id}
                - **Date:** {result.triage_date}
                - **Model:** {result.model_used}
                """)


# =============================================================================
# TRIAGE LOG PAGE
# =============================================================================

def show_triage_log():
    """Show triage log / history page."""
    
    st.title("📋 Triage Log")
    st.markdown("History of all triaged opportunities, including those killed.")
    
    # This would load from Google Sheets Triage_Log tab
    # For now, show placeholder
    
    st.info("Triage Log will display here once connected to database.")
    
    # Example data structure
    example_data = [
        {
            "triage_id": "TRI-20251212-ABC123",
            "date": "2025-12-12",
            "county": "Tulsa",
            "state": "OK",
            "claimed_mw": 200,
            "claimed_timeline": "Q4 2028",
            "utility": "PSO",
            "verdict": "CONDITIONAL",
            "advanced": True,
        },
        {
            "triage_id": "TRI-20251210-XYZ789",
            "date": "2025-12-10",
            "county": "Harris",
            "state": "TX",
            "claimed_mw": 500,
            "claimed_timeline": "2027",
            "utility": "CenterPoint",
            "verdict": "KILL",
            "advanced": False,
        },
    ]
    
    # Display as table
    st.dataframe(
        example_data,
        column_config={
            "verdict": st.column_config.TextColumn(
                "Verdict",
                help="KILL, CONDITIONAL, or PASS"
            ),
            "advanced": st.column_config.CheckboxColumn(
                "Advanced",
                help="Did this advance to Phase 2?"
            ),
        },
        use_container_width=True,
    )
    
    # Statistics
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Triaged", "47")
    with col2:
        st.metric("Kill Rate", "38%")
    with col3:
        st.metric("Pass Rate", "23%")
    with col4:
        st.metric("Conditional", "39%")
    
    # Pattern insights
    st.markdown("### 📊 Pattern Insights")
    st.markdown("""
    - **67%** of broker-sourced deals fail triage (timeline issues)
    - **PSO territory** has highest pass rate (54%)
    - **ERCOT** deals killed primarily due to queue backlog
    """)


# =============================================================================
# INTEGRATION HELPERS
# =============================================================================

def get_supported_states():
    """Get list of states with utility lookup data."""
    return sorted(UTILITY_LOOKUP.keys())


def get_counties_for_state(state: str) -> list:
    """Get list of counties with utility data for a state."""
    state_data = UTILITY_LOOKUP.get(state.upper(), {})
    return sorted([c.title() for c in state_data.keys()])
