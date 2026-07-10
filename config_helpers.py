import os
import json
from functools import lru_cache
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
BROWSER_ROOTS = "browser_roots"
SENSITIVE_PATHS = "sensitive_paths"

@lru_cache(maxsize=1)
def read_config() -> dict[str, Any]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))

def get_log_file():
    configured_log_file = read_config().get(LOG_FILE)
    if not isinstance(configured_log_file, str) or not configured_log_file:
        configured_log_file = "events.jsonl"

    configured_path = Path(configured_log_file)
    if configured_path.is_absolute():
        return str(configured_path)
    return str(PROJECT_ROOT / configured_path)

def get_watch_paths():
    paths = read_config().get(WATCH_PATHS, [])
    return [os.path.expandvars(path) for path in paths]

def get_ignored_directories():
    return read_config().get(IGNORED_DIRS)

def get_ignored_files():
    return read_config().get(IGNORED_FILES)

def get_mode():
    return read_config().get(MODE)

def get_collector():
    return read_config().get(COLLECTOR)

def get_noise_filter():
    return read_config().get(NOISE_FILTER)

def get_direct_file_path(event_data: dict[str, Any]) -> Any:
    for field in FILE_PATH_FIELDS:
        value = event_data.get(field)
        if value not in (None, ""):
            return value
    return None

def get_browser_roots():
    config = read_config()
    return config.get(BROWSER_ROOTS) or config.get(WATCH_PATHS, [])

def get_sensitive_paths():
    return read_config().get(SENSITIVE_PATHS, [])

def normalize_path(path: Any) -> str:
    if not isinstance(path, str):
        return ""
    return os.path.expandvars(path).casefold().replace("/", "\\").rstrip("\\")

def is_inside_browser_root(path: Any) -> bool:
    normalized_path = normalize_path(path)
    if not normalized_path:
        return False

    for browser_root in get_browser_roots() or []:
        normalized_root = normalize_path(browser_root)
        if not normalized_root:
            continue

        root_tail = normalized_root.split(":", 1)[-1].lstrip("\\")
        if normalized_path == normalized_root or normalized_path.startswith(normalized_root + "\\"):
            return True
        if root_tail and (normalized_path.endswith(root_tail) or f"\\{root_tail}\\" in normalized_path):
            return True
    return False

def ends_with_sensitive_path(path: Any) -> bool:
    normalized_path = normalize_path(path)
    if not normalized_path:
        return False

    sensitive_paths = get_sensitive_paths()
    if not sensitive_paths:
        return True

    for sensitive_path in sensitive_paths:
        normalized_sensitive = normalize_path(sensitive_path)
        if normalized_sensitive and (
            normalized_path == normalized_sensitive
            or normalized_path.endswith("\\" + normalized_sensitive)
        ):
            return True
    return False

def is_sensitive_path(path: Any) -> bool:
    return is_inside_browser_root(path) and ends_with_sensitive_path(path)
