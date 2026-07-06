import os
import json
import ntpath
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
NOISE_FILTER = "noise_filter"
FILE_PATH_FIELDS = ("FileName", "FilePath", "Path", "OpenPath", "Name")
SENSITIVE_PATHS = "sensitive_paths"
BROWSER_ROOTS = "browser_roots"

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

def get_noise_filter():
    return json.loads(open(CONFIG, "r").read()).get(NOISE_FILTER)

def get_direct_file_path(event_data: dict[str, Any]) -> Any:
    for field in FILE_PATH_FIELDS:
        value = event_data.get(field)
        if value not in (None, ""):
            return value
    return None

def get_sensitive_paths()-> list[str]:
    return json.loads(open(CONFIG, "r").read()).get(SENSITIVE_PATHS)

def get_browser_roots()-> list[str]:
    return json.loads(open(CONFIG, "r").read()).get(BROWSER_ROOTS)

def normalize_path(path: str) -> str:
    return ntpath.normpath(os.path.expandvars(path)).casefold()

# log this file event if:
# the path is inside a known browser profile root + the path ends with one of your sensitive file paths
def is_sensitive_path(path: Any) -> bool:
    if not isinstance(path, str) or not path:
        return False

    normalized_path = normalize_path(path)
    return (
        is_inside_browser_root(normalized_path)
        or ends_with_sensitive_path(normalized_path)
    )

def is_inside_browser_root(normalized_path: str) -> bool:
    for browser_root in get_browser_roots() or []:
        normalized_root = normalize_path(browser_root)
        if normalized_path == normalized_root:
            return True
        if normalized_path.startswith(normalized_root + "\\"):
            return True
    return False

def ends_with_sensitive_path(normalized_path: str) -> bool:
    for sensitive_path in get_sensitive_paths() or []:
        normalized_sensitive_path = normalize_path(sensitive_path).lstrip("\\")
        if normalized_path == normalized_sensitive_path:
            return True
        if normalized_path.endswith("\\" + normalized_sensitive_path):
            return True
    return False
