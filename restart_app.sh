#!/bin/bash

# Portfolio PDF Export - Fresh Restart Script
# This will ensure Streamlit loads the latest code

echo "🧹 Cleaning Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

echo "🔄 Starting Streamlit with fresh cache..."
echo ""
echo "After starting:"
echo "1. Go to Program Tracker → Portfolio Export tab"
echo "2. You should see a radio button: ● PDF  ○ PowerPoint"
echo "3. Select PDF"
echo "4. Select sites and click 'Generate PDF'"
echo ""

streamlit run app.py --server.port 8501 --server.headless true
