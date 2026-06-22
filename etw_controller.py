from __future__ import annotations
import os
import etw
import time
from typing import Any
from pprint import pprint
from values import PROCESS_PROVIDER_GUID

PROCESS_PROVIDER_NAME = "Microsoft-Windows-Kernel-Process"

def handle_event(event: tuple[int, dict[str, Any]]) -> None:

    event_id, event_data = event

    task_name = str(
        event_data.get("Task Name", "")
    ).upper()

    if task_name not in {"PROCESSSTART", "PROCESSSTOP"}:
        return

    process_id = event_data.get("ProcessID")
    parent_process_id = event_data.get("ParentProcessID")
    image_name = event_data.get("ImageName")
    command_line = event_data.get("CommandLine")
    exit_status = event_data.get("ExitStatus")

    print("\n" + "=" * 60)
    print(f"Task:         {task_name}")
    print(f"Event ID:     {event_id}")
    print(f"PID:          {process_id}")
    print(f"Parent PID:   {parent_process_id}")
    print(f"Image:        {image_name}")
    print(f"Command line: {command_line}")
    print(f"Exit status:  {exit_status}")

    print("\nComplete ETW event:")
    pprint(event_data)


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
    print("Open and close Notepad to generate events.")
    print("Press Ctrl+C to stop.\n")

    monitor.start()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nCtrl+C received.")

    finally:
        print("Stopping ETW process monitor...")
        monitor.stop()
        print("Monitor stopped.")


if __name__ == "__main__":
    run_process_monitor()