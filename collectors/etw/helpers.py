import ntpath
from typing import Any
from config_helpers import get_direct_file_path
from .constants import PROVIDER_NAMES, PROCESS_CACHE, FILE_OBJECT_PATHS, FILE_OBJECT_FIELDS

def get_provider_name(event_data: dict[str, Any]) -> str:
    provider_id = str(
        event_data.get("EventHeader", {}).get("ProviderId", "")
    ).lower()
    return PROVIDER_NAMES.get(provider_id, "unknown")

def get_event_timestamp(event_data: dict[str, Any]) -> Any:
    for field in ("TimeStamp", "CreateTime", "ExitTime"):
        value = event_data.get(field)
        if value:
            return value
    return event_data.get("EventHeader", {}).get("TimeStamp")

def get_event_pid(event_data: dict[str, Any]) -> int | None:
    process_id = event_data.get("ProcessID")
    if process_id in (None, ""):
        process_id = event_data.get("EventHeader", {}).get("ProcessId")
    return to_int(process_id)

def to_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    try:
        base = 16 if value.lower().startswith(("0x", "-0x")) else 10
        return int(value, base)
    except ValueError:
        return None

def update_process_cache(event_data: dict[str, Any]) -> None:
    pid = get_event_pid(event_data)
    if pid is None:
        return
    PROCESS_CACHE[pid] = get_process_info(pid, event_data)

def get_process_info(
    pid: int | None,
    event_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    process_info = PROCESS_CACHE.get(pid, {}).copy() if pid is not None else {}
    if event_data is None:
        return process_info

    image_path = event_data.get("ImageName")
    event_process_info = {
        "process_sequence": event_data.get("ProcessSequenceNumber"),
        "parent_pid": event_data.get("ParentProcessID"),
        "parent_process_sequence": event_data.get("ParentProcessSequenceNumber"),
        "image": get_image_name(image_path),
        "process_path": image_path,
        "session_id": event_data.get("SessionID"),
        "is_elevated": event_data.get("ProcessTokenIsElevated"),
        "token_elevation_type": event_data.get("ProcessTokenElevationType")
        or event_data.get("TokenElevationType"),
        "command_line": event_data.get("CommandLine"),
    }

    process_info.update(clean_log_entry(event_process_info))
    return process_info

def get_image_name(image_path: Any) -> Any:
    if isinstance(image_path, str):
        return ntpath.basename(image_path)
    return image_path

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

#used to mach paths with file events, on event that don't include them
def get_file_objects(event_data: dict[str, Any]) -> list[str]:
    file_objects = []
    #loops over possible etw field names since they may vary depending on the event
    for field in FILE_OBJECT_FIELDS:
        value = event_data.get(field)
        file_object = normalize_file_object(value)
        if file_object:
            file_objects.append(file_object)
    return file_objects

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

def clean_log_entry(log_entry: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in log_entry.items()
        if value not in (None, "")
    }

