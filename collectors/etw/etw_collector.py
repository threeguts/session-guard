from __future__ import annotations
import etw
import time
from .event_handling import handle_event
from .constants import ETW_PROVIDERS

def run_process_monitor() -> None:
    providers = [
        etw.ProviderInfo(provider_name, etw.GUID(provider_guid))
        for provider_name, provider_guid in ETW_PROVIDERS
    ]
    monitor = etw.ETW(
        session_name=f"ProcessMonitorTest",
        providers=providers,
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
