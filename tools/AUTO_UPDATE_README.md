# Automated Artist Update Tool for DJVIBE

This tool automatically identifies artists needing updates and processes them in a single operation. It combines the artist identification and batch update process into one streamlined workflow.

## Features

- Automatic identification of artists needing updates based on tier schedules
- All-in-one operation to find and update artists
- Detailed logging and reporting
- Support for tier filtering and update type selection
- Efficient batch processing with concurrency control
- Dry run mode for testing without making updates

## Basic Usage

To run the automated update with default settings:

```bash
auto_update_artists.bat
```

This will:
1. Find all artists needing updates based on their tier
2. Process them in batches of 10 artists
3. Use a concurrency level of 3 for simultaneous updates
4. Generate a detailed log and report

## Command Line Options

The tool accepts several command line options to customize its behavior:

### Essential Options

| Option | Description |
|--------|-------------|
| `--config`, `-c` | Path to configuration file (default: D:\\DJVIBE\\MCP\\spotify-mcp\\config.json) |
| `--batch-size`, `-b` | Number of artists to update in each batch (default: 10) |
| `--concurrency`, `-cc` | Maximum number of concurrent updates (default: 3) |
| `--delay`, `-d` | Delay between API requests in seconds (default: 0.5) |
| `--limit` | Maximum total number of artists to update |

### Update Type Options

| Option | Description |
|--------|-------------|
| `--standard-only`, `-s` | Only update with standard API |
| `--partner-only`, `-p` | Only update with Partner API |
| `--dry-run`, `-dr` | Don't actually update, just show what would be updated |

### Tier Filtering Options

| Option | Description |
|--------|-------------|
| `--top-tier-only`, `-t` | Only update top tier artists (popularity >= 75) |
| `--mid-tier-only`, `-m` | Only update mid tier artists (popularity 50-74) |
| `--lower-tier-only`, `-l` | Only update lower tier artists (popularity < 50) |

## Examples

### Update All Artists

```bash
auto_update_artists.bat
```

### Update Top Tier Artists Only

```bash
auto_update_artists.bat --top-tier-only
```

### Update Only with Standard API

```bash
auto_update_artists.bat --standard-only
```

### Dry Run to Test Updates

```bash
auto_update_artists.bat --dry-run
```

### Update with Larger Batch Size

```bash
auto_update_artists.bat --batch-size 20 --concurrency 5
```

### Update Limited Number of Artists

```bash
auto_update_artists.bat --limit 50
```

## How It Works

The automated update tool:

1. **Identifies Artists**: Queries the database for artists needing updates based on tier schedules
2. **Creates a Temporary File**: Writes the artist IDs to a temporary file
3. **Invokes Batch Update**: Calls the batch_artist_update.py script with the temporary file
4. **Monitors Progress**: Streams and logs the output in real-time
5. **Cleans Up**: Removes the temporary file when done

## Logs and Reports

The tool generates:

1. **Console Output**: Real-time progress information
2. **Log File**: Detailed logs in `auto_update_artists.log`
3. **Batch Update Logs**: Additional logs from the batch update process

## Scheduling Automated Updates

You can schedule this tool to run daily using Windows Task Scheduler:

1. Open Windows Task Scheduler
2. Create a new task
3. Set the action to run `D:\DJVIBE\MCP\spotify-mcp\tools\auto_update_artists.bat`
4. Set the schedule (e.g., daily at 2 AM)
5. For command arguments, use appropriate options (e.g., `--batch-size 15`)

## Troubleshooting

### Common Issues

1. **Database Connection Issues**:
   - Verify the database path in the configuration file
   - Check database file permissions
   - Ensure no other process has locked the database

2. **API Authentication Issues**:
   - Check the configuration file to ensure credentials are correct
   - Try running with `--standard-only` or `--partner-only` to isolate the problem
   - Verify the token file path for Partner API

3. **Performance Issues**:
   - Increase batch size (`--batch-size`)
   - Increase concurrency level (`--concurrency`)
   - Run during off-peak hours

### Checking Progress

To check the progress of an ongoing update:

1. View the `auto_update_artists.log` file
2. Check the batch process logs
3. Query the database for recently updated artists:

```sql
SELECT name, popularity, last_updated, enhanced_data_updated 
FROM artists 
WHERE last_updated > datetime('now', '-1 day')
ORDER BY last_updated DESC;
```

## Future Enhancements

Planned future enhancements include:

1. Email notifications on completion
2. Web dashboard for monitoring progress
3. Smart scheduling based on API rate limit usage
4. Automatic retry for failed updates

For any questions or issues, please refer to the main documentation or contact the DJVIBE development team.
