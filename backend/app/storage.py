import json, csv, os
from pathlib import Path
from datetime import datetime, timezone
BASE_DIR = Path(__file__).resolve().parents[1]
# Render's persistent disk is mounted at /var/data. Locally, keep data inside backend/.
PERSISTENT_DIR = Path(os.getenv("STUDENTFLOW_DATA_DIR", str(BASE_DIR))).expanduser().resolve()
DATA_DIR = PERSISTENT_DIR / "data"
RESULTS_DIR = PERSISTENT_DIR / "results"
DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
_DEFAULT_DOCUMENTS = BASE_DIR / "data" / "documents.json"
if not (DATA_DIR / "documents.json").exists():
    if _DEFAULT_DOCUMENTS.exists():
        (DATA_DIR / "documents.json").write_text(_DEFAULT_DOCUMENTS.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        (DATA_DIR / "documents.json").write_text("[]", encoding="utf-8")
def load_documents():
    path = DATA_DIR / "documents.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []
def save_run(result):
    (RESULTS_DIR / f"{result['run_id']}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    path = RESULTS_DIR / "evaluation_results.csv"
    row = {"run_id":result["run_id"],"mode":result["mode"],**result["metrics"]}
    exists = path.exists()
    with path.open("a",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(row));
        if not exists: w.writeheader()
        w.writerow(row)
def list_runs():
    out = []
    for path in RESULTS_DIR.glob("*.json"):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(item, dict):
                out.append(item)
        except Exception:
            continue
    # UUID filenames do not represent chronology; sort by the actual run timestamp.
    out.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return out
def utc_now(): return datetime.now(timezone.utc).isoformat()
