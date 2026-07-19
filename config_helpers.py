import os
import json
from fnmatch import fnmatch
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
BROWSER_PROCESSES = "browser_processes"
LIVE_DETECTION = "live_detection"
LIVE_FILE_EVENTS = "live_file_events"
ARCHIVE_FILE_EVENTS = "archive_file_events"
WRITER_BATCH_SIZE = "writer_batch_size"
WRITER_FLUSH_INTERVAL_SECONDS = "writer_flush_interval_seconds"
WRITER_HEALTH_INTERVAL_SECONDS = "writer_health_interval_seconds"
SENSITIVE_PATHS = "sensitive_paths"
DEFAULT_BROWSER_PROCESSES = ["chrome.exe", "brave.exe", "msedge.exe"]
DEFAULT_LIVE_FILE_EVENTS = ["create", "read", "write"]
DEFAULT_ARCHIVE_FILE_EVENTS = ["create", "read", "write", "cleanup", "close"]
DEFAULT_WRITER_BATCH_SIZE = 100
DEFAULT_WRITER_FLUSH_INTERVAL_SECONDS = 0.5
DEFAULT_WRITER_HEALTH_INTERVAL_SECONDS = 5.0
DEFAULT_SENSITIVE_PATHS = [
    "Network\\Cookies*",
    "Login Data*",
    "Web Data*",
    "History*",
    "Local State",
    "Preferences",
    "Secure Preferences",
]

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
    return read_config().get(IGNORED_DIRS, [])

def get_ignored_files():
    return read_config().get(IGNORED_FILES, [])

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

def get_browser_processes():
    return read_config().get(BROWSER_PROCESSES, DEFAULT_BROWSER_PROCESSES)

def get_live_detection_enabled() -> bool:
    return str(read_config().get(LIVE_DETECTION, "on")).casefold() == "on"

def get_live_file_events() -> list[str]:
    return get_string_list(LIVE_FILE_EVENTS, DEFAULT_LIVE_FILE_EVENTS)

def get_archive_file_events() -> list[str]:
    return get_string_list(ARCHIVE_FILE_EVENTS, DEFAULT_ARCHIVE_FILE_EVENTS)

def get_sensitive_paths() -> list[str]:
    return get_string_list(SENSITIVE_PATHS, DEFAULT_SENSITIVE_PATHS)

def get_writer_batch_size() -> int:
    return get_positive_int(WRITER_BATCH_SIZE, DEFAULT_WRITER_BATCH_SIZE)

def get_writer_flush_interval_seconds() -> float:
    return get_positive_float(
        WRITER_FLUSH_INTERVAL_SECONDS,
        DEFAULT_WRITER_FLUSH_INTERVAL_SECONDS,
    )

def get_writer_health_interval_seconds() -> float:
    return get_positive_float(
        WRITER_HEALTH_INTERVAL_SECONDS,
        DEFAULT_WRITER_HEALTH_INTERVAL_SECONDS,
    )

def get_string_list(key: str, default: list[str]) -> list[str]:
    values = read_config().get(key, default)
    if not isinstance(values, list):
        values = default
    return [
        str(value).casefold()
        for value in values
        if value not in (None, "")
    ]

def get_positive_int(key: str, default: int) -> int:
    try:
        value = int(read_config().get(key, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default

def get_positive_float(key: str, default: float) -> float:
    try:
        value = float(read_config().get(key, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default

def normalize_path(path: Any) -> str:
    if isinstance(path, os.PathLike):
        path = os.fspath(path)
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

@lru_cache(maxsize=1)
def get_normalized_sensitive_paths() -> tuple[str, ...]:
    return tuple(
        normalize_path(path).lstrip("\\")
        for path in get_sensitive_paths()
        if normalize_path(path).lstrip("\\")
    )

def is_sensitive_browser_path(path: Any) -> bool:
    if not is_inside_browser_root(path):
        return False

    normalized_path = normalize_path(path)
    sensitive_paths = get_normalized_sensitive_paths()
    if not sensitive_paths:
        return True

    return any(
        fnmatch(normalized_path, f"*\\{pattern}")
        or fnmatch(normalized_path, f"*\\{pattern}\\*")
        for pattern in sensitive_paths
    )
