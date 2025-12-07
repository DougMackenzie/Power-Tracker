"""
Critical Path to Energization Module
=====================================
Comprehensive critical path tracking with dynamic milestones, what-if scenarios,
and buyer/seller responsibility demarcation.

Integration:
1. Add this file to your portfolio_manager folder
2. Add critical_path_json column to Google Sheets
3. Import in streamlit_app.py (see INTEGRATION section at bottom)

Author: Portfolio Manager Extension
Version: 1.0.0
"""

from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union
import json
import re

# =============================================================================
# ENUMS & CONSTANTS
# =============================================================================

class Owner(str, Enum):
    """Responsible party for milestone."""
    SELLER = "Seller"               # Pre-sale landowner/developer
    BUYER = "Buyer"                 # Post-sale developer/operator
    CUSTOMER = "Customer"           # Generic customer (either)
    UTILITY = "Utility"             # Electric utility
    ISO = "ISO/RTO"                 # Grid operator
    COUNTY = "County"               # Local government
    MUNICIPAL = "Municipal"         # City/town
    STATE = "State"                 # State agencies
    FEDERAL = "Federal"             # Federal agencies
    VENDOR = "Vendor"               # Equipment vendors
    CONTRACTOR = "Contractor"       # Construction contractors
    LENDER = "Lender"               # Debt/equity providers
    END_USER = "End User"           # Hyperscaler/tenant
    CONSULTANT = "Consultant"       # Third-party consultants
    GAS_UTILITY = "Gas Utility"     # Natural gas provider
    EAAS = "EaaS Provider"          # Energy-as-a-Service (BTM)


class Phase(str, Enum):
    """Development phase."""
    PRE_SALE = "Pre-Sale"           # Due diligence through transaction
    POST_SALE = "Post-Sale"         # Post-transaction through energization


class ControlLevel(str, Enum):
    """Control over milestone timing."""
    FULL = "Full"
    PARTIAL = "Partial"
    NONE = "None"


class MilestoneStatus(str, Enum):
    """Milestone status."""
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETE = "Complete"
    BLOCKED = "Blocked"
    AT_RISK = "At Risk"
    NA = "N/A"


class Workstream(str, Enum):
    """Workstream category."""
    SITE_CONTROL = "Site Control"
    POWER = "Power/Interconnection"
    ZONING = "Zoning & Permitting"
    ENVIRONMENTAL = "Environmental"
    WATER = "Water"
    FIBER = "Fiber/Telecom"
    BTM = "BTM Generation"
    MARKETING = "Marketing/End User"
    FINANCING = "Financing"
    CONSTRUCTION = "Construction"
    EQUIPMENT = "Equipment Procurement"
    TRANSACTION = "Transaction"


# =============================================================================
# DEFAULT LEAD TIMES (weeks) - User can override
# =============================================================================

DEFAULT_LEAD_TIMES = {
    # Equipment (min, typical, max in weeks)
    'transformer_500kv': {'min': 130, 'typical': 182, 'max': 260},    # 2.5-5 years
    'transformer_345kv': {'min': 130, 'typical': 156, 'max': 234},    # 2.5-4.5 years
    'transformer_230kv': {'min': 104, 'typical': 130, 'max': 208},    # 2-4 years
    'transformer_138kv': {'min': 78, 'typical': 104, 'max': 182},     # 1.5-3.5 years
    'transformer_69kv': {'min': 52, 'typical': 78, 'max': 130},       # 1-2.5 years
    'breakers_hv': {'min': 130, 'typical': 156, 'max': 208},          # 2.5-4 years
    'breakers_mv': {'min': 52, 'typical': 78, 'max': 130},            # 1-2.5 years
    'switchgear': {'min': 52, 'typical': 78, 'max': 130},             # 1-2.5 years
    'gas_turbine': {'min': 156, 'typical': 182, 'max': 208},          # 3-4 years
    'recip_engine': {'min': 52, 'typical': 78, 'max': 130},           # 1-2.5 years
    
    # Studies by ISO
    'sis_pjm': {'min': 26, 'typical': 52, 'max': 78},
    'sis_ercot': {'min': 12, 'typical': 26, 'max': 52},
    'sis_spp': {'min': 16, 'typical': 36, 'max': 52},
    'sis_miso': {'min': 20, 'typical': 40, 'max': 65},
    'fs_typical': {'min': 12, 'typical': 24, 'max': 40},
    'screening_typical': {'min': 8, 'typical': 12, 'max': 20},
}

# Owner colors for visualization
OWNER_COLORS = {
    Owner.SELLER: "#10b981",      # Emerald
    Owner.BUYER: "#3b82f6",       # Blue
    Owner.CUSTOMER: "#22c55e",    # Green
    Owner.UTILITY: "#6366f1",     # Indigo
    Owner.ISO: "#8b5cf6",         # Violet
    Owner.COUNTY: "#a855f7",      # Purple
    Owner.MUNICIPAL: "#d946ef",   # Fuchsia
    Owner.STATE: "#ec4899",       # Pink
    Owner.FEDERAL: "#ef4444",     # Red
    Owner.VENDOR: "#f97316",      # Orange
    Owner.CONTRACTOR: "#f59e0b",  # Amber
    Owner.LENDER: "#0891b2",      # Cyan
    Owner.END_USER: "#14b8a6",    # Teal
    Owner.CONSULTANT: "#78716c",  # Stone
    Owner.GAS_UTILITY: "#ea580c", # Orange dark
    Owner.EAAS: "#7c3aed",        # Violet dark
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MilestoneTemplate:
    """Template definition for a milestone type."""
    id: str
    name: str
    workstream: Workstream
    phase: Phase
    owner: Owner
    
    # Duration defaults (weeks)
    duration_min: int = 1
    duration_typical: int = 4
    duration_max: int = 8
    
    # Control
    control: ControlLevel = ControlLevel.NONE
    
    # Dependencies (other milestone IDs)
    predecessors: List[str] = field(default_factory=list)
    
    # Flags
    is_critical_default: bool = False
    can_be_skipped: bool = False
    
    # Lead time key (for equipment/studies)
    lead_time_key: Optional[str] = None
    
    # Description
    description: str = ""
    
    # Acceleration options
    acceleration_options: List[str] = field(default_factory=list)


@dataclass
class MilestoneInstance:
    """Actual milestone instance for a site."""
    template_id: str
    
    # Status
    status: MilestoneStatus = MilestoneStatus.NOT_STARTED
    completion_pct: int = 0
    
    # Dates
    target_start: Optional[str] = None      # ISO format date string
    actual_start: Optional[str] = None
    target_end: Optional[str] = None
    actual_end: Optional[str] = None
    
    # Override values
    duration_override: Optional[int] = None  # weeks
    owner_override: Optional[str] = None
    
    # Tracking
    assigned_to: str = ""
    notes: str = ""
    blockers: List[str] = field(default_factory=list)
    
    # Document references
    source_docs: List[str] = field(default_factory=list)
    last_updated: Optional[str] = None
    updated_by: str = ""
    
    # Flags
    is_active: bool = True
    on_critical_path: bool = False


@dataclass
class ScenarioOverride:
    """Override for what-if scenario modeling."""
    milestone_id: str
    field: str              # 'duration', 'owner', 'start_date', etc.
    original_value: Any
    new_value: Any
    description: str = ""


@dataclass
class WhatIfScenario:
    """What-if scenario configuration."""
    id: str
    name: str
    description: str
    overrides: List[ScenarioOverride] = field(default_factory=list)
    
    # Results (calculated)
    energization_delta_weeks: int = 0
    new_critical_path: List[str] = field(default_factory=list)


@dataclass
class CriticalPathConfig:
    """Site-level critical path configuration."""
    site_id: str
    
    # Target
    target_energization: Optional[str] = None  # ISO date
    target_mw: int = 0
    voltage_kv: int = 138
    iso: str = "SPP"
    
    # Options
    include_btm: bool = False
    btm_owner: str = "utility"  # utility, eaas, customer
    customer_provides_breakers: bool = False
    bridge_power_strategy: str = "none"  # none, temporary_gen, utility_temp
    
    # Lead time overrides (key -> weeks)
    lead_time_overrides: Dict[str, int] = field(default_factory=dict)
    
    # Active scenarios
    active_scenario_id: Optional[str] = None


@dataclass
class CriticalPathData:
    """Complete critical path data for a site."""
    config: CriticalPathConfig
    milestones: Dict[str, MilestoneInstance] = field(default_factory=dict)
    scenarios: Dict[str, WhatIfScenario] = field(default_factory=dict)
    
    # Analysis results (calculated)
    critical_path: List[str] = field(default_factory=list)
    total_duration_weeks: int = 0
    calculated_energization: Optional[str] = None
    primary_driver: str = ""
    primary_driver_category: str = ""
    schedule_risk: str = "medium"
    
    # Metadata
    last_calculated: Optional[str] = None
    version: str = "1.0"
    
    # AI Agent Data
    document_scan_history: Dict = field(default_factory=dict)
    intelligence_database: Dict = field(default_factory=dict)


# =============================================================================
# MILESTONE TEMPLATES LIBRARY
# =============================================================================

def get_milestone_templates() -> Dict[str, MilestoneTemplate]:
    """
    Return all milestone templates organized by ID.
    Covers both pre-sale and post-sale phases.
    """
    templates = {}
    
    # =========================================================================
    # PRE-SALE: SITE CONTROL (Seller responsibilities)
    # =========================================================================
    presale_site = [
        MilestoneTemplate(
            id="PS-SC-01", name="Site Identified", workstream=Workstream.SITE_CONTROL,
            phase=Phase.PRE_SALE, owner=Owner.SELLER, duration_min=0, duration_typical=0, duration_max=0,
            control=ControlLevel.FULL, description="Initial site identification"
        ),
        MilestoneTemplate(
            id="PS-SC-02", name="Land Option/LOI Executed", workstream=Workstream.SITE_CONTROL,
            phase=Phase.PRE_SALE, owner=Owner.SELLER, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.PARTIAL, predecessors=["PS-SC-01"],
            description="Letter of Intent or Option with landowner"
        ),
        MilestoneTemplate(
            id="PS-SC-03", name="Land Under Contract (PSA)", workstream=Workstream.SITE_CONTROL,
            phase=Phase.PRE_SALE, owner=Owner.SELLER, duration_min=4, duration_typical=8, duration_max=16,
            control=ControlLevel.PARTIAL, predecessors=["PS-SC-02"],
            description="Purchase and Sale Agreement executed"
        ),
        MilestoneTemplate(
            id="PS-SC-04", name="Title Commitment", workstream=Workstream.SITE_CONTROL,
            phase=Phase.PRE_SALE, owner=Owner.CONSULTANT, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.PARTIAL, predecessors=["PS-SC-03"],
            description="Title commitment received"
        ),
        MilestoneTemplate(
            id="PS-SC-05", name="Survey Complete (ALTA)", workstream=Workstream.SITE_CONTROL,
            phase=Phase.PRE_SALE, owner=Owner.CONSULTANT, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.PARTIAL, predecessors=["PS-SC-03"],
            description="ALTA survey complete"
        ),
    ]
    
    # =========================================================================
    # PRE-SALE: POWER/INTERCONNECTION (Utility + Seller)
    # =========================================================================
    presale_power = [
        MilestoneTemplate(
            id="PS-PWR-01", name="Pre-Application Meeting", workstream=Workstream.POWER,
            phase=Phase.PRE_SALE, owner=Owner.SELLER, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.PARTIAL, predecessors=["PS-SC-02"],
            description="Initial utility meeting"
        ),
        MilestoneTemplate(
            id="PS-PWR-02", name="Interconnection Application Filed", workstream=Workstream.POWER,
            phase=Phase.PRE_SALE, owner=Owner.SELLER, duration_min=1, duration_typical=2, duration_max=4,
            control=ControlLevel.FULL, predecessors=["PS-PWR-01"],
            description="Formal application submitted"
        ),
        MilestoneTemplate(
            id="PS-PWR-03", name="Queue Position Assigned", workstream=Workstream.POWER,
            phase=Phase.PRE_SALE, owner=Owner.UTILITY, duration_min=2, duration_typical=4, duration_max=12,
            control=ControlLevel.NONE, predecessors=["PS-PWR-02"],
            description="Application accepted, queue position assigned"
        ),
        MilestoneTemplate(
            id="PS-PWR-04", name="Screening Study Complete", workstream=Workstream.POWER,
            phase=Phase.PRE_SALE, owner=Owner.UTILITY, duration_min=8, duration_typical=12, duration_max=20,
            control=ControlLevel.NONE, predecessors=["PS-PWR-03"],
            lead_time_key="screening_typical", is_critical_default=True,
            description="Initial feasibility/screening study"
        ),
        MilestoneTemplate(
            id="PS-PWR-05", name="System Impact Study (SIS) Complete", workstream=Workstream.POWER,
            phase=Phase.PRE_SALE, owner=Owner.UTILITY, duration_min=16, duration_typical=36, duration_max=78,
            control=ControlLevel.NONE, predecessors=["PS-PWR-04"],
            is_critical_default=True, description="Grid impact analysis - duration varies by ISO"
        ),
        MilestoneTemplate(
            id="PS-PWR-06", name="Facilities Study (FS) Complete", workstream=Workstream.POWER,
            phase=Phase.PRE_SALE, owner=Owner.UTILITY, duration_min=12, duration_typical=24, duration_max=40,
            control=ControlLevel.NONE, predecessors=["PS-PWR-05"],
            lead_time_key="fs_typical", is_critical_default=True,
            description="Detailed engineering and cost estimate"
        ),
        MilestoneTemplate(
            id="PS-PWR-07", name="IA/FA Draft Received", workstream=Workstream.POWER,
            phase=Phase.PRE_SALE, owner=Owner.UTILITY, duration_min=4, duration_typical=8, duration_max=16,
            control=ControlLevel.NONE, predecessors=["PS-PWR-06"],
            description="Draft Interconnection/Facilities Agreement"
        ),
        MilestoneTemplate(
            id="PS-PWR-08", name="IA/FA Negotiation Complete", workstream=Workstream.POWER,
            phase=Phase.PRE_SALE, owner=Owner.SELLER, duration_min=4, duration_typical=12, duration_max=26,
            control=ControlLevel.PARTIAL, predecessors=["PS-PWR-07"],
            description="Agreement terms negotiated",
            acceleration_options=["Engage legal early", "Pre-negotiate standard terms"]
        ),
        MilestoneTemplate(
            id="PS-PWR-09", name="IA/FA Executed", workstream=Workstream.POWER,
            phase=Phase.PRE_SALE, owner=Owner.SELLER, duration_min=1, duration_typical=2, duration_max=4,
            control=ControlLevel.PARTIAL, predecessors=["PS-PWR-08"],
            is_critical_default=True, description="MAJOR MILESTONE - Agreement fully executed"
        ),
        MilestoneTemplate(
            id="PS-PWR-10", name="Interconnection Security Posted", workstream=Workstream.POWER,
            phase=Phase.PRE_SALE, owner=Owner.SELLER, duration_min=1, duration_typical=2, duration_max=4,
            control=ControlLevel.FULL, predecessors=["PS-PWR-09"],
            description="Security/milestone deposit posted"
        ),
    ]
    
    # =========================================================================
    # PRE-SALE: ZONING (Seller + County)
    # =========================================================================
    presale_zoning = [
        MilestoneTemplate(
            id="PS-ZN-01", name="Zoning Due Diligence", workstream=Workstream.ZONING,
            phase=Phase.PRE_SALE, owner=Owner.SELLER, duration_min=1, duration_typical=2, duration_max=4,
            control=ControlLevel.FULL, predecessors=["PS-SC-01"],
            description="Confirm existing zoning, identify requirements"
        ),
        MilestoneTemplate(
            id="PS-ZN-02", name="Pre-Application Meeting (County)", workstream=Workstream.ZONING,
            phase=Phase.PRE_SALE, owner=Owner.SELLER, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.PARTIAL, predecessors=["PS-ZN-01"],
            description="Meeting with planning department"
        ),
        MilestoneTemplate(
            id="PS-ZN-03", name="Zoning Application Filed", workstream=Workstream.ZONING,
            phase=Phase.PRE_SALE, owner=Owner.SELLER, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.FULL, predecessors=["PS-ZN-02"],
            description="Formal zoning application submitted"
        ),
        MilestoneTemplate(
            id="PS-ZN-04", name="Staff Review Complete", workstream=Workstream.ZONING,
            phase=Phase.PRE_SALE, owner=Owner.COUNTY, duration_min=4, duration_typical=12, duration_max=20,
            control=ControlLevel.NONE, predecessors=["PS-ZN-03"],
            description="Planning staff review"
        ),
        MilestoneTemplate(
            id="PS-ZN-05", name="Planning Commission Approval", workstream=Workstream.ZONING,
            phase=Phase.PRE_SALE, owner=Owner.COUNTY, duration_min=1, duration_typical=4, duration_max=8,
            control=ControlLevel.NONE, predecessors=["PS-ZN-04"],
            description="Planning Commission hearing and decision"
        ),
        MilestoneTemplate(
            id="PS-ZN-06", name="Final Zoning Approval", workstream=Workstream.ZONING,
            phase=Phase.PRE_SALE, owner=Owner.COUNTY, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.NONE, predecessors=["PS-ZN-05"],
            is_critical_default=True, description="Zoning approval effective (after appeal period)"
        ),
    ]
    
    # =========================================================================
    # PRE-SALE: ENVIRONMENTAL (Seller + Consultants)
    # =========================================================================
    presale_env = [
        MilestoneTemplate(
            id="PS-ENV-01", name="Phase I ESA Complete", workstream=Workstream.ENVIRONMENTAL,
            phase=Phase.PRE_SALE, owner=Owner.CONSULTANT, duration_min=4, duration_typical=6, duration_max=10,
            control=ControlLevel.PARTIAL, predecessors=["PS-SC-02"],
            description="Environmental Site Assessment"
        ),
        MilestoneTemplate(
            id="PS-ENV-02", name="Wetlands Delineation", workstream=Workstream.ENVIRONMENTAL,
            phase=Phase.PRE_SALE, owner=Owner.CONSULTANT, duration_min=4, duration_typical=8, duration_max=16,
            control=ControlLevel.PARTIAL, predecessors=["PS-SC-02"], can_be_skipped=True,
            description="Wetlands study (if applicable)"
        ),
        MilestoneTemplate(
            id="PS-ENV-03", name="Geotech Study Complete", workstream=Workstream.ENVIRONMENTAL,
            phase=Phase.PRE_SALE, owner=Owner.CONSULTANT, duration_min=4, duration_typical=8, duration_max=12,
            control=ControlLevel.PARTIAL, predecessors=["PS-SC-03"],
            description="Geotechnical investigation"
        ),
    ]
    
    # =========================================================================
    # PRE-SALE: WATER (Seller + Municipal)
    # =========================================================================
    presale_water = [
        MilestoneTemplate(
            id="PS-WTR-01", name="Water Availability Confirmed", workstream=Workstream.WATER,
            phase=Phase.PRE_SALE, owner=Owner.SELLER, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.PARTIAL, predecessors=["PS-SC-02"],
            description="Water provider capacity confirmation"
        ),
        MilestoneTemplate(
            id="PS-WTR-02", name="Will-Serve Letter Received", workstream=Workstream.WATER,
            phase=Phase.PRE_SALE, owner=Owner.MUNICIPAL, duration_min=2, duration_typical=6, duration_max=16,
            control=ControlLevel.NONE, predecessors=["PS-WTR-01"],
            description="Water provider commitment letter"
        ),
    ]
    
    # =========================================================================
    # PRE-SALE: FINANCING (Lender - if security deposit financing needed)
    # =========================================================================
    presale_finance = [
        MilestoneTemplate(
            id="PS-FIN-01", name="Security Financing Term Sheet", workstream=Workstream.FINANCING,
            phase=Phase.PRE_SALE, owner=Owner.LENDER, duration_min=4, duration_typical=8, duration_max=16,
            control=ControlLevel.PARTIAL, predecessors=["PS-PWR-06"], can_be_skipped=True,
            description="Financing for interconnection security deposit (if required)"
        ),
        MilestoneTemplate(
            id="PS-FIN-02", name="Security Financing Closed", workstream=Workstream.FINANCING,
            phase=Phase.PRE_SALE, owner=Owner.LENDER, duration_min=4, duration_typical=8, duration_max=12,
            control=ControlLevel.PARTIAL, predecessors=["PS-FIN-01"], can_be_skipped=True,
            description="Security deposit financing complete"
        ),
    ]
    
    # =========================================================================
    # PRE-SALE: MARKETING / END USER
    # =========================================================================
    presale_marketing = [
        MilestoneTemplate(
            id="PS-MKT-01", name="Marketing Materials Prepared", workstream=Workstream.MARKETING,
            phase=Phase.PRE_SALE, owner=Owner.SELLER, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.FULL, predecessors=["PS-PWR-04"],
            description="Teaser, flyer, VDR established"
        ),
        MilestoneTemplate(
            id="PS-MKT-02", name="Buyer/End User Identified", workstream=Workstream.MARKETING,
            phase=Phase.PRE_SALE, owner=Owner.SELLER, duration_min=12, duration_typical=26, duration_max=52,
            control=ControlLevel.PARTIAL, predecessors=["PS-MKT-01"],
            description="Prospective buyer identified"
        ),
        MilestoneTemplate(
            id="PS-MKT-03", name="Buyer LOI Executed", workstream=Workstream.MARKETING,
            phase=Phase.PRE_SALE, owner=Owner.SELLER, duration_min=4, duration_typical=12, duration_max=26,
            control=ControlLevel.PARTIAL, predecessors=["PS-MKT-02"],
            description="Letter of Intent with buyer"
        ),
    ]
    
    # =========================================================================
    # PRE-SALE: TRANSACTION
    # =========================================================================
    presale_transaction = [
        MilestoneTemplate(
            id="PS-TXN-01", name="Buyer Due Diligence", workstream=Workstream.TRANSACTION,
            phase=Phase.PRE_SALE, owner=Owner.BUYER, duration_min=8, duration_typical=12, duration_max=20,
            control=ControlLevel.PARTIAL, predecessors=["PS-MKT-03"],
            description="Buyer's due diligence period"
        ),
        MilestoneTemplate(
            id="PS-TXN-02", name="PSA Negotiation (Buyer)", workstream=Workstream.TRANSACTION,
            phase=Phase.PRE_SALE, owner=Owner.SELLER, duration_min=4, duration_typical=8, duration_max=16,
            control=ControlLevel.PARTIAL, predecessors=["PS-MKT-03"],
            description="Purchase agreement negotiation"
        ),
        MilestoneTemplate(
            id="PS-TXN-03", name="Transaction Closed", workstream=Workstream.TRANSACTION,
            phase=Phase.PRE_SALE, owner=Owner.SELLER, duration_min=1, duration_typical=2, duration_max=4,
            control=ControlLevel.PARTIAL, 
            predecessors=["PS-TXN-01", "PS-TXN-02", "PS-PWR-09", "PS-ZN-06"],
            is_critical_default=True,
            description="MAJOR MILESTONE - Sale of powered land complete"
        ),
    ]
    
    # =========================================================================
    # POST-SALE: EQUIPMENT PROCUREMENT (Buyer responsibilities)
    # =========================================================================
    postsale_equipment = [
        MilestoneTemplate(
            id="POST-EQ-01", name="Transformer PO Issued", workstream=Workstream.EQUIPMENT,
            phase=Phase.POST_SALE, owner=Owner.BUYER, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.FULL, predecessors=["PS-TXN-03"],
            is_critical_default=True,
            description="Power transformer purchase order (CRITICAL - early procurement recommended)",
            acceleration_options=["Customer-funded early procurement", "Pre-order with utility"]
        ),
        MilestoneTemplate(
            id="POST-EQ-02", name="Transformer Manufacturing", workstream=Workstream.EQUIPMENT,
            phase=Phase.POST_SALE, owner=Owner.VENDOR, duration_min=130, duration_typical=156, duration_max=260,
            control=ControlLevel.NONE, predecessors=["POST-EQ-01"],
            lead_time_key="transformer_345kv", is_critical_default=True,
            description="2.5-5 year lead time depending on voltage"
        ),
        MilestoneTemplate(
            id="POST-EQ-03", name="Transformer Delivered", workstream=Workstream.EQUIPMENT,
            phase=Phase.POST_SALE, owner=Owner.VENDOR, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.NONE, predecessors=["POST-EQ-02"],
            is_critical_default=True, description="Delivery to site"
        ),
        MilestoneTemplate(
            id="POST-EQ-04", name="Breakers PO Issued", workstream=Workstream.EQUIPMENT,
            phase=Phase.POST_SALE, owner=Owner.BUYER, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.FULL, predecessors=["PS-TXN-03"],
            description="High-voltage breakers purchase order",
            acceleration_options=["Customer conveys breakers to utility"]
        ),
        MilestoneTemplate(
            id="POST-EQ-05", name="Breakers Manufacturing", workstream=Workstream.EQUIPMENT,
            phase=Phase.POST_SALE, owner=Owner.VENDOR, duration_min=130, duration_typical=156, duration_max=208,
            control=ControlLevel.NONE, predecessors=["POST-EQ-04"],
            lead_time_key="breakers_hv", is_critical_default=True,
            description="2.5-4 year lead time for HV breakers"
        ),
        MilestoneTemplate(
            id="POST-EQ-06", name="Breakers Delivered", workstream=Workstream.EQUIPMENT,
            phase=Phase.POST_SALE, owner=Owner.VENDOR, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.NONE, predecessors=["POST-EQ-05"],
            description="Delivery to site"
        ),
        MilestoneTemplate(
            id="POST-EQ-07", name="Switchgear PO Issued", workstream=Workstream.EQUIPMENT,
            phase=Phase.POST_SALE, owner=Owner.BUYER, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.FULL, predecessors=["PS-TXN-03"],
            description="Medium-voltage switchgear"
        ),
        MilestoneTemplate(
            id="POST-EQ-08", name="Switchgear Delivered", workstream=Workstream.EQUIPMENT,
            phase=Phase.POST_SALE, owner=Owner.VENDOR, duration_min=52, duration_typical=78, duration_max=130,
            control=ControlLevel.NONE, predecessors=["POST-EQ-07"],
            lead_time_key="switchgear", description="1-2.5 year lead time"
        ),
    ]
    
    # =========================================================================
    # POST-SALE: BTM GENERATION (if applicable)
    # =========================================================================
    postsale_btm = [
        MilestoneTemplate(
            id="POST-BTM-01", name="BTM Strategy Finalized", workstream=Workstream.BTM,
            phase=Phase.POST_SALE, owner=Owner.BUYER, duration_min=4, duration_typical=8, duration_max=16,
            control=ControlLevel.FULL, predecessors=["PS-TXN-03"], can_be_skipped=True,
            description="Behind-the-meter generation strategy (utility, EaaS, or self-owned)"
        ),
        MilestoneTemplate(
            id="POST-BTM-02", name="Gas Turbine PO Issued", workstream=Workstream.BTM,
            phase=Phase.POST_SALE, owner=Owner.BUYER, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.FULL, predecessors=["POST-BTM-01"], can_be_skipped=True,
            description="Gas turbine order (if self-owned or EaaS)"
        ),
        MilestoneTemplate(
            id="POST-BTM-03", name="Gas Turbine Manufacturing", workstream=Workstream.BTM,
            phase=Phase.POST_SALE, owner=Owner.VENDOR, duration_min=156, duration_typical=182, duration_max=208,
            control=ControlLevel.NONE, predecessors=["POST-BTM-02"], can_be_skipped=True,
            lead_time_key="gas_turbine", is_critical_default=True,
            description="3-4 year lead time for gas turbines"
        ),
        MilestoneTemplate(
            id="POST-BTM-04", name="Gas Turbine Delivered", workstream=Workstream.BTM,
            phase=Phase.POST_SALE, owner=Owner.VENDOR, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.NONE, predecessors=["POST-BTM-03"], can_be_skipped=True,
            description="Delivery to site"
        ),
        MilestoneTemplate(
            id="POST-BTM-05", name="Gas Service Agreement", workstream=Workstream.BTM,
            phase=Phase.POST_SALE, owner=Owner.GAS_UTILITY, duration_min=8, duration_typical=16, duration_max=26,
            control=ControlLevel.PARTIAL, predecessors=["POST-BTM-01"], can_be_skipped=True,
            description="Natural gas supply agreement"
        ),
        MilestoneTemplate(
            id="POST-BTM-06", name="Gas Pipeline Construction", workstream=Workstream.BTM,
            phase=Phase.POST_SALE, owner=Owner.GAS_UTILITY, duration_min=12, duration_typical=26, duration_max=52,
            control=ControlLevel.NONE, predecessors=["POST-BTM-05"], can_be_skipped=True,
            description="Gas pipeline extension (if required)"
        ),
    ]
    
    # =========================================================================
    # POST-SALE: UTILITY CONSTRUCTION
    # =========================================================================
    postsale_utility = [
        MilestoneTemplate(
            id="POST-UTL-01", name="Utility Engineering Start", workstream=Workstream.POWER,
            phase=Phase.POST_SALE, owner=Owner.UTILITY, duration_min=0, duration_typical=0, duration_max=0,
            control=ControlLevel.NONE, predecessors=["PS-PWR-10"],
            description="Utility begins detailed engineering"
        ),
        MilestoneTemplate(
            id="POST-UTL-02", name="Utility Engineering IFC", workstream=Workstream.POWER,
            phase=Phase.POST_SALE, owner=Owner.UTILITY, duration_min=16, duration_typical=26, duration_max=40,
            control=ControlLevel.NONE, predecessors=["POST-UTL-01"],
            description="Issued for Construction drawings"
        ),
        MilestoneTemplate(
            id="POST-UTL-03", name="Substation Construction Start", workstream=Workstream.POWER,
            phase=Phase.POST_SALE, owner=Owner.UTILITY, duration_min=0, duration_typical=0, duration_max=0,
            control=ControlLevel.NONE, predecessors=["POST-UTL-02"],
            description="Utility substation construction begins"
        ),
        MilestoneTemplate(
            id="POST-UTL-04", name="Substation Foundation Complete", workstream=Workstream.POWER,
            phase=Phase.POST_SALE, owner=Owner.UTILITY, duration_min=12, duration_typical=20, duration_max=30,
            control=ControlLevel.NONE, predecessors=["POST-UTL-03"],
            description="Civil work complete"
        ),
        MilestoneTemplate(
            id="POST-UTL-05", name="Equipment Installation", workstream=Workstream.POWER,
            phase=Phase.POST_SALE, owner=Owner.UTILITY, duration_min=8, duration_typical=16, duration_max=26,
            control=ControlLevel.NONE, predecessors=["POST-UTL-04", "POST-EQ-03", "POST-EQ-06"],
            is_critical_default=True, description="Transformer and breaker installation"
        ),
        MilestoneTemplate(
            id="POST-UTL-06", name="Transmission Line Complete", workstream=Workstream.POWER,
            phase=Phase.POST_SALE, owner=Owner.UTILITY, duration_min=0, duration_typical=0, duration_max=104,
            control=ControlLevel.NONE, predecessors=["POST-UTL-02"], can_be_skipped=True,
            description="Transmission line extension (if required)"
        ),
        MilestoneTemplate(
            id="POST-UTL-07", name="Substation Mechanical Complete", workstream=Workstream.POWER,
            phase=Phase.POST_SALE, owner=Owner.UTILITY, duration_min=4, duration_typical=8, duration_max=12,
            control=ControlLevel.NONE, predecessors=["POST-UTL-05", "POST-UTL-06"],
            description="Substation mechanically complete"
        ),
        MilestoneTemplate(
            id="POST-UTL-08", name="Commissioning & Testing", workstream=Workstream.POWER,
            phase=Phase.POST_SALE, owner=Owner.UTILITY, duration_min=4, duration_typical=8, duration_max=12,
            control=ControlLevel.NONE, predecessors=["POST-UTL-07"],
            is_critical_default=True, description="Protection relay settings, testing"
        ),
        MilestoneTemplate(
            id="POST-UTL-09", name="ENERGIZATION", workstream=Workstream.POWER,
            phase=Phase.POST_SALE, owner=Owner.UTILITY, duration_min=0, duration_typical=1, duration_max=2,
            control=ControlLevel.NONE, predecessors=["POST-UTL-08", "POST-CON-06"],
            is_critical_default=True, description="⚡ SITE ENERGIZED - Project Complete"
        ),
    ]
    
    # =========================================================================
    # POST-SALE: FINANCING (Construction financing)
    # =========================================================================
    postsale_finance = [
        MilestoneTemplate(
            id="POST-FIN-01", name="Construction Lender RFP", workstream=Workstream.FINANCING,
            phase=Phase.POST_SALE, owner=Owner.BUYER, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.FULL, predecessors=["PS-TXN-03"],
            description="RFP issued to construction lenders"
        ),
        MilestoneTemplate(
            id="POST-FIN-02", name="Lender Selected / Term Sheet", workstream=Workstream.FINANCING,
            phase=Phase.POST_SALE, owner=Owner.BUYER, duration_min=4, duration_typical=8, duration_max=16,
            control=ControlLevel.PARTIAL, predecessors=["POST-FIN-01"],
            description="Lender selection and term sheet"
        ),
        MilestoneTemplate(
            id="POST-FIN-03", name="Lender Due Diligence", workstream=Workstream.FINANCING,
            phase=Phase.POST_SALE, owner=Owner.LENDER, duration_min=8, duration_typical=16, duration_max=26,
            control=ControlLevel.PARTIAL, predecessors=["POST-FIN-02"],
            description="Lender due diligence process"
        ),
        MilestoneTemplate(
            id="POST-FIN-04", name="Credit Approval", workstream=Workstream.FINANCING,
            phase=Phase.POST_SALE, owner=Owner.LENDER, duration_min=2, duration_typical=4, duration_max=8,
            control=ControlLevel.NONE, predecessors=["POST-FIN-03"],
            description="Credit committee approval"
        ),
        MilestoneTemplate(
            id="POST-FIN-05", name="Construction Financing Closed", workstream=Workstream.FINANCING,
            phase=Phase.POST_SALE, owner=Owner.LENDER, duration_min=4, duration_typical=8, duration_max=16,
            control=ControlLevel.PARTIAL, predecessors=["POST-FIN-04"],
            is_critical_default=True, description="Construction loan closed"
        ),
    ]
    
    # =========================================================================
    # POST-SALE: CONSTRUCTION (Buyer/Developer)
    # =========================================================================
    postsale_construction = [
        MilestoneTemplate(
            id="POST-CON-01", name="A/E Selection", workstream=Workstream.CONSTRUCTION,
            phase=Phase.POST_SALE, owner=Owner.BUYER, duration_min=4, duration_typical=8, duration_max=16,
            control=ControlLevel.FULL, predecessors=["PS-TXN-03"],
            description="Architect/Engineer selection"
        ),
        MilestoneTemplate(
            id="POST-CON-02", name="Construction Documents Complete", workstream=Workstream.CONSTRUCTION,
            phase=Phase.POST_SALE, owner=Owner.CONSULTANT, duration_min=20, duration_typical=32, duration_max=52,
            control=ControlLevel.PARTIAL, predecessors=["POST-CON-01"],
            description="Full CD set complete"
        ),
        MilestoneTemplate(
            id="POST-CON-03", name="Building Permit Issued", workstream=Workstream.CONSTRUCTION,
            phase=Phase.POST_SALE, owner=Owner.COUNTY, duration_min=4, duration_typical=12, duration_max=20,
            control=ControlLevel.NONE, predecessors=["POST-CON-02", "PS-ZN-06"],
            description="Building permit issued"
        ),
        MilestoneTemplate(
            id="POST-CON-04", name="GC Selection / NTP", workstream=Workstream.CONSTRUCTION,
            phase=Phase.POST_SALE, owner=Owner.BUYER, duration_min=8, duration_typical=12, duration_max=20,
            control=ControlLevel.FULL, predecessors=["POST-CON-02", "POST-FIN-05"],
            description="General Contractor selected, NTP issued"
        ),
        MilestoneTemplate(
            id="POST-CON-05", name="Building Construction", workstream=Workstream.CONSTRUCTION,
            phase=Phase.POST_SALE, owner=Owner.CONTRACTOR, duration_min=52, duration_typical=78, duration_max=104,
            control=ControlLevel.PARTIAL, predecessors=["POST-CON-03", "POST-CON-04"],
            description="Data center building construction"
        ),
        MilestoneTemplate(
            id="POST-CON-06", name="Customer Facility Ready", workstream=Workstream.CONSTRUCTION,
            phase=Phase.POST_SALE, owner=Owner.BUYER, duration_min=4, duration_typical=8, duration_max=16,
            control=ControlLevel.PARTIAL, predecessors=["POST-CON-05"],
            is_critical_default=True, description="Building ready for energization"
        ),
    ]
    
    # Combine all templates
    all_templates = (
        presale_site + presale_power + presale_zoning + presale_env +
        presale_water + presale_finance + presale_marketing + presale_transaction +
        postsale_equipment + postsale_btm + postsale_utility +
        postsale_finance + postsale_construction
    )
    
    for t in all_templates:
        templates[t.id] = t
    
    return templates


# =============================================================================
# CRITICAL PATH ENGINE
# =============================================================================

class CriticalPathEngine:
    """Engine for calculating and analyzing critical path."""
    
    def __init__(self):
        self.templates = get_milestone_templates()
    
    def initialize_site(
        self,
        site_id: str,
        target_mw: int = 200,
        voltage_kv: int = 138,
        iso: str = "SPP",
        include_btm: bool = False,
        btm_owner: str = "utility",
        customer_provides_breakers: bool = False,
    ) -> CriticalPathData:
        """Initialize critical path data for a new site."""
        
        config = CriticalPathConfig(
            site_id=site_id,
            target_mw=target_mw,
            voltage_kv=voltage_kv,
            iso=iso,
            include_btm=include_btm,
            btm_owner=btm_owner,
            customer_provides_breakers=customer_provides_breakers,
        )
        
        milestones = {}
        
        for tmpl_id, tmpl in self.templates.items():
            # Skip BTM milestones if not applicable
            if tmpl.workstream == Workstream.BTM and not include_btm:
                continue
            
            # Adjust transformer lead time based on voltage
            duration = tmpl.duration_typical
            if tmpl.lead_time_key:
                duration = self._get_adjusted_duration(tmpl, config)
            
            # Create instance
            instance = MilestoneInstance(
                template_id=tmpl_id,
                duration_override=duration if duration != tmpl.duration_typical else None,
                is_active=True,
                on_critical_path=tmpl.is_critical_default,
            )
            
            milestones[tmpl_id] = instance
        
        return CriticalPathData(config=config, milestones=milestones)
    
    def _get_adjusted_duration(self, tmpl: MilestoneTemplate, config: CriticalPathConfig) -> int:
        """Get duration adjusted for configuration."""
        
        # Check for user override first
        if tmpl.lead_time_key and tmpl.lead_time_key in config.lead_time_overrides:
            return config.lead_time_overrides[tmpl.lead_time_key]
        
        # Transformer - adjust for voltage
        if 'transformer' in tmpl.id.lower() or (tmpl.lead_time_key and 'transformer' in tmpl.lead_time_key):
            if config.voltage_kv >= 345:
                key = 'transformer_345kv'
            elif config.voltage_kv >= 230:
                key = 'transformer_230kv'
            elif config.voltage_kv >= 138:
                key = 'transformer_138kv'
            else:
                key = 'transformer_69kv'
            return DEFAULT_LEAD_TIMES.get(key, {}).get('typical', tmpl.duration_typical)
        
        # SIS - adjust for ISO
        if 'sis' in tmpl.name.lower():
            iso_key = f"sis_{config.iso.lower()}"
            if iso_key in DEFAULT_LEAD_TIMES:
                return DEFAULT_LEAD_TIMES[iso_key]['typical']
        
        # Use template lead time key
        if tmpl.lead_time_key and tmpl.lead_time_key in DEFAULT_LEAD_TIMES:
            return DEFAULT_LEAD_TIMES[tmpl.lead_time_key]['typical']
        
        return tmpl.duration_typical
    
    def calculate_schedule(
        self,
        data: CriticalPathData,
        start_date: Optional[date] = None
    ) -> CriticalPathData:
        """Calculate schedule using forward pass algorithm."""
        
        if start_date is None:
            start_date = date.today()
        
        scheduled = {}
        
        def get_duration(ms_id: str) -> int:
            instance = data.milestones.get(ms_id)
            if not instance or not instance.is_active:
                return 0
            if instance.duration_override is not None:
                return instance.duration_override
            tmpl = self.templates.get(ms_id)
            return tmpl.duration_typical if tmpl else 0
        
        def get_earliest_start(ms_id: str) -> date:
            tmpl = self.templates.get(ms_id)
            if not tmpl or not tmpl.predecessors:
                return start_date
            
            earliest = start_date
            for pred_id in tmpl.predecessors:
                if pred_id in scheduled:
                    pred_end = scheduled[pred_id]['end']
                    if pred_end > earliest:
                        earliest = pred_end
            return earliest
        
        # Forward pass
        max_iterations = len(data.milestones) * 2
        iteration = 0
        
        while len(scheduled) < len([m for m in data.milestones.values() if m.is_active]) and iteration < max_iterations:
            iteration += 1
            
            for ms_id, instance in data.milestones.items():
                if ms_id in scheduled or not instance.is_active:
                    continue
                
                tmpl = self.templates.get(ms_id)
                if not tmpl:
                    continue
                
                # Check predecessors
                predecessors_ready = True
                for pred_id in tmpl.predecessors:
                    pred = data.milestones.get(pred_id)
                    if pred and pred.is_active and pred_id not in scheduled:
                        predecessors_ready = False
                        break
                
                if predecessors_ready:
                    ms_start = get_earliest_start(ms_id)
                    duration_weeks = get_duration(ms_id)
                    ms_end = ms_start + timedelta(weeks=duration_weeks)
                    
                    scheduled[ms_id] = {'start': ms_start, 'end': ms_end, 'duration': duration_weeks}
                    
                    # Update instance
                    if instance.target_start is None:
                        instance.target_start = ms_start.isoformat()
                    if instance.target_end is None:
                        instance.target_end = ms_end.isoformat()
        
        # Calculate total duration and find energization date
        if "POST-UTL-09" in scheduled:
            data.calculated_energization = scheduled["POST-UTL-09"]['end'].isoformat()
            data.total_duration_weeks = (scheduled["POST-UTL-09"]['end'] - start_date).days // 7
        
        data.last_calculated = datetime.now().isoformat()
        
        return data
    
    def identify_critical_path(self, data: CriticalPathData) -> List[str]:
        """Identify the critical path to energization."""
        
        end_milestone = "POST-UTL-09"  # ENERGIZATION
        
        def trace_back(ms_id: str, path: List[str]) -> List[str]:
            path.append(ms_id)
            
            tmpl = self.templates.get(ms_id)
            if not tmpl or not tmpl.predecessors:
                return path
            
            # Find predecessor with latest end date
            latest_pred = None
            latest_end = None
            
            for pred_id in tmpl.predecessors:
                instance = data.milestones.get(pred_id)
                if not instance or not instance.is_active:
                    continue
                
                if instance.target_end:
                    end_date = date.fromisoformat(instance.target_end)
                    if latest_end is None or end_date > latest_end:
                        latest_end = end_date
                        latest_pred = pred_id
            
            if latest_pred:
                return trace_back(latest_pred, path)
            
            return path
        
        critical_path = trace_back(end_milestone, [])
        critical_path.reverse()
        
        # Update instances
        for ms_id in critical_path:
            if ms_id in data.milestones:
                data.milestones[ms_id].on_critical_path = True
        
        data.critical_path = critical_path
        
        # Identify primary driver
        if critical_path:
            max_duration = 0
            for ms_id in critical_path:
                instance = data.milestones.get(ms_id)
                tmpl = self.templates.get(ms_id)
                if instance and tmpl:
                    duration = instance.duration_override or tmpl.duration_typical
                    if duration > max_duration:
                        max_duration = duration
                        data.primary_driver = ms_id
                        data.primary_driver_category = tmpl.workstream.value
        
        return critical_path
    
    def apply_scenario(self, data: CriticalPathData, scenario: WhatIfScenario) -> CriticalPathData:
        """Apply a what-if scenario and recalculate."""
        import copy
        
        # Deep copy the data
        scenario_data = copy.deepcopy(data)
        scenario_data.config.active_scenario_id = scenario.id
        
        # Apply overrides
        for override in scenario.overrides:
            if override.milestone_id in scenario_data.milestones:
                instance = scenario_data.milestones[override.milestone_id]
                if override.field == 'duration':
                    instance.duration_override = override.new_value
                elif override.field == 'owner':
                    instance.owner_override = override.new_value
                elif override.field == 'is_active':
                    instance.is_active = override.new_value
        
        # Recalculate
        # Reset dates first
        for instance in scenario_data.milestones.values():
            instance.target_start = None
            instance.target_end = None
        
        scenario_data = self.calculate_schedule(scenario_data)
        scenario_data.critical_path = self.identify_critical_path(scenario_data)
        
        return scenario_data
    
    def create_scenario(
        self,
        name: str,
        description: str,
        overrides: List[Dict[str, Any]]
    ) -> WhatIfScenario:
        """Create a what-if scenario."""
        
        scenario_overrides = []
        for o in overrides:
            scenario_overrides.append(ScenarioOverride(
                milestone_id=o['milestone_id'],
                field=o['field'],
                original_value=o.get('original_value'),
                new_value=o['new_value'],
                description=o.get('description', '')
            ))
        
        return WhatIfScenario(
            id=f"scenario_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name=name,
            description=description,
            overrides=scenario_overrides
        )


# =============================================================================
# PREDEFINED SCENARIOS
# =============================================================================

def get_predefined_scenarios() -> List[Dict]:
    """Get predefined what-if scenario templates."""
    return [
        {
            'name': "Customer Conveys Breakers",
            'description': "Customer procures and conveys HV breakers to utility, potentially accelerating schedule",
            'overrides': [
                {'milestone_id': 'POST-EQ-04', 'field': 'owner', 'new_value': Owner.BUYER.value},
                {'milestone_id': 'POST-EQ-05', 'field': 'duration', 'new_value': 104},  # Reduce by ~1 year
            ]
        },
        {
            'name': "Utility Fast-Track Studies",
            'description': "Utility agrees to expedited study processing",
            'overrides': [
                {'milestone_id': 'PS-PWR-04', 'field': 'duration', 'new_value': 8},
                {'milestone_id': 'PS-PWR-05', 'field': 'duration', 'new_value': 26},
                {'milestone_id': 'PS-PWR-06', 'field': 'duration', 'new_value': 16},
            ]
        },
        {
            'name': "Early Transformer Procurement",
            'description': "Customer funds early transformer procurement before IA execution",
            'overrides': [
                {'milestone_id': 'POST-EQ-01', 'field': 'duration', 'new_value': 0},
                # Note: Would need to change predecessor to earlier milestone
            ]
        },
        {
            'name': "Bridge Power (Temporary Generation)",
            'description': "Deploy temporary generation to enable early operation while awaiting full interconnection",
            'overrides': [
                # This would typically add a parallel path, simplified here
                {'milestone_id': 'POST-BTM-03', 'field': 'duration', 'new_value': 52},  # Faster temp gen
            ]
        },
        {
            'name': "EaaS BTM Provider",
            'description': "Third-party Energy-as-a-Service provider handles BTM generation",
            'overrides': [
                {'milestone_id': 'POST-BTM-01', 'field': 'owner', 'new_value': Owner.EAAS.value},
                {'milestone_id': 'POST-BTM-02', 'field': 'owner', 'new_value': Owner.EAAS.value},
                {'milestone_id': 'POST-BTM-03', 'field': 'owner', 'new_value': Owner.EAAS.value},
            ]
        },
    ]


# =============================================================================
# DOCUMENT PARSING (for email/meeting minutes updates)
# =============================================================================

def parse_document_for_updates(text: str, site_id: str) -> List[Dict]:
    """
    Parse document text (email, meeting minutes) for milestone updates.
    Returns list of suggested updates.
    """
    updates = []
    text_lower = text.lower()
    
    # Patterns to look for
    patterns = {
        # Study completions
        r'screening study.*(complete|finished|done)': {
            'milestone': 'PS-PWR-04',
            'status': MilestoneStatus.COMPLETE.value,
            'field': 'status'
        },
        r'sis.*(complete|finished|done)': {
            'milestone': 'PS-PWR-05',
            'status': MilestoneStatus.COMPLETE.value,
            'field': 'status'
        },
        r'facilities study.*(complete|finished|done)': {
            'milestone': 'PS-PWR-06',
            'status': MilestoneStatus.COMPLETE.value,
            'field': 'status'
        },
        r'ia.*(executed|signed)': {
            'milestone': 'PS-PWR-09',
            'status': MilestoneStatus.COMPLETE.value,
            'field': 'status'
        },
        
        # Zoning
        r'zoning.*(approved|granted)': {
            'milestone': 'PS-ZN-06',
            'status': MilestoneStatus.COMPLETE.value,
            'field': 'status'
        },
        
        # Equipment
        r'transformer.*(ordered|po issued)': {
            'milestone': 'POST-EQ-01',
            'status': MilestoneStatus.COMPLETE.value,
            'field': 'status'
        },
        r'transformer.*(delivered|arrived|on site)': {
            'milestone': 'POST-EQ-03',
            'status': MilestoneStatus.COMPLETE.value,
            'field': 'status'
        },
        
        # Lead time changes
        r'transformer lead time.?(\d+)\s*(weeks?|months?|years?)': {
            'milestone': 'POST-EQ-02',
            'field': 'duration',
            'extract_number': True
        },
        r'breaker lead time.?(\d+)\s*(weeks?|months?|years?)': {
            'milestone': 'POST-EQ-05',
            'field': 'duration',
            'extract_number': True
        },
    }
    
    for pattern, update_info in patterns.items():
        match = re.search(pattern, text_lower)
        if match:
            update = {
                'site_id': site_id,
                'milestone_id': update_info['milestone'],
                'field': update_info['field'],
                'source': 'document_parse',
                'confidence': 'medium',
            }
            
            if update_info['field'] == 'status':
                update['new_value'] = update_info['status']
            elif update_info.get('extract_number'):
                # Extract number and convert to weeks
                num = int(match.group(1))
                unit = match.group(2).lower()
                if 'month' in unit:
                    num = num * 4
                elif 'year' in unit:
                    num = num * 52
                update['new_value'] = num
            
            updates.append(update)
    
    return updates


# =============================================================================
# SERIALIZATION (for Google Sheets storage)
# =============================================================================

def serialize_critical_path(data: CriticalPathData) -> str:
    """Serialize critical path data to JSON string for storage."""
    
    def convert_to_dict(obj):
        """Convert object to dict, handling dataclasses and enums."""
        if isinstance(obj, Enum):
            return obj.value
        elif hasattr(obj, '__dataclass_fields__'):
            # It's a dataclass - use asdict
            result = {}
            for key, value in asdict(obj).items():
                result[key] = convert_to_dict(value)
            return result
        elif isinstance(obj, dict):
            return {k: convert_to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_dict(item) for item in obj]
        else:
            return obj
    
    return json.dumps(convert_to_dict(data), indent=None)


def deserialize_critical_path(json_str: str) -> Optional[CriticalPathData]:
    """Deserialize critical path data from JSON string."""
    if not json_str:
        return None
    
    try:
        data = json.loads(json_str)
        
        # Reconstruct config
        config_data = data.get('config', {})
        config = CriticalPathConfig(
            site_id=config_data.get('site_id', ''),
            target_energization=config_data.get('target_energization'),
            target_mw=config_data.get('target_mw', 0),
            voltage_kv=config_data.get('voltage_kv', 138),
            iso=config_data.get('iso', 'SPP'),
            include_btm=config_data.get('include_btm', False),
            btm_owner=config_data.get('btm_owner', 'utility'),
            customer_provides_breakers=config_data.get('customer_provides_breakers', False),
            lead_time_overrides=config_data.get('lead_time_overrides', {}),
            active_scenario_id=config_data.get('active_scenario_id'),
        )
        
        # Reconstruct milestones
        milestones = {}
        for ms_id, ms_data in data.get('milestones', {}).items():
            milestones[ms_id] = MilestoneInstance(
                template_id=ms_data.get('template_id', ms_id),
                status=MilestoneStatus(ms_data.get('status', 'Not Started')),
                completion_pct=ms_data.get('completion_pct', 0),
                target_start=ms_data.get('target_start'),
                actual_start=ms_data.get('actual_start'),
                target_end=ms_data.get('target_end'),
                actual_end=ms_data.get('actual_end'),
                duration_override=ms_data.get('duration_override'),
                owner_override=ms_data.get('owner_override'),
                assigned_to=ms_data.get('assigned_to', ''),
                notes=ms_data.get('notes', ''),
                blockers=ms_data.get('blockers', []),
                source_docs=ms_data.get('source_docs', []),
                last_updated=ms_data.get('last_updated'),
                updated_by=ms_data.get('updated_by', ''),
                is_active=ms_data.get('is_active', True),
                on_critical_path=ms_data.get('on_critical_path', False),
            )
        
        # Reconstruct scenarios
        scenarios = {}
        for sc_id, sc_data in data.get('scenarios', {}).items():
            overrides = []
            for o in sc_data.get('overrides', []):
                overrides.append(ScenarioOverride(
                    milestone_id=o.get('milestone_id', ''),
                    field=o.get('field', ''),
                    original_value=o.get('original_value'),
                    new_value=o.get('new_value'),
                    description=o.get('description', ''),
                ))
            scenarios[sc_id] = WhatIfScenario(
                id=sc_id,
                name=sc_data.get('name', ''),
                description=sc_data.get('description', ''),
                overrides=overrides,
                energization_delta_weeks=sc_data.get('energization_delta_weeks', 0),
                new_critical_path=sc_data.get('new_critical_path', []),
            )
        
        return CriticalPathData(
            config=config,
            milestones=milestones,
            scenarios=scenarios,
            critical_path=data.get('critical_path', []),
            total_duration_weeks=data.get('total_duration_weeks', 0),
            calculated_energization=data.get('calculated_energization'),
            primary_driver=data.get('primary_driver', ''),
            primary_driver_category=data.get('primary_driver_category', ''),
            schedule_risk=data.get('schedule_risk', 'medium'),
            last_calculated=data.get('last_calculated'),
            version=data.get('version', '1.0'),
        )
        
    except Exception as e:
        print(f"Error deserializing critical path: {e}")
        return None


# =============================================================================
# GOOGLE SHEETS COLUMN MAPPING
# =============================================================================

# Add this column to your existing SHEET_COLUMNS in google_integration.py:
# 'critical_path_json': 'AK'  (or next available column)

CRITICAL_PATH_COLUMN = 'critical_path_json'


# =============================================================================
# INTEGRATION HELPER FUNCTIONS
# =============================================================================

def get_critical_path_for_site(site: Dict) -> Optional[CriticalPathData]:
    """Get critical path data from a site dictionary."""
    json_str = site.get(CRITICAL_PATH_COLUMN) or site.get('critical_path_json')
    return deserialize_critical_path(json_str) if json_str else None


def save_critical_path_to_site(site: Dict, cp_data: CriticalPathData) -> Dict:
    """Save critical path data to a site dictionary."""
    site[CRITICAL_PATH_COLUMN] = serialize_critical_path(cp_data)
    return site


def initialize_critical_path_for_site(site: Dict) -> CriticalPathData:
    """Initialize critical path data from existing site data."""
    engine = CriticalPathEngine()
    
    # Extract configuration from site
    site_id = site.get('site_id', '')
    target_mw = site.get('target_mw', 200)
    iso = site.get('iso', 'SPP')
    
    # Determine voltage from target_mw (heuristic)
    if target_mw >= 500:
        voltage_kv = 345
    elif target_mw >= 200:
        voltage_kv = 230
    elif target_mw >= 100:
        voltage_kv = 138
    else:
        voltage_kv = 69
    
    # Check for BTM indicators
    include_btm = bool(site.get('onsite_gen', {}).get('has_btm'))
    
    # Initialize
    cp_data = engine.initialize_site(
        site_id=site_id,
        target_mw=target_mw,
        voltage_kv=voltage_kv,
        iso=iso,
        include_btm=include_btm,
    )
    
    # Calculate schedule
    cp_data = engine.calculate_schedule(cp_data)
    cp_data.critical_path = engine.identify_critical_path(cp_data)
    
    return cp_data


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    # Test the engine
    engine = CriticalPathEngine()
    
    # Initialize a test site
    data = engine.initialize_site(
        site_id="test-001",
        target_mw=600,
        voltage_kv=345,
        iso="SPP",
        include_btm=True,
    )
    
    # Calculate schedule
    data = engine.calculate_schedule(data)
    data.critical_path = engine.identify_critical_path(data)
    
    print(f"\n=== Critical Path Analysis ===\n")
    print(f"Target MW: {data.config.target_mw}")
    print(f"Voltage: {data.config.voltage_kv} kV")
    print(f"ISO: {data.config.iso}")
    print(f"\nTotal Duration: {data.total_duration_weeks} weeks ({data.total_duration_weeks/52:.1f} years)")
    print(f"Calculated Energization: {data.calculated_energization}")
    print(f"Primary Driver: {data.primary_driver} ({data.primary_driver_category})")
    print(f"\nCritical Path ({len(data.critical_path)} items):")
    
    templates = get_milestone_templates()
    for ms_id in data.critical_path[:15]:
        tmpl = templates.get(ms_id)
        if tmpl:
            print(f"  • {ms_id}: {tmpl.name} ({tmpl.owner.value})")
    
    # Test serialization
    json_str = serialize_critical_path(data)
    print(f"\nSerialized length: {len(json_str)} chars")
    
    # Test deserialization
    restored = deserialize_critical_path(json_str)
    print(f"Deserialized successfully: {restored is not None}")
    
    # Test scenario
    scenario = engine.create_scenario(
        name="Fast Track Studies",
        description="Utility expedites all studies",
        overrides=[
            {'milestone_id': 'PS-PWR-04', 'field': 'duration', 'new_value': 8},
            {'milestone_id': 'PS-PWR-05', 'field': 'duration', 'new_value': 20},
            {'milestone_id': 'PS-PWR-06', 'field': 'duration', 'new_value': 12},
        ]
    )
    
    scenario_data = engine.apply_scenario(data, scenario)
    print(f"\nWith scenario '{scenario.name}':")
    print(f"  New duration: {scenario_data.total_duration_weeks} weeks")
    print(f"  Savings: {data.total_duration_weeks - scenario_data.total_duration_weeks} weeks")
