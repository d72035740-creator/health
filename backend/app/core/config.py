import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    environment: str = "development"
    log_level: str = "INFO"

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            environment=os.getenv("AEQUOR_ENV", "development"),
            log_level=os.getenv("AEQUOR_LOG_LEVEL", "INFO").upper(),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_environment()

