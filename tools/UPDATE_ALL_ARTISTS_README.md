# Update All Artists Tool for DJVIBE Spotify MCP

This tool identifies and updates all artists that need updates based on their tier and last update time.

## Features

- Automatically identifies artists needing updates based on tier schedules
- Processes artists in batches to prevent API rate limiting
- Controls concurrency for optimal performance
- Provides detailed logging and reporting
- Supports filtering by tier
- Includes a dry-run mode for testing

## Usage

### Basic Usage

```bash
update_all_artists.bat
```

This will:
1. Find all artists needing updates
2. Update them in batches of 10
3. Use default concurrency (3 simultaneous updates)
4. Generate a report file with details

### Command Line Options

```bash
update_all_artists.bat [OPTIONS]
```

#### Essential Options

| Option | Description |
|--------|-------------|
| `--config`, `-c` | Path to configuration file (default: D:\\DJVIBE\\MCP\\spotify-mcp\\config.json) |
| `--batch-size`, `-b` | Number of artists to update in each batch (default: 10) |
| `--concurrency`, `-cc` | Maximum number of concurrent updates (default: 3) |
| `--delay`, `-d` | Delay between API requests in seconds (default: 0.5) |
| `--limit` | Maximum total number of artists to update |

#### Update Type Options

| Option | Description |
|--------|-------------|
| `--standard-only`, `-s` | Only update with standard API |
| `--partner-only`, `-p` | Only update with Partner API |
| `--dry-run`, `-dr` | Don't actually update, just show what would be updated |

#### Tier Filtering Options

| Option | Description |
|--------|-------------|
| `--top-tier-only`, `-t` | Only update top tier artists (popularity >= 75) |
| `--mid-tier-only`, `-m` | Only update mid tier artists (popularity 50-74) |
| `--lower-tier-only`, `-l` | Only update lower tier artists (popularity < 50) |

## Examples

### Update All Artists

```bash
update_all_artists.bat
```

### Update Top Tier Artists Only

```bash
update_all_artists.bat --top-tier-only
```

### Update Only with Standard API

```bash
update_all_artists.bat --standard-only
```

### Dry Run to Test Updates

```bash
update_all_artists.bat --dry-run
```

### Update with Larger Batch Size

```bash
update_all_artists.bat --batch-size 20 --concurrency 5
```

### Update Limited Number of Artists

```bash
update_all_artists.bat --limit 50
```

## Output

The tool generates:

1. **Console Output**: Real-time progress and summary information
2. **Log File**: Detailed logs in `update_all_artists.log`
3. **Report File**: JSON report with detailed statistics and batch information

## Report File Structure

The report file (named `update_report_YYYYMMDD_HHMMSS.json`) contains:

```json
{
  "started_at": "2025-03-11T15:30:00",
  "total_artists": 145,
  "batches": [
    {
      "batch_number": 1,
      "start_time": 1710186600.123,
      "end_time": 1710186650.456,
      "duration": 50.333,
      "artists_count": 10,
      "successful": 9,
      "failed": 1
    },
    ...
  ],
  "settings": {
    "batch_size": 10,
    "concurrency": 3,
    "delay": 0.5,
    "standard_api": true,
    "partner_api": true,
    "dry_run": false
  },
  "status": "completed",
  "completed_at": "2025-03-11T16:45:00",
  "total_duration": 4500.0,
  "summary": {
    "successful": 140,
    "failed": 5
  }
}
```

## Scheduling Automated Updates

You can schedule this tool to run daily using Windows Task Scheduler:

1. Open Windows Task Scheduler
2. Create a new task
3. Set the action to run `D:\DJVIBE\MCP\spotify-mcp\tools\update_all_artists.bat`
4. Set the schedule (e.g., daily at 2 AM)
5. For command arguments, use appropriate options (e.g., `--batch-size 15`)

## Troubleshooting

### API Authentication Issues

If you encounter API authentication issues:

1. Check the configuration file to ensure credentials are correct
2. Try running with `--standard-only` or `--partner-only` to isolate the problem
3. Verify the token file path for Partner API

### Database Connection Issues

If unable to connect to the database:

1. Verify the database path in the configuration file
2. Check database file permissions
3. Ensure no other process has locked the database

### Performance Issues

If updates are running slowly:

1. Increase batch size (`--batch-size`)
2. Increase concurrency level (`--concurrency`)
3. Run during off-peak hours
4. Consider splitting updates by tier (run separate processes for each tier)
