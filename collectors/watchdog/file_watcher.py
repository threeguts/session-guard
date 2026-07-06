import json
from pathlib import Path
from fnmatch import fnmatch
from datetime import datetime, timezone
from config_helpers import get_ignored_directories, get_ignored_files
from watchdog.events import FileSystemEvent, FileSystemEventHandler

EVENT_TYPE = [
    "created", "modified", "deleted", "moved", 
]
IGNORED_DIRECTORIES = {
    dir.casefold(): dir for dir in get_ignored_directories()
}
IGNORED_FILES = {
    file.casefold(): file for file in get_ignored_files()
}

class FileEventHandler(FileSystemEventHandler):
    def __init__(self, logs:str):
        self.log_file = Path(logs).resolve()

    def write_event(self, event: FileSystemEvent, event_type:str):
        event_log = {
            "collector": "watchdog",
            "event": f"file_{event_type}",
            "time": datetime.now(timezone.utc).isoformat(),
            "path": event.src_path,
            "is_dir": event.is_directory,
        }

        if event.dest_path:
            event_log["dest_path"] = event.dest_path

        with self.log_file.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event_log)+ "\n")
    
    def log_event(self, event: FileSystemEvent, event_type: str):
        self.write_event(event, event_type)

    def on_any_event(self, event: FileSystemEvent):
        path = Path(str(event.src_path))
        if path.resolve() == self.log_file:
            return
        if event.event_type not in EVENT_TYPE:
            return
        if any(
            part.casefold() == directory.casefold()
            for part in path.parts
            for directory in IGNORED_DIRECTORIES
        ):
            return
        if any(
            fnmatch(path.name.casefold(), file_pattern.casefold())
            for file_pattern in IGNORED_FILES
        ):
            return

        print("Event: ", event, "\nEvent type: ", event.event_type)
        self.log_event(event, event.event_type)

   
    
    

    
