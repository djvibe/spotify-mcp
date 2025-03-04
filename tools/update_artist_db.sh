#!/bin/bash
# Script to fetch enhanced artist data and update the database

# Default values
ARTIST_ID="76M2Ekj8bG8W7X2nbx2CpF"  # NGHTMRE
DB_PATH="../spotify.db"
OUTPUT_DIR="../tests/output"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -a|--artist-id)
      ARTIST_ID="$2"
      shift 2
      ;;
    -d|--db-path)
      DB_PATH="$2"
      shift 2
      ;;
    -o|--output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "Fetching enhanced data for artist: $ARTIST_ID"

# Step 1: Fetch the enhanced data using our test script
python ../tests/test_spotify_api.py --artist-id "$ARTIST_ID" --output-dir "$OUTPUT_DIR"

# Check if the fetch was successful
if [ $? -ne 0 ]; then
  echo "Failed to fetch enhanced data for artist: $ARTIST_ID"
  exit 1
fi

METRICS_FILE="$OUTPUT_DIR/${ARTIST_ID}_metrics.json"
RESPONSE_FILE="$OUTPUT_DIR/${ARTIST_ID}_spotify_response.json"

# Check if the metrics file exists
if [ ! -f "$METRICS_FILE" ]; then
  echo "Metrics file not found: $METRICS_FILE"
  exit 1
fi

# Check if the response file exists
if [ ! -f "$RESPONSE_FILE" ]; then
  echo "Response file not found: $RESPONSE_FILE"
  exit 1
fi

echo "Successfully fetched enhanced data"
echo "Metrics file: $METRICS_FILE"
echo "Response file: $RESPONSE_FILE"

# Step 2: Update the database with the enhanced data
echo "Updating database with enhanced data..."
python update_artist_from_enhanced_data.py --artist-id "$ARTIST_ID" --db-path "$DB_PATH" --metrics-file "$METRICS_FILE" --response-file "$RESPONSE_FILE"

# Check if the update was successful
if [ $? -ne 0 ]; then
  echo "Failed to update database with enhanced data"
  exit 1
fi

echo "Successfully updated database with enhanced data for artist: $ARTIST_ID"
echo "Done!"
