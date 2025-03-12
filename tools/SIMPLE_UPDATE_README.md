# Simple Unified Spotify Artist Update Tool

## Overview

This is a simplified version of the unified update tool that doesn't rely on importing from the existing package structure. It calls the existing scripts directly using subprocess, which avoids import issues.

## Usage

```bash
simple_artist_update.bat --artist-id "19SmlbABtI4bXz864MLqOS" --config D:\DJVIBE\MCP\spotify-mcp\config.json
```

## Features

- Updates artists using both standard Spotify API and Partner API
- Uses existing scripts to avoid code duplication
- Configurable via configuration file
- Logs detailed information about the update process

## Command Line Arguments

| Argument | Short | Description |
|----------|-------|-------------|
| `--config` | `-c` | Path to configuration file (required) |
| `--artist-id` | `-a` | Spotify artist ID to update (required) |
| `--standard-only` | `-s` | Only update with standard API |
| `--partner-only` | `-p` | Only update with Partner API |

## Configuration File

The tool uses the same configuration file format as the main unified update tool:

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
    "path": "D:\\DJVIBE\\MCP\\spotify-mcp\\spotify_artists.db"
  }
}
```

## Examples

### Update with Both APIs

```bash
simple_artist_update.bat --artist-id "19SmlbABtI4bXz864MLqOS" --config D:\DJVIBE\MCP\spotify-mcp\config.json
```

### Update with Standard API Only

```bash
simple_artist_update.bat --artist-id "19SmlbABtI4bXz864MLqOS" --config D:\DJVIBE\MCP\spotify-mcp\config.json --standard-only
```

### Update with Partner API Only

```bash
simple_artist_update.bat --artist-id "19SmlbABtI4bXz864MLqOS" --config D:\DJVIBE\MCP\spotify-mcp\config.json --partner-only
```
