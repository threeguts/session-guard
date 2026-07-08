from typing import Any

from config_helpers import get_direct_file_path

from ..constants import FILE_HANDLE_FIELDS, FILE_OBJECT_FIELDS, FILE_OBJECT_PATHS
from .process_helpers import get_event_pid


def update_file_path_cache(event_data: dict[str, Any]) -> None:
    path = get_direct_file_path(event_data)
    if not path:
        return

    for file_object in get_file_objects(event_data):
        FILE_OBJECT_PATHS[file_object] = path


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
    return None
