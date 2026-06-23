# Session-Guard

Session-Guard collects browser-profile filesystem activity or Windows process
events and writes them to JSONL.

## Collectors

- `watchdog`: Watches configured Chromium profiles. It records created,
  modified, deleted, and moved files while applying the configured exclusions.
- `etw`: Records `PROCESSSTART` and `PROCESSSTOP` events from the Windows kernel
  process provider. ETW requires an elevated terminal.

## Configuration

Edit `config.json`:

```json
{
  "watch_paths": [
    "C:\\Users\\username\\AppData\\Local\\Google\\Chrome\\User Data\\Default"
  ],
  "ignored_directories": ["Cache", "Code Cache", "GPUCache"],
  "ignored_files": ["*.tmp", "*.log", "*.lock"],
  "log_file": "events.jsonl",
  "mode": "chromium",
  "collector": "watchdog"
}
```

Set `collector` to `etw` to use ETW. Set `mode` to `chromium` to watch only the
configured profiles; any other value watches the current directory.

"mode": "chromium"/"",
"collector": "watchdog"

"mode": "",
"collector": "etw"

## Run

```powershell
python main.py
```

Stop with `Ctrl+C`. Accepted events are appended to the configured JSONL file.
