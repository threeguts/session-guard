from __future__ import annotations
import ntpath
import etw
import time
import json
from typing import Any
from helpers import get_log_file, get_noise_filter

PROCESS_PROVIDER_GUID = (
    "{22fb2cd6-0e7b-422b-a0c7-2fad1fd0e716}"
)
PROCESS_PROVIDER_NAME = "Microsoft-Windows-Kernel-Process"

NUMERIC_FIELDS = {
    "ProcessID",
    "ProcessSequenceNumber",
    "ParentProcessID",
    "ParentProcessSequenceNumber",
    "SessionID",
    "ProcessTokenElevationType",
    "ProcessTokenIsElevated",
    "ExitCode",
    "TokenElevationType",
    "HandleCount",
    "CommitCharge",
    "CommitPeak",
    "CPUCycleCount",
    "ReadOperationCount",
    "WriteOperationCount",
    "ReadTransferKiloBytes",
    "WriteTransferKiloBytes",
    "HardFaultCount",
}
TIMESTAMP_FIELDS = {"CreateTime", "ExitTime"}
EVENT_NAMES = {
    "PROCESSSTART": "process_start",
    "PROCESSSTOP": "process_stop",
}


def normalize_event_data(event_data: dict[str, Any]) -> dict[str, Any]:
    normalized = event_data.copy()

    for field in TIMESTAMP_FIELDS:
        value = normalized.get(field)
        if isinstance(value, str):
            normalized[field] = value.replace("\u200e", "")

    for field in NUMERIC_FIELDS:
        value = normalized.get(field)
        if not isinstance(value, str):
            continue
        try:
            base = 16 if value.lower().startswith(("0x", "-0x")) else 10
            normalized[field] = int(value, base)
        except ValueError:
            pass

    image_name = normalized.get("ImageName")
    if isinstance(image_name, str):
        normalized["ImageName"] = ntpath.basename(image_name)

    return normalized


def build_log_entry(
    event_id: int,
    task_name: str,
    event_data: dict[str, Any],
) -> dict[str, Any]:
    timestamp = event_data.get("CreateTime")
    if task_name == "PROCESSSTOP":
        timestamp = event_data.get("ExitTime")

    log_entry = {
        "collector": "etw",
        "event": EVENT_NAMES.get(task_name, task_name.lower()),
        "event_id": event_id,
        "time": timestamp,
        "pid": event_data.get("ProcessID"),
        "process_sequence": event_data.get("ProcessSequenceNumber"),
        "parent_pid": event_data.get("ParentProcessID"),
        "parent_process_sequence": event_data.get("ParentProcessSequenceNumber"),
        "image": event_data.get("ImageName"),
        "session_id": event_data.get("SessionID"),
        "is_elevated": event_data.get("ProcessTokenIsElevated"),
        "token_elevation_type": event_data.get("ProcessTokenElevationType")
        or event_data.get("TokenElevationType"),
    }

    command_line = event_data.get("CommandLine")
    if command_line:
        log_entry["command_line"] = command_line

    if task_name == "PROCESSSTOP":
        log_entry["exit_code"] = event_data.get("ExitCode")

    return {
        key: value
        for key, value in log_entry.items()
        if value not in (None, "")
    }


def handle_event(event: tuple[int, dict[str, Any]]) -> None:

    event_id, event_data = event

    task_name = str(
        event_data.get("Task Name", "")
    ).upper()

    if task_name not in {"PROCESSSTART", "PROCESSSTOP"}:
        return

    event_data = normalize_event_data(event_data)
    process_id = event_data.get("ProcessID")
    parent_process_id = event_data.get("ParentProcessID")
    image_name = event_data.get("ImageName")
    exit_code = event_data.get("ExitCode")

    if get_noise_filter()=="on":
        if image_name=="git.exe" or image_name=="conhost.exe":
            return

    log_entry = build_log_entry(event_id, task_name, event_data)

    with open(get_log_file(), "a", encoding="utf-8") as file:
        json.dump(log_entry, file)
        file.write("\n")

    print("\n" + "=" * 60)
    print(f"Event:        {log_entry.get('event')}")
    print(f"PID:          {log_entry.get('pid')}")
    print(f"Image:        {log_entry.get('image')}")
    if parent_process_id is not None:
        print(f"Parent PID:   {log_entry.get('parent_pid')}")
    if exit_code is not None:
        print(f"Exit code:    {log_entry.get('exit_code')}")


def run_process_monitor() -> None:
    process_provider = etw.ProviderInfo(
        PROCESS_PROVIDER_NAME,
        etw.GUID(PROCESS_PROVIDER_GUID),
    )

    monitor = etw.ETW(
        session_name=f"ProcessMonitorTest",
        providers=[process_provider],
        event_callback=handle_event,
    )

    print("Starting ETW process monitor...")
    print("Press Ctrl+C to stop.\n")

    monitor_started = False
    try:
        monitor.start()
        monitor_started = True
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nCtrl+C received.")

    finally:
        print("Stopping ETW process monitor...")
        if monitor_started:
            monitor.stop()
        print("Monitor stopped.")


if __name__ == "__main__":
    run_process_monitor()
