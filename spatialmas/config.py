from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_api_base: str
    model: str

    snowflake_user: str
    snowflake_password: str
    snowflake_account: str
    snowflake_database: str

    query_timeout_seconds: int
    default_result_limit: int
    max_result_limit: int

    schema_path: str
    schema_rules_path: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Backward compat: respect SCHEMA_DETAILED_PATH if SCHEMA_PATH is not set.
    schema_path = os.getenv("SCHEMA_PATH", "").strip()
    if not schema_path:
        schema_path = os.getenv("SCHEMA_DETAILED_PATH", "schema/schema_detailed.txt").strip()
    # If the legacy default points to the old file but it doesn't exist,
    # rewrite to the new default.
    if schema_path == "schema/schema_detailed.txt":
        schema_path = "schema/schema.txt"

    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_api_base=os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1/").strip(),
        model=os.getenv("MODEL", "openai/gpt-4.1-mini").strip(),
        snowflake_user=os.getenv("SNOWFLAKE_USER", "").strip(),
        snowflake_password=os.getenv("SNOWFLAKE_PASSWORD", "").strip(),
        snowflake_account=os.getenv("SNOWFLAKE_ACCOUNT", "").strip(),
        snowflake_database=os.getenv("SNOWFLAKE_DATABASE", "SPATIALMAS_DB").strip(),
        query_timeout_seconds=int(os.getenv("QUERY_TIMEOUT_SECONDS", "30")),
        default_result_limit=int(os.getenv("DEFAULT_RESULT_LIMIT", "1000")),
        max_result_limit=int(os.getenv("MAX_RESULT_LIMIT", "5000")),
        schema_path=schema_path,
        schema_rules_path=os.getenv("SCHEMA_RULES_PATH", "schema/rules.json").strip(),
    )


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return project_root() / path


def require_llm_settings() -> None:
    settings = get_settings()
    missing = []
    if not settings.openai_api_key:
        missing.append("OPENAI_API_KEY")
    if not settings.model:
        missing.append("MODEL")
    if missing:
        raise RuntimeError(f"Missing LLM settings: {', '.join(missing)}")


def require_snowflake_settings() -> None:
    settings = get_settings()
    missing = []
    if not settings.snowflake_user:
        missing.append("SNOWFLAKE_USER")
    if not settings.snowflake_password:
        missing.append("SNOWFLAKE_PASSWORD")
    if not settings.snowflake_account:
        missing.append("SNOWFLAKE_ACCOUNT")
    if missing:
        raise RuntimeError(f"Missing Snowflake settings: {', '.join(missing)}")