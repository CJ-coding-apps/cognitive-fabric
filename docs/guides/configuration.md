# Configuration Guide

This guide covers all configuration options for Cognitive-Fabric.

## Environment Variables

Cognitive-Fabric is configured primarily through environment variables. You can set these in a `.env` file or directly in your environment.

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `COGNITIVE_FABRIC_DB_PATH` | `./data/cognitive_fabric.db` | Path to KuzuDB database directory |
| `COGNITIVE_FABRIC_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `COGNITIVE_FABRIC_LOG_FORMAT` | `json` | Log format (`json` or `text`) |

### LLM Settings (for Memory Optimizer)

| Variable | Default | Description |
|----------|---------|-------------|
| `COGNITIVE_FABRIC_LLM_PROVIDER` | `openai` | LLM provider (`openai` or `anthropic`) |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `COGNITIVE_FABRIC_LLM_MODEL` | `gpt-4o-mini` | Model to use for optimization |

### Example .env File

```bash
# Database
COGNITIVE_FABRIC_DB_PATH=/app/data/memory.db

# Logging
COGNITIVE_FABRIC_LOG_LEVEL=INFO
COGNITIVE_FABRIC_LOG_FORMAT=json

# LLM (optional, for memory optimizer)
COGNITIVE_FABRIC_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here

# Alternative: Anthropic
# COGNITIVE_FABRIC_LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

## Configuration File

You can also use a `config.toml` file for configuration:

```toml
# config.toml
[database]
path = "./data/cognitive_fabric.db"

[logging]
level = "INFO"
format = "json"

[llm]
provider = "openai"
model = "gpt-4o-mini"

[optimizer]
default_strategy = "balanced"
max_deletions = 50
stale_days_threshold = 90
```

## CLI Configuration

The CLI supports configuration through command-line options:

```bash
# Specify database path
cognitive_fabric serve --db-path /path/to/database

# Set log level
cognitive_fabric serve --log-level DEBUG

# Use JSON logs
cognitive_fabric serve --json-logs
```

## Docker Configuration

### Environment Variables in Docker Compose

```yaml
# docker-compose.yml
services:
  cognitive_fabric:
    environment:
      - COGNITIVE_FABRIC_DB_PATH=/app/data/cognitive_fabric.db
      - COGNITIVE_FABRIC_LOG_LEVEL=INFO
      - COGNITIVE_FABRIC_LOG_FORMAT=json
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```

### Using .env with Docker Compose

```yaml
# docker-compose.yml
services:
  cognitive_fabric:
    env_file:
      - .env
```

### Volume Configuration

```yaml
services:
  cognitive_fabric:
    volumes:
      # Persist database
      - cognitive_fabric-data:/app/data
      # Custom config file
      - ./config.toml:/app/config.toml:ro

volumes:
  cognitive_fabric-data:
```

## MCP Client Configuration

### Claude Code Configuration

Add to your Claude Code MCP settings:

**macOS/Linux:**
```json
{
  "mcpServers": {
    "cognitive_fabric": {
      "command": "cognitive_fabric-server",
      "env": {
        "COGNITIVE_FABRIC_DB_PATH": "/Users/you/cognitive_fabric-data",
        "COGNITIVE_FABRIC_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**With Docker:**
```json
{
  "mcpServers": {
    "cognitive_fabric": {
      "command": "docker",
      "args": [
        "compose",
        "-f", "/path/to/cognitive-fabric/docker-compose.yml",
        "run", "--rm", "-T", "cognitive_fabric"
      ],
      "env": {
        "OPENAI_API_KEY": "${OPENAI_API_KEY}"
      }
    }
  }
}
```

## Logging Configuration

### Log Levels

| Level | Description |
|-------|-------------|
| DEBUG | Detailed debugging information |
| INFO | General operational messages |
| WARNING | Warning messages for potential issues |
| ERROR | Error messages for failures |

### JSON Log Format

When `COGNITIVE_FABRIC_LOG_FORMAT=json`:

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "info",
  "logger": "cognitive_fabric.mcp.server",
  "message": "Tool called",
  "tool": "entity",
  "operation": "create"
}
```

### Text Log Format

When `COGNITIVE_FABRIC_LOG_FORMAT=text`:

```
2024-01-15 10:30:00 [INFO] cognitive_fabric.mcp.server: Tool called tool=entity operation=create
```

## Database Configuration

### Database Path

The database path can be:
- **Relative**: `./data/memory.db` (relative to working directory)
- **Absolute**: `/var/lib/cognitive_fabric/memory.db`
- **In container**: `/app/data/memory.db`

### Database Initialization

The database is automatically initialized with the schema on first use. To manually initialize:

```bash
cognitive_fabric init /path/to/database
```

### Multiple Databases

You can run multiple instances with different databases:

```bash
# Instance 1
COGNITIVE_FABRIC_DB_PATH=/data/project1.db cognitive_fabric serve

# Instance 2
COGNITIVE_FABRIC_DB_PATH=/data/project2.db cognitive_fabric serve
```

## Memory Optimizer Configuration

### Strategy Settings

| Strategy | Stale Days | Max Deletions | Description |
|----------|------------|---------------|-------------|
| conservative | 180 | 5 | Minimal changes, safest |
| balanced | 90 | 20 | Moderate optimization |
| aggressive | 30 | 50 | Maximum cleanup |

### Custom Strategy Configuration

Via environment:
```bash
COGNITIVE_FABRIC_OPTIMIZER_MAX_DELETIONS=30
COGNITIVE_FABRIC_OPTIMIZER_STALE_DAYS=60
```

Via config file:
```toml
[optimizer]
default_strategy = "balanced"
max_deletions = 30
stale_days_threshold = 60
require_confirmation = true
preserve_recent_days = 14
```

## Security Configuration

### API Key Management

**Never commit API keys to version control.**

Use environment variables or secret management:

```bash
# From environment
export OPENAI_API_KEY=$(cat ~/.secrets/openai-key)

# From file
OPENAI_API_KEY=$(< /run/secrets/openai_key)
```

### Docker Secrets

```yaml
# docker-compose.yml
services:
  cognitive_fabric:
    secrets:
      - openai_key
    environment:
      - OPENAI_API_KEY_FILE=/run/secrets/openai_key

secrets:
  openai_key:
    file: ./secrets/openai_key.txt
```

## Performance Tuning

### Connection Settings

```toml
[database]
# Connection pool size (for future use)
pool_size = 5

# Query timeout in seconds
query_timeout = 30
```

### Memory Settings

```bash
# Build the same image CI builds, then cap its memory
docker build --file Dockerfile --tag cognitive-fabric:ci .
docker run -m 512m cognitive-fabric:ci
```

## Troubleshooting Configuration

### Verify Configuration

```bash
# Check effective configuration
cognitive_fabric info /path/to/database

# Debug mode
COGNITIVE_FABRIC_LOG_LEVEL=DEBUG cognitive_fabric serve
```

### Common Issues

**Database permission errors:**
```bash
# Ensure directory is writable
chmod 755 /path/to/data
```

**Environment variables not loaded:**
```bash
# Verify variables are set
env | grep KUZUMEMPY
```

**Docker volume issues:**
```bash
# Check volume permissions
docker compose run --rm cognitive_fabric ls -la /app/data
```
