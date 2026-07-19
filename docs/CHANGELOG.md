# Changelog

## v0.3.0 - 2026-07-06

- Added ETW file-event collection through `Microsoft-Windows-Kernel-File`.
- Added file-event path enrichment using cached ETW file objects.
- Added ETW filtering for browser roots.
- Added `browser_roots` and `noise_filter` configuration.
- Cleaned up ETW log entry building to share common process/file fields.
- Split ETW helpers into focused `etw_helpers` and `logs` modules.
- Added a queue-backed ETW JSONL writer that drains pending events on shutdown.
- Added ETW task-name filtering for the subscribed process and file events.
- Improved file-path caching for `FileObject` and per-process `FileHandle`
  values.
- Cached configuration reads and expanded the sample browser roots.
- Added `browser_processes` configuration for ETW browser-owned process/file
  logs.
- Kept stopped browser PIDs briefly so delayed ETW file rows can still be
  attributed.
- Deduplicated repeated ETW `cleanup` and `close` file rows.
- Added live ETW detection output before JSONL enqueueing.
- Added `ingested_at`, `queued_at`, and `written_at` timing fields to ETW logs.
- Batched the background ETW JSONL writer and added queue health output.
- Added sensitive ETW file-object tracking so path-bearing sensitive browser
  file events can retain later read/write rows by `FileObject`.
- Added a TraceEvent-based C# helper as the default ETW file-event source while
  keeping `pywintrace` for process events and as a file-event fallback.

## v0.2.0 - 2026-06-23

- Added selectable `watchdog` and `etw` collectors.
- Added ETW collection for process start and stop events on Windows.
- Added raw ETW event output to the configured JSONL file.
- Moved collector implementations under `collectors/`.
- Resolved relative log paths from the project directory.

## v0.1.0 - 2026-06-21

### New

- Added JSON configuration for watch paths, ignored directories, ignored file
  patterns, log destination, and monitoring mode.
- Added monitoring of multiple Chrome profile directories.
- Added exact path-component filtering for ignored directory names.
- Added wildcard filtering for ignored filename patterns.
- Added helper functions for reading watcher configuration.

### What's changed

- Kept `main.py` responsible for observer setup while moving configuration
  access into `helpers.py`.
- Preserved the v0.0.0 generic watcher as the fallback when Chromium mode is
  disabled.
- Changed the default structured event output to JSONL.

## v0.0.0

- Fixed the file watcher so it ignores its own log file and does not re-trigger
  on log writes.
- Kept the watcher focused on the supported event types: `created`, `modified`,
  `deleted`, and `moved`.
