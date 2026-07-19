from datetime import datetime, timezone
from threading import Event
from time import monotonic
from typing import Any

from .constants import (
    FILE_EVENTS,
    FILE_PATH_EVENTS,
    FILE_PROVIDER,
    NOISY_IMAGES,
    PROCESS_EVENTS,
)
from .etw_helpers.event_helpers import get_provider_name
from .etw_helpers.file_helpers import (
    get_file_path,
    get_interesting_file_info,
    mark_interesting_file_objects,
    update_file_path_cache,
)
from .etw_helpers.process_helpers import (
    clear_process_cache,
    get_event_pid,
    is_browser_image,
    update_process_cache,
)
from config_helpers import (
    get_archive_file_events,
    get_live_detection_enabled,
    get_live_file_events,
    get_noise_filter,
    is_sensitive_browser_path,
)
from .logs.log_builder import build_external_file_log_entry, build_log_entry
from .logs.log_handler import enqueue_log

STOP_REQUESTED = Event()
DEDUPED_FILE_EVENTS = {"CLEANUP", "CLOSE"}
FILE_DEDUPE_WINDOW_SECONDS = 1.0
RECENT_FILE_EVENTS: dict[tuple[str, int, str], float] = {}


def handle_event(event: tuple[int, dict[str, Any]]) -> None:
    _, event_data = event
    provider_name = get_provider_name(event_data)
    task_name = str(event_data.get("Task Name", "")).upper()
    if provider_name == FILE_PROVIDER[0]:
        handle_file_event(event)
    elif task_name in PROCESS_EVENTS:
        handle_process_event(event)


def handle_process_event(event: tuple[int, dict[str, Any]]) -> None:
    if STOP_REQUESTED.is_set():
        return

    ingested_at = utc_now()
    event_id, event_data = event
    task_name = str(event_data.get("Task Name", "")).upper()

    if task_name not in PROCESS_EVENTS:
        return
    if task_name == "PROCESSSTART":
        if get_event_pid(event_data) is None:
            return
        update_process_cache(event_data)

    provider_name = get_provider_name(event_data)
    log_entry = build_log_entry(event_id, task_name, event_data, provider_name)
    log_entry["ingested_at"] = ingested_at
    image = log_entry.get("image")
    pid = log_entry.get("pid")

    if pid is None:
        return

    if not is_browser_image(image):
        if task_name == "PROCESSSTOP":
            clear_process_cache(pid, event_data)
        return

    if get_noise_filter() == "on" and image in NOISY_IMAGES:
        return

    emit_live_process_event(log_entry)
    enqueue_log(log_entry)

    if task_name == "PROCESSSTOP":
        pid = get_event_pid(event_data)
        if pid is not None:
            clear_process_cache(pid, event_data)


def handle_file_event(event: tuple[int, dict[str, Any]]) -> None:
    if STOP_REQUESTED.is_set():
        return

    ingested_at = utc_now()
    event_id, event_data = event
    task_name = str(event_data.get("Task Name", "")).upper()

    if task_name in FILE_PATH_EVENTS:
        update_file_path_cache(event_data)
        mark_interesting_file_objects(event_data)
        return

    if task_name not in FILE_EVENTS:
        return

    update_file_path_cache(event_data)
    path = get_file_path(event_data)
    if task_name == "CREATE":
        if not path or not is_sensitive_browser_path(path):
            return
        mark_interesting_file_objects(event_data, path)
    else:
        file_info = get_interesting_file_info(event_data)
        if file_info is None:
            if not path or not is_sensitive_browser_path(path):
                return
            mark_interesting_file_objects(event_data, path)
        else:
            path = file_info.get("path") or path

    pid = get_event_pid(event_data)
    if pid is None:
        return

    if is_duplicate_file_event(task_name, pid, path):
        return

    provider_name = get_provider_name(event_data)
    log_entry = build_log_entry(event_id, task_name, event_data, provider_name)
    log_entry["ingested_at"] = ingested_at
    image = log_entry.get("image")
    is_browser_owner = is_browser_image(image)

    emit_live_file_event(log_entry, is_browser_owner)

    if not should_archive_file_event(log_entry, is_browser_owner):
        return

    if get_noise_filter() == "on" and image in NOISY_IMAGES:
        return

    enqueue_log(log_entry)


def handle_external_file_event(file_row: dict[str, Any]) -> None:
    if STOP_REQUESTED.is_set():
        return

    log_entry = build_external_file_log_entry(file_row)
    log_entry["ingested_at"] = utc_now()

    pid = log_entry.get("pid")
    path = log_entry.get("path")
    event_name = str(log_entry.get("event", "")).casefold()
    if pid is None or not path or event_name not in {"create", "read", "write"}:
        return

    if is_duplicate_file_event(event_name.upper(), pid, path):
        return

    image = log_entry.get("image")
    is_browser_owner = is_browser_image(image)

    emit_live_file_event(log_entry, is_browser_owner)

    if not should_archive_file_event(log_entry, is_browser_owner):
        return

    if get_noise_filter() == "on" and image in NOISY_IMAGES:
        return

    enqueue_log(log_entry)


def is_duplicate_file_event(task_name: str, pid: int, path: Any) -> bool:
    if task_name not in DEDUPED_FILE_EVENTS or not isinstance(path, str):
        return False

    now = monotonic()
    for key, seen_at in list(RECENT_FILE_EVENTS.items()):
        if now - seen_at > FILE_DEDUPE_WINDOW_SECONDS:
            RECENT_FILE_EVENTS.pop(key, None)

    event_key = (task_name, pid, path.casefold())
    seen_at = RECENT_FILE_EVENTS.get(event_key)
    if seen_at is not None and now - seen_at <= FILE_DEDUPE_WINDOW_SECONDS:
        return True

    RECENT_FILE_EVENTS[event_key] = now
    return False


def emit_live_process_event(log_entry: dict[str, Any]) -> None:
    if not get_live_detection_enabled():
        return
    if log_entry.get("event") != "process_start":
        return

    # print(
    #     "LIVE process_start | "
    #     f"pid={log_entry.get('pid')} | "
    #     f"image={log_entry.get('image')} | "
    #     f"path={log_entry.get('process_path')}"
    # )


def emit_live_file_event(
    log_entry: dict[str, Any],
    is_browser_owner: bool,
) -> None:
    if not get_live_detection_enabled():
        return

    event_name = str(log_entry.get("event", "")).casefold()
    if event_name not in get_live_file_events():
        return

    # label = "LIVE file" if is_browser_owner else "ALERT file"
    # print(
    #     f"{label}_{event_name} | "
    #     f"pid={log_entry.get('pid')} | "
    #     f"image={log_entry.get('image')} | "
    #     f"path={log_entry.get('path')}"
    # )


def should_archive_file_event(
    log_entry: dict[str, Any],
    is_browser_owner: bool,
) -> bool:
    event_name = str(log_entry.get("event", "")).casefold()
    if event_name not in get_archive_file_events():
        return False
    if is_browser_owner:
        return True
    return event_name in get_live_file_events()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
