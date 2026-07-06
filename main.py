from config_helpers import get_collector
from collectors.etw.etw_collector import run_process_monitor
from collectors.watchdog.watchdog_collector import run_watchdog

COLLECTOR_FILTER = "etw"

def main():
    if get_collector() == COLLECTOR_FILTER:
        run_process_monitor()
        return
    else:
        run_watchdog()
        return

if __name__ == "__main__":
    main()