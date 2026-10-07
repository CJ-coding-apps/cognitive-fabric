# Configuration Guide

This guide covers all configuration options for Cognitive-Fabric.

## Environment Variables

Cognitive-Fabric is configured primarily through environment variables. You can set these in a `.env` file or directly in your environment.

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `COGNITIVE_FABRIC_DB_PATH` | *(none)* | Path to the KuzuDB database directory. Required by the server; the CLI's `--db-path` sets the same thing. |
| `COGNITIVE_FABRIC_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `COGNITIVE_FABRIC_LOG_JSON` | `true` | `true` for JSON logs, `false` for plain text |

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
COGNITIVE_FABRIC_LOG_JSON=true

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

## CLI Configuration

The CLI supports configuration through command-line options:

```bash
# Specify database path
cognitive-fabric serve --db-path /path/to/database

# Set log level
cognitive-fabric serve --log-level DEBUG

# Use JSON logs
cognitive-fabric serve --json-logs
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
      - COGNITIVE_FABRIC_LOG_JSON=true
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
      "command": "cognitive-fabric-server",
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

When `COGNITIVE_FABRIC_LOG_JSON=true` (the default), one object per line on
stderr. The message key is `event`; there is no `logger` field, because
structlog's logger-name processor needs a stdlib logger and this package logs
through `PrintLogger`:

```json
{
  "tool": "entity",
  "operation": "create",
  "event": "Tool called",
  "level": "info",
  "timestamp": "2026-10-07T01:06:31.989849Z"
}
```

### Text Log Format

When `COGNITIVE_FABRIC_LOG_JSON=false`:

```
2026-10-07T01:06:31.990526Z [info     ] Tool called  operation=create tool=entity
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
cognitive-fabric init /path/to/database
```

### Multiple Databases

You can run multiple instances with different databases:

```bash
# Instance 1
COGNITIVE_FABRIC_DB_PATH=/data/project1.db cognitive-fabric serve

# Instance 2
COGNITIVE_FABRIC_DB_PATH=/data/project2.db cognitive-fabric serve
```

## Memory Optimizer Configuration

### Strategy Settings

<!-- BEGIN GENERATED: strategy table -->
| Strategy | Stale threshold (days) | Max deletions | Deletes orphaned tags | Requires no dependents |
|----------|------------------------|---------------|-----------------------|-----------------------|
| conservative | 90 | 10 | no | yes |
| balanced | 60 | 50 | yes | no |
| aggressive | 30 | 100 | yes | no |

The strategy that applies when none is requested is `COGNITIVE_FABRIC_OPTIMIZER_DEFAULT_STRATEGY`, which is `conservative`. A name that is none of these three is refused, not resolved to one of them.
<!-- END GENERATED: strategy table -->

### Capping how much one run may delete

The strategy's limit is what the optimizer would do if left to itself. A
deployment can impose a lower ceiling that no strategy and no caller can lift:

```bash
# Never remove more than 30 entities in a single optimization run.
COGNITIVE_FABRIC_OPTIMIZER_MAX_DELETIONS=30
```

It is a hard cap, enforced where the deletions are executed. Unset (the
default) means the strategy's own limit applies. The caller's `maxDeletions`
argument can lower the effective limit further but never raise it:

```
effective limit = min(strategy limit, COGNITIVE_FABRIC_OPTIMIZER_MAX_DELETIONS,
                      caller's maxDeletions)
```

## Security Configuration

### API Key Management

**Never commit API keys to version control.**

Use environment variables or secret management:

```bash
# From environment
export OPENAI_API_KEY=$(cat ~/.secrets/openai-key)

# From a file, expanded by the shell
export OPENAI_API_KEY=$(< /run/secrets/openai_key)
```

`OPENAI_API_KEY` is read by the OpenAI SDK. There is no separate file-reading
setting: the shell above, or Docker's own secret mounting, is the mechanism.

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
cognitive-fabric info /path/to/database

# Debug mode
COGNITIVE_FABRIC_LOG_LEVEL=DEBUG cognitive-fabric serve
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
env | grep COGNITIVE_FABRIC_
```

**Docker volume issues:**
```bash
# Check volume permissions
docker compose run --rm cognitive_fabric ls -la /app/data
```
