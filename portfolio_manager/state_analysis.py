"""
State-Level Analysis Module
============================
Integrates state scoring framework with utility-specific research capabilities.

Framework based on "Right Ingredients" state analysis:
- Regulatory Environment (25%)
- Transmission Capacity (20%)
- Power Cost & Availability (20%)
- Water Availability (15%)
- Business Climate (10%)
- Existing DC Ecosystem (10%)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import date
import json

# =============================================================================
# STATE SCORING FRAMEWORK
# =============================================================================

@dataclass
class StateProfile:
    """Complete state profile with scoring across all dimensions."""
    
    state_code: str
    state_name: str
    
    # Tier classification (1-4, 1 being best)
    tier: int = 3
    
    # Overall score (0-100)
    overall_score: int = 50
    
    # Component scores (0-100)
    regulatory_score: int = 50  # 25% weight
    transmission_score: int = 50  # 20% weight
    power_score: int = 50  # 20% weight
    water_score: int = 50  # 15% weight
    business_score: int = 50  # 10% weight
    ecosystem_score: int = 50  # 10% weight
    
    # Regulatory details
    regulatory_structure: str = ""  # "regulated", "deregulated", "hybrid"
    utility_type: str = ""  # "IOU", "coop", "municipal", "mixed"
    psc_dc_friendly: bool = False
    streamlined_permitting: bool = False
    data_center_incentives: List[str] = field(default_factory=list)
    known_moratoria: List[str] = field(default_factory=list)
    
    # Transmission details
    primary_iso: str = ""  # SPP, ERCOT, PJM, MISO, CAISO, etc.
    secondary_iso: str = ""
    avg_queue_time_months: int = 36
    queue_backlog_gw: float = 0
    major_transmission_projects: List[str] = field(default_factory=list)
    
    # Power details
    avg_industrial_rate: float = 0.0  # $/kWh
    available_capacity_gw: float = 0
    planned_generation_gw: float = 0
    renewable_percentage: float = 0
    nuclear_percentage: float = 0
    
    # Water details
    water_stress_level: str = ""  # "low", "medium", "high", "extreme"
    avg_water_cost: float = 0  # $/1000 gal
    water_rights_complexity: str = ""  # "simple", "moderate", "complex"
    
    # Business climate
    corporate_tax_rate: float = 0
    right_to_work: bool = False
    labor_availability: str = ""  # "strong", "moderate", "limited"
    
    # DC ecosystem
    existing_dc_mw: int = 0
    hyperscaler_presence: List[str] = field(default_factory=list)
    fiber_density: str = ""  # "high", "medium", "low"
    
    # Key considerations
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    threats: List[str] = field(default_factory=list)
    
    notes: str = ""
    last_updated: date = field(default_factory=date.today)


# Pre-built state profiles based on research
STATE_PROFILES: Dict[str, StateProfile] = {
    "OK": StateProfile(
        state_code="OK",
        state_name="Oklahoma",
        tier=1,
        overall_score=88,
        regulatory_score=90,
        transmission_score=85,
        power_score=88,
        water_score=75,
        business_score=92,
        ecosystem_score=70,
        regulatory_structure="regulated",
        utility_type="IOU",
        psc_dc_friendly=True,
        streamlined_permitting=True,
        data_center_incentives=["Sales tax exemption on equipment", "Property tax abatement", "Quality Jobs Program"],
        primary_iso="SPP",
        avg_queue_time_months=30,
        queue_backlog_gw=45,
        avg_industrial_rate=0.055,
        available_capacity_gw=2.5,
        planned_generation_gw=8.0,
        renewable_percentage=42,
        water_stress_level="medium",
        avg_water_cost=2.50,
        water_rights_complexity="moderate",
        corporate_tax_rate=4.0,
        right_to_work=True,
        labor_availability="moderate",
        existing_dc_mw=500,
        hyperscaler_presence=["Google (Pryor)", "Meta (announced)"],
        fiber_density="medium",
        strengths=["Pro-business PSC", "Low power costs", "SPP wholesale market", "Strong wind resources", "Tax incentives"],
        weaknesses=["Limited existing DC ecosystem", "Water constraints in west", "Tornado risk"],
        opportunities=["Major hyperscaler expansion", "Tulsa emerging as hub", "Gas generation flexibility"],
        threats=["Grid congestion in wind corridors", "Water rights competition"]
    ),
    
    "TX": StateProfile(
        state_code="TX",
        state_name="Texas",
        tier=1,
        overall_score=80,
        regulatory_score=75,
        transmission_score=70,
        power_score=85,
        water_score=60,
        business_score=95,
        ecosystem_score=90,
        regulatory_structure="deregulated",
        utility_type="mixed",
        psc_dc_friendly=True,
        streamlined_permitting=True,
        data_center_incentives=["Chapter 313 replacement", "Property tax limitations", "TCEQ expedited permitting"],
        known_moratoria=["Various municipal water moratoria"],
        primary_iso="ERCOT",
        avg_queue_time_months=36,
        queue_backlog_gw=200,
        avg_industrial_rate=0.065,
        available_capacity_gw=5.0,
        planned_generation_gw=15.0,
        renewable_percentage=35,
        water_stress_level="high",
        avg_water_cost=3.50,
        water_rights_complexity="complex",
        corporate_tax_rate=0,
        right_to_work=True,
        labor_availability="strong",
        existing_dc_mw=3000,
        hyperscaler_presence=["Google", "Microsoft", "Meta", "AWS", "Oracle"],
        fiber_density="high",
        strengths=["No state income tax", "Massive existing ecosystem", "ERCOT flexibility", "Strong labor market"],
        weaknesses=["Grid reliability concerns", "Water stress", "Queue backlog", "Summer heat"],
        opportunities=["Continued hyperscaler growth", "West Texas expansion", "Nuclear renaissance"],
        threats=["Grid instability events", "Water availability", "Political risk"]
    ),
    
    "WY": StateProfile(
        state_code="WY",
        state_name="Wyoming",
        tier=1,
        overall_score=82,
        regulatory_score=85,
        transmission_score=75,
        power_score=90,
        water_score=85,
        business_score=88,
        ecosystem_score=45,
        regulatory_structure="regulated",
        utility_type="IOU",
        psc_dc_friendly=True,
        streamlined_permitting=True,
        data_center_incentives=["No corporate income tax", "Sales tax exemptions", "Property tax caps"],
        primary_iso="SPP",
        secondary_iso="WECC",
        avg_queue_time_months=28,
        queue_backlog_gw=25,
        avg_industrial_rate=0.048,
        available_capacity_gw=3.0,
        planned_generation_gw=5.0,
        renewable_percentage=25,
        nuclear_percentage=0,
        water_stress_level="low",
        avg_water_cost=1.80,
        water_rights_complexity="moderate",
        corporate_tax_rate=0,
        right_to_work=True,
        labor_availability="limited",
        existing_dc_mw=200,
        hyperscaler_presence=["Microsoft (Cheyenne)"],
        fiber_density="low",
        strengths=["Lowest power costs", "No corporate tax", "Excellent cooling climate", "Water availability", "Nuclear-friendly"],
        weaknesses=["Limited labor pool", "Remote location", "Limited fiber", "Small ecosystem"],
        opportunities=["SMR deployment", "Microsoft expansion", "Crypto mining conversion"],
        threats=["Labor constraints", "Transmission bottlenecks"]
    ),
    
    "GA": StateProfile(
        state_code="GA",
        state_name="Georgia",
        tier=2,
        overall_score=70,
        regulatory_score=65,
        transmission_score=72,
        power_score=68,
        water_score=75,
        business_score=85,
        ecosystem_score=80,
        regulatory_structure="regulated",
        utility_type="IOU",
        psc_dc_friendly=True,
        streamlined_permitting=False,
        data_center_incentives=["Sales tax exemption", "Job tax credits"],
        primary_iso="SERC",
        avg_queue_time_months=42,
        queue_backlog_gw=60,
        avg_industrial_rate=0.072,
        available_capacity_gw=1.5,
        planned_generation_gw=4.0,
        renewable_percentage=15,
        nuclear_percentage=25,
        water_stress_level="medium",
        avg_water_cost=2.80,
        water_rights_complexity="moderate",
        corporate_tax_rate=5.75,
        right_to_work=True,
        labor_availability="strong",
        existing_dc_mw=1500,
        hyperscaler_presence=["Google", "Microsoft", "Meta", "QTS"],
        fiber_density="high",
        strengths=["Strong existing ecosystem", "Georgia Power partnership", "Atlanta connectivity", "Vogtle nuclear"],
        weaknesses=["Higher power costs", "Queue delays", "Limited new capacity"],
        opportunities=["Vogtle 3&4 online", "Rural expansion", "Southeast hub"],
        threats=["Capacity constraints", "Rate increases"]
    ),
    
    "VA": StateProfile(
        state_code="VA",
        state_name="Virginia",
        tier=3,
        overall_score=58,
        regulatory_score=50,
        transmission_score=45,
        power_score=55,
        water_score=70,
        business_score=75,
        ecosystem_score=95,
        regulatory_structure="hybrid",
        utility_type="IOU",
        psc_dc_friendly=False,
        streamlined_permitting=False,
        data_center_incentives=["Sales tax exemption (with conditions)"],
        known_moratoria=["Loudoun County capacity concerns", "Prince William constraints"],
        primary_iso="PJM",
        avg_queue_time_months=48,
        queue_backlog_gw=80,
        avg_industrial_rate=0.078,
        available_capacity_gw=0.5,
        planned_generation_gw=2.0,
        renewable_percentage=12,
        water_stress_level="medium",
        avg_water_cost=3.20,
        water_rights_complexity="moderate",
        corporate_tax_rate=6.0,
        right_to_work=True,
        labor_availability="strong",
        existing_dc_mw=4000,
        hyperscaler_presence=["AWS", "Microsoft", "Google", "Meta", "All major colos"],
        fiber_density="high",
        strengths=["World's largest DC cluster", "Fiber connectivity", "Skilled workforce", "Proximity to DC"],
        weaknesses=["Grid constraints", "Community opposition", "High costs", "Long queues"],
        opportunities=["Southern Virginia expansion", "Offshore wind"],
        threats=["Moratorium risk", "Rate cases", "Political opposition", "Dominion capacity"]
    ),
    
    "OH": StateProfile(
        state_code="OH",
        state_name="Ohio",
        tier=2,
        overall_score=70,
        regulatory_score=72,
        transmission_score=75,
        power_score=70,
        water_score=85,
        business_score=70,
        ecosystem_score=65,
        regulatory_structure="deregulated",
        utility_type="mixed",
        psc_dc_friendly=True,
        streamlined_permitting=True,
        data_center_incentives=["Data Center Tax Exemption", "Job Creation Tax Credit", "Property tax abatement"],
        primary_iso="PJM",
        avg_queue_time_months=36,
        queue_backlog_gw=55,
        avg_industrial_rate=0.068,
        available_capacity_gw=2.0,
        planned_generation_gw=6.0,
        renewable_percentage=8,
        nuclear_percentage=15,
        water_stress_level="low",
        avg_water_cost=2.20,
        water_rights_complexity="simple",
        corporate_tax_rate=0,
        right_to_work=False,
        labor_availability="strong",
        existing_dc_mw=800,
        hyperscaler_presence=["Google", "Meta", "AWS"],
        fiber_density="high",
        strengths=["PJM market access", "Great Lakes water", "Strong grid", "No corporate income tax", "Central location"],
        weaknesses=["Not right-to-work", "Political uncertainty", "Legacy infrastructure"],
        opportunities=["Columbus tech growth", "Intel fab synergy", "Nuclear baseload"],
        threats=["Regulatory changes", "Competition from neighbors"]
    ),
    
    "IN": StateProfile(
        state_code="IN",
        state_name="Indiana",
        tier=2,
        overall_score=72,
        regulatory_score=75,
        transmission_score=70,
        power_score=75,
        water_score=80,
        business_score=82,
        ecosystem_score=55,
        regulatory_structure="regulated",
        utility_type="IOU",
        psc_dc_friendly=True,
        streamlined_permitting=True,
        data_center_incentives=["EDGE Tax Credit", "Property tax abatement", "Training grants"],
        primary_iso="MISO",
        secondary_iso="PJM",
        avg_queue_time_months=32,
        queue_backlog_gw=40,
        avg_industrial_rate=0.062,
        available_capacity_gw=2.5,
        planned_generation_gw=5.0,
        renewable_percentage=12,
        water_stress_level="low",
        avg_water_cost=2.00,
        water_rights_complexity="simple",
        corporate_tax_rate=4.9,
        right_to_work=True,
        labor_availability="moderate",
        existing_dc_mw=400,
        hyperscaler_presence=["Microsoft", "Google (planned)"],
        fiber_density="medium",
        strengths=["Pro-business environment", "MISO/PJM flexibility", "Water abundance", "Central location", "Lower costs"],
        weaknesses=["Smaller ecosystem", "Limited fiber in rural areas"],
        opportunities=["Indianapolis growth", "EV/battery manufacturing synergy"],
        threats=["Coal plant retirements", "Capacity timing"]
    ),
    
    "PA": StateProfile(
        state_code="PA",
        state_name="Pennsylvania",
        tier=2,
        overall_score=68,
        regulatory_score=65,
        transmission_score=70,
        power_score=65,
        water_score=85,
        business_score=60,
        ecosystem_score=70,
        regulatory_structure="deregulated",
        utility_type="mixed",
        psc_dc_friendly=True,
        streamlined_permitting=False,
        data_center_incentives=["Keystone Opportunity Zones", "Job creation tax credits"],
        primary_iso="PJM",
        avg_queue_time_months=40,
        queue_backlog_gw=65,
        avg_industrial_rate=0.075,
        available_capacity_gw=1.5,
        planned_generation_gw=4.0,
        renewable_percentage=10,
        nuclear_percentage=35,
        water_stress_level="low",
        avg_water_cost=2.50,
        water_rights_complexity="moderate",
        corporate_tax_rate=8.99,
        right_to_work=False,
        labor_availability="strong",
        existing_dc_mw=600,
        hyperscaler_presence=["Microsoft", "Google", "Meta"],
        fiber_density="high",
        strengths=["Strong nuclear fleet", "PJM market", "Water abundance", "Northeast connectivity"],
        weaknesses=["High corporate tax", "Not right-to-work", "Permitting complexity"],
        opportunities=["Nuclear synergy", "Pittsburgh tech growth"],
        threats=["Tax environment", "Regulatory burden"]
    ),
    
    "NV": StateProfile(
        state_code="NV",
        state_name="Nevada",
        tier=3,
        overall_score=55,
        regulatory_score=60,
        transmission_score=50,
        power_score=55,
        water_score=30,
        business_score=85,
        ecosystem_score=75,
        regulatory_structure="deregulated",
        utility_type="IOU",
        psc_dc_friendly=True,
        streamlined_permitting=True,
        data_center_incentives=["Sales tax abatement", "Property tax abatement", "Modified business tax abatement"],
        primary_iso="WECC",
        avg_queue_time_months=36,
        queue_backlog_gw=30,
        avg_industrial_rate=0.072,
        available_capacity_gw=1.0,
        planned_generation_gw=3.0,
        renewable_percentage=30,
        water_stress_level="extreme",
        avg_water_cost=4.50,
        water_rights_complexity="complex",
        corporate_tax_rate=0,
        right_to_work=True,
        labor_availability="moderate",
        existing_dc_mw=800,
        hyperscaler_presence=["Google", "Apple", "Switch"],
        fiber_density="medium",
        strengths=["No corporate tax", "Strong incentives", "Reno ecosystem", "Solar resources"],
        weaknesses=["Extreme water stress", "Grid constraints", "Limited capacity"],
        opportunities=["Solar + storage", "Reno expansion"],
        threats=["Water availability", "Colorado River crisis"]
    ),
    
    "CA": StateProfile(
        state_code="CA",
        state_name="California",
        tier=4,
        overall_score=25,
        regulatory_score=15,
        transmission_score=30,
        power_score=20,
        water_score=25,
        business_score=30,
        ecosystem_score=85,
        regulatory_structure="deregulated",
        utility_type="mixed",
        psc_dc_friendly=False,
        streamlined_permitting=False,
        data_center_incentives=[],
        known_moratoria=["Various local moratoria", "CEQA challenges"],
        primary_iso="CAISO",
        avg_queue_time_months=60,
        queue_backlog_gw=150,
        avg_industrial_rate=0.18,
        available_capacity_gw=0.5,
        planned_generation_gw=2.0,
        renewable_percentage=45,
        water_stress_level="extreme",
        avg_water_cost=6.00,
        water_rights_complexity="complex",
        corporate_tax_rate=8.84,
        right_to_work=False,
        labor_availability="strong",
        existing_dc_mw=2500,
        hyperscaler_presence=["Google", "Apple", "Meta", "All majors (HQ)"],
        fiber_density="high",
        strengths=["Tech ecosystem proximity", "Fiber density", "Skilled workforce"],
        weaknesses=["Highest costs", "Regulatory burden", "Water crisis", "Grid constraints", "CEQA"],
        opportunities=["Very limited"],
        threats=["Continued exodus", "Grid reliability", "Wildfire risk"]
    ),
}


def get_state_profile(state_code: str) -> Optional[StateProfile]:
    """Get state profile by code."""
    return STATE_PROFILES.get(state_code.upper())


def calculate_state_score(profile: StateProfile) -> Dict:
    """Calculate weighted state score with component breakdown."""
    weights = {
        'regulatory': 0.25,
        'transmission': 0.20,
        'power': 0.20,
        'water': 0.15,
        'business': 0.10,
        'ecosystem': 0.10
    }
    
    weighted_score = (
        profile.regulatory_score * weights['regulatory'] +
        profile.transmission_score * weights['transmission'] +
        profile.power_score * weights['power'] +
        profile.water_score * weights['water'] +
        profile.business_score * weights['business'] +
        profile.ecosystem_score * weights['ecosystem']
    )
    
    return {
        'overall_score': round(weighted_score, 1),
        'tier': profile.tier,
        'components': {
            'regulatory': {'score': profile.regulatory_score, 'weight': weights['regulatory']},
            'transmission': {'score': profile.transmission_score, 'weight': weights['transmission']},
            'power': {'score': profile.power_score, 'weight': weights['power']},
            'water': {'score': profile.water_score, 'weight': weights['water']},
            'business': {'score': profile.business_score, 'weight': weights['business']},
            'ecosystem': {'score': profile.ecosystem_score, 'weight': weights['ecosystem']}
        }
    }


def compare_states(state_codes: List[str]) -> List[Dict]:
    """Compare multiple states side-by-side."""
    comparisons = []
    
    for code in state_codes:
        profile = get_state_profile(code)
        if profile:
            score_data = calculate_state_score(profile)
            comparisons.append({
                'state': code,
                'name': profile.state_name,
                'tier': profile.tier,
                'overall_score': score_data['overall_score'],
                'regulatory': profile.regulatory_score,
                'transmission': profile.transmission_score,
                'power': profile.power_score,
                'water': profile.water_score,
                'business': profile.business_score,
                'ecosystem': profile.ecosystem_score,
                'primary_iso': profile.primary_iso,
                'avg_queue_months': profile.avg_queue_time_months,
                'industrial_rate': profile.avg_industrial_rate,
                'strengths': profile.strengths[:3],
                'weaknesses': profile.weaknesses[:3]
            })
    
    # Sort by overall score descending
    comparisons.sort(key=lambda x: x['overall_score'], reverse=True)
    
    return comparisons


def get_tier_states(tier: int) -> List[str]:
    """Get all states in a specific tier."""
    return [code for code, profile in STATE_PROFILES.items() if profile.tier == tier]


# =============================================================================
# UTILITY RESEARCH QUERIES
# =============================================================================

def generate_utility_research_queries(utility_name: str, state: str) -> Dict[str, List[str]]:
    """
    Generate research queries for utility-specific information.
    These can be used with web search to gather current data.
    """
    
    queries = {
        'queue_and_interconnection': [
            f'"{utility_name}" interconnection queue data center',
            f'"{utility_name}" generator interconnection study timeline',
            f'"{utility_name}" large load interconnection process',
            f'{state} {utility_name} interconnection queue backlog',
        ],
        'capacity_and_generation': [
            f'"{utility_name}" integrated resource plan IRP {date.today().year}',
            f'"{utility_name}" new generation capacity announcement',
            f'"{utility_name}" RFP generation capacity',
            f'"{utility_name}" power plant construction',
            f'"{utility_name}" data center load growth',
        ],
        'rate_cases': [
            f'"{utility_name}" rate case {date.today().year}',
            f'"{utility_name}" industrial rate schedule',
            f'"{utility_name}" large power service tariff',
            f'{state} PSC {utility_name} rate filing',
        ],
        'data_center_specific': [
            f'"{utility_name}" data center customer',
            f'"{utility_name}" data center partnership',
            f'"{utility_name}" hyperscaler agreement',
            f'{state} data center utility agreement',
        ],
        'transmission_projects': [
            f'"{utility_name}" transmission expansion',
            f'"{utility_name}" substation construction',
            f'{state} transmission line project {date.today().year}',
        ],
        'regulatory_filings': [
            f'site:{state.lower()}.gov {utility_name} docket',
            f'{state} PSC {utility_name} filing',
            f'{state} corporation commission {utility_name}',
        ]
    }
    
    return queries


def get_iso_research_queries(iso: str) -> Dict[str, List[str]]:
    """Generate research queries for ISO/RTO specific information."""
    
    iso_urls = {
        'SPP': 'spp.org',
        'ERCOT': 'ercot.com',
        'PJM': 'pjm.com',
        'MISO': 'misoenergy.org',
        'CAISO': 'caiso.com',
        'WECC': 'wecc.org',
        'SERC': 'serc1.org',
        'NYISO': 'nyiso.com',
        'ISO-NE': 'iso-ne.com'
    }
    
    base_url = iso_urls.get(iso, '')
    
    queries = {
        'queue_status': [
            f'site:{base_url} interconnection queue',
            f'{iso} generator interconnection queue report {date.today().year}',
            f'{iso} interconnection study timeline',
            f'{iso} queue reform',
        ],
        'capacity_outlook': [
            f'{iso} resource adequacy report',
            f'{iso} capacity forecast {date.today().year}',
            f'{iso} load growth projection',
            f'{iso} data center load study',
        ],
        'transmission_planning': [
            f'{iso} transmission expansion plan',
            f'{iso} transmission planning report',
            f'{iso} grid upgrade project',
        ],
        'market_data': [
            f'{iso} wholesale power price',
            f'{iso} locational marginal pricing',
            f'{iso} congestion report',
        ]
    }
    
    return queries


# =============================================================================
# STATE CONTEXT FOR SITE REPORTS
# =============================================================================

def generate_state_context_section(state_code: str) -> Dict:
    """Generate state context section for site diagnostic reports."""
    
    profile = get_state_profile(state_code)
    if not profile:
        return {'error': f'No profile found for {state_code}'}
    
    score_data = calculate_state_score(profile)
    
    context = {
        'summary': {
            'state': profile.state_name,
            'tier': profile.tier,
            'tier_label': ['', 'Tier 1 - Optimal', 'Tier 2 - Strong', 'Tier 3 - Moderate', 'Tier 4 - Challenging'][profile.tier],
            'overall_score': score_data['overall_score'],
            'primary_iso': profile.primary_iso,
            'regulatory_structure': profile.regulatory_structure,
        },
        'scores': {
            'regulatory': {'score': profile.regulatory_score, 'label': 'Regulatory Environment', 'weight': '25%'},
            'transmission': {'score': profile.transmission_score, 'label': 'Transmission Capacity', 'weight': '20%'},
            'power': {'score': profile.power_score, 'label': 'Power Cost & Availability', 'weight': '20%'},
            'water': {'score': profile.water_score, 'label': 'Water Availability', 'weight': '15%'},
            'business': {'score': profile.business_score, 'label': 'Business Climate', 'weight': '10%'},
            'ecosystem': {'score': profile.ecosystem_score, 'label': 'DC Ecosystem', 'weight': '10%'},
        },
        'key_metrics': {
            'avg_industrial_rate': f"${profile.avg_industrial_rate:.3f}/kWh",
            'avg_queue_time': f"{profile.avg_queue_time_months} months",
            'queue_backlog': f"{profile.queue_backlog_gw} GW",
            'water_stress': profile.water_stress_level,
            'corporate_tax': f"{profile.corporate_tax_rate}%",
        },
        'regulatory_details': {
            'structure': profile.regulatory_structure,
            'utility_type': profile.utility_type,
            'psc_dc_friendly': profile.psc_dc_friendly,
            'streamlined_permitting': profile.streamlined_permitting,
            'incentives': profile.data_center_incentives,
            'moratoria': profile.known_moratoria,
        },
        'infrastructure': {
            'primary_iso': profile.primary_iso,
            'secondary_iso': profile.secondary_iso,
            'available_capacity_gw': profile.available_capacity_gw,
            'planned_generation_gw': profile.planned_generation_gw,
            'renewable_pct': profile.renewable_percentage,
            'nuclear_pct': profile.nuclear_percentage,
        },
        'swot': {
            'strengths': profile.strengths,
            'weaknesses': profile.weaknesses,
            'opportunities': profile.opportunities,
            'threats': profile.threats,
        },
        'existing_ecosystem': {
            'existing_dc_mw': profile.existing_dc_mw,
            'hyperscalers': profile.hyperscaler_presence,
            'fiber_density': profile.fiber_density,
        },
        'research_needed': generate_utility_research_queries('', state_code)
    }
    
    return context


# =============================================================================
# NATIONAL RANKING
# =============================================================================

def rank_all_states() -> List[Dict]:
    """Rank all states by overall score."""
    rankings = []
    
    for code, profile in STATE_PROFILES.items():
        score_data = calculate_state_score(profile)
        rankings.append({
            'rank': 0,  # Will be set after sorting
            'state': code,
            'name': profile.state_name,
            'tier': profile.tier,
            'overall_score': score_data['overall_score'],
            'regulatory': profile.regulatory_score,
            'transmission': profile.transmission_score,
            'power': profile.power_score,
            'water': profile.water_score,
            'business': profile.business_score,
            'ecosystem': profile.ecosystem_score,
            'iso': profile.primary_iso,
            'industrial_rate': profile.avg_industrial_rate,
            'queue_months': profile.avg_queue_time_months,
        })
    
    # Sort by overall score
    rankings.sort(key=lambda x: x['overall_score'], reverse=True)
    
    # Assign ranks
    for i, state in enumerate(rankings):
        state['rank'] = i + 1
    
    return rankings


if __name__ == "__main__":
    # Demo
    print("=" * 70)
    print("STATE ANALYSIS MODULE")
    print("=" * 70)
    
    # Show all state rankings
    print("\nNATIONAL STATE RANKINGS")
    print("-" * 70)
    print(f"{'Rank':<5} {'State':<6} {'Name':<15} {'Tier':<6} {'Score':<8} {'ISO':<8} {'Rate':<8}")
    print("-" * 70)
    
    rankings = rank_all_states()
    for state in rankings:
        print(f"{state['rank']:<5} {state['state']:<6} {state['name']:<15} {state['tier']:<6} {state['overall_score']:<8.1f} {state['iso']:<8} ${state['industrial_rate']:.3f}")
    
    # Show Oklahoma context
    print("\n" + "=" * 70)
    print("OKLAHOMA STATE CONTEXT")
    print("=" * 70)
    
    ok_context = generate_state_context_section("OK")
    print(f"\nTier: {ok_context['summary']['tier_label']}")
    print(f"Overall Score: {ok_context['summary']['overall_score']}")
    print(f"Primary ISO: {ok_context['summary']['primary_iso']}")
    
    print("\nComponent Scores:")
    for key, data in ok_context['scores'].items():
        print(f"  {data['label']}: {data['score']} ({data['weight']})")
    
    print("\nStrengths:")
    for s in ok_context['swot']['strengths']:
        print(f"  + {s}")
    
    print("\nWeaknesses:")
    for w in ok_context['swot']['weaknesses']:
        print(f"  - {w}")
