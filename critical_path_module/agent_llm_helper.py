"""
LLM helper for AI agents.
Simple wrapper around the existing LLM integration.
"""

import streamlit as st


def get_llm_response(prompt: str) -> str:
    """
    Get a response from the LLM for AI agent use.
    
    Args:
        prompt: The prompt to send to the LLM
        
    Returns:
        The LLM's response text
    """
    try:
        # Use Gemini directly
        import google.generativeai as genai
        
        # Get API key from secrets
        api_key = st.secrets.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in secrets")
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Generate response
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        print(f"LLM error: {e}")
        return "{\"updates\": []}"  # Return empty response for agents
