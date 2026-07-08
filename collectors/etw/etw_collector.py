import etw
import time
from .event_handling import handle_event
from .logs.log_handler import start_event_writer, request_event_stop, stop_event_writer
from .constants import ETW_PROVIDERS, PROCESS_EVENTS, FILE_EVENTS

def run_process_monitor() -> None:
    providers = [
        etw.ProviderInfo(provider_name, etw.GUID(provider_guid))
        for provider_name, provider_guid in ETW_PROVIDERS
    ]
    monitor = etw.ETW(
        session_name=f"ProcessMonitorTest",
        providers=providers,
        event_callback=handle_event,
        task_name_filters=sorted(PROCESS_EVENTS | FILE_EVENTS),
    )

    print("Starting ETW browser event monitor...")
    print("Press Ctrl+C to stop.\n")

    monitor_started = False
    try:
        start_event_writer()
        monitor.start()
        monitor_started = True
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nCtrl+C received.")

    finally:
        request_event_stop()
        print("Stopping ETW process monitor...")
        if monitor_started:
            monitor.stop()
        stop_event_writer()
        print("Monitor stopped.")

if __name__ == "__main__":
    run_process_monitor()
