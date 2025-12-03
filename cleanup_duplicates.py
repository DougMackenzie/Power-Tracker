"""
Script to clean up test sites from Google Sheets
"""

import gspread
from google.oauth2.service_account import Credentials

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
sites_ws = sheet.worksheet("Sites")

# Get all data
all_data = sites_ws.get_all_values()
headers = all_data[0]
rows = all_data[1:]

# Keep only non-test sites (Tulsa, DFW, Atlanta)
keep_names = ['Tulsa Metro Hub', 'DFW Industrial Corridor', 'Atlanta Metro Campus']
filtered_rows = [row for row in rows if row[1] in keep_names]

# Clear and rewrite
sites_ws.clear()
sites_ws.append_row(headers)
for row in filtered_rows:
    sites_ws.append_row(row)

print(f"Cleaned up sites. Kept {len(filtered_rows)} sites:")
for row in filtered_rows:
    print(f"  - {row[1]}")
print(f"Removed {len(rows) - len(filtered_rows)} test sites.")
