"""
Utility Research Agent
======================
Agentic module for performing deep web research on utility companies.
Uses DuckDuckGo for search and Gemini/Claude for analysis.
"""

import time
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from duckduckgo_search import DDGS
import streamlit as st
import json
import io
import PyPDF2

# Import our modules
from .llm_integration import GeminiClient, ClaudeClient
from .state_analysis import generate_utility_research_queries

class UtilityResearchAgent:
    """
    Agent that autonomously researches utility data.
    """
    
    def __init__(self, provider: str = "gemini", api_key: str = None):
        self.provider = provider
        self.client = None
        
        # Initialize LLM client
        if provider == "gemini":
            self.client = GeminiClient(api_key)
        elif provider == "claude":
            self.client = ClaudeClient(api_key)
        else:
            raise ValueError("Invalid provider")
            
        self.ddgs = DDGS()
        
    def search_web(self, query: str, max_results: int = 3) -> List[Dict]:
        """Perform web search using DuckDuckGo."""
        try:
            results = list(self.ddgs.text(query, max_results=max_results))
            return results
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def fetch_page_content(self, url: str) -> str:
        """Fetch and parse text content from a URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove scripts and styles
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
                
            text = soup.get_text(separator=' ', strip=True)
            
            # Truncate if too long (to fit in context window)
            return text[:15000]
            
        except Exception as e:
            print(f"Fetch error for {url}: {e}")
            return ""

    def fetch_pdf_content(self, url: str) -> str:
        """Fetch and parse text content from a PDF URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            f = io.BytesIO(response.content)
            reader = PyPDF2.PdfReader(f)
            
            text = ""
            # Read first 10 pages to avoid massive processing
            for i in range(min(len(reader.pages), 10)):
                text += reader.pages[i].extract_text() + "\n"
                
            return text[:20000] # Limit context
            
        except Exception as e:
            print(f"PDF Fetch error for {url}: {e}")
            return ""

    def fetch_content(self, url: str) -> str:
        """Smart fetcher that handles HTML and PDF."""
        if url.lower().endswith('.pdf'):
            return self.fetch_pdf_content(url)
        else:
            return self.fetch_page_content(url)

    def identify_parent_company(self, utility: str) -> str:
        """Ask LLM to identify the parent company."""
        try:
            self.client.start_chat("You are an energy market expert.")
            response = self.client.send_message(f"Who is the parent company of the utility '{utility}'? Return ONLY the company name (e.g. 'American Electric Power'). If it is independent, return '{utility}'.")
            return response.strip()
        except:
            return utility

    def analyze_content(self, topic: str, content: str, utility: str, state: str) -> str:
        """Use LLM to extract specific facts from content."""
        if not content:
            return "No content available to analyze."
            
        prompt = f"""
        Analyze the following text to extract information about **{topic}** for **{utility}** in **{state}**.
        
        Focus on:
        - Specific numbers (MW, dates, costs)
        - Policy details
        - Status updates
        
        If the text contains relevant information, summarize it concisely with citations (Source Title).
        If the text does not contain relevant information, return "No relevant information found."
        
        TEXT CONTENT:
        {content[:15000]}
        """
        
        try:
            # We use a fresh chat session for each analysis to avoid context pollution
            if self.provider == "gemini":
                self.client.start_chat("You are a research assistant.")
                return self.client.send_message(prompt)
            else:
                # Claude client doesn't need explicit start_chat for single message if we structured it right,
                # but our wrapper does.
                self.client.start_chat("You are a research assistant.")
                return self.client.send_message(prompt)
        except Exception as e:
            return f"Analysis error: {e}"

    def research_topic(self, utility: str, state: str, topic: str, queries: List[str]) -> Dict:
        """Research a specific topic (e.g. 'Queue Status')."""
        print(f"Researching {topic}...")
        
        # 1. Search
        search_results = []
        for q in queries[:2]: # Limit to top 2 queries per topic to save time
            results = self.search_web(q, max_results=2)
            search_results.extend(results)
        
        # Deduplicate by URL
        unique_results = {r['href']: r for r in search_results}.values()
        
        # 2. Fetch & Analyze
        findings = []
        sources = []
        
        for res in list(unique_results)[:3]: # Limit to top 3 URLs total
            url = res['href']
            title = res['title']
            print(f"  Reading: {title}")
            
            print(f"  Reading: {title}")
            
            content = self.fetch_content(url)
            if len(content) < 500: # Skip empty/blocked pages
                continue
                
            analysis = self.analyze_content(topic, content, utility, state)
            
            if "No relevant information found" not in analysis and "Analysis error" not in analysis:
                findings.append(analysis)
                sources.append({'title': title, 'url': url})
        
        # 3. Synthesize
        if not findings:
            return {'summary': "No information found.", 'sources': []}
            
        synthesis_prompt = f"""
        Synthesize the following research findings about **{topic}** for **{utility}** in **{state}**.
        Create a concise, bulleted summary of the key facts.
        
        FINDINGS:
        {json.dumps(findings)}
        """
        
        try:
            summary = self.client.send_message(synthesis_prompt)
        except:
            summary = "\n".join(findings)
            
        return {
            'summary': summary,
            'sources': sources
        }

    def run_full_research(self, utility: str, state: str) -> Dict:
        """Run full research suite for a utility."""
        
        # 1. Identify Parent Company
        parent_co = self.identify_parent_company(utility)
        print(f"Identified parent company: {parent_co}")
        
        # Generate queries (now including parent company context)
        # We'll manually inject parent company into queries for now or update state_analysis later
        # For now, let's just append parent company to the utility name for some queries
        
        all_queries = generate_utility_research_queries(utility, state)
        
        # Add parent company queries if different
        if parent_co and parent_co.lower() != utility.lower():
            parent_queries = generate_utility_research_queries(parent_co, state)
            for topic, queries in parent_queries.items():
                if topic in all_queries:
                    all_queries[topic].extend(queries)
        
        results = {
            'utility': utility,
            'parent_company': parent_co,
            'state': state,
            'last_updated': time.strftime("%Y-%m-%d"),
            'topics': {}
        }
        
        topics_to_research = [
            'queue_and_interconnection',
            'capacity_and_generation',
            'rate_cases',
            'data_center_specific',
            'transmission_projects', # Added
            'regulatory_filings'     # Added
        ]
        
        for topic in topics_to_research:
            queries = all_queries.get(topic, [])
            # Add specific PDF hunting queries for IRPs and RFPs
            if topic == 'capacity_and_generation':
                queries.append(f"{utility} Integrated Resource Plan {time.strftime('%Y')} filetype:pdf")
                queries.append(f"{parent_co} IRP {state} filetype:pdf")
            
            topic_result = self.research_topic(utility, state, topic, queries)
            results['topics'][topic] = topic_result
            
        return results
