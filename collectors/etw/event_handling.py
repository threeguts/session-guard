import json
from typing import Any
from .log_builder import build_log_entry
from .constants import PROCESS_EVENTS, FILE_EVENTS, PROCESS_CACHE, FILE_OBJECT_PATHS
from .helpers import get_provider_name, get_event_pid, get_process_info, get_file_objects
from config_helpers import get_log_file, get_noise_filter, get_direct_file_path, is_sensitive_path

def handle_event(event: tuple[int, dict[str, Any]]) -> None:
    event_id, event_data = event

    task_name = str(
        event_data.get("Task Name", "")
    ).upper()

    if task_name not in (PROCESS_EVENTS | FILE_EVENTS):
        return

    provider_name = get_provider_name(event_data)

    if task_name == "PROCESSSTART":
        pid = get_event_pid(event_data)
        if pid is None:
            return
        PROCESS_CACHE[pid] = get_process_info(pid, event_data)

    if task_name in FILE_EVENTS:
        path = get_direct_file_path(event_data)
        if path:
            for file_object in get_file_objects(event_data):
                FILE_OBJECT_PATHS[file_object] = path

    log_entry = build_log_entry(event_id, task_name, event_data, provider_name)
    process_info = get_process_info(log_entry.get("pid"), event_data)

    if get_noise_filter() == "on":
        if process_info.get("image") in {"git.exe", "conhost.exe"}:
            return

    if task_name in FILE_EVENTS and not is_sensitive_path(log_entry.get("path")):
        return
    
    if log_entry.get("pid") is None:
        return

    with open(get_log_file(), "a", encoding="utf-8") as file:
        json.dump(log_entry, file)
        file.write("\n")

    print(log_entry)
    print("\n" + "=" * 60)
    print(f"Event:        {log_entry.get('event')}")
    print(f"Provider:     {log_entry.get('provider')}")
    print(f"PID:          {log_entry.get('pid')}")
    print(f"Image:        {log_entry.get('image')}")
    if log_entry.get("process_path") is not None:
        print(f"Process path: {log_entry.get('process_path')}")
    if log_entry.get("path") is not None:
        print(f"File path:    {log_entry.get('path')}")
    if log_entry.get("parent_pid") is not None:
        print(f"Parent PID:   {log_entry.get('parent_pid')}")
    if log_entry.get("exit_code") is not None:
        print(f"Exit code:    {log_entry.get('exit_code')}")

    if task_name == "PROCESSSTOP":
        pid = get_event_pid(event_data)
        if pid is not None:
            PROCESS_CACHE.pop(pid, None)
