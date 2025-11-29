import os
import datetime
import time
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
        import json
        creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
    else:
        # Fallback for local testing if secrets.toml exists and is parsed (simplified here)
        # In production/GitHub Actions, GCP_SERVICE_ACCOUNT env var is required.
        raise ValueError("GCP_SERVICE_ACCOUNT environment variable not set.")
        
    return gspread.authorize(credentials)

def perform_research():
    print("Starting Weekly Research with Gemini & Tavily...")
    
    # Configure APIs
    if "GEMINI_API_KEY" not in os.environ:
        raise ValueError("GEMINI_API_KEY not set.")
    if "TAVILY_API_KEY" not in os.environ:
        raise ValueError("TAVILY_API_KEY not set.")
        
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    topics = [
        "FERC policy announcements power grid last week",
        "Transformer equipment lead times 2025 updates",
        "Gas turbine supply chain delays 2025",
        "TSMC Arizona fab progress delays news",
        "PJM interconnection queue updates 2025",
        "Data center power connection delays US news"
    ]
    
    results = []
    
    for topic in topics:
        print(f"Researching: {topic}...")
        try:
            # 1. Search
            search_response = tavily.search(query=topic, search_depth="basic", max_results=3)
            context = "\n".join([f"- {r['content']} (Source: {r['url']})" for r in search_response['results']])
            
            # 2. Summarize with Gemini
            prompt = f"""
            Analyze the following news search results regarding "{topic}".
            Summarize the key updates in 1-2 sentences.
            Determine if this news is 'Bullish' (increasing supply/demand trajectory), 'Bearish' (decreasing), or 'Neutral'.
            
            Search Results:
            {context}
            
            Output format:
            Summary: [Your summary]
            Impact: [Bullish/Bearish/Neutral]
            """
            
            response = model.generate_content(prompt)
            text = response.text
            
            # Simple parsing (robustness could be improved)
            summary = "No summary generated."
            impact = "Neutral"
            
            for line in text.split('\n'):
                if line.startswith("Summary:"):
                    summary = line.replace("Summary:", "").strip()
                elif line.startswith("Impact:"):
                    impact = line.replace("Impact:", "").strip()
            
            # Collect sources
            sources = ", ".join([r['url'] for r in search_response['results']])
            
            results.append({
                "Date": datetime.date.today().isoformat(),
                "Topic": topic,
                "Summary": summary,
                "Impact": impact,
                "Source": sources
            })
            
            # Rate limiting
            time.sleep(2)
            
        except Exception as e:
            print(f"Error researching {topic}: {e}")
            results.append({
                "Date": datetime.date.today().isoformat(),
                "Topic": topic,
                "Summary": f"Error: {str(e)}",
                "Impact": "Error",
                "Source": "N/A"
            })
        
    return results

def update_sheet(results):
    client = get_gspread_client()
    # Open spreadsheet by name
    # Note: Ensure the Service Account has 'Editor' access to this specific sheet
    try:
        sh = client.open("LiveProjection") # User mentioned 'LiveProjection' sheet earlier, or 'Power Tracker'
    except gspread.SpreadsheetNotFound:
        try:
            sh = client.open("Power Tracker")
        except:
            print("Error: Could not find spreadsheet 'LiveProjection' or 'Power Tracker'.")
            return

    try:
        worksheet = sh.worksheet("WeeklyResearch")
    except:
        worksheet = sh.add_worksheet(title="WeeklyResearch", rows=100, cols=10)
        worksheet.append_row(["Date", "Topic", "Summary", "Impact", "Source"])
        
    for row in results:
        worksheet.append_row([
            row["Date"],
            row["Topic"],
            row["Summary"],
            row["Impact"],
            row["Source"]
        ])
    
    print("Sheet updated successfully.")

if __name__ == "__main__":
    results = perform_research()
    update_sheet(results)
