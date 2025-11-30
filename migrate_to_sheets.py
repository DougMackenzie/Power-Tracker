"""
One-time migration script to populate Google Sheets with existing site data.
Run this locally to migrate the JSON data to Google Sheets.
"""

import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Load existing JSON data
with open('portfolio_manager/site_database.json', 'r') as f:
    db = json.load(f)

# Connect to Google Sheets
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

credentials = Credentials.from_service_account_file(
    'service_account.json',
    scopes=scopes
)

client = gspread.authorize(credentials)
sheet = client.open("Sites Tracker - App")

# Create Sites worksheet
try:
    sites_ws = sheet.worksheet("Sites")
    sites_ws.clear()
except:
    sites_ws = sheet.add_worksheet(title="Sites", rows=1000, cols=50)

# Add headers
headers = [
    "site_id", "name", "state", "utility", "target_mw", "acreage", "iso", "county",
    "developer", "land_status", "community_support", "political_support",
    "dev_experience", "capital_status", "financial_status", "last_updated",
    "phases_json", "onsite_gen_json", "schedule_json", "non_power_json",
    "risks_json", "opps_json", "questions_json"
]
sites_ws.append_row(headers)

# Add all sites
for site_id, site in db['sites'].items():
    row = [
        site_id,
        site.get('name', ''),
        site.get('state', ''),
        site.get('utility', ''),
        site.get('target_mw', 0),
        site.get('acreage', 0),
        site.get('iso', ''),
        site.get('county', ''),
        site.get('developer', ''),
        site.get('land_status', ''),
        site.get('community_support', ''),
        site.get('political_support', ''),
        site.get('dev_experience', ''),
        site.get('capital_status', ''),
        site.get('financial_status', ''),
        site.get('last_updated', ''),
        json.dumps(site.get('phases', [])),
        json.dumps(site.get('onsite_gen', {})),
        json.dumps(site.get('schedule', {})),
        json.dumps(site.get('non_power', {})),
        json.dumps(site.get('risks', [])),
        json.dumps(site.get('opps', [])),
        json.dumps(site.get('questions', []))
    ]
    sites_ws.append_row(row)
    print(f"Added {site.get('name')}")

# Create Metadata worksheet
try:
    meta_ws = sheet.worksheet("Metadata")
    meta_ws.clear()
except:
    meta_ws = sheet.add_worksheet(title="Metadata", rows=10, cols=5)

meta_ws.append_row(['created', 'last_updated', 'version'])
meta_ws.append_row([
    db['metadata']['created'],
    db['metadata']['last_updated'],
    db['metadata']['version']
])

print("\nMigration complete!")
print(f"Migrated {len(db['sites'])} sites to Google Sheets")
