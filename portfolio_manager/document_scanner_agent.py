"""
Document Scanner Agent for Critical Path Module.
Scans documents (emails, meeting notes, PDFs) for milestone updates.
"""

from pathlib import Path
from typing import List, Dict
from datetime import datetime
import json

from .document_utils import extract_text_from_file
from .llm_integration import get_llm_response
from .critical_path import CriticalPathData, MilestoneStatus, get_milestone_templates


def scan_documents_for_updates(
    folder_path: str,
    file_types: List[str],
    site_id: str,
    cp_data: CriticalPathData
) -> Dict:
    """
    Scan documents in folder for critical path updates.
    
    Args:
        folder_path: Path to folder containing documents
        file_types: List of file extensions to scan (e.g., ['PDF', 'DOCX'])
        site_id: Site identifier
        cp_data: Current critical path data
        
    Returns:
        Dictionary with scan results:
        {
            'files_scanned': int,
            'updates': List[Dict],
            'errors': List[str]
        }
    """
    results = {
        'files_scanned': 0,
        'updates': [],
        'errors': []
    }
    
    # Validate folder
    folder = Path(folder_path)
    if not folder.exists():
        results['errors'].append(f"Folder not found: {folder_path}")
        return results
    
    if not folder.is_dir():
        results['errors'].append(f"Path is not a directory: {folder_path}")
        return results
    
    # Normalize file types
    file_exts = [f".{ft.lower().replace('.', '')}" for ft in file_types]
    
    # Scan all files
    for file_path in folder.rglob('*'):
        if not file_path.is_file():
            continue
        
        if file_path.suffix.lower() not in file_exts:
            continue
        
        results['files_scanned'] += 1
        
        # Extract text
        text = extract_text_from_file(str(file_path))
        if not text or len(text.strip()) < 50:  # Skip very short files
            continue
        
        # Extract updates using LLM
        try:
            updates = extract_updates_with_llm(text, file_path.name, cp_data)
            results['updates'].extend(updates)
        except Exception as e:
            results['errors'].append(f"Error processing {file_path.name}: {str(e)}")
    
    # Update scan history
    if not cp_data.document_scan_history:
        cp_data.document_scan_history = {}
    
    cp_data.document_scan_history = {
        'last_scan_date': datetime.now().isoformat(),
        'scanned_folder': folder_path,
        'files_scanned': results['files_scanned'],
        'updates_found_count': len(results['updates'])
    }
    
    return results


def extract_updates_with_llm(
    text: str,
    source_file: str,
    cp_data: CriticalPathData
) -> List[Dict]:
    """
    Use LLM to extract milestone updates from document text.
    
    Args:
        text: Document text content
        source_file: Name of source file
        cp_data: Current critical path data
        
    Returns:
        List of update dictionaries
    """
    # Build milestone reference
    templates = get_milestone_templates()
    milestone_ref = []
    
    for ms_id, instance in cp_data.milestones.items():
        tmpl = templates.get(ms_id)
        if tmpl:
            milestone_ref.append({
                'id': ms_id,
                'name': tmpl.name,
                'current_status': instance.status.value,
                'phase': tmpl.phase.value,
                'workstream': tmpl.workstream.value
            })
    
    # Limit text to avoid token limits
    text_sample = text[:8000]  # ~2000 tokens
    
    prompt = f"""
Analyze this document for critical path milestone updates related to a power project.

DOCUMENT EXCERPT:
{text_sample}

CURRENT MILESTONES:
{json.dumps(milestone_ref[:30], indent=2)}  # First 30 milestones

TASK:
Extract any mentions of:
1. Study completions (screening, SIS, facilities study, environmental)
2. Agreement signings (IA, FA, PSA, land purchase)
3. Permit approvals (zoning, building, environmental)
4. Equipment milestones (transformer/breaker orders, deliveries, manufacturing)
5. Construction milestones (NTP, construction complete, energization)
6. Schedule changes or delays
7. New target dates

For each update found, determine:
- Which milestone it relates to (match to milestone ID)
- Type of update (status_change, date_change, duration_change)
- Old and new values
- Confidence level (0.0-1.0)
- Exact quote from document

Return ONLY valid JSON (no markdown formatting):
{{
  "updates": [
    {{
      "milestone_id": "PS-PWR-04",
      "milestone_name": "Screening Study Complete",
      "update_type": "status_change",
      "old_value": "In Progress",
      "new_value": "Complete",
      "confidence": 0.95,
      "excerpt": "exact quote from document showing this update"
    }}
  ]
}}

IMPORTANT:
- Only include updates with confidence >= 0.70
- Use exact milestone IDs from the list above
- Include actual text excerpts as evidence
- If no updates found, return {{"updates": []}}
"""
    
    try:
        response = get_llm_response(prompt)
        
        # Parse JSON response
        # Remove markdown formatting if present
        response = response.strip()
        if response.startswith('```'):
            # Remove code fence
            lines = response.split('\n')
            response = '\n'.join(lines[1:-1])
        
        data = json.loads(response)
        
        # Add source file to each update
        for update in data.get('updates', []):
            update['source_file'] = source_file
            update['timestamp'] = datetime.now().isoformat()
            update['applied'] = False
        
        return data.get('updates', [])
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Response was: {response[:200]}")
        return []
    except Exception as e:
        print(f"LLM extraction error: {e}")
        return []


def apply_document_update(cp_data: CriticalPathData, update: Dict) -> bool:
    """
    Apply a detected update to the critical path.
    
    Args:
        cp_data: Critical path data to update
        update: Update dictionary from scan results
        
    Returns:
        True if applied successfully
    """
    try:
        milestone_id = update['milestone_id']
        
        if milestone_id not in cp_data.milestones:
            return False
        
        instance = cp_data.milestones[milestone_id]
        update_type = update['update_type']
        
        if update_type == 'status_change':
            # Update milestone status
            try:
                new_status = MilestoneStatus(update['new_value'])
                instance.status = new_status
            except ValueError:
                # Try to map common status names
                status_map = {
                    'complete': MilestoneStatus.COMPLETE,
                    'completed': MilestoneStatus.COMPLETE,
                    'done': MilestoneStatus.COMPLETE,
                    'finished': MilestoneStatus.COMPLETE,
                    'in progress': MilestoneStatus.IN_PROGRESS,
                    'started': MilestoneStatus.IN_PROGRESS,
                    'ongoing': MilestoneStatus.IN_PROGRESS,
                    'blocked': MilestoneStatus.BLOCKED,
                    'delayed': MilestoneStatus.BLOCKED,
                    'not started': MilestoneStatus.NOT_STARTED,
                    'pending': MilestoneStatus.NOT_STARTED
                }
                status_key = update['new_value'].lower()
                if status_key in status_map:
                    instance.status = status_map[status_key]
                else:
                    return False
        
        elif update_type == 'duration_change':
            # Update duration override
            try:
                new_duration = int(update['new_value'])
                instance.duration_override = new_duration
            except ValueError:
                return False
        
        # Mark update as applied
        update['applied'] = True
        
        # Store in scan history
        if 'applied_updates' not in cp_data.document_scan_history:
            cp_data.document_scan_history['applied_updates'] = []
        
        cp_data.document_scan_history['applied_updates'].append(update)
        
        return True
        
    except Exception as e:
        print(f"Error applying update: {e}")
        return False
