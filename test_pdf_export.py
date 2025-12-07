"""
Quick Test: Portfolio PDF Export
=================================
This is a minimal test script to verify the PDF export function works.
Run this separately to test the PDF generation.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from portfolio_manager.streamlit_app import generate_portfolio_pdf, load_database

# Load your database
print("Loading database...")
db = load_database()
sites = db.get('sites', {})

if not sites:
    print("❌ No sites found in database!")
    sys.exit(1)

print(f"✅ Found {len(sites)} sites")

# Get all site IDs
site_ids = list(sites.keys())
print(f"Site IDs: {site_ids}")

# Default weights
weights = {'state': 0.20, 'power': 0.25, 'relationship': 0.20, 'execution': 0.15, 'fundamentals': 0.10, 'financial': 0.10}

print("\n🔧 Generating PDF...")
try:
    pdf_bytes = generate_portfolio_pdf(site_ids, db, weights)
    
    # Save to file
    output_file = "test_portfolio_export.pdf"
    with open(output_file, 'wb') as f:
        f.write(pdf_bytes)
    
    print(f"✅ SUCCESS! PDF generated: {output_file}")
    print(f"   File size: {len(pdf_bytes):,} bytes")
    print(f"   Sites included: {len(site_ids)}")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
