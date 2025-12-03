# Google Sheets Integration Setup Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA FLOW ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   💬 Chat Intake    📁 VDR Upload    ➕ Manual Entry            │
│        │                 │                 │                    │
│        └────────────────┼─────────────────┘                    │
│                         ▼                                       │
│              ┌──────────────────┐                               │
│              │  Streamlit App   │                               │
│              └────────┬─────────┘                               │
│                       │                                         │
│         ┌─────────────┴─────────────┐                          │
│         ▼                           ▼                           │
│  ┌──────────────────┐    ┌──────────────────┐                  │
│  │  Google Sheets   │    │  Google Drive    │                  │
│  │  "Sites Tracker" │    │  "VDR Uploads"   │                  │
│  │                  │    │                  │                  │
│  │  • Site data     │    │  /site_1_name/   │                  │
│  │  • Scores        │    │    - doc1.pdf    │                  │
│  │  • JSON columns  │    │    - study.xlsx  │                  │
│  │                  │    │  /site_2_name/   │                  │
│  └──────────────────┘    │    - vdr.pdf     │                  │
│           │              └──────────────────┘                  │
│           ▼                                                     │
│  ┌──────────────────────────────────────┐                      │
│  │     SINGLE SOURCE OF TRUTH           │                      │
│  │  - Team can edit Sheet directly      │                      │
│  │  - App syncs automatically           │                      │
│  │  - Full audit trail                  │                      │
│  └──────────────────────────────────────┘                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Your Google Sheet Structure

Based on your "Sites Tracker - App" sheet:

| Column | Field | Type | Description |
|--------|-------|------|-------------|
| A | site_id | text | Unique identifier (auto-generated) |
| B | name | text | Site display name |
| C | state | text | 2-letter state code |
| D | utility | text | Utility company name |
| E | target_mw | number | Target MW capacity |
| F | acreage | number | Site acreage |
| G | iso | text | ISO/RTO (SPP, ERCOT, etc.) |
| H | county | text | County name |
| I | developer | text | Developer/partner name |
| J | land_status | text | Land control status |
| K | community_supp | text | Community support level |
| L | political_support | text | Political support level |
| M | dev_experience | text | Developer experience level |
| N | capital_status | text | Capital availability |
| O | financial_status | text | Financial/end-user status |
| P | last_updated | datetime | Auto-updated timestamp |
| Q | phases_json | JSON | Phase details |
| R | onsite_gen_json | JSON | Onsite generation details |
| S | schedule_json | JSON | Study status, timeline |
| T | non_power_json | JSON | Water, fiber, zoning |
| U | risks_json | JSON | Identified risks |
| V | opps_json | JSON | Opportunities |
| W | questions_json | JSON | Open questions |

### Program Tracker Columns (X-AJ)

| Column | Field | Type | Description |
|--------|-------|------|-------------|
| X | client | text | Client/Partner name |
| Y | total_fee_potential | number | Total fee potential ($) |
| Z | contract_status | text | No/Verbal/MOU/Definitive |
| AA | site_control_stage | number | Stage 1-4 |
| AB | power_stage | number | Stage 1-4 |
| AC | marketing_stage | number | Stage 1-4 |
| AD | buyer_stage | number | Stage 1-4 |
| AE | zoning_stage | number | Stage 1-3 |
| AF | water_stage | number | Stage 1-4 |
| AG | incentives_stage | number | Stage 1-4 |
| AH | probability | number | Calculated probability (0-1) |
| AI | weighted_fee | number | Calculated weighted fee ($) |
| AJ | tracker_notes | text | Notes |

## Setup Steps

### 1. Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable APIs:
   - Google Sheets API
   - Google Drive API

### 2. Create Service Account

1. In Google Cloud Console → IAM & Admin → Service Accounts
2. Click "Create Service Account"
3. Name it (e.g., `portfolio-manager`)
4. Grant no roles (not needed)
5. Click "Done"
6. Click on the service account → Keys → Add Key → JSON
7. Download the JSON file

### 3. Share Google Resources

1. **Google Sheet**: Share "Sites Tracker - App" with the service account email
   - Found in JSON as `client_email`
   - Give "Editor" access

2. **Google Drive Folder**: Share "VDR Uploads" folder with same email
   - Give "Editor" access

### 4. Get Resource IDs

**Sheet ID** - from URL:
```
https://docs.google.com/spreadsheets/d/[SHEET_ID_HERE]/edit
```

**Folder ID** - from URL when viewing folder:
```
https://drive.google.com/drive/folders/[FOLDER_ID_HERE]
```

### 5. Configure Streamlit

Create `.streamlit/secrets.toml`:

```toml
GOOGLE_SHEET_ID = "1abc123def456..."  # Your Sheet ID
GOOGLE_VDR_FOLDER_ID = "1xyz789..."   # Your Folder ID

# Paste the ENTIRE contents of your JSON key file here
GOOGLE_CREDENTIALS_JSON = '''
{
  "type": "service_account",
  "project_id": "your-project",
  "private_key_id": "abc123",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "portfolio-manager@your-project.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
'''
```

### 6. Install Dependencies

```bash
pip install streamlit pandas plotly google-api-python-client google-auth PyPDF2 python-docx openpyxl
```

### 7. Run the App

```bash
streamlit run streamlit_gsheets.py
```

## File Organization

When you upload a VDR zip for a site, files are organized as:

```
VDR Uploads/
├── tulsa_metro_hub_ok/
│   ├── SIS_Report.pdf
│   ├── Site_Plan.pdf
│   └── Financial_Model.xlsx
├── dfw_industrial_tx/
│   ├── Interconnection_Study.pdf
│   └── Land_Survey.pdf
└── atlanta_metro_ga/
    └── Georgia_Power_Agreement.pdf
```

## How Data Flows

### Adding a Site via Chat:
1. User describes site in natural language
2. App extracts: state, utility, MW, study status, etc.
3. User reviews and clicks "Save"
4. App writes row to Google Sheet
5. Sheet is immediately updated (visible to team)

### Adding via VDR Upload:
1. User uploads zip file
2. App extracts text from PDFs/DOCX/XLSX
3. App parses MW figures, dates, study references
4. User reviews extracted data
5. App:
   - Creates site folder in Google Drive
   - Uploads all files to that folder
   - Writes site data row to Google Sheet

### Manual Edits:
- Team can edit Google Sheet directly
- App reads current data on each page load
- No sync conflicts

## Troubleshooting

### "Google credentials not found"
- Check `.streamlit/secrets.toml` exists
- Verify JSON is valid (no extra quotes/escaping)
- Restart Streamlit

### "Permission denied" on Sheet
- Verify service account email has Editor access
- Check Sheet ID is correct

### "Permission denied" on Drive
- Verify service account has Editor access to folder
- Check Folder ID is correct

### Files not appearing in Drive
- Check folder sharing permissions
- Verify GOOGLE_VDR_FOLDER_ID is correct

## Security Notes

- Service account credentials should NEVER be committed to git
- Add `.streamlit/secrets.toml` to `.gitignore`
- For production, use Streamlit Cloud secrets management
- Service account only has access to resources you explicitly share

## Program Tracker Probability Calculation

### Contract Status (Gatekeeper Multiplier)
| Status | Multiplier | Effect |
|--------|------------|--------|
| No | 0× | Kills all probability |
| Verbal | 0.33× | Reduces to 33% |
| MOU | 0.66× | Reduces to 66% |
| Definitive | 0.90× | Deal risk cap |

### Probability Drivers
| Driver | Weight | Stages |
|--------|--------|--------|
| Buyer Progress | 30% | 4 stages |
| Site Control | 20% | 4 stages |
| Power Confirmation | 20% | 4 stages |
| Zoning | 20% | 3 stages |
| Incentives | 10% | 4 stages |

### Stage Progression
| Stage | Progress % |
|-------|------------|
| 1 (Not Started) | 0% |
| 2 | 33.3% |
| 3 | 66.6% |
| 4 (Complete) | 100% |

*Note: Zoning has only 3 stages (Not Started=0%, In Progress=50%, Approved=100%)*

### Formula
```
Base Probability = Σ (Driver Weight × Stage Progress)
Final Probability = Base Probability × Contract Multiplier
Weighted Fee = Total Fee Potential × Final Probability
```

### Stage Definitions

**Site Control:**
1. Not Started
2. Identified
3. LOI
4. PSA/Contract

**Power:**
1. Not Started
2. Preliminary Study
3. Contract Study
4. Interconnect Agreement

**Buyer:**
1. Not Started
2. Preliminary Discussion
3. LOI
4. PSA/Contract

**Zoning:** (3 stages)
1. Not Started
2. Comp Plan/In Progress
3. Zoning Approved

**Incentives:**
1. Not Started
2. Application Filed
3. Preliminary Response
4. Final Award

**Marketing:** (informational only, not in probability)
1. Not Started
2. Flyer
3. VDR
4. Full Package

**Water:** (informational only, not in probability)
1. Not Started
2. Preliminary Capacities
3. Will-Serve Letter
4. Final Capacities
