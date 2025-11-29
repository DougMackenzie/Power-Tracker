# Data extracted from "Power Research Framework.pdf"

# Appendix D: Year-by-Year Demand Projections (Base Case Midpoints)
# Global GW = [Chips(M) * TDP(W) * Util * 1.45 * PUE] / 1e9
# US Share ~70-85% depending on year
BASE_CASE_DATA = [
    {"Year": 2024, "Chips_M": 23.5, "TDP": 680, "Util": 0.65, "PUE": 1.30, "US_Share": 0.85},
    {"Year": 2025, "Chips_M": 43.5, "TDP": 720, "Util": 0.68, "PUE": 1.28, "US_Share": 0.84},
    {"Year": 2026, "Chips_M": 69.0, "TDP": 780, "Util": 0.70, "PUE": 1.25, "US_Share": 0.82},
    {"Year": 2027, "Chips_M": 98.5, "TDP": 850, "Util": 0.72, "PUE": 1.22, "US_Share": 0.80},
    {"Year": 2028, "Chips_M": 127.5, "TDP": 920, "Util": 0.73, "PUE": 1.20, "US_Share": 0.78},
    {"Year": 2030, "Chips_M": 205.0, "TDP": 1050, "Util": 0.75, "PUE": 1.16, "US_Share": 0.75},
    {"Year": 2032, "Chips_M": 285.0, "TDP": 1150, "Util": 0.76, "PUE": 1.14, "US_Share": 0.73},
    {"Year": 2035, "Chips_M": 450.0, "TDP": 1300, "Util": 0.78, "PUE": 1.12, "US_Share": 0.72},
]

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
