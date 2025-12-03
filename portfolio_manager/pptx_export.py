"""
PowerPoint Export Module v3
===========================
Comprehensive site profile export including all diagnostic report sections.

Slide Order:
0. Title (dark blue background - from template)
1. Site Profile (white - from template)
2. Site Boundary (white - from template)
3. Topography (white - from template)
4. Capacity Trajectory (white background, dark header bar)
5. Infrastructure & Critical Path (white background, dark header bar)
6. Thank You (dark blue - moved to end from template)

Diagnostic Sections Captured:
- Site overview with key metrics
- Capacity trajectory (Interconnection vs Generation)
- Critical path phases with study/contract status
- Infrastructure readiness scores
- Risks and opportunities
- Market analysis context
- Score analysis (optional radar chart)
"""

import os
import io
import json
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from copy import deepcopy

# For chart generation
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.ticker import MaxNLocator
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


# =============================================================================
# CONFIGURATION
# =============================================================================

JLL_COLORS = {
    'dark_blue': '#003f5c',      # Darker header blue
    'red': '#e31837',            # Fatal flaw red
    'light_gray': '#f5f5f5',
    'medium_gray': '#666666',
    'dark_gray': '#333333',
    'teal': '#2b6777',           # Primary teal (infrastructure bars, etc.)
    'tan': '#c9b89d',            # Generation line contrast
    'white': '#ffffff',
    'green': '#4caf50',          # Rating: Desirable
    'yellow': '#ffc107',         # Rating: Acceptable
    'orange': '#ff9800',         # Rating: Marginal
    'rating_gray': '#9e9e9e',    # Rating: N/R (not rated)
    'amber': '#f9a825',          # Legacy amber (keep for compat)
    'light_blue': '#4a90d9',
}

# Template version - increment to force regeneration
TEMPLATE_VERSION = "2.0"  # Updated with professional formatting

TEMPLATE_SLIDES = {
    'title': 0,
    'site_profile': 1,
    'site_boundary': 2,
    'topography': 3,
    'thank_you': 4,
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PhaseData:
    """Data for a single development phase."""
    phase_num: int
    target_mw: float
    voltage_kv: int
    target_online: str
    screening_study: str = 'Not Started'
    contract_study: str = 'Not Started'
    letter_of_agreement: str = 'Not Started'
    energy_contract: str = 'Not Started'
    transmission_type: str = ''
    substation_type: str = ''
    distance_to_transmission: float = 0.0

    def to_dict(self) -> Dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class CapacityTrajectory:
    """Capacity trajectory data."""
    years: List[int]
    interconnection_mw: List[float]
    generation_mw: List[float]
    available_mw: List[float]

    @classmethod
    def from_dict(cls, data: Dict) -> 'CapacityTrajectory':
        years, interconnection, generation, available = [], [], [], []
        for year_str, values in sorted(data.items()):
            try:
                year = int(year_str)
                years.append(year)
                ic = values.get('interconnection_mw', values.get('capacity', 0))
                gen = values.get('generation_mw', values.get('ramp', 0))
                interconnection.append(ic)
                generation.append(gen)
                available.append(values.get('available_mw', min(ic, gen) if ic and gen else 0))
            except (ValueError, TypeError):
                continue
        return cls(years=years, interconnection_mw=interconnection,
                   generation_mw=generation, available_mw=available)

    @classmethod
    def generate_default(cls, target_mw: float, phase1_mw: float = None,
                         start_year: int = 2028, years: int = 8) -> 'CapacityTrajectory':
        if phase1_mw is None:
            phase1_mw = target_mw * 0.5
        year_list = list(range(start_year, start_year + years))
        interconnection, generation = [], []
        for i in range(len(year_list)):
            ic = phase1_mw * 0.5 if i == 0 else (phase1_mw if i == 1 else target_mw)
            gen = (phase1_mw * 0.3 if i == 0 else
                   (phase1_mw * 0.8 if i == 1 else
                    (phase1_mw if i == 2 else
                     (target_mw * 0.8 if i == 3 else target_mw))))
            interconnection.append(ic)
            generation.append(gen)
        available = [min(ic, gen) for ic, gen in zip(interconnection, generation)]
        return cls(years=year_list, interconnection_mw=interconnection,
                   generation_mw=generation, available_mw=available)


@dataclass
class ScoreAnalysis:
    """Site scoring analysis."""
    overall_score: float = 0
    power_pathway: float = 0
    site_specific: float = 0
    execution: float = 0
    relationship_capital: float = 0
    financial: float = 0

    # Sub-scores
    land_score: float = 0
    queue_score: float = 0
    water_score: float = 0
    fiber_score: float = 0


@dataclass
class RiskOpportunity:
    """Risk or opportunity item."""
    category: str  # 'risk' or 'opportunity'
    title: str
    description: str
    impact: str = 'Medium'  # Low, Medium, High
    mitigation: str = ''


@dataclass
class MarketAnalysis:
    """
    Market analysis data based on state analysis framework.
    
    Note: Queue time refers to GENERATION interconnection (bringing new power plants online),
    NOT large load interconnection for data center customers.
    """
    
    # Site's state info
    state_code: str = ''
    state_name: str = ''
    
    # ISO/Utility Profile
    primary_iso: str = ''
    regulatory_structure: str = ''  # regulated, deregulated, hybrid
    utility_name: str = ''
    avg_queue_time_months: int = 36  # Generation interconnection queue, NOT large load
    avg_industrial_rate: float = 0.0  # $/kWh
    renewable_percentage: float = 0
    
    # State scores (from StateProfile)
    overall_score: int = 0
    regulatory_score: int = 0
    transmission_score: int = 0
    power_score: int = 0
    water_score: int = 0
    business_score: int = 0
    ecosystem_score: int = 0
    tier: int = 3
    
    # Competitive landscape
    existing_dc_mw: int = 0
    hyperscaler_presence: List[str] = field(default_factory=list)
    fiber_density: str = ''
    
    # State SWOT
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    threats: List[str] = field(default_factory=list)
    
    # Comparison states (state_code: {name, queue_months, rate, score})
    comparison_states: Dict[str, Dict] = field(default_factory=dict)
    
    # Data center incentives
    incentives: List[str] = field(default_factory=list)
    
    # Known constraints
    known_moratoria: List[str] = field(default_factory=list)
    
    @classmethod
    def from_state_profile(cls, profile, utility_name: str = '', 
                           comparison_profiles: List = None) -> 'MarketAnalysis':
        """Create MarketAnalysis from StateProfile."""
        comparisons = {}
        if comparison_profiles:
            for cp in comparison_profiles:
                comparisons[cp.state_code] = {
                    'name': cp.state_name,
                    'queue_months': cp.avg_queue_time_months,
                    'rate': cp.avg_industrial_rate,
                    'score': cp.overall_score,
                    'tier': cp.tier,
                }
        
        return cls(
            state_code=profile.state_code,
            state_name=profile.state_name,
            primary_iso=profile.primary_iso,
            regulatory_structure=profile.regulatory_structure,
            utility_name=utility_name or profile.utility_type,
            avg_queue_time_months=profile.avg_queue_time_months,
            avg_industrial_rate=profile.avg_industrial_rate,
            renewable_percentage=profile.renewable_percentage,
            overall_score=profile.overall_score,
            regulatory_score=profile.regulatory_score,
            transmission_score=profile.transmission_score,
            power_score=profile.power_score,
            water_score=profile.water_score,
            business_score=profile.business_score,
            ecosystem_score=profile.ecosystem_score,
            tier=profile.tier,
            existing_dc_mw=profile.existing_dc_mw,
            hyperscaler_presence=profile.hyperscaler_presence,
            fiber_density=profile.fiber_density,
            strengths=profile.strengths,
            weaknesses=profile.weaknesses,
            opportunities=profile.opportunities,
            threats=profile.threats,
            comparison_states=comparisons,
            incentives=profile.data_center_incentives,
            known_moratoria=profile.known_moratoria,
        )


@dataclass
class ExportConfig:
    """Configuration for PPTX export."""
    include_capacity_trajectory: bool = True
    include_infrastructure: bool = True
    include_site_boundary: bool = True
    include_topography: bool = True
    include_score_analysis: bool = True
    include_market_analysis: bool = True
    contact_name: str = ""
    contact_title: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    custom_images: Dict[str, str] = field(default_factory=dict)
    chart_subtitle: str = "Anticipated Power Ramp (Pending Contract Study Results)"


# =============================================================================
# CHART GENERATION
# =============================================================================

def generate_capacity_trajectory_chart(
    trajectory: CapacityTrajectory,
    site_name: str,
    output_path: str,
    phases: List[PhaseData] = None,
    width: float = 11,
    height: float = 5.5,
    subtitle: str = "Anticipated Power Ramp (Pending Contract Study Results)",
) -> str:
    """Generate capacity trajectory chart with Interconnection vs Generation lines."""
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib required")

    fig, ax = plt.subplots(figsize=(width, height), facecolor='white')
    ax.set_facecolor('white')

    dates = [datetime(year, 1, 1) for year in trajectory.years]

    # Interconnection (teal)
    ax.plot(dates, trajectory.interconnection_mw, color=JLL_COLORS['teal'],
            linewidth=2.5, label='Utility Interconnection Rating', marker='o', markersize=4, zorder=3)

    # Generation (tan)
    ax.plot(dates, trajectory.generation_mw, color=JLL_COLORS['tan'],
            linewidth=2.5, label='Utility Generation Capacity', marker='s', markersize=4, zorder=2)

    # Max capacity annotation
    max_ic = max(trajectory.interconnection_mw)
    max_idx = trajectory.interconnection_mw.index(max_ic)
    label = f'Full {max_ic/1000:.1f}GW' if max_ic >= 1000 else f'Full {max_ic:.0f}MW'
    ax.annotate(label, xy=(dates[max_idx], max_ic), xytext=(dates[max_idx], max_ic * 1.05),
                fontsize=11, fontweight='bold', ha='center', color=JLL_COLORS['dark_blue'])

    # Styling
    ax.set_ylabel('Capacity (MW)', fontsize=12, fontweight='bold', color=JLL_COLORS['dark_blue'])
    ax.set_title('Capacity Trajectory', fontsize=16, fontweight='bold',
                 color=JLL_COLORS['dark_blue'], pad=20, loc='left')
    ax.text(0.0, 1.02, subtitle, transform=ax.transAxes, fontsize=10,
            ha='left', color=JLL_COLORS['medium_gray'])

    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    max_y = max(max(trajectory.interconnection_mw), max(trajectory.generation_mw)) * 1.15
    ax.set_ylim(0, max_y)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))

    ax.grid(True, axis='y', linestyle='-', alpha=0.3, color=JLL_COLORS['medium_gray'])
    ax.grid(True, axis='x', linestyle='-', alpha=0.2, color=JLL_COLORS['medium_gray'])
    ax.legend(loc='upper left', frameon=True, framealpha=0.9, fontsize=10)

    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    ax.spines['left'].set_color(JLL_COLORS['medium_gray'])
    ax.spines['bottom'].set_color(JLL_COLORS['medium_gray'])
    ax.tick_params(colors=JLL_COLORS['dark_gray'])

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    return output_path


def generate_critical_path_chart(
    phases: List[PhaseData],
    site_data: Dict,
    output_path: str,
    width: float = 11,
    height: float = 6,
) -> str:
    """Generate critical path and infrastructure summary."""
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib required")

    fig = plt.figure(figsize=(width, height), facecolor='white')
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1], wspace=0.3)

    # Left: Critical Path
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor('white')
    ax1.set_title('Critical Path to Power', fontsize=14, fontweight='bold',
                  color=JLL_COLORS['dark_blue'], loc='left', pad=10)

    y_pos = 0.95
    for phase in phases:
        ax1.text(0.02, y_pos, f"Phase {phase.phase_num}: {phase.target_mw:.0f} MW @ {phase.voltage_kv} kV",
                fontsize=11, fontweight='bold', color=JLL_COLORS['dark_blue'], transform=ax1.transAxes)
        y_pos -= 0.06
        ax1.text(0.04, y_pos, f"Target: {phase.target_online}",
                fontsize=9, color=JLL_COLORS['medium_gray'], transform=ax1.transAxes)
        y_pos -= 0.05

        items = [
            ('Screening Study', phase.screening_study),
            ('Contract Study', phase.contract_study),
            ('Letter of Agreement', phase.letter_of_agreement),
            ('Energy Contract', phase.energy_contract),
        ]
        for label, status in items:
            if status.lower() in ['complete', 'executed']:
                symbol, color = '✓', JLL_COLORS['green']
            elif status.lower() in ['drafted', 'initiated', 'in_progress', 'in progress']:
                symbol, color = '○', JLL_COLORS['amber']
            else:
                symbol, color = '□', JLL_COLORS['medium_gray']
            ax1.text(0.04, y_pos, symbol, fontsize=12, color=color, transform=ax1.transAxes)
            ax1.text(0.08, y_pos, f"{label}: {status}", fontsize=9,
                    color=JLL_COLORS['dark_gray'], transform=ax1.transAxes)
            y_pos -= 0.045
        y_pos -= 0.03
    ax1.axis('off')

    # Right: Infrastructure
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor('white')
    ax2.set_title('Infrastructure Readiness', fontsize=14, fontweight='bold',
                  color=JLL_COLORS['dark_blue'], loc='left', pad=10)

    categories = [
        ('Power', site_data.get('power_stage', 1), 4),
        ('Site Control', site_data.get('site_control_stage', 1), 4),
        ('Zoning', site_data.get('zoning_stage', 1), 3),
        ('Water', site_data.get('water_stage', 1), 4),
        ('Fiber', 3 if site_data.get('fiber_available') else 1, 4),
        ('Environmental', 4 if site_data.get('environmental_complete') else 2, 4),
    ]

    y_positions = list(range(len(categories) - 1, -1, -1))
    for i, (name, stage, max_stage) in enumerate(categories):
        pct = (stage / max_stage) * 100
        ax2.barh(y_positions[i], 100, height=0.6, color=JLL_COLORS['light_gray'], zorder=1)
        color = JLL_COLORS['green'] if pct >= 75 else (JLL_COLORS['amber'] if pct >= 50 else JLL_COLORS['teal'])
        ax2.barh(y_positions[i], pct, height=0.6, color=color, zorder=2)
        ax2.text(pct + 2, y_positions[i], f'{pct:.0f}%', va='center', fontsize=10,
                color=JLL_COLORS['dark_blue'], fontweight='bold')

    ax2.set_yticks(y_positions)
    ax2.set_yticklabels([c[0] for c in categories], fontsize=10)
    ax2.set_xlim(0, 115)
    for spine in ['top', 'right', 'bottom']:
        ax2.spines[spine].set_visible(False)
    ax2.tick_params(bottom=False, labelbottom=False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    return output_path


def generate_score_radar_chart(scores: ScoreAnalysis, site_name: str, output_path: str,
                                width: float = 6, height: float = 6) -> str:
    """Generate radar chart for site scores."""
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib required")

    categories = ['Power\nPathway', 'Site\nSpecific', 'Execution', 'Relationship\nCapital', 'Financial']
    values = [scores.power_pathway, scores.site_specific, scores.execution,
              scores.relationship_capital, scores.financial]

    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    values_closed = values + values[:1]
    angles_closed = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(width, height), subplot_kw=dict(polar=True), facecolor='white')
    
    # Fill area
    ax.fill(angles_closed, values_closed, color=JLL_COLORS['teal'], alpha=0.25)
    ax.plot(angles_closed, values_closed, color=JLL_COLORS['teal'], linewidth=2.5, marker='o', markersize=6)
    
    # Add value labels
    for angle, value, cat in zip(angles, values, categories):
        ax.annotate(f'{value:.0f}', xy=(angle, value), xytext=(angle, value + 8),
                   ha='center', fontsize=10, fontweight='bold', color=JLL_COLORS['dark_blue'])
    
    ax.set_xticks(angles)
    ax.set_xticklabels(categories, fontsize=11, color=JLL_COLORS['dark_gray'])
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(['25', '50', '75', '100'], fontsize=8, color=JLL_COLORS['medium_gray'])
    ax.grid(True, color=JLL_COLORS['medium_gray'], alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    return output_path


def generate_score_summary_chart(scores: ScoreAnalysis, site_name: str, output_path: str,
                                  width: float = 11, height: float = 6) -> str:
    """Generate comprehensive score summary with radar + details."""
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib required")

    fig = plt.figure(figsize=(width, height), facecolor='white')
    gs = fig.add_gridspec(1, 2, width_ratios=[1.2, 1], wspace=0.3)

    # Left: Radar chart
    ax1 = fig.add_subplot(gs[0, 0], polar=True)
    
    categories = ['Power\nPathway', 'Site\nSpecific', 'Execution', 'Relationship\nCapital', 'Financial']
    values = [scores.power_pathway, scores.site_specific, scores.execution,
              scores.relationship_capital, scores.financial]

    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    values_closed = values + values[:1]
    angles_closed = angles + angles[:1]

    ax1.fill(angles_closed, values_closed, color=JLL_COLORS['teal'], alpha=0.25)
    ax1.plot(angles_closed, values_closed, color=JLL_COLORS['teal'], linewidth=2.5, marker='o', markersize=6)
    
    for angle, value in zip(angles, values):
        ax1.annotate(f'{value:.0f}', xy=(angle, value), xytext=(angle, value + 10),
                    ha='center', fontsize=10, fontweight='bold', color=JLL_COLORS['dark_blue'])

    ax1.set_xticks(angles)
    ax1.set_xticklabels(categories, fontsize=10, color=JLL_COLORS['dark_gray'])
    ax1.set_ylim(0, 100)
    ax1.set_yticks([25, 50, 75, 100])
    ax1.grid(True, color=JLL_COLORS['medium_gray'], alpha=0.3)

    # Right: Score breakdown
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor('white')
    ax2.axis('off')

    # Overall score display
    ax2.text(0.5, 0.95, 'Overall Score', fontsize=14, fontweight='bold',
            color=JLL_COLORS['dark_blue'], ha='center', transform=ax2.transAxes)
    
    # Score circle
    score_color = JLL_COLORS['green'] if scores.overall_score >= 70 else (
        JLL_COLORS['amber'] if scores.overall_score >= 50 else JLL_COLORS['red'])
    circle = plt.Circle((0.5, 0.75), 0.15, color=score_color, alpha=0.2, transform=ax2.transAxes)
    ax2.add_patch(circle)
    ax2.text(0.5, 0.75, f'{scores.overall_score:.0f}', fontsize=36, fontweight='bold',
            color=score_color, ha='center', va='center', transform=ax2.transAxes)

    # Sub-scores
    sub_scores = [
        ('Power Pathway', scores.power_pathway, 0.30),
        ('Site Specific', scores.site_specific, 0.10),
        ('Execution', scores.execution, 0.20),
        ('Relationships', scores.relationship_capital, 0.35),
        ('Financial', scores.financial, 0.05),
    ]

    y_pos = 0.50
    ax2.text(0.1, y_pos + 0.05, 'Category', fontsize=10, fontweight='bold',
            color=JLL_COLORS['dark_blue'], transform=ax2.transAxes)
    ax2.text(0.55, y_pos + 0.05, 'Score', fontsize=10, fontweight='bold',
            color=JLL_COLORS['dark_blue'], ha='center', transform=ax2.transAxes)
    ax2.text(0.8, y_pos + 0.05, 'Weight', fontsize=10, fontweight='bold',
            color=JLL_COLORS['dark_blue'], ha='center', transform=ax2.transAxes)

    for name, score, weight in sub_scores:
        y_pos -= 0.08
        ax2.text(0.1, y_pos, name, fontsize=10, color=JLL_COLORS['dark_gray'], transform=ax2.transAxes)
        
        # Mini bar
        bar_width = score / 100 * 0.25
        ax2.barh(y_pos, bar_width, height=0.04, left=0.4, color=JLL_COLORS['teal'],
                transform=ax2.transAxes, zorder=2)
        ax2.barh(y_pos, 0.25, height=0.04, left=0.4, color=JLL_COLORS['light_gray'],
                transform=ax2.transAxes, zorder=1)
        
        ax2.text(0.68, y_pos, f'{score:.0f}', fontsize=10, va='center',
                color=JLL_COLORS['dark_blue'], transform=ax2.transAxes)
        ax2.text(0.8, y_pos, f'{weight*100:.0f}%', fontsize=10, va='center', ha='center',
                color=JLL_COLORS['medium_gray'], transform=ax2.transAxes)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    return output_path


def generate_market_analysis_chart(market_data: Dict, site_name: str, output_path: str,
                                    width: float = 11, height: float = 6.5) -> str:
    """
    Generate market analysis visualization using state analysis framework.
    
    Quadrants:
    - Top Left: State Comparison (queue times + costs)
    - Top Right: Competitive Landscape (DC MW, hyperscalers)
    - Bottom Left: ISO/Utility Profile
    - Bottom Right: State SWOT Summary
    """
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib required")

    fig = plt.figure(figsize=(width, height), facecolor='white')
    gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.25)

    # === TOP LEFT: State Comparison (New Generation Timeline) ===
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor('white')
    ax1.set_title('New Generation Capacity: State Comparison', fontsize=11, fontweight='bold',
                  color=JLL_COLORS['dark_blue'], loc='left', pad=8)
    
    # Get state data
    state_code = market_data.get('state_code', 'OK')
    state_name = market_data.get('state_name', 'State')
    queue_months = market_data.get('avg_queue_time_months', 36)
    rate = market_data.get('avg_industrial_rate', 0.06)
    comparisons = market_data.get('comparison_states', {})
    
    # Build comparison data
    states = [state_code]
    queues = [queue_months]
    rates = [rate * 100]  # Convert to cents/kWh
    colors = [JLL_COLORS['teal']]
    
    for code, data in comparisons.items():
        states.append(code)
        queues.append(data.get('queue_months', 36))
        rates.append(data.get('rate', 0.06) * 100)
        colors.append(JLL_COLORS['light_gray'])
    
    # Create dual bar chart
    x = np.arange(len(states))
    bar_width = 0.35
    
    bars1 = ax1.bar(x - bar_width/2, queues, bar_width, label='Gen. Queue (months)', 
                    color=[c if i == 0 else JLL_COLORS['teal'] for i, c in enumerate(colors)], alpha=0.8)
    
    ax1_twin = ax1.twinx()
    bars2 = ax1_twin.bar(x + bar_width/2, rates, bar_width, label='Power Cost (¢/kWh)',
                         color=[JLL_COLORS['tan'] if i == 0 else JLL_COLORS['tan'] for i in range(len(states))], alpha=0.7)
    
    ax1.set_xticks(x)
    ax1.set_xticklabels(states, fontsize=10)
    ax1.set_ylabel('Gen. Interconnection (months)', fontsize=9, color=JLL_COLORS['teal'])
    ax1_twin.set_ylabel('Power Cost (¢/kWh)', fontsize=9, color=JLL_COLORS['tan'])
    
    # Add value labels
    for bar, val in zip(bars1, queues):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f'{val}',
                ha='center', fontsize=8, color=JLL_COLORS['dark_blue'])
    for bar, val in zip(bars2, rates):
        ax1_twin.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, f'{val:.1f}¢',
                     ha='center', fontsize=8, color=JLL_COLORS['dark_gray'])
    
    ax1.spines['top'].set_visible(False)
    ax1_twin.spines['top'].set_visible(False)
    ax1.legend(loc='upper left', fontsize=8, frameon=False)
    ax1_twin.legend(loc='upper right', fontsize=8, frameon=False)

    # === TOP RIGHT: Competitive Landscape ===
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor('white')
    ax2.axis('off')
    ax2.set_title('Competitive Landscape', fontsize=11, fontweight='bold',
                  color=JLL_COLORS['dark_blue'], loc='left', pad=8)
    
    existing_mw = market_data.get('existing_dc_mw', 0)
    hyperscalers = market_data.get('hyperscaler_presence', [])
    fiber = market_data.get('fiber_density', 'medium')
    
    # DC Capacity indicator
    ax2.text(0.05, 0.85, 'Existing DC Capacity:', fontsize=10, fontweight='bold',
            color=JLL_COLORS['dark_gray'], transform=ax2.transAxes)
    ax2.text(0.55, 0.85, f'{existing_mw:,} MW', fontsize=12, fontweight='bold',
            color=JLL_COLORS['teal'], transform=ax2.transAxes)
    
    # Fiber density
    ax2.text(0.05, 0.72, 'Fiber Density:', fontsize=10, fontweight='bold',
            color=JLL_COLORS['dark_gray'], transform=ax2.transAxes)
    fiber_color = JLL_COLORS['green'] if fiber == 'high' else (JLL_COLORS['amber'] if fiber == 'medium' else JLL_COLORS['red'])
    ax2.text(0.55, 0.72, fiber.title(), fontsize=10, fontweight='bold',
            color=fiber_color, transform=ax2.transAxes)
    
    # Hyperscaler presence
    ax2.text(0.05, 0.55, 'Hyperscaler Presence:', fontsize=10, fontweight='bold',
            color=JLL_COLORS['dark_gray'], transform=ax2.transAxes)
    
    y_pos = 0.42
    if hyperscalers:
        for hs in hyperscalers[:5]:
            ax2.text(0.08, y_pos, f'• {hs}', fontsize=9, color=JLL_COLORS['dark_gray'],
                    transform=ax2.transAxes)
            y_pos -= 0.10
    else:
        ax2.text(0.08, y_pos, '• Limited presence', fontsize=9, color=JLL_COLORS['medium_gray'],
                transform=ax2.transAxes)

    # === BOTTOM LEFT: ISO/Utility Profile ===
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.set_facecolor('white')
    ax3.axis('off')
    ax3.set_title('ISO & Utility Profile', fontsize=11, fontweight='bold',
                  color=JLL_COLORS['dark_blue'], loc='left', pad=8)
    
    profile_items = [
        ('Primary ISO', market_data.get('primary_iso', 'N/A')),
        ('Regulatory Structure', market_data.get('regulatory_structure', 'N/A').title()),
        ('Utility', market_data.get('utility_name', 'N/A')),
        ('Gen. Queue Time', f"{market_data.get('avg_queue_time_months', 'N/A')} months"),
        ('Industrial Rate', f"{market_data.get('avg_industrial_rate', 0)*100:.1f} ¢/kWh"),
        ('Renewable Mix', f"{market_data.get('renewable_percentage', 0):.0f}%"),
        ('State Tier', f"Tier {market_data.get('tier', 3)}"),
        ('Overall Score', f"{market_data.get('overall_score', 0)}/100"),
    ]
    
    y_pos = 0.88
    for label, value in profile_items:
        ax3.text(0.05, y_pos, f'{label}:', fontsize=9, fontweight='bold',
                color=JLL_COLORS['dark_gray'], transform=ax3.transAxes)
        ax3.text(0.50, y_pos, str(value), fontsize=9,
                color=JLL_COLORS['dark_blue'], transform=ax3.transAxes)
        y_pos -= 0.11
    
    # Incentives if available
    incentives = market_data.get('incentives', [])
    if incentives:
        ax3.text(0.05, y_pos - 0.02, 'Key Incentives:', fontsize=9, fontweight='bold',
                color=JLL_COLORS['dark_gray'], transform=ax3.transAxes)
        y_pos -= 0.12
        for inc in incentives[:2]:
            ax3.text(0.07, y_pos, f'• {inc[:40]}...', fontsize=8, 
                    color=JLL_COLORS['medium_gray'], transform=ax3.transAxes)
            y_pos -= 0.08

    # === BOTTOM RIGHT: State SWOT Summary ===
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_facecolor('white')
    ax4.axis('off')
    ax4.set_title(f'{state_name} SWOT Summary', fontsize=11, fontweight='bold',
                  color=JLL_COLORS['dark_blue'], loc='left', pad=8)
    
    strengths = market_data.get('strengths', [])
    weaknesses = market_data.get('weaknesses', [])
    opportunities = market_data.get('opportunities', [])
    threats = market_data.get('threats', [])
    
    # Two columns
    y_pos = 0.88
    
    # Strengths
    ax4.text(0.02, y_pos, 'Strengths', fontsize=9, fontweight='bold',
            color=JLL_COLORS['green'], transform=ax4.transAxes)
    y_pos -= 0.08
    for s in strengths[:2]:
        ax4.text(0.02, y_pos, f'+ {s[:25]}', fontsize=8, color=JLL_COLORS['dark_gray'],
                transform=ax4.transAxes)
        y_pos -= 0.07
    
    # Weaknesses
    y_pos -= 0.03
    ax4.text(0.02, y_pos, 'Weaknesses', fontsize=9, fontweight='bold',
            color=JLL_COLORS['red'], transform=ax4.transAxes)
    y_pos -= 0.08
    for w in weaknesses[:2]:
        ax4.text(0.02, y_pos, f'- {w[:25]}', fontsize=8, color=JLL_COLORS['dark_gray'],
                transform=ax4.transAxes)
        y_pos -= 0.07
    
    # Opportunities (right column)
    y_pos = 0.88
    ax4.text(0.52, y_pos, 'Opportunities', fontsize=9, fontweight='bold',
            color=JLL_COLORS['teal'], transform=ax4.transAxes)
    y_pos -= 0.08
    for o in opportunities[:2]:
        ax4.text(0.52, y_pos, f'↑ {o[:23]}', fontsize=8, color=JLL_COLORS['dark_gray'],
                transform=ax4.transAxes)
        y_pos -= 0.07
    
    # Threats
    y_pos -= 0.03
    ax4.text(0.52, y_pos, 'Threats', fontsize=9, fontweight='bold',
            color=JLL_COLORS['amber'], transform=ax4.transAxes)
    y_pos -= 0.08
    for t in threats[:2]:
        ax4.text(0.52, y_pos, f'! {t[:23]}', fontsize=8, color=JLL_COLORS['dark_gray'],
                transform=ax4.transAxes)
        y_pos -= 0.07

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    return output_path


# =============================================================================
# SLIDE HELPERS
# =============================================================================

def set_slide_background_white(slide, Inches, RGBColor):
    """Set slide background to white."""
    from pptx.enum.dml import MSO_THEME_COLOR
    from pptx.oxml.ns import qn
    from pptx.oxml import parse_xml
    
    # Access the slide's spTree and add a background
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(255, 255, 255)


def add_header_bar(slide, title_text: str, Inches, Pt, RGBColor):
    """Add dark blue header bar."""
    from pptx.enum.shapes import MSO_SHAPE

    header = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0),
                                     Inches(13.33), Inches(0.6))
    header.fill.solid()
    header.fill.fore_color.rgb = RGBColor.from_string(JLL_COLORS['dark_blue'][1:])
    header.line.fill.background()

    title_box = slide.shapes.add_textbox(Inches(0.4), Inches(0.12), Inches(10), Inches(0.4))
    p = title_box.text_frame.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = RGBColor.from_string('ffffff')


def add_footer(slide, page_num: int, Inches, Pt, RGBColor):
    """Add JLL footer."""
    footer = slide.shapes.add_textbox(Inches(0.4), Inches(7.2), Inches(10), Inches(0.25))
    p = footer.text_frame.paragraphs[0]
    p.text = f"© {datetime.now().year} Jones Lang LaSalle IP, Inc. All rights reserved  |  {page_num}"
    p.font.size = Pt(8)
    p.font.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])


def find_and_replace_text(shape, replacements: Dict[str, str]) -> bool:
    """Find and replace text in shape."""
    if not shape.has_text_frame:
        return False
    replaced = False
    for para in shape.text_frame.paragraphs:
        for run in para.runs:
            for old, new in replacements.items():
                if old in run.text:
                    run.text = run.text.replace(old, new)
                    replaced = True
    return replaced


def replace_in_table(table, replacements: Dict[str, str]) -> bool:
    """Replace text in table cells."""
    replaced = False
    for row in table.rows:
        for cell in row.cells:
            if cell.text_frame:
                for para in cell.text_frame.paragraphs:
                    for run in para.runs:
                        for old, new in replacements.items():
                            if old in run.text:
                                run.text = run.text.replace(old, new)
                                replaced = True
    return replaced


def build_replacements(site_data: Dict, config: ExportConfig) -> Dict[str, str]:
    """Build replacement dictionary."""
    target_mw = site_data.get('target_mw', 0)
    mw_display = f"{target_mw/1000:.1f}GW" if target_mw >= 1000 else f"{target_mw:.0f}MW"

    replacements = {
        'SITE NAME': site_data.get('name', 'Site Name'),
        '[STATE]': site_data.get('state', 'State'),
        'December 2, 2025': datetime.now().strftime('%B %d, %Y'),
        '[Coordinates linked]': f"{site_data.get('latitude', 'N/A')}, {site_data.get('longitude', 'N/A')}",
        '1GW+': mw_display,
        'Estimated 1GW+': f"Estimated {mw_display}",
        'NAME': config.contact_name or site_data.get('contact_name', 'Contact Name'),
        'TITLE': config.contact_title or site_data.get('contact_title', 'Title'),
        'Phone': config.contact_phone or site_data.get('contact_phone', 'Phone'),
        'Email': config.contact_email or site_data.get('contact_email', 'email@jll.com'),
    }

    if site_data.get('utility'):
        replacements['OG&E 345kV line'] = site_data['utility']
    if site_data.get('total_acres'):
        replacements['1,250 acres'] = f"{site_data['total_acres']:,.0f} acres"
    if site_data.get('water_capacity'):
        replacements['3M GDP capacity'] = site_data['water_capacity']
    if site_data.get('overview'):
        replacements['1,250 acre site with significant growth opportunity located between Tulsa and Oklahoma City.'] = site_data['overview']

    return replacements


def get_rating_color(rating: str) -> tuple:
    """Get RGB color tuple for rating."""
    from pptx.dml.color import RGBColor
    
    rating_upper = rating.upper()
    if rating_upper in ['DESIRABLE', 'GREEN']:
        return RGBColor.from_string(JLL_COLORS['green'][1:])
    elif rating_upper in ['ACCEPTABLE', 'YELLOW']:
        return RGBColor.from_string(JLL_COLORS['yellow'][1:])
    elif rating_upper in ['MARGINAL', 'ORANGE']:
        return RGBColor.from_string(JLL_COLORS['orange'][1:])
    elif rating_upper in ['FATAL FLAW', 'RED']:
        return RGBColor.from_string(JLL_COLORS['red'][1:])
    else:  # N/R or unknown
        return RGBColor.from_string(JLL_COLORS['rating_gray'][1:])


def populate_site_profile_table(presentation, site_data: Dict):
    """Populate the Site Profile table (slide 1) with actual site data."""
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    
    # Get Site Profile slide (slide index 1)
    if len(presentation.slides) < 2:
        return
    
    slide = presentation.slides[1]
    
    # Find the table in the slide
    table = None
    for shape in slide.shapes:
        if shape.has_table:
            table = shape.table
            break
    
    if not table or len(table.rows) < 15:
        return  # Table not found or wrong format
    
    # Extract site data with defaults
    def safe_get(d, *keys, default='TBD'):
        """Safely get nested dictionary values."""
        for key in keys:
            if isinstance(d, dict):
                d = d.get(key, {})
            else:
                return default
        return d if d and d != {} else default
    
    # Build rating data from site
    rating_rows = [
        {
            'item': 'Location',
            'preference': 'Proximity and Surroundings',
            'rating': safe_get(site_data, 'location_rating', default='N/R'),
            'description': f"• Nearest Town: {safe_get(site_data, 'nearest_town')}\n"
                          f"• Distance to Large City: {safe_get(site_data, 'distance_to_city')}\n"
                          f"• Neighboring Uses: {safe_get(site_data, 'neighboring_uses', default='Mostly Agricultural')}"
        },
        {
            'item': 'Ownership &\nAsking Price',
            'preference': 'Single Owner',
            'rating': safe_get(site_data, 'ownership_rating', default='N/R'),
            'description': f"• Owner(s): {safe_get(site_data, 'developer', default='TBD')}\n"
                          f"• Asking Price: {safe_get(site_data, 'asking_price', default='TBD')}"
        },
        {
            'item': 'Size / Shape /\nDimensions',
            'preference': f"{site_data.get('acreage', '1000')} acres",
            'rating': safe_get(site_data, 'size_rating', default='N/R'),
            'description': f"• Total Size: {site_data.get('acreage', 'TBD')} acres\n"
                          f"• Dimensions: {safe_get(site_data, 'dimensions', default='TBD')}\n"
                          f"• Expandable: {safe_get(site_data, 'expandable', default='TBD')}"
        },
        {
            'item': 'Zoning',
            'preference': 'Data Center Compatible',
            'rating': safe_get(site_data, 'zoning_rating', default='N/R'),
            'description': f"• Zoning: {safe_get(site_data, 'non_power', 'zoning_status', default='TBD')}\n"
                          f"• Site condition: {safe_get(site_data, 'site_condition', default='TBD')}"
        },
        {
            'item': 'Timing',
            'preference': 'Transfer by Q1 2026',
            'rating': safe_get(site_data, 'timing_rating', default='N/R'),
            'description': f"• Transfer timeline: {safe_get(site_data, 'transfer_timeline', default='TBD')}"
        },
        {
            'item': 'Geotechnical\nand Topography',
            'preference': 'Generally Flat with\nGood Soils',
            'rating': safe_get(site_data, 'geotech_rating', default='N/R'),
            'description': f"• Soil type: {safe_get(site_data, 'soil_type', default='TBD')}\n"
                          f"• Topography: {safe_get(site_data, 'topography', default='TBD')}\n"
                          f"• Elevation change: {safe_get(site_data, 'elevation_change', default='TBD')}"
        },
        {
            'item': 'Environmental,\nEcological,\nArcheological',
            'preference': 'No Barriers to\nConstruction',
            'rating': safe_get(site_data, 'environmental_rating', default='N/R'),
            'description': f"• Environmental: {safe_get(site_data, 'non_power', 'env_issues', default='TBD')}\n"
                          f"• Ecological: {safe_get(site_data, 'ecological_concerns', default='TBD')}\n"
                          f"• Archeological: {safe_get(site_data, 'archeological_concerns', default='TBD')}"
        },
        {
            'item': 'Wetlands and\nJurisdictional\nWater',
            'preference': 'No Wetlands or\nJurisdictional Water',
            'rating': safe_get(site_data, 'wetlands_rating', default='N/R'),
            'description': f"• Wetlands: {safe_get(site_data, 'wetlands_present', default='TBD')}\n"
                          f"• Water Features: {safe_get(site_data, 'water_features', default='TBD')}"
        },
        {
            'item': 'Disaster',
            'preference': 'Outside Zone of Risk',
            'rating': safe_get(site_data, 'disaster_rating', default='N/R'),
            'description': f"• Flood: {safe_get(site_data, 'flood_risk', default='TBD')}\n"
                          f"• Seismic: {safe_get(site_data, 'seismic_risk', default='TBD')}"
        },
        {
            'item': 'Easements',
            'preference': 'No Utility Easements or\nROW',
            'rating': safe_get(site_data, 'easements_rating', default='N/R'),
            'description': f"• Utility easements: {safe_get(site_data, 'utility_easements', default='TBD')}\n"
                          f"• ROW: {safe_get(site_data, 'row_easements', default='TBD')}"
        },
        {
            'item': 'Electricity',
            'preference': f"{site_data.get('target_mw', '300')} MW+",
            'rating': safe_get(site_data, 'electricity_rating', default='N/R'),
            'description': f"• Available capacity: {site_data.get('target_mw', 'TBD')} MW\n"
                          f"• Service type: {safe_get(site_data, 'phases', 0, 'service_type', default='TBD') if site_data.get('phases') else 'TBD'}"
        },
        {
            'item': 'Water',
            'preference': '1M GPD+',
            'rating': safe_get(site_data, 'water_rating', default='N/R'),
            'description': f"• Water source: {safe_get(site_data, 'non_power', 'water_source', default='TBD')}\n"
                          f"• Capacity: {safe_get(site_data, 'non_power', 'water_cap', default='TBD')} GPD"
        },
        {
            'item': 'Wastewater',
            'preference': '300K GPD+',
            'rating': safe_get(site_data, 'wastewater_rating', default='N/R'),
            'description': f"• Wastewater solution: {safe_get(site_data, 'wastewater_solution', default='TBD')}"
        },
        {
            'item': 'Telecom',
            'preference': 'High Bandwidth Fiber',
            'rating': safe_get(site_data, 'telecom_rating', default='N/R'),
            'description': f"• Fiber status: {safe_get(site_data, 'non_power', 'fiber_status', default='TBD')}\n"
                          f"• Provider: {safe_get(site_data, 'non_power', 'fiber_provider', default='TBD')}"
        },
    ]
    
    # Populate table rows
    for row_idx, row_data in enumerate(rating_rows, start=1):
        if row_idx >= len(table.rows):
            break
        
        # Update preference (column 1)
        table.cell(row_idx, 1).text = row_data['preference']
        
        # Update rating (column 2) with color
        rating_cell = table.cell(row_idx, 2)
        rating_cell.text = row_data['rating']
        rating_cell.fill.solid()
        rating_cell.fill.fore_color.rgb = get_rating_color(row_data['rating'])
        
        # Update description (column 3)
        table.cell(row_idx, 3).text = row_data['description']



# =============================================================================
# MAIN EXPORT
# =============================================================================

def export_site_to_pptx(
    site_data: Dict,
    template_path: str,
    output_path: str,
    config: ExportConfig = None,
) -> str:
    """Export site data to PowerPoint."""
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.enum.text import PP_ALIGN
    except ImportError:
        raise ImportError("python-pptx required")

    config = config or ExportConfig()
    prs = Presentation(template_path)
    replacements = build_replacements(site_data, config)

    # Process existing slides
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_table:
                replace_in_table(shape.table, replacements)
            elif shape.has_text_frame:
                find_and_replace_text(shape, replacements)
    
    # Populate Site Profile table with actual data
    populate_site_profile_table(prs, site_data)

    # Find blank layout
    blank_layout = None
    for layout in prs.slide_layouts:
        if 'blank' in layout.name.lower():
            blank_layout = layout
            break
    blank_layout = blank_layout or prs.slide_layouts[-1]

    # Get trajectory and phases
    trajectory = None
    if config.include_capacity_trajectory and MATPLOTLIB_AVAILABLE:
        traj_data = site_data.get('capacity_trajectory', {})
        trajectory = (CapacityTrajectory.from_dict(traj_data) if traj_data else
                      CapacityTrajectory.generate_default(
                          site_data.get('target_mw', 600),
                          site_data.get('phase1_mw'),
                          site_data.get('start_year', 2028)))

    phases = []
    phase_data = site_data.get('phases', [])
    if phase_data:
        for pd in phase_data:
            phases.append(PhaseData(**pd) if isinstance(pd, dict) else pd)
    else:
        target_mw = site_data.get('target_mw', 600)
        phase1_mw = site_data.get('phase1_mw', min(100, target_mw * 0.2))
        phases = [
            PhaseData(1, phase1_mw, 138, site_data.get('phase1_online', '2028-01-01'),
                      site_data.get('screening_study', 'Complete'),
                      site_data.get('contract_study', 'In Progress'),
                      site_data.get('loa_status', 'Not Started'),
                      site_data.get('energy_contract', 'Not Started')),
            PhaseData(2, target_mw, 345, site_data.get('phase2_online', '2029-01-01'),
                      site_data.get('phase2_screening', 'Complete'),
                      site_data.get('phase2_contract_study', 'Not Started')),
        ]

    # ADD SLIDE: Capacity Trajectory (WHITE background)
    if config.include_capacity_trajectory and trajectory:
        slide = prs.slides.add_slide(blank_layout)
        
        # Set white background explicitly
        set_slide_background_white(slide, Inches, RGBColor)
        
        add_header_bar(slide, f"{site_data.get('name', 'Site')}: Capacity Trajectory",
                      Inches, Pt, RGBColor)

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            chart_path = tmp.name
        generate_capacity_trajectory_chart(trajectory, site_data.get('name', 'Site'),
                                           chart_path, phases, subtitle=config.chart_subtitle)
        slide.shapes.add_picture(chart_path, Inches(0.4), Inches(0.8), width=Inches(12.5))
        add_footer(slide, 5, Inches, Pt, RGBColor)
        os.unlink(chart_path)

    # ADD SLIDE: Infrastructure & Critical Path (WHITE background) - NATIVE POWERPOINT
    if config.include_infrastructure:
        slide = prs.slides.add_slide(blank_layout)
        
        # Set white background explicitly
        set_slide_background_white(slide, Inches, RGBColor)
        
        add_header_bar(slide, "Infrastructure & Critical Path", Inches, Pt, RGBColor)

        # === LEFT PANEL: Critical Path Text ===
        left_panel = slide.shapes.add_textbox(Inches(0.5), Inches(1.0), Inches(6.0), Inches(5.5))
        tf = left_panel.text_frame
        tf.word_wrap = True
        
        # Title
        p = tf.paragraphs[0]
        p.text = "Critical Path to Power"
        p.font.size = Pt(20)
        p.font.bold = True
        p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_blue'][1:])
        p.space_after = Pt(12)
        
        # Add phase information
        for i, phase in enumerate(phases[:2]):  # Show first 2 phases
            # Phase header
            p = tf.add_paragraph()
            p.text = f"Phase {phase.phase_num}: {int(phase.target_mw)} MW @ {phase.voltage_kv} kV"
            p.font.size = Pt(16)
            p.font.bold = True
            p.font.color.rgb = RGBColor.from_string(JLL_COLORS['teal'][1:])
            p.space_after = Pt(6)
            
            # Target date
            p = tf.add_paragraph()
            p.text = f"Target: {phase.target_online}"
            p.font.size = Pt(12)
            p.font.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])
            p.space_after = Pt(8)
            
            # Study statuses with symbols
            studies = [
                ('Screening Study', phase.screening_study),
                ('Contract Study', phase.contract_study),
                ('Letter of Agreement', phase.letter_of_agreement),
                ('Energy Contract', phase.energy_contract),
            ]
            
            for study_name, status in studies:
                p = tf.add_paragraph()
                # Add status symbol
                if status.lower() in ['complete', 'executed']:
                    symbol = '✓ '
                    color = RGBColor.from_string(JLL_COLORS['green'][1:])
                elif status.lower() in ['drafted', 'initiated', 'in_progress', 'in progress']:
                    symbol = '○ '
                    color = RGBColor.from_string(JLL_COLORS['yellow'][1:])
                else:
                    symbol = '□ '
                    color = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])
                
                # Symbol run
                run = p.runs[0] if p.runs else p.add_run()
                run.text = symbol
                run.font.size = Pt(11)
                run.font.color.rgb = color
                run.font.bold = True
                
                # Status text run
                run = p.add_run()
                run.text = f"{study_name}: {status}"
                run.font.size = Pt(12)
                run.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_gray'][1:])
                
                p.space_after = Pt(5)
            
            p.space_after = Pt(8)
        
        # Add key risks at bottom
        p = tf.add_paragraph()
        p.text = "Key Risks: "
        p.font.size = Pt(8)
        p.font.italic = True
        p.font.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])
        
        risks = site_data.get('risks', [])
        if risks:
            run = p.add_run()
            run.text = ', '.join(risks[:2])
            run.font.size = Pt(8)
            run.font.italic = True
        
        # === RIGHT PANEL: Infrastructure Readiness Bar Chart (Native) ===
        right_title = slide.shapes.add_textbox(Inches(7.0), Inches(1.0), Inches(5.5), Inches(0.4))
        p = right_title.text_frame.paragraphs[0]
        p.text = "Infrastructure Readiness"
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_blue'][1:])
        
        # Infrastructure categories and scores
        categories = [
            ('Power', site_data.get('power_stage', 1), 4),
            ('Site Control', site_data.get('site_control_stage', 1), 4),
            ('Zoning', site_data.get('zoning_stage', 1), 3),
            ('Water', site_data.get('water_stage', 1), 4),
            ('Fiber', 3 if site_data.get('fiber_available') else 1, 4),
            ('Environmental', 4 if site_data.get('environmental_complete') else 2, 4),
        ]
        
        # Draw bars manually with shapes
        bar_y_start = Inches(1.6)
        bar_height = Inches(0.5)
        bar_spacing = Inches(0.7)
        bar_max_width = Inches(4.5)
        bar_x_start = Inches(7.8)
        
        for i, (name, stage, max_stage) in enumerate(categories):
            y_pos = bar_y_start + (i * bar_spacing)
            pct = (stage / max_stage) * 100
            
            # Category label
            label_box = slide.shapes.add_textbox(Inches(7.0), y_pos + Inches(0.1), Inches(0.7), Inches(0.3))
            p = label_box.text_frame.paragraphs[0]
            p.text = name
            p.font.size = Pt(10)
            p.font.bold = False
            p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_gray'][1:])
            p.alignment = PP_ALIGN.RIGHT
            
            # Background bar (light gray)
            bg_bar = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                bar_x_start, y_pos,
                bar_max_width, bar_height
            )
            bg_bar.fill.solid()
            bg_bar.fill.fore_color.rgb = RGBColor(240, 240, 240)
            bg_bar.line.fill.background()
            
            # Foreground bar (colored by percentage)
            if pct >= 75:
                bar_color = RGBColor.from_string(JLL_COLORS['green'][1:])
            elif pct >= 50:
                bar_color = RGBColor.from_string(JLL_COLORS['yellow'][1:])
            else:
                bar_color = RGBColor.from_string(JLL_COLORS['teal'][1:])
            
            fg_bar = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                bar_x_start, y_pos,
                bar_max_width * (pct / 100), bar_height
            )
            fg_bar.fill.solid()
            fg_bar.fill.fore_color.rgb = bar_color
            fg_bar.line.fill.background()
            
            # Percentage label
            pct_label = slide.shapes.add_textbox(
                bar_x_start + bar_max_width + Inches(0.1), 
                y_pos + Inches(0.05), 
                Inches(0.6), Inches(0.4)
            )
            p = pct_label.text_frame.paragraphs[0]
            p.text = f"{int(pct)}%"
            p.font.size = Pt(11)
            p.font.bold = True
            p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_blue'][1:])

        add_footer(slide, 6, Inches, Pt, RGBColor)

    # ADD SLIDE: Score Analysis (WHITE background)
    if config.include_score_analysis and MATPLOTLIB_AVAILABLE:
        slide = prs.slides.add_slide(blank_layout)
        set_slide_background_white(slide, Inches, RGBColor)
        add_header_bar(slide, "Site Score Analysis", Inches, Pt, RGBColor)
        
        # Get or create scores
        scores_data = site_data.get('scores', {})
        scores = ScoreAnalysis(
            overall_score=scores_data.get('overall', site_data.get('overall_score', 65)),
            power_pathway=scores_data.get('power_pathway', site_data.get('power_score', 70)),
            site_specific=scores_data.get('site_specific', site_data.get('site_score', 60)),
            execution=scores_data.get('execution', site_data.get('execution_score', 55)),
            relationship_capital=scores_data.get('relationship_capital', site_data.get('relationship_score', 50)),
            financial=scores_data.get('financial', site_data.get('financial_score', 75)),
            land_score=scores_data.get('land', 0),
            queue_score=scores_data.get('queue', 0),
            water_score=scores_data.get('water', 0),
            fiber_score=scores_data.get('fiber', 0),
        )
        
        # Generate simplified radar chart (matplotlib)
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            score_path = tmp.name
        generate_score_radar_chart(scores, site_data.get('name', 'Site'), score_path)
        
        # Add radar chart on left side
        slide.shapes.add_picture(score_path, Inches(0.5), Inches(1.2), width=Inches(5.5))
        
        # === RIGHT SIDE: Overall Score + Breakdown Table ===
        # Overall Score display
        overall_box = slide.shapes.add_textbox(Inches(7.0), Inches(1.2), Inches(5.5), Inches(1.2))
        tf = overall_box.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = "Overall Score"
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = RGBColor.from_string(JLL_COLORS['teal'][1:])
        p.alignment = PP_ALIGN.CENTER
        p.space_after = Pt(8)
        
        p = tf.add_paragraph()
        p.text = f"{int(scores.overall_score)}"
        p.font.size = Pt(48)
        p.font.bold = True
        p.font.color.rgb = RGBColor.from_string(JLL_COLORS['green'][1:])
        p.alignment = PP_ALIGN.CENTER
        
        # Category breakdown table
        table_top = Inches(2.6)
        table_data = [
            ("Category", "Score", "Weight"),
            ("Power Pathway", f"{int(scores.power_pathway)}", "30%"),
            ("Site Specific", f"{int(scores.site_specific)}", "10%"),
            ("Execution", f"{int(scores.execution)}", "20%"),
            ("Relationships", f"{int(scores.relationship_capital)}", "35%"),
            ("Financial", f"{int(scores.financial)}", "5%"),
        ]
        
        # Create table
        rows, cols = len(table_data), 3
        score_table = slide.shapes.add_table(rows, cols, Inches(7.0), table_top, Inches(5.5), Inches(3.5)).table
        
        # Set column widths
        score_table.columns[0].width = Inches(2.8)
        score_table.columns[1].width = Inches(1.3)
        score_table.columns[2].width = Inches(1.4)
        
        # Populate table
        for row_idx, (category, score, weight) in enumerate(table_data):
            for col_idx, text in enumerate([category, score, weight]):
                cell = score_table.cell(row_idx, col_idx)
                cell.text = text
                
                # Header row styling
                if row_idx == 0:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = RGBColor.from_string(JLL_COLORS['teal'][1:])
                    for paragraph in cell.text_frame.paragraphs:
                        paragraph.font.size = Pt(11)
                        paragraph.font.bold = True
                        paragraph.font.color.rgb = RGBColor(255, 255, 255)
                        paragraph.alignment = PP_ALIGN.CENTER
                else:
                    # Data rows
                    for paragraph in cell.text_frame.paragraphs:
                        paragraph.font.size = Pt(10)
                        paragraph.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_gray'][1:])
                        if col_idx == 0:
                            paragraph.alignment = PP_ALIGN.LEFT
                        else:
                            paragraph.alignment = PP_ALIGN.CENTER
                            paragraph.font.bold = True
        
        add_footer(slide, 7, Inches, Pt, RGBColor)
        os.unlink(score_path)

    # ADD SLIDE: Market Analysis (WHITE background) - NATIVE 4-QUADRANT LAYOUT
    if config.include_market_analysis:
        slide = prs.slides.add_slide(blank_layout)
        set_slide_background_white(slide, Inches, RGBColor)
        add_header_bar(slide, "Market Analysis", Inches, Pt, RGBColor)
        
        # Build market data from site_data
        state_code = site_data.get('state_code', site_data.get('state', 'OK')[:2].upper())
        
        # State defaults
        site_state_defaults = {
            'OK': {'iso': 'SPP', 'reg': 'Regulated', 'utility': 'OG&E', 'queue': 30, 'rate': 5.5, 'renew': 42,
                   'score': 84.5, 'tier': 1, 'dc_mw': 500, 'fiber': 'Medium',
                   'hyperscalers': ['Google (Pryor)', 'Meta (announced)'],
                   'strengths': ['Pro-business PSC', 'Low power costs'],
                   'weaknesses': ['Limited DC ecosystem', 'Water constraints'],
                   'opportunities': ['Hyperscaler expansion', 'Tulsa hub growth'],
                   'threats': ['Grid congestion', 'Water rights competition'],
                   'incentives': ['Sales tax exemption', 'Property tax abatement']},
            'TX': {'iso': 'ERCOT', 'reg': 'Deregulated', 'utility': 'Oncor', 'queue': 36, 'rate': 6.5, 'renew': 35,
                   'score': 77.2, 'tier': 1, 'dc_mw': 3000, 'fiber': 'High',
                   'hyperscalers': ['Google', 'Microsoft', 'Meta', 'AWS', 'Oracle'],
                   'strengths': ['No state income tax', 'Massive ecosystem'],
                   'weaknesses': ['Grid reliability', 'Water stress'],
                   'opportunities': ['Continued growth', 'West Texas expansion'],
                   'threats': ['Grid instability', 'Water availability'],
                   'incentives': ['Chapter 313 replacement', 'Property tax limits']},
        }
        
        defaults = site_state_defaults.get(state_code, site_state_defaults.get('OK'))
        state_name = site_data.get('state', defaults.get('name', 'State'))
        
        
        # === TOP-LEFT QUADRANT: State Comparison Chart ===
        if MATPLOTLIB_AVAILABLE:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')
            
            # State comparison data
            states_data = [
                (state_code, defaults.get('queue', 30), defaults.get('rate', 5.5)),
                ('TX', 36, 6.5),
                ('GA', 42, 7.2),
                ('OH', 36, 6.8),
            ]
            
            states = [s[0] for s in states_data[:4]]
            queue_months = [s[1] for s in states_data[:4]]
            power_rates = [s[2] for s in states_data[:4]]
            
            # Create bar chart
            fig, ax1 = plt.subplots(figsize=(5.5, 2.8))
            
            x = range(len(states))
            width = 0.35
            
            # Queue months bars
            bars1 = ax1.bar([i - width/2 for i in x], queue_months, width, 
                           color=JLL_COLORS['teal'], label='Gen. Queue (months)', alpha=0.8)
            ax1.set_ylabel('Gen. Interconnection (months)', fontsize=9, color=JLL_COLORS['teal'])
            ax1.tick_params(axis='y', labelcolor=JLL_COLORS['teal'], labelsize=8)
            ax1.set_ylim(0, max(queue_months) * 1.2)
            
            # Add values on bars
            for bar, val in zip(bars1, queue_months):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(val)}', ha='center', va='bottom', fontsize=8, color=JLL_COLORS['dark_gray'])
            
            # Power cost bars (second axis)
            ax2 = ax1.twinx()
            bars2 = ax2.bar([i + width/2 for i in x], power_rates, width,
                           color='#d4af37', label='Power Cost (¢/kWh)', alpha=0.8)
            ax2.set_ylabel('Power Cost (¢/kWh)', fontsize=9, color='#d4af37')
            ax2.tick_params(axis='y', labelcolor='#d4af37', labelsize=8)
            ax2.set_ylim(0, max(power_rates) * 1.3)
            
            # Add values on bars
            for bar, val in zip(bars2, power_rates):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{val:.1f}¢', ha='center', va='bottom', fontsize=8, color=JLL_COLORS['dark_gray'])
            
            # Set x-axis
            ax1.set_xticks(x)
            ax1.set_xticklabels(states, fontsize=10, fontweight='bold')
            ax1.set_xlabel('')
            
            # Title
            ax1.set_title('New Generation Capacity: State Comparison', 
                         fontsize=11, fontweight='bold', pad=10, color=JLL_COLORS['dark_blue'])
            
            # Remove top/right spines
            ax1.spines['top'].set_visible(False)
            ax2.spines['top'].set_visible(False)
            
            plt.tight_layout()
            
            # Save chart
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                state_chart_path = tmp.name
            plt.savefig(state_chart_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()
            
            # Add chart to slide
            slide.shapes.add_picture(state_chart_path, Inches(0.5), Inches(1.0), width=Inches(5.8))
            os.unlink(state_chart_path)
        
        # === TOP-RIGHT QUADRANT: Competitive Landscape ===
        tr_title = slide.shapes.add_textbox(Inches(6.8), Inches(1.0), Inches(5.8), Inches(0.4))
        p = tr_title.text_frame.paragraphs[0]
        p.text = "Competitive Landscape"
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_blue'][1:])
        
        comp_land = slide.shapes.add_textbox(Inches(6.8), Inches(1.5), Inches(5.8), Inches(2.3))
        tf = comp_land.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = f"Existing DC Capacity:"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_gray'][1:])
        
        run = p.add_run()
        run.text = f"  {defaults.get('dc_mw', 500)} MW"
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = RGBColor.from_string(JLL_COLORS['teal'][1:])
        p.space_after = Pt(8)
        
        p = tf.add_paragraph()
        p.text = f"Fiber Density:"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_gray'][1:])
        
        run = p.add_run()
        fiber = defaults.get('fiber', 'Medium')
        fiber_color = JLL_COLORS['yellow'][1:] if fiber == 'Medium' else JLL_COLORS['green'][1:]
        run.text = f"  {fiber}"
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = RGBColor.from_string(fiber_color)
        p.space_after = Pt(8)
        
        p = tf.add_paragraph()
        p.text = "Hyperscaler Presence:"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_gray'][1:])
        p.space_after = Pt(4)
        
        for hyperscaler in defaults.get('hyperscalers', [])[:5]:
            p = tf.add_paragraph()
            p.text = f"• {hyperscaler}"
            p.font.size = Pt(9)
            p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_gray'][1:])
            p.level = 1
            p.space_after = Pt(2)
        
        # === BOTTOM-LEFT QUADRANT: ISO & Utility Profile ===
        bl_title = slide.shapes.add_textbox(Inches(0.5), Inches(4.0), Inches(6.0), Inches(0.4))
        p = bl_title.text_frame.paragraphs[0]
        p.text = "ISO & Utility Profile"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_blue'][1:])
        
        iso_box = slide.shapes.add_textbox(Inches(0.5), Inches(4.5), Inches(6.0), Inches(2.2))
        tf = iso_box.text_frame
        tf.word_wrap = True
        
        iso_data = [
            ('Primary ISO:', defaults.get('iso', 'SPP')),
            ('Regulatory Structure:', defaults.get('reg', 'Regulated')),
            ('Utility:', defaults.get('utility', site_data.get('utility', 'Utility'))),
            ('Gen. Queue Time:', f"{defaults.get('queue', 36)} months"),
            ('Industrial Rate:', f"{defaults.get('rate', 5.5)} ¢/kWh"),
            ('Renewable Mix:', f"{defaults.get('renew', 30)}%"),
            ('State Tier:', f"Tier {defaults.get('tier', 1)}"),
            ('Overall Score:', f"{defaults.get('score', 70)}/100"),
        ]
        
        for i, (label, value) in enumerate(iso_data):
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            
            p.text = label
            p.font.size = Pt(10)
            p.font.bold = True
            p.font.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])
            
            run = p.add_run()
            run.text = f"  {value}"
            run.font.size = Pt(11)
            run.font.bold = True
            run.font.color.rgb = RGBColor.from_string(JLL_COLORS['teal'][1:])
            p.space_after = Pt(4)
        
        # Key Incentives
        p = tf.add_paragraph()
        p.text = "Key Incentives:"
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])
        p.space_after = Pt(3)
        
        for incentive in defaults.get('incentives', [])[:2]:
            p = tf.add_paragraph()
            p.text = f"• {incentive}"
            p.font.size = Pt(9)
            p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_gray'][1:])
            p.level = 1
        
        # === BOTTOM-RIGHT QUADRANT: SWOT Summary ===
        br_title = slide.shapes.add_textbox(Inches(6.8), Inches(4.0), Inches(5.8), Inches(0.4))
        p = br_title.text_frame.paragraphs[0]
        p.text = f"{state_name} SWOT Summary"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_blue'][1:])
        
        # SWOT in 2x2 grid
        swot_data = [
            ("Strengths", defaults.get('strengths', []), JLL_COLORS['green'][1:], Inches(6.8), Inches(4.5)),
            ("Opportunities", defaults.get('opportunities', []), JLL_COLORS['teal'][1:], Inches(9.8), Inches(4.5)),
            ("Weaknesses", defaults.get('weaknesses', []), JLL_COLORS['red'][1:], Inches(6.8), Inches(5.6)),
            ("Threats", defaults.get('threats', []), JLL_COLORS['orange'][1:], Inches(9.8), Inches(5.6)),
        ]
        
        for title, items, color, x, y in swot_data:
            swot_box = slide.shapes.add_textbox(x, y, Inches(2.8), Inches(1.0))
            tf = swot_box.text_frame
            tf.word_wrap = True
            
            p = tf.paragraphs[0]
            p.text = title
            p.font.size = Pt(11)
            p.font.bold = True
            p.font.color.rgb = RGBColor.from_string(color)
            p.space_after = Pt(4)
            
            for item in items[:2]:
                p = tf.add_paragraph()
                p.text = f"+ {item}" if title in ['Strengths', 'Opportunities'] else f"- {item}"
                p.font.size = Pt(9)
                p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_gray'][1:])
                p.space_after = Pt(2)
        
        add_footer(slide, 8, Inches, Pt, RGBColor)

    # REORDER: Move Thank You to end
    def move_slide_to_end(prs, slide_index):
        slides = list(prs.slides._sldIdLst)
        if slide_index < len(slides):
            slide_id = slides[slide_index]
            prs.slides._sldIdLst.remove(slide_id)
            prs.slides._sldIdLst.append(slide_id)

    move_slide_to_end(prs, 4)  # Original Thank You position

    prs.save(output_path)
    return output_path


def export_multiple_sites(sites: List[Dict], template_path: str,
                          output_dir: str, config: ExportConfig = None) -> List[str]:
    """Export multiple sites."""
    config = config or ExportConfig()
    os.makedirs(output_dir, exist_ok=True)
    output_paths = []
    for site in sites:
        site_id = site.get('site_id', 'site')
        output_path = os.path.join(output_dir, f"{site_id}_profile.pptx")
        try:
            export_site_to_pptx(site, template_path, output_path, config)
            output_paths.append(output_path)
        except Exception as e:
            print(f"Error exporting {site_id}: {e}")
    return output_paths


def analyze_template(template_path: str) -> Dict:
    """Analyze template structure."""
    try:
        from pptx import Presentation
    except ImportError:
        raise ImportError("python-pptx required")

    prs = Presentation(template_path)
    analysis = {'slide_count': len(prs.slides), 'slides': []}
    for i, slide in enumerate(prs.slides):
        slide_info = {'index': i, 'shapes': [], 'tables': []}
        for shape in slide.shapes:
            if shape.has_table:
                slide_info['tables'].append({
                    'rows': len(shape.table.rows),
                    'cols': len(shape.table.columns)
                })
            elif shape.has_text_frame and shape.text_frame.text.strip():
                slide_info['shapes'].append({'text': shape.text_frame.text[:100]})
        analysis['slides'].append(slide_info)
    return analysis


def create_default_template(output_path: str) -> str:
    """
    Create a default PowerPoint template with JLL branding.
    This template follows the structure expected by export_site_to_pptx().
    
    Slide Order:
    0. Title (dark blue background)
    1. Site Profile
    2. Site Boundary
    3. Topography
    4. Thank You (dark blue background)
    """
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
        from pptx.enum.shapes import MSO_SHAPE
    except ImportError:
        raise ImportError("python-pptx required")
    
    prs = Presentation()
    prs.slide_width = Inches(13.33)  # Widescreen 16:9
    prs.slide_height = Inches(7.5)
    
    # === SLIDE 0: Title Slide (Dark Blue Background) ===
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
    
    # Dark blue background
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor.from_string(JLL_COLORS['dark_blue'][1:])
    
    # Title text
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(12), Inches(2))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "SITE NAME"
    p.font.size = Pt(54)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.alignment = PP_ALIGN.CENTER
    
    # Subtitle
    subtitle_box = slide.shapes.add_textbox(Inches(0.5), Inches(4.5), Inches(12), Inches(1))
    tf2 = subtitle_box.text_frame
    p2 = tf2.paragraphs[0]
    p2.text = "[STATE] | Power Site Profile"
    p2.font.size = Pt(24)
    p2.font.color.rgb = RGBColor(200, 200, 200)
    p2.alignment = PP_ALIGN.CENTER
    
    # Date
    date_box = slide.shapes.add_textbox(Inches(0.5), Inches(6.5), Inches(12), Inches(0.5))
    tf3 = date_box.text_frame
    p3 = tf3.paragraphs[0]
    p3.text = f"December 2, 2025"
    p3.font.size = Pt(14)
    p3.font.color.rgb = RGBColor(180, 180, 180)
    p3.alignment = PP_ALIGN.CENTER
    
    # === SLIDE 1: Site Profile (White Background with Rating Table) ===
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Header bar
    header = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0),
                                     Inches(13.33), Inches(0.6))
    header.fill.solid()
    header.fill.fore_color.rgb = RGBColor.from_string(JLL_COLORS['dark_blue'][1:])
    header.line.fill.background()
    
    header_text = slide.shapes.add_textbox(Inches(0.4), Inches(0.12), Inches(10), Inches(0.4))
    p = header_text.text_frame.paragraphs[0]
    p.text = "Site Profile"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    
    # Create rating table (15 rows: 1 header + 14 data rows)
    rows, cols = 15, 4
    left, top = Inches(0.25), Inches(0.75)
    width, height = Inches(7.9), Inches(6.3)
    
    table = slide.shapes.add_table(rows, cols, left, top, width, height).table
    
    # Set column widths
    table.columns[0].width = Inches(1.3)   # Item
    table.columns[1].width = Inches(2.0)   # Preference
    table.columns[2].width = Inches(0.6)   # Rating
    table.columns[3].width = Inches(4.0)   # Description
    
    # Set row heights for professional appearance
    for row in table.rows:
        row.height = Inches(0.45)
    table.rows[0].height = Inches(0.4)  # Header
    
    # Header row styling
    header_items = ['Item', 'Preference', 'Rating', 'Description']
    for col_idx, header_text in enumerate(header_items):
        cell = table.cell(0, col_idx)
        cell.text = header_text
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor.from_string(JLL_COLORS['dark_blue'][1:])
        
        # Style header text
        cell.text_frame.margin_top = Inches(0.05)
        cell.text_frame.margin_bottom = Inches(0.05)
        cell.text_frame.margin_left = Inches(0.05)
        cell.text_frame.margin_right = Inches(0.05)
        
        for paragraph in cell.text_frame.paragraphs:
            paragraph.font.size = Pt(10)
            paragraph.font.bold = True
            paragraph.font.color.rgb = RGBColor(255, 255, 255)
            paragraph.alignment = PP_ALIGN.CENTER
    
    # Data rows (populate with placeholders)
    rating_data = [
        ('Location', 'Proximity and Surroundings', 'N/R', '• Nearest Town: TBD\\n• Distance to Large City: TBD\\n• Neighboring Uses: TBD'),
        ('Ownership &\\nAsking Price', 'Single Owner', 'N/R', '• Owner(s): TBD\\n• Asking Price: TBD'),
        ('Size / Shape /\\nDimensions', '1000 acres', 'N/R', '• Total Size: TBD acres\\n• Dimensions: TBD'),
        ('Zoning', 'Data Center Compatible', 'N/R', '• Zoning: TBD\\n• Site condition: TBD'),
        ('Timing', 'Transfer by Q1 2026', 'N/R', '• Transfer timeline: TBD'),
        ('Geotechnical\\nand Topography', 'Generally Flat with\\nGood Soils', 'N/R', '• Soil type: TBD\\n• Topography: TBD\\n• Elevation change: TBD'),
        ('Environmental,\\nEcological,\\nArcheological', 'No Barriers to\\nConstruction', 'N/R', '• Environmental: TBD\\n• Ecological: TBD\\n• Archeological: TBD'),
        ('Wetlands and\\nJurisdictional\\nWater', 'No Wetlands or\\nJurisdictional Water', 'N/R', '• Wetlands: TBD\\n• Water Features: TBD'),
        ('Disaster', 'Outside Zone of Risk', 'N/R', '• Flood: TBD\\n• Seismic: TBD'),
        ('Easements', 'No Utility Easements or\\nROW', 'N/R', '• Utility easements: TBD\\n• ROW: TBD'),
        ('Electricity', '300 MW+', 'N/R', '• Available capacity: TBD MW\\n• Service type: TBD'),
        ('Water', '1M GPD+', 'N/R', '• Water source: TBD\\n• Capacity: TBD GPD'),
        ('Wastewater', '300K GPD+', 'N/R', '• Wastewater solution: TBD'),
        ('Telecom', 'High Bandwidth Fiber', 'N/R', '• Fiber status: TBD\\n• Provider: TBD'),
    ]
    
    for row_idx, (item, preference, rating, description) in enumerate(rating_data, start=1):
        # Item column
        cell = table.cell(row_idx, 0)
        cell.text = item
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(250, 250, 250)
        cell.text_frame.margin_top = Inches(0.03)
        cell.text_frame.margin_bottom = Inches(0.03)
        cell.text_frame.margin_left = Inches(0.05)
        cell.text_frame.margin_right = Inches(0.05)
        cell.text_frame.word_wrap = True
        
        for paragraph in cell.text_frame.paragraphs:
            paragraph.font.size = Pt(10)
            paragraph.font.bold = True
            paragraph.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_gray'][1:])
            paragraph.line_spacing = 1.0
        
        # Preference column
        cell = table.cell(row_idx, 1)
        cell.text = preference
        cell.text_frame.margin_top = Inches(0.03)
        cell.text_frame.margin_bottom = Inches(0.03)
        cell.text_frame.margin_left = Inches(0.05)
        cell.text_frame.margin_right = Inches(0.05)
        cell.text_frame.word_wrap = True
        
        for paragraph in cell.text_frame.paragraphs:
            paragraph.font.size = Pt(10)
            paragraph.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_gray'][1:])
            paragraph.line_spacing = 1.0
        
        # Rating column (color-coded)
        cell = table.cell(row_idx, 2)
        cell.text = rating
        cell.fill.solid()
        # Default to gray for N/R
        cell.fill.fore_color.rgb = RGBColor.from_string(JLL_COLORS['rating_gray'][1:])
        cell.text_frame.margin_top = Inches(0.03)
        cell.text_frame.margin_bottom = Inches(0.03)
        
        for paragraph in cell.text_frame.paragraphs:
            paragraph.font.size = Pt(7)
            paragraph.font.bold = True
            paragraph.font.color.rgb = RGBColor(255, 255, 255)
            paragraph.alignment = PP_ALIGN.CENTER
        
        # Description column
        cell = table.cell(row_idx, 3)
        cell.text = description
        cell.text_frame.word_wrap = True
        cell.text_frame.margin_top = Inches(0.03)
        cell.text_frame.margin_bottom = Inches(0.03)
        cell.text_frame.margin_left = Inches(0.05)
        cell.text_frame.margin_right = Inches(0.05)
        
        for paragraph in cell.text_frame.paragraphs:
            paragraph.font.size = Pt(9)
            paragraph.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_gray'][1:])
            paragraph.line_spacing = 0.9
    
    # Add map placeholder on right side
    map_placeholder = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(8.3), Inches(0.8),
        Inches(4.8), Inches(3.0)
    )
    map_placeholder.fill.solid()
    map_placeholder.fill.fore_color.rgb = RGBColor(240, 240, 240)
    map_placeholder.line.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])
    map_placeholder.line.width = Pt(1)
    
    # Map label
    map_label = slide.shapes.add_textbox(Inches(8.3), Inches(2.0), Inches(4.8), Inches(0.5))
    p = map_label.text_frame.paragraphs[0]
    p.text = "[Location Map]"
    p.font.size = Pt(12)
    p.font.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])
    p.alignment = PP_ALIGN.CENTER
    
    # Add site image placeholders below map
    site_placeholder = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(8.3), Inches(4.0),
        Inches(4.8), Inches(2.8)
    )
    site_placeholder.fill.solid()
    site_placeholder.fill.fore_color.rgb = RGBColor(240, 240, 240)
    site_placeholder.line.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])
    site_placeholder.line.width = Pt(1)
    
    site_label = slide.shapes.add_textbox(Inches(8.3), Inches(5.2), Inches(4.8), Inches(0.5))
    p = site_label.text_frame.paragraphs[0]
    p.text = "[Site Image]"
    p.font.size = Pt(12)
    p.font.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])
    p.alignment = PP_ALIGN.CENTER
    
    # Footer
    footer = slide.shapes.add_textbox(Inches(0.4), Inches(7.2), Inches(12), Inches(0.25))
    p = footer.text_frame.paragraphs[0]
    p.text = f"© {datetime.now().year} Jones Lang LaSalle IP, Inc. All rights reserved  |  2"
    p.font.size = Pt(8)
    p.font.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])
    
    # === SLIDE 2: Site Boundary (White Background w/ placeholder) ===
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Header bar
    header = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0),
                                     Inches(13.33), Inches(0.6))
    header.fill.solid()
    header.fill.fore_color.rgb = RGBColor.from_string(JLL_COLORS['dark_blue'][1:])
    header.line.fill.background()
    
    header_text = slide.shapes.add_textbox(Inches(0.4), Inches(0.12), Inches(10), Inches(0.4))
    p = header_text.text_frame.paragraphs[0]
    p.text = "Site Boundary"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    
    # Placeholder for map
    placeholder = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(1.5), Inches(1.5),
        Inches(10), Inches(5)
    )
    placeholder.fill.solid()
    placeholder.fill.fore_color.rgb = RGBColor(240, 240, 240)
    placeholder.line.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])
    placeholder.line.width = Pt(1)
    
    # Placeholder text
    text_box = slide.shapes.add_textbox(Inches(1.5), Inches(3.5), Inches(10), Inches(1))
    p = text_box.text_frame.paragraphs[0]
    p.text = "[Site Boundary Map]"
    p.font.size = Pt(18)
    p.font.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])
    p.alignment = PP_ALIGN.CENTER
    
    # Footer
    footer = slide.shapes.add_textbox(Inches(0.4), Inches(7.2), Inches(12), Inches(0.25))
    p = footer.text_frame.paragraphs[0]
    p.text = f"© {datetime.now().year} Jones Lang LaSalle IP, Inc. All rights reserved  |  3"
    p.font.size = Pt(8)
    p.font.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])
    
    # === SLIDE 3: Topography (White Background w/ placeholder) ===
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Header bar
    header = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0),
                                     Inches(13.33), Inches(0.6))
    header.fill.solid()
    header.fill.fore_color.rgb = RGBColor.from_string(JLL_COLORS['dark_blue'][1:])
    header.line.fill.background()
    
    header_text = slide.shapes.add_textbox(Inches(0.4), Inches(0.12), Inches(10), Inches(0.4))
    p = header_text.text_frame.paragraphs[0]
    p.text = "Topography"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    
    # Placeholder for map
    placeholder = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(1.5), Inches(1.5),
        Inches(10), Inches(5)
    )
    placeholder.fill.solid()
    placeholder.fill.fore_color.rgb = RGBColor(240, 240, 240)
    placeholder.line.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:]) 
    placeholder.line.width = Pt(1)
    
    # Placeholder text
    text_box = slide.shapes.add_textbox(Inches(1.5), Inches(3.5), Inches(10), Inches(1))
    p = text_box.text_frame.paragraphs[0]
    p.text = "[Topography Map]"
    p.font.size = Pt(18)
    p.font.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])
    p.alignment = PP_ALIGN.CENTER
    
    # Footer
    footer = slide.shapes.add_textbox(Inches(0.4), Inches(7.2), Inches(12), Inches(0.25))
    p = footer.text_frame.paragraphs[0]
    p.text = f"© {datetime.now().year} Jones Lang LaSalle IP, Inc. All rights reserved  |  4"
    p.font.size = Pt(8)
    p.font.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])
    
    # === SLIDE 4: Thank You (Dark Blue Background) ===
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Dark blue background
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor.from_string(JLL_COLORS['dark_blue'][1:])
    
    # Thank you text
    thank_you_box = slide.shapes.add_textbox(Inches(0.5), Inches(2), Inches(12), Inches(1.5))
    tf = thank_you_box.text_frame
    p = tf.paragraphs[0]
    p.text = "Thank You"
    p.font.size = Pt(48)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.alignment = PP_ALIGN.CENTER
    
    # Contact info
    contact_box = slide.shapes.add_textbox(Inches(0.5), Inches(4.5), Inches(12), Inches(2))
    tf = contact_box.text_frame
    tf.word_wrap = True
    
    # Name
    p = tf.paragraphs[0]
    p.text = "NAME"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.alignment = PP_ALIGN.CENTER
    p.space_after = Pt(6)
    
    # Title
    p = tf.add_paragraph()
    p.text = "TITLE"
    p.font.size = Pt(14)
    p.font.color.rgb = RGBColor(200, 200, 200)
    p.alignment = PP_ALIGN.CENTER
    p.space_after = Pt(12)
    
    # Contact details
    p = tf.add_paragraph()
    p.text = "Phone  |  Email"
    p.font.size = Pt(12)
    p.font.color.rgb = RGBColor(180, 180, 180)
    p.alignment = PP_ALIGN.CENTER
    
    # Save template
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    prs.save(output_path)
    return output_path





__all__ = [
    'CapacityTrajectory', 'PhaseData', 'ScoreAnalysis', 'RiskOpportunity', 'MarketAnalysis',
    'ExportConfig', 'export_site_to_pptx', 'export_multiple_sites',
    'generate_capacity_trajectory_chart', 'generate_critical_path_chart',
    'generate_score_radar_chart', 'generate_score_summary_chart',
    'generate_market_analysis_chart', 'analyze_template', 'create_default_template',
    'JLL_COLORS', 'MATPLOTLIB_AVAILABLE',
]

