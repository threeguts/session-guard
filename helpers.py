import json

LOG_FILE = "log_file"
WATCH_PATHS = "watch_paths"
IGNORED_DIRS = "ignored_directories"
IGNORED_FILES = "ignored_files"
MODE = "mode"
CONFIG = "./config.json"

def get_log_file():
    return json.loads(open(CONFIG, "r").read()).get(LOG_FILE)

def get_watch_paths():
    return json.loads(open(CONFIG, "r").read()).get(WATCH_PATHS)

def get_ignored_directories():
    return json.loads(open(CONFIG, "r").read()).get(IGNORED_DIRS)

def get_ignored_files():
    return json.loads(open(CONFIG, "r").read()).get(IGNORED_FILES)

def get_mode():
    return json.loads(open(CONFIG, "r").read()).get(MODE)
