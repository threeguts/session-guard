import json
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
from typing import Any
from config_helpers import get_log_file
from ..etw_helpers.event_helpers import clean_json_value

STOP_REQUESTED = Event()
WRITER_STOP_REQUESTED = Event()
LOG_QUEUE: Queue[dict[str, Any]] = Queue()
WRITER_THREAD: Thread | None = None

def start_event_writer() -> None:
    global WRITER_THREAD

    if WRITER_THREAD is not None and WRITER_THREAD.is_alive():
        return

    STOP_REQUESTED.clear()
    WRITER_STOP_REQUESTED.clear()
    log_file = Path(get_log_file()).resolve()
    WRITER_THREAD = Thread(target=write_events, args=(log_file,), daemon=True)
    WRITER_THREAD.start()

def request_event_stop() -> None:
    STOP_REQUESTED.set()

def stop_event_writer() -> None:
    global WRITER_THREAD

    WRITER_STOP_REQUESTED.set()
    if WRITER_THREAD is not None:
        WRITER_THREAD.join(timeout=5)
        if WRITER_THREAD.is_alive():
            print("ETW writer is still draining queued events.")
        else:
            WRITER_THREAD = None

def write_events(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with log_file.open("a", encoding="utf-8") as event_file:
        while not WRITER_STOP_REQUESTED.is_set() or not LOG_QUEUE.empty():
            try:
                log_entry = LOG_QUEUE.get(timeout=0.1)
            except Empty:
                continue

            try:
                json.dump(
                    clean_json_value(log_entry),
                    event_file,
                    default=str,
                    ensure_ascii=False,
                )
                event_file.write("\n")
                event_file.flush()
            except Exception as error:
                print(f"ETW writer failed to write an event: {error}")
            finally:
                LOG_QUEUE.task_done()

def enqueue_log(log_entry: dict[str, Any]) -> None:
    if WRITER_THREAD is None or not WRITER_THREAD.is_alive():
        start_event_writer()
    LOG_QUEUE.put(log_entry)
