## Authentication

The unified tool handles two different authentication systems:

### 1. Standard Spotify API (OAuth 2.0)

The standard Spotify Web API uses OAuth 2.0 with client credentials:

- **Client ID**: Your Spotify Developer application client ID
- **Client Secret**: Your Spotify Developer application client secret
- **Redirect URI**: URI for OAuth callbacks

These credentials are normally set as environment variables:
```bash
export SPOTIFY_CLIENT_ID="8dff091491b2479abbd38c29997c43a8"
export SPOTIFY_CLIENT_SECRET="f10a979bd4954dabb61f135fa91da205"
export SPOTIFY_REDIRECT_URI="http://localhost:8888"
```

You can also provide them directly via command-line arguments:
```bash
unified_update.bat --artist-id "64KEffDW9EtZ1y2vBYgq8T" --db-path D:\DJVIBE\MCP\spotify-mcp\spotify_artists.db --client-id "your-client-id" --client-secret "your-client-secret" --redirect-uri "your-redirect-uri"
```

### 2. Partner API Token Management

The Partner API uses a different authentication system with access tokens. The token management system:

- Stores tokens in a JSON file and loads them when needed
- Reuses existing valid tokens to minimize API rate limiting
- Only refreshes tokens when they expire or are about to expire
- Provides token health monitoring

By default, tokens are stored in `tokens.json` in the project root directory, but a custom path can be specified with the `--tokens-file` parameter.

```bash
# Specify custom tokens file location
unified_update.bat --artist-id "64KEffDW9EtZ1y2vBYgq8T" --db-path D:\DJVIBE\MCP\spotify-mcp\spotify_artists.db --tokens-file D:\DJVIBE\MCP\tokens\partner_api_tokens.json
```

### Using a Configuration File

For convenience, you can set up a `config.json` file in the project root with all necessary credentials and settings. A template is provided (`config.json.template`) that you can copy and modify.

```json
{
  "standard_api": {
    "client_id": "your-spotify-client-id",
    "client_secret": "your-spotify-client-secret",
    "redirect_uri": "http://localhost:8888"
  },
  "partner_api": {
    "tokens_file": "tokens.json"
  },
  "database": {
    "path": "spotify_artists.db"
  }
}
```

Using a configuration file simplifies command-line usage:

```bash
# Using a config file simplifies command-line arguments
unified_update.bat --artist-id "64KEffDW9EtZ1y2vBYgq8T" --config D:\DJVIBE\MCP\spotify-mcp\config.json
```

Command-line arguments override configuration file settings when both are provided.
# DJVIBE Unified Spotify API Update Tool

## Overview

This tool combines both the standard Spotify API and the Partner API for more efficient artist updates. It intelligently determines which API to use based on artist tiers and update schedules.

## Key Features

- Updates artists with both standard API and Partner API in a single operation
- Direct integration with Partner API using proper token management
- Smart field preservation to maintain extended data during standard API updates
- Tier-based update scheduling
- Batch processing with configurable concurrency
- Comprehensive logging and error handling

## Usage

### Single Artist Update

```bash
unified_update.bat --artist-id "64KEffDW9EtZ1y2vBYgq8T" --db-path D:\DJVIBE\MCP\spotify-mcp\spotify_artists.db --tokens-file D:\DJVIBE\MCP\spotify-mcp\tokens.json
```

### Multiple Artists Update

```bash
unified_update.bat --artist-ids "64KEffDW9EtZ1y2vBYgq8T,1Cs0zKBU1kc0i8ypK3B9ai" --db-path D:\DJVIBE\MCP\spotify-mcp\spotify_artists.db
```

### Update Artists Needing Updates Based on Schedule

```bash
unified_update.bat --needs-update --db-path D:\DJVIBE\MCP\spotify-mcp\spotify_artists.db
```

### Limit Number of Artists to Update

```bash
unified_update.bat --needs-update --db-path D:\DJVIBE\MCP\spotify-mcp\spotify_artists.db --limit 10
```

### Force Standard API Updates Only

```bash
unified_update.bat --artist-id "64KEffDW9EtZ1y2vBYgq8T" --db-path D:\DJVIBE\MCP\spotify-mcp\spotify_artists.db --standard-only
```

### Force Partner API Updates Only

```bash
unified_update.bat --artist-id "64KEffDW9EtZ1y2vBYgq8T" --db-path D:\DJVIBE\MCP\spotify-mcp\spotify_artists.db --partner-only
```

### Adjust Concurrency for Batch Updates

```bash
unified_update.bat --needs-update --db-path D:\DJVIBE\MCP\spotify-mcp\spotify_artists.db --concurrency 5
```

## Command Line Arguments

| Argument | Short | Description |
|----------|-------|-------------|
| `--config` | `-c` | Path to configuration file |
| `--artist-id` | `-a` | Single Spotify artist ID to update |
| `--artist-ids` | `-ids` | Comma-separated list of Spotify artist IDs |
| `--needs-update` | `-n` | Update artists needing updates based on their tier |
| `--db-path` | `-d` | Path to SQLite database (overrides config) |
| `--tokens-file` | `-t` | Path to tokens file for Partner API (overrides config) |
| `--client-id` | | Spotify API client ID (overrides env var and config) |
| `--client-secret` | | Spotify API client secret (overrides env var and config) |
| `--redirect-uri` | | Spotify API redirect URI (overrides env var and config) |
| `--force-standard` | `-fs` | Force standard API update regardless of schedule |
| `--force-partner` | `-fp` | Force partner API update regardless of schedule |
| `--standard-only` | `-so` | Only perform standard API updates |
| `--partner-only` | `-po` | Only perform partner API updates |
| `--concurrency` | `-c` | Maximum concurrent updates (default: 3) |
| `--limit` | `-l` | Limit number of artists to update |

## Update Schedule

Artists are updated based on their popularity tier:

| Tier | Popularity Range | Standard API Update | Partner API Update |
|------|------------------|---------------------|-------------------|
| Top Tier | ≥75 | Every 3 days | Weekly |
| Mid Tier | 50-74 | Every 7 days | Bi-weekly |
| Lower Tier | <50 | Every 14 days | Monthly |

## Examples

### Update Top Artists

```bash
unified_update.bat --db-path D:\DJVIBE\MCP\spotify-mcp\spotify_artists.db --needs-update --limit 10
```

### Weekly Scheduled Update (All Tiers)

```bash
unified_update.bat --db-path D:\DJVIBE\MCP\spotify-mcp\spotify_artists.db --needs-update
```

### Force Update for a Single Artist

```bash
unified_update.bat --artist-id "64KEffDW9EtZ1y2vBYgq8T" --db-path D:\DJVIBE\MCP\spotify-mcp\spotify_artists.db --force-standard --force-partner
```
