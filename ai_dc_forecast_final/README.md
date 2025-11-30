# AI Data Center Power Forecast Application

A Streamlit-based dashboard for forecasting AI data center power supply and demand, with site maturity scoring and valuation tools.

## Features

- **Supply/Demand Forecasting**: Track and forecast US AI data center power supply vs demand through 2035
- **Scenario Analysis**: Toggle between acceleration, plateau, and correction scenarios
- **News Signal Processing**: Process news headlines to adjust forecasts (designed for Antigravity integration)
- **Site Analyzer**: Score site maturity and estimate valuation based on development stage
- **State Rankings**: Heat map of state priority scores for powered land development

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run streamlit_app.py
```

## Files

- `streamlit_app.py` - Main Streamlit application
- `ai_dc_forecast_models.py` - Core forecasting models (DemandModel, SupplyModel, SiteScorer, etc.)
- `ai_dc_forecast_framework.md` - Comprehensive framework documentation
- `requirements.txt` - Python dependencies

## Antigravity Integration

The app is designed to integrate with Antigravity for automated news monitoring. Key integration points:

1. **News Signal Processor**: Feed news data from Antigravity queries to the `NewsSignalProcessor` class
2. **Weekly Updates**: Use Antigravity to scan for:
   - Hyperscaler capex announcements
   - Interconnection queue updates
   - Equipment delivery news
   - Data center project announcements

### Suggested Antigravity Queries

```python
# Demand signals
"hyperscaler data center capex announcements last week"
"AI infrastructure investment news"
"data center construction announcements"

# Supply signals
"interconnection queue updates PJM ERCOT SPP"
"transformer delivery delays power grid"
"nuclear plant restart announcements"
```

## Site Data Format

For batch site analysis, upload a CSV with these columns:

```csv
site_name,capacity_mw,geography,queue_status,utility_engagement,land_control,...
```

See `ai_dc_forecast_framework.md` for complete field definitions.

## Model Weights

### Demand Model
- CoWoS Capacity: 25%
- Hyperscaler Capex: 22%
- AI Revenue Growth: 18%
- GPU Shipments: 15%
- Chip TDP: 12%
- Training Mix: 8%

### Site Scoring
- Power Pathway: 40%
- Site Fundamentals: 25%
- End User Demand: 20%
- Execution Capability: 15%

### State Scoring
- Queue Efficiency: 25%
- Permitting Speed: 20%
- BTM Flexibility: 15%
- Transmission Headroom: 15%
- Resource Access: 10%
- Saturation: 10%
- Cost Structure: 5%

## License

Internal use only. Based on analysis conducted with Doug @ Black & Veatch.
