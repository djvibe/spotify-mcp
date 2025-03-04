# Batch Artist Update Tool

This tool allows you to update multiple artists with enhanced data from Spotify's partner API in a single operation.

## Features

- Update multiple artists in parallel
- Smart artist selection based on various criteria
- Rate limit management to avoid API throttling
- Detailed logging and error handling
- Summary reporting

## Usage

### Basic Usage

```bash
python batch_update_artists.py --db-path DATABASE_PATH [artist selection options]
```

### Artist Selection Options

You must choose one of these options:

1. **Specific Artist IDs**:
   ```bash
   python batch_update_artists.py --artist-ids "id1,id2,id3" --db-path DATABASE_PATH
   ```

2. **From a File**:
   ```bash
   python batch_update_artists.py --file artists.txt --db-path DATABASE_PATH
   ```

3. **All Artists**:
   ```bash
   python batch_update_artists.py --all-artists --db-path DATABASE_PATH
   ```

4. **Artists Needing Updates** (based on tier):
   ```bash
   python batch_update_artists.py --needs-update --db-path DATABASE_PATH
   ```

5. **By Last Update Date**:
   ```bash
   python batch_update_artists.py --days 7 --db-path DATABASE_PATH
   ```

### Additional Options

- `--output-dir DIR`: Directory to save output files (default: tests/output)
- `--max-workers N`: Maximum number of concurrent workers (default: 3)
- `--delay N`: Delay between API requests in seconds (default: 1)
- `--limit N`: Limit the number of artists to process

## Examples

### Update Top 5 Artists

```bash
python batch_update_artists.py --needs-update --limit 5 --db-path D:\DJVIBE\MCP\spotify-mcp\spotify_artists.db
```

### Update From a List

```bash
python batch_update_artists.py --file sample_artists.txt --db-path D:\DJVIBE\MCP\spotify-mcp\spotify_artists.db
```

### Update All Artists Not Updated in 14 Days

```bash
python batch_update_artists.py --days 14 --db-path D:\DJVIBE\MCP\spotify-mcp\spotify_artists.db
```

## Using the Batch File

For convenience, you can use the batch file:

```bash
batch_update_artists.bat --needs-update --limit 5 --db-path D:\DJVIBE\MCP\spotify-mcp\spotify_artists.db
```

## How It Works

1. The script selects artists to update based on your criteria
2. It processes artists in parallel, respecting rate limits
3. For each artist:
   - Fetches enhanced data using the test_spotify_api.py script
   - Updates the database using update_artist_from_enhanced_data.py
4. Generates a summary report with statistics and any errors

## Output

1. **Log File**: batch_artist_update.log
2. **Results File**: batch_update_results_TIMESTAMP.json in the output directory
3. **Console Output**: Summary information about the batch process

## Notes

- Be mindful of Spotify API rate limits. Using --max-workers=3 and --delay=1 is recommended.
- Tokens in tests/spotify_tokens.json must be valid and not expired.
- If you get authentication errors, update your Spotify tokens and try again.
