from typing import Any

KERNEL_FILE_KEYWORD_FILENAME = 0x10
KERNEL_FILE_KEYWORD_CREATE = 0x80
KERNEL_FILE_KEYWORD_READ = 0x100
KERNEL_FILE_KEYWORD_WRITE = 0x200
FILE_PROVIDER_KEYWORDS = (
    KERNEL_FILE_KEYWORD_FILENAME
    | KERNEL_FILE_KEYWORD_CREATE
    | KERNEL_FILE_KEYWORD_READ
    | KERNEL_FILE_KEYWORD_WRITE
)

PROCESS_PROVIDER = (
    "Microsoft-Windows-Kernel-Process",
    "{22fb2cd6-0e7b-422b-a0c7-2fad1fd0e716}",
    None,
)
FILE_PROVIDER = (
    "Microsoft-Windows-Kernel-File",
    "{EDD08927-9CC4-4E65-B970-C2560FB5C289}",
    FILE_PROVIDER_KEYWORDS,
)
ETW_PROVIDERS = [
    PROCESS_PROVIDER,
    FILE_PROVIDER,
]

EVENT_NAMES = {
    "PROCESSSTART": "process_start",
    "PROCESSSTOP": "process_stop",
    "CREATE": "create",
    "READ": "read",
    "WRITE": "write",
    "CLOSE": "close",
    "CLEANUP": "cleanup",
}

PROCESS_PROVIDER_ID = "{22fb2cd6-0e7b-422b-a0c7-2fad1fd0e716}"
FILE_PROVIDER_ID = "{edd08927-9cc4-4e65-b970-c2560fb5c289}"
PROVIDER_NAMES = {
    PROCESS_PROVIDER_ID: "Microsoft-Windows-Kernel-Process",
    FILE_PROVIDER_ID: "Microsoft-Windows-Kernel-File",
}

PROCESS_EVENTS = {"PROCESSSTART", "PROCESSSTOP"}
PROCESS_EVENT_ID_FILTERS = {1, 2}
FILE_EVENT_ID_FILTERS = {10, 12, 15, 16}
FILE_PATH_EVENTS = {
    "NAMECREATE",
}
FILE_EVENTS = {
    "CREATE",
    "READ",
    "WRITE",
}
FILE_OBJECT_FIELDS = ("FileObject", "FileKey", "FileObjectPointer")
FILE_HANDLE_FIELDS = ("FileHandle",)
PROCESS_CACHE: dict[int, dict[str, Any]] = {}
FILE_OBJECT_PATHS: dict[str, str] = {}
NOISY_IMAGES = {"git.exe", "conhost.exe"}
