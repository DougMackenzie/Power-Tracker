"""
Prompt Templates for Triage & Diagnosis
=======================================
Structured prompts for Gemini API calls.
Designed for JSON output parsing.
"""


# =============================================================================
# PHASE 1: QUICK TRIAGE PROMPT
# =============================================================================

TRIAGE_PROMPT = """You are a data center site evaluation expert. Perform a quick red-flag analysis on this opportunity.

OPPORTUNITY DETAILS:
- Location: {county} County, {state}
- Claimed MW: {claimed_mw}
- Developer's Timeline Claim: {claimed_timeline}
- Power Story (what they told us): {power_story}
- Site Size: {site_acres}

AUTO-ENRICHED CONTEXT:
- Detected Utility: {utility}
- Utility Parent: {utility_parent}
- Detected ISO: {iso}
- Regulatory Type: {regulatory_type}
- Jurisdiction Type: {jurisdiction_type}

INTELLIGENCE CONTEXT:
{utility_intel}

KNOWN REGIONAL CONSTRAINTS:
{known_constraints}

---

EVALUATE FOR RED FLAGS IN THESE CATEGORIES:

1. POWER (fatal = deal killer, warning = proceed with caution):
   - Is the timeline claim realistic given utility capacity and queue status?
   - Is the MW claim reasonable for this utility territory?
   - Are there any moratoriums, queue freezes, or capacity constraints?
   - Does the "power story" align with what we know about this utility?

2. LAND (fatal/warning):
   - Is the acreage sufficient for the claimed MW? (Rule: ~3-5 acres/MW for hyperscale)
   - Is this location likely in a compatible zoning category?
   - Are there known environmental constraints in this region?

3. EXECUTION (fatal/warning):
   - Does this jurisdiction have a pattern of opposition to data centers?
   - Are there any known community resistance issues in this area?
   - Is there any indication the developer/landowner is unrealistic?

4. TIMELINE (warning):
   - Is the claimed timeline achievable given typical utility study timelines?
   - Are there specific queue or study bottlenecks to consider?

---

DECISION RULES:
- KILL: Any FATAL red flag → Stop evaluation, archive with reason
- CONDITIONAL: Any WARNING flags → Proceed but validate specific items
- PASS: No significant flags → Green light to Phase 2 diagnosis

---

Return ONLY a valid JSON object with this exact structure:
{{
    "verdict": "KILL" | "CONDITIONAL" | "PASS",
    "recommendation": "One sentence summary of your assessment",
    "red_flags": [
        {{
            "category": "power" | "land" | "execution" | "timeline",
            "severity": "fatal" | "warning" | "info",
            "flag": "Short description (under 50 chars)",
            "detail": "Longer explanation with specifics"
        }}
    ],
    "validation_questions": [
        "Question to ask developer/landowner to validate a specific concern"
    ],
    "utility_intel_summary": "Brief summary of what we know about this utility's position",
    "timeline_assessment": "Brief assessment of whether claimed timeline is achievable"
}}

IMPORTANT: Return ONLY the JSON object. No markdown, no explanation, no preamble.
"""


# =============================================================================
# PHASE 2: FULL DIAGNOSIS PROMPT
# =============================================================================

DIAGNOSIS_PROMPT = """You are a data center site evaluation expert conducting a comprehensive diagnosis.

SITE INFORMATION:
- Name: {site_name}
- Location: {county} County, {state}
- Utility: {utility}
- ISO: {iso}
- Target MW: {target_mw}
- Site Acreage: {site_acres}
- Developer's Claimed Timeline: {claimed_timeline}

PRIOR TRIAGE RESULTS:
- Triage Verdict: {triage_verdict}
- Red Flags Identified: {triage_red_flags}
- Validation Questions: {validation_questions}

DEVELOPER/LANDOWNER CLAIMS TO VALIDATE:
{developer_claims}

UTILITY INTELLIGENCE (if available):
{utility_intel}

MARKET INTELLIGENCE (if available):
{market_intel}

---

RESEARCH AND VALIDATE THE FOLLOWING:

1. UTILITY CAPACITY & APPETITE
   - What is {utility}'s actual capacity position?
   - What is their realistic timeline for new large loads?
   - Are they actively seeking load or in defensive mode?
   - Any recent IRP filings, RFPs, or capacity announcements?
   - What is the queue backlog for this ISO?

2. TIMELINE VALIDATION
   - Compare claimed timeline ({claimed_timeline}) against:
     * Typical utility study timelines (screening: 3-6mo, system impact: 6-12mo)
     * Facilities study and IA negotiation (6-12mo)
     * Construction timeline for required infrastructure
   - Calculate realistic energization date
   - Identify specific bottlenecks

3. CLAIM VALIDATION
   For each developer claim, determine:
   - VERIFIED: Evidence directly supports the claim
   - PARTIALLY_VERIFIED: Directionally correct but overstated or missing nuance
   - NOT_VERIFIED: Cannot find supporting evidence
   - CONTRADICTED: Evidence directly contradicts the claim

4. COMPETITIVE LANDSCAPE
   - What other data center projects are announced in this region?
   - Who are the major developers/hyperscalers active here?
   - Is this site differentiated or commoditized?
   - What would make this site stand out?

5. SITE DUE DILIGENCE
   - Zoning pathway in this jurisdiction
   - Water availability and provider
   - Community sentiment (any recent opposition?)
   - Environmental considerations

---

Return ONLY a valid JSON object with this exact structure:
{{
    "recommendation": "GO" | "CONDITIONAL_GO" | "NO_GO",
    "recommendation_rationale": "2-3 sentence explanation of the recommendation",
    
    "validated_timeline": "YYYY-QN (your realistic assessment)",
    "claimed_timeline": "{claimed_timeline}",
    "timeline_risk": "on_track" | "at_risk" | "not_credible",
    "timeline_delta_months": N,
    "timeline_explanation": "Explanation of timeline assessment",
    
    "claim_validations": [
        {{
            "claim": "What they claimed",
            "status": "verified" | "partially_verified" | "not_verified" | "contradicted",
            "evidence": "What we found",
            "confidence": "high" | "medium" | "low",
            "follow_up": "Question to ask if further validation needed"
        }}
    ],
    
    "utility_assessment": {{
        "appetite": "aggressive" | "moderate" | "defensive",
        "capacity_position": "Description of capacity position (e.g., '500 MW deficit by 2028')",
        "realistic_timeline": "YYYY-QN",
        "key_insight": "Most important thing to know about this utility",
        "queue_status": "Description of queue/interconnection backlog",
        "recent_activity": "Recent RFPs, IRPs, announcements"
    }},
    
    "competitive_context": {{
        "regional_projects": N,
        "key_competitors": ["Developer (status)", "Developer (status)"],
        "differentiation_required": "What this site needs to stand out",
        "market_saturation": "low" | "moderate" | "high"
    }},
    
    "top_risks": [
        "Risk 1 (most critical)",
        "Risk 2",
        "Risk 3"
    ],
    
    "follow_up_actions": [
        "Specific action required",
        "Another action"
    ],
    
    "research_summary": "500-word synthesis of findings covering utility position, timeline assessment, competitive landscape, and key considerations for this opportunity"
}}

IMPORTANT: Return ONLY the JSON object. No markdown, no explanation, no preamble.
"""


# =============================================================================
# UTILITY INTELLIGENCE PROMPT
# =============================================================================

UTILITY_INTEL_PROMPT = """Research the following electric utility for data center development context.

UTILITY: {utility_name}
PARENT COMPANY: {parent_company}
SERVICE TERRITORY: {service_territory}
ISO/RTO: {iso}

RESEARCH THE FOLLOWING:

1. CAPACITY POSITION
   - Current generation capacity vs peak demand
   - Announced capacity additions or retirements
   - Load growth projections from most recent IRP
   - Any capacity deficit or surplus expected?

2. DATA CENTER APPETITE
   - Have they announced interest in data center load?
   - Any recent large load interconnections approved?
   - Any moratoriums or restrictions on new large loads?
   - What is their typical timeline for large load interconnections?

3. INTERCONNECTION PROCESS
   - What studies are required? (screening, system impact, facilities)
   - Typical duration for each study phase
   - Are there any expedited pathways available?
   - Current queue backlog

4. RECENT ACTIVITY
   - Recent IRP filings (date and key findings)
   - Any RFPs for capacity or large load service?
   - Recent rate cases or regulatory proceedings
   - Any announced partnerships or initiatives

5. RELATIONSHIP INTELLIGENCE
   - Key contacts for large load development
   - Known decision-making process
   - Historical responsiveness to data center inquiries

Return ONLY a valid JSON object:
{{
    "utility_name": "{utility_name}",
    "parent_company": "{parent_company}",
    "iso": "{iso}",
    
    "capacity_position": {{
        "current_deficit_surplus_mw": N,
        "deficit_year": "YYYY",
        "trend": "growing_deficit" | "stable" | "improving",
        "notes": "Explanation"
    }},
    
    "appetite_rating": "aggressive" | "moderate" | "defensive",
    "appetite_explanation": "Why this rating",
    
    "timeline_intel": {{
        "typical_screening_months": N,
        "typical_impact_study_months": N,
        "typical_facilities_study_months": N,
        "typical_ia_negotiation_months": N,
        "expedited_pathways": ["pathway1", "pathway2"],
        "realistic_total_months": N
    }},
    
    "queue_status": {{
        "backlog_mw": N,
        "backlog_projects": N,
        "average_wait_months": N,
        "notes": "Any relevant details"
    }},
    
    "recent_activity": [
        {{
            "date": "YYYY-MM",
            "type": "IRP" | "RFP" | "announcement" | "rate_case",
            "summary": "Brief description"
        }}
    ],
    
    "key_contacts": [
        {{
            "name": "Name",
            "title": "Title",
            "notes": "Any relevant notes"
        }}
    ],
    
    "data_center_history": {{
        "known_projects": N,
        "recent_approvals": "Description of recent approvals if any",
        "known_issues": "Any known issues or concerns"
    }},
    
    "overall_assessment": "2-3 sentence summary of utility's position for data center development"
}}
"""


# =============================================================================
# MARKET SNAPSHOT PROMPT
# =============================================================================

MARKET_SNAPSHOT_PROMPT = """Provide a market intelligence snapshot for data center development in this region.

REGION: {state} - {iso} territory
UTILITY: {utility}
DATE: {current_date}

RESEARCH THE FOLLOWING:

1. ACTIVE PROJECTS
   - Announced data center projects in this region
   - Projects under construction
   - Recently completed projects
   - Known pipeline or rumors

2. DEVELOPER ACTIVITY
   - Which hyperscalers are active here?
   - Which data center developers are active?
   - Any recent land acquisitions or announcements?

3. SUPPLY/DEMAND DYNAMICS
   - Current data center inventory (MW)
   - Vacancy rates if available
   - Demand drivers for this region

4. REGULATORY ENVIRONMENT
   - Any recent regulatory changes affecting data centers?
   - Tax incentives available
   - Known moratoria or restrictions

5. COMPETITIVE POSITIONING
   - What makes sites attractive in this market?
   - Key differentiators for successful projects
   - Common pitfalls or challenges

Return ONLY a valid JSON object:
{{
    "region": "{state} - {iso}",
    "snapshot_date": "{current_date}",
    
    "active_projects": [
        {{
            "name": "Project Name",
            "developer": "Developer Name",
            "location": "City/County",
            "capacity_mw": N,
            "status": "announced" | "construction" | "operational",
            "notes": "Any relevant details"
        }}
    ],
    
    "developer_activity": {{
        "hyperscalers_active": ["Company1", "Company2"],
        "developers_active": ["Developer1", "Developer2"],
        "recent_land_deals": "Description of recent activity"
    }},
    
    "market_metrics": {{
        "estimated_inventory_mw": N,
        "estimated_pipeline_mw": N,
        "vacancy_rate": "X%" | "unknown",
        "demand_outlook": "strong" | "moderate" | "weak"
    }},
    
    "regulatory_environment": {{
        "incentives_available": ["Incentive1", "Incentive2"],
        "known_restrictions": ["Restriction1"],
        "recent_changes": "Description of any recent changes"
    }},
    
    "competitive_insights": {{
        "key_differentiators": ["Factor1", "Factor2"],
        "common_challenges": ["Challenge1", "Challenge2"],
        "market_saturation": "low" | "moderate" | "high"
    }},
    
    "observations": [
        "Key observation 1",
        "Key observation 2"
    ],
    
    "overall_assessment": "2-3 sentence summary of market conditions"
}}
"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_triage_prompt(
    county: str,
    state: str,
    claimed_mw: int,
    claimed_timeline: str,
    power_story: str = "Not provided",
    site_acres: str = "Not provided",
    utility: str = "Unknown",
    utility_parent: str = "Unknown",
    iso: str = "Unknown",
    regulatory_type: str = "Unknown",
    jurisdiction_type: str = "Unknown",
    utility_intel: str = "None available",
    known_constraints: str = "None known",
) -> str:
    """Format the triage prompt with provided values."""
    return TRIAGE_PROMPT.format(
        county=county,
        state=state,
        claimed_mw=claimed_mw,
        claimed_timeline=claimed_timeline,
        power_story=power_story,
        site_acres=site_acres,
        utility=utility,
        utility_parent=utility_parent or "Unknown",
        iso=iso,
        regulatory_type=regulatory_type or "Unknown",
        jurisdiction_type=jurisdiction_type,
        utility_intel=utility_intel,
        known_constraints=known_constraints,
    )


def format_diagnosis_prompt(
    site_name: str,
    county: str,
    state: str,
    utility: str,
    iso: str,
    target_mw: int,
    site_acres: str,
    claimed_timeline: str,
    triage_verdict: str,
    triage_red_flags: str,
    validation_questions: str,
    developer_claims: str,
    utility_intel: str = "None available",
    market_intel: str = "None available",
) -> str:
    """Format the diagnosis prompt with provided values."""
    return DIAGNOSIS_PROMPT.format(
        site_name=site_name,
        county=county,
        state=state,
        utility=utility,
        iso=iso,
        target_mw=target_mw,
        site_acres=site_acres,
        claimed_timeline=claimed_timeline,
        triage_verdict=triage_verdict,
        triage_red_flags=triage_red_flags,
        validation_questions=validation_questions,
        developer_claims=developer_claims,
        utility_intel=utility_intel,
        market_intel=market_intel,
    )


def format_utility_intel_prompt(
    utility_name: str,
    parent_company: str,
    service_territory: str,
    iso: str,
) -> str:
    """Format the utility intelligence prompt."""
    return UTILITY_INTEL_PROMPT.format(
        utility_name=utility_name,
        parent_company=parent_company or "Unknown",
        service_territory=service_territory,
        iso=iso,
    )


def format_market_snapshot_prompt(
    state: str,
    iso: str,
    utility: str,
) -> str:
    """Format the market snapshot prompt."""
    from datetime import datetime
    return MARKET_SNAPSHOT_PROMPT.format(
        state=state,
        iso=iso,
        utility=utility,
        current_date=datetime.now().strftime("%Y-%m-%d"),
    )
