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

There is no default model. A model id picks a vendor, a price and a capability
envelope, none of which this package should choose on your behalf, so a provider
becomes usable only once you name a model for it. Without one the call fails and
names the setting to set, rather than guessing; a name the provider no longer
lists fails the same way, listing what it does offer.

| Variable | Default | Description |
|----------|---------|-------------|
| `COGNITIVE_FABRIC_LLM_PROVIDER` | `openai` | Which provider the memory optimizer calls (`openai` or `anthropic`) |
| `COGNITIVE_FABRIC_OPENAI_MODEL` | *(none)* | OpenAI model id — pick a current one from <https://platform.openai.com/docs/models>. Required when the provider is `openai`. |
| `COGNITIVE_FABRIC_ANTHROPIC_MODEL` | *(none)* | Anthropic model id — pick a current one from <https://docs.anthropic.com/en/docs/about-claude/models>. Required when the provider is `anthropic`. |
| `OPENAI_API_KEY` | - | OpenAI API key (also readable as `COGNITIVE_FABRIC_OPENAI_API_KEY`) |
| `ANTHROPIC_API_KEY` | - | Anthropic API key (also readable as `COGNITIVE_FABRIC_ANTHROPIC_API_KEY`) |

### Example .env File

```bash
# Database
COGNITIVE_FABRIC_DB_PATH=/app/data/memory.db

# Logging
COGNITIVE_FABRIC_LOG_LEVEL=INFO
COGNITIVE_FABRIC_LOG_FORMAT=json

# LLM (optional -- only the memory optimizer calls a provider). There is no
# default model, so name one; without it the call stops and says so. The model
# id below is a placeholder, not a recommendation.
COGNITIVE_FABRIC_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here
COGNITIVE_FABRIC_OPENAI_MODEL=<model id from https://platform.openai.com/docs/models>

# Alternative: Anthropic
# COGNITIVE_FABRIC_LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-your-api-key-here
# COGNITIVE_FABRIC_ANTHROPIC_MODEL=<model id from https://docs.anthropic.com/en/docs/about-claude/models>
```

## Configuration File

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

```bash
COGNITIVE_FABRIC_OPTIMIZER_MAX_DELETIONS=30
COGNITIVE_FABRIC_OPTIMIZER_STALE_DAYS=60
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
