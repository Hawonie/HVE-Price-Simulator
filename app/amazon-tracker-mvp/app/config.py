"""Configuration module using pydantic-settings with environment variable support."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with TRACKER_ env prefix and sensible defaults."""

    # Database (SQLite by default — no external DB needed)
    database_url: str = "sqlite+aiosqlite:///./tracker.db"

    # Scraper
    playwright_headless: bool = True
    page_load_timeout: int = 30  # seconds
    retry_count: int = 3
    retry_base_delay: float = 2.0  # seconds, exponential backoff base

    # Scheduler
    crawl_interval_minutes: int = 360  # 6 hours default
    crawl_concurrency: int = 1  # sequential by default

    # Marketplace defaults
    supported_marketplaces: list[str] = ["AE", "SA", "AU"]

    # Logging
    log_level: str = "INFO"

    # Proxy for AU marketplace (optional)
    # Example: "http://user:pass@au-proxy.example.com:8080"
    au_proxy_url: str = ""

    model_config = {"env_file": ".env", "env_prefix": "TRACKER_"}


MARKETPLACE_CONFIG: dict[str, dict] = {
    "AE": {
        "domain": "www.amazon.ae",
        "currency": "AED",
        "locale": "en-AE",
        "timezone": "Asia/Dubai",
    },
    "SA": {
        "domain": "www.amazon.sa",
        "currency": "SAR",
        "locale": "en-SA",
        "timezone": "Asia/Riyadh",
    },
    "AU": {
        "domain": "www.amazon.com.au",
        "currency": "AUD",
        "locale": "en-AU",
        "timezone": "Australia/Sydney",
    },
}


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton for dependency injection."""
    return Settings()
