import ctypes
import ntpath
import os
from time import monotonic
from ctypes import wintypes
from typing import Any

from config_helpers import get_browser_processes
from ..constants import PROCESS_CACHE
from .event_helpers import clean_log_entry, to_int

SYSTEM_PID = 4
SYSTEM_PROCESS_NAME = "System"
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STOPPED_AT = "_stopped_at"
STOPPED_PROCESS_GRACE_SECONDS = 300
LIVE_PROCESS_CACHE: dict[int, dict[str, Any]] = {}


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
    prune_process_cache()
    PROCESS_CACHE[pid] = get_event_process_info(event_data)
    LIVE_PROCESS_CACHE.pop(pid, None)


def clear_process_cache(
    pid: int,
    event_data: dict[str, Any] | None = None,
) -> None:
    prune_process_cache()
    process_info = PROCESS_CACHE.get(pid, {}).copy()
    if event_data is not None and has_process_identity(event_data):
        process_info.update(get_event_process_info(event_data))

    if is_browser_process_info(process_info):
        process_info[STOPPED_AT] = monotonic()
        PROCESS_CACHE[pid] = process_info
    else:
        PROCESS_CACHE.pop(pid, None)
    LIVE_PROCESS_CACHE.pop(pid, None)


def get_process_info(
    pid: int | None,
    event_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prune_process_cache()
    process_info = PROCESS_CACHE.get(pid, {}).copy() if pid is not None else {}

    if event_data is not None and has_process_identity(event_data):
        process_info.update(get_event_process_info(event_data))
        process_info["attribution_source"] = "event_data"
        return clean_log_entry(process_info)

    if process_info:
        if STOPPED_AT in process_info:
            process_info["attribution_source"] = "recent_process_cache"
        else:
            process_info["attribution_source"] = "process_cache"
        return clean_log_entry(remove_internal_fields(process_info))

    return get_fallback_process_info(pid)


def prune_process_cache() -> None:
    now = monotonic()
    for pid, process_info in list(PROCESS_CACHE.items()):
        stopped_at = process_info.get(STOPPED_AT)
        if stopped_at is None:
            continue
        if now - stopped_at > STOPPED_PROCESS_GRACE_SECONDS:
            PROCESS_CACHE.pop(pid, None)


def remove_internal_fields(process_info: dict[str, Any]) -> dict[str, Any]:
    public_process_info = process_info.copy()
    public_process_info.pop(STOPPED_AT, None)
    return public_process_info


def is_browser_process_info(process_info: dict[str, Any]) -> bool:
    return is_browser_image(process_info.get("image"))


def is_browser_image(image: Any) -> bool:
    if not isinstance(image, str):
        return False
    browser_processes = {
        str(browser_process).casefold()
        for browser_process in get_browser_processes() or []
    }
    return image.casefold() in browser_processes


def has_process_identity(event_data: dict[str, Any]) -> bool:
    for field in ("ImageName", "CommandLine"):
        if event_data.get(field) not in (None, ""):
            return True
    return False


def get_event_process_info(event_data: dict[str, Any]) -> dict[str, Any]:
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

    return clean_log_entry(event_process_info)


def get_fallback_process_info(pid: int | None) -> dict[str, Any]:
    if pid is None:
        return {"attribution_source": "unknown"}

    if pid == SYSTEM_PID:
        return {
            "image": SYSTEM_PROCESS_NAME,
            "process_path": SYSTEM_PROCESS_NAME,
            "attribution_source": "system_pid",
        }

    cached_process_info = LIVE_PROCESS_CACHE.get(pid)
    if cached_process_info is not None:
        return cached_process_info.copy()

    process_path = get_live_process_path(pid)
    if process_path:
        process_info = {
            "image": get_image_name(process_path),
            "process_path": process_path,
            "attribution_source": "live_process_lookup",
        }
    else:
        process_info = {"attribution_source": "unknown"}

    LIVE_PROCESS_CACHE[pid] = process_info
    return process_info.copy()


def get_live_process_path(pid: int) -> str | None:
    if os.name != "nt":
        return None

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        open_process = kernel32.OpenProcess
        open_process.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        open_process.restype = wintypes.HANDLE

        query_image_name = kernel32.QueryFullProcessImageNameW
        query_image_name.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        query_image_name.restype = wintypes.BOOL

        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL

        process_handle = open_process(
            PROCESS_QUERY_LIMITED_INFORMATION,
            False,
            pid,
        )
        if not process_handle:
            return None

        try:
            buffer_size = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(buffer_size.value)
            if not query_image_name(
                process_handle,
                0,
                buffer,
                ctypes.byref(buffer_size),
            ):
                return None
            return buffer.value
        finally:
            close_handle(process_handle)
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def get_image_name(image_path: Any) -> Any:
    if isinstance(image_path, str):
        return ntpath.basename(image_path)
    return image_path
