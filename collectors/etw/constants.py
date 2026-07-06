from typing import Any 

ETW_PROVIDERS = [
    ("Microsoft-Windows-Kernel-Process", "{22fb2cd6-0e7b-422b-a0c7-2fad1fd0e716}"),
    ("Microsoft-Windows-Kernel-File", "{EDD08927-9CC4-4E65-B970-C2560FB5C289}"),
]

NUMERIC_FIELDS = {
    "ProcessID",
    "ProcessSequenceNumber",
    "ParentProcessID",
    "ParentProcessSequenceNumber",
    "SessionID",
    "ProcessTokenElevationType",
    "ProcessTokenIsElevated",
    "ExitCode",
    "TokenElevationType",
    "HandleCount",
    "CommitCharge",
    "CommitPeak",
    "CPUCycleCount",
    "ReadOperationCount",
    "WriteOperationCount",
    "ReadTransferKiloBytes",
    "WriteTransferKiloBytes",
    "HardFaultCount",
}

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

TIMESTAMP_FIELDS = {"CreateTime", "ExitTime"}
PROCESS_EVENTS = {"PROCESSSTART", "PROCESSSTOP"}
FILE_EVENTS = {
    "CREATE",
    "READ",
    "WRITE",
    "CLOSE",
    "CLEANUP",
}
FILE_OBJECT_FIELDS = ("FileObject", "FileKey", "FileObjectPointer", "FileHandle")
PROCESS_CACHE: dict[int, dict[str, Any]] = {}
FILE_OBJECT_PATHS: dict[str, str] = {}