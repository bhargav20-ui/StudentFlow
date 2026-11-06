import os
from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
def optional_float(name):
    try: return float(os.getenv(name, "")) if os.getenv(name, "").strip() else None
    except ValueError: return None
INPUT_PRICE_PER_1M = optional_float("GEMINI_INPUT_PRICE_PER_1M")
OUTPUT_PRICE_PER_1M = optional_float("GEMINI_OUTPUT_PRICE_PER_1M")
