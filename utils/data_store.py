
import json, os
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

def _path(name):
    return os.path.join(DATA_DIR, name)

def load_json(name):
    p = _path(name)
    if not os.path.exists(p):
        return {} if name.endswith(".json") else None
    with open(p, "r") as f:
        return json.load(f)

def save_json(name, data):
    p = _path(name)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, default=str)

def append_history(entry):
    hist = load_json("signals_history.json") or []
    hist.append(entry)
    save_json("signals_history.json", hist)
