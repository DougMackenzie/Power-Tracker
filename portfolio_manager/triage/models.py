"""
Triage Data Models
==================
Dataclasses for Phase 1 (Quick Triage) and Phase 2 (Full Diagnosis).
Designed to integrate with existing Google Sheets JSON blob columns.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime
import json


# =============================================================================
# ENUMS
# =============================================================================

class TriageVerdict(Enum):
    """Phase 1 triage outcome."""
    KILL = "KILL"               # Fatal flaws - do not pursue
    CONDITIONAL = "CONDITIONAL" # Proceed with caution, validate specific items
    PASS = "PASS"               # Green light to Phase 2

class RedFlagSeverity(Enum):
    """Severity level for identified issues."""
    FATAL = "fatal"             # Deal killer - triggers KILL verdict
    WARNING = "warning"         # Significant concern - triggers CONDITIONAL
    INFO = "info"               # Notable but not blocking

class RedFlagCategory(Enum):
    """Categories for red flag classification."""
    POWER = "power"             # Utility capacity, timeline, queue issues
    LAND = "land"               # Zoning, acreage, environmental
    EXECUTION = "execution"     # Developer capability, community opposition
    COMMERCIAL = "commercial"   # Deal structure, pricing, competition
    TIMELINE = "timeline"       # Schedule credibility

class TimelineRisk(Enum):
    """Timeline validation assessment."""
    ON_TRACK = "on_track"           # Claimed timeline is achievable
    AT_RISK = "at_risk"             # Timeline aggressive but possible
    NOT_CREDIBLE = "not_credible"   # Timeline is not realistic

class DiagnosisRecommendation(Enum):
    """Phase 2 diagnosis outcome."""
    GO = "GO"                       # Proceed with deal
    CONDITIONAL_GO = "CONDITIONAL_GO"  # Proceed with specific conditions
    NO_GO = "NO_GO"                 # Do not proceed

class ClaimValidationStatus(Enum):
    """Status of developer claim validation."""
    VERIFIED = "verified"                   # Evidence supports claim
    PARTIALLY_VERIFIED = "partially_verified"  # Directionally correct, overstated
    NOT_VERIFIED = "not_verified"           # Cannot find supporting evidence
    CONTRADICTED = "contradicted"           # Evidence contradicts claim

class OpportunitySource(Enum):
    """Source of the opportunity."""
    LANDOWNER = "landowner"
    BROKER = "broker"
    DEVELOPER = "developer"
    UTILITY_REFERRAL = "utility_referral"
    INTERNAL = "internal"
    OTHER = "other"

class SitePhase(Enum):
    """Lifecycle phase of a site in the pipeline."""
    PROSPECT = "0_prospect"         # Just identified, not triaged
    TRIAGE = "1_triage"             # Undergoing triage
    DIAGNOSIS = "2_diagnosis"       # Passed triage, in diagnosis
    ACTIVE = "active"               # In active pipeline
    DEAD = "dead"                   # Killed or abandoned


# =============================================================================
# PHASE 1: TRIAGE MODELS
# =============================================================================

@dataclass
class RedFlag:
    """A single red flag identified during triage or diagnosis."""
    category: RedFlagCategory
    severity: RedFlagSeverity
    flag: str                       # Short description (< 50 chars)
    detail: Optional[str] = None    # Longer explanation
    source: Optional[str] = None    # Where this info came from
    
    def to_dict(self) -> Dict:
        return {
            'category': self.category.value,
            'severity': self.severity.value,
            'flag': self.flag,
            'detail': self.detail,
            'source': self.source,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RedFlag':
        return cls(
            category=RedFlagCategory(data['category']),
            severity=RedFlagSeverity(data['severity']),
            flag=data['flag'],
            detail=data.get('detail'),
            source=data.get('source'),
        )
    
    def is_fatal(self) -> bool:
        return self.severity == RedFlagSeverity.FATAL


@dataclass
class TriageIntake:
    """
    Minimal input for Phase 1 Quick Triage.
    This is what the user provides - everything else is auto-enriched.
    """
    # Required fields
    county: str
    state: str                      # 2-letter code
    claimed_mw: int
    claimed_timeline: str           # e.g., "Q4 2028", "2029", "24 months"
    
    # Optional context
    power_story: Optional[str] = None       # What they told us about power
    site_acres: Optional[float] = None
    source: OpportunitySource = OpportunitySource.OTHER
    contact_name: Optional[str] = None
    contact_info: Optional[str] = None      # Email/phone
    notes: Optional[str] = None
    
    # Options
    run_quick_search: bool = True           # Whether to do web enrichment
    
    def to_dict(self) -> Dict:
        return {
            'county': self.county,
            'state': self.state,
            'claimed_mw': self.claimed_mw,
            'claimed_timeline': self.claimed_timeline,
            'power_story': self.power_story,
            'site_acres': self.site_acres,
            'source': self.source.value if isinstance(self.source, OpportunitySource) else self.source,
            'contact_name': self.contact_name,
            'contact_info': self.contact_info,
            'notes': self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TriageIntake':
        source = data.get('source', 'other')
        if isinstance(source, str):
            try:
                source = OpportunitySource(source)
            except ValueError:
                source = OpportunitySource.OTHER
        
        return cls(
            county=data['county'],
            state=data['state'],
            claimed_mw=int(data['claimed_mw']),
            claimed_timeline=data['claimed_timeline'],
            power_story=data.get('power_story'),
            site_acres=float(data['site_acres']) if data.get('site_acres') else None,
            source=source,
            contact_name=data.get('contact_name'),
            contact_info=data.get('contact_info'),
            notes=data.get('notes'),
        )


@dataclass
class TriageEnrichment:
    """
    Auto-detected/enriched data from location.
    This is populated automatically from county/state lookup.
    """
    utility: str
    iso: str                                # SPP, ERCOT, PJM, MISO, etc.
    jurisdiction_type: str                  # 'unincorporated_county' | 'municipal' | 'etj'
    municipality: Optional[str] = None      # If within city limits
    
    # Additional auto-detected info
    utility_parent: Optional[str] = None    # Parent company if applicable
    regulatory_type: Optional[str] = None   # 'vertically_integrated' | 'deregulated'
    known_constraints: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'utility': self.utility,
            'iso': self.iso,
            'jurisdiction_type': self.jurisdiction_type,
            'municipality': self.municipality,
            'utility_parent': self.utility_parent,
            'regulatory_type': self.regulatory_type,
            'known_constraints': self.known_constraints,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TriageEnrichment':
        return cls(
            utility=data.get('utility', 'Unknown'),
            iso=data.get('iso', 'Unknown'),
            jurisdiction_type=data.get('jurisdiction_type', 'unknown'),
            municipality=data.get('municipality'),
            utility_parent=data.get('utility_parent'),
            regulatory_type=data.get('regulatory_type'),
            known_constraints=data.get('known_constraints', []),
        )


@dataclass
class TriageResult:
    """
    Output from Phase 1 Quick Triage.
    Contains verdict, red flags, and enrichment data.
    """
    verdict: TriageVerdict
    recommendation: str                     # One sentence summary
    red_flags: List[RedFlag]
    enrichment: TriageEnrichment
    
    # Additional outputs
    utility_intel_summary: Optional[str] = None
    validation_questions: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    
    # Metadata
    triage_id: Optional[str] = None
    triage_date: Optional[str] = None
    model_used: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'verdict': self.verdict.value,
            'recommendation': self.recommendation,
            'red_flags': [rf.to_dict() for rf in self.red_flags],
            'enrichment': self.enrichment.to_dict(),
            'utility_intel_summary': self.utility_intel_summary,
            'validation_questions': self.validation_questions,
            'next_steps': self.next_steps,
            'triage_id': self.triage_id,
            'triage_date': self.triage_date,
            'model_used': self.model_used,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TriageResult':
        return cls(
            verdict=TriageVerdict(data['verdict']),
            recommendation=data['recommendation'],
            red_flags=[RedFlag.from_dict(rf) for rf in data.get('red_flags', [])],
            enrichment=TriageEnrichment.from_dict(data.get('enrichment', {})),
            utility_intel_summary=data.get('utility_intel_summary'),
            validation_questions=data.get('validation_questions', []),
            next_steps=data.get('next_steps', []),
            triage_id=data.get('triage_id'),
            triage_date=data.get('triage_date'),
            model_used=data.get('model_used'),
        )
    
    def has_fatal_flags(self) -> bool:
        return any(rf.is_fatal() for rf in self.red_flags)
    
    def get_flags_by_category(self, category: RedFlagCategory) -> List[RedFlag]:
        return [rf for rf in self.red_flags if rf.category == category]
    
    def get_fatal_flags(self) -> List[RedFlag]:
        return [rf for rf in self.red_flags if rf.is_fatal()]


# =============================================================================
# PHASE 2: DIAGNOSIS MODELS
# =============================================================================

@dataclass
class ClaimValidation:
    """Validation of a specific developer claim."""
    claim: str                              # What they claimed
    status: ClaimValidationStatus
    evidence: str                           # What we found
    confidence: str                         # 'high' | 'medium' | 'low'
    follow_up: Optional[str] = None         # Question to ask if needed
    
    def to_dict(self) -> Dict:
        return {
            'claim': self.claim,
            'status': self.status.value,
            'evidence': self.evidence,
            'confidence': self.confidence,
            'follow_up': self.follow_up,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ClaimValidation':
        return cls(
            claim=data['claim'],
            status=ClaimValidationStatus(data['status']),
            evidence=data['evidence'],
            confidence=data.get('confidence', 'medium'),
            follow_up=data.get('follow_up'),
        )


@dataclass
class UtilityAssessment:
    """Deep assessment of utility position and capabilities."""
    appetite: str                           # 'aggressive' | 'moderate' | 'defensive'
    capacity_position: str                  # e.g., "500 MW deficit by 2028"
    realistic_timeline: str                 # e.g., "Q2 2031"
    key_insight: str                        # Most important thing to know
    queue_status: Optional[str] = None      # Queue backlog info
    recent_activity: Optional[str] = None   # Recent RFPs, IRPs, etc.
    
    def to_dict(self) -> Dict:
        return {
            'appetite': self.appetite,
            'capacity_position': self.capacity_position,
            'realistic_timeline': self.realistic_timeline,
            'key_insight': self.key_insight,
            'queue_status': self.queue_status,
            'recent_activity': self.recent_activity,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UtilityAssessment':
        return cls(
            appetite=data.get('appetite', 'unknown'),
            capacity_position=data.get('capacity_position', 'Unknown'),
            realistic_timeline=data.get('realistic_timeline', 'Unknown'),
            key_insight=data.get('key_insight', ''),
            queue_status=data.get('queue_status'),
            recent_activity=data.get('recent_activity'),
        )


@dataclass
class CompetitiveContext:
    """Competitive landscape assessment."""
    regional_projects: int                  # Count of known projects
    key_competitors: List[str]              # "Developer (status)"
    differentiation_required: str           # What this site needs to stand out
    market_saturation: Optional[str] = None # 'low' | 'moderate' | 'high'
    
    def to_dict(self) -> Dict:
        return {
            'regional_projects': self.regional_projects,
            'key_competitors': self.key_competitors,
            'differentiation_required': self.differentiation_required,
            'market_saturation': self.market_saturation,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CompetitiveContext':
        return cls(
            regional_projects=data.get('regional_projects', 0),
            key_competitors=data.get('key_competitors', []),
            differentiation_required=data.get('differentiation_required', ''),
            market_saturation=data.get('market_saturation'),
        )


@dataclass
class DiagnosisResult:
    """
    Output from Phase 2 Full Diagnosis.
    Contains comprehensive assessment and research findings.
    """
    recommendation: DiagnosisRecommendation
    
    # Timeline analysis
    validated_timeline: str                 # Our realistic assessment
    claimed_timeline: str                   # What they claimed
    timeline_risk: TimelineRisk
    timeline_delta_months: int              # Difference in months
    
    # Validations
    claim_validations: List[ClaimValidation]
    
    # Assessments
    utility_assessment: UtilityAssessment
    competitive_context: CompetitiveContext
    
    # Summary outputs
    top_risks: List[str]
    follow_up_actions: List[str]
    research_summary: str                   # 500-word synthesis
    
    # Research artifacts
    research_reports: List[Dict] = field(default_factory=list)  # [{type, url, date}]
    
    # Metadata
    diagnosis_id: Optional[str] = None
    diagnosis_date: Optional[str] = None
    model_used: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'recommendation': self.recommendation.value,
            'validated_timeline': self.validated_timeline,
            'claimed_timeline': self.claimed_timeline,
            'timeline_risk': self.timeline_risk.value,
            'timeline_delta_months': self.timeline_delta_months,
            'claim_validations': [cv.to_dict() for cv in self.claim_validations],
            'utility_assessment': self.utility_assessment.to_dict(),
            'competitive_context': self.competitive_context.to_dict(),
            'top_risks': self.top_risks,
            'follow_up_actions': self.follow_up_actions,
            'research_summary': self.research_summary,
            'research_reports': self.research_reports,
            'diagnosis_id': self.diagnosis_id,
            'diagnosis_date': self.diagnosis_date,
            'model_used': self.model_used,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DiagnosisResult':
        return cls(
            recommendation=DiagnosisRecommendation(data['recommendation']),
            validated_timeline=data['validated_timeline'],
            claimed_timeline=data['claimed_timeline'],
            timeline_risk=TimelineRisk(data['timeline_risk']),
            timeline_delta_months=data.get('timeline_delta_months', 0),
            claim_validations=[ClaimValidation.from_dict(cv) for cv in data.get('claim_validations', [])],
            utility_assessment=UtilityAssessment.from_dict(data.get('utility_assessment', {})),
            competitive_context=CompetitiveContext.from_dict(data.get('competitive_context', {})),
            top_risks=data.get('top_risks', []),
            follow_up_actions=data.get('follow_up_actions', []),
            research_summary=data.get('research_summary', ''),
            research_reports=data.get('research_reports', []),
            diagnosis_id=data.get('diagnosis_id'),
            diagnosis_date=data.get('diagnosis_date'),
            model_used=data.get('model_used'),
        )


# =============================================================================
# TRIAGE LOG RECORD
# =============================================================================

@dataclass
class TriageLogRecord:
    """
    A record in the Triage Log sheet.
    Tracks all opportunities, including those killed.
    """
    triage_id: str
    created_date: str
    
    # Input data
    county: str
    state: str
    claimed_mw: int
    claimed_timeline: str
    power_story: Optional[str]
    source: str
    contact_name: Optional[str]
    contact_info: Optional[str]
    
    # Auto-enriched
    detected_utility: str
    detected_iso: str
    jurisdiction_type: str
    
    # Results
    verdict: str                            # 'KILL' | 'CONDITIONAL' | 'PASS'
    red_flags_json: str                     # JSON string of red flags
    enrichment_json: str                    # JSON string of enrichment
    notes: Optional[str]
    
    # Disposition
    advanced_to_phase2: bool = False
    phase2_site_id: Optional[str] = None    # If advanced, link to Sites sheet
    archived_reason: Optional[str] = None   # If killed
    
    def to_row(self) -> List[Any]:
        """Convert to a row for Google Sheets."""
        return [
            self.triage_id,
            self.created_date,
            self.county,
            self.state,
            self.claimed_mw,
            self.claimed_timeline,
            self.power_story or '',
            self.source,
            self.contact_name or '',
            self.contact_info or '',
            self.detected_utility,
            self.detected_iso,
            self.jurisdiction_type,
            self.verdict,
            self.red_flags_json,
            self.enrichment_json,
            self.notes or '',
            self.advanced_to_phase2,
            self.phase2_site_id or '',
            self.archived_reason or '',
        ]
    
    @classmethod
    def from_row(cls, row: List[Any]) -> 'TriageLogRecord':
        """Create from a Google Sheets row."""
        return cls(
            triage_id=str(row[0]),
            created_date=str(row[1]),
            county=str(row[2]),
            state=str(row[3]),
            claimed_mw=int(row[4]) if row[4] else 0,
            claimed_timeline=str(row[5]),
            power_story=str(row[6]) if row[6] else None,
            source=str(row[7]),
            contact_name=str(row[8]) if row[8] else None,
            contact_info=str(row[9]) if row[9] else None,
            detected_utility=str(row[10]),
            detected_iso=str(row[11]),
            jurisdiction_type=str(row[12]),
            verdict=str(row[13]),
            red_flags_json=str(row[14]),
            enrichment_json=str(row[15]),
            notes=str(row[16]) if row[16] else None,
            advanced_to_phase2=bool(row[17]) if len(row) > 17 else False,
            phase2_site_id=str(row[18]) if len(row) > 18 and row[18] else None,
            archived_reason=str(row[19]) if len(row) > 19 and row[19] else None,
        )


# =============================================================================
# COLUMN DEFINITIONS FOR GOOGLE SHEETS
# =============================================================================

# New columns to add to Sites sheet
SITES_TRIAGE_COLUMNS = [
    'phase',                    # SitePhase value
    'triage_date',
    'triage_verdict',
    'triage_red_flags_json',
    'claimed_timeline',
    'triage_source',
    'triage_contact',
    'triage_power_story',
]

SITES_DIAGNOSIS_COLUMNS = [
    'diagnosis_date',
    'diagnosis_json',
    'validated_timeline',
    'timeline_risk',
    'claim_validation_json',
    'diagnosis_recommendation',
    'diagnosis_top_risks',
    'diagnosis_follow_ups',
]

SITES_INTELLIGENCE_COLUMNS = [
    'utility_intel_json',
    'market_intel_json',
    'research_summary',
    'research_reports_json',
    'last_research_date',
]

# Triage Log sheet columns
TRIAGE_LOG_COLUMNS = [
    'triage_id',
    'created_date',
    'county',
    'state',
    'claimed_mw',
    'claimed_timeline',
    'power_story',
    'source',
    'contact_name',
    'contact_info',
    'detected_utility',
    'detected_iso',
    'jurisdiction_type',
    'verdict',
    'red_flags_json',
    'enrichment_json',
    'notes',
    'advanced_to_phase2',
    'phase2_site_id',
    'archived_reason',
]
