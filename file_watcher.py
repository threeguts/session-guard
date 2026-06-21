import json
from datetime import datetime, timezone
from watchdog.events import FileSystemEvent, FileSystemEventHandler

EVENT_TYPE = [
    "created", "modified", "deleted", "moved", 
]

class FileEventHandler(FileSystemEventHandler):
    def __init__(self, logs:str):
        self.log_file = logs

    

    def write_event(self, event: FileSystemEvent, event_type:str):
        event_log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "path": event.src_path,
            "is_dir": event.is_directory,
        }

        with open(self.log_file, "a", encoding="utf-8") as file:
            file.write(json.dumps(event_log)+ "\n")
    
    def log_event(self, event: FileSystemEvent, event_type: str):
        self.write_event(event, event_type)

    def on_any_event(self, event: FileSystemEvent):
        
        if str(event.src_path).endswith(self.log_file):
            return

        if event.event_type not in EVENT_TYPE:
            return

        print("Event: ", event, "\nEvent type: ", event.event_type)
        self.log_event(event, event.event_type)

   
    
    

    