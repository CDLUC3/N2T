import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(env_prefix='n2t_')
    host: str = "localhost"
    port: int = 8001
    protocol: str = "http"
    prefix_base_config: str = "data/config.json"


settings = Settings()
