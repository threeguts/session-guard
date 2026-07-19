import json
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
from time import monotonic
from typing import Any
from config_helpers import (
    get_log_file,
    get_writer_batch_size,
    get_writer_flush_interval_seconds,
    get_writer_health_interval_seconds,
)
from ..etw_helpers.event_helpers import clean_json_value

STOP_REQUESTED = Event()
WRITER_STOP_REQUESTED = Event()
LOG_QUEUE: Queue[dict[str, Any]] = Queue()
WRITER_THREAD: Thread | None = None
QUEUED_MONOTONIC = "_queued_monotonic"

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
    batch_size = get_writer_batch_size()
    flush_interval = get_writer_flush_interval_seconds()
    health_interval = get_writer_health_interval_seconds()
    batch: list[dict[str, Any]] = []
    next_flush = monotonic() + flush_interval
    next_health = monotonic() + health_interval
    last_health = monotonic()
    last_written_count = 0
    written_count = 0
    oldest_queued_age = 0.0

    with log_file.open("a", encoding="utf-8") as event_file:
        while not WRITER_STOP_REQUESTED.is_set() or not LOG_QUEUE.empty():
            timeout = max(0.0, next_flush - monotonic()) if batch else 0.1
            try:
                log_entry = LOG_QUEUE.get(timeout=timeout)
                queued_at = log_entry.get(QUEUED_MONOTONIC)
                if isinstance(queued_at, float):
                    oldest_queued_age = max(0.0, monotonic() - queued_at)
                batch.append(log_entry)
            except Empty:
                pass

            if batch and (
                len(batch) >= batch_size
                or monotonic() >= next_flush
                or WRITER_STOP_REQUESTED.is_set()
            ):
                written_count += write_batch(event_file, batch)
                batch.clear()
                next_flush = monotonic() + flush_interval

            if monotonic() >= next_health:
                elapsed = max(monotonic() - last_health, 0.001)
                written_delta = written_count - last_written_count
                rows_per_second = written_delta / elapsed
                last_health = monotonic()
                last_written_count = written_count
                next_health = monotonic() + health_interval

        if batch:
            write_batch(event_file, batch)

def write_batch(
    event_file: Any,
    batch: list[dict[str, Any]],
    mark_done: bool = True,
) -> int:
    written_count = 0
    try:
        for log_entry in batch:
            log_entry["written_at"] = utc_now()
            log_entry.pop(QUEUED_MONOTONIC, None)
            json.dump(
                clean_json_value(log_entry),
                event_file,
                default=str,
                ensure_ascii=False,
            )
            event_file.write("\n")
            written_count += 1
        event_file.flush()
    except Exception as error:
        print(f"ETW writer failed to write an event batch: {error}")
    finally:
        if mark_done:
            for _ in batch:
                LOG_QUEUE.task_done()
    return written_count

def enqueue_log(log_entry: dict[str, Any]) -> None:
    if WRITER_THREAD is None or not WRITER_THREAD.is_alive():
        start_event_writer()
    log_entry["queued_at"] = utc_now()
    log_entry[QUEUED_MONOTONIC] = monotonic()
    LOG_QUEUE.put(log_entry)

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
