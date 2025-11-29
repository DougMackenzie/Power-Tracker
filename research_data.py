# Data extracted from "Power Research Framework.pdf"

# Appendix D: Year-by-Year Demand Projections (Base Case Midpoints)
# Global GW = [Chips(M) * TDP(W) * Util * 1.45 * PUE] / 1e9
# US Share ~70-85% depending on year
# Updated targets to match Page 27 "Recalibrated" chart
BASE_CASE_DATA = [
    {"Year": 2024, "Chips_M": 23.5, "TDP": 680, "Util": 0.65, "PUE": 1.30, "US_Share": 0.85, "US_GW_Base": 12.0},
    {"Year": 2025, "Chips_M": 43.5, "TDP": 720, "Util": 0.68, "PUE": 1.28, "US_Share": 0.84, "US_GW_Base": 22.0},
    {"Year": 2026, "Chips_M": 69.0, "TDP": 780, "Util": 0.70, "PUE": 1.25, "US_Share": 0.82, "US_GW_Base": 39.0},
    {"Year": 2027, "Chips_M": 98.5, "TDP": 850, "Util": 0.72, "PUE": 1.22, "US_Share": 0.80, "US_GW_Base": 57.0},
    {"Year": 2028, "Chips_M": 127.5, "TDP": 920, "Util": 0.73, "PUE": 1.20, "US_Share": 0.78, "US_GW_Base": 75.0},
    {"Year": 2030, "Chips_M": 205.0, "TDP": 1050, "Util": 0.75, "PUE": 1.16, "US_Share": 0.75, "US_GW_Base": 115.0}, # Page 27
    {"Year": 2032, "Chips_M": 285.0, "TDP": 1150, "Util": 0.76, "PUE": 1.14, "US_Share": 0.73, "US_GW_Base": 160.0},
    {"Year": 2035, "Chips_M": 450.0, "TDP": 1300, "Util": 0.78, "PUE": 1.12, "US_Share": 0.72, "US_GW_Base": 230.0}, # Page 27
]

# Supply Scenarios
# Conservative: Matches PDF "Low Trend" (Page 27)
# Base: ~50% improvement over Conservative
# Aggressive: ~100% improvement (closing the gap)
SUPPLY_SCENARIOS = {
    "Conservative": [
        {"Year": 2024, "Supply_GW": 35.0},
        {"Year": 2025, "Supply_GW": 36.5},
        {"Year": 2026, "Supply_GW": 38.0},
        {"Year": 2027, "Supply_GW": 40.0},
        {"Year": 2028, "Supply_GW": 42.5},
        {"Year": 2030, "Supply_GW": 50.0},
        {"Year": 2032, "Supply_GW": 80.0},
        {"Year": 2035, "Supply_GW": 140.0},
    ],
    "Base": [
        {"Year": 2024, "Supply_GW": 35.0},
        {"Year": 2025, "Supply_GW": 38.0},
        {"Year": 2026, "Supply_GW": 42.0},
        {"Year": 2027, "Supply_GW": 48.0},
        {"Year": 2028, "Supply_GW": 55.0},
        {"Year": 2030, "Supply_GW": 75.0},
        {"Year": 2032, "Supply_GW": 110.0},
        {"Year": 2035, "Supply_GW": 180.0},
    ],
    "Aggressive": [
        {"Year": 2024, "Supply_GW": 35.0},
        {"Year": 2025, "Supply_GW": 40.0},
        {"Year": 2026, "Supply_GW": 46.0},
        {"Year": 2027, "Supply_GW": 55.0},
        {"Year": 2028, "Supply_GW": 68.0},
        {"Year": 2030, "Supply_GW": 100.0},
        {"Year": 2032, "Supply_GW": 150.0},
        {"Year": 2035, "Supply_GW": 230.0},
    ]
}

# Appendix E: Scenario Parameters (2030)
SCENARIOS = {
    "Conservative": {
        "Chips_M_Multiplier": 0.8, # Approx from 160-250 range vs 205 base
        "TDP_Multiplier": 1.0,
        "PUE_Target": 1.40,
        "Util_Target": 0.60
    },
    "Base": {
        "Chips_M_Multiplier": 1.0,
        "TDP_Multiplier": 1.0,
        "PUE_Target": 1.25, # Note: PDF says 1.16 for 2030 base in App D, but 1.25 in App E. Using App E for scenario logic.
        "Util_Target": 0.72
    },
    "Aggressive": {
        "Chips_M_Multiplier": 1.2,
        "TDP_Multiplier": 1.1, # Assuming higher TDP for aggressive perf
        "PUE_Target": 1.12,
        "Util_Target": 0.80
    }
}

# Appendix G: U.S. Stack by Chip Designer (2030)
# Used for breakdown visualization
COMPANY_SPLIT_2030 = {
    "NVIDIA": 0.615, # Midpoint of 58-65%
    "AMD": 0.135,
    "Google TPU": 0.09,
    "AWS Trainium": 0.07,
    "Intel": 0.05,
    "Broadcom/Marvell": 0.045,
    "Microsoft Maia": 0.045,
    "Meta/Others": 0.03
}
