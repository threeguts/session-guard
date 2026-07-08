from typing import Any
from ..constants import FILE_EVENTS, EVENT_NAMES
from ..etw_helpers.event_helpers import (
    clean_log_entry,
    get_event_timestamp,
    normalize_timestamp,
)
from ..etw_helpers.file_helpers import get_file_object, get_file_path
from ..etw_helpers.process_helpers import get_event_pid, get_process_info

def build_log_entry(
    event_id: int,
    task_name: str,
    event_data: dict[str, Any],
    provider_name: str,
) -> dict[str, Any]:
    pid = get_event_pid(event_data)
    process_info = get_process_info(pid, event_data)

    log_entry = {
        "collector": "etw",
        "provider": provider_name,
        "event": EVENT_NAMES.get(task_name, task_name.lower()),
        "event_id": event_id,
        "time": get_log_time(task_name, event_data),
        "pid": pid,
        "process_sequence": process_info.get("process_sequence"),
        "image": process_info.get("image"),
        "process_path": process_info.get("process_path"),
        "command_line": process_info.get("command_line"),
    }

    if task_name in FILE_EVENTS:
        log_entry.update({
            "path": get_file_path(event_data),
            "file_object": get_file_object(event_data),
        })
    else:
        log_entry.update({
            "parent_pid": process_info.get("parent_pid"),
            "parent_process_sequence": process_info.get("parent_process_sequence"),
            "session_id": process_info.get("session_id"),
            "is_elevated": process_info.get("is_elevated"),
            "token_elevation_type": process_info.get("token_elevation_type"),
        })
    return clean_log_entry(log_entry)

def get_log_time(task_name: str, event_data: dict[str, Any]) -> Any:
    if task_name == "PROCESSSTART":
        return normalize_timestamp(event_data.get("CreateTime"))
    if task_name == "PROCESSSTOP":
        return normalize_timestamp(event_data.get("ExitTime"))
    return normalize_timestamp(get_event_timestamp(event_data))
