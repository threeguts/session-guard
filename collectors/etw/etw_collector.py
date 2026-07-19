import etw
import time
from .event_handling import (
    STOP_REQUESTED,
    handle_file_event,
    handle_process_event,
)
from .logs.log_handler import start_event_writer, request_event_stop, stop_event_writer
from .constants import (
    FILE_EVENT_ID_FILTERS,
    FILE_EVENTS,
    FILE_PROVIDER,
    FILE_PATH_EVENTS,
    PROCESS_EVENT_ID_FILTERS,
    PROCESS_EVENTS,
    PROCESS_PROVIDER,
)


def run_process_monitor() -> None:
    process_monitor = etw.ETW(
        session_name=f"ProcessMonitorTest",
        providers=[build_provider(PROCESS_PROVIDER)],
        event_callback=handle_process_event,
        task_name_filters=sorted(PROCESS_EVENTS),
        event_id_filters=sorted(PROCESS_EVENT_ID_FILTERS),
    )
    file_monitor = etw.ETW(
        session_name=f"ProcessMonitorFileTest",
        providers=[build_provider(FILE_PROVIDER)],
        event_callback=handle_file_event,
        task_name_filters=sorted(FILE_EVENTS | FILE_PATH_EVENTS),
        event_id_filters=sorted(FILE_EVENT_ID_FILTERS),
    )
    monitors = (process_monitor, file_monitor)

    print("Starting ETW browser event monitor...")
    print("Press Ctrl+C to stop.\n")

    started_monitors = []
    try:
        STOP_REQUESTED.clear()
        start_event_writer()
        for monitor in monitors:
            monitor.start()
            started_monitors.append(monitor)
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nCtrl+C received.")

    finally:
        STOP_REQUESTED.set()
        request_event_stop()
        print("Stopping ETW process monitor...")
        for monitor in reversed(started_monitors):
            monitor.stop()
        stop_event_writer()
        print("Monitor stopped.")

def build_provider(provider: tuple[str, str, int | None]) -> etw.ProviderInfo:
    provider_name, provider_guid, any_keywords = provider
    return etw.ProviderInfo(
        provider_name,
        etw.GUID(provider_guid),
        any_keywords=any_keywords,
    )

if __name__ == "__main__":
    run_process_monitor()
