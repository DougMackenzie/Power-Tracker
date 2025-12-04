"""
PACES GIS Image Analysis
=========================
Uses vision AI (Gemini or Claude) to extract structured site data 
from PACES screenshots and exports.

Extracts:
- Parcel information (acreage, dimensions)
- Transmission proximity (distance, voltage, line name)
- Environmental constraints (wetlands, floodplain, protected areas)
- Adjacent land use and neighborhood context
- Infrastructure (roads, rail, water access)
"""

import json
import base64
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

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
# DATA STRUCTURES
# =============================================================================

@dataclass
class TransmissionInfo:
    """Transmission line information extracted from PACES."""
    voltage_kv: Optional[int] = None
    distance_miles: Optional[float] = None
    line_name: Optional[str] = None
    substation_name: Optional[str] = None
    substation_distance_miles: Optional[float] = None
    owner_utility: Optional[str] = None
    notes: str = ""


@dataclass
class EnvironmentalInfo:
    """Environmental constraints from PACES."""
    wetlands_present: bool = False
    wetlands_percentage: Optional[float] = None
    wetlands_type: Optional[str] = None  # e.g., "forested", "emergent"
    
    floodplain_100yr: bool = False
    floodplain_500yr: bool = False
    floodplain_percentage: Optional[float] = None
    
    protected_lands: bool = False
    protected_type: Optional[str] = None
    
    slope_issues: bool = False
    slope_notes: Optional[str] = None
    
    notes: str = ""


@dataclass  
class ParcelInfo:
    """Parcel information from PACES."""
    acreage: Optional[float] = None
    developable_acreage: Optional[float] = None
    dimensions: Optional[str] = None  # e.g., "2500ft x 3000ft"
    parcel_id: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    zoning: Optional[str] = None
    current_use: Optional[str] = None
    notes: str = ""


@dataclass
class InfrastructureInfo:
    """Infrastructure access from PACES."""
    road_access: bool = False
    road_type: Optional[str] = None  # "highway", "county road", etc.
    road_name: Optional[str] = None
    
    rail_access: bool = False
    rail_distance_miles: Optional[float] = None
    
    water_body_nearby: bool = False
    water_body_name: Optional[str] = None
    water_distance_miles: Optional[float] = None
    
    fiber_visible: bool = False
    fiber_notes: Optional[str] = None
    
    notes: str = ""


@dataclass
class AdjacentLandUse:
    """Adjacent land use and neighborhood context."""
    north: Optional[str] = None
    south: Optional[str] = None  
    east: Optional[str] = None
    west: Optional[str] = None
    
    residential_nearby: bool = False
    residential_distance_miles: Optional[float] = None
    
    industrial_nearby: bool = False
    commercial_nearby: bool = False
    agricultural_nearby: bool = False
    
    sensitive_receptors: List[str] = field(default_factory=list)  # schools, hospitals, etc.
    
    notes: str = ""


@dataclass
class PACESAnalysisResult:
    """Complete PACES image analysis result."""
    parcel: ParcelInfo = field(default_factory=ParcelInfo)
    transmission: TransmissionInfo = field(default_factory=TransmissionInfo)
    environmental: EnvironmentalInfo = field(default_factory=EnvironmentalInfo)
    infrastructure: InfrastructureInfo = field(default_factory=InfrastructureInfo)
    adjacent_land_use: AdjacentLandUse = field(default_factory=AdjacentLandUse)
    
    overall_suitability: Optional[str] = None  # "high", "medium", "low"
    key_constraints: List[str] = field(default_factory=list)
    key_advantages: List[str] = field(default_factory=list)
    recommended_next_steps: List[str] = field(default_factory=list)
    
    confidence_score: float = 0.0  # 0-1 confidence in extraction
    raw_analysis: str = ""  # Full AI response for reference
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_site_data(self) -> Dict:
        """Convert to site database format."""
        return {
            'acreage': self.parcel.acreage,
            'county': self.parcel.county,
            'state': self.parcel.state,
            'transmission_voltage': self.transmission.voltage_kv,
            'transmission_distance': self.transmission.distance_miles,
            'substation_name': self.transmission.substation_name,
            'substation_distance': self.transmission.substation_distance_miles,
            'wetlands_present': self.environmental.wetlands_present,
            'wetlands_percentage': self.environmental.wetlands_percentage,
            'floodplain_100yr': self.environmental.floodplain_100yr,
            'road_access': self.infrastructure.road_access,
            'residential_nearby': self.adjacent_land_use.residential_nearby,
            'paces_suitability': self.overall_suitability,
            'paces_constraints': self.key_constraints,
            'paces_advantages': self.key_advantages,
        }


# =============================================================================
# ANALYSIS PROMPT
# =============================================================================

PACES_ANALYSIS_PROMPT = '''Analyze this PACES GIS map image for data center site suitability. Extract all visible information into structured data.

## EXTRACTION REQUIREMENTS

### 1. PARCEL INFORMATION
- Total acreage (look for labels, scale bar calculations)
- Parcel boundaries and shape
- Parcel ID if visible
- County and state
- Current zoning designation
- Current land use

### 2. TRANSMISSION INFRASTRUCTURE
- Nearest transmission line voltage (69kV, 115kV, 138kV, 161kV, 230kV, 345kV, 500kV)
- Distance from parcel to transmission line (miles)
- Transmission line name/identifier if visible
- Nearest substation name and distance
- Utility owner if indicated

### 3. ENVIRONMENTAL CONSTRAINTS
- Wetlands: presence, approximate % of parcel, type (forested, emergent, etc.)
- Floodplain: 100-year and/or 500-year zones, % of parcel affected
- Protected lands, conservation easements
- Significant slope or terrain issues
- Any other environmental features (streams, ponds, etc.)

### 4. INFRASTRUCTURE ACCESS
- Road access: type (highway, county road), name
- Rail proximity and distance
- Water bodies and distance
- Visible fiber/telecom infrastructure

### 5. ADJACENT LAND USE
- Land use in each cardinal direction (N, S, E, W)
- Distance to nearest residential development
- Presence of industrial, commercial, agricultural uses
- Sensitive receptors (schools, hospitals, churches) within visible range

### 6. OVERALL ASSESSMENT
- Suitability rating: HIGH, MEDIUM, or LOW
- Top 3-5 constraints (issues that could impede development)
- Top 3-5 advantages (factors favoring development)
- Recommended next steps for due diligence

## RESPONSE FORMAT

Respond with a JSON object matching this structure:
```json
{
  "parcel": {
    "acreage": <number or null>,
    "developable_acreage": <number or null>,
    "dimensions": "<string or null>",
    "parcel_id": "<string or null>",
    "county": "<string or null>",
    "state": "<string or null>",
    "zoning": "<string or null>",
    "current_use": "<string or null>",
    "notes": "<any additional observations>"
  },
  "transmission": {
    "voltage_kv": <number or null>,
    "distance_miles": <number or null>,
    "line_name": "<string or null>",
    "substation_name": "<string or null>",
    "substation_distance_miles": <number or null>,
    "owner_utility": "<string or null>",
    "notes": "<any additional observations>"
  },
  "environmental": {
    "wetlands_present": <boolean>,
    "wetlands_percentage": <number or null>,
    "wetlands_type": "<string or null>",
    "floodplain_100yr": <boolean>,
    "floodplain_500yr": <boolean>,
    "floodplain_percentage": <number or null>,
    "protected_lands": <boolean>,
    "protected_type": "<string or null>",
    "slope_issues": <boolean>,
    "slope_notes": "<string or null>",
    "notes": "<any additional observations>"
  },
  "infrastructure": {
    "road_access": <boolean>,
    "road_type": "<string or null>",
    "road_name": "<string or null>",
    "rail_access": <boolean>,
    "rail_distance_miles": <number or null>,
    "water_body_nearby": <boolean>,
    "water_body_name": "<string or null>",
    "water_distance_miles": <number or null>,
    "fiber_visible": <boolean>,
    "fiber_notes": "<string or null>",
    "notes": "<any additional observations>"
  },
  "adjacent_land_use": {
    "north": "<description>",
    "south": "<description>",
    "east": "<description>",
    "west": "<description>",
    "residential_nearby": <boolean>,
    "residential_distance_miles": <number or null>,
    "industrial_nearby": <boolean>,
    "commercial_nearby": <boolean>,
    "agricultural_nearby": <boolean>,
    "sensitive_receptors": ["<list of schools, hospitals, etc. if visible>"],
    "notes": "<any additional observations>"
  },
  "overall_suitability": "HIGH|MEDIUM|LOW",
  "key_constraints": ["<constraint 1>", "<constraint 2>", ...],
  "key_advantages": ["<advantage 1>", "<advantage 2>", ...],
  "recommended_next_steps": ["<step 1>", "<step 2>", ...],
  "confidence_score": <0.0-1.0 based on image clarity and visible data>
}
```

Be precise with distances and measurements. If you cannot determine a value from the image, use null. Include relevant observations in the notes fields.'''


# =============================================================================
# IMAGE ANALYSIS FUNCTIONS
# =============================================================================

def encode_image_to_base64(image_path: str) -> str:
    """Encode an image file to base64."""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def encode_image_bytes_to_base64(image_bytes: bytes) -> str:
    """Encode image bytes to base64."""
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def get_image_mime_type(filename: str) -> str:
    """Determine MIME type from filename."""
    ext = filename.lower().split('.')[-1]
    mime_types = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'pdf': 'application/pdf',
    }
    return mime_types.get(ext, 'image/png')


def analyze_paces_image_gemini(
    image_data: bytes,
    filename: str,
    api_key: str,
    model: str = "gemini-1.5-flash"
) -> PACESAnalysisResult:
    """
    Analyze PACES image using Google Gemini Vision.
    
    Args:
        image_data: Raw image bytes
        filename: Original filename for MIME type detection
        api_key: Gemini API key
        model: Gemini model to use
        
    Returns:
        PACESAnalysisResult with extracted data
    """
    if not GEMINI_AVAILABLE:
        raise ImportError("google-generativeai not installed")
    
    genai.configure(api_key=api_key)
    model_client = genai.GenerativeModel(model)
    
    # Prepare image
    mime_type = get_image_mime_type(filename)
    image_part = {
        "mime_type": mime_type,
        "data": image_data
    }
    
    # Send to Gemini
    response = model_client.generate_content([PACES_ANALYSIS_PROMPT, image_part])
    response_text = response.text
    
    return parse_analysis_response(response_text)


def analyze_paces_image_claude(
    image_data: bytes,
    filename: str,
    api_key: str,
    model: str = "claude-sonnet-4-20250514"
) -> PACESAnalysisResult:
    """
    Analyze PACES image using Anthropic Claude Vision.
    
    Args:
        image_data: Raw image bytes
        filename: Original filename for MIME type detection
        api_key: Anthropic API key
        model: Claude model to use
        
    Returns:
        PACESAnalysisResult with extracted data
    """
    if not ANTHROPIC_AVAILABLE:
        raise ImportError("anthropic not installed")
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Prepare image
    mime_type = get_image_mime_type(filename)
    base64_image = encode_image_bytes_to_base64(image_data)
    
    # Send to Claude
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": base64_image,
                        }
                    },
                    {
                        "type": "text",
                        "text": PACES_ANALYSIS_PROMPT
                    }
                ]
            }
        ]
    )
    
    response_text = response.content[0].text
    return parse_analysis_response(response_text)


def parse_analysis_response(response_text: str) -> PACESAnalysisResult:
    """Parse the AI response into structured PACESAnalysisResult."""
    import re
    
    # Try to extract JSON from response
    json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find raw JSON
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            json_str = json_match.group(0)
        else:
            # Return empty result with raw response
            result = PACESAnalysisResult()
            result.raw_analysis = response_text
            return result
    
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        result = PACESAnalysisResult()
        result.raw_analysis = response_text
        return result
    
    # Build result from parsed data
    result = PACESAnalysisResult()
    result.raw_analysis = response_text
    
    # Parcel
    if 'parcel' in data:
        p = data['parcel']
        result.parcel = ParcelInfo(
            acreage=p.get('acreage'),
            developable_acreage=p.get('developable_acreage'),
            dimensions=p.get('dimensions'),
            parcel_id=p.get('parcel_id'),
            county=p.get('county'),
            state=p.get('state'),
            zoning=p.get('zoning'),
            current_use=p.get('current_use'),
            notes=p.get('notes', '')
        )
    
    # Transmission
    if 'transmission' in data:
        t = data['transmission']
        result.transmission = TransmissionInfo(
            voltage_kv=t.get('voltage_kv'),
            distance_miles=t.get('distance_miles'),
            line_name=t.get('line_name'),
            substation_name=t.get('substation_name'),
            substation_distance_miles=t.get('substation_distance_miles'),
            owner_utility=t.get('owner_utility'),
            notes=t.get('notes', '')
        )
    
    # Environmental
    if 'environmental' in data:
        e = data['environmental']
        result.environmental = EnvironmentalInfo(
            wetlands_present=e.get('wetlands_present', False),
            wetlands_percentage=e.get('wetlands_percentage'),
            wetlands_type=e.get('wetlands_type'),
            floodplain_100yr=e.get('floodplain_100yr', False),
            floodplain_500yr=e.get('floodplain_500yr', False),
            floodplain_percentage=e.get('floodplain_percentage'),
            protected_lands=e.get('protected_lands', False),
            protected_type=e.get('protected_type'),
            slope_issues=e.get('slope_issues', False),
            slope_notes=e.get('slope_notes'),
            notes=e.get('notes', '')
        )
    
    # Infrastructure
    if 'infrastructure' in data:
        i = data['infrastructure']
        result.infrastructure = InfrastructureInfo(
            road_access=i.get('road_access', False),
            road_type=i.get('road_type'),
            road_name=i.get('road_name'),
            rail_access=i.get('rail_access', False),
            rail_distance_miles=i.get('rail_distance_miles'),
            water_body_nearby=i.get('water_body_nearby', False),
            water_body_name=i.get('water_body_name'),
            water_distance_miles=i.get('water_distance_miles'),
            fiber_visible=i.get('fiber_visible', False),
            fiber_notes=i.get('fiber_notes'),
            notes=i.get('notes', '')
        )
    
    # Adjacent land use
    if 'adjacent_land_use' in data:
        a = data['adjacent_land_use']
        result.adjacent_land_use = AdjacentLandUse(
            north=a.get('north'),
            south=a.get('south'),
            east=a.get('east'),
            west=a.get('west'),
            residential_nearby=a.get('residential_nearby', False),
            residential_distance_miles=a.get('residential_distance_miles'),
            industrial_nearby=a.get('industrial_nearby', False),
            commercial_nearby=a.get('commercial_nearby', False),
            agricultural_nearby=a.get('agricultural_nearby', False),
            sensitive_receptors=a.get('sensitive_receptors', []),
            notes=a.get('notes', '')
        )
    
    # Overall assessment
    result.overall_suitability = data.get('overall_suitability')
    result.key_constraints = data.get('key_constraints', [])
    result.key_advantages = data.get('key_advantages', [])
    result.recommended_next_steps = data.get('recommended_next_steps', [])
    result.confidence_score = data.get('confidence_score', 0.5)
    
    return result


def analyze_paces_image(
    image_data: bytes,
    filename: str,
    provider: str = "gemini",
    api_key: str = None
) -> PACESAnalysisResult:
    """
    Analyze PACES image using specified provider.
    
    Args:
        image_data: Raw image bytes
        filename: Original filename
        provider: "gemini" or "claude"
        api_key: API key (will check env/secrets if not provided)
        
    Returns:
        PACESAnalysisResult with extracted data
    """
    # Get API key
    if api_key is None:
        if HAS_STREAMLIT:
            if provider == "gemini":
                api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
            else:
                api_key = st.secrets.get("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY"))
        else:
            if provider == "gemini":
                api_key = os.getenv("GEMINI_API_KEY")
            else:
                api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        raise ValueError(f"No API key found for {provider}")
    
    if provider == "gemini":
        return analyze_paces_image_gemini(image_data, filename, api_key)
    elif provider == "claude":
        return analyze_paces_image_claude(image_data, filename, api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}")


# =============================================================================
# MULTI-IMAGE ANALYSIS (for multiple PACES exports of same site)
# =============================================================================

def analyze_multiple_paces_images(
    images: List[tuple],  # List of (image_data, filename) tuples
    provider: str = "gemini",
    api_key: str = None
) -> PACESAnalysisResult:
    """
    Analyze multiple PACES images and consolidate results.
    Useful when you have separate exports for different layers.
    
    Args:
        images: List of (image_data, filename) tuples
        provider: "gemini" or "claude"
        api_key: API key
        
    Returns:
        Consolidated PACESAnalysisResult
    """
    results = []
    
    for image_data, filename in images:
        try:
            result = analyze_paces_image(image_data, filename, provider, api_key)
            results.append(result)
        except Exception as e:
            print(f"Error analyzing {filename}: {e}")
    
    if not results:
        return PACESAnalysisResult()
    
    if len(results) == 1:
        return results[0]
    
    # Consolidate multiple results
    # Take non-null values, prefer higher confidence
    consolidated = PACESAnalysisResult()
    
    # Sort by confidence
    results.sort(key=lambda r: r.confidence_score, reverse=True)
    
    # Merge parcel info
    for r in results:
        if r.parcel.acreage and not consolidated.parcel.acreage:
            consolidated.parcel.acreage = r.parcel.acreage
        if r.parcel.county and not consolidated.parcel.county:
            consolidated.parcel.county = r.parcel.county
        if r.parcel.state and not consolidated.parcel.state:
            consolidated.parcel.state = r.parcel.state
        # ... continue for other fields
    
    # Merge transmission info (take first non-null)
    for r in results:
        if r.transmission.voltage_kv and not consolidated.transmission.voltage_kv:
            consolidated.transmission = r.transmission
            break
    
    # Merge environmental (union of constraints)
    for r in results:
        if r.environmental.wetlands_present:
            consolidated.environmental.wetlands_present = True
            if r.environmental.wetlands_percentage:
                consolidated.environmental.wetlands_percentage = r.environmental.wetlands_percentage
        if r.environmental.floodplain_100yr:
            consolidated.environmental.floodplain_100yr = True
        if r.environmental.floodplain_500yr:
            consolidated.environmental.floodplain_500yr = True
    
    # Take highest suitability assessment from most confident result
    consolidated.overall_suitability = results[0].overall_suitability
    
    # Union of constraints and advantages
    all_constraints = set()
    all_advantages = set()
    for r in results:
        all_constraints.update(r.key_constraints)
        all_advantages.update(r.key_advantages)
    consolidated.key_constraints = list(all_constraints)
    consolidated.key_advantages = list(all_advantages)
    
    # Average confidence
    consolidated.confidence_score = sum(r.confidence_score for r in results) / len(results)
    
    return consolidated


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("PACES GIS Analysis Module")
    print("=" * 50)
    print(f"\nGemini available: {GEMINI_AVAILABLE}")
    print(f"Claude available: {ANTHROPIC_AVAILABLE}")
    print("\nUsage:")
    print("  from paces_analysis import analyze_paces_image")
    print("  result = analyze_paces_image(image_bytes, 'map.png', provider='gemini')")
    print("  print(result.transmission.distance_miles)")
    print("  print(result.environmental.wetlands_present)")
