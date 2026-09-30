"""Configuration using pydantic-settings."""

from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="COGNITIVE_FABRIC_",
        case_sensitive=False,
    )

    # Application
    app_name: str = "cognitive-fabric"
    version: str = "1.0.0"
    db_name: str = "cognitive_fabric"

    # Database
    db_path_override: Optional[str] = None

    # Logging
    log_level: str = "INFO"
    log_json: bool = True

    # HTTP-stream transport (opt-in; stdio remains the default). Bind localhost
    # by default so the MCP endpoint is not exposed on all interfaces.
    http_host: str = "127.0.0.1"
    http_port: int = 8001

    # LLM Configuration
    llm_provider: Literal["openai", "anthropic"] = "openai"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Memory Optimizer
    optimizer_default_strategy: Literal["conservative", "balanced", "aggressive"] = (
        "conservative"
    )
    optimizer_enable_mcp_sampling: bool = True
    optimizer_snapshot_failure_policy: Literal["abort", "continue", "warn"] = "warn"
    optimizer_default_sampling_strategy: Literal[
        "representative", "problematic", "recent", "diverse"
    ] = "representative"
    optimizer_default_sample_size: int = 20

    # Cognitive Fabric
    fabric_data_dir: Optional[str] = None
    fabric_embedding_provider: Literal[
        "fastembed", "openai", "sentence-transformers"
    ] = "fastembed"
    fabric_embedding_model: Optional[str] = None


settings = Settings()
