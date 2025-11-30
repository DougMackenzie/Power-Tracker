import os
import datetime
import time
import json
import sys
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from tavily import TavilyClient

# Add root directory to path to import forecast_tracker
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from forecast_tracker import ForecastTracker, COWOS_BASELINE, HYPERSCALER_CAPEX_BASELINE, QUEUE_BASELINE
except ImportError:
    # Fallback if running from root
    from forecast_tracker import ForecastTracker, COWOS_BASELINE, HYPERSCALER_CAPEX_BASELINE, QUEUE_BASELINE

# Configuration
# Secrets must be set in GitHub Actions environment
# GEMINI_API_KEY
# TAVILY_API_KEY
# GCP_SERVICE_ACCOUNT (JSON string)

def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    if "GCP_SERVICE_ACCOUNT" in os.environ:
        creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
    else:
        raise ValueError("GCP_SERVICE_ACCOUNT environment variable not set.")
        
    return gspread.authorize(credentials)

def perform_targeted_research():
    print("Starting Targeted Signal Research...")
    
    if "GEMINI_API_KEY" not in os.environ or "TAVILY_API_KEY" not in os.environ:
        raise ValueError("Missing API Keys")
        
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
    
    # Define Targets based on ForecastTracker inputs
    targets = [
        {
            "type": "cowos_capacity",
            "query": "TSMC CoWoS monthly capacity 2025 2026 forecast",
            "prompt": f"Extract the latest TSMC CoWoS monthly capacity (wafers per month) forecast for 2025 or 2026. Baseline is {COWOS_BASELINE[2025]} for 2025. Return JSON: {{'year': int, 'capacity': int, 'source': str}} or null if no clear number."
        },
        {
            "type": "hyperscaler_capex",
            "query": "Microsoft Google Amazon Meta quarterly capex 2025",
            "prompt": f"Extract the latest combined quarterly capex for Hyperscalers (MSFT+GOOG+AMZN+META). Baseline is ${HYPERSCALER_CAPEX_BASELINE}B. Return JSON: {{'quarterly_capex_bn': float, 'source': str}} or null."
        },
        {
            "type": "queue_update",
            "query": "PJM interconnection queue active GW 2025",
            "prompt": f"Extract the current active GW in the PJM interconnection queue. Baseline is {QUEUE_BASELINE['pjm']['queue_gw']} GW. Return JSON: {{'iso': 'PJM', 'active_gw': float, 'source': str}} or null."
        }
    ]
    
    found_signals = []
    
    for target in targets:
        print(f"Searching for {target['type']}...")
        try:
            # 1. Search
            search_results = tavily.search(query=target['query'], search_depth="advanced", max_results=3)
            context = "\n".join([f"- {r['content']} ({r['url']})" for r in search_results['results']])
            
            # 2. Extract
            full_prompt = f"""
            {target['prompt']}
            
            Search Results:
            {context}
            """
            
            response = model.generate_content(full_prompt, generation_config={"response_mime_type": "application/json"})
            data = json.loads(response.text)
            
            if data:
                print(f"Found data: {data}")
                found_signals.append({
                    "date": datetime.date.today().isoformat(),
                    "type": target['type'],
                    "data": json.dumps(data), # Store as JSON string in sheet
                    "source": data.get('source', 'Tavily Search')
                })
            else:
                print("No clear data extracted.")
                
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing {target['type']}: {e}")
            
    return found_signals

def update_sheet(signals):
    if not signals:
        print("No signals to save.")
        return

    client = get_gspread_client()
    try:
        sh = client.open("LiveProjection")
    except:
        try:
            sh = client.open("Power Tracker")
        except:
            print("Error: Could not find spreadsheet.")
            return

    # Update WeeklyResearch Tab (Now acts as Signal Log)
    try:
        worksheet = sh.worksheet("WeeklyResearch")
    except:
        worksheet = sh.add_worksheet(title="WeeklyResearch", rows=100, cols=10)
        worksheet.append_row(["Date", "Type", "Data_JSON", "Source"])
        
    for s in signals:
        worksheet.append_row([
            s["date"],
            s["type"],
            s["data"],
            s["source"]
        ])
    
    print(f"Saved {len(signals)} signals to sheet.")

if __name__ == "__main__":
    signals = perform_targeted_research()
    update_sheet(signals)
