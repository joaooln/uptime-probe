from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (PROBE_*)."""

    model_config = SettingsConfigDict(env_prefix="PROBE_")

    interval_seconds: float = 30.0
    timeout_seconds: float = 5.0
    # Comma-separated list of URLs to monitor from startup, e.g. from a ConfigMap.
    initial_targets: str = ""
    log_level: str = "info"

    def initial_target_list(self) -> list[str]:
        return [t.strip() for t in self.initial_targets.split(",") if t.strip()]


settings = Settings()
