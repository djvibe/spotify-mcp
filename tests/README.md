# Spotify Enhanced Artist Data Test

This test script demonstrates how to fetch enhanced artist data from Spotify's partner API, which includes additional metrics not available in the standard Spotify Web API.

## Features

- Retrieves monthly listeners count
- Gets top cities with listener counts
- Retrieves upcoming concerts
- Gets social media links
- Retrieves biography and verified status

## Setup

### Authentication Tokens

The script requires valid Spotify authentication tokens. These should be stored in `spotify_tokens.json` with the following structure:

```json
{
  "auth_token": "your_auth_token_here",
  "client_token": "your_client_token_here"
}
```

### Obtaining Tokens

To get fresh authentication tokens:

1. Log into Spotify Web Player (https://open.spotify.com/)
2. Open browser developer tools (F12)
3. Go to the Network tab
4. Navigate to an artist page
5. Look for requests to `api-partner.spotify.com`
6. Find the following header values:
   - `authorization` header (remove the "Bearer " prefix if including it in the JSON file)
   - `client-token` header

### Token Lifetime

Spotify tokens typically expire after a short period (approximately 1 hour). If you get a 401 Unauthorized error, you'll need to refresh the tokens.

## Command Line Options

The test script accepts the following command line arguments:

```
  -h, --help            Show help message and exit
  --artist-id ARTIST_ID, -a ARTIST_ID
                        Spotify artist ID to fetch data for (default: 76M2Ekj8bG8W7X2nbx2CpF)
  --tokens-file TOKENS_FILE, -t TOKENS_FILE
                        Path to tokens JSON file
  --output-dir OUTPUT_DIR, -o OUTPUT_DIR
                        Directory to save output files
```

### Examples

```bash
# Fetch data for Daft Punk
python tests/test_spotify_api.py --artist-id 4tZwfgrHOc3mvqYlEYSvVi

# Specify a different tokens file
python tests/test_spotify_api.py -a 4tZwfgrHOc3mvqYlEYSvVi -t path/to/tokens.json

# Save output to a different directory
python tests/test_spotify_api.py -a 4tZwfgrHOc3mvqYlEYSvVi -o path/to/output/dir
```

## Output

The script will:

1. Log progress to both console and a log file (`spotify_api_test.log`)
2. Save the full API response to `tests/output/spotify_response.json`
3. Extract and display key metrics:
   - Name and basic info
   - Monthly listeners
   - Top cities with listener counts
   - Social media links
   - Upcoming concerts
