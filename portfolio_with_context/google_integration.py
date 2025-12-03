"""
Google Sheets & Drive Integration
==================================
Connects the Portfolio Manager to Google Sheets as the single source of truth
and Google Drive for VDR document storage.

Setup Requirements:
1. Create a Google Cloud Project
2. Enable Google Sheets API and Google Drive API
3. Create a Service Account and download credentials JSON
4. Share your Google Sheet with the service account email
5. Share your VDR Uploads folder with the service account email

Environment Variables or Streamlit Secrets:
- GOOGLE_CREDENTIALS_JSON: The service account credentials JSON (as string)
- GOOGLE_SHEET_ID: The ID of your Sites Tracker spreadsheet
- GOOGLE_VDR_FOLDER_ID: The ID of your VDR Uploads folder
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import streamlit as st

# Google API imports
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False
    print("Google API libraries not installed. Run: pip install google-api-python-client google-auth")


# =============================================================================
# CONFIGURATION
# =============================================================================

# Column mapping from app fields to Google Sheet columns
SHEET_COLUMNS = {
    'site_id': 'A',
    'name': 'B', 
    'state': 'C',
    'utility': 'D',
    'target_mw': 'E',
    'acreage': 'F',
    'iso': 'G',
    'county': 'H',
    'developer': 'I',
    'land_status': 'J',
    'community_supp': 'K',
    'political_support': 'L',
    'dev_experience': 'M',
    'capital_status': 'N',
    'financial_status': 'O',
    'last_updated': 'P',
    'phases_json': 'Q',
    'onsite_gen_json': 'R',
    'schedule_json': 'S',
    'non_power_json': 'T',
    'risks_json': 'U',
    'opps_json': 'V',
    'questions_json': 'W',
    # Program Tracker columns (X-AJ)
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

# Column order for reading/writing rows
COLUMN_ORDER = [
    'site_id', 'name', 'state', 'utility', 'target_mw', 'acreage', 'iso', 
    'county', 'developer', 'land_status', 'community_supp', 'political_support',
    'dev_experience', 'capital_status', 'financial_status', 'last_updated',
    'phases_json', 'onsite_gen_json', 'schedule_json', 'non_power_json',
    'risks_json', 'opps_json', 'questions_json',
    # Program Tracker fields
    'client', 'total_fee_potential', 'contract_status',
    'site_control_stage', 'power_stage', 'marketing_stage', 'buyer_stage',
    'zoning_stage', 'water_stage', 'incentives_stage',
    'probability', 'weighted_fee', 'tracker_notes'
]

# Tracker column order (for reference)
TRACKER_COLUMN_ORDER = [
    'client', 'total_fee_potential', 'contract_status',
    'site_control_stage', 'power_stage', 'marketing_stage', 'buyer_stage',
    'zoning_stage', 'water_stage', 'incentives_stage',
    'probability', 'weighted_fee', 'tracker_notes'
]

# Sheet name (tab)
SHEET_NAME = "Sites"  # Adjust if your tab has a different name


# =============================================================================
# GOOGLE API CLIENT
# =============================================================================

class GoogleSheetsClient:
    """Client for Google Sheets and Drive operations."""
    
    def __init__(self, credentials_json: str = None, sheet_id: str = None, vdr_folder_id: str = None):
        """
        Initialize the Google API client.
        
        Args:
            credentials_json: Service account credentials as JSON string
            sheet_id: Google Sheet ID (from URL)
            vdr_folder_id: Google Drive folder ID for VDR uploads
        """
        self.sheet_id = sheet_id or os.getenv('GOOGLE_SHEET_ID') or st.secrets.get('GOOGLE_SHEET_ID')
        self.vdr_folder_id = vdr_folder_id or os.getenv('GOOGLE_VDR_FOLDER_ID') or st.secrets.get('GOOGLE_VDR_FOLDER_ID')
        
        # Get credentials
        creds_json = credentials_json or os.getenv('GOOGLE_CREDENTIALS_JSON')
        if not creds_json and hasattr(st, 'secrets') and 'GOOGLE_CREDENTIALS_JSON' in st.secrets:
            creds_json = st.secrets['GOOGLE_CREDENTIALS_JSON']
        
        if not creds_json:
            raise ValueError("Google credentials not found. Set GOOGLE_CREDENTIALS_JSON environment variable or Streamlit secret.")
        
        # Parse credentials
        if isinstance(creds_json, str):
            creds_dict = json.loads(creds_json)
        else:
            creds_dict = dict(creds_json)
        
        # Create credentials object
        self.credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        
        # Build service clients
        self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
        self.drive_service = build('drive', 'v3', credentials=self.credentials)
    
    # -------------------------------------------------------------------------
    # SHEETS OPERATIONS
    # -------------------------------------------------------------------------
    
    def get_all_sites(self) -> List[Dict]:
        """Fetch all sites from the Google Sheet."""
        try:
            # Read all data starting from row 2 (skip header)
            range_name = f"{SHEET_NAME}!A2:W"
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=range_name
            ).execute()
            
            rows = result.get('values', [])
            sites = []
            
            for row in rows:
                # Pad row to ensure all columns exist
                while len(row) < len(COLUMN_ORDER):
                    row.append('')
                
                site = {}
                for i, col_name in enumerate(COLUMN_ORDER):
                    value = row[i] if i < len(row) else ''
                    
                    # Parse JSON columns
                    if col_name.endswith('_json') and value:
                        try:
                            site[col_name] = json.loads(value)
                        except json.JSONDecodeError:
                            site[col_name] = value
                    # Parse numeric columns
                    elif col_name in ['target_mw', 'acreage']:
                        try:
                            site[col_name] = int(float(value)) if value else 0
                        except ValueError:
                            site[col_name] = 0
                    else:
                        site[col_name] = value
                
                if site.get('site_id'):  # Only include rows with site_id
                    sites.append(site)
            
            return sites
            
        except Exception as e:
            st.error(f"Error fetching sites: {str(e)}")
            return []
    
    def get_site(self, site_id: str) -> Optional[Dict]:
        """Fetch a single site by ID."""
        sites = self.get_all_sites()
        for site in sites:
            if site.get('site_id') == site_id:
                return site
        return None
    
    def find_site_row(self, site_id: str) -> Optional[int]:
        """Find the row number for a site ID (1-indexed, accounting for header)."""
        try:
            range_name = f"{SHEET_NAME}!A:A"
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            for i, row in enumerate(values):
                if row and row[0] == site_id:
                    return i + 1  # 1-indexed
            return None
            
        except Exception as e:
            st.error(f"Error finding site row: {str(e)}")
            return None
    
    def add_site(self, site_data: Dict) -> bool:
        """Add a new site to the Google Sheet."""
        try:
            # Prepare row data
            row = self._site_to_row(site_data)
            
            # Append to sheet
            body = {'values': [row]}
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range=f"{SHEET_NAME}!A:W",
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            return True
            
        except Exception as e:
            st.error(f"Error adding site: {str(e)}")
            return False
    
    def update_site(self, site_id: str, site_data: Dict) -> bool:
        """Update an existing site in the Google Sheet."""
        try:
            # Find the row
            row_num = self.find_site_row(site_id)
            if not row_num:
                st.error(f"Site {site_id} not found")
                return False
            
            # Prepare row data
            row = self._site_to_row(site_data)
            
            # Update the row
            range_name = f"{SHEET_NAME}!A{row_num}:W{row_num}"
            body = {'values': [row]}
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            return True
            
        except Exception as e:
            st.error(f"Error updating site: {str(e)}")
            return False
    
    def delete_site(self, site_id: str) -> bool:
        """Delete a site from the Google Sheet."""
        try:
            row_num = self.find_site_row(site_id)
            if not row_num:
                return False
            
            # Get sheet ID (not spreadsheet ID)
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=self.sheet_id
            ).execute()
            
            sheet_id = None
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == SHEET_NAME:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                st.error(f"Sheet '{SHEET_NAME}' not found")
                return False
            
            # Delete the row
            request = {
                'deleteDimension': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'ROWS',
                        'startIndex': row_num - 1,  # 0-indexed
                        'endIndex': row_num
                    }
                }
            }
            
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=self.sheet_id,
                body={'requests': [request]}
            ).execute()
            
            return True
            
        except Exception as e:
            st.error(f"Error deleting site: {str(e)}")
            return False
    
    def _site_to_row(self, site_data: Dict) -> List:
        """Convert site data dict to row list for Google Sheets."""
        # Set last_updated
        site_data['last_updated'] = datetime.now().isoformat()
        
        row = []
        for col_name in COLUMN_ORDER:
            value = site_data.get(col_name, '')
            
            # Serialize JSON columns
            if col_name.endswith('_json') and isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif value is None:
                value = ''
            else:
                value = str(value)
            
            row.append(value)
        
        return row
    
    # -------------------------------------------------------------------------
    # DRIVE OPERATIONS
    # -------------------------------------------------------------------------
    
    def get_or_create_site_folder(self, site_id: str, site_name: str) -> str:
        """Get or create a folder for a site within VDR Uploads."""
        try:
            folder_name = f"{site_id}_{site_name}".replace(' ', '_')
            
            # Check if folder exists
            query = f"name='{folder_name}' and '{self.vdr_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            files = results.get('files', [])
            if files:
                return files[0]['id']
            
            # Create folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.vdr_folder_id]
            }
            
            folder = self.drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            return folder['id']
            
        except Exception as e:
            st.error(f"Error creating site folder: {str(e)}")
            return None
    
    def upload_file(self, file_content: bytes, filename: str, site_folder_id: str, mimetype: str = None) -> Optional[str]:
        """Upload a file to a site's folder in Google Drive."""
        try:
            import io
            
            if mimetype is None:
                # Guess mimetype from extension
                ext = filename.lower().split('.')[-1]
                mimetypes = {
                    'pdf': 'application/pdf',
                    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'txt': 'text/plain',
                    'csv': 'text/csv',
                    'png': 'image/png',
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                }
                mimetype = mimetypes.get(ext, 'application/octet-stream')
            
            file_metadata = {
                'name': filename,
                'parents': [site_folder_id]
            }
            
            media = MediaIoBaseUpload(
                io.BytesIO(file_content),
                mimetype=mimetype,
                resumable=True
            )
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            return file.get('webViewLink')
            
        except Exception as e:
            st.error(f"Error uploading file: {str(e)}")
            return None
    
    def list_site_files(self, site_folder_id: str) -> List[Dict]:
        """List all files in a site's folder."""
        try:
            results = self.drive_service.files().list(
                q=f"'{site_folder_id}' in parents and trashed=false",
                fields="files(id, name, mimeType, webViewLink, createdTime, size)"
            ).execute()
            
            return results.get('files', [])
            
        except Exception as e:
            st.error(f"Error listing files: {str(e)}")
            return []
    
    def upload_vdr_zip(self, zip_content: bytes, site_id: str, site_name: str) -> Dict:
        """
        Upload and extract a VDR zip file to a site's folder.
        Returns dict with folder_id and list of uploaded files.
        """
        import zipfile
        import io
        
        try:
            # Get or create site folder
            folder_id = self.get_or_create_site_folder(site_id, site_name)
            if not folder_id:
                return {'error': 'Failed to create site folder'}
            
            uploaded_files = []
            
            # Extract and upload each file
            with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zf:
                for filename in zf.namelist():
                    # Skip directories and hidden files
                    if filename.endswith('/') or filename.startswith('__') or '/.' in filename:
                        continue
                    
                    # Get just the filename (not path)
                    clean_name = filename.split('/')[-1]
                    if not clean_name:
                        continue
                    
                    # Read file content
                    file_content = zf.read(filename)
                    
                    # Upload to Drive
                    link = self.upload_file(file_content, clean_name, folder_id)
                    if link:
                        uploaded_files.append({
                            'name': clean_name,
                            'link': link
                        })
            
            return {
                'folder_id': folder_id,
                'files_uploaded': len(uploaded_files),
                'files': uploaded_files
            }
            
        except Exception as e:
            return {'error': str(e)}


# =============================================================================
# HELPER FUNCTIONS FOR APP INTEGRATION
# =============================================================================

def map_app_to_sheet(app_site: Dict) -> Dict:
    """Map app site data format to Google Sheet format."""
    
    # Map field names
    field_mapping = {
        'name': 'name',
        'state': 'state',
        'utility': 'utility',
        'target_mw': 'target_mw',
        'acreage': 'acreage',
        'iso': 'iso',
        'county': 'county',
        'developer': 'developer',
        'land_control': 'land_status',
        'community_support': 'community_supp',
        'political_support': 'political_support',
        'developer_track_record': 'dev_experience',
        'capital_access': 'capital_status',
        'end_user_status': 'financial_status',  # Could map differently
    }
    
    sheet_site = {}
    
    # Map simple fields
    for app_field, sheet_field in field_mapping.items():
        if app_field in app_site:
            sheet_site[sheet_field] = app_site[app_field]
    
    # Generate site_id if not present
    if 'site_id' not in sheet_site:
        name = app_site.get('name', 'site')
        sheet_site['site_id'] = name.lower().replace(' ', '_').replace('-', '_')
    
    # Map complex data to JSON columns
    if 'phases' in app_site:
        sheet_site['phases_json'] = app_site['phases']
    
    if 'onsite_generation' in app_site:
        sheet_site['onsite_gen_json'] = app_site['onsite_generation']
    
    # Map study status and other fields to schedule_json
    schedule_data = {}
    if 'study_status' in app_site:
        schedule_data['study_status'] = app_site['study_status']
    if 'utility_commitment' in app_site:
        schedule_data['utility_commitment'] = app_site['utility_commitment']
    if 'power_timeline_months' in app_site:
        schedule_data['power_timeline_months'] = app_site['power_timeline_months']
    if schedule_data:
        sheet_site['schedule_json'] = schedule_data
    
    # Map non-power items
    non_power = {}
    if 'water_status' in app_site:
        non_power['water_status'] = app_site['water_status']
    if 'fiber_status' in app_site:
        non_power['fiber_status'] = app_site['fiber_status']
    if 'zoning_approved' in app_site:
        non_power['zoning_approved'] = app_site['zoning_approved']
    if non_power:
        sheet_site['non_power_json'] = non_power
    
    # Map risks and opportunities
    if 'risks' in app_site:
        sheet_site['risks_json'] = app_site['risks']
    if 'opportunities' in app_site:
        sheet_site['opps_json'] = app_site['opportunities']
    if 'questions' in app_site:
        sheet_site['questions_json'] = app_site['questions']
    if 'notes' in app_site:
        sheet_site['questions_json'] = sheet_site.get('questions_json', {})
        if isinstance(sheet_site['questions_json'], dict):
            sheet_site['questions_json']['notes'] = app_site['notes']
    
    # Map Program Tracker fields (X-AJ)
    tracker_fields = [
        'client', 'total_fee_potential', 'contract_status',
        'site_control_stage', 'power_stage', 'marketing_stage', 'buyer_stage',
        'zoning_stage', 'water_stage', 'incentives_stage',
        'probability', 'weighted_fee', 'tracker_notes'
    ]
    for field in tracker_fields:
        if field in app_site:
            sheet_site[field] = app_site[field]
    
    return sheet_site


def map_sheet_to_app(sheet_site: Dict) -> Dict:
    """Map Google Sheet format to app site data format."""
    
    app_site = {
        'site_id': sheet_site.get('site_id'),
        'name': sheet_site.get('name'),
        'state': sheet_site.get('state'),
        'utility': sheet_site.get('utility'),
        'target_mw': sheet_site.get('target_mw', 0),
        'acreage': sheet_site.get('acreage', 0),
        'iso': sheet_site.get('iso'),
        'county': sheet_site.get('county'),
        'developer': sheet_site.get('developer'),
        'land_control': sheet_site.get('land_status', 'none'),
        'community_support': sheet_site.get('community_supp', 'neutral'),
        'political_support': sheet_site.get('political_support', 'neutral'),
        'developer_track_record': sheet_site.get('dev_experience', 'none'),
        'capital_access': sheet_site.get('capital_status', 'limited'),
        'last_updated': sheet_site.get('last_updated'),
    }
    
    # Parse schedule_json for study status
    schedule = sheet_site.get('schedule_json', {})
    if isinstance(schedule, dict):
        app_site['study_status'] = schedule.get('study_status', 'not_started')
        app_site['utility_commitment'] = schedule.get('utility_commitment', 'none')
        app_site['power_timeline_months'] = schedule.get('power_timeline_months', 48)
    
    # Parse non_power_json
    non_power = sheet_site.get('non_power_json', {})
    if isinstance(non_power, dict):
        app_site['water_status'] = non_power.get('water_status', 'unknown')
        app_site['fiber_status'] = non_power.get('fiber_status', 'unknown')
        app_site['zoning_approved'] = non_power.get('zoning_approved', False)
    
    # Parse phases
    app_site['phases'] = sheet_site.get('phases_json', [])
    app_site['onsite_generation'] = sheet_site.get('onsite_gen_json', [])
    app_site['risks'] = sheet_site.get('risks_json', [])
    app_site['opportunities'] = sheet_site.get('opps_json', [])
    app_site['questions'] = sheet_site.get('questions_json', [])
    
    # Parse Program Tracker fields (X-AJ)
    app_site['client'] = sheet_site.get('client', '')
    app_site['total_fee_potential'] = _safe_float(sheet_site.get('total_fee_potential', 0))
    app_site['contract_status'] = sheet_site.get('contract_status', 'No') or 'No'
    app_site['site_control_stage'] = _safe_int(sheet_site.get('site_control_stage', 1))
    app_site['power_stage'] = _safe_int(sheet_site.get('power_stage', 1))
    app_site['marketing_stage'] = _safe_int(sheet_site.get('marketing_stage', 1))
    app_site['buyer_stage'] = _safe_int(sheet_site.get('buyer_stage', 1))
    app_site['zoning_stage'] = _safe_int(sheet_site.get('zoning_stage', 1))
    app_site['water_stage'] = _safe_int(sheet_site.get('water_stage', 1))
    app_site['incentives_stage'] = _safe_int(sheet_site.get('incentives_stage', 1))
    app_site['probability'] = _safe_float(sheet_site.get('probability', 0))
    app_site['weighted_fee'] = _safe_float(sheet_site.get('weighted_fee', 0))
    app_site['tracker_notes'] = sheet_site.get('tracker_notes', '')
    
    return app_site


def _safe_float(val, default=0.0):
    """Safely convert value to float."""
    if val is None or val == '':
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=1):
    """Safely convert value to int."""
    if val is None or val == '':
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def get_google_client() -> Optional[GoogleSheetsClient]:
    """Get or create Google API client from Streamlit session state."""
    if 'google_client' not in st.session_state:
        try:
            st.session_state.google_client = GoogleSheetsClient()
        except Exception as e:
            st.error(f"Failed to initialize Google client: {str(e)}")
            return None
    return st.session_state.google_client


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("Google Sheets Integration Module")
    print("=" * 50)
    print("\nRequired environment variables:")
    print("  - GOOGLE_CREDENTIALS_JSON")
    print("  - GOOGLE_SHEET_ID")
    print("  - GOOGLE_VDR_FOLDER_ID")
    print("\nOr set these in Streamlit secrets (.streamlit/secrets.toml)")
