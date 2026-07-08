# Session-Guard

Session-Guard collects browser-profile filesystem activity or Windows ETW events and writes them to JSONL.

## Requirements

- Windows 10 or 11.
- Python 3.10 (tested with Python 3.10.5).
- Administrator privileges when using the ETW collector.
- A Chromium-based browser profile when using the Watchdog collector in
  `chromium` mode.

Install the required third-party packages:

```powershell
python -m pip install watchdog==6.0.0 pywintrace==0.2.0
```

- `watchdog` provides filesystem event monitoring.
- `pywintrace` provides the `etw` module used for Windows ETW tracing.

## Collectors

- `watchdog`: Watches configured Chromium profiles. It records created,
  modified, deleted, and moved files while applying the configured exclusions.
- `etw`: Records Windows kernel process events and selected kernel file events.
  File events are enriched through direct paths plus cached file objects, then
  filtered to configured browser roots and sensitive profile paths. ETW uses a
  background JSONL writer and requires an elevated terminal.

## Configuration

Edit `config.json`:

```json
{
  "watch_paths": [
    "%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default",
    "%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Profile 1"
  ],
  "browser_roots": [
    "%LOCALAPPDATA%\\Google\\Chrome\\User Data",
    "%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default",
    "%LOCALAPPDATA%\\BraveSoftware\\Brave-Browser\\User Data"
  ],
  "sensitive_paths": [
    "Network\\Cookies",
    "Network\\Cookies-wal",
    "Network\\Cookies-shm",
    "Network\\Cookies-journal",
    "Login Data",
    "Login Data-wal",
    "Login Data-shm",
    "Login Data-journal",
    "Local State"
  ],
  "ignored_directories": [
    "Cache",
    "Code Cache",
    "GPUCache",
    "ShaderCache",
    "Crashpad"
  ],
  "ignored_files": ["*.tmp", "*.log", "*.lock"],
  "log_file": "events.jsonl",
  "mode": "",
  "collector": "etw",
  "noise_filter": "on"
}
```

The sample above runs the ETW collector. Set `collector` to `watchdog` and
`mode` to `chromium` to watch only the configured profile folders; any other
mode watches the current directory.

- `watch_paths`: Profile folders used by the Watchdog collector.
- `browser_roots`: Browser profile roots used to scope ETW file events. If this
  is missing, ETW falls back to `watch_paths`.
- `sensitive_paths`: Relative file endings that ETW should keep under a browser
  root. Leave this empty to keep all file events under the configured roots.
- `ignored_directories` and `ignored_files`: Watchdog-only filesystem noise
  filters.
- `noise_filter`: When `on`, drops known noisy process names from ETW output,
  such as `git.exe` and `conhost.exe`.

Common combinations:

- Watchdog Chromium profile monitoring: `"collector": "watchdog"`,
  `"mode": "chromium"`.
- ETW process/file monitoring: `"collector": "etw"`, `"mode": ""`.

## Run

```powershell
python main.py
```

Stop with `Ctrl+C`. ETW prints compact event summaries while accepted events are
queued and appended to the configured JSONL file.
