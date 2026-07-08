from datetime import datetime, timedelta, timezone
import re
from typing import Any

from ..constants import PROVIDER_NAMES

LOCAL_TIMEZONE = timezone(timedelta(hours=3))
WINDOWS_FILETIME_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)
UNICODE = str.maketrans("", "", "\u200e\u200f\ufeff")
FRACTIONAL_SECONDS = re.compile(r"(\.\d{6})\d+")


def get_provider_name(event_data: dict[str, Any]) -> str:
    provider_id = str(
        event_data.get("EventHeader", {}).get("ProviderId", "")
    ).lower()
    return PROVIDER_NAMES.get(provider_id, "unknown")


def get_event_timestamp(event_data: dict[str, Any]) -> Any:
    for field in ("TimeStamp", "CreateTime", "ExitTime"):
        value = event_data.get(field)
        if value:
            return value
    return event_data.get("EventHeader", {}).get("TimeStamp")


def normalize_timestamp(value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return filetime_to_local_time(value)
    if not isinstance(value, str):
        return value

    cleaned_value = remove_unicode(value).strip()
    numeric_value = to_int(cleaned_value)
    if numeric_value is not None and len(cleaned_value) >= 16:
        return filetime_to_local_time(numeric_value)

    parsed_time = parse_timestamp(cleaned_value)
    if parsed_time is None:
        return cleaned_value
    return parsed_time.astimezone(LOCAL_TIMEZONE).isoformat()


def filetime_to_local_time(filetime: int) -> str:
    seconds, remainder = divmod(filetime, 10_000_000)
    timestamp = WINDOWS_FILETIME_EPOCH + timedelta(
        seconds=seconds,
        microseconds=remainder // 10,
    )
    return timestamp.astimezone(LOCAL_TIMEZONE).isoformat()


def parse_timestamp(value: str) -> datetime | None:
    cleaned_value = FRACTIONAL_SECONDS.sub(r"\1", value)
    if cleaned_value.endswith("Z"):
        cleaned_value = cleaned_value[:-1] + "+00:00"

    try:
        parsed_time = datetime.fromisoformat(cleaned_value)
    except ValueError:
        return None
    if parsed_time.tzinfo is None:
        return parsed_time.replace(tzinfo=timezone.utc)
    return parsed_time


def remove_unicode(value: str) -> str:
    return value.translate(UNICODE)


def clean_json_value(value: Any) -> Any:
    if isinstance(value, str):
        return remove_unicode(value)
    if isinstance(value, dict):
        return {
            clean_json_value(key): clean_json_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [clean_json_value(item) for item in value]
    return value


def clean_log_entry(log_entry: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in log_entry.items()
        if value not in (None, "")
    }


def to_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    try:
        base = 16 if value.lower().startswith(("0x", "-0x")) else 10
        return int(value, base)
    except ValueError:
        return None
