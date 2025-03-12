# DJVIBE Spotify MCP - Artist Update System

This directory contains tools for managing artist data updates in the DJVIBE Spotify Music Curation Platform. The system is designed to efficiently update artist information from both the standard Spotify API and the Spotify Partner API, with support for batch processing, tier-based scheduling, and comprehensive reporting.

## Quick Start

For new users, the recommended approach is:

1. **Run a test update first**:
   ```
   test_update.bat
   ```
   This will update 5 artists to verify everything is working correctly.

2. **Run the full update**:
   ```
   update_all_artists.bat
   ```
   This will update all artists that need updates based on their tier schedule.

## Available Tools

### Main Update Tools

| Script | Description |
|--------|-------------|
| `update_all_artists.bat` | Update all artists needing updates based on tier schedule |
| `update_top_tier.bat` | Update only top tier artists (popularity >= 75) |
| `update_standard_only.bat` | Update using only the standard Spotify API |
| `test_update.bat` | Test update with a small batch of artists |

### Single-Artist Update

For updating individual artists:

```
batch_artist_update.bat --artist-id [SPOTIFY_ID] --config D:\DJVIBE\MCP\spotify-mcp\config.json
```

### Specific Batch Update

To update a specific list of artists:

```
batch_artist_update.bat --file D:\DJVIBE\MCP\spotify-mcp\tools\artists_to_update.txt --config D:\DJVIBE\MCP\spotify-mcp\config.json
```

## Update Schedule

The system follows a tier-based update schedule:

| Tier | Popularity Range | Standard API Update | Partner API Update |
|------|------------------|---------------------|-------------------|
| Top Tier | ≥75 | Every 3 days | Every 7 days |
| Mid Tier | 50-74 | Every 7 days | Every 14 days |
| Lower Tier | <50 | Every 14 days | Every 30 days |

## System Components

### 1. Update All Artists Tool (`update_all_artists.py`)

This is the main tool that:
- Identifies artists needing updates based on tier schedule
- Processes artists in batches
- Manages concurrency
- Generates detailed reports
- Supports filtering by tier

### 2. Batch Artist Update Tool (`batch_artist_update.py`)

This is the core processing engine that:
- Handles API authentication
- Makes API requests
- Updates the database
- Provides smart field preservation
- Manages concurrent processing

### 3. Configuration (`config.json`)

Contains all necessary configuration:
- API credentials
- Database path
- Update schedule settings

## Output and Reporting

The system generates several outputs:

1. **Log Files**:
   - `update_all_artists.log` - Main log file for the update process
   - `batch_update.log` - Log file for the batch processing engine

2. **Report Files**:
   - JSON report with detailed statistics and batch information
   - Named with timestamp: `update_report_YYYYMMDD_HHMMSS.json`

## Advanced Usage

### Running from Command Line

For advanced users, all tools accept command-line arguments:

```
update_all_artists.py --batch-size 15 --concurrency 5 --top-tier-only --config D:\DJVIBE\MCP\spotify-mcp\config.json
```

### Optimizing Performance

For large updates:
- Increase batch size (`--batch-size 20`)
- Increase concurrency (`--concurrency 5`)
- Consider using tier-specific updates

### Troubleshooting

If experiencing issues:

1. **Check the logs**:
   - `update_all_artists.log`
   - `batch_update.log`

2. **Run with reduced scope**:
   - Use `test_update.bat` to verify basic functionality
   - Try standard API only with `update_standard_only.bat`
   - Update a single artist to isolate issues

3. **Verify configuration**:
   - Check credentials in `config.json`
   - Ensure database path is correct
   - Verify token file for Partner API

## Database Verification

After updates, verify the results in the database:

```sql
-- Check recently updated artists
SELECT name, popularity, last_updated, enhanced_data_updated 
FROM artists 
WHERE last_updated > datetime('now', '-1 day')
ORDER BY last_updated DESC;
```

## Scheduled Updates

For automated updates, configure Windows Task Scheduler:

1. Create a new task
2. Set the action to run `D:\DJVIBE\MCP\spotify-mcp\tools\update_all_artists.bat`
3. Set the schedule (e.g., daily at 2 AM)

## Extending the System

To add new functionality:

1. Modify `update_all_artists.py` for new filtering or processing options
2. Add new batch files for common scenarios
3. Extend reporting capabilities as needed

## For More Information

See these additional documentation files:
- `UPDATE_ALL_ARTISTS_README.md` - Detailed documentation for the update_all_artists tool
- `BATCH_UPDATE_README.md` - Details on the batch processing engine
