"""
Powered Land Site Assessment Tool
=================================
Diagnoses development stage, scores against ingredients framework,
estimates valuation, and identifies gaps to advance.

Based on research framework:
- Right Ingredients hierarchy
- State tier scoring
- Bimodal valuation model
- 12-18 month sprint requirements
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import date
import json

# =============================================================================
# REFERENCE DATA
# =============================================================================

STATE_SCORES = {
    # Tier 1 (75-100)
    'OK': {'score': 88, 'tier': 1, 'name': 'Oklahoma'},
    'WY': {'score': 82, 'tier': 1, 'name': 'Wyoming'},
    'TX': {'score': 80, 'tier': 1, 'name': 'Texas'},
    
    # Tier 2 (60-74)
    'WV': {'score': 76, 'tier': 2, 'name': 'West Virginia'},
    'IN': {'score': 72, 'tier': 2, 'name': 'Indiana'},
    'AR': {'score': 71, 'tier': 2, 'name': 'Arkansas'},
    'OH': {'score': 70, 'tier': 2, 'name': 'Ohio'},
    'GA': {'score': 70, 'tier': 2, 'name': 'Georgia'},
    'PA': {'score': 68, 'tier': 2, 'name': 'Pennsylvania'},
    'LA': {'score': 68, 'tier': 2, 'name': 'Louisiana'},
    'MS': {'score': 64, 'tier': 2, 'name': 'Mississippi'},
    
    # Tier 3 (50-64)
    'NM': {'score': 67, 'tier': 3, 'name': 'New Mexico'},
    'MT': {'score': 62, 'tier': 3, 'name': 'Montana'},
    'VA': {'score': 58, 'tier': 3, 'name': 'Virginia (Secondary)'},
    'NV': {'score': 55, 'tier': 3, 'name': 'Nevada'},
    'AZ': {'score': 52, 'tier': 3, 'name': 'Arizona'},
    
    # Avoid (<50)
    'NY': {'score': 40, 'tier': 4, 'name': 'New York'},
    'MA': {'score': 35, 'tier': 4, 'name': 'New England'},
    'NoVA': {'score': 30, 'tier': 4, 'name': 'Northern Virginia'},
    'CA': {'score': 25, 'tier': 4, 'name': 'California'},
}

# Valuation by stage ($/MW, 2025, emerging/central markets)
VALUATION_BY_STAGE = {
    'queue_only': {'low': 0, 'mid': 0, 'high': 50000, 'description': 'Queue position only, no other ingredients'},
    'early_real': {'low': 150000, 'mid': 225000, 'high': 300000, 'description': 'Queue + land + credible developer + early utility engagement'},
    'study_in_progress': {'low': 250000, 'mid': 325000, 'high': 400000, 'description': 'Interconnection study underway'},
    'utility_commitment': {'low': 400000, 'mid': 550000, 'high': 700000, 'description': 'Utility has committed to serve'},
    'fully_entitled': {'low': 700000, 'mid': 950000, 'high': 1200000, 'description': 'Zoning, permits, utility locked, 36-mo delivery'},
    'end_user_attached': {'low': 1000000, 'mid': 1250000, 'high': 1500000, 'description': 'LOI or term sheet with hyperscaler/end-user'},
}

# Scale premium for 1GW+ sites
SCALE_PREMIUM = {
    500: 1.0,    # Baseline
    750: 1.15,   # 15% premium
    1000: 1.35,  # 35% premium
    1500: 1.40,  # 40% premium
    2000: 1.45,  # 45% premium
    3000: 1.50,  # 50% premium
}

# Market adjustment factors (vs Central Belt baseline)
MARKET_FACTORS = {
    1: 1.0,    # Tier 1: Central Belt baseline
    2: 1.1,    # Tier 2: 10% premium (slightly harder markets)
    3: 1.0,    # Tier 3: No premium (constraints offset location)
    4: 1.5,    # Tier 4: 50% premium (scarcity pricing) but avoid anyway
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class DevelopmentStage(Enum):
    QUEUE_ONLY = 'queue_only'
    EARLY_REAL = 'early_real'
    STUDY_IN_PROGRESS = 'study_in_progress'
    UTILITY_COMMITMENT = 'utility_commitment'
    FULLY_ENTITLED = 'fully_entitled'
    END_USER_ATTACHED = 'end_user_attached'


@dataclass
class SiteInputs:
    """Input data for site assessment."""
    
    # Basic info
    site_name: str
    state: str  # 2-letter code
    county: str = ""
    nearest_city: str = ""
    
    # Scale
    total_acreage: int = 0
    developable_acreage: int = 0
    target_mw: int = 0  # Target IT load
    max_potential_mw: int = 0  # Maximum buildout potential
    
    # Land status
    land_controlled: bool = False
    land_control_type: str = ""  # "owned", "option", "LOI", "none"
    option_expiry_date: Optional[date] = None
    option_extensions_available: int = 0
    
    # Power/Queue status
    queue_position: bool = False
    queue_iso: str = ""  # PJM, ERCOT, SPP, MISO, etc.
    queue_mw: int = 0
    queue_date: Optional[date] = None
    study_phase: str = ""  # "none", "feasibility", "system_impact", "facilities"
    study_completion_date: Optional[date] = None
    
    # Utility engagement
    utility_name: str = ""
    utility_contact_level: str = ""  # "none", "initial", "account_rep", "executive", "committed"
    utility_study_requested: bool = False
    utility_study_approved: bool = False
    utility_commitment_letter: bool = False
    estimated_service_date: Optional[date] = None
    
    # Infrastructure
    transmission_distance_miles: float = 0
    substation_capacity_mw: int = 0
    upgrade_required: bool = False
    upgrade_cost_estimate: int = 0  # $
    
    water_source: str = ""  # "municipal", "well", "river", "none"
    water_rights_secured: bool = False
    water_capacity_mgd: float = 0  # Million gallons per day
    
    fiber_lit: bool = False
    fiber_providers: List[str] = field(default_factory=list)
    fiber_distance_miles: float = 0
    
    # Entitlements
    zoning_compatible: bool = False
    zoning_change_required: bool = False
    zoning_application_submitted: bool = False
    zoning_approved: bool = False
    
    environmental_phase1_complete: bool = False
    environmental_phase2_required: bool = False
    environmental_issues: List[str] = field(default_factory=list)
    
    permits_identified: List[str] = field(default_factory=list)
    permits_obtained: List[str] = field(default_factory=list)
    
    # End-user interest
    end_user_tours: int = 0
    end_user_nda_signed: int = 0
    end_user_loi: bool = False
    end_user_term_sheet: bool = False
    end_user_name: str = ""  # If disclosed
    
    # BTM potential
    btm_viable: bool = False
    btm_sources: List[str] = field(default_factory=list)  # "solar", "gas", "fuel_cell", "battery"
    btm_mw_potential: int = 0
    
    # Community/Political
    community_support: str = ""  # "unknown", "neutral", "supportive", "opposition"
    political_engagement: str = ""  # "none", "initial", "supportive", "champion"
    
    # Developer capability (self-assessment or known)
    developer_name: str = ""
    developer_track_record: str = ""  # "none", "limited", "proven", "extensive"
    developer_utility_relationships: str = ""  # "none", "some", "strong"
    developer_capital_access: str = ""  # "limited", "moderate", "strong"
    
    # Notes
    notes: str = ""
    key_risks: List[str] = field(default_factory=list)
    key_opportunities: List[str] = field(default_factory=list)


# =============================================================================
# ASSESSMENT ENGINE
# =============================================================================

class SiteAssessment:
    """
    Assesses a site against the Ingredients framework.
    Determines development stage, valuation, and gaps.
    """
    
    def __init__(self, inputs: SiteInputs):
        self.inputs = inputs
        self.scores = {}
        self.stage = None
        self.valuation = {}
        self.gaps = []
        self.next_actions = []
        
    def run_assessment(self) -> Dict:
        """Run full assessment and return results."""
        self._score_ingredients()
        self._determine_stage()
        self._calculate_valuation()
        self._identify_gaps()
        self._recommend_actions()
        
        return self.get_summary()
    
    def _score_ingredients(self):
        """Score site against each ingredient category."""
        
        # TIER 4: Site-Specific (Table Stakes)
        land_score = self._score_land()
        queue_score = self._score_queue()
        water_score = self._score_water()
        fiber_score = self._score_fiber()
        
        self.scores['site_specific'] = {
            'land': land_score,
            'queue': queue_score,
            'water': water_score,
            'fiber': fiber_score,
            'total': round((land_score + queue_score + water_score + fiber_score) / 4, 1)
        }
        
        # TIER 3: Financial Capability
        capital_score = self._score_capital()
        self.scores['financial'] = {
            'capital_access': capital_score,
            'total': capital_score
        }
        
        # TIER 2: Execution Capability
        developer_score = self._score_developer()
        utility_relationship_score = self._score_utility_relationship()
        btm_score = self._score_btm()
        
        self.scores['execution'] = {
            'developer': developer_score,
            'utility_relationship': utility_relationship_score,
            'btm_capability': btm_score,
            'total': round((developer_score + utility_relationship_score + btm_score) / 3, 1)
        }
        
        # TIER 1: Relationship Capital
        end_user_score = self._score_end_user()
        community_score = self._score_community()
        
        self.scores['relationship_capital'] = {
            'end_user': end_user_score,
            'community': community_score,
            'total': round((end_user_score + community_score) / 2, 1)
        }
        
        # Power pathway (special - crosses tiers)
        power_score = self._score_power_pathway()
        self.scores['power_pathway'] = power_score
        
        # Overall weighted score
        # Weights reflect value hierarchy (Tier 1 most important)
        weights = {
            'relationship_capital': 0.35,
            'power_pathway': 0.30,
            'execution': 0.20,
            'site_specific': 0.10,
            'financial': 0.05
        }
        
        overall = (
            self.scores['relationship_capital']['total'] * weights['relationship_capital'] +
            self.scores['power_pathway']['total'] * weights['power_pathway'] +
            self.scores['execution']['total'] * weights['execution'] +
            self.scores['site_specific']['total'] * weights['site_specific'] +
            self.scores['financial']['total'] * weights['financial']
        )
        
        self.scores['overall'] = round(overall, 1)
    
    def _score_land(self) -> int:
        """Score land control (0-100)."""
        if not self.inputs.land_controlled:
            return 0
        
        score = 50  # Base for any control
        
        if self.inputs.land_control_type == 'owned':
            score = 100
        elif self.inputs.land_control_type == 'option':
            score = 70
            # Penalize if expiring soon
            if self.inputs.option_expiry_date:
                days_remaining = (self.inputs.option_expiry_date - date.today()).days
                if days_remaining < 180:
                    score -= 20
                elif days_remaining < 365:
                    score -= 10
        elif self.inputs.land_control_type == 'LOI':
            score = 40
        
        # Bonus for adequate acreage
        if self.inputs.developable_acreage >= 500:
            score = min(100, score + 10)
        
        return score
    
    def _score_queue(self) -> int:
        """Score queue position (0-100)."""
        if not self.inputs.queue_position:
            return 0
        
        score = 30  # Base for having queue
        
        # Study phase progression
        phase_scores = {
            'feasibility': 50,
            'system_impact': 70,
            'facilities': 90
        }
        score = phase_scores.get(self.inputs.study_phase, score)
        
        # ISO quality adjustment
        iso_bonus = {
            'SPP': 15,
            'MISO': 10,
            'ERCOT': 5,
            'SERC': 5,
            'PJM': 0,  # Congested
            'WECC': -5,  # Slow
        }
        score += iso_bonus.get(self.inputs.queue_iso, 0)
        
        return min(100, max(0, score))
    
    def _score_water(self) -> int:
        """Score water access (0-100)."""
        if self.inputs.water_source == 'none' or not self.inputs.water_source:
            return 0
        
        score = 40  # Base for identified source
        
        if self.inputs.water_rights_secured:
            score = 80
        
        # Capacity adequacy (rough: 0.5 MGD per 100MW)
        if self.inputs.water_capacity_mgd > 0 and self.inputs.target_mw > 0:
            required_mgd = self.inputs.target_mw * 0.005
            if self.inputs.water_capacity_mgd >= required_mgd:
                score = min(100, score + 20)
        
        return score
    
    def _score_fiber(self) -> int:
        """Score fiber connectivity (0-100)."""
        if not self.inputs.fiber_lit and not self.inputs.fiber_providers:
            return 20  # Fiber is rarely a blocker
        
        if self.inputs.fiber_lit:
            score = 100
        elif self.inputs.fiber_providers:
            score = 70
            if self.inputs.fiber_distance_miles <= 1:
                score = 90
            elif self.inputs.fiber_distance_miles <= 5:
                score = 80
        else:
            score = 50
        
        return score
    
    def _score_capital(self) -> int:
        """Score financial capability (0-100)."""
        access_scores = {
            'strong': 100,
            'moderate': 70,
            'limited': 40,
            '': 50  # Unknown
        }
        return access_scores.get(self.inputs.developer_capital_access, 50)
    
    def _score_developer(self) -> int:
        """Score developer track record (0-100)."""
        track_scores = {
            'extensive': 100,
            'proven': 80,
            'limited': 50,
            'none': 20,
            '': 50  # Unknown
        }
        return track_scores.get(self.inputs.developer_track_record, 50)
    
    def _score_utility_relationship(self) -> int:
        """Score utility relationship depth (0-100)."""
        level_scores = {
            'committed': 100,
            'executive': 80,
            'account_rep': 50,
            'initial': 30,
            'none': 0,
            '': 20  # Unknown
        }
        base = level_scores.get(self.inputs.utility_contact_level, 20)
        
        # Bonus for relationship quality assessment
        rel_bonus = {
            'strong': 20,
            'some': 10,
            'none': 0,
            '': 0
        }
        bonus = rel_bonus.get(self.inputs.developer_utility_relationships, 0)
        
        return min(100, base + bonus)
    
    def _score_btm(self) -> int:
        """Score behind-the-meter capability (0-100)."""
        if not self.inputs.btm_viable:
            return 30  # Not critical but helpful
        
        score = 60  # Base for viable BTM
        
        # Multiple sources = more flexibility
        if len(self.inputs.btm_sources) >= 2:
            score += 20
        
        # Meaningful capacity
        if self.inputs.btm_mw_potential >= 100:
            score += 20
        
        return min(100, score)
    
    def _score_end_user(self) -> int:
        """Score end-user pipeline (0-100)."""
        if self.inputs.end_user_term_sheet:
            return 100
        if self.inputs.end_user_loi:
            return 85
        if self.inputs.end_user_nda_signed >= 2:
            return 60
        if self.inputs.end_user_nda_signed == 1:
            return 45
        if self.inputs.end_user_tours >= 2:
            return 35
        if self.inputs.end_user_tours == 1:
            return 25
        return 10  # No engagement
    
    def _score_community(self) -> int:
        """Score community/political support (0-100)."""
        community_scores = {
            'supportive': 80,
            'neutral': 50,
            'opposition': 20,
            'unknown': 40,
            '': 40
        }
        political_scores = {
            'champion': 100,
            'supportive': 80,
            'initial': 50,
            'none': 30,
            '': 30
        }
        
        community = community_scores.get(self.inputs.community_support, 40)
        political = political_scores.get(self.inputs.political_engagement, 30)
        
        return round((community + political) / 2)
    
    def _score_power_pathway(self) -> Dict:
        """Score overall power pathway (critical path)."""
        
        # Queue position
        queue = self._score_queue()
        
        # Utility commitment level
        utility_scores = {
            'committed': 100,
            'executive': 70,
            'account_rep': 40,
            'initial': 20,
            'none': 0,
            '': 10
        }
        utility = utility_scores.get(self.inputs.utility_contact_level, 10)
        
        if self.inputs.utility_commitment_letter:
            utility = 100
        elif self.inputs.utility_study_approved:
            utility = max(utility, 60)
        elif self.inputs.utility_study_requested:
            utility = max(utility, 40)
        
        # Transmission access
        if self.inputs.transmission_distance_miles <= 1:
            transmission = 90
        elif self.inputs.transmission_distance_miles <= 5:
            transmission = 70
        elif self.inputs.transmission_distance_miles <= 15:
            transmission = 50
        else:
            transmission = 30
        
        if self.inputs.upgrade_required:
            transmission -= 20
        
        # Timeline reality
        timeline = 50  # Default
        if self.inputs.estimated_service_date:
            months_out = (self.inputs.estimated_service_date - date.today()).days / 30
            if months_out <= 24:
                timeline = 100
            elif months_out <= 36:
                timeline = 80
            elif months_out <= 48:
                timeline = 60
            else:
                timeline = 40
        
        total = round((queue * 0.3 + utility * 0.4 + transmission * 0.2 + timeline * 0.1), 1)
        
        return {
            'queue': queue,
            'utility': utility,
            'transmission': min(100, max(0, transmission)),
            'timeline': timeline,
            'total': total
        }
    
    def _determine_stage(self):
        """Determine current development stage."""
        i = self.inputs
        
        # End-user attached
        if i.end_user_term_sheet or i.end_user_loi:
            self.stage = DevelopmentStage.END_USER_ATTACHED
            return
        
        # Fully entitled
        if (i.utility_commitment_letter and 
            i.zoning_approved and 
            i.environmental_phase1_complete and
            len(i.permits_obtained) >= len(i.permits_identified) * 0.8):
            self.stage = DevelopmentStage.FULLY_ENTITLED
            return
        
        # Utility commitment
        if i.utility_commitment_letter:
            self.stage = DevelopmentStage.UTILITY_COMMITMENT
            return
        
        # Study in progress
        if i.study_phase in ['feasibility', 'system_impact', 'facilities']:
            self.stage = DevelopmentStage.STUDY_IN_PROGRESS
            return
        
        # Early real (has real ingredients beyond queue)
        real_ingredients = sum([
            i.land_controlled,
            i.queue_position,
            i.utility_contact_level in ['account_rep', 'executive', 'committed'],
            i.developer_track_record in ['proven', 'extensive'],
            i.water_source not in ['none', ''],
        ])
        
        if real_ingredients >= 3:
            self.stage = DevelopmentStage.EARLY_REAL
            return
        
        # Queue only
        if i.queue_position:
            self.stage = DevelopmentStage.QUEUE_ONLY
            return
        
        # Pre-queue (not really a stage, but handle it)
        self.stage = DevelopmentStage.QUEUE_ONLY  # Treat as queue-only for valuation
    
    def _calculate_valuation(self):
        """Calculate valuation range based on stage and factors."""
        
        stage_key = self.stage.value
        base_valuation = VALUATION_BY_STAGE[stage_key]
        
        # Get state info
        state_info = STATE_SCORES.get(self.inputs.state, {'tier': 2, 'score': 65})
        state_tier = state_info['tier']
        
        # Market factor
        market_factor = MARKET_FACTORS.get(state_tier, 1.0)
        
        # Scale factor
        target_mw = self.inputs.target_mw or self.inputs.max_potential_mw or 500
        scale_factor = 1.0
        for mw_threshold, factor in sorted(SCALE_PREMIUM.items()):
            if target_mw >= mw_threshold:
                scale_factor = factor
        
        # Quality adjustment based on ingredient scores
        quality_factor = 0.8 + (self.scores['overall'] / 100) * 0.4  # 0.8 to 1.2
        
        # Calculate ranges
        self.valuation = {
            'stage': stage_key,
            'stage_description': base_valuation['description'],
            'target_mw': target_mw,
            'base_per_mw': {
                'low': base_valuation['low'],
                'mid': base_valuation['mid'],
                'high': base_valuation['high']
            },
            'factors': {
                'market': market_factor,
                'scale': scale_factor,
                'quality': round(quality_factor, 2)
            },
            'adjusted_per_mw': {
                'low': int(base_valuation['low'] * market_factor * scale_factor * quality_factor),
                'mid': int(base_valuation['mid'] * market_factor * scale_factor * quality_factor),
                'high': int(base_valuation['high'] * market_factor * scale_factor * quality_factor)
            },
            'total_value': {
                'low': int(base_valuation['low'] * market_factor * scale_factor * quality_factor * target_mw / 1000000),
                'mid': int(base_valuation['mid'] * market_factor * scale_factor * quality_factor * target_mw / 1000000),
                'high': int(base_valuation['high'] * market_factor * scale_factor * quality_factor * target_mw / 1000000)
            },
            'state_tier': state_tier,
            'state_score': state_info['score']
        }
    
    def _identify_gaps(self):
        """Identify gaps preventing advancement to next stage."""
        i = self.inputs
        gaps = []
        
        # Critical gaps (blockers)
        if not i.land_controlled:
            gaps.append({'category': 'critical', 'item': 'Land Control', 
                        'detail': 'No land control in place', 'priority': 1})
        
        if not i.queue_position:
            gaps.append({'category': 'critical', 'item': 'Queue Position',
                        'detail': 'No interconnection queue position', 'priority': 1})
        
        if i.utility_contact_level in ['none', '', 'initial']:
            gaps.append({'category': 'critical', 'item': 'Utility Engagement',
                        'detail': f'Utility engagement at "{i.utility_contact_level or "none"}" level', 'priority': 1})
        
        # Stage-specific gaps
        if self.stage == DevelopmentStage.QUEUE_ONLY:
            if not i.utility_study_requested:
                gaps.append({'category': 'advancement', 'item': 'Interconnection Study',
                            'detail': 'Study not yet requested', 'priority': 2})
        
        elif self.stage == DevelopmentStage.EARLY_REAL:
            if not i.utility_study_approved:
                gaps.append({'category': 'advancement', 'item': 'Study Approval',
                            'detail': 'Interconnection study not yet approved', 'priority': 2})
            if i.end_user_tours == 0:
                gaps.append({'category': 'advancement', 'item': 'End-User Pipeline',
                            'detail': 'No end-user engagement', 'priority': 2})
        
        elif self.stage == DevelopmentStage.STUDY_IN_PROGRESS:
            if not i.utility_commitment_letter:
                gaps.append({'category': 'advancement', 'item': 'Utility Commitment',
                            'detail': 'No commitment letter from utility', 'priority': 2})
            if not i.zoning_application_submitted:
                gaps.append({'category': 'advancement', 'item': 'Zoning',
                            'detail': 'Zoning application not submitted', 'priority': 2})
        
        elif self.stage == DevelopmentStage.UTILITY_COMMITMENT:
            if not i.zoning_approved:
                gaps.append({'category': 'advancement', 'item': 'Zoning Approval',
                            'detail': 'Zoning not yet approved', 'priority': 2})
            if not i.environmental_phase1_complete:
                gaps.append({'category': 'advancement', 'item': 'Environmental',
                            'detail': 'Phase 1 environmental not complete', 'priority': 2})
            if not i.end_user_loi:
                gaps.append({'category': 'advancement', 'item': 'End-User LOI',
                            'detail': 'No LOI from end-user', 'priority': 2})
        
        elif self.stage == DevelopmentStage.FULLY_ENTITLED:
            if not i.end_user_term_sheet:
                gaps.append({'category': 'advancement', 'item': 'Term Sheet',
                            'detail': 'No term sheet with end-user', 'priority': 2})
        
        # Risk gaps (not blockers but concerning)
        if i.option_expiry_date:
            days_remaining = (i.option_expiry_date - date.today()).days
            if days_remaining < 365:
                gaps.append({'category': 'risk', 'item': 'Option Timeline',
                            'detail': f'Option expires in {days_remaining} days', 'priority': 3})
        
        if i.water_source == 'none' or not i.water_rights_secured:
            gaps.append({'category': 'risk', 'item': 'Water',
                        'detail': 'Water rights not secured', 'priority': 3})
        
        if i.community_support == 'opposition':
            gaps.append({'category': 'risk', 'item': 'Community Opposition',
                        'detail': 'Active community opposition identified', 'priority': 3})
        
        self.gaps = sorted(gaps, key=lambda x: x['priority'])
    
    def _recommend_actions(self):
        """Generate recommended next actions."""
        actions = []
        i = self.inputs
        
        # Based on stage and gaps
        if self.stage == DevelopmentStage.QUEUE_ONLY:
            actions.append({
                'action': 'Secure land control',
                'timeline': '0-60 days',
                'detail': 'Execute option or LOI on suitable acreage'
            })
            actions.append({
                'action': 'Elevate utility relationship',
                'timeline': '0-90 days',
                'detail': 'Request meeting with utility economic development team'
            })
            actions.append({
                'action': 'Initiate interconnection study',
                'timeline': '30-90 days',
                'detail': 'Submit study request to queue'
            })
        
        elif self.stage == DevelopmentStage.EARLY_REAL:
            actions.append({
                'action': 'Advance utility engagement',
                'timeline': '0-60 days',
                'detail': 'Push for utility study approval and preliminary cost estimate'
            })
            actions.append({
                'action': 'Begin end-user outreach',
                'timeline': '0-90 days',
                'detail': 'Identify and contact potential hyperscaler/colo tenants'
            })
            actions.append({
                'action': 'Initiate zoning pre-application',
                'timeline': '30-90 days',
                'detail': 'Meet with planning department, understand requirements'
            })
        
        elif self.stage == DevelopmentStage.STUDY_IN_PROGRESS:
            actions.append({
                'action': 'Negotiate utility commitment',
                'timeline': '0-120 days',
                'detail': 'Work toward commitment letter with service date'
            })
            actions.append({
                'action': 'Submit zoning application',
                'timeline': '0-60 days',
                'detail': 'File formal zoning application with county/city'
            })
            actions.append({
                'action': 'Intensify end-user pursuit',
                'timeline': '0-90 days',
                'detail': 'Schedule site tours, push for NDA and LOI'
            })
            actions.append({
                'action': 'Complete environmental baseline',
                'timeline': '0-90 days',
                'detail': 'Commission Phase 1 environmental study'
            })
        
        elif self.stage == DevelopmentStage.UTILITY_COMMITMENT:
            actions.append({
                'action': 'Close end-user LOI',
                'timeline': '0-90 days',
                'detail': 'Convert NDA discussions to LOI with key terms'
            })
            actions.append({
                'action': 'Complete entitlements',
                'timeline': '0-180 days',
                'detail': 'Secure all zoning, permits, environmental clearances'
            })
            actions.append({
                'action': 'Finalize utility agreements',
                'timeline': '60-180 days',
                'detail': 'Execute interconnection agreement, confirm upgrade timeline'
            })
        
        elif self.stage == DevelopmentStage.FULLY_ENTITLED:
            actions.append({
                'action': 'Convert LOI to term sheet',
                'timeline': '0-90 days',
                'detail': 'Negotiate binding term sheet with end-user'
            })
            actions.append({
                'action': 'Evaluate exit options',
                'timeline': '0-60 days',
                'detail': 'Assess sell vs. build vs. JV structures'
            })
        
        elif self.stage == DevelopmentStage.END_USER_ATTACHED:
            actions.append({
                'action': 'Execute definitive agreements',
                'timeline': '0-120 days',
                'detail': 'Finalize lease, development agreement, construction contracts'
            })
            actions.append({
                'action': 'Close transaction or commence construction',
                'timeline': '90-180 days',
                'detail': 'Either sell to end-user/developer or break ground'
            })
        
        self.next_actions = actions
    
    def get_summary(self) -> Dict:
        """Return complete assessment summary."""
        state_info = STATE_SCORES.get(self.inputs.state, {'tier': 2, 'score': 65, 'name': self.inputs.state})
        
        return {
            'site': {
                'name': self.inputs.site_name,
                'location': f"{self.inputs.nearest_city}, {state_info['name']}",
                'state': self.inputs.state,
                'state_score': state_info['score'],
                'state_tier': state_info['tier'],
                'target_mw': self.inputs.target_mw,
                'max_potential_mw': self.inputs.max_potential_mw,
                'acreage': self.inputs.developable_acreage
            },
            'assessment': {
                'stage': self.stage.value,
                'stage_name': self.stage.value.replace('_', ' ').title(),
                'overall_score': self.scores['overall'],
                'scores': self.scores
            },
            'valuation': self.valuation,
            'gaps': self.gaps,
            'next_actions': self.next_actions,
            'key_risks': self.inputs.key_risks,
            'key_opportunities': self.inputs.key_opportunities,
            'notes': self.inputs.notes
        }


# =============================================================================
# REPORT GENERATOR (JSON for now, DOCX in separate module)
# =============================================================================

def generate_report_json(assessment: Dict) -> str:
    """Generate JSON report."""
    return json.dumps(assessment, indent=2, default=str)


def format_currency(value: int) -> str:
    """Format integer as currency."""
    if value >= 1000000000:
        return f"${value/1000000000:.1f}B"
    elif value >= 1000000:
        return f"${value/1000000:.0f}M"
    elif value >= 1000:
        return f"${value/1000:.0f}K"
    else:
        return f"${value:,.0f}"


def print_assessment(assessment: Dict):
    """Print formatted assessment to console."""
    site = assessment['site']
    a = assessment['assessment']
    v = assessment['valuation']
    
    print("=" * 70)
    print(f"SITE ASSESSMENT: {site['name']}")
    print("=" * 70)
    
    print(f"\nLocation: {site['location']}")
    print(f"State Tier: {site['state_tier']} (Score: {site['state_score']})")
    print(f"Target Capacity: {site['target_mw']} MW ({site['acreage']} acres)")
    
    print(f"\n--- DEVELOPMENT STAGE ---")
    print(f"Current Stage: {a['stage_name']}")
    print(f"Overall Score: {a['overall_score']}/100")
    
    print(f"\n--- INGREDIENT SCORES ---")
    print(f"  Relationship Capital: {a['scores']['relationship_capital']['total']}/100")
    print(f"    - End-User Pipeline: {a['scores']['relationship_capital']['end_user']}")
    print(f"    - Community Support: {a['scores']['relationship_capital']['community']}")
    print(f"  Power Pathway: {a['scores']['power_pathway']['total']}/100")
    print(f"    - Queue Position: {a['scores']['power_pathway']['queue']}")
    print(f"    - Utility Engagement: {a['scores']['power_pathway']['utility']}")
    print(f"    - Transmission: {a['scores']['power_pathway']['transmission']}")
    print(f"  Execution Capability: {a['scores']['execution']['total']}/100")
    print(f"  Site Fundamentals: {a['scores']['site_specific']['total']}/100")
    
    print(f"\n--- VALUATION ESTIMATE ---")
    print(f"Stage: {v['stage_description']}")
    print(f"Factors: Market {v['factors']['market']:.2f}x, Scale {v['factors']['scale']:.2f}x, Quality {v['factors']['quality']:.2f}x")
    print(f"Per MW: {format_currency(v['adjusted_per_mw']['low'])} - {format_currency(v['adjusted_per_mw']['high'])}")
    print(f"Total ({v['target_mw']} MW): {format_currency(v['total_value']['low']*1000000)} - {format_currency(v['total_value']['high']*1000000)}")
    
    print(f"\n--- GAPS TO ADVANCEMENT ---")
    for gap in assessment['gaps'][:5]:
        priority = "🔴" if gap['priority'] == 1 else "🟡" if gap['priority'] == 2 else "🟢"
        print(f"  {priority} {gap['item']}: {gap['detail']}")
    
    print(f"\n--- RECOMMENDED ACTIONS ---")
    for action in assessment['next_actions'][:4]:
        print(f"  → {action['action']} ({action['timeline']})")
        print(f"    {action['detail']}")
    
    print()


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example: Tulsa-area site
    site = SiteInputs(
        site_name="Catoosa Industrial Site",
        state="OK",
        county="Rogers",
        nearest_city="Catoosa",
        
        total_acreage=650,
        developable_acreage=500,
        target_mw=500,
        max_potential_mw=800,
        
        land_controlled=True,
        land_control_type="option",
        option_expiry_date=date(2026, 6, 30),
        option_extensions_available=2,
        
        queue_position=True,
        queue_iso="SPP",
        queue_mw=600,
        queue_date=date(2024, 3, 15),
        study_phase="system_impact",
        study_completion_date=date(2025, 6, 1),
        
        utility_name="PSO",
        utility_contact_level="account_rep",
        utility_study_requested=True,
        utility_study_approved=True,
        utility_commitment_letter=False,
        estimated_service_date=date(2028, 6, 1),
        
        transmission_distance_miles=2.5,
        substation_capacity_mw=200,
        upgrade_required=True,
        upgrade_cost_estimate=25000000,
        
        water_source="municipal",
        water_rights_secured=False,
        water_capacity_mgd=3.0,
        
        fiber_lit=False,
        fiber_providers=["Zayo", "AT&T"],
        fiber_distance_miles=4,
        
        zoning_compatible=True,
        zoning_change_required=False,
        environmental_phase1_complete=True,
        
        end_user_tours=2,
        end_user_nda_signed=1,
        end_user_loi=False,
        
        btm_viable=True,
        btm_sources=["solar", "gas"],
        btm_mw_potential=150,
        
        community_support="supportive",
        political_engagement="supportive",
        
        developer_name="Example Developer",
        developer_track_record="proven",
        developer_utility_relationships="strong",
        developer_capital_access="strong",
        
        key_risks=["Upgrade cost uncertainty", "Water rights timeline"],
        key_opportunities=["Strong state incentives", "Utility relationship", "Multiple end-user interest"]
    )
    
    # Run assessment
    assessor = SiteAssessment(site)
    result = assessor.run_assessment()
    
    # Print results
    print_assessment(result)
    
    # Also print JSON
    print("\n--- JSON OUTPUT ---")
    print(generate_report_json(result))
