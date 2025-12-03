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
    'dark_blue': '#1a2b4a',
    'red': '#e31837',
    'light_gray': '#f5f5f5',
    'medium_gray': '#666666',
    'dark_gray': '#333333',
    'teal': '#2b6777',           # Interconnection line
    'tan': '#c9b89d',            # Generation line
    'white': '#ffffff',
    'green': '#2e7d32',
    'amber': '#f9a825',
    'light_blue': '#4a90d9',
}

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

    # ADD SLIDE: Infrastructure & Critical Path (WHITE background)
    if config.include_infrastructure and MATPLOTLIB_AVAILABLE:
        slide = prs.slides.add_slide(blank_layout)
        
        # Set white background explicitly
        set_slide_background_white(slide, Inches, RGBColor)
        
        add_header_bar(slide, "Infrastructure & Critical Path", Inches, Pt, RGBColor)

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            infra_path = tmp.name
        generate_critical_path_chart(phases, site_data, infra_path)
        slide.shapes.add_picture(infra_path, Inches(0.4), Inches(0.8), width=Inches(12.5))

        # Add risks/opportunities summary at bottom
        risks = site_data.get('risks', [])
        opportunities = site_data.get('opportunities', [])
        if risks or opportunities:
            details_box = slide.shapes.add_textbox(Inches(0.4), Inches(6.3), Inches(12), Inches(0.8))
            tf = details_box.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            summary_parts = []
            if risks:
                summary_parts.append(f"Key Risks: {', '.join(risks[:3])}")
            if opportunities:
                summary_parts.append(f"Opportunities: {', '.join(opportunities[:3])}")
            p.text = "  |  ".join(summary_parts)
            p.font.size = Pt(9)
            p.font.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])

        add_footer(slide, 6, Inches, Pt, RGBColor)
        os.unlink(infra_path)

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
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            score_path = tmp.name
        generate_score_summary_chart(scores, site_data.get('name', 'Site'), score_path)
        slide.shapes.add_picture(score_path, Inches(0.4), Inches(0.8), width=Inches(12.5))
        add_footer(slide, 7, Inches, Pt, RGBColor)
        os.unlink(score_path)

    # ADD SLIDE: Market Analysis (WHITE background)
    if config.include_market_analysis and MATPLOTLIB_AVAILABLE:
        slide = prs.slides.add_slide(blank_layout)
        set_slide_background_white(slide, Inches, RGBColor)
        add_header_bar(slide, "Market Analysis", Inches, Pt, RGBColor)
        
        # Build market data from site_data and state analysis
        state_code = site_data.get('state_code', site_data.get('state', 'OK')[:2].upper())
        
        # Get market_analysis if provided, otherwise build from available data
        market_raw = site_data.get('market_analysis', {})
        
        # Build comparison states data
        comparison_states = market_raw.get('comparison_states', {})
        if not comparison_states:
            # Default comparison states based on common alternatives
            default_comparisons = {
                'OK': {'TX': {}, 'GA': {}, 'OH': {}},
                'TX': {'OK': {}, 'GA': {}, 'AZ': {}},
                'GA': {'TX': {}, 'VA': {}, 'OH': {}},
                'VA': {'GA': {}, 'OH': {}, 'TX': {}},
                'OH': {'IN': {}, 'GA': {}, 'TX': {}},
            }
            comp_codes = list(default_comparisons.get(state_code, {'TX': {}, 'GA': {}}).keys())[:3]
            
            # Default state data (from state_analysis framework)
            state_defaults = {
                'OK': {'name': 'Oklahoma', 'queue_months': 30, 'rate': 0.055, 'score': 88, 'tier': 1},
                'TX': {'name': 'Texas', 'queue_months': 36, 'rate': 0.065, 'score': 80, 'tier': 1},
                'GA': {'name': 'Georgia', 'queue_months': 42, 'rate': 0.072, 'score': 70, 'tier': 2},
                'VA': {'name': 'Virginia', 'queue_months': 48, 'rate': 0.078, 'score': 58, 'tier': 3},
                'OH': {'name': 'Ohio', 'queue_months': 36, 'rate': 0.068, 'score': 70, 'tier': 2},
                'IN': {'name': 'Indiana', 'queue_months': 32, 'rate': 0.062, 'score': 72, 'tier': 2},
                'WY': {'name': 'Wyoming', 'queue_months': 28, 'rate': 0.048, 'score': 82, 'tier': 1},
                'AZ': {'name': 'Arizona', 'queue_months': 38, 'rate': 0.070, 'score': 52, 'tier': 3},
            }
            for code in comp_codes:
                if code in state_defaults:
                    comparison_states[code] = state_defaults[code]
        
        # Get state defaults for site's state
        site_state_defaults = {
            'OK': {'iso': 'SPP', 'reg': 'regulated', 'queue': 30, 'rate': 0.055, 'renew': 42,
                   'score': 88, 'tier': 1, 'dc_mw': 500, 'fiber': 'medium',
                   'hyperscalers': ['Google (Pryor)', 'Meta (announced)'],
                   'strengths': ['Pro-business PSC', 'Low power costs', 'SPP wholesale market'],
                   'weaknesses': ['Limited DC ecosystem', 'Water constraints'],
                   'opportunities': ['Hyperscaler expansion', 'Tulsa hub growth'],
                   'threats': ['Grid congestion', 'Water rights competition'],
                   'incentives': ['Sales tax exemption', 'Property tax abatement', 'Quality Jobs Program']},
            'TX': {'iso': 'ERCOT', 'reg': 'deregulated', 'queue': 36, 'rate': 0.065, 'renew': 35,
                   'score': 80, 'tier': 1, 'dc_mw': 3000, 'fiber': 'high',
                   'hyperscalers': ['Google', 'Microsoft', 'Meta', 'AWS', 'Oracle'],
                   'strengths': ['No state income tax', 'Massive ecosystem', 'ERCOT flexibility'],
                   'weaknesses': ['Grid reliability', 'Water stress', 'Queue backlog'],
                   'opportunities': ['Continued growth', 'West Texas expansion'],
                   'threats': ['Grid instability', 'Water availability'],
                   'incentives': ['Chapter 313 replacement', 'Property tax limits']},
        }
        
        defaults = site_state_defaults.get(state_code, site_state_defaults.get('OK'))
        
        market_data = {
            'state_code': state_code,
            'state_name': market_raw.get('state_name', site_data.get('state', defaults.get('name', 'State'))),
            'primary_iso': market_raw.get('primary_iso', site_data.get('iso', defaults.get('iso', 'SPP'))),
            'regulatory_structure': market_raw.get('regulatory_structure', defaults.get('reg', 'regulated')),
            'utility_name': market_raw.get('utility_name', site_data.get('utility', 'Utility')),
            'avg_queue_time_months': market_raw.get('avg_queue_time_months', defaults.get('queue', 36)),
            'avg_industrial_rate': market_raw.get('avg_industrial_rate', defaults.get('rate', 0.06)),
            'renewable_percentage': market_raw.get('renewable_percentage', defaults.get('renew', 30)),
            'overall_score': market_raw.get('overall_score', defaults.get('score', 70)),
            'tier': market_raw.get('tier', defaults.get('tier', 2)),
            'existing_dc_mw': market_raw.get('existing_dc_mw', defaults.get('dc_mw', 500)),
            'hyperscaler_presence': market_raw.get('hyperscaler_presence', defaults.get('hyperscalers', [])),
            'fiber_density': market_raw.get('fiber_density', defaults.get('fiber', 'medium')),
            'strengths': market_raw.get('strengths', defaults.get('strengths', [])),
            'weaknesses': market_raw.get('weaknesses', defaults.get('weaknesses', [])),
            'opportunities': market_raw.get('opportunities', defaults.get('opportunities', [])),
            'threats': market_raw.get('threats', defaults.get('threats', [])),
            'comparison_states': comparison_states,
            'incentives': market_raw.get('incentives', defaults.get('incentives', [])),
        }
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            market_path = tmp.name
        generate_market_analysis_chart(market_data, site_data.get('name', 'Site'), market_path)
        slide.shapes.add_picture(market_path, Inches(0.4), Inches(0.8), width=Inches(12.5))
        
        add_footer(slide, 8, Inches, Pt, RGBColor)
        os.unlink(market_path)

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
    
    # === SLIDE 1: Site Profile (White Background) ===
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
    
    # Content - Two columns
    # Left column: Key metrics
    left_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(6), Inches(5))
    tf = left_box.text_frame
    tf.word_wrap = True
    
    # Title
    p = tf.paragraphs[0]
    p.text = "Site Overview"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_blue'][1:])
    p.space_after = Pt(12)
    
    # Key details
    details = [
        ("Location:", "[STATE]"),
        ("Target Capacity:", "1GW+"),
        ("Utility Connection:", "OG&E 345kV line"),
        ("Total Acres:", "1,250 acres"),
        ("Coordinates:", "[Coordinates linked]"),
    ]
    
    for label, value in details:
        p = tf.add_paragraph()
        p.text = f"{label}"
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = RGBColor.from_string(JLL_COLORS['medium_gray'][1:])
        p.space_after = Pt(2)
        
        p = tf.add_paragraph()
        p.text = f"  {value}"
        p.font.size = Pt(14)
        p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_blue'][1:])
        p.space_after = Pt(8)
    
    # Right column: Description
    right_box = slide.shapes.add_textbox(Inches(7), Inches(1.2), Inches(6), Inches(5))
    tf = right_box.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = "Site Description"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_blue'][1:])
    p.space_after = Pt(12)
    
    p = tf.add_paragraph()
    p.text = "1,250 acre site with significant growth opportunity located between Tulsa and Oklahoma City."
    p.font.size = Pt(12)
    p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_gray'][1:])
    p.space_after = Pt(12)
    
    p = tf.add_paragraph()
    p.text = "Key Features:"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_blue'][1:])
    p.space_after = Pt(6)
    
    features = ["Estimated 1GW+", "3M GDP capacity", "Favorable utility relationship"]
    for feature in features:
        p = tf.add_paragraph()
        p.text = f"• {feature}"
        p.font.size = Pt(11)
        p.font.color.rgb = RGBColor.from_string(JLL_COLORS['dark_gray'][1:])
        p.space_after = Pt(4)
    
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

