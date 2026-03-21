import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULTS = {
    "last_subnet":   "192.168.1.0/24",
    "window_size":   "1280x760",
    "last_session":  "",
}

def load() -> dict:
    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
            # Merge with defaults so missing keys are always present
            return {**DEFAULTS, **data}
    except Exception:
        return dict(DEFAULTS)

def save(data: dict):
    try:
        current = load()
        current.update(data)
        with open(CONFIG_PATH, "w") as f:
            json.dump(current, f, indent=2)
    except Exception as e:
        print(f"Config save failed: {e}")
