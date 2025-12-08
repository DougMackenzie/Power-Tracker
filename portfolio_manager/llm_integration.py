"""
LLM Integration for Portfolio Manager
======================================
Supports both Google Gemini and Anthropic Claude APIs.
Provides contextual, diagnostic chat grounded in your portfolio data.

Configuration (in .streamlit/secrets.toml):
    LLM_PROVIDER = "gemini"  # or "claude"
    GEMINI_API_KEY = "your-gemini-key"
    ANTHROPIC_API_KEY = "your-anthropic-key"  # if using Claude
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

# Try importing API clients
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


# =============================================================================
# SYSTEM PROMPT - Your Full Diagnostic Framework
# =============================================================================

SYSTEM_PROMPT_TEMPLATE = '''You are an expert data center development advisor embedded in a Powered Land Portfolio Manager application. You help evaluate and advance data center site opportunities through the interconnection and development process.

## YOUR ROLE

You assist a data center development professional in:
1. Evaluating new site opportunities
2. Diagnosing where sites are in the development pipeline
3. Identifying critical path items and next steps
4. Comparing sites against portfolio benchmarks
5. Asking the right due diligence questions

## DEVELOPMENT STAGE FRAMEWORK

Sites progress through these stages:

1. **Pre-Development** - No queue position, early exploration
2. **Queue Only** - Queue position filed but no other progress  
3. **Early Real** - Land control + utility engagement + early studies
4. **Study In Progress** - SIS/FS active or complete
5. **Utility Commitment** - Committed utility service agreement
6. **Fully Entitled** - FA/IA executed + zoning + land control
7. **End-User Attached** - LOI or Term Sheet with hyperscaler/customer

## INTERCONNECTION STUDY PROGRESSION

1. **SIS (System Impact Study)** - Initial grid impact analysis
2. **FS (Facilities Study)** - Detailed engineering and cost estimates  
3. **FA (Facilities Agreement)** - Executed agreement on upgrade scope
4. **IA (Interconnection Agreement)** - Final executed interconnection rights

## SCORING FRAMEWORK (100-point scale)

You evaluate sites on these weighted dimensions:

**State Score (20%)** - Regulatory environment, power costs, transmission capacity
- Tier 1 (80+): OK, WY, TX - Optimal regulatory/cost environment
- Tier 2 (65-79): IN, OH, GA, PA - Strong with constraints
- Tier 3 (50-64): VA, NV - Moderate challenges
- Tier 4 (<50): CA - Significant barriers

**Power Pathway (25%)** - Study status, utility commitment, timeline
- IA Executed: 40 pts | FA Executed: 35 pts | FS Complete: 28 pts
- SIS Complete: 20 pts | SIS In Progress: 12 pts | Not Started: 0 pts
- Plus utility commitment and timeline factors

**Relationship Capital (25%)** - End-user status, community/political support
- Champion community support: 40 pts
- Strong political backing: 30 pts
- Developer track record: up to 30 pts

**Fundamentals (30%)** - Land control, infrastructure, capital access
- Land owned: 35 pts | Option: 28 pts | LOI: 18 pts
- Strong capital access: 35 pts
- Water/fiber/zoning readiness

## STATE PROFILES

{state_profiles}

## CURRENT PORTFOLIO

{portfolio_context}

## YOUR BEHAVIOR

When a user describes a site or asks questions:

1. **Extract key details** - State, utility, MW, study status, land control, etc.
2. **Assess stage** - Determine where the site falls in the development framework
3. **Calculate preliminary score** - Apply the scoring framework
4. **Identify gaps** - What critical information is missing?
5. **Ask diagnostic questions** - Probe for details that affect feasibility
6. **Provide context** - Reference state profiles, comparable sites, market dynamics
7. **Recommend next steps** - What should advance this site?

## DIAGNOSTIC QUESTIONS TO CONSIDER

Power Pathway:
- What's the interconnection voltage (69kV, 138kV, 230kV, 345kV)?
- Distance to substation or transmission line?
- Current study status and timeline to next milestone?
- Any upgrade cost estimates from utility?
- Queue position number and date?

Land & Site:
- Acreage and developable area?
- Land control status (owned, option, LOI, negotiating)?
- Zoning status - data center permitted?
- Water availability and rights?
- Fiber proximity?

Relationships:
- Utility relationship quality and key contacts?
- Community sentiment - any opposition?
- Political support at local/state level?
- End-user interest or commitments?

Financial:
- Development budget allocated?
- Capital partners identified?
- Expected $/MW development cost?

## RESPONSE STYLE

- Be direct and analytical, like a senior development colleague
- Reference specific data from state profiles and portfolio
- Ask focused follow-up questions (1-3 at a time, not overwhelming lists)
- Provide actionable insights, not generic advice
- When comparing sites, use concrete metrics
- Flag risks and opportunities specific to the situation
- Use your knowledge of utility processes, ISO dynamics, and market trends

## AGENT CAPABILITIES (TOOLS)

You have access to tools to interact with the application. USE THEM PROACTIVELY.

1. **Site Management**:
   - `create_new_site(name, state, target_mw)`: Create a new site entry.
   - `update_site_field(site_name, field, value)`: Update specific fields (e.g., 'target_mw', 'utility', 'zoning_status').

2. **Navigation**:
   - `navigate_to_page(page_name)`: Switch the user's view to 'Dashboard', 'Site Database', 'Critical Path', 'Research', etc.

## BEHAVIOR GUIDELINES

1. **Be Action-Oriented**: If a user says "Change the MW to 500", call `update_site_field` immediately. Don't just say you will do it.
2. **Navigation**: If a user asks to see something (e.g., "Show me the Gantt chart"), call `navigate_to_page('Critical Path')`.
3. **Confirmation**: After taking an action, confirm what you did (e.g., "I've updated the capacity to 500MW.").
4. **Data Integrity**: When creating sites, infer the State code (e.g., 'Oklahoma' -> 'OK') if possible.

## SAVING SITES

You can now use `create_new_site` directly when the user provides enough information. You don't need to ask for permission if the intent is clear.
'''



# =============================================================================
# CONTEXT BUILDERS
# =============================================================================

def build_state_profiles_context() -> str:
    """Build state profiles summary for system prompt."""
    try:
        # Try different import paths depending on context
        try:
            from portfolio_manager.state_analysis import STATE_PROFILES, get_state_profile
        except ImportError:
            from state_analysis import STATE_PROFILES, get_state_profile
        
        lines = []
        for code in ['OK', 'TX', 'WY', 'GA', 'VA', 'OH', 'IN', 'PA', 'NV', 'CA']:
            profile = get_state_profile(code)
            if profile:
                lines.append(f"- **{profile.state_name} ({code})**: Tier {profile.tier}, Score {profile.overall_score}, "
                           f"ISO: {profile.primary_iso}, Rate: ${profile.avg_industrial_rate}/kWh, "
                           f"Queue: {profile.avg_queue_time_months} months")
        
        return "\n".join(lines) if lines else "State profiles not available."
    except ImportError:
        return "State analysis module not available."


def build_portfolio_context(sites: Dict[str, Dict]) -> str:
    """Build current portfolio summary for system prompt."""
    if not sites:
        return "No sites currently in portfolio."
    
    lines = ["Current sites in portfolio:\n"]
    
    for site_id, site in sites.items():
        name = site.get('name', site_id)
        state = site.get('state', 'N/A')
        utility = site.get('utility', 'N/A')
        mw = site.get('target_mw', 0)
        study = site.get('study_status', 'unknown')
        land = site.get('land_control', 'unknown')
        
        lines.append(f"- **{name}** ({state}): {mw}MW, Utility: {utility}, "
                    f"Study: {study.replace('_', ' ')}, Land: {land}")
    
    total_mw = sum(s.get('target_mw', 0) for s in sites.values())
    lines.append(f"\nPortfolio total: {len(sites)} sites, {total_mw:,}MW pipeline")
    
    return "\n".join(lines)


def build_system_prompt(sites: Dict[str, Dict]) -> str:
    """Build complete system prompt with current context."""
    state_context = build_state_profiles_context()
    portfolio_context = build_portfolio_context(sites)
    
    return SYSTEM_PROMPT_TEMPLATE.format(
        state_profiles=state_context,
        portfolio_context=portfolio_context
    )


# =============================================================================
# LLM CLIENTS
# =============================================================================

# Import Agent Tools
try:
    from .agent_tools import AGENT_TOOLS, TOOL_FUNCTIONS
except ImportError:
    # Fallback if tools not available yet
    AGENT_TOOLS = []
    TOOL_FUNCTIONS = {}

# ... (Previous imports)

class GeminiClient:
    """Google Gemini API client."""
    
    def __init__(self, api_key: str, model: str = "models/gemini-1.5-pro-002"):
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.chat = None
    
    def start_chat(self, system_prompt: str, history: List[Dict] = None, use_tools: bool = True):
        """Start or reset chat with system context."""
        self.system_prompt = system_prompt
        
        # Convert history
        gemini_history = []
        if history:
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                # Skip tool outputs in history for now to keep it simple, or handle them if needed
                if msg["role"] in ["user", "assistant"]: 
                    gemini_history.append({"role": role, "parts": [msg["content"]]})
        
        # Configure tools
        tools = AGENT_TOOLS if use_tools else []
        
        # Create model with tools
        if tools:
            self.model = genai.GenerativeModel(self.model.model_name, tools=tools)
            
        self.chat = self.model.start_chat(history=gemini_history)
        self.first_message = True
    
    def send_message(self, message: str) -> Any:
        """
        Send message and get response. 
        Returns either text response OR a list of function calls.
        """
        if self.chat is None:
            raise ValueError("Chat not started. Call start_chat first.")
        
        # Prepend system prompt to first user message
        if self.first_message:
            full_message = f"""[SYSTEM CONTEXT]
{self.system_prompt}

[USER MESSAGE]
{message}"""
            self.first_message = False
        else:
            full_message = message
        
        response = self.chat.send_message(full_message)
        return response


class ClaudeClient:
    """Anthropic Claude API client."""
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic not installed. Run: pip install anthropic")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.system_prompt = ""
        self.messages = []
    
    def start_chat(self, system_prompt: str, history: List[Dict] = None):
        """Start or reset chat with system context."""
        self.system_prompt = system_prompt
        self.messages = history if history else []
    
    def send_message(self, message: str) -> str:
        """Send message and get response."""
        self.messages.append({"role": "user", "content": message})
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=self.system_prompt,
            messages=self.messages
        )
        
        assistant_message = response.content[0].text
        self.messages.append({"role": "assistant", "content": assistant_message})
        
        return assistant_message


# =============================================================================
# UNIFIED CHAT INTERFACE
# =============================================================================

class AgenticPortfolioChat:
    """
    Unified chat interface for portfolio diagnostics.
    Supports both Gemini and Claude backends.
    """
    
    def __init__(self, provider: str = "gemini", api_key: str = None, model: str = None):
        """
        Initialize chat with specified provider.
        
        Args:
            provider: "gemini" or "claude"
            api_key: API key for the provider
            model: Optional model override
        """
        self.provider = provider.lower()
        self.client = None
        self.messages = []  # Conversation history
        self.sites = {}  # Portfolio context
        
        # Get API key from various sources
        if api_key is None:
            if HAS_STREAMLIT:
                if self.provider == "gemini":
                    api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
                else:
                    api_key = st.secrets.get("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY"))
            else:
                if self.provider == "gemini":
                    api_key = os.getenv("GEMINI_API_KEY")
                else:
                    api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            raise ValueError(f"No API key found for {provider}. Set {'GEMINI_API_KEY' if provider == 'gemini' else 'ANTHROPIC_API_KEY'}")
        
        # Initialize appropriate client
        if self.provider == "gemini":
            self.client = GeminiClient(api_key, model or "models/gemini-2.0-flash-exp")
        elif self.provider == "claude":
            self.client = ClaudeClient(api_key, model or "claude-sonnet-4-20250514")
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'gemini' or 'claude'")
    
    def set_portfolio_context(self, sites: Dict[str, Dict]):
        """Update portfolio context for the chat."""
        self.sites = sites
        self._refresh_system_prompt()
    
    def _refresh_system_prompt(self):
        """Refresh system prompt with current portfolio context."""
        system_prompt = build_system_prompt(self.sites)
        # Enable tools for Gemini
        use_tools = (self.provider == "gemini")
        self.client.start_chat(system_prompt, self.messages, use_tools=use_tools)
    
    def chat(self, user_message: str) -> str:
        """
        Send a message and get a response, handling tool calls if needed.
        """
        if not hasattr(self.client, 'chat') or self.client.chat is None:
            self._refresh_system_prompt()
            
        # 1. Send user message
        response = self.client.send_message(user_message)
        
        # 2. Handle Function Calls (Gemini only for now)
        if self.provider == "gemini":
            return self._handle_gemini_response(response)
        else:
            # Claude text response
            text_response = response
            self.messages.append({"role": "user", "content": user_message})
            self.messages.append({"role": "assistant", "content": text_response})
            return text_response
            
    def _handle_gemini_response(self, response) -> str:
        """Process Gemini response loop for function calling."""
        
        # Loop to handle multiple function calls if needed
        max_turns = 5
        current_response = response
        
        for _ in range(max_turns):
            # Check for function calls
            tool_executed = False
            if hasattr(current_response, 'parts'):
                for part in current_response.parts:
                    if fn := part.function_call:
                        # Execute tool
                        tool_name = fn.name
                        tool_args = dict(fn.args)
                        
                        print(f"Executing tool: {tool_name} with {tool_args}")
                        
                        if tool_name in TOOL_FUNCTIONS:
                            try:
                                result = TOOL_FUNCTIONS[tool_name](**tool_args)
                            except Exception as e:
                                result = f"Error executing {tool_name}: {str(e)}"
                        else:
                            result = f"Error: Tool {tool_name} not found."
                            
                        # Send result back to model
                        from google.ai.generativelanguage import Part, FunctionResponse
                        
                        current_response = self.client.chat.send_message(
                            Part(function_response=FunctionResponse(name=tool_name, response={'result': result}))
                        )
                        
                        tool_executed = True
                        break # Break inner loop to process new response
            
            if tool_executed:
                continue # Continue outer loop to check new response
            
            # If we get here, it should be a text response
            try:
                text_response = current_response.text
                
                # Update history
                if self.messages and self.messages[-1]['role'] == 'user':
                     self.messages.append({"role": "assistant", "content": text_response})
                else:
                    self.messages.append({"role": "assistant", "content": text_response})
                    
                return text_response
            except ValueError:
                # This happens if response is not text (e.g. function call that we missed or mixed content)
                # Fallback: try to extract text from parts
                if hasattr(current_response, 'parts'):
                    texts = []
                    for part in current_response.parts:
                        if part.text:
                            texts.append(part.text)
                    if texts:
                        return "\n".join(texts)
                
                return "Error: Received response with no text content."
                
        return "Error: Maximum tool execution turns reached."
    
    def clear_history(self):
        """Clear conversation history."""
        self.messages = []
        self._refresh_system_prompt()
    
    def get_history(self) -> List[Dict]:
        """Get conversation history."""
        return self.messages.copy()
    
    def extract_site_data(self, response: str) -> Optional[Dict]:
        """
        Attempt to extract structured site data from a response.
        Returns None if no structured data found.
        """
        # Look for JSON block in response
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Look for key-value extraction markers
        # This is a fallback heuristic
        extracted = {}
        patterns = {
            'state': r'\*\*State\*\*:\s*(\w{2})',
            'utility': r'\*\*Utility\*\*:\s*([^\n,]+)',
            'target_mw': r'\*\*(?:MW|Capacity)\*\*:\s*(\d+)',
            'study_status': r'\*\*Study Status\*\*:\s*([^\n,]+)',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                extracted[field] = match.group(1).strip()
        
        return extracted if extracted else None


# =============================================================================
# STREAMLIT INTEGRATION HELPERS
# =============================================================================

def get_chat_client() -> Optional[AgenticPortfolioChat]:
    """Get or create chat client from Streamlit session state."""
    if not HAS_STREAMLIT:
        return None
    
    if 'portfolio_chat' not in st.session_state:
        try:
            # Determine provider
            provider = st.secrets.get("LLM_PROVIDER", "gemini").lower()
            
            # Create client
            st.session_state.portfolio_chat = AgenticPortfolioChat(provider=provider)
            
        except Exception as e:
            st.error(f"Failed to initialize chat: {str(e)}")
            return None
    
    return st.session_state.portfolio_chat


def refresh_chat_context(sites: Dict[str, Dict]):
    """Refresh chat context with current portfolio data."""
    if HAS_STREAMLIT and 'portfolio_chat' in st.session_state:
        st.session_state.portfolio_chat.set_portfolio_context(sites)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("LLM Integration Module")
    print("=" * 50)
    print(f"\nGemini available: {GEMINI_AVAILABLE}")
    print(f"Claude available: {ANTHROPIC_AVAILABLE}")
    print("\nTo use:")
    print("  from llm_integration import PortfolioChat")
    print("  chat = PortfolioChat(provider='gemini', api_key='your-key')")
    print("  chat.set_portfolio_context(your_sites_dict)")
    print("  response = chat.chat('Tell me about a 500MW site in Oklahoma')")
