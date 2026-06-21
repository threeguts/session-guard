# Session-Guard

Session-Guard is an experimental foundation for detecting browser-session theft.
It currently monitors filesystem activity and records relevant events as JSONL.

## Versions

- **v0.0.0:** Generic recursive filesystem watcher supporting `created`,
  `modified`, `deleted`, and `moved` events.
- **v0.1.0:** Adds configurable Chrome profile monitoring and filters noisy files
  and directories while preserving the generic v0.0.0 mode.

## v0.1.0 scope

The current version:

- Watches the configured Chrome `Default` and additional profile directories.
- Supports multiple watch paths.
- Ignores configured directory names such as `Cache`, `Code Cache`, and
  `GPUCache`.
- Ignores configured filename patterns such as `*.tmp`, `*.log`, and `*.lock`.
- Writes one structured JSON object per line to the configured log file.
- Preserves generic recursive monitoring when Chromium mode is disabled.

This version monitors Chrome profile filesystem activity. It does not yet detect
Chrome processes, classify suspicious activity, or respond to session theft.

## Configuration

Edit `config.json` before starting the watcher:

```json
{
  "watch_paths": [
    "C:\\Users\\username\\AppData\\Local\\Google\\Chrome\\User Data\\Default"
  ],
  "ignored_directories": ["Cache", "Code Cache", "GPUCache"],
  "ignored_files": ["*.tmp", "*.log", "*.lock"],
  "log_file": "events.jsonl",
  "mode": "chromium"
}
```

Set `mode` to `chromium` to monitor the configured profiles. Any other value
uses the original generic watcher and monitors the current directory.

## Run

From the project directory:

```powershell
python main.py
```

Stop the watcher with `Ctrl+C`.

Each accepted event is appended to the configured JSONL file with a UTC
timestamp, event type, source path, and directory flag.
