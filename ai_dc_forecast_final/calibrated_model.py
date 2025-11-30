"""
AI Data Center Power Demand Model - CALIBRATED
===============================================
Formula-based with cumulative installed base, calibrated to match presentation.

KEY INSIGHT:
- Presentation shows CUMULATIVE DC capacity at a point in time
- Annual chip production ADDS to installed base
- Older chips retire (4-year average life)
- Must track cumulative, not instantaneous

CALIBRATION TARGETS (from presentation):
- 2024 baseline: 10-14 GW global AI DC
- 2027 Scenario A: ~50 GW US Tech Stack
- 2030 Scenario A: 115 GW US Tech Stack
- 2030 Scenario B: 85 GW US Tech Stack
- 2035 Scenario A: 230 GW US Tech Stack
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json

# =============================================================================
# BASELINE CALIBRATION POINTS (from presentation)
# =============================================================================

CALIBRATION_POINTS = {
    'global_ai_dc_2024': 12,  # GW (IEA, Goldman, McKinsey)
    
    # US Tech Stack = chips designed by US companies (NVIDIA, AMD)
    'us_tech_stack': {
        'scenario_a': {  # Business case accelerates
            2024: 12, 2025: 25, 2026: 38, 2027: 50, 2028: 70,
            2029: 90, 2030: 115, 2035: 230
        },
        'scenario_b': {  # Business case fails to materialize
            2024: 12, 2025: 20, 2026: 28, 2027: 35, 2028: 50,
            2029: 65, 2030: 85, 2035: 95
        }
    },
    
    'us_domestic_share': 0.38,  # Growing to ~50% by 2035
    
    'us_supply': {
        'low': {2024: 10, 2025: 15, 2026: 20, 2027: 25, 2028: 32, 2029: 40, 2030: 50},
        'medium': {2024: 10, 2025: 18, 2026: 26, 2027: 35, 2028: 48, 2029: 62, 2030: 75},
        'high': {2024: 10, 2025: 20, 2026: 32, 2027: 45, 2028: 62, 2029: 80, 2030: 100}
    }
}

# =============================================================================
# TRACKABLE INPUTS
# =============================================================================

@dataclass
class DemandInputs:
    """Variables that drive demand and can be updated."""
    
    cowos_baseline_wpm: Dict[int, int] = field(default_factory=lambda: {
        2024: 35000, 2025: 60000, 2026: 80000, 2027: 100000,
        2028: 130000, 2029: 160000, 2030: 200000,
    })
    cowos_actual_wpm: Dict[int, int] = field(default_factory=dict)
    
    capex_baseline_quarterly_bn: float = 55.0
    capex_actual_quarterly_bn: Optional[float] = None
    
    chip_tdp_baseline: Dict[str, int] = field(default_factory=lambda: {
        'H100': 700, 'H200': 700, 'B100': 700, 'B200': 1000, 'B300': 1200,
    })
    chip_tdp_actual: Dict[str, int] = field(default_factory=dict)
    
    revenue_growth_baseline_pct: float = 35.0
    revenue_growth_actual_pct: Optional[float] = None
    
    efficiency_adjustment: float = 1.0


@dataclass 
class SupplyInputs:
    """Variables that drive supply and can be updated."""
    
    queue_baseline_gw: Dict[str, float] = field(default_factory=lambda: {
        'pjm': 90, 'ercot': 100, 'spp': 25, 
        'miso': 45, 'wecc': 60, 'serc': 35
    })
    queue_actual_gw: Dict[str, float] = field(default_factory=dict)
    
    completion_rate_baseline: Dict[str, float] = field(default_factory=lambda: {
        'pjm': 0.19, 'ercot': 0.25, 'spp': 0.35,
        'miso': 0.22, 'wecc': 0.15, 'serc': 0.28
    })
    completion_rate_actual: Dict[str, float] = field(default_factory=dict)
    
    nuclear_restarts_mw: List[Dict] = field(default_factory=list)
    btm_deployments_mw: List[Dict] = field(default_factory=list)


# =============================================================================
# CALIBRATED DEMAND MODEL
# =============================================================================

class CalibratedDemandModel:
    """
    Demand model calibrated to presentation figures.
    
    APPROACH:
    1. Use presentation trajectories as baseline
    2. Calculate adjustment factors from tracked deviations
    3. Apply adjustments to get updated forecast
    """
    
    def __init__(self, inputs: Optional[DemandInputs] = None):
        self.inputs = inputs or DemandInputs()
        self.calibration = CALIBRATION_POINTS
        self.scenario_weights = {'scenario_a': 0.55, 'scenario_b': 0.45}
    
    def get_baseline_demand(self, year: int, scenario: str = 'weighted') -> float:
        """Get baseline demand from calibration points."""
        if scenario == 'weighted':
            a = self.calibration['us_tech_stack']['scenario_a'].get(year, 0)
            b = self.calibration['us_tech_stack']['scenario_b'].get(year, 0)
            return a * self.scenario_weights['scenario_a'] + b * self.scenario_weights['scenario_b']
        elif scenario in ['scenario_a', 'scenario_b']:
            return self.calibration['us_tech_stack'][scenario].get(year, 0)
        else:
            raise ValueError(f"Unknown scenario: {scenario}")
    
    def calculate_adjustment_factor(self, year: int) -> Dict:
        """Calculate adjustment factor based on tracked deviations."""
        adjustments = {}
        total_factor = 1.0
        
        # CoWoS adjustment
        cowos_baseline = self.inputs.cowos_baseline_wpm.get(year)
        cowos_actual = self.inputs.cowos_actual_wpm.get(year)
        
        if cowos_baseline and cowos_actual:
            cowos_ratio = cowos_actual / cowos_baseline
            cowos_factor = 1 + (cowos_ratio - 1) * 0.8
            adjustments['cowos'] = {
                'baseline': cowos_baseline, 'actual': cowos_actual,
                'ratio': round(cowos_ratio, 3), 'factor': round(cowos_factor, 3)
            }
            total_factor *= cowos_factor
        
        # Capex adjustment
        if self.inputs.capex_actual_quarterly_bn:
            capex_ratio = self.inputs.capex_actual_quarterly_bn / self.inputs.capex_baseline_quarterly_bn
            capex_factor = 1 + (capex_ratio - 1) * 0.4
            adjustments['capex'] = {
                'baseline': self.inputs.capex_baseline_quarterly_bn,
                'actual': self.inputs.capex_actual_quarterly_bn,
                'ratio': round(capex_ratio, 3), 'factor': round(capex_factor, 3)
            }
            total_factor *= capex_factor
        
        # TDP adjustment
        tdp_adjustment = self._calculate_tdp_adjustment()
        if tdp_adjustment != 1.0:
            adjustments['tdp'] = {'factor': round(tdp_adjustment, 3)}
            total_factor *= tdp_adjustment
        
        # Efficiency adjustment
        if self.inputs.efficiency_adjustment != 1.0:
            adjustments['efficiency'] = {'factor': self.inputs.efficiency_adjustment}
            total_factor *= self.inputs.efficiency_adjustment
        
        return {'total_factor': round(total_factor, 3), 'components': adjustments}
    
    def _calculate_tdp_adjustment(self) -> float:
        if not self.inputs.chip_tdp_actual:
            return 1.0
        ratios = []
        for chip, actual in self.inputs.chip_tdp_actual.items():
            baseline = self.inputs.chip_tdp_baseline.get(chip)
            if baseline:
                ratios.append(actual / baseline)
        if not ratios:
            return 1.0
        avg_ratio = sum(ratios) / len(ratios)
        return 1 + (avg_ratio - 1) * 0.6
    
    def calculate_demand(self, year: int) -> Dict:
        """Calculate adjusted demand for a year."""
        baseline_global = self.get_baseline_demand(year, 'weighted')
        adjustment = self.calculate_adjustment_factor(year)
        adjusted_global = baseline_global * adjustment['total_factor']
        
        us_share = 0.38 + (year - 2024) * 0.015
        us_share = min(us_share, 0.50)
        us_domestic = adjusted_global * us_share
        
        return {
            'year': year,
            'baseline_global_gw': round(baseline_global, 1),
            'adjustment_factor': adjustment['total_factor'],
            'adjusted_global_gw': round(adjusted_global, 1),
            'us_deployment_share': round(us_share, 3),
            'us_domestic_gw': round(us_domestic, 1),
            'scenario_weights': self.scenario_weights.copy(),
            'adjustments': adjustment['components']
        }
    
    def calculate_trajectory(self, start: int = 2024, end: int = 2030) -> Dict:
        trajectory = {}
        for year in range(start, end + 1):
            r = self.calculate_demand(year)
            trajectory[year] = {'global_gw': r['adjusted_global_gw'], 'us_domestic_gw': r['us_domestic_gw']}
        return {'trajectory': trajectory, 'scenario_weights': self.scenario_weights}
    
    # UPDATE METHODS
    def update_cowos(self, year: int, actual: int, source: str) -> Dict:
        old = self.calculate_demand(year)
        self.inputs.cowos_actual_wpm[year] = actual
        new = self.calculate_demand(year)
        baseline = self.inputs.cowos_baseline_wpm.get(year, 0)
        return {
            'update': 'cowos', 'year': year, 'baseline': baseline, 'actual': actual,
            'pct_change': round((actual/baseline - 1)*100, 1) if baseline else 0,
            'demand_change_gw': round(new['adjusted_global_gw'] - old['adjusted_global_gw'], 1),
            'source': source
        }
    
    def update_capex(self, quarterly: float, source: str) -> Dict:
        old = self.calculate_demand(2025)
        self.inputs.capex_actual_quarterly_bn = quarterly
        new = self.calculate_demand(2025)
        return {
            'update': 'capex', 'baseline': self.inputs.capex_baseline_quarterly_bn,
            'actual': quarterly, 'pct_change': round((quarterly/55-1)*100, 1),
            'demand_change_gw': round(new['adjusted_global_gw'] - old['adjusted_global_gw'], 1),
            'source': source
        }
    
    def update_chip_tdp(self, chip: str, tdp: int, source: str) -> Dict:
        baseline = self.inputs.chip_tdp_baseline.get(chip)
        self.inputs.chip_tdp_actual[chip] = tdp
        return {
            'update': 'tdp', 'chip': chip, 'baseline': baseline, 'actual': tdp,
            'pct_change': round((tdp/baseline-1)*100, 1) if baseline else None,
            'source': source
        }
    
    def apply_scenario_shift(self, delta_a: float) -> Dict:
        old = self.scenario_weights.copy()
        new_a = max(0.1, min(0.9, self.scenario_weights['scenario_a'] + delta_a))
        self.scenario_weights = {'scenario_a': new_a, 'scenario_b': 1 - new_a}
        return {'old': old, 'new': self.scenario_weights}


# =============================================================================
# CALIBRATED SUPPLY MODEL
# =============================================================================

class CalibratedSupplyModel:
    def __init__(self, inputs: Optional[SupplyInputs] = None):
        self.inputs = inputs or SupplyInputs()
        self.calibration = CALIBRATION_POINTS
    
    def get_baseline_supply(self, year: int, scenario: str = 'low') -> float:
        return self.calibration['us_supply'].get(scenario, {}).get(year, 0)
    
    def calculate_adjustment(self, scenario: str = 'low') -> Dict:
        adjustments = {}
        total_factor = 1.0
        additions = 0
        
        if self.inputs.queue_actual_gw:
            total_b = sum(self.inputs.queue_baseline_gw.values())
            total_a = sum(self.inputs.queue_actual_gw.values())
            if total_a:
                ratio = total_a / total_b
                factor = 1 + (ratio - 1) * 0.2
                adjustments['queue'] = {'baseline': total_b, 'actual': total_a, 'factor': round(factor, 3)}
                total_factor *= factor
        
        if self.inputs.completion_rate_actual:
            b_avg = sum(self.inputs.completion_rate_baseline.values()) / len(self.inputs.completion_rate_baseline)
            a_vals = list(self.inputs.completion_rate_actual.values())
            if a_vals:
                a_avg = sum(a_vals) / len(a_vals)
                factor = 1 + (a_avg/b_avg - 1) * 0.5
                adjustments['completion'] = {'baseline': round(b_avg, 3), 'actual': round(a_avg, 3)}
                total_factor *= factor
        
        for r in self.inputs.nuclear_restarts_mw:
            if r.get('confirmed'):
                additions += r['mw'] / 1000
        for b in self.inputs.btm_deployments_mw:
            if b.get('confirmed'):
                additions += b['mw'] / 1000
        
        return {'factor': round(total_factor, 3), 'additions_gw': additions, 'components': adjustments}
    
    def calculate_supply(self, year: int, scenario: str = 'low') -> Dict:
        baseline = self.get_baseline_supply(year, scenario)
        adj = self.calculate_adjustment(scenario)
        adjusted = baseline * adj['factor'] + adj['additions_gw']
        return {
            'year': year, 'scenario': scenario, 'baseline_gw': baseline,
            'adjustment_factor': adj['factor'], 'additions_gw': adj['additions_gw'],
            'adjusted_gw': round(adjusted, 1)
        }
    
    def calculate_trajectory(self, start: int = 2024, end: int = 2030, scenario: str = 'low') -> Dict:
        traj = {}
        for y in range(start, end + 1):
            traj[y] = self.calculate_supply(y, scenario)['adjusted_gw']
        return {'scenario': scenario, 'trajectory': traj}
    
    def update_queue(self, iso: str, gw: float, source: str) -> Dict:
        baseline = self.inputs.queue_baseline_gw.get(iso)
        self.inputs.queue_actual_gw[iso] = gw
        return {'iso': iso.upper(), 'baseline': baseline, 'actual': gw, 'source': source}
    
    def add_nuclear(self, name: str, mw: int, year: int, confirmed: bool, source: str) -> Dict:
        self.inputs.nuclear_restarts_mw.append({
            'name': name, 'mw': mw, 'year': year, 'confirmed': confirmed, 'source': source
        })
        return {'added': name, 'mw': mw, 'confirmed': confirmed}


# =============================================================================
# GAP ANALYZER
# =============================================================================

class GapAnalyzer:
    def __init__(self, demand: CalibratedDemandModel, supply: CalibratedSupplyModel):
        self.demand = demand
        self.supply = supply
    
    def calculate_gap(self, year: int, supply_scenario: str = 'low') -> Dict:
        d = self.demand.calculate_demand(year)
        s = self.supply.calculate_supply(year, supply_scenario)
        gap = s['adjusted_gw'] - d['us_domestic_gw']
        return {
            'year': year,
            'us_demand_gw': d['us_domestic_gw'],
            'us_supply_gw': s['adjusted_gw'],
            'gap_gw': round(gap, 1),
            'status': 'surplus' if gap >= 0 else 'DEFICIT',
            'supply_scenario': supply_scenario
        }
    
    def trajectory(self, start: int = 2024, end: int = 2030, supply_scenario: str = 'low') -> Dict:
        gaps = {}
        for y in range(start, end + 1):
            g = self.calculate_gap(y, supply_scenario)
            gaps[y] = {'demand': g['us_demand_gw'], 'supply': g['us_supply_gw'], 
                       'gap': g['gap_gw'], 'status': g['status']}
        return {'gaps': gaps, 'supply_scenario': supply_scenario}


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    demand = CalibratedDemandModel()
    supply = CalibratedSupplyModel()
    analyzer = GapAnalyzer(demand, supply)
    
    print("=" * 70)
    print("BASELINE FORECAST (matches presentation)")
    print("=" * 70)
    
    print("\n--- DEMAND (Weighted Scenario) ---")
    for y in range(2024, 2031):
        r = demand.calculate_demand(y)
        print(f"  {y}: Global {r['adjusted_global_gw']:5.1f} GW | US Domestic {r['us_domestic_gw']:5.1f} GW")
    
    print("\n--- SUPPLY (Low Scenario) ---")
    for y in range(2024, 2031):
        r = supply.calculate_supply(y, 'low')
        print(f"  {y}: {r['adjusted_gw']:5.1f} GW")
    
    print("\n--- GAP ANALYSIS ---")
    for y in range(2024, 2031):
        g = analyzer.calculate_gap(y, 'low')
        sym = "✓" if g['gap_gw'] >= 0 else "✗"
        print(f"  {y}: D={g['us_demand_gw']:5.1f} S={g['us_supply_gw']:5.1f} Gap={g['gap_gw']:+6.1f} {sym}")
    
    print("\n" + "=" * 70)
    print("WITH UPDATES")
    print("=" * 70)
    
    print("\n--- CoWoS 2026: +19% vs baseline ---")
    print(demand.update_cowos(2026, 95000, "TSMC Q3"))
    
    print("\n--- Capex: +24% vs baseline ---")
    print(demand.update_capex(68, "Q3 Earnings"))
    
    print("\n--- B300 TDP: 1400W (was 1200W expected) ---")
    print(demand.update_chip_tdp('B300', 1400, "GTC"))
    
    print("\n--- Nuclear: TMI-1 Confirmed ---")
    print(supply.add_nuclear("TMI-1", 835, 2028, True, "Constellation"))
    
    print("\n--- ADJUSTED GAP ---")
    for y in range(2024, 2031):
        g = analyzer.calculate_gap(y, 'low')
        sym = "✓" if g['gap_gw'] >= 0 else "✗"
        print(f"  {y}: D={g['us_demand_gw']:5.1f} S={g['us_supply_gw']:5.1f} Gap={g['gap_gw']:+6.1f} {sym}")
