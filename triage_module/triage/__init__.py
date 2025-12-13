"""
Triage & Intelligence Module
============================
Phase 1 (Quick Triage) and Phase 2 (Full Diagnosis) for data center site evaluation.

Usage:
    from triage import run_triage, run_diagnosis, TriageIntake, show_quick_triage
    
    # Phase 1: Quick Triage
    intake = TriageIntake(
        county="Tulsa",
        state="OK",
        claimed_mw=200,
        claimed_timeline="Q4 2028",
    )
    result = run_triage(intake)
    
    # Phase 2: Full Diagnosis  
    diagnosis = run_diagnosis(site_data, triage_result=result)
    
    # Pages
    show_quick_triage()  # Streamlit page for triage
    show_full_diagnosis()  # Streamlit page for diagnosis
    show_intelligence_center()  # Streamlit page for intel management
"""

# Models
from .models import (
    # Enums
    TriageVerdict,
    RedFlagSeverity,
    RedFlagCategory,
    TimelineRisk,
    DiagnosisRecommendation,
    ClaimValidationStatus,
    OpportunitySource,
    SitePhase,
    
    # Phase 1 Models
    RedFlag,
    TriageIntake,
    TriageEnrichment,
    TriageResult,
    TriageLogRecord,
    
    # Phase 2 Models
    ClaimValidation,
    UtilityAssessment,
    CompetitiveContext,
    DiagnosisResult,
    
    # Schema
    SITES_TRIAGE_COLUMNS,
    SITES_DIAGNOSIS_COLUMNS,
    SITES_INTELLIGENCE_COLUMNS,
    TRIAGE_LOG_COLUMNS,
)

# Enrichment
from .enrichment import (
    auto_enrich_location,
    lookup_utility,
    get_known_constraints,
    get_utility_appetite_hint,
    validate_mw_for_acreage,
    parse_timeline_claim,
    UTILITY_LOOKUP,
    STATE_ISO_DEFAULT,
)

# Engine
from .engine import (
    run_triage,
    run_diagnosis,
    research_utility,
    get_market_snapshot,
    create_triage_log_record,
    apply_triage_to_site,
    apply_diagnosis_to_site,
    call_gemini_structured,
    call_gemini_simple,
)

# Prompts
from .prompts import (
    TRIAGE_PROMPT,
    DIAGNOSIS_PROMPT,
    UTILITY_INTEL_PROMPT,
    MARKET_SNAPSHOT_PROMPT,
    format_triage_prompt,
    format_diagnosis_prompt,
    format_utility_intel_prompt,
    format_market_snapshot_prompt,
)

# Pages - Quick Triage
from .page import (
    show_quick_triage,
    show_triage_log,
    get_supported_states,
    get_counties_for_state,
)

# Pages - Full Diagnosis
from .diagnosis_page import (
    show_full_diagnosis,
    show_site_intelligence,
)

# Pages - Intelligence Center
from .intelligence_page import (
    show_intelligence_center,
)

# Storage
from .storage import (
    save_triage_to_log,
    load_triage_log,
    get_triage_statistics,
    update_site_triage_fields,
    update_site_diagnosis_fields,
    ensure_triage_columns_exist,
    ensure_triage_log_sheet_exists,
    create_site_from_triage,
)

# Program Tracker Integration
from .tracker_integration import (
    render_intelligence_summary,
    show_intel_summary_widget,
    show_triage_funnel_metrics,
    get_portfolio_intel_metrics,
    render_site_intel_badge,
    render_site_intel_columns,
    prepare_intel_export_data,
)

# PPTX Integration
from .pptx_integration import (
    add_intelligence_slide,
    add_utility_assessment_slide,
    add_competitive_landscape_slide,
    add_all_intelligence_slides,
)

__version__ = "1.0.0"
__all__ = [
    # Enums
    'TriageVerdict',
    'RedFlagSeverity', 
    'RedFlagCategory',
    'TimelineRisk',
    'DiagnosisRecommendation',
    'ClaimValidationStatus',
    'OpportunitySource',
    'SitePhase',
    
    # Models
    'RedFlag',
    'TriageIntake',
    'TriageEnrichment',
    'TriageResult',
    'TriageLogRecord',
    'ClaimValidation',
    'UtilityAssessment',
    'CompetitiveContext',
    'DiagnosisResult',
    
    # Core Functions
    'run_triage',
    'run_diagnosis',
    'auto_enrich_location',
    'research_utility',
    'get_market_snapshot',
    'apply_triage_to_site',
    'apply_diagnosis_to_site',
    
    # Pages
    'show_quick_triage',
    'show_triage_log',
    'show_full_diagnosis',
    'show_site_intelligence',
    'show_intelligence_center',
    
    # Storage
    'save_triage_to_log',
    'load_triage_log',
    'get_triage_statistics',
    'update_site_triage_fields',
    'update_site_diagnosis_fields',
    'ensure_triage_columns_exist',
    'ensure_triage_log_sheet_exists',
    'create_site_from_triage',
    
    # Tracker Integration
    'render_intelligence_summary',
    'show_intel_summary_widget',
    'show_triage_funnel_metrics',
    'get_portfolio_intel_metrics',
    'render_site_intel_badge',
    'render_site_intel_columns',
    'prepare_intel_export_data',
    
    # PPTX Integration
    'add_intelligence_slide',
    'add_utility_assessment_slide',
    'add_competitive_landscape_slide',
    'add_all_intelligence_slides',
    
    # Schema
    'SITES_TRIAGE_COLUMNS',
    'SITES_DIAGNOSIS_COLUMNS',
    'SITES_INTELLIGENCE_COLUMNS',
    'TRIAGE_LOG_COLUMNS',
]
