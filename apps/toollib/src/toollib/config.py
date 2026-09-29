from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read from TOOLLIB_* environment variables."""

    model_config = SettingsConfigDict(env_prefix="TOOLLIB_")

    database_url: str = "sqlite:///./toollib.db"
    # Enables the /__test__ endpoints (reset data, control the clock). Never on in production.
    test_mode: bool = False
