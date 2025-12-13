"""
Triage Storage Layer
====================
Google Sheets integration for persisting triage and diagnosis data.
Follows the existing pattern from the main app.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any

from .models import (
    TriageLogRecord, TriageResult, DiagnosisResult,
    TRIAGE_LOG_COLUMNS, SITES_TRIAGE_COLUMNS, SITES_DIAGNOSIS_COLUMNS,
)


# =============================================================================
# TRIAGE LOG OPERATIONS
# =============================================================================

def save_triage_to_log(
    record: TriageLogRecord,
    sheet_name: str = "Triage_Log"
) -> bool:
    """
    Save a triage record to the Triage_Log sheet.
    
    Returns True if successful.
    """
    try:
        import streamlit as st
        import gspread
        from google.oauth2.service_account import Credentials
        
        # Get sheets client (reuse from main app if available)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )
        
        client = gspread.authorize(credentials)
        
        # Open the spreadsheet (use same sheet as main app)
        spreadsheet_name = st.secrets.get("GOOGLE_SHEET_NAME", "Sites Tracker - App")
        sheet = client.open(spreadsheet_name)
        
        # Get or create Triage_Log worksheet
        try:
            ws = sheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            # Create the worksheet with headers
            ws = sheet.add_worksheet(title=sheet_name, rows=1000, cols=len(TRIAGE_LOG_COLUMNS))
            ws.append_row(TRIAGE_LOG_COLUMNS)
        
        # Append the record
        row = record.to_row()
        ws.append_row(row)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to save triage log: {e}")
        return False


def load_triage_log(
    sheet_name: str = "Triage_Log",
    limit: int = 100,
) -> List[TriageLogRecord]:
    """
    Load triage log records from Google Sheets.
    
    Returns list of TriageLogRecord objects.
    """
    try:
        import streamlit as st
        import gspread
        from google.oauth2.service_account import Credentials
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )
        
        client = gspread.authorize(credentials)
        
        spreadsheet_name = st.secrets.get("GOOGLE_SHEET_NAME", "Sites Tracker - App")
        sheet = client.open(spreadsheet_name)
        
        try:
            ws = sheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            return []
        
        # Get all records
        rows = ws.get_all_values()
        
        if len(rows) <= 1:
            return []
        
        # Skip header, convert to records
        records = []
        for row in rows[1:limit+1]:
            try:
                record = TriageLogRecord.from_row(row)
                records.append(record)
            except Exception as e:
                print(f"[WARNING] Failed to parse triage log row: {e}")
                continue
        
        return records
        
    except Exception as e:
        print(f"[ERROR] Failed to load triage log: {e}")
        return []


def get_triage_statistics() -> Dict:
    """
    Calculate statistics from triage log.
    
    Returns dict with counts and rates.
    """
    records = load_triage_log(limit=500)
    
    if not records:
        return {
            'total': 0,
            'kill_count': 0,
            'conditional_count': 0,
            'pass_count': 0,
            'kill_rate': 0,
            'conditional_rate': 0,
            'pass_rate': 0,
            'advanced_count': 0,
            'by_source': {},
            'by_utility': {},
        }
    
    total = len(records)
    kill_count = len([r for r in records if r.verdict == 'KILL'])
    conditional_count = len([r for r in records if r.verdict == 'CONDITIONAL'])
    pass_count = len([r for r in records if r.verdict == 'PASS'])
    advanced_count = len([r for r in records if r.advanced_to_phase2])
    
    # By source
    by_source = {}
    for r in records:
        source = r.source or 'unknown'
        if source not in by_source:
            by_source[source] = {'total': 0, 'kill': 0, 'pass': 0}
        by_source[source]['total'] += 1
        if r.verdict == 'KILL':
            by_source[source]['kill'] += 1
        elif r.verdict == 'PASS':
            by_source[source]['pass'] += 1
    
    # By utility
    by_utility = {}
    for r in records:
        utility = r.detected_utility or 'unknown'
        if utility not in by_utility:
            by_utility[utility] = {'total': 0, 'kill': 0, 'pass': 0}
        by_utility[utility]['total'] += 1
        if r.verdict == 'KILL':
            by_utility[utility]['kill'] += 1
        elif r.verdict == 'PASS':
            by_utility[utility]['pass'] += 1
    
    return {
        'total': total,
        'kill_count': kill_count,
        'conditional_count': conditional_count,
        'pass_count': pass_count,
        'kill_rate': (kill_count / total * 100) if total > 0 else 0,
        'conditional_rate': (conditional_count / total * 100) if total > 0 else 0,
        'pass_rate': (pass_count / total * 100) if total > 0 else 0,
        'advanced_count': advanced_count,
        'by_source': by_source,
        'by_utility': by_utility,
    }


# =============================================================================
# SITE RECORD OPERATIONS
# =============================================================================

def update_site_triage_fields(
    site_id: str,
    triage_result: TriageResult,
    db: Optional[Dict] = None,
) -> bool:
    """
    Update a site record with triage results.
    
    If db is provided, updates in-memory dict.
    Otherwise tries to update Google Sheets directly.
    """
    try:
        # Build update fields
        updates = {
            'phase': '1_triage',
            'triage_date': triage_result.triage_date,
            'triage_verdict': triage_result.verdict.value,
            'triage_red_flags_json': json.dumps([rf.to_dict() for rf in triage_result.red_flags]),
        }
        
        # Update utility/ISO if enriched
        if triage_result.enrichment.utility and 'unknown' not in triage_result.enrichment.utility.lower():
            updates['utility'] = triage_result.enrichment.utility
        if triage_result.enrichment.iso and triage_result.enrichment.iso != 'Unknown':
            updates['iso'] = triage_result.enrichment.iso
        
        if db:
            # Update in-memory database
            if site_id in db.get('sites', {}):
                db['sites'][site_id].update(updates)
                db['sites'][site_id]['last_updated'] = datetime.now().isoformat()
                return True
            return False
        else:
            # Would update Google Sheets directly
            # For now, return False to indicate in-memory update required
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to update site triage fields: {e}")
        return False


def update_site_diagnosis_fields(
    site_id: str,
    diagnosis_result: DiagnosisResult,
    db: Optional[Dict] = None,
) -> bool:
    """
    Update a site record with diagnosis results.
    """
    try:
        updates = {
            'phase': '2_diagnosis',
            'diagnosis_date': diagnosis_result.diagnosis_date,
            'diagnosis_json': diagnosis_result.to_json(),
            'validated_timeline': diagnosis_result.validated_timeline,
            'timeline_risk': diagnosis_result.timeline_risk.value,
            'claim_validation_json': json.dumps([cv.to_dict() for cv in diagnosis_result.claim_validations]),
            'diagnosis_recommendation': diagnosis_result.recommendation.value,
            'diagnosis_top_risks': ', '.join(diagnosis_result.top_risks[:3]),
            'diagnosis_follow_ups': ', '.join(diagnosis_result.follow_up_actions[:3]),
            'research_summary': diagnosis_result.research_summary,
        }
        
        if db:
            if site_id in db.get('sites', {}):
                db['sites'][site_id].update(updates)
                db['sites'][site_id]['last_updated'] = datetime.now().isoformat()
                return True
            return False
        else:
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to update site diagnosis fields: {e}")
        return False


# =============================================================================
# SCHEMA MIGRATION
# =============================================================================

def ensure_triage_columns_exist(sheet_name: str = "Sites") -> bool:
    """
    Ensure the Sites sheet has all required triage/diagnosis columns.
    Adds missing columns if needed.
    """
    try:
        import streamlit as st
        import gspread
        from google.oauth2.service_account import Credentials
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )
        
        client = gspread.authorize(credentials)
        
        spreadsheet_name = st.secrets.get("GOOGLE_SHEET_NAME", "Sites Tracker - App")
        sheet = client.open(spreadsheet_name)
        ws = sheet.worksheet(sheet_name)
        
        # Get existing headers
        existing_headers = ws.row_values(1)
        
        # Required new columns
        required_columns = SITES_TRIAGE_COLUMNS + SITES_DIAGNOSIS_COLUMNS
        
        # Find missing columns
        missing = [col for col in required_columns if col not in existing_headers]
        
        if missing:
            print(f"[INFO] Adding {len(missing)} missing columns: {missing}")
            
            # Add missing columns
            next_col = len(existing_headers) + 1
            for col_name in missing:
                ws.update_cell(1, next_col, col_name)
                next_col += 1
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to ensure triage columns: {e}")
        return False


def ensure_triage_log_sheet_exists() -> bool:
    """
    Ensure the Triage_Log sheet exists with proper headers.
    """
    try:
        import streamlit as st
        import gspread
        from google.oauth2.service_account import Credentials
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )
        
        client = gspread.authorize(credentials)
        
        spreadsheet_name = st.secrets.get("GOOGLE_SHEET_NAME", "Sites Tracker - App")
        sheet = client.open(spreadsheet_name)
        
        try:
            ws = sheet.worksheet("Triage_Log")
            # Verify headers
            headers = ws.row_values(1)
            if headers != TRIAGE_LOG_COLUMNS:
                print("[INFO] Updating Triage_Log headers")
                ws.update('A1', [TRIAGE_LOG_COLUMNS])
        except gspread.WorksheetNotFound:
            print("[INFO] Creating Triage_Log sheet")
            ws = sheet.add_worksheet(title="Triage_Log", rows=1000, cols=len(TRIAGE_LOG_COLUMNS))
            ws.append_row(TRIAGE_LOG_COLUMNS)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to ensure Triage_Log sheet: {e}")
        return False


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_site_from_triage(
    triage_result: TriageResult,
    intake_data: Dict,
    db: Dict,
) -> Optional[str]:
    """
    Create a new site record from a triage result that passed.
    
    Returns site_id if successful, None otherwise.
    """
    if triage_result.verdict == 'KILL':
        return None
    
    # Generate site_id
    county = intake_data.get('county', 'site').lower().replace(' ', '_')
    state = intake_data.get('state', '').lower()
    site_id = f"{county}_{state}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Build site record
    site = {
        'name': f"{intake_data.get('county', 'New Site')} ({intake_data.get('state', '')})",
        'state': intake_data.get('state', ''),
        'county': intake_data.get('county', ''),
        'utility': triage_result.enrichment.utility,
        'iso': triage_result.enrichment.iso,
        'target_mw': intake_data.get('claimed_mw', 0),
        'acreage': intake_data.get('site_acres'),
        
        # Triage fields
        'phase': '1_triage',
        'triage_date': triage_result.triage_date,
        'triage_verdict': triage_result.verdict.value,
        'triage_red_flags_json': json.dumps([rf.to_dict() for rf in triage_result.red_flags]),
        'claimed_timeline': intake_data.get('claimed_timeline', ''),
        'triage_source': intake_data.get('source', ''),
        'triage_contact': intake_data.get('contact_name', ''),
        'triage_power_story': intake_data.get('power_story', ''),
        
        # Initialize other fields
        'developer': '',
        'land_status': '',
        'last_updated': datetime.now().isoformat(),
        
        # Program tracker defaults
        'site_control_stage': 1,
        'power_stage': 1,
        'marketing_stage': 1,
        'buyer_stage': 1,
        'zoning_stage': 1,
        'water_stage': 1,
        'incentives_stage': 1,
        'probability': 0,
        'weighted_fee': 0,
    }
    
    # Add to database
    if 'sites' not in db:
        db['sites'] = {}
    db['sites'][site_id] = site
    
    return site_id
