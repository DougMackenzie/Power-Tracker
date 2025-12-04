"""
Powered Land Site Diagnostic Tool
==================================
Comprehensive power pathway analysis with critical path to power.

Captures:
- Phase-by-phase power delivery breakdown
- Interconnection vs generation capacity
- Infrastructure details (voltage, transmission, switching)
- Study/approval status (SIS, FS, FA, IA)
- Equipment procurement (breakers, transformers)
- Contract structures (utility, PPA, self-gen)
- Year-by-year capacity projections
- Critical path with dependencies
- Non-power items (zoning, water, permits)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import date, timedelta
import json

# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class StudyStatus(Enum):
    NOT_STARTED = "not_started"
    REQUESTED = "requested"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    APPROVED = "approved"

class ContractStructure(Enum):
    UTILITY_OWNED = "utility_owned"
    PPA_THIRD_PARTY = "ppa_third_party"
    SELF_OWNED = "self_owned"
    HYBRID = "hybrid"
    TBD = "tbd"

class PowerSource(Enum):
    UTILITY_GRID = "utility_grid"
    NATURAL_GAS = "natural_gas"
    SOLAR = "solar"
    BATTERY = "battery"
    FUEL_CELL = "fuel_cell"
    NUCLEAR_SMR = "nuclear_smr"
    NUCLEAR_TRADITIONAL = "nuclear_traditional"
    WIND = "wind"
    HYDRO = "hydro"
    OTHER = "other"

class ServiceType(Enum):
    SWITCHING_STATION = "switching_station"
    RADIAL = "radial"
    LOOP = "loop"
    NETWORK = "network"
    TBD = "tbd"

class TaskStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    AT_RISK = "at_risk"


# Standard lead times (months) for critical path
STANDARD_LEAD_TIMES = {
    # Studies & Approvals
    'system_impact_study': 12,
    'facilities_study': 9,
    'facilities_agreement': 6,
    'interconnection_agreement': 3,
    
    # Equipment
    'transformer_345kv': 36,
    'transformer_230kv': 30,
    'transformer_115kv': 24,
    'breaker_high_voltage': 18,
    'breaker_customer_provided': 12,
    'switchgear': 12,
    
    # Infrastructure
    'transmission_per_mile': 6,  # months per mile for new transmission
    'substation_new': 30,
    'substation_upgrade': 18,
    'switching_station': 24,
    
    # Generation
    'gas_turbine_simple': 24,
    'gas_turbine_combined': 36,
    'solar_utility_scale': 18,
    'battery_storage': 12,
    'fuel_cell': 18,
    'smr_licensing': 48,
    'smr_construction': 36,
    
    # Other
    'gas_pipeline_per_mile': 4,
    'water_infrastructure': 18,
    'zoning_approval': 12,
    'environmental_review': 12,
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class StudyApprovalStatus:
    """Tracks status of interconnection studies and approvals."""
    system_impact_study: StudyStatus = StudyStatus.NOT_STARTED
    sis_start_date: Optional[date] = None
    sis_completion_date: Optional[date] = None
    sis_results_summary: str = ""
    
    facilities_study: StudyStatus = StudyStatus.NOT_STARTED
    fs_start_date: Optional[date] = None
    fs_completion_date: Optional[date] = None
    fs_cost_estimate: int = 0  # $
    
    facilities_agreement: StudyStatus = StudyStatus.NOT_STARTED
    fa_execution_date: Optional[date] = None
    fa_required_deposits: int = 0  # $
    
    interconnection_agreement: StudyStatus = StudyStatus.NOT_STARTED
    ia_execution_date: Optional[date] = None
    
    notes: str = ""


@dataclass
class PowerPhase:
    """Represents a single phase of power delivery."""
    phase_number: int
    phase_name: str = ""
    
    # Capacity
    interconnection_capacity_mw: int = 0  # What the grid connection supports
    generation_capacity_mw: int = 0  # What generation is available
    it_load_capacity_mw: int = 0  # What IT load can be served (after PUE)
    
    # Timeline
    target_online_date: Optional[date] = None
    current_projected_date: Optional[date] = None
    is_permanent: bool = True  # vs temporary/bridge solution
    
    # Power sources (can be multiple)
    power_sources: List[PowerSource] = field(default_factory=list)
    primary_source: PowerSource = PowerSource.UTILITY_GRID
    
    # Interconnection details
    voltage_kv: int = 0  # 115, 230, 345, 500
    service_type: ServiceType = ServiceType.TBD
    transmission_distance_miles: float = 0
    requires_new_transmission: bool = False
    requires_substation_upgrade: bool = False
    requires_new_substation: bool = False
    
    # Contract structure
    utility_power_contract: ContractStructure = ContractStructure.TBD
    onsite_gen_contract: ContractStructure = ContractStructure.TBD
    
    # Study status
    studies: StudyApprovalStatus = field(default_factory=StudyApprovalStatus)
    
    # Equipment requirements
    transformer_spec: str = ""
    breaker_spec: str = ""
    customer_provided_equipment: List[str] = field(default_factory=list)
    
    # Cost estimates
    interconnection_cost: int = 0  # $
    network_upgrade_cost: int = 0  # $
    generation_capex: int = 0  # $
    
    notes: str = ""


@dataclass
class OnsiteGeneration:
    """Details on onsite/behind-the-meter generation."""
    source: PowerSource
    capacity_mw: int = 0
    contract_structure: ContractStructure = ContractStructure.TBD
    operator: str = ""  # Utility name, IPP name, or "self"
    
    # Timeline
    development_start: Optional[date] = None
    target_cod: Optional[date] = None
    current_projected_cod: Optional[date] = None
    
    # For gas generation
    gas_pipeline_required: bool = False
    gas_pipeline_distance_miles: float = 0
    gas_pipeline_upgrade_scope: str = ""
    gas_study_status: str = ""
    
    # For solar
    land_required_acres: int = 0
    
    # For SMR/nuclear
    nrc_licensing_status: str = ""
    site_characterization_complete: bool = False
    
    # For all
    permits_required: List[str] = field(default_factory=list)
    permits_obtained: List[str] = field(default_factory=list)
    
    capex_estimate: int = 0  # $
    ppa_rate: float = 0  # $/MWh if PPA
    
    notes: str = ""


@dataclass
class CriticalPathTask:
    """A task in the critical path to power."""
    task_id: str
    task_name: str
    category: str  # "study", "equipment", "infrastructure", "approval", "generation"
    phase: int  # Which power phase this supports (0 = all phases)
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)  # List of task_ids
    enables: List[str] = field(default_factory=list)  # List of task_ids
    
    # Timeline
    duration_months: int = 0
    earliest_start: Optional[date] = None
    target_completion: Optional[date] = None
    current_projected_completion: Optional[date] = None
    
    # Status
    status: TaskStatus = TaskStatus.NOT_STARTED
    percent_complete: int = 0
    
    # Owner
    responsible_party: str = ""  # Utility, developer, contractor, etc.
    
    # Risk
    risk_level: str = ""  # "low", "medium", "high", "critical"
    risk_notes: str = ""
    
    # Acceleration options
    acceleration_options: List[str] = field(default_factory=list)
    
    notes: str = ""


@dataclass
class YearlyCapacity:
    """Capacity breakdown for a single year."""
    year: int
    
    # Interconnection (what the grid can deliver)
    interconnection_mw: int = 0
    interconnection_sources: str = ""  # e.g., "Utility 115kV"
    
    # Generation (what can be produced)
    utility_generation_mw: int = 0
    onsite_generation_mw: int = 0
    total_generation_mw: int = 0
    generation_sources: str = ""  # e.g., "Utility + 100MW gas"
    
    # Available to IT (limiting factor of interconnect vs generation)
    available_mw: int = 0  # min(interconnection, generation)
    limiting_factor: str = ""  # "interconnection" or "generation"
    
    # IT Load (after PUE)
    it_load_mw: int = 0
    assumed_pue: float = 1.3
    
    # Cumulative
    cumulative_interconnection_mw: int = 0
    cumulative_generation_mw: int = 0
    cumulative_available_mw: int = 0
    cumulative_it_load_mw: int = 0
    
    notes: str = ""


@dataclass
class NonPowerItems:
    """Non-power infrastructure and approvals."""
    # Zoning
    zoning_status: str = ""  # "not_started", "pre-app", "submitted", "approved"
    zoning_application_date: Optional[date] = None
    zoning_approval_date: Optional[date] = None
    zoning_expected_duration_months: int = 12
    zoning_conditions: List[str] = field(default_factory=list)
    
    # Water
    water_consumption_gpd: int = 0  # Gallons per day
    water_source: str = ""
    water_rights_secured: bool = False
    water_capacity_available_gpd: int = 0
    
    wastewater_discharge_gpd: int = 0
    wastewater_capacity_available_gpd: int = 0
    wastewater_treatment: str = ""  # "municipal", "onsite", "zero_discharge"
    
    water_infrastructure_required: str = ""
    water_timeline_months: int = 0
    
    # Environmental
    phase1_complete: bool = False
    phase2_required: bool = False
    environmental_issues: List[str] = field(default_factory=list)
    
    # Fiber
    fiber_lit: bool = False
    fiber_providers: List[str] = field(default_factory=list)
    fiber_extension_required_miles: float = 0
    
    # Other permits
    permits_required: List[str] = field(default_factory=list)
    permits_obtained: List[str] = field(default_factory=list)
    permits_timeline: Dict[str, int] = field(default_factory=dict)  # permit: months
    
    notes: str = ""


@dataclass 
class SiteDiagnostic:
    """Complete site diagnostic input."""
    
    # Basic info
    site_name: str
    state: str
    utility_name: str
    developer_name: str = ""
    assessment_date: date = field(default_factory=date.today)
    
    # Scale
    total_site_acreage: int = 0
    total_target_capacity_mw: int = 0  # Ultimate buildout
    
    # Phases
    phases: List[PowerPhase] = field(default_factory=list)
    
    # Onsite generation
    onsite_generation: List[OnsiteGeneration] = field(default_factory=list)
    
    # Yearly projections
    yearly_capacity: List[YearlyCapacity] = field(default_factory=list)
    
    # Critical path
    critical_path_tasks: List[CriticalPathTask] = field(default_factory=list)
    
    # Non-power
    non_power: NonPowerItems = field(default_factory=NonPowerItems)
    
    # Key questions/issues
    open_questions: List[str] = field(default_factory=list)
    key_risks: List[str] = field(default_factory=list)
    acceleration_opportunities: List[str] = field(default_factory=list)
    
    notes: str = ""


# =============================================================================
# DIAGNOSTIC ENGINE
# =============================================================================

class SiteDiagnosticEngine:
    """
    Analyzes a site diagnostic and generates:
    - Power pathway summary
    - Critical path with dependencies
    - Year-by-year capacity projections
    - Gap analysis
    - Risk assessment
    - Recommended actions
    """
    
    def __init__(self, diagnostic: SiteDiagnostic):
        self.d = diagnostic
        self.analysis = {}
    
    def run_analysis(self) -> Dict:
        """Run complete analysis."""
        self._analyze_phases()
        self._analyze_capacity_trajectory()
        self._build_critical_path()
        self._identify_bottlenecks()
        self._assess_risks()
        self._generate_recommendations()
        
        return self.get_report()
    
    def _analyze_phases(self):
        """Analyze each power phase."""
        phase_summary = []
        
        for phase in self.d.phases:
            summary = {
                'phase': phase.phase_number,
                'name': phase.phase_name,
                'interconnection_mw': phase.interconnection_capacity_mw,
                'generation_mw': phase.generation_capacity_mw,
                'it_load_mw': phase.it_load_capacity_mw,
                'voltage_kv': phase.voltage_kv,
                'service_type': phase.service_type.value,
                'target_date': phase.target_online_date,
                'projected_date': phase.current_projected_date,
                'is_permanent': phase.is_permanent,
                'study_status': self._summarize_study_status(phase.studies),
                'infrastructure': self._summarize_infrastructure(phase),
                'issues': []
            }
            
            # Check for issues
            if phase.interconnection_capacity_mw < phase.generation_capacity_mw:
                summary['issues'].append(f"Interconnection ({phase.interconnection_capacity_mw}MW) < Generation ({phase.generation_capacity_mw}MW) - generation constrained")
            
            if phase.generation_capacity_mw < phase.interconnection_capacity_mw:
                summary['issues'].append(f"Generation ({phase.generation_capacity_mw}MW) < Interconnection ({phase.interconnection_capacity_mw}MW) - interconnection underutilized")
            
            if phase.current_projected_date and phase.target_online_date:
                if phase.current_projected_date > phase.target_online_date:
                    delay_days = (phase.current_projected_date - phase.target_online_date).days
                    summary['issues'].append(f"Projected {delay_days} day delay vs target")
            
            phase_summary.append(summary)
        
        self.analysis['phases'] = phase_summary
    
    def _summarize_study_status(self, studies: StudyApprovalStatus) -> Dict:
        """Summarize study/approval status."""
        return {
            'sis': studies.system_impact_study.value,
            'fs': studies.facilities_study.value,
            'fa': studies.facilities_agreement.value,
            'ia': studies.interconnection_agreement.value,
            'overall': self._get_overall_study_status(studies)
        }
    
    def _get_overall_study_status(self, studies: StudyApprovalStatus) -> str:
        """Get overall study progress."""
        if studies.interconnection_agreement == StudyStatus.APPROVED:
            return "Complete - IA Executed"
        if studies.facilities_agreement == StudyStatus.APPROVED:
            return "FA Complete - Awaiting IA"
        if studies.facilities_study == StudyStatus.COMPLETE:
            return "FS Complete - Awaiting FA"
        if studies.system_impact_study == StudyStatus.COMPLETE:
            return "SIS Complete - Awaiting FS"
        if studies.system_impact_study == StudyStatus.IN_PROGRESS:
            return "SIS In Progress"
        if studies.system_impact_study == StudyStatus.REQUESTED:
            return "SIS Requested"
        return "Studies Not Started"
    
    def _summarize_infrastructure(self, phase: PowerPhase) -> Dict:
        """Summarize infrastructure requirements."""
        return {
            'new_transmission': phase.requires_new_transmission,
            'transmission_miles': phase.transmission_distance_miles,
            'new_substation': phase.requires_new_substation,
            'substation_upgrade': phase.requires_substation_upgrade,
            'voltage_kv': phase.voltage_kv,
            'service_type': phase.service_type.value
        }
    
    def _analyze_capacity_trajectory(self):
        """Build year-by-year capacity projection."""
        years = range(2025, 2036)
        trajectory = []
        
        cumulative_interconnect = 0
        cumulative_generation = 0
        
        for year in years:
            # Find existing yearly data or calculate from phases
            existing = next((y for y in self.d.yearly_capacity if y.year == year), None)
            
            if existing:
                trajectory.append({
                    'year': year,
                    'interconnection_mw': existing.interconnection_mw,
                    'generation_mw': existing.total_generation_mw,
                    'available_mw': existing.available_mw,
                    'it_load_mw': existing.it_load_mw,
                    'cumulative_interconnection': existing.cumulative_interconnection_mw,
                    'cumulative_generation': existing.cumulative_generation_mw,
                    'limiting_factor': existing.limiting_factor,
                    'sources': existing.generation_sources
                })
            else:
                # Calculate from phases
                year_interconnect = 0
                year_generation = 0
                sources = []
                
                for phase in self.d.phases:
                    if phase.target_online_date and phase.target_online_date.year <= year:
                        year_interconnect += phase.interconnection_capacity_mw
                        year_generation += phase.generation_capacity_mw
                        sources.extend([s.value for s in phase.power_sources])
                
                for gen in self.d.onsite_generation:
                    if gen.target_cod and gen.target_cod.year <= year:
                        year_generation += gen.capacity_mw
                        sources.append(gen.source.value)
                
                cumulative_interconnect = year_interconnect
                cumulative_generation = year_generation
                available = min(year_interconnect, year_generation)
                limiting = "interconnection" if year_interconnect < year_generation else "generation" if year_generation < year_interconnect else "balanced"
                
                trajectory.append({
                    'year': year,
                    'interconnection_mw': year_interconnect,
                    'generation_mw': year_generation,
                    'available_mw': available,
                    'it_load_mw': int(available / 1.3),  # Assume 1.3 PUE
                    'cumulative_interconnection': cumulative_interconnect,
                    'cumulative_generation': cumulative_generation,
                    'limiting_factor': limiting,
                    'sources': ', '.join(set(sources)) if sources else 'None'
                })
        
        self.analysis['capacity_trajectory'] = trajectory
    
    def _build_critical_path(self):
        """Build critical path with dependencies."""
        tasks = []
        
        # Add standard tasks for each phase
        for phase in self.d.phases:
            phase_num = phase.phase_number
            prefix = f"P{phase_num}"
            
            # Studies sequence
            if phase.studies.system_impact_study != StudyStatus.COMPLETE:
                tasks.append({
                    'id': f"{prefix}_SIS",
                    'name': f"Phase {phase_num}: System Impact Study",
                    'category': 'study',
                    'phase': phase_num,
                    'duration_months': STANDARD_LEAD_TIMES['system_impact_study'],
                    'status': phase.studies.system_impact_study.value,
                    'depends_on': [],
                    'enables': [f"{prefix}_FS"],
                    'responsible': self.d.utility_name,
                    'target': phase.studies.sis_completion_date
                })
            
            if phase.studies.facilities_study != StudyStatus.COMPLETE:
                tasks.append({
                    'id': f"{prefix}_FS",
                    'name': f"Phase {phase_num}: Facilities Study",
                    'category': 'study',
                    'phase': phase_num,
                    'duration_months': STANDARD_LEAD_TIMES['facilities_study'],
                    'status': phase.studies.facilities_study.value,
                    'depends_on': [f"{prefix}_SIS"],
                    'enables': [f"{prefix}_FA"],
                    'responsible': self.d.utility_name,
                    'target': phase.studies.fs_completion_date
                })
            
            if phase.studies.facilities_agreement != StudyStatus.APPROVED:
                tasks.append({
                    'id': f"{prefix}_FA",
                    'name': f"Phase {phase_num}: Facilities Agreement",
                    'category': 'approval',
                    'phase': phase_num,
                    'duration_months': STANDARD_LEAD_TIMES['facilities_agreement'],
                    'status': phase.studies.facilities_agreement.value,
                    'depends_on': [f"{prefix}_FS"],
                    'enables': [f"{prefix}_IA", f"{prefix}_EQUIP"],
                    'responsible': 'Developer / Utility',
                    'target': phase.studies.fa_execution_date
                })
            
            # Equipment based on voltage
            if phase.voltage_kv >= 345:
                xfmr_lead = STANDARD_LEAD_TIMES['transformer_345kv']
            elif phase.voltage_kv >= 230:
                xfmr_lead = STANDARD_LEAD_TIMES['transformer_230kv']
            else:
                xfmr_lead = STANDARD_LEAD_TIMES['transformer_115kv']
            
            tasks.append({
                'id': f"{prefix}_XFMR",
                'name': f"Phase {phase_num}: Transformer Procurement ({phase.voltage_kv}kV)",
                'category': 'equipment',
                'phase': phase_num,
                'duration_months': xfmr_lead,
                'status': 'not_started',
                'depends_on': [f"{prefix}_FA"],
                'enables': [f"{prefix}_CONST"],
                'responsible': 'Developer / Utility',
                'acceleration': 'Pre-order with cancellation risk'
            })
            
            # Breakers
            breaker_type = 'customer_provided' if phase.customer_provided_equipment else 'high_voltage'
            tasks.append({
                'id': f"{prefix}_BKR",
                'name': f"Phase {phase_num}: Breaker Procurement",
                'category': 'equipment',
                'phase': phase_num,
                'duration_months': STANDARD_LEAD_TIMES[f'breaker_{breaker_type}'],
                'status': 'not_started',
                'depends_on': [f"{prefix}_FA"],
                'enables': [f"{prefix}_CONST"],
                'responsible': 'Developer' if 'customer' in breaker_type else 'Utility',
                'acceleration': 'Customer-provided breakers save ~6 months'
            })
            
            # Transmission if needed
            if phase.requires_new_transmission:
                tx_months = int(phase.transmission_distance_miles * STANDARD_LEAD_TIMES['transmission_per_mile'])
                tasks.append({
                    'id': f"{prefix}_TX",
                    'name': f"Phase {phase_num}: Transmission Construction ({phase.transmission_distance_miles} mi)",
                    'category': 'infrastructure',
                    'phase': phase_num,
                    'duration_months': tx_months,
                    'status': 'not_started',
                    'depends_on': [f"{prefix}_FA"],
                    'enables': [f"{prefix}_CONST"],
                    'responsible': self.d.utility_name
                })
            
            # Substation
            if phase.requires_new_substation:
                tasks.append({
                    'id': f"{prefix}_SUB",
                    'name': f"Phase {phase_num}: New Substation",
                    'category': 'infrastructure',
                    'phase': phase_num,
                    'duration_months': STANDARD_LEAD_TIMES['substation_new'],
                    'status': 'not_started',
                    'depends_on': [f"{prefix}_FA"],
                    'enables': [f"{prefix}_CONST"],
                    'responsible': self.d.utility_name
                })
            elif phase.requires_substation_upgrade:
                tasks.append({
                    'id': f"{prefix}_SUB",
                    'name': f"Phase {phase_num}: Substation Upgrade",
                    'category': 'infrastructure',
                    'phase': phase_num,
                    'duration_months': STANDARD_LEAD_TIMES['substation_upgrade'],
                    'status': 'not_started',
                    'depends_on': [f"{prefix}_FA"],
                    'enables': [f"{prefix}_CONST"],
                    'responsible': self.d.utility_name
                })
        
        # Add onsite generation tasks
        for i, gen in enumerate(self.d.onsite_generation):
            prefix = f"GEN{i+1}"
            
            if gen.source == PowerSource.NATURAL_GAS:
                # Gas generation tasks
                tasks.append({
                    'id': f"{prefix}_PERMIT",
                    'name': f"Gas Generation Permitting ({gen.capacity_mw}MW)",
                    'category': 'approval',
                    'phase': 0,
                    'duration_months': 12,
                    'status': 'not_started',
                    'depends_on': [],
                    'enables': [f"{prefix}_CONST"],
                    'responsible': gen.operator or 'Developer/IPP'
                })
                
                if gen.gas_pipeline_required:
                    tasks.append({
                        'id': f"{prefix}_PIPE",
                        'name': f"Gas Pipeline ({gen.gas_pipeline_distance_miles} mi)",
                        'category': 'infrastructure',
                        'phase': 0,
                        'duration_months': int(gen.gas_pipeline_distance_miles * STANDARD_LEAD_TIMES['gas_pipeline_per_mile']),
                        'status': 'not_started',
                        'depends_on': [f"{prefix}_PERMIT"],
                        'enables': [f"{prefix}_CONST"],
                        'responsible': 'Gas utility / Developer'
                    })
                
                tasks.append({
                    'id': f"{prefix}_CONST",
                    'name': f"Gas Generation Construction ({gen.capacity_mw}MW)",
                    'category': 'generation',
                    'phase': 0,
                    'duration_months': STANDARD_LEAD_TIMES['gas_turbine_simple'],
                    'status': 'not_started',
                    'depends_on': [f"{prefix}_PERMIT"] + ([f"{prefix}_PIPE"] if gen.gas_pipeline_required else []),
                    'enables': [],
                    'responsible': gen.operator or 'Developer/IPP',
                    'target': gen.target_cod
                })
            
            elif gen.source == PowerSource.SOLAR:
                tasks.append({
                    'id': f"{prefix}_CONST",
                    'name': f"Solar Construction ({gen.capacity_mw}MW)",
                    'category': 'generation',
                    'phase': 0,
                    'duration_months': STANDARD_LEAD_TIMES['solar_utility_scale'],
                    'status': 'not_started',
                    'depends_on': [],
                    'enables': [],
                    'responsible': gen.operator or 'Developer/IPP',
                    'target': gen.target_cod
                })
            
            elif gen.source == PowerSource.NUCLEAR_SMR:
                tasks.append({
                    'id': f"{prefix}_NRC",
                    'name': f"SMR NRC Licensing ({gen.capacity_mw}MW)",
                    'category': 'approval',
                    'phase': 0,
                    'duration_months': STANDARD_LEAD_TIMES['smr_licensing'],
                    'status': gen.nrc_licensing_status or 'not_started',
                    'depends_on': [],
                    'enables': [f"{prefix}_CONST"],
                    'responsible': 'SMR Vendor / NRC'
                })
                
                tasks.append({
                    'id': f"{prefix}_CONST",
                    'name': f"SMR Construction ({gen.capacity_mw}MW)",
                    'category': 'generation',
                    'phase': 0,
                    'duration_months': STANDARD_LEAD_TIMES['smr_construction'],
                    'status': 'not_started',
                    'depends_on': [f"{prefix}_NRC"],
                    'enables': [],
                    'responsible': 'SMR Vendor',
                    'target': gen.target_cod
                })
        
        # Add any custom tasks from input
        for task in self.d.critical_path_tasks:
            tasks.append({
                'id': task.task_id,
                'name': task.task_name,
                'category': task.category,
                'phase': task.phase,
                'duration_months': task.duration_months,
                'status': task.status.value,
                'depends_on': task.depends_on,
                'enables': task.enables,
                'responsible': task.responsible_party,
                'target': task.target_completion
            })
        
        self.analysis['critical_path'] = tasks
    
    def _identify_bottlenecks(self):
        """Identify bottlenecks and critical constraints."""
        bottlenecks = []
        
        # Check capacity trajectory for constraints
        for i, year_data in enumerate(self.analysis.get('capacity_trajectory', [])):
            if year_data['interconnection_mw'] > 0 or year_data['generation_mw'] > 0:
                if year_data['limiting_factor'] == 'interconnection':
                    bottlenecks.append({
                        'year': year_data['year'],
                        'type': 'interconnection_constraint',
                        'detail': f"Interconnection ({year_data['interconnection_mw']}MW) limits available power vs generation ({year_data['generation_mw']}MW)",
                        'impact_mw': year_data['generation_mw'] - year_data['interconnection_mw']
                    })
                elif year_data['limiting_factor'] == 'generation':
                    bottlenecks.append({
                        'year': year_data['year'],
                        'type': 'generation_constraint',
                        'detail': f"Generation ({year_data['generation_mw']}MW) limits available power vs interconnection ({year_data['interconnection_mw']}MW)",
                        'impact_mw': year_data['interconnection_mw'] - year_data['generation_mw']
                    })
        
        # Check critical path for long-lead items
        for task in self.analysis.get('critical_path', []):
            if task['duration_months'] >= 24:
                bottlenecks.append({
                    'type': 'long_lead_time',
                    'task': task['name'],
                    'duration_months': task['duration_months'],
                    'detail': f"{task['name']} requires {task['duration_months']} months",
                    'acceleration': task.get('acceleration', 'None identified')
                })
        
        # Check for study delays
        for phase in self.d.phases:
            if phase.studies.system_impact_study == StudyStatus.NOT_STARTED:
                bottlenecks.append({
                    'type': 'study_not_started',
                    'phase': phase.phase_number,
                    'detail': f"Phase {phase.phase_number}: SIS not started - delays all downstream"
                })
        
        self.analysis['bottlenecks'] = bottlenecks
    
    def _assess_risks(self):
        """Assess risks to power delivery."""
        risks = []
        
        # Phase timing risks
        for phase in self.d.phases:
            if phase.current_projected_date and phase.target_online_date:
                if phase.current_projected_date > phase.target_online_date:
                    delay = (phase.current_projected_date - phase.target_online_date).days
                    risks.append({
                        'category': 'schedule',
                        'severity': 'high' if delay > 180 else 'medium',
                        'detail': f"Phase {phase.phase_number} projected {delay} days behind target",
                        'mitigation': 'Evaluate acceleration options'
                    })
        
        # Study/approval risks
        for phase in self.d.phases:
            if phase.studies.facilities_study == StudyStatus.NOT_STARTED and phase.phase_number == 1:
                risks.append({
                    'category': 'approval',
                    'severity': 'high',
                    'detail': f"Phase {phase.phase_number}: Facilities Study not started",
                    'mitigation': 'Expedite SIS completion and FS initiation'
                })
        
        # Equipment procurement risks
        for phase in self.d.phases:
            if phase.voltage_kv >= 345:
                risks.append({
                    'category': 'equipment',
                    'severity': 'high',
                    'detail': f"Phase {phase.phase_number}: 345kV transformer lead time is 36+ months",
                    'mitigation': 'Consider early procurement with cancellation risk, or customer-provided option'
                })
        
        # Add input risks
        for risk in self.d.key_risks:
            risks.append({
                'category': 'identified',
                'severity': 'medium',
                'detail': risk,
                'mitigation': 'TBD'
            })
        
        self.analysis['risks'] = risks
    
    def _generate_recommendations(self):
        """Generate actionable recommendations."""
        recommendations = []
        
        # Based on bottlenecks
        for bn in self.analysis.get('bottlenecks', []):
            if bn['type'] == 'study_not_started':
                recommendations.append({
                    'priority': 1,
                    'action': f"Initiate System Impact Study for Phase {bn['phase']}",
                    'rationale': 'Studies are on critical path - delay cascades to all downstream',
                    'timeline': 'Immediate'
                })
            elif bn['type'] == 'long_lead_time' and 'transformer' in bn['task'].lower():
                recommendations.append({
                    'priority': 1,
                    'action': 'Evaluate early transformer procurement',
                    'rationale': f"{bn['duration_months']} month lead time - consider at-risk order",
                    'timeline': 'Within 30 days'
                })
            elif bn['type'] == 'generation_constraint':
                recommendations.append({
                    'priority': 2,
                    'action': f"Accelerate generation capacity for {bn['year']}",
                    'rationale': f"Generation limits available power by {bn['impact_mw']}MW",
                    'timeline': 'Evaluate within 60 days'
                })
        
        # Based on risks
        for risk in self.analysis.get('risks', []):
            if risk['severity'] == 'high' and risk['category'] == 'equipment':
                recommendations.append({
                    'priority': 1,
                    'action': 'Explore customer-provided breakers',
                    'rationale': 'Can compress timeline by 6+ months',
                    'timeline': 'Within 30 days'
                })
        
        # Standard recommendations
        if not any(p.studies.facilities_agreement == StudyStatus.APPROVED for p in self.d.phases):
            recommendations.append({
                'priority': 1,
                'action': 'Confirm study/approval timeline with utility',
                'rationale': 'No Facilities Agreement in place - all power dates at risk',
                'timeline': 'Immediate'
            })
        
        # Add input opportunities
        for opp in self.d.acceleration_opportunities:
            recommendations.append({
                'priority': 2,
                'action': opp,
                'rationale': 'Identified acceleration opportunity',
                'timeline': 'Evaluate'
            })
        
        # Sort by priority
        recommendations.sort(key=lambda x: x['priority'])
        
        self.analysis['recommendations'] = recommendations
    
    def get_report(self) -> Dict:
        """Return complete analysis report."""
        return {
            'site': {
                'name': self.d.site_name,
                'state': self.d.state,
                'utility': self.d.utility_name,
                'total_capacity_mw': self.d.total_target_capacity_mw,
                'num_phases': len(self.d.phases),
                'assessment_date': self.d.assessment_date.isoformat() if self.d.assessment_date else None
            },
            'phases': self.analysis.get('phases', []),
            'capacity_trajectory': self.analysis.get('capacity_trajectory', []),
            'critical_path': self.analysis.get('critical_path', []),
            'bottlenecks': self.analysis.get('bottlenecks', []),
            'risks': self.analysis.get('risks', []),
            'recommendations': self.analysis.get('recommendations', []),
            'open_questions': self.d.open_questions,
            'non_power': {
                'zoning_status': self.d.non_power.zoning_status,
                'zoning_timeline_months': self.d.non_power.zoning_expected_duration_months,
                'water_consumption_gpd': self.d.non_power.water_consumption_gpd,
                'wastewater_discharge_gpd': self.d.non_power.wastewater_discharge_gpd,
                'water_capacity_gpd': self.d.non_power.water_capacity_available_gpd,
                'wastewater_capacity_gpd': self.d.non_power.wastewater_capacity_available_gpd
            }
        }


# =============================================================================
# INQUIRY CHECKLIST GENERATOR
# =============================================================================

def generate_inquiry_checklist(site_name: str, utility: str, phases: List[int], 
                               total_mw: int) -> str:
    """
    Generate a comprehensive inquiry checklist for a new site.
    Based on the user's real-world DD template.
    """
    
    checklist = f"""
================================================================================
SITE DIAGNOSTIC INQUIRY CHECKLIST
================================================================================
Site: {site_name}
Utility: {utility}
Target Capacity: {total_mw}MW

Date: {date.today().isoformat()}

--------------------------------------------------------------------------------
POWER SYSTEM STUDIES & APPROVALS
--------------------------------------------------------------------------------

What is the stage of power system studies and approvals with {utility} for each phase?

For each phase, provide status of:
[ ] System Impact Study (SIS) - Status, start date, completion date
[ ] Facilities Study (FS) - Status, start date, completion date, cost estimate
[ ] Facilities Agreement (FA) - Status, execution date, required deposits
[ ] Interconnection Agreement (IA) - Status, execution date

"""
    
    for p in phases:
        checklist += f"""
Phase {p}:
  - SIS Status: _________________ Completion Date: _____________
  - FS Status: __________________ Completion Date: _____________
  - FA Status: __________________ Execution Date: ______________
  - IA Status: __________________ Execution Date: ______________

"""

    checklist += f"""
--------------------------------------------------------------------------------
POWER CAPACITY & PHASING
--------------------------------------------------------------------------------

Confirm the total power capacity and phasing for the site:

"""
    
    for p in phases:
        checklist += f"""Phase {p}:
  - Interconnection Capacity: _________ MW
  - Generation Capacity: _________ MW  
  - IT Load Capacity: _________ MW
  - Target Online Date: _____________
  - Power Sources: [ ] Utility Grid  [ ] Nat Gas  [ ] Solar  [ ] Battery  [ ] Other: _____
  - Is this permanent or temporary/bridge? _____________

"""

    checklist += f"""
--------------------------------------------------------------------------------
INTERCONNECTION DETAILS (Per Phase)
--------------------------------------------------------------------------------

For each phase, describe the scope of interconnection:

"""
    
    for p in phases:
        checklist += f"""Phase {p}:
  - Voltage: _________ kV
  - Service Type: [ ] Switching Station  [ ] Radial  [ ] Loop  [ ] Network
  - Transmission extension required? [ ] Yes  [ ] No
    If yes, distance: _________ miles
  - New substation required? [ ] Yes  [ ] No
  - Substation upgrade required? [ ] Yes  [ ] No
  - Nearest existing transmission voltage: _________ kV, distance: _________ miles
  - Interface point: _________________________________

"""

    checklist += f"""
--------------------------------------------------------------------------------
ONSITE GENERATION
--------------------------------------------------------------------------------

For each onsite/BTM generation source:

Natural Gas:
  - Capacity: _________ MW
  - Contract Structure: [ ] Utility-owned  [ ] PPA (3rd party)  [ ] Self-owned
  - Operator: _________________________________
  - Target COD: _____________
  - Gas pipeline required? [ ] Yes  [ ] No
    If yes, distance: _________ miles
  - Gas pipeline upgrade scope: _________________________________
  - Gas study status: _________________________________

Solar:
  - Capacity: _________ MW
  - Contract Structure: [ ] Utility-owned  [ ] PPA (3rd party)  [ ] Self-owned
  - Land required: _________ acres
  - Target COD: _____________

Battery Storage:
  - Capacity: _________ MW / _________ MWh
  - Contract Structure: [ ] Utility-owned  [ ] PPA (3rd party)  [ ] Self-owned
  - Target COD: _____________

SMR/Nuclear (if applicable):
  - Capacity: _________ MW
  - Vendor: _________________________________
  - NRC licensing status: _________________________________
  - Site characterization complete? [ ] Yes  [ ] No
  - Target COD: _____________
  - Study scope/status: _________________________________

--------------------------------------------------------------------------------
YEAR-BY-YEAR CAPACITY BREAKDOWN
--------------------------------------------------------------------------------

Provide interconnection capacity AND generation capacity for each year.
These may differ (e.g., 300MW interconnect but only 200MW generation available).

"""
    
    for year in range(2025, 2036):
        checklist += f"""{year}:
  Interconnection: _________ MW (cumulative: _________ MW)
  Generation: _________ MW (cumulative: _________ MW)
  Sources: _________________________________

"""

    checklist += f"""
--------------------------------------------------------------------------------
TIMELINE ACCELERATION
--------------------------------------------------------------------------------

[ ] What is driving the timeline for the first phase and has there been 
    exploration of ways to compress? Consider:
    - Generation capacity additions
    - Customer-provided breakers
    - Early transformer procurement
    - Temporary/bridge solutions
    - Alternative interconnection points

[ ] What equipment is on critical path?
    - Transformers: Lead time _________ months
    - Breakers: Lead time _________ months
    - Switchgear: Lead time _________ months

[ ] Are there customer-provided equipment options that could accelerate?
    _________________________________________________________________

--------------------------------------------------------------------------------
NON-POWER ITEMS
--------------------------------------------------------------------------------

Zoning:
  - Current status: [ ] Not started  [ ] Pre-application  [ ] Submitted  [ ] Approved
  - Expected duration: _________ months
  - Key conditions/requirements: _________________________________

Water:
  - Consumption (GPD): _________
  - Source: _________________________________
  - Capacity available (GPD): _________
  - Rights secured? [ ] Yes  [ ] No

Wastewater:
  - Discharge (GPD): _________
  - Treatment: [ ] Municipal  [ ] Onsite  [ ] Zero discharge
  - Capacity available (GPD): _________

Environmental:
  - Phase 1 complete? [ ] Yes  [ ] No
  - Phase 2 required? [ ] Yes  [ ] No
  - Known issues: _________________________________

Fiber:
  - Lit building? [ ] Yes  [ ] No
  - Providers: _________________________________
  - Extension required: _________ miles

--------------------------------------------------------------------------------
OPEN QUESTIONS / ISSUES
--------------------------------------------------------------------------------

1. _________________________________________________________________

2. _________________________________________________________________

3. _________________________________________________________________

4. _________________________________________________________________

5. _________________________________________________________________

--------------------------------------------------------------------------------
KEY RISKS
--------------------------------------------------------------------------------

1. _________________________________________________________________

2. _________________________________________________________________

3. _________________________________________________________________

--------------------------------------------------------------------------------
ACCELERATION OPPORTUNITIES
--------------------------------------------------------------------------------

1. _________________________________________________________________

2. _________________________________________________________________

3. _________________________________________________________________

================================================================================
"""
    
    return checklist


# =============================================================================
# EXAMPLE / DEMO
# =============================================================================

if __name__ == "__main__":
    # Example: 2GW+ site similar to user's inquiry
    
    diagnostic = SiteDiagnostic(
        site_name="Example 2GW Site",
        state="OK",
        utility_name="PSO",
        developer_name="Example Developer",
        total_site_acreage=2000,
        total_target_capacity_mw=2000,
        
        phases=[
            PowerPhase(
                phase_number=1,
                phase_name="Initial Power",
                interconnection_capacity_mw=120,
                generation_capacity_mw=120,
                it_load_capacity_mw=92,
                target_online_date=date(2029, 1, 1),
                voltage_kv=115,
                service_type=ServiceType.RADIAL,
                transmission_distance_miles=5,
                requires_new_transmission=True,
                primary_source=PowerSource.UTILITY_GRID,
                power_sources=[PowerSource.UTILITY_GRID],
                studies=StudyApprovalStatus(
                    system_impact_study=StudyStatus.IN_PROGRESS,
                    sis_completion_date=date(2025, 6, 1),
                    facilities_study=StudyStatus.NOT_STARTED
                )
            ),
            PowerPhase(
                phase_number=2,
                phase_name="Expansion",
                interconnection_capacity_mw=500,
                generation_capacity_mw=500,
                it_load_capacity_mw=385,
                target_online_date=date(2030, 6, 1),
                voltage_kv=230,
                service_type=ServiceType.SWITCHING_STATION,
                transmission_distance_miles=8,
                requires_new_transmission=True,
                requires_new_substation=True,
                primary_source=PowerSource.UTILITY_GRID,
                power_sources=[PowerSource.UTILITY_GRID, PowerSource.NATURAL_GAS],
                studies=StudyApprovalStatus(
                    system_impact_study=StudyStatus.NOT_STARTED
                )
            ),
            PowerPhase(
                phase_number=3,
                phase_name="1GW+ Buildout",
                interconnection_capacity_mw=1000,
                generation_capacity_mw=1000,
                it_load_capacity_mw=770,
                target_online_date=date(2032, 1, 1),
                voltage_kv=345,
                service_type=ServiceType.SWITCHING_STATION,
                transmission_distance_miles=35,
                requires_new_transmission=True,
                requires_new_substation=True,
                primary_source=PowerSource.UTILITY_GRID,
                power_sources=[PowerSource.UTILITY_GRID, PowerSource.NUCLEAR_SMR]
            )
        ],
        
        onsite_generation=[
            OnsiteGeneration(
                source=PowerSource.NATURAL_GAS,
                capacity_mw=200,
                contract_structure=ContractStructure.PPA_THIRD_PARTY,
                operator="IPP Partner",
                target_cod=date(2029, 6, 1),
                gas_pipeline_required=True,
                gas_pipeline_distance_miles=12,
                gas_pipeline_upgrade_scope="New 12-inch lateral from main"
            ),
            OnsiteGeneration(
                source=PowerSource.SOLAR,
                capacity_mw=100,
                contract_structure=ContractStructure.PPA_THIRD_PARTY,
                land_required_acres=500,
                target_cod=date(2028, 12, 1)
            ),
            OnsiteGeneration(
                source=PowerSource.NUCLEAR_SMR,
                capacity_mw=300,
                contract_structure=ContractStructure.TBD,
                operator="NuScale",
                target_cod=date(2033, 1, 1),
                nrc_licensing_status="Pre-application",
                site_characterization_complete=False
            )
        ],
        
        non_power=NonPowerItems(
            zoning_status="pre-app",
            zoning_expected_duration_months=12,
            water_consumption_gpd=3100000,  # 3.1 MGD
            wastewater_discharge_gpd=2500000,
            water_source="municipal",
            water_capacity_available_gpd=5000000,
            wastewater_capacity_available_gpd=3000000
        ),
        
        open_questions=[
            "Confirm total power capacity phasing - states 2GW+ but only shows 1.62GW in phases",
            "What is driving the 2029 timeline for first 120MW and can it be compressed?",
            "Is 345kV being upgraded/provided? Nearest 345kV appears 35 miles away.",
            "Clarify if 3.1 MGD is water consumption or WW discharge",
            "Describe scope of Phase 4 if planned beyond 1.62GW"
        ],
        
        key_risks=[
            "345kV transformer lead time (36+ months)",
            "Gas pipeline permitting timeline",
            "SMR licensing uncertainty"
        ],
        
        acceleration_opportunities=[
            "Customer-provided breakers for Phase 1",
            "Early transformer procurement with cancellation risk",
            "Temporary generation bridge solution"
        ]
    )
    
    # Run analysis
    engine = SiteDiagnosticEngine(diagnostic)
    report = engine.run_analysis()
    
    # Print summary
    print("=" * 70)
    print(f"SITE DIAGNOSTIC: {report['site']['name']}")
    print("=" * 70)
    
    print(f"\nTotal Capacity: {report['site']['total_capacity_mw']}MW across {report['site']['num_phases']} phases")
    print(f"Utility: {report['site']['utility']}")
    
    print("\n--- PHASE SUMMARY ---")
    for phase in report['phases']:
        print(f"\nPhase {phase['phase']}: {phase['name']}")
        print(f"  Interconnection: {phase['interconnection_mw']}MW | Generation: {phase['generation_mw']}MW")
        print(f"  Voltage: {phase['voltage_kv']}kV | Service: {phase['service_type']}")
        print(f"  Target: {phase['target_date']} | Studies: {phase['study_status']['overall']}")
        if phase['issues']:
            for issue in phase['issues']:
                print(f"  ⚠️  {issue}")
    
    print("\n--- CAPACITY TRAJECTORY ---")
    print(f"{'Year':<6} {'Interconn':<12} {'Generation':<12} {'Available':<12} {'IT Load':<10} {'Limiting'}")
    print("-" * 70)
    for year in report['capacity_trajectory']:
        if year['interconnection_mw'] > 0 or year['generation_mw'] > 0:
            print(f"{year['year']:<6} {year['interconnection_mw']:<12} {year['generation_mw']:<12} {year['available_mw']:<12} {year['it_load_mw']:<10} {year['limiting_factor']}")
    
    print("\n--- CRITICAL PATH TASKS ---")
    for task in report['critical_path'][:10]:
        deps = ', '.join(task['depends_on']) if task['depends_on'] else 'None'
        print(f"  [{task['status'][:8]:<8}] {task['name'][:45]:<45} ({task['duration_months']}mo) → Depends: {deps[:20]}")
    if len(report['critical_path']) > 10:
        print(f"  ... and {len(report['critical_path']) - 10} more tasks")
    
    print("\n--- BOTTLENECKS ---")
    for bn in report['bottlenecks'][:5]:
        print(f"  • {bn['type']}: {bn['detail'][:60]}")
    
    print("\n--- TOP RECOMMENDATIONS ---")
    for rec in report['recommendations'][:5]:
        print(f"  {rec['priority']}. {rec['action']}")
        print(f"     → {rec['rationale']}")
    
    print("\n--- OPEN QUESTIONS ---")
    for q in report['open_questions']:
        print(f"  ? {q}")
    
    print("\n--- NON-POWER STATUS ---")
    np = report['non_power']
    print(f"  Zoning: {np['zoning_status']} ({np['zoning_timeline_months']} months expected)")
    print(f"  Water: {np['water_consumption_gpd']:,} GPD consumption, {np['water_capacity_gpd']:,} GPD available")
    print(f"  Wastewater: {np['wastewater_discharge_gpd']:,} GPD discharge, {np['wastewater_capacity_gpd']:,} GPD available")
    
    # Generate inquiry checklist
    print("\n" + "=" * 70)
    print("INQUIRY CHECKLIST (for new sites)")
    print("=" * 70)
    checklist = generate_inquiry_checklist(
        site_name="[Site Name]",
        utility="[Utility]",
        phases=[1, 2, 3, 4],
        total_mw=2000
    )
    print(checklist[:3000])  # Print first part
    print("... [truncated] ...")
