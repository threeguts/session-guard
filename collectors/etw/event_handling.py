from .constants import PROCESS_EVENTS, FILE_EVENTS, PROCESS_CACHE, NOISY_IMAGES
from .etw_helpers.event_helpers import get_provider_name
from .etw_helpers.file_helpers import update_file_path_cache
from .etw_helpers.process_helpers import get_event_pid, update_process_cache
from config_helpers import get_noise_filter, is_sensitive_path
from .logs.log_builder import build_log_entry
from .logs.log_handler import enqueue_log
from threading import Event
from typing import Any

STOP_REQUESTED = Event()

def handle_event(event: tuple[int, dict[str, Any]]) -> None:
    if STOP_REQUESTED.is_set():
        return

    event_id, event_data = event
    task_name = str(event_data.get("Task Name", "")).upper()

    if task_name not in (PROCESS_EVENTS | FILE_EVENTS):
        return

    if task_name == "PROCESSSTART":
        if get_event_pid(event_data) is None:
            return
        update_process_cache(event_data)

    if task_name in FILE_EVENTS:
        update_file_path_cache(event_data)

    provider_name = get_provider_name(event_data)
    log_entry = build_log_entry(event_id, task_name, event_data, provider_name)

    if task_name in FILE_EVENTS and not is_sensitive_path(log_entry.get("path")):
        return

    if log_entry.get("pid") is None:
        return

    image = log_entry.get("image")
    if (
        get_noise_filter() == "on"
        and isinstance(image, str)
        and image.casefold() in NOISY_IMAGES
    ):
        return

    enqueue_log(log_entry)
    summary = f"ETW {log_entry.get('event')} | pid={log_entry.get('pid')} | | image={log_entry.get('image')}"
    if log_entry.get("path"):
        summary += f" | path={log_entry.get('path')}"
    print(summary)

    if task_name == "PROCESSSTOP":
        pid = get_event_pid(event_data)
        if pid is not None:
            PROCESS_CACHE.pop(pid, None)
