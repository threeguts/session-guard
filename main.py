from watchdog.observers import Observer
from file_watcher import FileEventHandler
import time

LOG_FILE = "events.json"

def main():
    event_handler = FileEventHandler(LOG_FILE)
    observer = Observer()
    observer.schedule(event_handler, ".", recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping observer..")
    finally:
        observer.stop()
        observer.join()
        print("Observer stopped..")

if __name__ == "__main__":
    main()