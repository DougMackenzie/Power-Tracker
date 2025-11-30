# AI DC Power Forecast Tracking Framework
## Aligned with Presentation Methodology

---

## CRITICAL CORRECTION

The previous framework incorrectly described the demand model as a regression with arbitrary weights. **That was wrong.**

Our actual methodology uses:
1. **Demand**: Bottoms-up physical conversion (CoWoS → Chips → TDP → Server → DC GW)
2. **Supply**: Constraint-based projection (queue completion rates, lead times, reform timelines)
3. **Gap Analysis**: Scenario matrix combinations
4. **State Scoring**: Weighted criteria (explicitly defined in presentation)
5. **Site Valuation**: Stage-based with geographic/scale multipliers

This document provides the correct framework for tracking and updating forecasts.

---

## PART 1: BASELINE DEFINITIONS

### 1.1 Demand Baseline (as of November 2025)

```python
DEMAND_BASELINE = {
    'snapshot_date': '2025-11-01',
    'source': 'Presentation Analysis',
    
    # Current operational capacity
    'current_global_ai_dc_gw': {
        'value': 12,
        'range': (10, 14),
        'reference_year': 2024,
        'sources': ['IEA', 'Goldman Sachs', 'McKinsey']
    },
    
    # Scenario trajectories (US Tech Stack Demand in GW)
    'scenario_a_acceleration': {
        'description': 'AI business case continues to scale',
        '2027': 50,
        '2030': 115,
        '2035': 230,
        'cagr': '25-30%',
        'triggers': [
            'Reasoning inference drives exponential compute',
            'Model sizes continue 10x/2yr scaling',
            'Enterprise adoption reaches majority workflows',
            'Autonomous systems scale'
        ]
    },
    'scenario_b_plateau': {
        'description': 'AI business case fails to materialize',
        '2027': 35,
        '2030': 85,
        '2035': 95,
        'cagr': '5-10% post-2030',
        'triggers': [
            'Efficiency gains outpace demand',
            'ROI skepticism reduces investment',
            'Model scaling hits diminishing returns',
            'Regulatory constraints limit deployment'
        ]
    },
    
    # Binding constraint through 2027
    'binding_constraint': 'CoWoS_packaging',
    'cowos_capacity_baseline': {
        '2024': 35000,  # wafers per month
        '2025': 60000,
        '2026': 80000,
        '2027': 100000,
        'source': 'TSMC earnings/guidance'
    },
    
    # Physical conversion factors (from slide 13)
    'conversion_factors': {
        'yield_mature_n4_n5': (0.70, 0.85),
        'yield_early_n3_n2': (0.50, 0.65),
        'h100_die_size_mm2': 814,
        'dies_per_wafer_h100': (60, 73),
        'utilization_training': (0.75, 0.85),
        'utilization_inference': (0.50, 0.65),
        'utilization_blended': (0.60, 0.80),
        'server_overhead_factor': 1.45,
        'pue_traditional': (1.4, 1.6),
        'pue_hyperscale': (1.2, 1.3),
        'pue_liquid_cooling': (1.1, 1.2)
    }
}
```

### 1.2 Supply Baseline (as of November 2025)

```python
SUPPLY_BASELINE = {
    'snapshot_date': '2025-11-01',
    'source': 'Presentation Analysis',
    
    # Current US DC power capacity
    'current_us_dc_gw': {
        'value': 10,
        'reference_year': 2024
    },
    
    # Supply scenarios (US deliverable capacity in GW)
    'supply_low': {
        'description': 'Utility delivery slippage, minimal GETs/SMR',
        '2027': 25,
        '2030': 50,
        '2035': 140
    },
    'supply_medium': {
        'description': 'Moderate reform impact, some GETs',
        '2027': 35,
        '2030': 75,
        '2035': 257
    },
    'supply_high': {
        'description': 'Aggressive reforms + GETs + SMR deployment',
        '2027': 45,
        '2030': 100,
        '2035': 418
    },
    
    # Constraint baselines
    'constraints': {
        'interconnection_queue_gw': {
            'pjm': 90,
            'ercot': 100,
            'spp': 25,
            'miso': 45,
            'wecc': 60,
            'serc': 35,
            'total_us': 355
        },
        'queue_completion_rate': {
            'historical_avg': 0.19,
            'pjm': 0.19,
            'ercot': 0.25,
            'spp': 0.35,
            'caiso': 0.12
        },
        'avg_queue_timeline_years': 5,
        'gas_turbine_lead_time_years': (5, 7),
        'transformer_lead_time_years': (2, 4),
        'ferc_2023_implementation': '2026-2027',
        'meaningful_backlog_reduction': '2028-2030'
    }
}
```

### 1.3 Gap Baseline (as of November 2025)

```python
GAP_BASELINE = {
    'snapshot_date': '2025-11-01',
    'most_likely_scenario': 'Low Supply × Demand A',
    
    # Gap matrix (from slide 29)
    'gap_matrix_gw': {
        'low_supply_demand_a': {
            '2027': -25,
            '2030': -65,
            '2035': -90,
            'probability': 0.40,  # Most likely
            'label': 'Persistent severe deficit'
        },
        'low_supply_demand_b': {
            '2027': -10,
            '2030': -35,
            '2035': +45,
            'probability': 0.20,
            'label': 'Tight then surplus'
        },
        'med_supply_demand_a': {
            '2027': -15,
            '2030': -40,
            '2035': +27,
            'probability': 0.25,
            'label': 'Requires GETs/SMR success'
        },
        'med_supply_demand_b': {
            '2027': 0,
            '2030': -10,
            '2035': +162,
            'probability': 0.10,
            'label': 'Balanced then surplus'
        },
        'high_supply_demand_a': {
            '2027': -5,
            '2030': -15,
            '2035': +188,
            'probability': 0.04,
            'label': 'Achievable if aggressive'
        },
        'high_supply_demand_b': {
            '2027': +10,
            '2030': +15,
            '2035': +323,
            'probability': 0.01,
            'label': 'Major surplus'
        }
    },
    
    # Weighted expected gap
    'expected_gap_gw': {
        '2027': -17,  # Probability-weighted
        '2030': -45,
        '2035': -12
    }
}
```

### 1.4 State Scoring Baseline

```python
STATE_SCORING_BASELINE = {
    'snapshot_date': '2025-11-01',
    
    # Weights (from slide 34 - THESE ARE CORRECT)
    'dimension_weights': {
        'queue_efficiency': 0.25,          # 25%
        'permitting_speed': 0.20,          # 20%
        'btm_flexibility': 0.15,           # 15%
        'transmission_headroom': 0.15,     # 15%
        'resource_access': 0.10,           # 10%
        'saturation_competition': 0.10,    # 10%
        'cost_structure': 0.05             # 5%
    },
    
    # Tier thresholds
    'tier_thresholds': {
        'tier_1': (75, 100),  # Highest priority
        'tier_2': (60, 74),   # Strong potential
        'tier_3': (50, 64),   # Selective
        'avoid': (0, 49)      # Structural barriers
    },
    
    # Baseline state scores (from presentation tier slides)
    'state_scores': {
        # Tier 1
        'oklahoma': {'score': 88, 'queue': 85, 'permitting': 90, 'btm': 85, 
                     'transmission': 80, 'resources': 95, 'saturation': 90},
        'wyoming': {'score': 82, 'queue': 80, 'permitting': 95, 'btm': 90,
                    'transmission': 70, 'resources': 90, 'saturation': 95},
        'texas_secondary': {'score': 80, 'queue': 75, 'permitting': 95, 'btm': 95,
                           'transmission': 65, 'resources': 85, 'saturation': 60},
        
        # Tier 2
        'west_virginia': {'score': 76, 'queue': 65, 'permitting': 85, 'btm': 70,
                         'transmission': 75, 'resources': 80, 'saturation': 90},
        'indiana': {'score': 72, 'queue': 60, 'permitting': 75, 'btm': 65,
                   'transmission': 70, 'resources': 75, 'saturation': 80},
        'arkansas': {'score': 71, 'queue': 75, 'permitting': 80, 'btm': 70,
                    'transmission': 65, 'resources': 75, 'saturation': 85},
        'ohio': {'score': 70, 'queue': 55, 'permitting': 70, 'btm': 60,
                'transmission': 65, 'resources': 80, 'saturation': 75},
        'georgia': {'score': 70, 'queue': 65, 'permitting': 70, 'btm': 55,
                   'transmission': 60, 'resources': 70, 'saturation': 65},
        'louisiana': {'score': 68, 'queue': 65, 'permitting': 75, 'btm': 75,
                     'transmission': 60, 'resources': 85, 'saturation': 85},
        'pennsylvania_west': {'score': 68, 'queue': 55, 'permitting': 65, 'btm': 60,
                             'transmission': 65, 'resources': 80, 'saturation': 75},
        'mississippi': {'score': 64, 'queue': 60, 'permitting': 75, 'btm': 65,
                       'transmission': 55, 'resources': 70, 'saturation': 90},
        
        # Tier 3
        'new_mexico': {'score': 67, 'queue': 70, 'permitting': 75, 'btm': 80,
                      'transmission': 60, 'resources': 85, 'saturation': 85},
        'montana': {'score': 62, 'queue': 75, 'permitting': 80, 'btm': 75,
                   'transmission': 50, 'resources': 70, 'saturation': 90},
        'virginia_secondary': {'score': 58, 'queue': 35, 'permitting': 65, 'btm': 50,
                              'transmission': 30, 'resources': 65, 'saturation': 20},
        'nevada': {'score': 55, 'queue': 60, 'permitting': 65, 'btm': 65,
                  'transmission': 50, 'resources': 60, 'saturation': 65},
        'arizona': {'score': 52, 'queue': 55, 'permitting': 60, 'btm': 60,
                   'transmission': 45, 'resources': 65, 'saturation': 60},
        
        # Avoid
        'new_york': {'score': 40},
        'new_england': {'score': 35},
        'virginia_nova': {'score': 30},
        'california': {'score': 25}
    }
}
```

---

## PART 2: TRACKING SIGNALS & DELTA CALCULATION

### 2.1 Signal Categories

```python
SIGNAL_CATEGORIES = {
    # DEMAND SIGNALS - Things that would change demand trajectory
    'demand': {
        'cowos_capacity_change': {
            'description': 'TSMC CoWoS capacity announcement different from baseline',
            'baseline_source': 'DEMAND_BASELINE.cowos_capacity_baseline',
            'impact': 'Direct - CoWoS is binding constraint through 2027',
            'data_sources': ['TSMC earnings', 'TSMC investor days', 'DigiTimes']
        },
        'hyperscaler_capex': {
            'description': 'Combined MSFT/GOOG/AMZN/META quarterly capex',
            'baseline': '$50-60B quarterly (2025)',
            'threshold_up': '+15% vs baseline = consider scenario shift toward A',
            'threshold_down': '-15% vs baseline = consider scenario shift toward B',
            'data_sources': ['Quarterly earnings reports']
        },
        'chip_tdp_announcement': {
            'description': 'Next-gen AI accelerator TDP (B200, B300, etc)',
            'baseline': 'B200: 1000W, B300: ~1200W expected',
            'impact': 'Higher TDP = higher per-chip power = higher GW demand',
            'data_sources': ['NVIDIA/AMD product announcements', 'GTC']
        },
        'ai_revenue_growth': {
            'description': 'Cloud AI revenue growth rates',
            'baseline': '30-40% YoY growth (2025)',
            'threshold_up': '>50% sustained = strengthen Scenario A confidence',
            'threshold_down': '<20% for 2+ quarters = strengthen Scenario B confidence',
            'data_sources': ['MSFT Azure AI', 'GOOG Cloud', 'AWS AI services revenue']
        },
        'major_model_release': {
            'description': 'Foundation model releases that change inference demand',
            'examples': ['GPT-5', 'Claude 4', 'Gemini 3'],
            'impact': 'Qualitative - larger models = more compute per query',
            'data_sources': ['Company announcements', 'ArXiv', 'Industry coverage']
        },
        'efficiency_breakthrough': {
            'description': 'Major inference efficiency improvement',
            'examples': ['2x inference efficiency', 'New quantization method'],
            'impact': 'Reduces GW demand per unit AI output',
            'direction': 'Shifts toward Scenario B'
        }
    },
    
    # SUPPLY SIGNALS - Things that would change supply trajectory
    'supply': {
        'queue_data_update': {
            'description': 'ISO interconnection queue reports',
            'baseline_source': 'SUPPLY_BASELINE.constraints.interconnection_queue_gw',
            'frequency': 'Monthly',
            'track': ['Total GW in queue', 'Completion rate', 'Withdrawals', 'New filings'],
            'data_sources': ['PJM queue', 'ERCOT GIS', 'SPP GI', 'MISO queue']
        },
        'ferc_reform_progress': {
            'description': 'FERC Order 2023 implementation status',
            'baseline': 'Full implementation 2026-2027',
            'impact': 'Acceleration = shift toward High Supply; Delays = confirm Low Supply',
            'data_sources': ['FERC orders', 'ISO compliance filings']
        },
        'transformer_lead_time': {
            'description': 'Large power transformer delivery times',
            'baseline': '2-4 years',
            'impact': 'Longer = confirm supply constraint; Shorter = supply acceleration',
            'data_sources': ['DOE transformer reports', 'Utility IRP filings']
        },
        'utility_dc_commitment': {
            'description': 'Utility announces major DC power commitment',
            'examples': ['AEP 5GW program', 'Dominion expansion'],
            'impact': 'Increases confidence in supply delivery',
            'track': 'MW committed, timeline, location'
        },
        'nuclear_restart': {
            'description': 'Nuclear plant restart announcements',
            'baseline': 'TMI-1, Palisades in progress',
            'impact': '~800MW-1GW per restart, 2-4 year timeline',
            'data_sources': ['NRC filings', 'Utility announcements']
        },
        'smr_progress': {
            'description': 'Small modular reactor milestones',
            'examples': ['NuScale deployment', 'TerraPower progress'],
            'baseline': 'Not material before 2030',
            'impact': 'Progress = shift toward High Supply scenario post-2030'
        },
        'btm_deployment': {
            'description': 'Behind-the-meter generation at data centers',
            'examples': ['Microsoft gas plant', 'Google fuel cells'],
            'impact': 'Reduces grid supply requirement',
            'track': 'MW deployed, location, technology'
        }
    },
    
    # STATE-LEVEL SIGNALS - Things that would change state scores
    'state': {
        'queue_policy_change': {
            'description': 'State/ISO queue process reform',
            'impact': 'Affects queue_efficiency dimension (25% weight)',
            'examples': ['Cluster study adoption', 'Fast-track provisions']
        },
        'permitting_legislation': {
            'description': 'State permitting law changes',
            'impact': 'Affects permitting_speed dimension (20% weight)',
            'examples': ['Streamlined approval process', 'Environmental exemptions']
        },
        'btm_regulatory_change': {
            'description': 'PUC rulings on behind-the-meter generation',
            'impact': 'Affects btm_flexibility dimension (15% weight)',
            'examples': ['Wheeling agreements', 'Self-generation caps']
        },
        'transmission_project': {
            'description': 'Major transmission project approval/completion',
            'impact': 'Affects transmission_headroom dimension (15% weight)',
            'examples': ['New 345kV line', 'Substation upgrade']
        },
        'dc_moratorium': {
            'description': 'Data center moratorium or restriction',
            'impact': 'Major negative - likely shifts to lower tier',
            'examples': ['Prince William County', 'Loudoun restrictions']
        },
        'major_dc_announcement': {
            'description': 'Large DC campus announcement in state',
            'impact': 'Affects saturation dimension (10% weight) negatively',
            'examples': ['1GW+ campus', 'Hyperscaler commitment']
        }
    }
}
```

### 2.2 Delta Calculation Methodology

```python
def calculate_demand_delta(signal_type: str, signal_data: dict) -> dict:
    """
    Calculate impact of a demand signal on forecast.
    
    Returns adjustment to scenario probabilities, not direct GW changes.
    Our methodology uses discrete scenarios, not continuous regression.
    """
    
    if signal_type == 'cowos_capacity_change':
        baseline = DEMAND_BASELINE['cowos_capacity_baseline']
        new_value = signal_data['new_capacity_wpm']
        year = signal_data['year']
        
        pct_change = (new_value - baseline[year]) / baseline[year]
        
        return {
            'type': 'scenario_probability_shift',
            'signal': f"CoWoS {year} capacity: {new_value:,} WPM (was {baseline[year]:,})",
            'pct_change_from_baseline': pct_change,
            'recommendation': (
                'Increase Scenario A probability' if pct_change > 0.10 else
                'Decrease Scenario A probability' if pct_change < -0.10 else
                'No material change'
            ),
            'magnitude': abs(pct_change)
        }
    
    elif signal_type == 'hyperscaler_capex':
        baseline_quarterly = 55  # $55B baseline
        new_value = signal_data['quarterly_capex_bn']
        
        pct_change = (new_value - baseline_quarterly) / baseline_quarterly
        
        return {
            'type': 'scenario_probability_shift',
            'signal': f"Hyperscaler capex: ${new_value}B (baseline ${baseline_quarterly}B)",
            'pct_change_from_baseline': pct_change,
            'recommendation': (
                'Strengthen Scenario A' if pct_change > 0.15 else
                'Strengthen Scenario B' if pct_change < -0.15 else
                'Within normal variance'
            )
        }
    
    # Add other signal types...
    
    return {'error': f'Unknown signal type: {signal_type}'}


def calculate_supply_delta(signal_type: str, signal_data: dict) -> dict:
    """
    Calculate impact of a supply signal on forecast.
    
    Returns adjustment to supply scenario, not direct GW changes.
    """
    
    if signal_type == 'queue_data_update':
        baseline = SUPPLY_BASELINE['constraints']['interconnection_queue_gw']
        iso = signal_data['iso']
        new_queue_gw = signal_data['new_queue_gw']
        new_completion_rate = signal_data.get('completion_rate')
        
        baseline_queue = baseline.get(iso, 0)
        queue_change = new_queue_gw - baseline_queue
        
        result = {
            'type': 'supply_scenario_indicator',
            'signal': f"{iso.upper()} queue: {new_queue_gw} GW (was {baseline_queue} GW)",
            'queue_change_gw': queue_change
        }
        
        if new_completion_rate:
            baseline_rate = SUPPLY_BASELINE['constraints']['queue_completion_rate'].get(iso, 0.19)
            rate_change = new_completion_rate - baseline_rate
            result['completion_rate_change'] = rate_change
            result['recommendation'] = (
                'Supply improving' if rate_change > 0.05 else
                'Supply deteriorating' if rate_change < -0.05 else
                'No material change'
            )
        
        return result
    
    elif signal_type == 'nuclear_restart':
        mw = signal_data['capacity_mw']
        timeline_years = signal_data['timeline_years']
        
        return {
            'type': 'supply_addition',
            'signal': f"Nuclear restart: {mw} MW by {2025 + timeline_years}",
            'gw_addition': mw / 1000,
            'timeline': timeline_years,
            'recommendation': 'Add to supply forecast for applicable years'
        }
    
    # Add other signal types...
    
    return {'error': f'Unknown signal type: {signal_type}'}


def calculate_state_score_delta(state: str, signal_type: str, signal_data: dict) -> dict:
    """
    Calculate impact of a state-level signal on state score.
    """
    
    weights = STATE_SCORING_BASELINE['dimension_weights']
    current_scores = STATE_SCORING_BASELINE['state_scores'].get(state, {})
    
    if not current_scores:
        return {'error': f'No baseline scores for state: {state}'}
    
    dimension_map = {
        'queue_policy_change': 'queue_efficiency',
        'permitting_legislation': 'permitting_speed',
        'btm_regulatory_change': 'btm_flexibility',
        'transmission_project': 'transmission_headroom',
        'dc_moratorium': 'saturation_competition',  # But also permitting
        'major_dc_announcement': 'saturation_competition'
    }
    
    affected_dimension = dimension_map.get(signal_type)
    if not affected_dimension:
        return {'error': f'Unknown signal type: {signal_type}'}
    
    dimension_weight = weights[affected_dimension]
    score_change = signal_data.get('score_change', 0)  # e.g., +10 or -15
    
    # Weighted impact on total score
    weighted_impact = score_change * dimension_weight
    
    current_total = current_scores.get('score', 0)
    new_total = current_total + weighted_impact
    
    # Determine tier change
    old_tier = get_tier(current_total)
    new_tier = get_tier(new_total)
    
    return {
        'state': state,
        'signal': signal_data.get('description', signal_type),
        'dimension_affected': affected_dimension,
        'dimension_weight': dimension_weight,
        'dimension_score_change': score_change,
        'total_score_impact': round(weighted_impact, 1),
        'old_score': current_total,
        'new_score': round(new_total, 1),
        'old_tier': old_tier,
        'new_tier': new_tier,
        'tier_changed': old_tier != new_tier
    }


def get_tier(score: float) -> str:
    """Determine tier from score."""
    if score >= 75:
        return 'Tier 1'
    elif score >= 60:
        return 'Tier 2'
    elif score >= 50:
        return 'Tier 3'
    else:
        return 'Avoid'
```

---

## PART 3: DATA SOURCES TO MONITOR

### 3.1 Weekly Monitoring

| Signal Category | Source | Data Points | Antigravity Query |
|----------------|--------|-------------|-------------------|
| Queue Updates | ISO websites | Queue GW, withdrawals, completions | `"PJM interconnection queue update"` |
| DC Announcements | DataCenter Dynamics, News | Location, MW, timeline | `"data center announcement"` |
| Hyperscaler News | Earnings, Press | Capex guidance, AI revenue | `"Microsoft Google Amazon AI infrastructure"` |

### 3.2 Monthly Monitoring

| Signal Category | Source | Data Points | Antigravity Query |
|----------------|--------|-------------|-------------------|
| Queue Reports | PJM/ERCOT/SPP/MISO | Full queue spreadsheet | `"[ISO] generator interconnection queue monthly"` |
| Transformer | DOE, Industry | Lead times, orders | `"large power transformer lead time"` |
| Utility IRPs | State PUC | Planned capacity, DC load | `"utility integrated resource plan data center"` |

### 3.3 Quarterly Monitoring

| Signal Category | Source | Data Points | Antigravity Query |
|----------------|--------|-------------|-------------------|
| Hyperscaler Capex | Earnings calls | Quarterly capex, guidance | `"[Company] earnings capex AI"` |
| CoWoS Capacity | TSMC | WPM capacity, utilization | `"TSMC CoWoS capacity earnings"` |
| Chip TDP | NVIDIA/AMD | New product specs | `"NVIDIA AMD AI chip power TDP"` |
| AI Revenue | Earnings | Cloud AI revenue growth | `"cloud AI revenue growth"` |

### 3.4 Event-Driven Monitoring

| Signal Type | Trigger | Impact |
|-------------|---------|--------|
| TSMC Investor Day | Semi-annual | CoWoS capacity roadmap |
| FERC Orders | As issued | Queue reform progress |
| GTC/Hot Chips | Annual | Next-gen chip specs |
| Nuclear NRC Filing | As filed | Restart timeline |
| State Legislation | As enacted | Score adjustment |

---

## PART 4: SITE MATURITY SCORING (UNCHANGED)

The site maturity scoring framework from the previous document remains valid. It was based on our discussion of the "Right Ingredients" framework, not invented weights.

Key dimensions:
- **Power Pathway (40 pts)**: Queue, utility engagement, transmission, BTM, timeline
- **Site Fundamentals (25 pts)**: Land, acreage, zoning, water, fiber, environmental
- **End User Demand (20 pts)**: Interest level, market, latency
- **Execution Capability (15 pts)**: Track record, relationships, capital, community

This framework emerged from our discussion of what creates value vs. queue-only positions.

---

## PART 5: VALUATION FRAMEWORK (ALIGNED WITH PRESENTATION)

From slides 56-57 (Geographic Convergence, Valuation Forecast):

```python
VALUATION_FRAMEWORK = {
    # Actual market data from our discussion
    'current_market_data_2025': {
        'nova': {'range': (1000000, None), 'label': '$1M+/MW'},
        'dfw': {'range': (500000, 1000000), 'label': '$500K-$1M/MW'},
        'tulsa_ok': {'range': (200000, 300000), 'label': '~$200K/MW'},
        'rural_emerging': {'range': (150000, 200000), 'label': '$150K+/MW'}
    },
    
    # Convergence thesis: Central Belt → 70-85% of NoVA by 2030
    'convergence_trajectory': {
        '2025': 0.30,  # Central Belt at 30% of NoVA
        '2027': 0.50,  # 50% of NoVA
        '2030': 0.75   # 75% of NoVA
    },
    
    # De-risked site valuations (from slide 56)
    'valuation_by_year_500mw': {
        '2025': {'low': 400000, 'mid': 600000, 'high': 900000},
        '2026': {'low': 500000, 'mid': 800000, 'high': 1200000},
        '2027': {'low': 700000, 'mid': 1100000, 'high': 1600000},
        '2028': {'low': 800000, 'mid': 1300000, 'high': 2000000},  # Peak
        '2029': {'low': 900000, 'mid': 1400000, 'high': 2200000},
        '2030': {'low': 800000, 'mid': 1300000, 'high': 2000000}
    },
    
    'valuation_by_year_1gw': {
        '2025': {'low': 550000, 'mid': 800000, 'high': 1200000},
        '2026': {'low': 700000, 'mid': 1100000, 'high': 1600000},
        '2027': {'low': 1000000, 'mid': 1500000, 'high': 2200000},
        '2028': {'low': 1200000, 'mid': 1800000, 'high': 2800000},  # Peak
        '2029': {'low': 1300000, 'mid': 2000000, 'high': 3000000},
        '2030': {'low': 1200000, 'mid': 1800000, 'high': 2800000}
    },
    
    # Scale premium
    'scale_premium': {
        '2025': 0.35,  # 1GW is 35% more valuable per MW than 500MW
        '2027': 0.40,
        '2030': 0.45
    },
    
    # Stage multipliers (bimodal distribution concept)
    'stage_multipliers': {
        'queue_only': 0.0,         # ~$0 - just filing costs
        'early_real': 0.25,        # 25% of de-risked
        'study_in_progress': 0.50, # 50% of de-risked
        'utility_commitment': 0.70, # 70% of de-risked
        'fully_entitled': 1.0,     # Full de-risked value
        'end_user_attached': 1.3   # 30% premium
    }
}
```

---

## PART 6: IMPLEMENTATION NOTES

### What This Framework Does

1. **Defines explicit baselines** with specific numbers from our presentation
2. **Lists trackable data sources** for each forecast input
3. **Provides delta calculation logic** that respects our scenario-based methodology
4. **Aligns state scoring** with the actual weights we established

### What This Framework Does NOT Do

1. **No invented regression weights** - We use scenarios, not regressions
2. **No continuous demand function** - Demand is scenario-driven from CoWoS bottleneck
3. **No arbitrary signal impacts** - Each signal type has specific meaning

### Recommended Antigravity Integration

```python
# Weekly scan queries
WEEKLY_QUERIES = [
    # Demand signals
    'TSMC CoWoS capacity update',
    'hyperscaler data center capex announcement',
    'AI infrastructure investment',
    'NVIDIA AMD new chip announcement TDP',
    
    # Supply signals  
    'PJM ERCOT SPP MISO interconnection queue',
    'FERC order interconnection reform',
    'nuclear plant restart data center',
    'large power transformer delivery',
    
    # Market signals
    'data center powered land transaction',
    'hyperscaler campus location announcement',
    'data center moratorium'
]
```

---

## VERSION HISTORY

- **v2.0** (2025-11-30): Corrected framework. Removed fabricated regression weights. Aligned with actual presentation methodology.
- **v1.0** (2025-11-30): Initial framework. DEPRECATED - contained invented demand model weights.

---

*This framework reflects the actual methodology from our AI DC Power Analysis presentation. The demand model is scenario-based from physical bottlenecks (CoWoS), not a regression. State scoring weights come directly from slide 34.*
