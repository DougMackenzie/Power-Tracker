"""
Site Profile Builder
=====================
Maps existing app data to SiteProfileData and identifies gaps
that can be filled via:
1. Existing app data (auto-mapped)
2. AI research using lat/lon (researchable)
3. Human input (site-specific knowledge required)

Usage:
    from site_profile_builder import SiteProfileBuilder, build_research_prompt
    
    builder = SiteProfileBuilder(site_data)
    profile = builder.build_profile()
    
    # Get gaps that need AI research
    research_prompt = builder.get_research_prompt()
    
    # Get gaps that need human input
    missing = builder.get_human_input_fields()
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import json
from .pptx_export import SiteProfileData


# =============================================================================
# FIELD CLASSIFICATION
# =============================================================================

# Fields already captured in the app (from google_integration.py COLUMN_ORDER)
APP_FIELDS = {
    'site_id', 'name', 'state', 'utility', 'target_mw', 'acreage', 'iso', 
    'county', 'developer', 'land_status', 'community_supp', 'political_support',
    'dev_experience', 'capital_status', 'financial_status',
    'phases_json', 'onsite_gen_json', 'schedule_json', 'non_power_json',
    'risks_json', 'opps_json', 'questions_json',
    'client', 'total_fee_potential', 'contract_status',
    'site_control_stage', 'power_stage', 'marketing_stage', 'buyer_stage',
    'zoning_stage', 'water_stage', 'incentives_stage',
    'probability', 'weighted_fee', 'tracker_notes',
    # These might also be in the app
    'latitude', 'longitude', 'voltage_kv', 'water_capacity',
    'fiber_available', 'environmental_complete',
}

# Fields that can be researched via AI using lat/lon coordinates
AI_RESEARCHABLE_FIELDS = {
    # Location/Distance calculations
    'nearest_town': 'Nearest incorporated town/city',
    'distance_to_town': 'Distance to nearest town in miles',
    'airport_name': 'Nearest commercial airport',
    'distance_to_airport': 'Distance to nearest commercial airport',
    'highway_name': 'Nearest major highway/interstate',
    'highway_distance': 'Distance to nearest highway interchange',
    'rail_access': 'Nearest rail line and distance',
    
    # Risk assessment (FEMA, USGS data)
    'flood_zone': 'FEMA flood zone designation',
    'seismic_risk': 'Seismic hazard level (Low/Moderate/High)',
    'hurricane_risk': 'Hurricane/severe weather risk level',
    'tornado_risk': 'Tornado frequency/risk for region',
    
    # Demographics (Census data)
    'workforce_population': 'Population within 30-mile radius',
    'unemployment_rate': 'Regional unemployment rate',
    
    # Utility territory
    'electric_utility': 'Electric utility serving the area',
    'gas_provider': 'Natural gas provider in area',
    'water_provider': 'Municipal water provider',
    
    # Regulatory
    'current_zoning': 'Current zoning classification',
}

# Fields requiring human input (site-specific knowledge)
HUMAN_INPUT_FIELDS = {
    # Ownership (confidential/negotiation)
    'owner_name': 'Property owner name(s)',
    'willing_to_sell': 'Confirmed willingness to sell (Yes/No/TBD)',
    'asking_price': 'Asking price or price expectation',
    
    # Site observations (require site visit)
    'site_condition': 'Site condition (Greenfield/Brownfield/Existing)',
    'topography': 'Topography description',
    'slope': 'Slope/grade percentage',
    'soil_type': 'Soil type and bearing capacity',
    
    # Environmental (require studies)
    'environmental_status': 'Phase I ESA status',
    'phase1_esa': 'Phase I ESA findings',
    'ecological_concerns': 'Ecological concerns identified',
    'archeological': 'Archeological survey status',
    
    # Wetlands (require delineation)
    'wetlands_present': 'Wetlands present on site (True/False)',
    'wetlands_acres': 'Wetland acreage',
    'wetlands_avoidable': 'Can wetlands be avoided for development',
    'jurisdictional_water': 'Jurisdictional waters description',
    
    # Easements (require title search)
    'easements': 'Existing easements on property',
    'right_of_way': 'Right of way requirements',
    
    # Utilities (require utility contact)
    'voltage_kv': 'Available transmission voltage (kV)',
    'transmission_line': 'Nearest transmission line description',
    'distance_to_transmission': 'Distance to transmission interconnect',
    'water_capacity_gpd': 'Available water capacity (GPD)',
    'water_line_size': 'Water line size to property',
    'wastewater_solution': 'Wastewater discharge solution',
    'wastewater_capacity_gpd': 'Wastewater capacity (GPD)',
    'fiber_provider': 'Fiber provider(s) at site',
    'fiber_capacity': 'Available fiber capacity',
    'gas_capacity': 'Available gas capacity',
    
    # Timeline (negotiation dependent)
    'time_to_close': 'Estimated time to close',
    'phase1_delivery': 'Phase 1 delivery target',
    'zoning_timeline': 'Zoning approval timeline',
}


# =============================================================================
# MAPPING FROM APP TO SITE PROFILE
# =============================================================================

def map_app_to_profile(site_data: Dict) -> SiteProfileData:
    """
    Map existing app data to SiteProfileData fields.
    Returns a partially filled profile with available data.
    """
    profile = SiteProfileData()
    
    # === FIRST: Load previously saved profile_json if exists ===
    if site_data.get('profile_json'):
        try:
            saved_profile = site_data['profile_json']
            # Handle both dict and JSON string
            if isinstance(saved_profile, str):
                saved_profile = json.loads(saved_profile)
            
            if isinstance(saved_profile, dict):
                # Restore all saved fields
                fields_restored = 0
                for field, value in saved_profile.items():
                    if hasattr(profile, field) and value:
                        setattr(profile, field, value)
                        fields_restored += 1
                
                # Debug: Print how many fields were restored
                print(f"[DEBUG] Restored {fields_restored} fields from profile_json")
                
                # If we have a saved profile, return it (already enriched)
                # We still continue below to overlay any NEW data from current site_data
        except (json.JSONDecodeError, Exception) as e:
            print(f"[DEBUG] Failed to load profile_json: {type(e).__name__}: {e}")
            pass  # Ignore errors, fall through to auto-mapping
    else:
        print(f"[DEBUG] No profile_json found in site_data. Keys: {list(site_data.keys())[:10]}")
    
    # Direct mappings (will override saved data if present)
    if site_data.get('name'):
        profile.name = site_data.get('name', '')
    if site_data.get('state'):
        profile.state = site_data.get('state', '')
    
    # Acreage
    acreage = site_data.get('acreage') or site_data.get('total_acres', 0)
    if acreage:
        profile.total_acres = float(acreage)
    
    # Electricity from utility field
    profile.electric_utility = site_data.get('utility', '')
    
    # Estimated capacity from target_mw
    if site_data.get('target_mw'):
        profile.estimated_capacity_mw = float(site_data['target_mw'])
    
    # Coordinates
    if site_data.get('latitude') and site_data.get('longitude'):
        profile.coordinates = f"{site_data['latitude']}, {site_data['longitude']}"
    
    # === NEW: Extract from phases data ===
    phases = site_data.get('phases_json') or site_data.get('phases', [])
    if phases and isinstance(phases, list):
        # Voltage (highest available)
        voltages = []
        for p in phases:
            if isinstance(p, dict):
                v = p.get('voltage') or p.get('voltage_kv', 0)
                if v:
                    try:
                        voltages.append(int(v))
                    except (ValueError, TypeError):
                        pass
        if voltages:
            max_voltage = max(voltages)
            profile.voltage_kv = str(max_voltage)
            profile.transmission_line = f"{max_voltage} kV line (see phases)"
        
        # Distance to transmission (shortest from any phase)
        distances = []
        for p in phases:
            if isinstance(p, dict) and p.get('trans_dist'):
                try:
                    distances.append(float(p['trans_dist']))
                except (ValueError, TypeError):
                    pass
        if distances:
            min_dist = min(distances)
            profile.distance_to_transmission = f"{min_dist} miles"
        
        # Phase 1 delivery from first phase
        if len(phases) > 0:
            phase1 = phases[0]
            if isinstance(phase1, dict):
                if phase1.get('target_date'):
                    profile.phase1_delivery = phase1['target_date']
                elif phase1.get('target_online'):
                    profile.phase1_delivery = phase1['target_online']
                if phase1.get('mw') or phase1.get('target_mw'):
                    mw = phase1.get('mw') or phase1.get('target_mw')
                    try:
                        profile.phase1_acres = float(mw) / 5  # Estimate: 5 MW/acre
                    except (ValueError, TypeError):
                        pass
    
    # === NEW: Extract from non_power data ===
    non_power = site_data.get('non_power_json') or site_data.get('non_power', {})
    if isinstance(non_power, dict):
        # Water
        if non_power.get('water_cap'):
            water_val = non_power['water_cap']
            # Handle both string and numeric formats
            if isinstance(water_val, (int, float)):
                profile.water_capacity_gpd = f"{water_val:,} GPD"
            else:
                profile.water_capacity_gpd = str(water_val)
        
        if non_power.get('water_source'):
            profile.water_provider = non_power['water_source']
        
        if non_power.get('wastewater'):
            profile.wastewater_solution = non_power['wastewater']
        
        # Fiber
        if non_power.get('fiber_provider'):
            profile.fiber_provider = non_power['fiber_provider']
        
        if non_power.get('fiber_status'):
            fiber_status = non_power['fiber_status']
            if 'lit' in fiber_status.lower():
                profile.fiber_capacity = "Lit fiber available"
            elif 'at site' in fiber_status.lower() or 'nearby' in fiber_status.lower():
                profile.fiber_capacity = fiber_status
            else:
                profile.fiber_capacity = f"Status: {fiber_status}"
        
        # Gas
        if non_power.get('gas_cap') or non_power.get('gas_capacity'):
            gas_val = non_power.get('gas_cap') or non_power.get('gas_capacity')
            if isinstance(gas_val, (int, float)):
                profile.gas_capacity = f"{gas_val:,} MMBTU/day"
            else:
                profile.gas_capacity = str(gas_val)
        
        # Zoning
        if non_power.get('zoning_status'):
            zoning = non_power['zoning_status']
            profile.current_zoning = zoning
            if 'approved' in zoning.lower():
                profile.permits_proposed_use = 'Approved'
            elif 'submitted' in zoning.lower():
                profile.permits_proposed_use = 'Pending approval'
            elif 'pre-app' in zoning.lower():
                profile.permits_proposed_use = 'Pre-application in progress'
    
    # Voltage fallback if not in phases
    if not profile.voltage_kv and site_data.get('voltage_kv'):
        profile.voltage_kv = str(site_data['voltage_kv'])
    
    # Water fallback from water_capacity
    if not profile.water_capacity_gpd and site_data.get('water_capacity'):
        profile.water_capacity_gpd = str(site_data['water_capacity'])
    
    # Fiber fallback from fiber_available
    if not profile.fiber_capacity and site_data.get('fiber_available'):
        profile.fiber_capacity = 'Available' if site_data['fiber_available'] else 'TBD'
    
    # Environmental from environmental_complete
    if site_data.get('environmental_complete'):
        profile.environmental_status = 'Complete' if site_data['environmental_complete'] else 'In Progress'
    
    # Land status to site condition
    land_status = site_data.get('land_status', '')
    if 'control' in land_status.lower() or 'loi' in land_status.lower():
        profile.willing_to_sell = 'Yes'
    
    # Zoning stage to zoning status (if not already set from non_power)
    if not profile.permits_proposed_use:
        zoning_stage = site_data.get('zoning_stage', 0)
        if zoning_stage:
            zoning_map = {
                1: 'Research needed',
                2: 'In progress',
                3: 'Approved',
            }
            profile.permits_proposed_use = zoning_map.get(zoning_stage, 'TBD')
    
    # County
    if site_data.get('county'):
        # Only use county as nearest_town if we don't have better info
        if not profile.nearest_town or profile.nearest_town == '':
            profile.nearest_town = site_data['county'] + ' County'
    
    # Overview from existing data - build a compelling summary
    overview_parts = []
    if profile.total_acres:
        overview_parts.append(f"{profile.total_acres:,.0f} acre site")
    if profile.estimated_capacity_mw:
        mw = profile.estimated_capacity_mw
        cap = f"{mw/1000:.1f}GW" if mw >= 1000 else f"{mw:.0f}MW"
        overview_parts.append(f"with {cap} target capacity")
    if site_data.get('county'):
        overview_parts.append(f"in {site_data['county']} County")
    if profile.state:
        if not site_data.get('county'):
            overview_parts.append(f"in {profile.state}")
        else:
            overview_parts[-1] += f", {profile.state}"
    if profile.electric_utility:
        overview_parts.append(f"served by {profile.electric_utility}")
    
    if overview_parts:
        profile.overview = " ".join(overview_parts) + "."
    else:
        profile.overview = ""
    
    # Observation - key positive observations
    observations = []
    if site_data.get('power_stage', 0) >= 3:
        observations.append("Strong utility engagement")
    if site_data.get('land_status') and 'loi' in site_data.get('land_status', '').lower():
        observations.append("Land under LOI")
    if site_data.get('zoning_stage', 0) >= 2:
        observations.append("Zoning pathway identified")
    profile.observation = "; ".join(observations) if observations else "to be completed"
    
    # Outstanding - items needing resolution
    outstanding = []
    if site_data.get('water_stage', 0) < 3:
        outstanding.append("Water capacity confirmation")
    if site_data.get('zoning_stage', 0) < 2:
        outstanding.append("Zoning approval")
    if not site_data.get('environmental_complete'):
        outstanding.append("Environmental studies")
    profile.outstanding = "; ".join(outstanding) if outstanding else "to be completed"
    
    return profile


# =============================================================================
# AI RESEARCH PROMPT BUILDER
# =============================================================================

def build_research_prompt(site_data: Dict, profile: SiteProfileData) -> str:
    """
    Build a prompt for AI to research missing fields using lat/lon.
    Returns a structured prompt that asks for specific, verifiable information.
    """
    lat = site_data.get('latitude', '')
    lon = site_data.get('longitude', '')
    state = site_data.get('state', '')
    county = site_data.get('county', '')
    name = site_data.get('name', 'the site')
    
    if not (lat and lon):
        return "ERROR: Latitude and longitude required for location research."
    
    prompt = f"""Research the following location-based information for a data center site evaluation.

**Site Location:**
- Name: {name}
- Coordinates: {lat}, {lon}
- State: {state}
- County: {county}

**Please research and provide the following information. Use specific data sources where possible (FEMA, Census, DOT, utility websites).**

---

**1. DISTANCE CALCULATIONS** (use straight-line or driving distance)

- Nearest incorporated city/town: [Name] - [X miles]
- Nearest commercial airport (with code): [Name (CODE)] - [X miles]  
- Nearest interstate/major highway: [Highway name] - [X miles to interchange]
- Nearest rail line: [Railroad name] - [X miles], [active/inactive]

---

**2. NATURAL HAZARD ASSESSMENT**

- FEMA Flood Zone: [Zone X/A/AE/etc.] (Source: FEMA Flood Map Service Center)
- Seismic Risk: [Low/Moderate/High] (Source: USGS Seismic Hazard Maps)
- Hurricane/Severe Weather Risk: [Low/Moderate/High]
- Tornado Risk: [Low/Moderate/High] (Note: {state} tornado alley proximity)

---

**3. LABOR MARKET** (30-mile radius from site)

- Population within 30 miles: [X million/thousand]
- Major population centers nearby: [List top 2-3 cities]
- Unemployment rate (county or MSA): [X.X%]
- Source: US Census Bureau, BLS

---

**4. UTILITY PROVIDERS** (for this specific location)

- Electric Utility: [Utility name] (IOU/Coop/Municipal)
- Natural Gas Provider: [Provider name]
- Water Provider: [Municipal provider or well required]
- Wastewater: [Municipal sewer or septic required]

---

**5. ZONING/LAND USE** (if publicly available)

- Current Zoning: [Classification if available]
- County/Municipality: [Jurisdiction name]
- Data Center Permitted: [Yes/Conditional/Rezoning Required/Unknown]

---

**Format your response as a JSON object with these exact keys:**

```json
{{
    "nearest_town": "City Name",
    "distance_to_town": "X miles",
    "airport_name": "Airport Name (CODE)",
    "distance_to_airport": "X miles",
    "highway_name": "I-XX / US-XX",
    "highway_distance": "X miles to interchange",
    "rail_access": "Railroad Name - X miles",
    "flood_zone": "Zone X",
    "seismic_risk": "Low",
    "hurricane_risk": "Moderate", 
    "tornado_risk": "Moderate",
    "workforce_population": "X.XM in MSA",
    "unemployment_rate": "X.X%",
    "electric_utility": "Utility Name",
    "gas_provider": "Provider Name",
    "water_provider": "Provider Name",
    "current_zoning": "Zoning Classification or Unknown"
}}
```
"""
    return prompt


# =============================================================================
# SITE PROFILE BUILDER CLASS
# =============================================================================

class SiteProfileBuilder:
    """
    Builds a complete SiteProfileData from multiple sources.
    """
    
    def __init__(self, site_data: Dict):
        self.site_data = site_data
        self.profile = map_app_to_profile(site_data)
        self.ai_research_results: Dict = {}
        self.human_inputs: Dict = {}
    
    def get_filled_fields(self) -> List[str]:
        """Get list of fields that have been populated."""
        filled = []
        for field_name in SiteProfileData.__dataclass_fields__:
            value = getattr(self.profile, field_name)
            if value and value != 'TBD' and value != '' and value != 0:
                filled.append(field_name)
        return filled
    
    def get_missing_fields(self) -> Dict[str, List[Tuple[str, str]]]:
        """
        Get missing fields categorized by source.
        Returns dict with 'ai_research' and 'human_input' keys.
        """
        filled = set(self.get_filled_fields())
        
        ai_missing = []
        for field, desc in AI_RESEARCHABLE_FIELDS.items():
            if field not in filled:
                ai_missing.append((field, desc))
        
        human_missing = []
        for field, desc in HUMAN_INPUT_FIELDS.items():
            if field not in filled:
                human_missing.append((field, desc))
        
        return {
            'ai_research': ai_missing,
            'human_input': human_missing,
        }
    
    def get_research_prompt(self) -> str:
        """Get prompt for AI to research missing fields."""
        return build_research_prompt(self.site_data, self.profile)
    
    def apply_ai_research(self, research_results: Dict):
        """Apply AI research results to profile."""
        self.ai_research_results = research_results
        
        # Map research results to profile fields
        field_mapping = {
            'nearest_town': 'nearest_town',
            'distance_to_town': 'distance_to_town',
            'airport_name': 'airport_name',
            'distance_to_airport': 'distance_to_airport',
            'highway_name': 'highway_name',
            'highway_distance': 'highway_distance',
            'rail_access': 'rail_access',
            'flood_zone': 'flood_zone',
            'seismic_risk': 'seismic_risk',
            'hurricane_risk': 'hurricane_risk',
            'tornado_risk': 'tornado_risk',
            'workforce_population': 'workforce_population',
            'unemployment_rate': 'unemployment_rate',
            'electric_utility': 'electric_utility',
            'gas_provider': 'gas_provider',
            'water_provider': 'water_provider',
            'current_zoning': 'current_zoning',
        }
        
        for result_key, profile_field in field_mapping.items():
            if result_key in research_results and research_results[result_key]:
                setattr(self.profile, profile_field, research_results[result_key])
    
    def apply_human_inputs(self, inputs: Dict):
        """Apply human-provided inputs to profile."""
        self.human_inputs = inputs
        
        for field, value in inputs.items():
            if hasattr(self.profile, field) and value:
                # Handle boolean fields
                if field in ['wetlands_present', 'wetlands_avoidable']:
                    value = value if isinstance(value, bool) else value.lower() in ['true', 'yes', '1']
                # Handle numeric fields
                elif field in ['wetlands_acres', 'total_acres', 'phase1_acres', 'voltage_kv']:
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        pass
                
                setattr(self.profile, field, value)
    
    def build_profile(self) -> SiteProfileData:
        """Return the current profile state."""
        return self.profile
    
    def get_completion_status(self) -> Dict:
        """Get profile completion percentage by category."""
        all_fields = set(SiteProfileData.__dataclass_fields__.keys())
        filled = set(self.get_filled_fields())
        
        # Categorize
        location_fields = {'name', 'state', 'coordinates', 'nearest_town', 'distance_to_town',
                          'airport_name', 'distance_to_airport', 'highway_name', 'highway_distance'}
        ownership_fields = {'owner_name', 'willing_to_sell', 'asking_price', 'total_acres',
                           'phase1_acres', 'phase2_acres'}
        infrastructure_fields = {'electric_utility', 'voltage_kv', 'estimated_capacity_mw',
                                'water_provider', 'water_capacity_gpd', 'wastewater_solution',
                                'fiber_provider', 'gas_provider'}
        risk_fields = {'flood_zone', 'seismic_risk', 'hurricane_risk', 'tornado_risk',
                      'wetlands_present', 'environmental_status'}
        
        def pct(category_fields):
            if not category_fields:
                return 0
            return int(len(category_fields & filled) / len(category_fields) * 100)
        
        return {
            'overall': int(len(filled) / len(all_fields) * 100),
            'location': pct(location_fields),
            'ownership': pct(ownership_fields),
            'infrastructure': pct(infrastructure_fields),
            'risk': pct(risk_fields),
            'filled_count': len(filled),
            'total_count': len(all_fields),
        }


# =============================================================================
# STREAMLIT UI HELPERS
# =============================================================================

def get_human_input_form_fields() -> List[Dict]:
    """
    Returns form field definitions for Streamlit UI.
    Each field has: name, label, type, options (if select), help text
    """
    return [
        # Ownership section
        {'section': 'Ownership & Price', 'fields': [
            {'name': 'owner_name', 'label': 'Owner Name(s)', 'type': 'text', 'help': 'Property owner name(s)'},
            {'name': 'willing_to_sell', 'label': 'Willing to Sell', 'type': 'select', 
             'options': ['TBD', 'Yes', 'No', 'In Negotiation'], 'help': 'Confirmed willingness to sell'},
            {'name': 'asking_price', 'label': 'Asking Price', 'type': 'text', 'help': 'e.g., $15,000/acre or $4.5M total'},
        ]},
        
        # Site Condition section
        {'section': 'Site Condition', 'fields': [
            {'name': 'site_condition', 'label': 'Site Condition', 'type': 'select',
             'options': ['Greenfield', 'Brownfield', 'Existing Structure'], 'help': 'Current site condition'},
            {'name': 'topography', 'label': 'Topography', 'type': 'text', 'help': 'e.g., Generally flat, Rolling hills'},
            {'name': 'slope', 'label': 'Slope/Grade', 'type': 'text', 'help': 'e.g., <2% grade'},
            {'name': 'soil_type', 'label': 'Soil Type', 'type': 'text', 'help': 'e.g., Clay loam, suitable for construction'},
        ]},
        
        # Environmental section  
        {'section': 'Environmental', 'fields': [
            {'name': 'environmental_status', 'label': 'Phase I ESA Status', 'type': 'select',
             'options': ['TBD', 'Not Started', 'In Progress', 'Complete - Clean', 'Complete - RECs Found'],
             'help': 'Phase I Environmental Site Assessment status'},
            {'name': 'phase1_esa', 'label': 'Phase I ESA Findings', 'type': 'text',
             'help': 'Summary of Phase I ESA findings'},
            {'name': 'ecological_concerns', 'label': 'Ecological Concerns', 'type': 'text',
             'help': 'e.g., None identified, Protected species habitat'},
            {'name': 'archeological', 'label': 'Archeological Survey Status', 'type': 'text',
             'help': 'e.g., Survey completed - no findings, Not yet surveyed'},
            {'name': 'jurisdictional_water', 'label': 'Jurisdictional Waters', 'type': 'text',
             'help': 'Description of jurisdictional waters on or near site'},
        ]},
        
        # Wetlands section
        {'section': 'Wetlands', 'fields': [
            {'name': 'wetlands_present', 'label': 'Wetlands Present', 'type': 'select',
             'options': ['Unknown', 'Yes', 'No'], 'help': 'Are wetlands present on site?'},
            {'name': 'wetlands_acres', 'label': 'Wetland Acres', 'type': 'number', 
             'help': 'Approximate wetland acreage if present'},
            {'name': 'wetlands_avoidable', 'label': 'Wetlands Avoidable', 'type': 'select',
             'options': ['Unknown', 'Yes', 'No'], 'help': 'Can development avoid wetland areas?'},
        ]},
        
        # Utilities section
        {'section': 'Utility Details', 'fields': [
            {'name': 'voltage_kv', 'label': 'Transmission Voltage (kV)', 'type': 'number',
             'help': 'Available transmission voltage: 138, 230, 345, 500'},
            {'name': 'transmission_line', 'label': 'Transmission Line', 'type': 'text',
             'help': 'e.g., 345kV line 0.5 miles north'},
            {'name': 'water_capacity_gpd', 'label': 'Water Capacity', 'type': 'text',
             'help': 'e.g., 3,000,000 GPD available'},
            {'name': 'water_line_size', 'label': 'Water Line Size', 'type': 'text',
             'help': 'e.g., 12-inch main, 6-inch service'},
            {'name': 'wastewater_solution', 'label': 'Wastewater Solution', 'type': 'text',
             'help': 'e.g., Municipal sewer, On-site treatment required'},
            {'name': 'wastewater_capacity_gpd', 'label': 'Wastewater Capacity (GPD)', 'type': 'text',
             'help': 'e.g., 2,000,000 GPD capacity'},
            {'name': 'fiber_provider', 'label': 'Fiber Provider(s)', 'type': 'text',
             'help': 'e.g., Zayo, AT&T, Crown Castle'},
            {'name': 'gas_capacity', 'label': 'Gas Capacity', 'type': 'text',
             'help': 'e.g., 50,000 MMBTU/day available'},
        ]},
        
        # Easements section
        {'section': 'Easements & Access', 'fields': [
            {'name': 'easements', 'label': 'Existing Easements', 'type': 'text',
             'help': 'e.g., Gas pipeline on north boundary'},
            {'name': 'right_of_way', 'label': 'Right of Way', 'type': 'text',
             'help': 'e.g., County road ROW, Private access'},
        ]},
        
        # Timeline section
        {'section': 'Timeline', 'fields': [
            {'name': 'time_to_close', 'label': 'Time to Close', 'type': 'text',
             'help': 'e.g., 90 days, 6 months'},
            {'name': 'phase1_delivery', 'label': 'Phase 1 Delivery', 'type': 'text',
             'help': 'e.g., Q1 2028'},
            {'name': 'zoning_timeline', 'label': 'Zoning Timeline', 'type': 'text',
             'help': 'e.g., 6-9 months for rezoning'},
        ]},
    ]
