# Enhanced Artist Data Tools

This directory contains tools for accessing Spotify's enhanced artist data through their partner API and updating your artist database with the additional metrics.

## Setup

Before using these tools, you need to:

1. Ensure you have valid Spotify authentication tokens in `tests/spotify_tokens.json`
2. Make sure your artist already exists in the database (added through the standard API)
3. Verify that the database has the necessary columns for enhanced data

## Available Tools

### 1. update_artist_from_enhanced_data.py

This script updates your SQLite database with enhanced artist data fetched from Spotify's partner API.

#### Usage

```bash
python tools\update_artist_from_enhanced_data.py --artist-id ARTIST_ID --db-path DATABASE_PATH
```

#### Parameters:

- `--artist-id` or `-a`: Spotify artist ID to update (required)
- `--db-path` or `-d`: Path to SQLite database file (required)
- `--metrics-file` or `-m`: Custom path to metrics JSON file (optional)
- `--response-file` or `-r`: Custom path to full response JSON file (optional)

By default, the script looks for metrics files in `tests/output/ARTIST_ID_metrics.json`.

### 2. update_artist_db.bat (Windows)

This is a convenient batch script that fetches the data and updates the database in one step.

#### Usage

```bash
tools\update_artist_db.bat -a ARTIST_ID -d DATABASE_PATH
```

#### Parameters:

- `-a` or `--artist-id`: Spotify artist ID to update
- `-d` or `--db-path`: Path to SQLite database file
- `-o` or `--output-dir`: Custom output directory for JSON files

### 3. update_artist_db.sh (Linux/Mac)

Same functionality as the batch file but for Linux/Mac systems.

#### Usage

```bash
./tools/update_artist_db.sh -a ARTIST_ID -d DATABASE_PATH
```

### 4. verify_artist_update.sql

Contains SQL queries to verify the updated data in your database.

## Workflow Example

Here's a complete workflow example:

1. Fetch enhanced data for an artist:
   ```bash
   python tests\test_spotify_api.py --artist-id 76M2Ekj8bG8W7X2nbx2CpF
   ```

2. Update your database with the enhanced data:
   ```bash
   python tools\update_artist_from_enhanced_data.py --artist-id 76M2Ekj8bG8W7X2nbx2CpF --db-path path\to\your\database.db
   ```

3. Or do both in one step (Windows):
   ```bash
   tools\update_artist_db.bat -a 76M2Ekj8bG8W7X2nbx2CpF -d path\to\your\database.db
   ```

## Troubleshooting

If you encounter errors like "Metrics file not found", check:

1. Make sure you've run the test script first to generate the metrics files
2. Verify the output directory exists (`tests/output`)
3. Check if the artist ID is correct
4. Ensure your Spotify tokens are valid and up-to-date

## Token Management

The tools rely on authentication tokens stored in `tests/spotify_tokens.json`. These tokens expire frequently, so you'll need to update them regularly:

1. Log into Spotify Web Player
2. Open browser developer tools (F12)
3. Go to the Network tab
4. Navigate to an artist page
5. Look for requests to api-partner.spotify.com
6. Find the request headers for authorization and client-token
7. Update `tests/spotify_tokens.json` with the new tokens
