import functools
import os.path
import typing

import pydantic_settings

BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))

class Settings(pydantic_settings.BaseSettings):
    # env_prefix provides the environment variable prefix
    # for overriding these settings with env vars.
    # e.g. RSLV_PORT=11000
    model_config = pydantic_settings.SettingsConfigDict(env_prefix="rslv_", env_file=".env")
    host: str = "localhost"
    port: int = 8000
    protocol: str = "http"
    db_connection_string: str = f"sqlite:///{BASE_FOLDER}/data/n2t.sqlite"
    json_dir: str = f"{BASE_FOLDER}/prefixes"
    static_dir: str = os.path.join(BASE_FOLDER, "static")
    template_dir: str = os.path.join(BASE_FOLDER, "templates")
    log_filename: typing.Optional[str] = None
    environment: str = "development"


@functools.lru_cache
def get_settings(env_file=None):
    if env_file is None:
        return Settings()
    return Settings(_env_file=env_file)
