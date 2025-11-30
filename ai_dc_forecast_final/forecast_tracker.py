"""
AI Data Center Power Forecast Tracking
======================================
Baseline tracking and delta calculation for supply/demand forecasting.
Aligned with presentation methodology (scenarios, not regression).

Version: 2.0 (Corrected)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime
import json

# =============================================================================
# ENUMS
# =============================================================================

class DemandScenario(Enum):
    ACCELERATION = "scenario_a"  # Business case continues
    PLATEAU = "scenario_b"       # Business case fails to materialize

class SupplyScenario(Enum):
    LOW = "low"       # Utility delivery slippage, minimal GETs/SMR
    MEDIUM = "medium" # Moderate reform impact
    HIGH = "high"     # Aggressive reforms + GETs + SMR

class StateTier(Enum):
    TIER_1 = "tier_1"  # 75-100
    TIER_2 = "tier_2"  # 60-74
    TIER_3 = "tier_3"  # 50-64
    AVOID = "avoid"    # <50

# =============================================================================
# BASELINE DATA (From Presentation)
# =============================================================================

BASELINE_SNAPSHOT_DATE = "2025-11-01"

# Demand scenarios (US Tech Stack GW)
DEMAND_SCENARIOS = {
    DemandScenario.ACCELERATION: {
        'description': 'AI business case continues to scale',
        'trajectory': {2024: 12, 2025: 25, 2026: 38, 2027: 50, 2028: 70, 
                      2029: 90, 2030: 115, 2035: 230},
        'triggers': [
            'Reasoning inference drives exponential compute',
            'Model sizes continue 10x/2yr scaling',
            'Enterprise adoption reaches majority workflows',
            'Autonomous systems scale'
        ]
    },
    DemandScenario.PLATEAU: {
        'description': 'AI business case fails to materialize',
        'trajectory': {2024: 12, 2025: 20, 2026: 28, 2027: 35, 2028: 50,
                      2029: 65, 2030: 85, 2035: 95},
        'triggers': [
            'Efficiency gains outpace demand',
            'ROI skepticism reduces investment',
            'Model scaling hits diminishing returns',
            'Regulatory constraints limit deployment'
        ]
    }
}

# Supply scenarios (US deliverable GW)
SUPPLY_SCENARIOS = {
    SupplyScenario.LOW: {
        'description': 'Utility delivery slippage, minimal GETs/SMR',
        'trajectory': {2024: 10, 2025: 15, 2026: 20, 2027: 25, 2028: 32,
                      2029: 40, 2030: 50, 2035: 140}
    },
    SupplyScenario.MEDIUM: {
        'description': 'Moderate reform impact, some GETs adoption',
        'trajectory': {2024: 10, 2025: 18, 2026: 26, 2027: 35, 2028: 48,
                      2029: 62, 2030: 75, 2035: 257}
    },
    SupplyScenario.HIGH: {
        'description': 'Aggressive reforms + GETs + SMR deployment',
        'trajectory': {2024: 10, 2025: 20, 2026: 32, 2027: 45, 2028: 62,
                      2029: 80, 2030: 100, 2035: 418}
    }
}

# Gap matrix (from slide 29) - GW deficit (negative = shortfall)
GAP_MATRIX = {
    (SupplyScenario.LOW, DemandScenario.ACCELERATION): {
        'gaps': {2027: -25, 2030: -65, 2035: -90},
        'probability': 0.40,
        'label': 'MOST LIKELY - Persistent severe deficit'
    },
    (SupplyScenario.LOW, DemandScenario.PLATEAU): {
        'gaps': {2027: -10, 2030: -35, 2035: +45},
        'probability': 0.20,
        'label': 'Tight then surplus'
    },
    (SupplyScenario.MEDIUM, DemandScenario.ACCELERATION): {
        'gaps': {2027: -15, 2030: -40, 2035: +27},
        'probability': 0.25,
        'label': 'Requires GETs/SMR success'
    },
    (SupplyScenario.MEDIUM, DemandScenario.PLATEAU): {
        'gaps': {2027: 0, 2030: -10, 2035: +162},
        'probability': 0.10,
        'label': 'Balanced then surplus'
    },
    (SupplyScenario.HIGH, DemandScenario.ACCELERATION): {
        'gaps': {2027: -5, 2030: -15, 2035: +188},
        'probability': 0.04,
        'label': 'Achievable if aggressive'
    },
    (SupplyScenario.HIGH, DemandScenario.PLATEAU): {
        'gaps': {2027: +10, 2030: +15, 2035: +323},
        'probability': 0.01,
        'label': 'Major surplus'
    }
}

# CoWoS baseline (binding constraint through 2027)
COWOS_BASELINE = {
    2024: 35000,   # wafers per month
    2025: 60000,
    2026: 80000,
    2027: 100000
}

# Hyperscaler capex baseline (quarterly, $B)
HYPERSCALER_CAPEX_BASELINE = 55  # Combined MSFT/GOOG/AMZN/META

# Queue baselines (GW in queue)
QUEUE_BASELINE = {
    'pjm': {'queue_gw': 90, 'completion_rate': 0.19},
    'ercot': {'queue_gw': 100, 'completion_rate': 0.25},
    'spp': {'queue_gw': 25, 'completion_rate': 0.35},
    'miso': {'queue_gw': 45, 'completion_rate': 0.22},
    'wecc': {'queue_gw': 60, 'completion_rate': 0.15},
    'serc': {'queue_gw': 35, 'completion_rate': 0.28}
}

# State scoring weights (from slide 34 - THESE ARE EXACT)
STATE_DIMENSION_WEIGHTS = {
    'queue_efficiency': 0.25,
    'permitting_speed': 0.20,
    'btm_flexibility': 0.15,
    'transmission_headroom': 0.15,
    'resource_access': 0.10,
    'saturation_competition': 0.10,
    'cost_structure': 0.05
}

# State baseline scores (from tier slides)
STATE_SCORES_BASELINE = {
    # Tier 1
    'oklahoma': {'total': 88, 'queue': 85, 'permitting': 90, 'btm': 85,
                 'transmission': 80, 'resources': 95, 'saturation': 90},
    'wyoming': {'total': 82, 'queue': 80, 'permitting': 95, 'btm': 90,
                'transmission': 70, 'resources': 90, 'saturation': 95},
    'texas_secondary': {'total': 80, 'queue': 75, 'permitting': 95, 'btm': 95,
                       'transmission': 65, 'resources': 85, 'saturation': 60},
    # Tier 2
    'west_virginia': {'total': 76, 'queue': 65, 'permitting': 85, 'btm': 70,
                     'transmission': 75, 'resources': 80, 'saturation': 90},
    'indiana': {'total': 72, 'queue': 60, 'permitting': 75, 'btm': 65,
               'transmission': 70, 'resources': 75, 'saturation': 80},
    'arkansas': {'total': 71, 'queue': 75, 'permitting': 80, 'btm': 70,
                'transmission': 65, 'resources': 75, 'saturation': 85},
    'ohio': {'total': 70, 'queue': 55, 'permitting': 70, 'btm': 60,
            'transmission': 65, 'resources': 80, 'saturation': 75},
    'georgia': {'total': 70, 'queue': 65, 'permitting': 70, 'btm': 55,
               'transmission': 60, 'resources': 70, 'saturation': 65},
    'louisiana': {'total': 68, 'queue': 65, 'permitting': 75, 'btm': 75,
                 'transmission': 60, 'resources': 85, 'saturation': 85},
    'pennsylvania_west': {'total': 68, 'queue': 55, 'permitting': 65, 'btm': 60,
                         'transmission': 65, 'resources': 80, 'saturation': 75},
    'mississippi': {'total': 64, 'queue': 60, 'permitting': 75, 'btm': 65,
                   'transmission': 55, 'resources': 70, 'saturation': 90},
    # Tier 3
    'new_mexico': {'total': 67, 'queue': 70, 'permitting': 75, 'btm': 80,
                  'transmission': 60, 'resources': 85, 'saturation': 85},
    'montana': {'total': 62, 'queue': 75, 'permitting': 80, 'btm': 75,
               'transmission': 50, 'resources': 70, 'saturation': 90},
    'virginia_secondary': {'total': 58, 'queue': 35, 'permitting': 65, 'btm': 50,
                          'transmission': 30, 'resources': 65, 'saturation': 20},
    'nevada': {'total': 55, 'queue': 60, 'permitting': 65, 'btm': 65,
              'transmission': 50, 'resources': 60, 'saturation': 65},
    'arizona': {'total': 52, 'queue': 55, 'permitting': 60, 'btm': 60,
               'transmission': 45, 'resources': 65, 'saturation': 60},
    # Avoid
    'new_york': {'total': 40},
    'new_england': {'total': 35},
    'virginia_nova': {'total': 30},
    'california': {'total': 25}
}

# =============================================================================
# TRACKING CLASSES
# =============================================================================

@dataclass
class Signal:
    """A tracked signal that may affect forecasts."""
    timestamp: str
    category: str  # 'demand', 'supply', 'state'
    signal_type: str
    source: str
    data: Dict
    analysis: Optional[Dict] = None


@dataclass
class ForecastState:
    """Current state of the forecast model."""
    snapshot_date: str
    demand_scenario_probabilities: Dict[DemandScenario, float]
    supply_scenario: SupplyScenario
    state_scores: Dict[str, Dict]
    signals_processed: List[Signal] = field(default_factory=list)
    
    @classmethod
    def create_baseline(cls) -> 'ForecastState':
        """Create baseline forecast state."""
        return cls(
            snapshot_date=BASELINE_SNAPSHOT_DATE,
            demand_scenario_probabilities={
                DemandScenario.ACCELERATION: 0.60,  # Weighted toward acceleration
                DemandScenario.PLATEAU: 0.40
            },
            supply_scenario=SupplyScenario.LOW,  # Most conservative
            state_scores=STATE_SCORES_BASELINE.copy()
        )


class ForecastTracker:
    """
    Tracks forecast state and processes signals.
    """
    
    def __init__(self, initial_state: Optional[ForecastState] = None):
        self.state = initial_state or ForecastState.create_baseline()
        self.signal_log: List[Signal] = []
    
    def get_demand_forecast(self, year: int) -> Dict:
        """Get probability-weighted demand forecast for year."""
        forecasts = {}
        weighted = 0
        
        for scenario, prob in self.state.demand_scenario_probabilities.items():
            trajectory = DEMAND_SCENARIOS[scenario]['trajectory']
            value = trajectory.get(year, 0)
            forecasts[scenario.value] = value
            weighted += value * prob
        
        return {
            'year': year,
            'weighted_gw': round(weighted, 1),
            'scenario_forecasts': forecasts,
            'probabilities': {s.value: p for s, p in 
                            self.state.demand_scenario_probabilities.items()}
        }
    
    def get_supply_forecast(self, year: int) -> Dict:
        """Get supply forecast for year under current scenario."""
        trajectory = SUPPLY_SCENARIOS[self.state.supply_scenario]['trajectory']
        value = trajectory.get(year, 0)
        
        return {
            'year': year,
            'supply_gw': value,
            'scenario': self.state.supply_scenario.value,
            'description': SUPPLY_SCENARIOS[self.state.supply_scenario]['description']
        }
    
    def get_gap_forecast(self, year: int) -> Dict:
        """Get supply-demand gap forecast."""
        demand = self.get_demand_forecast(year)
        supply = self.get_supply_forecast(year)
        
        # Get from gap matrix for most likely combination
        gap_key = (self.state.supply_scenario, 
                   max(self.state.demand_scenario_probabilities,
                       key=self.state.demand_scenario_probabilities.get))
        
        matrix_entry = GAP_MATRIX.get(gap_key, {})
        matrix_gap = matrix_entry.get('gaps', {}).get(year)
        
        # Also calculate directly
        calculated_gap = supply['supply_gw'] - demand['weighted_gw']
        
        return {
            'year': year,
            'demand_gw': demand['weighted_gw'],
            'supply_gw': supply['supply_gw'],
            'gap_gw': round(calculated_gap, 1),
            'matrix_gap_gw': matrix_gap,
            'scenario_combo': f"{self.state.supply_scenario.value} × {gap_key[1].value}",
            'status': 'deficit' if calculated_gap < 0 else 'surplus'
        }
    
    def process_cowos_signal(self, year: int, new_capacity_wpm: int, source: str) -> Dict:
        """Process CoWoS capacity update signal."""
        baseline = COWOS_BASELINE.get(year, 0)
        if baseline == 0:
            return {'error': f'No baseline for year {year}'}
        
        pct_change = (new_capacity_wpm - baseline) / baseline
        
        signal = Signal(
            timestamp=datetime.now().isoformat(),
            category='demand',
            signal_type='cowos_capacity',
            source=source,
            data={'year': year, 'new_capacity': new_capacity_wpm, 'baseline': baseline}
        )
        
        # Determine recommendation
        if pct_change > 0.15:
            recommendation = 'INCREASE Scenario A probability (+5-10%)'
            adjustment = 0.05
        elif pct_change < -0.15:
            recommendation = 'DECREASE Scenario A probability (-5-10%)'
            adjustment = -0.05
        else:
            recommendation = 'No material change to scenario probabilities'
            adjustment = 0
        
        signal.analysis = {
            'pct_change': round(pct_change * 100, 1),
            'recommendation': recommendation,
            'suggested_adjustment': adjustment
        }
        
        self.signal_log.append(signal)
        
        return {
            'signal': f"CoWoS {year}: {new_capacity_wpm:,} WPM (baseline: {baseline:,})",
            'pct_change': f"{pct_change*100:+.1f}%",
            'recommendation': recommendation,
            'applied': False  # User must confirm
        }
    
    def process_capex_signal(self, quarterly_capex_bn: float, source: str) -> Dict:
        """Process hyperscaler capex signal."""
        pct_change = (quarterly_capex_bn - HYPERSCALER_CAPEX_BASELINE) / HYPERSCALER_CAPEX_BASELINE
        
        signal = Signal(
            timestamp=datetime.now().isoformat(),
            category='demand',
            signal_type='hyperscaler_capex',
            source=source,
            data={'quarterly_capex_bn': quarterly_capex_bn, 
                  'baseline': HYPERSCALER_CAPEX_BASELINE}
        )
        
        if pct_change > 0.20:
            recommendation = 'Strong signal for Scenario A - consider +10% probability'
        elif pct_change > 0.10:
            recommendation = 'Moderate signal for Scenario A - consider +5% probability'
        elif pct_change < -0.20:
            recommendation = 'Strong signal for Scenario B - consider -10% probability'
        elif pct_change < -0.10:
            recommendation = 'Moderate signal for Scenario B - consider -5% probability'
        else:
            recommendation = 'Within normal variance - no adjustment'
        
        signal.analysis = {'pct_change': round(pct_change * 100, 1), 
                          'recommendation': recommendation}
        self.signal_log.append(signal)
        
        return {
            'signal': f"Hyperscaler capex: ${quarterly_capex_bn}B (baseline: ${HYPERSCALER_CAPEX_BASELINE}B)",
            'pct_change': f"{pct_change*100:+.1f}%",
            'recommendation': recommendation
        }
    
    def process_queue_signal(self, iso: str, new_queue_gw: float, 
                            new_completion_rate: Optional[float], source: str) -> Dict:
        """Process interconnection queue update signal."""
        baseline = QUEUE_BASELINE.get(iso.lower())
        if not baseline:
            return {'error': f'No baseline for ISO: {iso}'}
        
        queue_change = new_queue_gw - baseline['queue_gw']
        
        signal = Signal(
            timestamp=datetime.now().isoformat(),
            category='supply',
            signal_type='queue_update',
            source=source,
            data={'iso': iso, 'new_queue_gw': new_queue_gw, 
                  'baseline_queue_gw': baseline['queue_gw'],
                  'new_completion_rate': new_completion_rate}
        )
        
        recommendations = []
        
        # Queue size assessment
        if queue_change > 10:
            recommendations.append(f"Queue growth +{queue_change:.0f} GW - pressure on timelines")
        elif queue_change < -10:
            recommendations.append(f"Queue reduction {queue_change:.0f} GW - possible improvement")
        
        # Completion rate assessment
        if new_completion_rate:
            rate_change = new_completion_rate - baseline['completion_rate']
            if rate_change > 0.05:
                recommendations.append(f"Completion rate improved +{rate_change*100:.0f}% - supply positive")
            elif rate_change < -0.05:
                recommendations.append(f"Completion rate declined {rate_change*100:.0f}% - supply negative")
        
        signal.analysis = {'queue_change': queue_change, 'recommendations': recommendations}
        self.signal_log.append(signal)
        
        return {
            'signal': f"{iso.upper()} queue: {new_queue_gw} GW (baseline: {baseline['queue_gw']} GW)",
            'queue_change_gw': queue_change,
            'recommendations': recommendations or ['No material change']
        }
    
    def process_state_signal(self, state: str, dimension: str, 
                            score_change: int, description: str, source: str) -> Dict:
        """Process state-level signal that affects scoring."""
        if state not in self.state.state_scores:
            return {'error': f'Unknown state: {state}'}
        
        # Map dimension to weight key
        dimension_map = {
            'queue': 'queue_efficiency',
            'permitting': 'permitting_speed',
            'btm': 'btm_flexibility',
            'transmission': 'transmission_headroom',
            'resources': 'resource_access',
            'saturation': 'saturation_competition',
            'cost': 'cost_structure'
        }
        
        weight_key = dimension_map.get(dimension)
        if not weight_key:
            return {'error': f'Unknown dimension: {dimension}'}
        
        weight = STATE_DIMENSION_WEIGHTS[weight_key]
        weighted_impact = score_change * weight
        
        current_scores = self.state.state_scores[state]
        old_total = current_scores.get('total', 0)
        new_total = old_total + weighted_impact
        
        old_tier = self._get_tier(old_total)
        new_tier = self._get_tier(new_total)
        
        signal = Signal(
            timestamp=datetime.now().isoformat(),
            category='state',
            signal_type='state_score_change',
            source=source,
            data={'state': state, 'dimension': dimension, 
                  'score_change': score_change, 'description': description}
        )
        
        signal.analysis = {
            'weighted_impact': round(weighted_impact, 1),
            'old_total': old_total,
            'new_total': round(new_total, 1),
            'tier_changed': old_tier != new_tier
        }
        
        self.signal_log.append(signal)
        
        return {
            'state': state,
            'signal': description,
            'dimension': dimension,
            'dimension_weight': f"{weight*100:.0f}%",
            'score_change': score_change,
            'weighted_impact': round(weighted_impact, 1),
            'old_score': old_total,
            'new_score': round(new_total, 1),
            'old_tier': old_tier.value,
            'new_tier': new_tier.value,
            'tier_changed': old_tier != new_tier
        }
    
    def _get_tier(self, score: float) -> StateTier:
        """Determine tier from score."""
        if score >= 75:
            return StateTier.TIER_1
        elif score >= 60:
            return StateTier.TIER_2
        elif score >= 50:
            return StateTier.TIER_3
        else:
            return StateTier.AVOID
    
    def apply_scenario_adjustment(self, scenario_a_delta: float) -> Dict:
        """Apply adjustment to scenario probabilities."""
        current_a = self.state.demand_scenario_probabilities[DemandScenario.ACCELERATION]
        new_a = max(0.1, min(0.9, current_a + scenario_a_delta))  # Bound 10-90%
        new_b = 1 - new_a
        
        self.state.demand_scenario_probabilities = {
            DemandScenario.ACCELERATION: new_a,
            DemandScenario.PLATEAU: new_b
        }
        
        return {
            'old_probabilities': {
                'scenario_a': current_a,
                'scenario_b': 1 - current_a
            },
            'new_probabilities': {
                'scenario_a': new_a,
                'scenario_b': new_b
            },
            'adjustment_applied': scenario_a_delta
        }
    
    def get_state_summary(self) -> Dict:
        """Get current forecast state summary."""
        return {
            'snapshot_date': self.state.snapshot_date,
            'demand_probabilities': {
                s.value: p for s, p in 
                self.state.demand_scenario_probabilities.items()
            },
            'supply_scenario': self.state.supply_scenario.value,
            'signals_processed': len(self.signal_log),
            'forecast_2027': self.get_gap_forecast(2027),
            'forecast_2030': self.get_gap_forecast(2030)
        }
    
    def export_signal_log(self) -> List[Dict]:
        """Export signal log for review."""
        return [
            {
                'timestamp': s.timestamp,
                'category': s.category,
                'type': s.signal_type,
                'source': s.source,
                'data': s.data,
                'analysis': s.analysis
            }
            for s in self.signal_log
        ]


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_tracker() -> ForecastTracker:
    """Create a new tracker with baseline state."""
    return ForecastTracker()


def compare_to_baseline(tracker: ForecastTracker) -> Dict:
    """Compare current state to baseline."""
    baseline = ForecastState.create_baseline()
    
    return {
        'demand_probability_delta': {
            'scenario_a': (tracker.state.demand_scenario_probabilities[DemandScenario.ACCELERATION] - 
                          baseline.demand_scenario_probabilities[DemandScenario.ACCELERATION])
        },
        'supply_scenario_changed': tracker.state.supply_scenario != baseline.supply_scenario,
        'signals_since_baseline': len(tracker.signal_log)
    }


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Create tracker
    tracker = create_tracker()
    
    print("=== Baseline State ===")
    print(json.dumps(tracker.get_state_summary(), indent=2))
    
    print("\n=== Process CoWoS Signal ===")
    result = tracker.process_cowos_signal(
        year=2025,
        new_capacity_wpm=70000,  # +17% vs 60K baseline
        source="TSMC Q3 2025 Earnings"
    )
    print(json.dumps(result, indent=2))
    
    print("\n=== Process Capex Signal ===")
    result = tracker.process_capex_signal(
        quarterly_capex_bn=68,  # +24% vs $55B baseline
        source="Combined Q3 earnings"
    )
    print(json.dumps(result, indent=2))
    
    print("\n=== Process Queue Signal ===")
    result = tracker.process_queue_signal(
        iso="PJM",
        new_queue_gw=95,  # +5 GW vs baseline
        new_completion_rate=0.21,  # +2% vs baseline
        source="PJM Monthly Queue Report"
    )
    print(json.dumps(result, indent=2))
    
    print("\n=== Process State Signal ===")
    result = tracker.process_state_signal(
        state="oklahoma",
        dimension="queue",
        score_change=5,  # Improved queue efficiency
        description="SPP implements fast-track interconnection for data centers",
        source="SPP Announcement"
    )
    print(json.dumps(result, indent=2))
    
    print("\n=== Apply Adjustment ===")
    result = tracker.apply_scenario_adjustment(0.05)  # +5% to Scenario A
    print(json.dumps(result, indent=2))
    
    print("\n=== Updated Forecast ===")
    print(json.dumps(tracker.get_gap_forecast(2027), indent=2))
    
    print("\n=== Signal Log ===")
    for signal in tracker.export_signal_log():
        print(f"- [{signal['timestamp'][:10]}] {signal['type']}: {signal['source']}")
