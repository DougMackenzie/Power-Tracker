import os
import datetime
import time
import json
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from tavily import TavilyClient

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

def perform_quantitative_research():
    print("Starting Quantitative Research with Gemini & Tavily...")
    
    # Configure APIs
    if "GEMINI_API_KEY" not in os.environ:
        raise ValueError("GEMINI_API_KEY not set.")
    if "TAVILY_API_KEY" not in os.environ:
        raise ValueError("TAVILY_API_KEY not set.")
        
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    
    # Use user-specified model
    model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
    
    # Define Indicators
    indicators = {
        "Supply": [
            "US interconnection queue backlog GW 2024 2025",
            "High voltage transformer lead times 2025",
            "Gas turbine delivery lead times GE Siemens 2025",
            "FERC grid connection policy updates 2025 impact"
        ],
        "Demand": [
            "US data center vacancy rates Northern Virginia 2025",
            "NVIDIA GPU shipment backlog wait times 2025",
            "US utility load growth forecast revisions 2025"
        ]
    }
    
    research_data = []
    
    # 1. Gather Data via Tavily
    for category, queries in indicators.items():
        for query in queries:
            print(f"Searching: {query}...")
            try:
                response = tavily.search(query=query, search_depth="advanced", max_results=3)
                context = "\n".join([f"- {r['content']} (Source: {r['url']})" for r in response['results']])
                research_data.append(f"Category: {category}\nTopic: {query}\nData:\n{context}\n")
                time.sleep(1) # Rate limit
            except Exception as e:
                print(f"Error searching {query}: {e}")

    full_context = "\n".join(research_data)
    
    # 2. Analyze with Gemini (The "Quant")
    print("Analyzing data to determine scenario probabilities...")
    
    prompt = f"""
    You are a Quantitative Energy Analyst. Your goal is to determine the probability of "Low", "Mid", and "High" scenarios for US Power Supply and Demand based on the latest market data.

    **Scenario Definitions:**
    *   **Supply Low**: Supply chain crunches (transformers >100 weeks), massive queue delays, strict regulations.
    *   **Supply Mid**: Moderate delays, steady improvements in interconnection.
    *   **Supply High**: Rapid policy unlocking (FERC reform works), supply chain easing, fast gas buildout.
    
    *   **Demand Low**: AI bubble bursts, vacancy rates rise, efficiency gains offset growth.
    *   **Demand Mid**: Steady data center growth, consistent utility revisions.
    *   **Demand High**: AI acceleration, massive GPU deployments, utilities doubling forecasts.

    **Latest Research Data:**
    {full_context}

    **Task:**
    1.  Analyze the data points above.
    2.  Assign a probability (0-100%) to each scenario (Low/Mid/High) for BOTH Supply and Demand. The sum for each category must equal 100%.
    3.  Provide a brief "Market Sentiment" summary explaining *why* you assigned these weights.

    **Output Format (JSON):**
    {{
        "supply_probs": {{ "low": <int>, "mid": <int>, "high": <int> }},
        "demand_probs": {{ "low": <int>, "mid": <int>, "high": <int> }},
        "sentiment_summary": "<string>"
    }}
    """
    
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        result = json.loads(response.text)
        print("Analysis complete.")
        return result
    except Exception as e:
        print(f"Error in Gemini analysis: {e}")
        # Fallback to neutral if analysis fails
        return {
            "supply_probs": {"low": 33, "mid": 34, "high": 33},
            "demand_probs": {"low": 33, "mid": 34, "high": 33},
            "sentiment_summary": "Error in analysis, defaulting to neutral weights."
        }

def update_sheet(data):
    client = get_gspread_client()
    try:
        sh = client.open("LiveProjection")
    except gspread.SpreadsheetNotFound:
        try:
            sh = client.open("Power Tracker")
        except:
            print("Error: Could not find spreadsheet.")
            return

    # Update ScenarioWeights Tab
    try:
        worksheet = sh.worksheet("ScenarioWeights")
    except:
        worksheet = sh.add_worksheet(title="ScenarioWeights", rows=100, cols=10)
        worksheet.append_row(["Date", "Supply_Low", "Supply_Mid", "Supply_High", "Demand_Low", "Demand_Mid", "Demand_High", "Sentiment"])
        
    today = datetime.date.today().isoformat()
    
    row = [
        today,
        data["supply_probs"]["low"],
        data["supply_probs"]["mid"],
        data["supply_probs"]["high"],
        data["demand_probs"]["low"],
        data["demand_probs"]["mid"],
        data["demand_probs"]["high"],
        data["sentiment_summary"]
    ]
    
    worksheet.append_row(row)
    print("Sheet updated successfully.")

if __name__ == "__main__":
    data = perform_quantitative_research()
    update_sheet(data)
