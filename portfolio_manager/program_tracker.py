"""
Program Tracker Module
======================
Extends the Portfolio Manager with program management capabilities.
Tracks deal progress, calculates probabilities, and manages transaction values.

Integrates with Google Sheets by adding columns to the existing Sites tab.

New Columns Added (X through AJ):
- X: client (partner/developer name)
- Y: total_fee_potential (manual or calculated)
- Z: contract_status (No/Verbal/MOU/Definitive)
- AA: site_control_stage (stage 1-4)
- AB: power_stage (stage 1-4)
- AC: marketing_stage (stage 1-4)
- AD: buyer_stage (stage 1-4)
- AE: zoning_stage (stage 1-3, special case)
- AF: water_stage (stage 1-4)
- AG: incentives_stage (stage 1-4)
- AH: probability (auto-calculated)
- AI: weighted_fee (auto-calculated)
- AJ: tracker_notes
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json

# =============================================================================
# CONFIGURATION - Status Options
# =============================================================================

class ContractStatus(str, Enum):
    """Contract status options with their multipliers."""
    NO = "No"
    VERBAL = "Verbal"
    MOU = "MOU"
    DEFINITIVE = "Definitive"

# Contract multipliers (gatekeeper)
CONTRACT_MULTIPLIERS = {
    ContractStatus.NO: 0.0,
    ContractStatus.VERBAL: 0.33,
    ContractStatus.MOU: 0.66,
    ContractStatus.DEFINITIVE: 0.90,
    # String versions for flexibility
    "No": 0.0,
    "Verbal": 0.33,
    "MOU": 0.66,
    "Definitive": 0.90,
    "": 0.0,
    None: 0.0,
}

# Probability drivers with their max weights
PROBABILITY_DRIVERS = {
    'buyer': {'weight': 0.30, 'stages': 4},      # 30%
    'site_control': {'weight': 0.20, 'stages': 4},  # 20%
    'power': {'weight': 0.20, 'stages': 4},      # 20%
    'zoning': {'weight': 0.20, 'stages': 3},     # 20% (only 3 stages)
    'incentives': {'weight': 0.10, 'stages': 4}, # 10%
}

# Stage progression percentages
STAGE_PROGRESS = {
    1: 0.0,      # Not Started
    2: 0.333,    # Stage 2 (33.3%)
    3: 0.666,    # Stage 3 (66.6%)
    4: 1.0,      # Complete (100%)
}

# Zoning has only 3 stages
ZONING_STAGE_PROGRESS = {
    1: 0.0,      # Not Started
    2: 0.50,     # In Progress
    3: 1.0,      # Complete
}

# Stage labels for display
STAGE_LABELS = {
    'site_control': {
        1: 'Not Started',
        2: 'Identified',
        3: 'LOI',
        4: 'PSA/Contract',
    },
    'power': {
        1: 'Not Started',
        2: 'Preliminary Study',
        3: 'Contract Study',
        4: 'Interconnect Agreement',
    },
    'marketing': {
        1: 'Not Started',
        2: 'Flyer',
        3: 'VDR',
        4: 'Full Package',
    },
    'buyer': {
        1: 'Not Started',
        2: 'Preliminary Discussion',
        3: 'LOI',
        4: 'PSA/Contract',
    },
    'zoning': {
        1: 'Not Started',
        2: 'Comp Plan/In Progress',
        3: 'Zoning Approved',
    },
    'water': {
        1: 'Not Started',
        2: 'Preliminary Capacities',
        3: 'Will-Serve Letter',
        4: 'Final Capacities',
    },
    'incentives': {
        1: 'Not Started',
        2: 'Application Filed',
        3: 'Preliminary Response',
        4: 'Final Award',
    },
}

# Column mapping for program tracker fields
TRACKER_COLUMNS = {
    'client': 'X',
    'total_fee_potential': 'Y',
    'contract_status': 'Z',
    'site_control_stage': 'AA',
    'power_stage': 'AB',
    'marketing_stage': 'AC',
    'buyer_stage': 'AD',
    'zoning_stage': 'AE',
    'water_stage': 'AF',
    'incentives_stage': 'AG',
    'probability': 'AH',
    'weighted_fee': 'AI',
    'tracker_notes': 'AJ',
}

# All tracker column names in order
TRACKER_COLUMN_ORDER = [
    'client', 'total_fee_potential', 'contract_status',
    'site_control_stage', 'power_stage', 'marketing_stage', 'buyer_stage',
    'zoning_stage', 'water_stage', 'incentives_stage',
    'probability', 'weighted_fee', 'tracker_notes'
]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ProgramTrackerData:
    """Program tracking data for a single site."""
    site_id: str
    client: str = ""
    total_fee_potential: float = 0.0
    contract_status: str = "No"
    site_control_stage: int = 1
    power_stage: int = 1
    marketing_stage: int = 1
    buyer_stage: int = 1
    zoning_stage: int = 1
    water_stage: int = 1
    incentives_stage: int = 1
    probability: float = 0.0
    weighted_fee: float = 0.0
    tracker_notes: str = ""
    
    def calculate_probability(self) -> float:
        """
        Calculate probability based on the formula:
        Base Probability = sum of (driver_weight × stage_progress)
        Final Probability = Base Probability × Contract Multiplier
        """
        # Calculate base probability from drivers
        base_prob = 0.0
        
        # Buyer (30%)
        buyer_progress = STAGE_PROGRESS.get(self.buyer_stage, 0.0)
        base_prob += PROBABILITY_DRIVERS['buyer']['weight'] * buyer_progress
        
        # Site Control (20%)
        site_progress = STAGE_PROGRESS.get(self.site_control_stage, 0.0)
        base_prob += PROBABILITY_DRIVERS['site_control']['weight'] * site_progress
        
        # Power (20%)
        power_progress = STAGE_PROGRESS.get(self.power_stage, 0.0)
        base_prob += PROBABILITY_DRIVERS['power']['weight'] * power_progress
        
        # Zoning (20%) - special 3-stage progression
        zoning_progress = ZONING_STAGE_PROGRESS.get(self.zoning_stage, 0.0)
        base_prob += PROBABILITY_DRIVERS['zoning']['weight'] * zoning_progress
        
        # Incentives (10%)
        incentives_progress = STAGE_PROGRESS.get(self.incentives_stage, 0.0)
        base_prob += PROBABILITY_DRIVERS['incentives']['weight'] * incentives_progress
        
        # Apply contract multiplier (gatekeeper)
        contract_mult = CONTRACT_MULTIPLIERS.get(self.contract_status, 0.0)
        final_prob = base_prob * contract_mult
        
        return final_prob
    
    def calculate_weighted_fee(self) -> float:
        """Calculate weighted fee: Total Fee × Probability"""
        prob = self.calculate_probability()
        return self.total_fee_potential * prob
    
    def update_calculations(self):
        """Update probability and weighted fee calculations."""
        self.probability = self.calculate_probability()
        self.weighted_fee = self.calculate_weighted_fee()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        self.update_calculations()
        return {
            'site_id': self.site_id,
            'client': self.client,
            'total_fee_potential': self.total_fee_potential,
            'contract_status': self.contract_status,
            'site_control_stage': self.site_control_stage,
            'power_stage': self.power_stage,
            'marketing_stage': self.marketing_stage,
            'buyer_stage': self.buyer_stage,
            'zoning_stage': self.zoning_stage,
            'water_stage': self.water_stage,
            'incentives_stage': self.incentives_stage,
            'probability': self.probability,
            'weighted_fee': self.weighted_fee,
            'tracker_notes': self.tracker_notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgramTrackerData':
        """Create from dictionary."""
        def safe_float(val, default=0.0):
            try:
                if val is None or val == "": return default
                if isinstance(val, str): val = val.replace(',', '').replace('$', '').strip()
                return float(val)
            except (ValueError, TypeError):
                return default

        def safe_int(val, default=1):
            try:
                if val is None or val == "": return default
                return int(float(val)) # Handle "1.0" strings
            except (ValueError, TypeError):
                return default

        tracker = cls(
            site_id=data.get('site_id', ''),
            client=data.get('client', ''),
            total_fee_potential=safe_float(data.get('total_fee_potential')),
            contract_status=data.get('contract_status', 'No') or 'No',
            site_control_stage=safe_int(data.get('site_control_stage')),
            power_stage=safe_int(data.get('power_stage')),
            marketing_stage=safe_int(data.get('marketing_stage')),
            buyer_stage=safe_int(data.get('buyer_stage')),
            zoning_stage=safe_int(data.get('zoning_stage')),
            water_stage=safe_int(data.get('water_stage')),
            incentives_stage=safe_int(data.get('incentives_stage')),
            tracker_notes=data.get('tracker_notes', ''),
        )
        tracker.update_calculations()
        return tracker


# =============================================================================
# CALCULATION UTILITIES
# =============================================================================

def calculate_portfolio_summary(sites: List[Dict]) -> Dict[str, Any]:
    """Calculate portfolio-level summary statistics."""
    total_potential = 0.0
    total_weighted = 0.0
    by_client = {}
    by_contract_status = {}
    by_stage = {
        'early': [],      # Probability < 20%
        'developing': [], # 20-50%
        'advanced': [],   # 50-80%
        'closing': [],    # >80%
    }
    
    for site in sites:
        tracker = ProgramTrackerData.from_dict(site)
        
        total_potential += tracker.total_fee_potential
        total_weighted += tracker.weighted_fee
        
        # By client
        client = tracker.client or 'Unassigned'
        if client not in by_client:
            by_client[client] = {'count': 0, 'potential': 0.0, 'weighted': 0.0}
        by_client[client]['count'] += 1
        by_client[client]['potential'] += tracker.total_fee_potential
        by_client[client]['weighted'] += tracker.weighted_fee
        
        # By contract status
        status = tracker.contract_status
        if status not in by_contract_status:
            by_contract_status[status] = {'count': 0, 'potential': 0.0}
        by_contract_status[status]['count'] += 1
        by_contract_status[status]['potential'] += tracker.total_fee_potential
        
        # By probability stage
        prob = tracker.probability
        site_summary = {
            'site_id': tracker.site_id,
            'name': site.get('name', tracker.site_id),
            'probability': prob,
            'potential': tracker.total_fee_potential,
            'weighted': tracker.weighted_fee,
        }
        if prob < 0.20:
            by_stage['early'].append(site_summary)
        elif prob < 0.50:
            by_stage['developing'].append(site_summary)
        elif prob < 0.80:
            by_stage['advanced'].append(site_summary)
        else:
            by_stage['closing'].append(site_summary)
    
    return {
        'total_potential': total_potential,
        'total_weighted': total_weighted,
        'site_count': len(sites),
        'avg_probability': total_weighted / total_potential if total_potential > 0 else 0,
        'by_client': by_client,
        'by_contract_status': by_contract_status,
        'by_stage': by_stage,
    }


def get_stage_label(driver: str, stage: int) -> str:
    """Get human-readable label for a stage."""
    labels = STAGE_LABELS.get(driver, {})
    return labels.get(stage, f'Stage {stage}')


def get_stage_color(stage: int, max_stages: int = 4) -> str:
    """Get color for stage display."""
    if stage == 1:
        return '🔴'  # Red - Not Started
    elif stage == max_stages:
        return '🟢'  # Green - Complete
    elif stage == max_stages - 1:
        return '🟡'  # Yellow - Almost there
    else:
        return '⚪'  # Grey - In progress


def format_currency(value: float) -> str:
    """Format number as currency."""
    if value >= 1_000_000:
        return f"${value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"${value/1_000:.0f}K"
    else:
        return f"${value:.0f}"


def format_percentage(value: float) -> str:
    """Format decimal as percentage."""
    return f"{value*100:.1f}%"


# =============================================================================
# FEE CALCULATION METHODOLOGIES
# =============================================================================

class FeeCalculationMethod(str, Enum):
    """Methods for calculating total fee potential."""
    MANUAL = "manual"                    # User enters manually
    PER_MW = "per_mw"                    # Fee per MW
    PERCENTAGE_OF_VALUE = "pct_value"    # % of transaction value
    FIXED_PLUS_MW = "fixed_plus_mw"      # Fixed fee + per MW bonus


# Default fee calculation parameters (can be customized)
DEFAULT_FEE_PARAMS = {
    'per_mw_rate': 25000,        # $25K per MW
    'percentage_rate': 0.015,    # 1.5% of transaction value
    'fixed_fee': 500000,         # $500K fixed
    'mw_bonus_rate': 10000,      # $10K per MW bonus
}


def calculate_fee_potential(
    method: str,
    target_mw: float = 0,
    transaction_value: float = 0,
    manual_fee: float = 0,
    params: Dict = None
) -> float:
    """
    Calculate total fee potential using specified method.
    
    Args:
        method: Calculation method
        target_mw: Target capacity in MW
        transaction_value: Estimated transaction value
        manual_fee: Manual override if method is MANUAL
        params: Custom calculation parameters
    """
    params = params or DEFAULT_FEE_PARAMS
    
    if method == FeeCalculationMethod.MANUAL or method == "manual":
        return manual_fee
    
    elif method == FeeCalculationMethod.PER_MW or method == "per_mw":
        return target_mw * params.get('per_mw_rate', 25000)
    
    elif method == FeeCalculationMethod.PERCENTAGE_OF_VALUE or method == "pct_value":
        return transaction_value * params.get('percentage_rate', 0.015)
    
    elif method == FeeCalculationMethod.FIXED_PLUS_MW or method == "fixed_plus_mw":
        fixed = params.get('fixed_fee', 500000)
        mw_bonus = target_mw * params.get('mw_bonus_rate', 10000)
        return fixed + mw_bonus
    
    return 0.0


# =============================================================================
# GOOGLE SHEETS INTEGRATION EXTENSION
# =============================================================================

def extend_site_with_tracker(site_data: Dict, tracker_data: Dict = None) -> Dict:
    """Merge site data with tracker data."""
    merged = site_data.copy()
    
    if tracker_data:
        for key in TRACKER_COLUMN_ORDER:
            merged[key] = tracker_data.get(key, '')
    else:
        # Initialize with defaults
        for key in TRACKER_COLUMN_ORDER:
            if key not in merged:
                if key in ['site_control_stage', 'power_stage', 'marketing_stage', 
                          'buyer_stage', 'zoning_stage', 'water_stage', 'incentives_stage']:
                    merged[key] = 1
                elif key in ['total_fee_potential', 'probability', 'weighted_fee']:
                    merged[key] = 0.0
                elif key == 'contract_status':
                    merged[key] = 'No'
                else:
                    merged[key] = ''
    
    return merged


def get_tracker_row_values(tracker: ProgramTrackerData) -> List[Any]:
    """Get row values for tracker columns only."""
    tracker.update_calculations()
    return [
        tracker.client,
        tracker.total_fee_potential,
        tracker.contract_status,
        tracker.site_control_stage,
        tracker.power_stage,
        tracker.marketing_stage,
        tracker.buyer_stage,
        tracker.zoning_stage,
        tracker.water_stage,
        tracker.incentives_stage,
        tracker.probability,
        tracker.weighted_fee,
        tracker.tracker_notes,
    ]


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    'ContractStatus',
    'CONTRACT_MULTIPLIERS',
    'PROBABILITY_DRIVERS',
    'STAGE_LABELS',
    'TRACKER_COLUMNS',
    'TRACKER_COLUMN_ORDER',
    'ProgramTrackerData',
    'calculate_portfolio_summary',
    'get_stage_label',
    'get_stage_color',
    'format_currency',
    'format_percentage',
    'FeeCalculationMethod',
    'calculate_fee_potential',
    'extend_site_with_tracker',
    'get_tracker_row_values',
]
