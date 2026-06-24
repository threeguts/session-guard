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

    with open(get_log_file(), "a", encoding="utf-8") as file:
        json.dump(event_data, file)
        file.write("\n")

    print("\n" + "=" * 60)
    print(f"Task:         {task_name}")
    print(f"Event ID:     {event_id}")
    print(f"PID:          {process_id}")
    print(f"Image:        {image_name}")
    if parent_process_id is not None:
        print(f"Parent PID:   {parent_process_id}")
    if exit_code is not None:
        print(f"Exit code:    {exit_code}")


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
