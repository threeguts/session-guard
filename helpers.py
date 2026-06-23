import os
import json
from typing import Any
from pathlib import Path

LOG_FILE = "log_file"
WATCH_PATHS = "watch_paths"
IGNORED_DIRS = "ignored_directories"
IGNORED_FILES = "ignored_files"
MODE = "mode"
COLLECTOR = "collector"
PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG = PROJECT_ROOT / "config.json"

def get_log_file():
    configured_path = Path(
        json.loads(CONFIG.read_text(encoding="utf-8")).get(LOG_FILE)
    )
    if configured_path.is_absolute():
        return str(configured_path)
    return str(PROJECT_ROOT / configured_path)

def get_watch_paths():
    paths = json.loads(CONFIG.read_text(encoding="utf-8")).get(WATCH_PATHS, [])
    return [os.path.expandvars(path) for path in paths]

def get_ignored_directories():
    return json.loads(open(CONFIG, "r").read()).get(IGNORED_DIRS)

def get_ignored_files():
    return json.loads(open(CONFIG, "r").read()).get(IGNORED_FILES)

def get_mode():
    return json.loads(open(CONFIG, "r").read()).get(MODE)

def get_collector():
    return json.loads(open(CONFIG, "r").read()).get(COLLECTOR)
