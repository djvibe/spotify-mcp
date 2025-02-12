# DJVIBE MCP Server Current Functionality

## Overview
The DJVIBE MCP Server provides a set of tools for interacting with Spotify's API. It's built on top of the MCP framework and provides real-time interaction capabilities with Spotify.

## Available Tools

### 1. Playback Control (SpotifyPlayback)
Controls music playback with the following actions:

```python
actions = {
    "get": "Get current track information",
    "start": "Start/resume playback",
    "pause": "Pause playback",
    "skip": "Skip to next track"
}

parameters = {
    "track_id": "Optional. Specific track to play (for 'start' action)",
    "num_skips": "Optional. Number of tracks to skip (default: 1)"
}
```

Example usage:
```python
# Start playing a specific track
SpotifyPlayback(action="start", track_id="1HL3yEnYq8LEyFQ3QegA5V")

# Get current track info
SpotifyPlayback(action="get")
```

### 2. Search (SpotifySearch)
Search for music on Spotify:

```python
parameters = {
    "query": "Search term",
    "qtype": "Type of search (track/album/artist/playlist)",
    "limit": "Maximum number of results (default: 10)"
}
```

Example usage:
```python
# Search for an artist
SpotifySearch(query="Dave Matthews Band", qtype="artist", limit=1)

# Search for tracks
SpotifySearch(query="Crash Into Me", qtype="track", limit=5)
```

### 3. Queue Management (SpotifyQueue)
Manage the playback queue:

```python
actions = {
    "add": "Add track to queue",
    "get": "Get current queue"
}

parameters = {
    "action": "Required. Either 'add' or 'get'",
    "track_id": "Required for 'add' action"
}
```

Example usage:
```python
# Add track to queue
SpotifyQueue(action="add", track_id="1HL3yEnYq8LEyFQ3QegA5V")

# Get current queue
SpotifyQueue(action="get")
```

### 4. Item Information (SpotifyGetInfo)
Get detailed information about Spotify items with new batch processing capabilities:

```python
parameters = {
    "item_id": "Spotify ID or comma-separated IDs for batch processing",
    "qtype": "Type of item (track/album/artist/playlist)"
}

batch_processing = {
    "max_batch_size": 50,
    "supported_types": ["artist"],
    "response_format": "Dict with 'artists' array"
}
```

Example usage:
```python
# Single artist info
SpotifyGetInfo(item_id="19SmlbABtI4bXz864MLqOS", qtype="artist")

# Batch artist info (up to 50 artists)
SpotifyGetInfo(
    item_id="19SmlbABtI4bXz864MLqOS,5fMUXHkw8R8eOP2RNVYEZX,5ttgIeUVka6FLyi00Uu5h8",
    qtype="artist"
)
```

## Core Features

### Authentication
- OAuth2 authentication with Spotify
- Automatic token refresh
- Scoped permissions for different operations

```python
SCOPES = [
    "user-read-currently-playing",
    "user-read-playback-state",
    "app-remote-control",
    "streaming",
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-private",
    "playlist-modify-public",
    "user-read-playback-position",
    "user-top-read",
    "user-read-recently-played",
    "user-library-modify",
    "user-library-read"
]
```

### Batch Processing
- Support for processing multiple artists in a single request
- Maximum batch size of 50 items
- Error handling for partial successes
- Database caching of results

### Device Management
- Automatic device detection
- Active device validation
- Device selection for playback

### Error Handling
- Built-in retry mechanism
- Rate limit handling
- Comprehensive error logging

## Future Enhancements
1. Batch processing for other item types (tracks, albums)
2. Enhanced caching mechanisms
3. Better error recovery
4. More comprehensive device management
5. Extended playlist management
6. Real-time artist updates