import etw
import time
from config_helpers import get_etw_file_source

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
from .traceevent_file_source import TraceEventFileSource


def run_process_monitor() -> None:
    process_monitor = etw.ETW(
        session_name="ProcessMonitorTest",
        providers=[build_provider(PROCESS_PROVIDER)],
        event_callback=handle_process_event,
        task_name_filters=sorted(PROCESS_EVENTS),
        event_id_filters=sorted(PROCESS_EVENT_ID_FILTERS),
    )
    file_source = get_etw_file_source()
    file_monitor = None
    traceevent_file_source = None

    if file_source == "pywintrace":
        file_monitor = etw.ETW(
            session_name="ProcessMonitorFileTest",
            providers=[build_provider(FILE_PROVIDER)],
            event_callback=handle_file_event,
            task_name_filters=sorted(FILE_EVENTS | FILE_PATH_EVENTS),
            event_id_filters=sorted(FILE_EVENT_ID_FILTERS),
        )
    else:
        traceevent_file_source = TraceEventFileSource()

    monitors = [process_monitor]
    if file_monitor is not None:
        monitors.append(file_monitor)

    print(f"Starting ETW browser event monitor with {file_source} file events...")
    print("Press Ctrl+C to stop.\n")

    started_monitors = []
    try:
        STOP_REQUESTED.clear()
        start_event_writer()
        for monitor in monitors:
            monitor.start()
            started_monitors.append(monitor)
        if traceevent_file_source is not None:
            traceevent_file_source.start()
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nCtrl+C received.")

    finally:
        STOP_REQUESTED.set()
        request_event_stop()
        print("Stopping ETW process monitor...")
        if traceevent_file_source is not None:
            traceevent_file_source.stop()
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
