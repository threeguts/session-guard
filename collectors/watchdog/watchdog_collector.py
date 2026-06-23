import os
import time
from watchdog.observers import Observer
from .file_watcher import FileEventHandler
from helpers import get_log_file, get_watch_paths, get_mode

BROWSER_FILTER = "chromium"

def run_watchdog():
    event_handler = FileEventHandler(get_log_file())
    observer = Observer()
    if get_mode() == BROWSER_FILTER:
        for path in get_watch_paths():
            if os.path.exists(path):
                print(f"Watching {path}..")
                observer.schedule(event_handler, path, recursive=True)
            else:
                print(f"Path {path} does not exist..")
    else:
        observer.schedule(event_handler, ".", recursive=True)

    observer.start()
    print("Observer started..")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping observer..")
    finally:
        observer.stop()
        observer.join()
        print("Observer stopped..")