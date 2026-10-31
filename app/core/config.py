import os
from pathlib import Path

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Use IMS_DATA_DIR when provided (Docker); otherwise use the parent folder locally.
DATA_FOLDER = Path(
    os.getenv("IMS_DATA_DIR", str(PROJECT_ROOT.parent))
)

OUTPUT_FOLDER = PROJECT_ROOT / "outputs"

COMPANY_FILE = DATA_FOLDER / "IMS_Company_Analysis.csv"
GROUP_FILE = DATA_FOLDER / "IMS_Company_Group_Analysis.csv"
VALUE_UNIT_FILE = DATA_FOLDER / "IMS_Company_Value_Unit_Analysis.csv"

DEFAULT_COMPANY = "ALKEM*"
DEFAULT_COMPETITORS = ["ALKEM*", "CIPLA", "SUN*"]
DEFAULT_GROUP_LIMIT = 10
DEFAULT_MIN_GROUP_SALES = 10.0

DATA_PERIOD = "MAT Sep 2025 vs MAT Sep 2024"