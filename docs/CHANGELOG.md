# Changelog

## v0.3.0 - 2026-07-06

- Added ETW file-event collection through `Microsoft-Windows-Kernel-File`.
- Added file-event path enrichment using cached ETW file objects.
- Added ETW filtering for browser roots plus sensitive profile paths.
- Added `browser_roots`, `sensitive_paths`, and `noise_filter` configuration.
- Cleaned up ETW log entry building to share common process/file fields.

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
