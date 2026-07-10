import ntpath
from typing import Any

from ..constants import PROCESS_CACHE
from .event_helpers import clean_log_entry, to_int


def get_event_pid(event_data: dict[str, Any]) -> int | None:
    for field in ("ProcessID", "ProcessId", "PID", "Pid"):
        process_id = event_data.get(field)
        if process_id not in (None, ""):
            return to_int(process_id)
    return to_int(event_data.get("EventHeader", {}).get("ProcessId"))


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
