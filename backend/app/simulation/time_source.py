import time
from datetime import datetime, timezone
from typing import Protocol


class TimeSource(Protocol):
    def monotonic(self) -> float: ...

    def wall_clock_time(self) -> datetime: ...


class SystemTimeSource:
    def monotonic(self) -> float:
        return time.monotonic()

    def wall_clock_time(self) -> datetime:
        return datetime.now(timezone.utc)

