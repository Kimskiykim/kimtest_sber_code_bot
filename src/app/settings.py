import logging
from typing import Any
from pathlib import Path


from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings, SettingsConfigDict
)


dot_env_path = Path(Path(__file__).parents[2], ".env").resolve()
db_path = str(Path(Path(__file__).parents[2], "sqlite.db").resolve())


class AppCTXSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=dot_env_path,
        validate_by_alias=True,  case_sensitive=True,
        extra="ignore")
    # fields:
    TG_BOT_TOKEN: str = ""
    TG_BOT_ADMINS: int | str | list[int] = Field(default_factory=list, description="Comma-separated list of admin user IDs or list of ints.")
    DB_CONNECTION_STRING: str = db_path
    DB_PREFIX: str = "sqlite+aiosqlite:///"

    @field_validator('TG_BOT_ADMINS', mode='after')
    @classmethod
    def ensure_list(cls, value: Any) -> Any: 
        result = list()
        if isinstance(value, list):
            for i, v in enumerate(value):
                if isinstance(v, int):
                    result.append(v)
                else:
                    logging.warning(f"Invalid admin ID in list at position {i}")
        elif isinstance(value, str):
            result = [int(v.strip()) for v in value.split(",") if v.strip().isdigit()]
        elif isinstance(value, int):
            result = [value]
        
        return result
