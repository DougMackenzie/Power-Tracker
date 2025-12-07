"""
Web Intelligence Agent for Critical Path Module.
Researches equipment lead times and interconnection timelines.
"""

from typing import Dict
from datetime import datetime
import json

from .llm_integration import get_llm_response
from .critical_path import CriticalPathData, get_milestone_templates


def research_equipment_lead_times(cp_data: CriticalPathData) -> Dict:
    """
    Research current equipment lead times using AI.
    
    Args:
        cp_data: Critical path data to update
        
    Returns:
        Dictionary with research results
    """
    equipment_types = [
        "transformer_345kv",
        "transformer_230kv",
        "transformer_138kv",
        "transformer_69kv",
        "circuit_breaker_345kv",
        "circuit_breaker_230kv",
        "circuit_breaker_138kv",
        "gas_turbine_combustion",
        "battery_storage_system",
        "switchgear_med_voltage"
    ]
    
    prompt = f"""
You are a power industry expert. Research CURRENT (2025) lead times for major power equipment.

EQUIPMENT TYPES TO RESEARCH:
{json.dumps(equipment_types, indent=2)}

For each equipment type, provide:
1. **typical_weeks**: Historical typical lead time (in weeks)
2. **current_weeks**: Current 2025 lead time based on market conditions (in weeks)
3. **trend**: "increasing", "stable", or "decreasing"
4. **confidence**: 0.0-1.0 (how confident you are in this information)
5. **factors**: List of 2-3 key factors affecting lead times
6. **notes**: Brief explanation of current market conditions

Consider factors:
- Supply chain status in 2025
- Manufacturing capacity
- Data center boom impact on transformer demand
- Material availability (copper, steel, silicon steel)
- Backlog at major manufacturers (ABB, Siemens, GE)
- Energy transition investments

Return ONLY valid JSON:
{{
  "equipment_lead_times": {{
    "transformer_345kv": {{
      "typical_weeks": 130,
      "current_weeks": 165,
      "trend": "increasing",
      "confidence": 0.85,
      "factors": ["Data center demand surge", "Limited manufacturing capacity", "Copper supply constraints"],
      "notes": "345kV transformers seeing significant delays due to unprecedented data center demand"
    }}
  }},
  "research_date": "2025-12-06",
  "sources_consulted": ["Industry knowledge base", "Market trends 2024-2025", "Supply chain analysis"]
}}
"""
    
    try:
        response = get_llm_response(prompt)
        
        # Parse response
        response = response.strip()
        if response.startswith('```'):
            lines = response.split('\n')
            response = '\n'.join(lines[1:-1])
        
        data = json.loads(response)
        
        # Initialize intelligence database if needed
        if not cp_data.intelligence_database:
            cp_data.intelligence_database = {}
        
        # Store equipment lead times
        cp_data.intelligence_database['equipment_lead_times'] = data.get('equipment_lead_times', {})
        cp_data.intelligence_database['last_updated'] = datetime.now().isoformat()
        cp_data.intelligence_database['equipment_research_date'] = data.get('research_date')
        
        return data
        
    except Exception as e:
        print(f"Equipment research error: {e}")
        return {'error': str(e)}


def research_iso_timelines(cp_data: CriticalPathData) -> Dict:
    """
    Research interconnection study timelines by ISO.
    
    Args:
        cp_data: Critical path data to update
        
    Returns:
        Dictionary with research results
    """
    isos = ["PJM", "ERCOT", "MISO", "SPP", "CAISO", "ISONE", "NYISO"]
    
    prompt = f"""
You are a power interconnection expert. Research CURRENT (2025) interconnection study timelines.

ISOS TO RESEARCH:
{json.dumps(isos, indent=2)}

For each ISO, provide typical duration in weeks for:
1. **screening_weeks**: Screening/Feasibility Study
2. **sis_weeks**: System Impact Study
3. **fs_weeks**: Facilities Study  
4. **queue_weeks**: Typical queue wait time before study start
5. **total_process_weeks**: Total from application to IA execution
6. **trend**: "improving", "stable", or "worsening"
7. **notes**: Key insights about this ISO's process

Consider:
- Recent reform efforts (e.g., FERC Order 2023)
- Queue sizes and backlog
- Study consolidation practices
- Fast-track options for large projects
- ISO-specific process improvements

Return ONLY valid JSON:
{{
  "iso_timelines": {{
    "PJM": {{
      "screening_weeks": 8,
      "sis_weeks": 26,
      "fs_weeks": 38,
      "queue_weeks": 12,
      "total_process_weeks": 84,
      "trend": "improving",
      "notes": "PJM implementing reforms to speed up process for large loads"
    }}
  }},
  "research_date": "2025-12-06"
}}
"""
    
    try:
        response = get_llm_response(prompt)
        
        # Parse response
        response = response.strip()
        if response.startswith('```'):
            lines = response.split('\n')
            response = '\n'.join(lines[1:-1])
        
        data = json.loads(response)
        
        # Initialize intelligence database if needed
        if not cp_data.intelligence_database:
            cp_data.intelligence_database = {}
        
        # Store ISO timelines
        cp_data.intelligence_database['iso_timelines'] = data.get('iso_timelines', {})
        cp_data.intelligence_database['last_updated'] = datetime.now().isoformat()
        cp_data.intelligence_database['iso_research_date'] = data.get('research_date')
        
        return data
        
    except Exception as e:
        print(f"ISO research error: {e}")
        return {'error': str(e)}


def research_all_intelligence(cp_data: CriticalPathData) -> Dict:
    """
    Perform comprehensive research on all intelligence areas.
    
    Args:
        cp_data: Critical path data to update
        
    Returns:
        Combined research results
    """
    results = {}
    
    # Research equipment lead times
    equip_results = research_equipment_lead_times(cp_data)
    results['equipment'] = equip_results
    
    # Research ISO timelines
    iso_results = research_iso_timelines(cp_data)
    results['iso'] = iso_results
    
    return results


def apply_intelligence_to_schedule(
    cp_data: CriticalPathData,
    equipment_id: str,
    intelligence_data: Dict
) -> bool:
    """
    Apply intelligence data to update schedule lead times.
    
    Args:
        cp_data: Critical path data
        equipment_id: Equipment type ID (e.g., 'transformer_345kv')
        intelligence_data: Intelligence data for this equipment
        
    Returns:
        True if applied successfully
    """
    try:
        # Map equipment types to milestones
        equipment_milestone_map = {
            'transformer_345kv': 'POST-EQ-02',  # Transformer Manufacturing
            'transformer_230kv': 'POST-EQ-02',
            'transformer_138kv': 'POST-EQ-02',
            'transformer_69kv': 'POST-EQ-02',
            'circuit_breaker_345kv': 'POST-EQ-05',  # Breaker Manufacturing
            'circuit_breaker_230kv': 'POST-EQ-05',
            'circuit_breaker_138kv': 'POST-EQ-05',
        }
        
        milestone_id = equipment_milestone_map.get(equipment_id)
        if not milestone_id or milestone_id not in cp_data.milestones:
            return False
        
        instance = cp_data.milestones[milestone_id]
        current_weeks = intelligence_data.get('current_weeks')
        
        if current_weeks:
            instance.duration_override = current_weeks
            
            # Record application in intelligence database
            if 'applied_intelligence' not in cp_data.intelligence_database:
                cp_data.intelligence_database['applied_intelligence'] = []
            
            cp_data.intelligence_database['applied_intelligence'].append({
                'timestamp': datetime.now().isoformat(),
                'equipment_id': equipment_id,
                'milestone_id': milestone_id,
                'weeks_applied': current_weeks,
                'previous_weeks': instance.duration_override
            })
            
            return True
        
        return False
        
    except Exception as e:
        print(f"Error applying intelligence: {e}")
        return False


def apply_iso_intelligence_to_schedule(
    cp_data: CriticalPathData,
    iso: str,
    timeline_data: Dict
) -> bool:
    """
    Apply ISO timeline intelligence to interconnection milestones.
    
    Args:
        cp_data: Critical path data
        iso: ISO name (e.g., 'PJM')
        timeline_data: Timeline data for this ISO
        
    Returns:
        True if applied successfully
    """
    try:
        # Map to milestones
        milestone_mapping = {
            'screening_weeks': 'PS-PWR-04',  # Screening Study
            'sis_weeks': 'PS-PWR-05',  # SIS
            'fs_weeks': 'PS-PWR-06',  # FS
        }
        
        applied_count = 0
        
        for timeline_key, milestone_id in milestone_mapping.items():
            if milestone_id in cp_data.milestones and timeline_key in timeline_data:
                weeks = timeline_data[timeline_key]
                cp_data.milestones[milestone_id].duration_override = weeks
                applied_count += 1
        
        if applied_count > 0:
            # Record application
            if 'applied_intelligence' not in cp_data.intelligence_database:
                cp_data.intelligence_database['applied_intelligence'] = []
            
            cp_data.intelligence_database['applied_intelligence'].append({
                'timestamp': datetime.now().isoformat(),
                'iso': iso,
                'milestones_updated': applied_count,
                'timeline_data': timeline_data
            })
            
            return True
        
        return False
        
    except Exception as e:
        print(f"Error applying ISO intelligence: {e}")
        return False
