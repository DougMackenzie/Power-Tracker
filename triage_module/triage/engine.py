"""
Triage Engine
=============
Core logic for Phase 1 (Quick Triage) and Phase 2 (Full Diagnosis).
Uses Gemini API for AI-powered analysis.
"""

import json
import re
import uuid
from datetime import datetime
from typing import Dict, Optional, List, Any, Tuple

from .models import (
    TriageIntake, TriageResult, TriageEnrichment, TriageLogRecord,
    DiagnosisResult, RedFlag, ClaimValidation, UtilityAssessment, CompetitiveContext,
    TriageVerdict, RedFlagSeverity, RedFlagCategory,
    TimelineRisk, DiagnosisRecommendation, ClaimValidationStatus,
    SitePhase,
)
from .enrichment import (
    auto_enrich_location, 
    get_utility_appetite_hint,
    validate_mw_for_acreage,
    parse_timeline_claim,
)
from .prompts import (
    format_triage_prompt,
    format_diagnosis_prompt,
    format_utility_intel_prompt,
    format_market_snapshot_prompt,
)


# =============================================================================
# GEMINI API INTEGRATION
# =============================================================================

def get_gemini_model(model_name: str = "models/gemini-2.0-flash-exp"):
    """
    Get configured Gemini model.
    Uses Streamlit secrets for API key.
    """
    try:
        import google.generativeai as genai
        import streamlit as st
        
        api_key = st.secrets.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in Streamlit secrets")
        
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(model_name)
    except ImportError:
        raise ImportError("google-generativeai package not installed")


def call_gemini_structured(
    prompt: str, 
    model_name: str = "models/gemini-2.0-flash-exp"
) -> Tuple[Dict, Optional[str]]:
    """
    Call Gemini with a structured prompt, parse JSON response.
    
    Returns:
        Tuple of (parsed_dict, error_message)
        If successful, error_message is None
        If failed, parsed_dict is empty and error_message contains details
    """
    try:
        model = get_gemini_model(model_name)
        response = model.generate_content(prompt)
        
        # Extract text from response
        raw_text = response.text.strip()
        
        # Parse JSON with multiple fallback strategies
        json_str = raw_text
        
        # Strategy 1: Look for ```json blocks
        if "```json" in raw_text:
            json_str = raw_text.split("```json")[1].split("```")[0].strip()
        # Strategy 2: Look for generic ``` blocks
        elif "```" in raw_text:
            parts = raw_text.split("```")
            if len(parts) >= 2:
                json_str = parts[1].strip()
        # Strategy 3: Look for { } braces
        elif "{" in raw_text and "}" in raw_text:
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if match:
                json_str = match.group(0)
        
        # Attempt to parse
        try:
            parsed = json.loads(json_str)
            return parsed, None
        except json.JSONDecodeError as e:
            return {}, f"JSON parse error: {e}. Raw response: {raw_text[:500]}"
            
    except Exception as e:
        return {}, f"Gemini API error: {str(e)}"


def call_gemini_simple(
    prompt: str, 
    model_name: str = "models/gemini-2.0-flash-exp"
) -> Tuple[str, Optional[str]]:
    """
    Call Gemini and return raw text response.
    
    Returns:
        Tuple of (response_text, error_message)
    """
    try:
        model = get_gemini_model(model_name)
        response = model.generate_content(prompt)
        return response.text.strip(), None
    except Exception as e:
        return "", f"Gemini API error: {str(e)}"


# =============================================================================
# PHASE 1: QUICK TRIAGE
# =============================================================================

def run_triage(intake: TriageIntake) -> TriageResult:
    """
    Run Phase 1 Quick Triage on an opportunity.
    
    This is the main entry point for triage. It:
    1. Auto-enriches location data (utility, ISO, etc.)
    2. Checks for obvious red flags
    3. Calls Gemini for AI-powered analysis
    4. Returns structured TriageResult
    """
    
    # Generate triage ID
    triage_id = f"TRI-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    triage_date = datetime.now().isoformat()
    
    # Step 1: Auto-enrich location
    enrichment = auto_enrich_location(intake.county, intake.state)
    
    # Step 2: Check for immediate red flags (pre-AI checks)
    pre_flags = []
    
    # Check MW vs acreage
    if intake.site_acres:
        mw_valid, mw_note = validate_mw_for_acreage(intake.claimed_mw, intake.site_acres)
        if not mw_valid:
            pre_flags.append(RedFlag(
                category=RedFlagCategory.LAND,
                severity=RedFlagSeverity.WARNING,
                flag="MW/acreage mismatch",
                detail=mw_note,
            ))
    
    # Check for unknown utility
    if "unknown" in enrichment.utility.lower():
        pre_flags.append(RedFlag(
            category=RedFlagCategory.POWER,
            severity=RedFlagSeverity.INFO,
            flag="Utility not in lookup table",
            detail=f"County {intake.county} not found in utility lookup. Manual research required.",
        ))
    
    # Step 3: Get utility intelligence hint (placeholder for full intel)
    utility_hint = get_utility_appetite_hint(enrichment.utility)
    
    # Step 4: Format known constraints
    constraints_str = "\n".join([f"- {c}" for c in enrichment.known_constraints]) if enrichment.known_constraints else "None known"
    
    # Step 5: Build and call Gemini prompt
    prompt = format_triage_prompt(
        county=intake.county,
        state=intake.state,
        claimed_mw=intake.claimed_mw,
        claimed_timeline=intake.claimed_timeline,
        power_story=intake.power_story or "Not provided",
        site_acres=f"{intake.site_acres} acres" if intake.site_acres else "Not provided",
        utility=enrichment.utility,
        utility_parent=enrichment.utility_parent,
        iso=enrichment.iso,
        regulatory_type=enrichment.regulatory_type,
        jurisdiction_type=enrichment.jurisdiction_type,
        utility_intel=utility_hint or "None available - utility not yet researched",
        known_constraints=constraints_str,
    )
    
    # Call Gemini
    result_dict, error = call_gemini_structured(prompt)
    
    if error:
        # Return error result
        return TriageResult(
            verdict=TriageVerdict.CONDITIONAL,
            recommendation=f"Triage incomplete due to error: {error}",
            red_flags=pre_flags,
            enrichment=enrichment,
            next_steps=["Retry triage", "Manual review required"],
            triage_id=triage_id,
            triage_date=triage_date,
            model_used="error",
        )
    
    # Step 6: Parse AI response
    try:
        # Parse verdict
        verdict_str = result_dict.get('verdict', 'CONDITIONAL')
        try:
            verdict = TriageVerdict(verdict_str)
        except ValueError:
            verdict = TriageVerdict.CONDITIONAL
        
        # Parse red flags from AI
        ai_flags = []
        for rf_dict in result_dict.get('red_flags', []):
            try:
                ai_flags.append(RedFlag(
                    category=RedFlagCategory(rf_dict.get('category', 'power')),
                    severity=RedFlagSeverity(rf_dict.get('severity', 'warning')),
                    flag=rf_dict.get('flag', 'Unknown flag'),
                    detail=rf_dict.get('detail'),
                    source="AI analysis",
                ))
            except (ValueError, KeyError):
                continue
        
        # Combine pre-flags with AI flags
        all_flags = pre_flags + ai_flags
        
        # Build result
        return TriageResult(
            verdict=verdict,
            recommendation=result_dict.get('recommendation', 'Review required'),
            red_flags=all_flags,
            enrichment=enrichment,
            utility_intel_summary=result_dict.get('utility_intel_summary'),
            validation_questions=result_dict.get('validation_questions', []),
            next_steps=_determine_next_steps(verdict, all_flags),
            triage_id=triage_id,
            triage_date=triage_date,
            model_used="gemini-2.0-flash-exp",
        )
        
    except Exception as e:
        return TriageResult(
            verdict=TriageVerdict.CONDITIONAL,
            recommendation=f"Error parsing AI response: {str(e)}",
            red_flags=pre_flags,
            enrichment=enrichment,
            next_steps=["Manual review required"],
            triage_id=triage_id,
            triage_date=triage_date,
            model_used="parse_error",
        )


def _determine_next_steps(verdict: TriageVerdict, flags: List[RedFlag]) -> List[str]:
    """Determine next steps based on verdict and flags."""
    steps = []
    
    if verdict == TriageVerdict.KILL:
        steps.append("Archive opportunity with reason")
        steps.append("Document for pattern analysis")
        return steps
    
    if verdict == TriageVerdict.PASS:
        steps.append("Advance to Phase 2 Full Diagnosis")
        steps.append("Gather developer claims for validation")
        steps.append("Request site documentation")
        return steps
    
    # CONDITIONAL
    steps.append("Validate specific concerns before proceeding")
    
    # Add specific steps based on flags
    categories = set(f.category for f in flags if f.severity == RedFlagSeverity.WARNING)
    
    if RedFlagCategory.POWER in categories:
        steps.append("Verify utility timeline claims with utility contact")
    if RedFlagCategory.LAND in categories:
        steps.append("Confirm site acreage and zoning")
    if RedFlagCategory.EXECUTION in categories:
        steps.append("Research jurisdiction approval history")
    if RedFlagCategory.TIMELINE in categories:
        steps.append("Build realistic timeline model")
    
    return steps


# =============================================================================
# PHASE 2: FULL DIAGNOSIS
# =============================================================================

def run_diagnosis(
    site_data: Dict,
    triage_result: Optional[TriageResult] = None,
    developer_claims: Optional[List[str]] = None,
    utility_intel: Optional[Dict] = None,
    market_intel: Optional[Dict] = None,
) -> DiagnosisResult:
    """
    Run Phase 2 Full Diagnosis on a site.
    
    This performs comprehensive research and validation:
    1. Validates developer claims
    2. Assesses utility position and timeline
    3. Analyzes competitive landscape
    4. Provides detailed recommendations
    """
    
    # Generate diagnosis ID
    diagnosis_id = f"DX-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    diagnosis_date = datetime.now().isoformat()
    
    # Extract site info
    site_name = site_data.get('name', 'Unknown Site')
    county = site_data.get('county', '')
    state = site_data.get('state', '')
    utility = site_data.get('utility', '')
    iso = site_data.get('iso', '')
    target_mw = site_data.get('target_mw', 0)
    site_acres = site_data.get('acreage', 'Unknown')
    claimed_timeline = site_data.get('claimed_timeline', 'Not specified')
    
    # Format triage context
    triage_verdict = "Not triaged"
    triage_red_flags = "None"
    validation_questions = "None"
    
    if triage_result:
        triage_verdict = triage_result.verdict.value
        triage_red_flags = "\n".join([
            f"- [{rf.severity.value.upper()}] {rf.flag}: {rf.detail}"
            for rf in triage_result.red_flags
        ]) or "None identified"
        validation_questions = "\n".join([
            f"- {q}" for q in triage_result.validation_questions
        ]) or "None"
    
    # Format developer claims
    claims_str = "None provided"
    if developer_claims:
        claims_str = "\n".join([f"- {claim}" for claim in developer_claims])
    
    # Format intelligence
    utility_intel_str = "None available"
    if utility_intel:
        utility_intel_str = json.dumps(utility_intel, indent=2)
    
    market_intel_str = "None available"
    if market_intel:
        market_intel_str = json.dumps(market_intel, indent=2)
    
    # Build prompt
    prompt = format_diagnosis_prompt(
        site_name=site_name,
        county=county,
        state=state,
        utility=utility,
        iso=iso,
        target_mw=target_mw,
        site_acres=str(site_acres),
        claimed_timeline=claimed_timeline,
        triage_verdict=triage_verdict,
        triage_red_flags=triage_red_flags,
        validation_questions=validation_questions,
        developer_claims=claims_str,
        utility_intel=utility_intel_str,
        market_intel=market_intel_str,
    )
    
    # Call Gemini
    result_dict, error = call_gemini_structured(prompt)
    
    if error:
        # Return error result
        return DiagnosisResult(
            recommendation=DiagnosisRecommendation.CONDITIONAL_GO,
            validated_timeline="Unknown",
            claimed_timeline=claimed_timeline,
            timeline_risk=TimelineRisk.AT_RISK,
            timeline_delta_months=0,
            claim_validations=[],
            utility_assessment=UtilityAssessment(
                appetite="unknown",
                capacity_position="Unknown - diagnosis failed",
                realistic_timeline="Unknown",
                key_insight=f"Diagnosis failed: {error}",
            ),
            competitive_context=CompetitiveContext(
                regional_projects=0,
                key_competitors=[],
                differentiation_required="Unable to assess",
            ),
            top_risks=[f"Diagnosis incomplete: {error}"],
            follow_up_actions=["Retry diagnosis", "Manual research required"],
            research_summary=f"Diagnosis failed due to error: {error}",
            diagnosis_id=diagnosis_id,
            diagnosis_date=diagnosis_date,
            model_used="error",
        )
    
    # Parse response
    try:
        # Parse recommendation
        rec_str = result_dict.get('recommendation', 'CONDITIONAL_GO')
        try:
            recommendation = DiagnosisRecommendation(rec_str)
        except ValueError:
            recommendation = DiagnosisRecommendation.CONDITIONAL_GO
        
        # Parse timeline risk
        risk_str = result_dict.get('timeline_risk', 'at_risk')
        try:
            timeline_risk = TimelineRisk(risk_str)
        except ValueError:
            timeline_risk = TimelineRisk.AT_RISK
        
        # Parse claim validations
        claim_validations = []
        for cv_dict in result_dict.get('claim_validations', []):
            try:
                claim_validations.append(ClaimValidation(
                    claim=cv_dict.get('claim', ''),
                    status=ClaimValidationStatus(cv_dict.get('status', 'not_verified')),
                    evidence=cv_dict.get('evidence', ''),
                    confidence=cv_dict.get('confidence', 'medium'),
                    follow_up=cv_dict.get('follow_up'),
                ))
            except (ValueError, KeyError):
                continue
        
        # Parse utility assessment
        ua_dict = result_dict.get('utility_assessment', {})
        utility_assessment = UtilityAssessment(
            appetite=ua_dict.get('appetite', 'unknown'),
            capacity_position=ua_dict.get('capacity_position', 'Unknown'),
            realistic_timeline=ua_dict.get('realistic_timeline', 'Unknown'),
            key_insight=ua_dict.get('key_insight', ''),
            queue_status=ua_dict.get('queue_status'),
            recent_activity=ua_dict.get('recent_activity'),
        )
        
        # Parse competitive context
        cc_dict = result_dict.get('competitive_context', {})
        competitive_context = CompetitiveContext(
            regional_projects=cc_dict.get('regional_projects', 0),
            key_competitors=cc_dict.get('key_competitors', []),
            differentiation_required=cc_dict.get('differentiation_required', ''),
            market_saturation=cc_dict.get('market_saturation'),
        )
        
        return DiagnosisResult(
            recommendation=recommendation,
            validated_timeline=result_dict.get('validated_timeline', 'Unknown'),
            claimed_timeline=claimed_timeline,
            timeline_risk=timeline_risk,
            timeline_delta_months=result_dict.get('timeline_delta_months', 0),
            claim_validations=claim_validations,
            utility_assessment=utility_assessment,
            competitive_context=competitive_context,
            top_risks=result_dict.get('top_risks', []),
            follow_up_actions=result_dict.get('follow_up_actions', []),
            research_summary=result_dict.get('research_summary', ''),
            research_reports=[],  # Would be populated by actual research
            diagnosis_id=diagnosis_id,
            diagnosis_date=diagnosis_date,
            model_used="gemini-2.0-flash-exp",
        )
        
    except Exception as e:
        return DiagnosisResult(
            recommendation=DiagnosisRecommendation.CONDITIONAL_GO,
            validated_timeline="Unknown",
            claimed_timeline=claimed_timeline,
            timeline_risk=TimelineRisk.AT_RISK,
            timeline_delta_months=0,
            claim_validations=[],
            utility_assessment=UtilityAssessment(
                appetite="unknown",
                capacity_position="Parse error",
                realistic_timeline="Unknown",
                key_insight=f"Error parsing response: {str(e)}",
            ),
            competitive_context=CompetitiveContext(
                regional_projects=0,
                key_competitors=[],
                differentiation_required="Unable to assess",
            ),
            top_risks=[f"Parse error: {str(e)}"],
            follow_up_actions=["Manual review required"],
            research_summary=f"Error parsing diagnosis response: {str(e)}",
            diagnosis_id=diagnosis_id,
            diagnosis_date=diagnosis_date,
            model_used="parse_error",
        )


# =============================================================================
# UTILITY INTELLIGENCE
# =============================================================================

def research_utility(
    utility_name: str,
    parent_company: Optional[str] = None,
    service_territory: Optional[str] = None,
    iso: Optional[str] = None,
) -> Tuple[Dict, Optional[str]]:
    """
    Research a utility for data center development context.
    
    Returns:
        Tuple of (intel_dict, error_message)
    """
    prompt = format_utility_intel_prompt(
        utility_name=utility_name,
        parent_company=parent_company or "Unknown",
        service_territory=service_territory or utility_name,
        iso=iso or "Unknown",
    )
    
    return call_gemini_structured(prompt)


# =============================================================================
# MARKET INTELLIGENCE
# =============================================================================

def get_market_snapshot(
    state: str,
    iso: str,
    utility: Optional[str] = None,
) -> Tuple[Dict, Optional[str]]:
    """
    Get a market intelligence snapshot for a region.
    
    Returns:
        Tuple of (snapshot_dict, error_message)
    """
    prompt = format_market_snapshot_prompt(
        state=state,
        iso=iso,
        utility=utility or "Various",
    )
    
    return call_gemini_structured(prompt)


# =============================================================================
# TRIAGE LOG MANAGEMENT
# =============================================================================

def create_triage_log_record(
    intake: TriageIntake,
    result: TriageResult,
) -> TriageLogRecord:
    """Create a TriageLogRecord from intake and result."""
    return TriageLogRecord(
        triage_id=result.triage_id or f"TRI-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        created_date=result.triage_date or datetime.now().isoformat(),
        county=intake.county,
        state=intake.state,
        claimed_mw=intake.claimed_mw,
        claimed_timeline=intake.claimed_timeline,
        power_story=intake.power_story,
        source=intake.source.value if hasattr(intake.source, 'value') else str(intake.source),
        contact_name=intake.contact_name,
        contact_info=intake.contact_info,
        detected_utility=result.enrichment.utility,
        detected_iso=result.enrichment.iso,
        jurisdiction_type=result.enrichment.jurisdiction_type,
        verdict=result.verdict.value,
        red_flags_json=json.dumps([rf.to_dict() for rf in result.red_flags]),
        enrichment_json=json.dumps(result.enrichment.to_dict()),
        notes=intake.notes,
        advanced_to_phase2=result.verdict != TriageVerdict.KILL,
    )


# =============================================================================
# SITE DATABASE INTEGRATION
# =============================================================================

def apply_triage_to_site(site_data: Dict, result: TriageResult) -> Dict:
    """
    Apply triage results to a site data dictionary.
    Returns the updated site_data.
    """
    site_data['phase'] = SitePhase.TRIAGE.value if result.verdict != TriageVerdict.KILL else SitePhase.DEAD.value
    site_data['triage_date'] = result.triage_date
    site_data['triage_verdict'] = result.verdict.value
    site_data['triage_red_flags_json'] = json.dumps([rf.to_dict() for rf in result.red_flags])
    
    # Update utility/ISO if auto-enriched
    if result.enrichment.utility and "unknown" not in result.enrichment.utility.lower():
        site_data['utility'] = result.enrichment.utility
    if result.enrichment.iso and result.enrichment.iso != "Unknown":
        site_data['iso'] = result.enrichment.iso
    
    return site_data


def apply_diagnosis_to_site(site_data: Dict, result: DiagnosisResult) -> Dict:
    """
    Apply diagnosis results to a site data dictionary.
    Returns the updated site_data.
    """
    site_data['phase'] = SitePhase.DIAGNOSIS.value
    site_data['diagnosis_date'] = result.diagnosis_date
    site_data['diagnosis_json'] = result.to_json()
    site_data['validated_timeline'] = result.validated_timeline
    site_data['timeline_risk'] = result.timeline_risk.value
    site_data['claim_validation_json'] = json.dumps([cv.to_dict() for cv in result.claim_validations])
    site_data['diagnosis_recommendation'] = result.recommendation.value
    site_data['diagnosis_top_risks'] = ", ".join(result.top_risks[:3])
    site_data['diagnosis_follow_ups'] = ", ".join(result.follow_up_actions[:3])
    site_data['research_summary'] = result.research_summary
    
    return site_data
