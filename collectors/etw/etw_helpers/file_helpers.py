from typing import Any
from time import monotonic

from config_helpers import (
    get_direct_file_path,
    is_inside_browser_root,
    is_sensitive_browser_path,
)

from ..constants import FILE_HANDLE_FIELDS, FILE_OBJECT_FIELDS, FILE_OBJECT_PATHS
from .process_helpers import get_event_pid

INTERESTING_FILE_OBJECT_TTL_SECONDS = 120.0
INTERESTING_FILE_OBJECTS: dict[str, dict[str, Any]] = {}


def update_file_path_cache(event_data: dict[str, Any]) -> bool:
    path = get_direct_file_path(event_data)
    if not path or not is_inside_browser_root(path):
        return False

    cached_path = False
    for file_object in get_file_objects(event_data):
        FILE_OBJECT_PATHS[file_object] = path
        cached_path = True
    return cached_path


def mark_interesting_file_objects(
    event_data: dict[str, Any],
    path: Any = None,
) -> bool:
    if path is None:
        path = get_file_path(event_data)
    if not is_sensitive_browser_path(path):
        return False

    now = monotonic()
    prune_interesting_file_objects(now)
    pid = get_event_pid(event_data)
    marked = False

    for file_object in get_file_objects(event_data):
        FILE_OBJECT_PATHS[file_object] = path
        INTERESTING_FILE_OBJECTS[file_object] = {
            "path": path,
            "pid": pid,
            "first_seen": now,
            "last_seen": now,
        }
        marked = True
    return marked


def get_interesting_file_info(
    event_data: dict[str, Any],
) -> dict[str, Any] | None:
    now = monotonic()
    prune_interesting_file_objects(now)

    for file_object in get_file_objects(event_data):
        file_info = INTERESTING_FILE_OBJECTS.get(file_object)
        if file_info is None:
            continue

        file_info["last_seen"] = now
        path = file_info.get("path")
        if path:
            FILE_OBJECT_PATHS[file_object] = path

        public_info = file_info.copy()
        public_info["file_object"] = file_object
        return public_info
    return None


def prune_interesting_file_objects(now: float | None = None) -> None:
    if now is None:
        now = monotonic()

    for file_object, file_info in list(INTERESTING_FILE_OBJECTS.items()):
        last_seen = file_info.get("last_seen", file_info.get("first_seen"))
        if not isinstance(last_seen, (int, float)):
            INTERESTING_FILE_OBJECTS.pop(file_object, None)
            continue
        if now - last_seen > INTERESTING_FILE_OBJECT_TTL_SECONDS:
            INTERESTING_FILE_OBJECTS.pop(file_object, None)


def get_file_object(event_data: dict[str, Any]) -> str | None:
    file_objects = get_file_objects(event_data)
    if file_objects:
        return file_objects[0]
    return None


def get_file_objects(event_data: dict[str, Any]) -> list[str]:
    file_objects: list[str] = []
    pid = get_event_pid(event_data)

    for field in FILE_OBJECT_FIELDS:
        file_identity = get_file_identity(field, event_data.get(field), pid)
        if file_identity:
            file_objects.append(file_identity)

    for field in FILE_HANDLE_FIELDS:
        file_identity = get_file_identity(field, event_data.get(field), pid)
        if file_identity:
            file_objects.append(file_identity)
    return file_objects


def get_file_identity(field: str, value: Any, pid: int | None) -> str | None:
    file_object = normalize_file_object(value)
    if not file_object:
        return None
    if field in FILE_HANDLE_FIELDS:
        if pid is None:
            return None
        return f"pid:{pid}:{field.casefold()}:{file_object}"
    return f"{field.casefold()}:{file_object}"


def normalize_file_object(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return hex(value)
    if not isinstance(value, str):
        return str(value)

    value = value.strip()
    try:
        base = 16 if value.lower().startswith(("0x", "-0x")) else 10
        return hex(int(value, base))
    except ValueError:
        return value.lower()


def get_file_path(event_data: dict[str, Any]) -> Any:
    direct_path = get_direct_file_path(event_data)
    if direct_path:
        return direct_path

    for file_object in get_file_objects(event_data):
        path = FILE_OBJECT_PATHS.get(file_object)
        if path:
            return path
        file_info = INTERESTING_FILE_OBJECTS.get(file_object)
        if file_info:
            path = file_info.get("path")
            if path:
                return path
    return None
