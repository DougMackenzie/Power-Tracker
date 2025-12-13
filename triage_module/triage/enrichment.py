"""
Location Enrichment & Utility Lookup
====================================
Auto-enriches triage intake with utility, ISO, and jurisdiction data.
Based on county/state lookup tables.
"""

from typing import Dict, Optional, Tuple, List
from .models import TriageEnrichment


# =============================================================================
# UTILITY SERVICE TERRITORY DATA
# =============================================================================

# Format: state -> county -> {utility, iso, notes}
# This is a subset - expand based on your focus markets
UTILITY_LOOKUP: Dict[str, Dict[str, Dict]] = {
    # OKLAHOMA
    'OK': {
        # PSO Territory (AEP subsidiary) - Eastern Oklahoma
        'tulsa': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'rogers': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'wagoner': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'creek': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'okmulgee': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'muskogee': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'mcintosh': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'pittsburg': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'latimer': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'le flore': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'sequoyah': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'adair': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'cherokee': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'delaware': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'mayes': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'ottawa': {'utility': 'PSO/Empire', 'iso': 'SPP', 'parent': 'AEP/Liberty', 'type': 'vertically_integrated'},
        'craig': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'nowata': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'washington': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'osage': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'pawnee': {'utility': 'PSO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        
        # OG&E Territory - Central/Western Oklahoma
        'oklahoma': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'canadian': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'cleveland': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'logan': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'lincoln': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'pottawatomie': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'seminole': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'pontotoc': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'garvin': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'mcclain': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'grady': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'caddo': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'comanche': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'stephens': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'carter': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'murray': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'johnston': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'marshall': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'love': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'jefferson': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'cotton': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'tillman': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'kiowa': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'washita': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'custer': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'blaine': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'kingfisher': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'payne': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'noble': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'garfield': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'major': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'woodward': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'dewey': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'roger mills': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'beckham': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'greer': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'harmon': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'jackson': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        
        # Panhandle - Mixed territory
        'texas': {'utility': 'Xcel/SPS', 'iso': 'SPP', 'parent': 'Xcel Energy', 'type': 'vertically_integrated'},
        'cimarron': {'utility': 'Xcel/SPS', 'iso': 'SPP', 'parent': 'Xcel Energy', 'type': 'vertically_integrated'},
        'beaver': {'utility': 'OGE/Coop', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'harper': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'woods': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'alfalfa': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'grant': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'kay': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'ellis': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
    },
    
    # TEXAS
    'TX': {
        # ERCOT - Most of Texas
        'dallas': {'utility': 'Oncor', 'iso': 'ERCOT', 'parent': 'Sempra', 'type': 'deregulated'},
        'tarrant': {'utility': 'Oncor', 'iso': 'ERCOT', 'parent': 'Sempra', 'type': 'deregulated'},
        'collin': {'utility': 'Oncor', 'iso': 'ERCOT', 'parent': 'Sempra', 'type': 'deregulated'},
        'denton': {'utility': 'Oncor', 'iso': 'ERCOT', 'parent': 'Sempra', 'type': 'deregulated'},
        'ellis': {'utility': 'Oncor', 'iso': 'ERCOT', 'parent': 'Sempra', 'type': 'deregulated'},
        'johnson': {'utility': 'Oncor', 'iso': 'ERCOT', 'parent': 'Sempra', 'type': 'deregulated'},
        'kaufman': {'utility': 'Oncor', 'iso': 'ERCOT', 'parent': 'Sempra', 'type': 'deregulated'},
        'rockwall': {'utility': 'Oncor', 'iso': 'ERCOT', 'parent': 'Sempra', 'type': 'deregulated'},
        'hunt': {'utility': 'Oncor', 'iso': 'ERCOT', 'parent': 'Sempra', 'type': 'deregulated'},
        'navarro': {'utility': 'Oncor', 'iso': 'ERCOT', 'parent': 'Sempra', 'type': 'deregulated'},
        'hill': {'utility': 'Oncor', 'iso': 'ERCOT', 'parent': 'Sempra', 'type': 'deregulated'},
        'mclennan': {'utility': 'Oncor', 'iso': 'ERCOT', 'parent': 'Sempra', 'type': 'deregulated'},
        'bell': {'utility': 'Oncor', 'iso': 'ERCOT', 'parent': 'Sempra', 'type': 'deregulated'},
        'williamson': {'utility': 'Oncor', 'iso': 'ERCOT', 'parent': 'Sempra', 'type': 'deregulated'},
        'travis': {'utility': 'Austin Energy', 'iso': 'ERCOT', 'parent': 'Municipal', 'type': 'municipal'},
        'hays': {'utility': 'Oncor/PEC', 'iso': 'ERCOT', 'parent': 'Mixed', 'type': 'deregulated'},
        'bexar': {'utility': 'CPS Energy', 'iso': 'ERCOT', 'parent': 'Municipal', 'type': 'municipal'},
        'comal': {'utility': 'GVEC/NBU', 'iso': 'ERCOT', 'parent': 'Coop/Municipal', 'type': 'mixed'},
        'guadalupe': {'utility': 'GVEC', 'iso': 'ERCOT', 'parent': 'Coop', 'type': 'coop'},
        'harris': {'utility': 'CenterPoint', 'iso': 'ERCOT', 'parent': 'CenterPoint Energy', 'type': 'deregulated'},
        'fort bend': {'utility': 'CenterPoint', 'iso': 'ERCOT', 'parent': 'CenterPoint Energy', 'type': 'deregulated'},
        'montgomery': {'utility': 'Entergy/LSPC', 'iso': 'ERCOT', 'parent': 'Entergy', 'type': 'deregulated'},
        'brazoria': {'utility': 'CenterPoint', 'iso': 'ERCOT', 'parent': 'CenterPoint Energy', 'type': 'deregulated'},
        'galveston': {'utility': 'CenterPoint', 'iso': 'ERCOT', 'parent': 'CenterPoint Energy', 'type': 'deregulated'},
        'nueces': {'utility': 'AEP Texas', 'iso': 'ERCOT', 'parent': 'AEP', 'type': 'deregulated'},
        'hidalgo': {'utility': 'AEP Texas', 'iso': 'ERCOT', 'parent': 'AEP', 'type': 'deregulated'},
        'cameron': {'utility': 'AEP Texas', 'iso': 'ERCOT', 'parent': 'AEP', 'type': 'deregulated'},
        'webb': {'utility': 'AEP Texas', 'iso': 'ERCOT', 'parent': 'AEP', 'type': 'deregulated'},
        'midland': {'utility': 'Oncor', 'iso': 'ERCOT', 'parent': 'Sempra', 'type': 'deregulated'},
        'ector': {'utility': 'Oncor', 'iso': 'ERCOT', 'parent': 'Sempra', 'type': 'deregulated'},
        'taylor': {'utility': 'AEP Texas', 'iso': 'ERCOT', 'parent': 'AEP', 'type': 'deregulated'},
        'lubbock': {'utility': 'Xcel/LP&L', 'iso': 'ERCOT', 'parent': 'Xcel/Municipal', 'type': 'mixed'},
        'potter': {'utility': 'Xcel/SPS', 'iso': 'SPP', 'parent': 'Xcel Energy', 'type': 'vertically_integrated'},
        'randall': {'utility': 'Xcel/SPS', 'iso': 'SPP', 'parent': 'Xcel Energy', 'type': 'vertically_integrated'},
        'el paso': {'utility': 'El Paso Electric', 'iso': 'WECC', 'parent': 'IIF', 'type': 'vertically_integrated'},
        
        # Texas Panhandle - SPP
        'moore': {'utility': 'Xcel/SPS', 'iso': 'SPP', 'parent': 'Xcel Energy', 'type': 'vertically_integrated'},
        'hutchinson': {'utility': 'Xcel/SPS', 'iso': 'SPP', 'parent': 'Xcel Energy', 'type': 'vertically_integrated'},
        'carson': {'utility': 'Xcel/SPS', 'iso': 'SPP', 'parent': 'Xcel Energy', 'type': 'vertically_integrated'},
        'gray': {'utility': 'Xcel/SPS', 'iso': 'SPP', 'parent': 'Xcel Energy', 'type': 'vertically_integrated'},
        'hemphill': {'utility': 'Xcel/SPS', 'iso': 'SPP', 'parent': 'Xcel Energy', 'type': 'vertically_integrated'},
        'ochiltree': {'utility': 'Xcel/SPS', 'iso': 'SPP', 'parent': 'Xcel Energy', 'type': 'vertically_integrated'},
        'hansford': {'utility': 'Xcel/SPS', 'iso': 'SPP', 'parent': 'Xcel Energy', 'type': 'vertically_integrated'},
        'sherman': {'utility': 'Xcel/SPS', 'iso': 'SPP', 'parent': 'Xcel Energy', 'type': 'vertically_integrated'},
        'dallam': {'utility': 'Xcel/SPS', 'iso': 'SPP', 'parent': 'Xcel Energy', 'type': 'vertically_integrated'},
        'hartley': {'utility': 'Xcel/SPS', 'iso': 'SPP', 'parent': 'Xcel Energy', 'type': 'vertically_integrated'},
    },
    
    # KANSAS
    'KS': {
        'johnson': {'utility': 'Evergy', 'iso': 'SPP', 'parent': 'Evergy', 'type': 'vertically_integrated'},
        'wyandotte': {'utility': 'Evergy/BPU', 'iso': 'SPP', 'parent': 'Evergy/Municipal', 'type': 'mixed'},
        'douglas': {'utility': 'Evergy', 'iso': 'SPP', 'parent': 'Evergy', 'type': 'vertically_integrated'},
        'shawnee': {'utility': 'Evergy', 'iso': 'SPP', 'parent': 'Evergy', 'type': 'vertically_integrated'},
        'sedgwick': {'utility': 'Evergy', 'iso': 'SPP', 'parent': 'Evergy', 'type': 'vertically_integrated'},
        'butler': {'utility': 'Evergy', 'iso': 'SPP', 'parent': 'Evergy', 'type': 'vertically_integrated'},
        'harvey': {'utility': 'Evergy', 'iso': 'SPP', 'parent': 'Evergy', 'type': 'vertically_integrated'},
        'reno': {'utility': 'Evergy', 'iso': 'SPP', 'parent': 'Evergy', 'type': 'vertically_integrated'},
        'saline': {'utility': 'Evergy', 'iso': 'SPP', 'parent': 'Evergy', 'type': 'vertically_integrated'},
        'riley': {'utility': 'Evergy', 'iso': 'SPP', 'parent': 'Evergy', 'type': 'vertically_integrated'},
        'geary': {'utility': 'Evergy', 'iso': 'SPP', 'parent': 'Evergy', 'type': 'vertically_integrated'},
        'leavenworth': {'utility': 'Evergy', 'iso': 'SPP', 'parent': 'Evergy', 'type': 'vertically_integrated'},
    },
    
    # ARKANSAS
    'AR': {
        'benton': {'utility': 'SWEPCO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
        'washington': {'utility': 'SWEPCO/Ozarks', 'iso': 'SPP', 'parent': 'AEP/Coop', 'type': 'mixed'},
        'sebastian': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'crawford': {'utility': 'OGE', 'iso': 'SPP', 'parent': 'OGE Energy', 'type': 'vertically_integrated'},
        'pulaski': {'utility': 'Entergy', 'iso': 'MISO', 'parent': 'Entergy', 'type': 'vertically_integrated'},
        'saline': {'utility': 'Entergy', 'iso': 'MISO', 'parent': 'Entergy', 'type': 'vertically_integrated'},
        'faulkner': {'utility': 'Entergy', 'iso': 'MISO', 'parent': 'Entergy', 'type': 'vertically_integrated'},
        'lonoke': {'utility': 'Entergy', 'iso': 'MISO', 'parent': 'Entergy', 'type': 'vertically_integrated'},
        'jefferson': {'utility': 'Entergy', 'iso': 'MISO', 'parent': 'Entergy', 'type': 'vertically_integrated'},
        'garland': {'utility': 'Entergy', 'iso': 'MISO', 'parent': 'Entergy', 'type': 'vertically_integrated'},
        'miller': {'utility': 'SWEPCO', 'iso': 'SPP', 'parent': 'AEP', 'type': 'vertically_integrated'},
    },
    
    # MISSOURI
    'MO': {
        'jackson': {'utility': 'Evergy', 'iso': 'SPP', 'parent': 'Evergy', 'type': 'vertically_integrated'},
        'clay': {'utility': 'Evergy', 'iso': 'SPP', 'parent': 'Evergy', 'type': 'vertically_integrated'},
        'platte': {'utility': 'Evergy', 'iso': 'SPP', 'parent': 'Evergy', 'type': 'vertically_integrated'},
        'cass': {'utility': 'Evergy', 'iso': 'SPP', 'parent': 'Evergy', 'type': 'vertically_integrated'},
        'st. louis': {'utility': 'Ameren', 'iso': 'MISO', 'parent': 'Ameren', 'type': 'vertically_integrated'},
        'st. charles': {'utility': 'Ameren', 'iso': 'MISO', 'parent': 'Ameren', 'type': 'vertically_integrated'},
        'jefferson': {'utility': 'Ameren', 'iso': 'MISO', 'parent': 'Ameren', 'type': 'vertically_integrated'},
        'franklin': {'utility': 'Ameren', 'iso': 'MISO', 'parent': 'Ameren', 'type': 'vertically_integrated'},
        'boone': {'utility': 'Ameren', 'iso': 'MISO', 'parent': 'Ameren', 'type': 'vertically_integrated'},
        'greene': {'utility': 'City Utilities', 'iso': 'SPP', 'parent': 'Municipal', 'type': 'municipal'},
        'jasper': {'utility': 'Empire/Liberty', 'iso': 'SPP', 'parent': 'Liberty Utilities', 'type': 'vertically_integrated'},
        'newton': {'utility': 'Empire/Liberty', 'iso': 'SPP', 'parent': 'Liberty Utilities', 'type': 'vertically_integrated'},
    },
    
    # Add more states as needed...
}


# =============================================================================
# KNOWN CONSTRAINTS & ISSUES BY REGION
# =============================================================================

KNOWN_CONSTRAINTS: Dict[str, Dict[str, List[str]]] = {
    'OK': {
        '_statewide': [
            'Oklahoma has limited large-load interconnection experience',
            'Water availability varies significantly by region',
        ],
        'tulsa': [
            'Tulsa Metro has active data center interest',
            'PSO has announced capacity expansion plans',
        ],
    },
    'TX': {
        '_statewide': [
            'ERCOT queue backlog exceeds 5 years for large loads',
            'Summer reliability concerns may limit new interconnections',
            'Behind-the-meter generation may be required',
        ],
        'dallas': [
            'Dallas/Fort Worth is highly competitive market',
            'Oncor has significant queue backlog',
        ],
        'travis': [
            'Austin Energy has limited capacity for new large loads',
            'Municipal utility with different approval process',
        ],
    },
    # Add more as needed...
}


# =============================================================================
# ISO DEFAULTS BY STATE
# =============================================================================

STATE_ISO_DEFAULT: Dict[str, str] = {
    'OK': 'SPP',
    'TX': 'ERCOT',
    'KS': 'SPP',
    'AR': 'SPP',  # Split between SPP and MISO
    'MO': 'SPP',  # Split between SPP and MISO
    'LA': 'MISO',
    'NM': 'SPP',
    'CO': 'SPP',
    'NE': 'SPP',
    'SD': 'SPP',
    'ND': 'SPP',
    'MN': 'MISO',
    'IA': 'MISO',
    'WI': 'MISO',
    'IL': 'MISO',
    'IN': 'MISO',
    'MI': 'MISO',
    'OH': 'PJM',
    'PA': 'PJM',
    'NJ': 'PJM',
    'MD': 'PJM',
    'VA': 'PJM',
    'NC': 'SERC',
    'SC': 'SERC',
    'GA': 'SERC',
    'FL': 'SERC',
    'AL': 'SERC',
    'MS': 'MISO',
    'TN': 'SERC',
    'KY': 'PJM',
    'WV': 'PJM',
    'NY': 'NYISO',
    'CT': 'ISO-NE',
    'MA': 'ISO-NE',
    'AZ': 'WECC',
    'NV': 'WECC',
    'UT': 'WECC',
    'WA': 'WECC',
    'OR': 'WECC',
    'CA': 'CAISO',
}


# =============================================================================
# ENRICHMENT FUNCTIONS
# =============================================================================

def normalize_county(county: str) -> str:
    """Normalize county name for lookup."""
    normalized = county.lower().strip()
    # Remove common suffixes
    for suffix in [' county', ' parish', ' borough']:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
    return normalized.strip()


def normalize_state(state: str) -> str:
    """Normalize state to 2-letter code."""
    state = state.upper().strip()
    
    # Full name to code mapping
    state_names = {
        'OKLAHOMA': 'OK', 'TEXAS': 'TX', 'KANSAS': 'KS', 'ARKANSAS': 'AR',
        'MISSOURI': 'MO', 'LOUISIANA': 'LA', 'NEW MEXICO': 'NM', 'COLORADO': 'CO',
        'NEBRASKA': 'NE', 'SOUTH DAKOTA': 'SD', 'NORTH DAKOTA': 'ND',
        'MINNESOTA': 'MN', 'IOWA': 'IA', 'WISCONSIN': 'WI', 'ILLINOIS': 'IL',
        'INDIANA': 'IN', 'MICHIGAN': 'MI', 'OHIO': 'OH', 'PENNSYLVANIA': 'PA',
        'NEW JERSEY': 'NJ', 'MARYLAND': 'MD', 'VIRGINIA': 'VA',
        'NORTH CAROLINA': 'NC', 'SOUTH CAROLINA': 'SC', 'GEORGIA': 'GA',
        'FLORIDA': 'FL', 'ALABAMA': 'AL', 'MISSISSIPPI': 'MS', 'TENNESSEE': 'TN',
        'KENTUCKY': 'KY', 'WEST VIRGINIA': 'WV', 'NEW YORK': 'NY',
        'CONNECTICUT': 'CT', 'MASSACHUSETTS': 'MA', 'ARIZONA': 'AZ',
        'NEVADA': 'NV', 'UTAH': 'UT', 'WASHINGTON': 'WA', 'OREGON': 'OR',
        'CALIFORNIA': 'CA',
    }
    
    if len(state) == 2:
        return state
    
    return state_names.get(state, state[:2])


def lookup_utility(county: str, state: str) -> Optional[Dict]:
    """
    Look up utility information for a county/state combination.
    Returns dict with utility, iso, parent, type or None if not found.
    """
    state_code = normalize_state(state)
    county_norm = normalize_county(county)
    
    state_data = UTILITY_LOOKUP.get(state_code, {})
    return state_data.get(county_norm)


def get_known_constraints(county: str, state: str) -> List[str]:
    """Get known constraints for a location."""
    state_code = normalize_state(state)
    county_norm = normalize_county(county)
    
    constraints = []
    
    state_data = KNOWN_CONSTRAINTS.get(state_code, {})
    
    # Add statewide constraints
    constraints.extend(state_data.get('_statewide', []))
    
    # Add county-specific constraints
    constraints.extend(state_data.get(county_norm, []))
    
    return constraints


def auto_enrich_location(county: str, state: str) -> TriageEnrichment:
    """
    Auto-enrich location data from county/state.
    This is the main entry point for location enrichment.
    """
    state_code = normalize_state(state)
    county_norm = normalize_county(county)
    
    # Look up utility data
    utility_data = lookup_utility(county, state)
    
    if utility_data:
        utility = utility_data.get('utility', 'Unknown')
        iso = utility_data.get('iso', STATE_ISO_DEFAULT.get(state_code, 'Unknown'))
        utility_parent = utility_data.get('parent')
        regulatory_type = utility_data.get('type')
    else:
        # Fall back to state defaults
        utility = 'Unknown (needs research)'
        iso = STATE_ISO_DEFAULT.get(state_code, 'Unknown')
        utility_parent = None
        regulatory_type = None
    
    # Get known constraints
    constraints = get_known_constraints(county, state)
    
    return TriageEnrichment(
        utility=utility,
        iso=iso,
        jurisdiction_type='unincorporated_county',  # Default, can be overridden
        municipality=None,
        utility_parent=utility_parent,
        regulatory_type=regulatory_type,
        known_constraints=constraints,
    )


def get_utility_appetite_hint(utility: str) -> Optional[str]:
    """
    Get a hint about utility's appetite for data center load.
    This is placeholder for integration with utility intelligence.
    """
    # This will be replaced with actual utility intelligence lookup
    appetite_hints = {
        'PSO': 'AEP subsidiary actively seeking large load; has announced capacity expansion',
        'OGE': 'Moderate interest; focused on transmission reliability',
        'Oncor': 'Massive queue backlog; very competitive market',
        'CenterPoint': 'Houston market well-served; moderate capacity',
        'Evergy': 'Seeking load growth; Kansas City market attractive',
        'Entergy': 'Arkansas territory has capacity; Texas market more constrained',
        'Xcel/SPS': 'Panhandle region has capacity; transmission-constrained',
        'AEP Texas': 'South Texas has capacity; West Texas more constrained',
    }
    
    for key, hint in appetite_hints.items():
        if key.lower() in utility.lower():
            return hint
    
    return None


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_mw_for_acreage(claimed_mw: int, site_acres: Optional[float]) -> Tuple[bool, str]:
    """
    Validate if claimed MW is reasonable for site acreage.
    Rule of thumb: 3-5 acres per MW for hyperscale, 2-3 for colo.
    """
    if not site_acres:
        return True, "Acreage not provided - cannot validate"
    
    # Calculate MW per acre
    mw_per_acre = claimed_mw / site_acres
    
    if mw_per_acre > 0.5:  # More than 0.5 MW per acre is aggressive
        return False, f"Claimed {claimed_mw} MW on {site_acres} acres ({mw_per_acre:.2f} MW/acre) is aggressive - typical is 0.2-0.33 MW/acre"
    elif mw_per_acre > 0.33:
        return True, f"MW density ({mw_per_acre:.2f} MW/acre) is feasible but on the high end"
    else:
        return True, f"MW density ({mw_per_acre:.2f} MW/acre) is reasonable"


def parse_timeline_claim(claimed_timeline: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Parse a timeline claim into year and quarter.
    Returns (year, quarter) or (None, None) if unparseable.
    """
    import re
    
    claimed = claimed_timeline.upper().strip()
    
    # Pattern: "Q4 2028" or "2028 Q4"
    match = re.search(r'Q([1-4])\s*(\d{4})', claimed)
    if match:
        return int(match.group(2)), int(match.group(1))
    
    match = re.search(r'(\d{4})\s*Q([1-4])', claimed)
    if match:
        return int(match.group(1)), int(match.group(2))
    
    # Pattern: Just a year "2028"
    match = re.search(r'(\d{4})', claimed)
    if match:
        return int(match.group(1)), None
    
    # Pattern: "24 months" or "2 years"
    match = re.search(r'(\d+)\s*months?', claimed.lower())
    if match:
        from datetime import datetime
        months = int(match.group(1))
        now = datetime.now()
        target_year = now.year + (now.month + months - 1) // 12
        target_quarter = ((now.month + months - 1) % 12) // 3 + 1
        return target_year, target_quarter
    
    match = re.search(r'(\d+)\s*years?', claimed.lower())
    if match:
        from datetime import datetime
        years = int(match.group(1))
        now = datetime.now()
        return now.year + years, None
    
    return None, None
