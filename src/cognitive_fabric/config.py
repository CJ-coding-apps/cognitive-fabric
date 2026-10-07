"""Configuration using pydantic-settings."""

from typing import Literal, Optional

from pydantic import Field
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

    # Database. The environment variable is COGNITIVE_FABRIC_DB_PATH: pydantic
    # derives it from `env_prefix` plus this field name, and that is the name the
    # CLI's --db-path, the Dockerfile, docker-compose.yml and
    # docs/guides/configuration.md all use. The field was `db_path_override`,
    # which reads COGNITIVE_FABRIC_DB_PATH_OVERRIDE -- a second name, used
    # nowhere else. `python -m cognitive_fabric.main`, the entry point the
    # container runs, reaches this field and nothing else, so the published
    # image set a variable no reader looked at, started with db_path None, and
    # exited on "db_path is required when creating MemoryService" before it
    # could answer `initialize`. One setting, one name.
    db_path: Optional[str] = None

    # Logging. Both are read by `configure_logging` in the server entry points,
    # which is where the docs' claims about them are made true: they used to be
    # declared and read by nothing, so the Dockerfile set them and the process
    # logged by the function's own defaults regardless.
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_json: bool = True

    # HTTP-stream transport (opt-in; stdio remains the default). Bind localhost
    # by default so the MCP endpoint is not exposed on all interfaces.
    http_host: str = "127.0.0.1"
    http_port: int = 8001

    # LLM Configuration
    llm_provider: Literal["openai", "anthropic"] = "openai"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # No default model. A model id compiled into the package is a decision
    # nobody made: it picks a vendor, a price and a capability envelope at
    # install time, and it fails only when the provider retires the name. These
    # were `gpt-4o` and `claude-sonnet-4-20250514`. A provider is now usable only
    # once a model is named for it, and `get_model_name` says which setting is
    # missing when one is not.
    openai_model: Optional[str] = None
    anthropic_model: Optional[str] = None

    # Memory Optimizer
    optimizer_default_strategy: Literal["conservative", "balanced", "aggressive"] = (
        "conservative"
    )
    # A deployment-level ceiling on how many entities one optimization run may
    # delete, under any strategy and whatever the caller asks for. Unset means
    # the strategy's own limit applies. It is enforced where the deletions
    # happen, not where the plan is drawn up, so a caller cannot route around it.
    #
    # The published docs described this setting for a release in which nothing
    # read it. A safety limit that silently does nothing is worse than none: the
    # operator believes a cap exists and behaves accordingly.
    optimizer_max_deletions: Optional[int] = Field(default=None, ge=0)
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
