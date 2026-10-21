from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = ROOT / "figures"
REPORT_DIR = ROOT / "report"

N_USERS = 300
START_DATE = "2025-01-01"
END_DATE = "2026-06-30"
SIMULATION_START_DATE = "2024-11-01"
RANDOM_SEED = 42
TARGET_SHORTFALL_RATE = 0.25
BASE_SPEND_RATIO = 0.90

PATTERNS = [
    "đều",
    "dồn đầu chu kỳ",
    "tăng cuối tuần",
    "chi lớn bất thường",
]
INCOME_TYPES = ["trợ cấp đầu tháng", "lương ngày 25"]

DAILY_COLUMNS = [
    "user_id",
    "date",
    "spend",
    "income",
    "balance",
    "days_to_next_income",
    "day_in_cycle",
    "pattern",
]
