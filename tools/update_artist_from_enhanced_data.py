#!/usr/bin/env python3
import os
import sys
import json
import sqlite3
import argparse
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("artist_update.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("artist_update")

def load_metrics_file(file_path):
    """Load the metrics JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Metrics file not found: {file_path}")
        return None
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in metrics file: {file_path}")
        return None

def load_full_response_file(file_path):
    """Load the full Spotify response JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Response file not found: {file_path}")
        return None
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in response file: {file_path}")
        return None

def calculate_top_tracks_plays(full_data):
    """Calculate the total play count from top tracks"""
    try:
        top_tracks = full_data.get("data", {}).get("artistUnion", {}).get("discography", {}).get("topTracks", {}).get("items", [])
        total_plays = 0
        
        for track_item in top_tracks:
            track = track_item.get("track", {})
            playcount_str = track.get("playcount", "0")
            try:
                playcount = int(playcount_str)
                total_plays += playcount
            except ValueError:
                logger.warning(f"Invalid playcount: {playcount_str}")
                
        return total_plays
    except Exception as e:
        logger.error(f"Error calculating top tracks plays: {str(e)}")
        return 0

def create_artist_top_cities_table(conn):
    """Create the artist_top_cities table if it doesn't exist"""
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS artist_top_cities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id TEXT NOT NULL,
                city TEXT NOT NULL,
                country TEXT NOT NULL,
                region TEXT,
                listeners INTEGER NOT NULL,
                snapshot_date TIMESTAMP NOT NULL,
                FOREIGN KEY (artist_id) REFERENCES artists(id)
            )
        ''')
        
        # Create index on artist_id
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_top_cities_artist_id 
            ON artist_top_cities(artist_id)
        ''')
        
        conn.commit()
        logger.info("Created or verified artist_top_cities table")
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error creating top cities table: {str(e)}")
        return False

def update_artist_data(conn, artist_id, metrics, full_data):
    """Update the artist data in the database"""
    try:
        cursor = conn.cursor()
        
        # Check if artist exists
        cursor.execute("SELECT id FROM artists WHERE id = ?", (artist_id,))
        result = cursor.fetchone()
        
        if not result:
            logger.warning(f"Artist {artist_id} not found in database. Please add the artist first using the standard API.")
            return False
        
        # Calculate total plays from top tracks
        top_tracks_total_plays = calculate_top_tracks_plays(full_data)
        
        # Convert social links to JSON
        social_links_json = json.dumps(metrics.get("social_links", {}))
        
        # Count upcoming concerts
        upcoming_tours_count = len(metrics.get("upcoming_concerts", []))
        
        # Convert upcoming concerts to JSON
        upcoming_tours_json = json.dumps({
            "total_count": upcoming_tours_count,
            "dates": metrics.get("upcoming_concerts", [])
        }) if upcoming_tours_count > 0 else None
        
        # Update the artist record
        cursor.execute("""
            UPDATE artists SET
                monthly_listeners = ?,
                social_links_json = ?,
                top_tracks_total_plays = ?,
                upcoming_tours_count = ?,
                upcoming_tours_json = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            metrics.get("monthly_listeners"),
            social_links_json,
            top_tracks_total_plays,
            upcoming_tours_count,
            upcoming_tours_json,
            artist_id
        ))
        
        # Add a history record
        cursor.execute("""
            INSERT INTO artist_stats_history (
                artist_id, 
                snapshot_date, 
                popularity, 
                follower_count, 
                monthly_listeners,
                top_tracks_total_plays,
                upcoming_tours_count,
                upcoming_tours_json
            ) VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?)
        """, (
            artist_id,
            # Use existing popularity from the database
            cursor.execute("SELECT popularity FROM artists WHERE id = ?", (artist_id,)).fetchone()[0],
            metrics.get("followers"),
            metrics.get("monthly_listeners"),
            top_tracks_total_plays,
            upcoming_tours_count,
            upcoming_tours_json
        ))
        
        # Handle top cities
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # First delete existing entries for this artist to prevent duplicates
        cursor.execute("DELETE FROM artist_top_cities WHERE artist_id = ?", (artist_id,))
        
        # Insert new top cities data
        for city in metrics.get("top_cities", []):
            cursor.execute("""
                INSERT INTO artist_top_cities (
                    artist_id,
                    city,
                    country,
                    region,
                    listeners,
                    snapshot_date
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                artist_id,
                city.get("city"),
                city.get("country"),
                city.get("region"),
                city.get("listeners"),
                now
            ))
        
        conn.commit()
        
        logger.info(f"Updated artist {artist_id} with enhanced metrics")
        logger.info(f"Monthly Listeners: {metrics.get('monthly_listeners')}")
        logger.info(f"Followers: {metrics.get('followers')}")
        logger.info(f"Top Tracks Total Plays: {top_tracks_total_plays}")
        logger.info(f"Upcoming Tours: {upcoming_tours_count}")
        logger.info(f"Added {len(metrics.get('top_cities', []))} top cities")
        
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Database error updating artist data: {str(e)}")
        conn.rollback()
        return False
    except Exception as e:
        logger.error(f"Error updating artist data: {str(e)}")
        conn.rollback()
        return False

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Update artist data with enhanced metrics from Spotify")
    parser.add_argument("--artist-id", "-a", required=True, help="Spotify artist ID")
    parser.add_argument("--db-path", "-d", required=True, help="Path to SQLite database file")
    parser.add_argument("--metrics-file", "-m", help="Path to metrics JSON file (default: {artist_id}_metrics.json in current directory)")
    parser.add_argument("--response-file", "-r", help="Path to full response JSON file (default: {artist_id}_spotify_response.json in current directory)")
    
    args = parser.parse_args()
    
    artist_id = args.artist_id
    db_path = args.db_path
    
    # Set default paths if not specified
    tests_output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "output")
    metrics_file = args.metrics_file or os.path.join(tests_output_dir, f"{artist_id}_metrics.json")
    response_file = args.response_file or os.path.join(tests_output_dir, f"{artist_id}_spotify_response.json")
    
    # Load the metrics data
    metrics = load_metrics_file(metrics_file)
    if not metrics:
        logger.error(f"Failed to load metrics from {metrics_file}")
        return 1
    
    # Load the full response data
    full_data = load_full_response_file(response_file)
    if not full_data:
        logger.error(f"Failed to load full response from {response_file}")
        return 1
    
    # Connect to the database
    try:
        conn = sqlite3.connect(db_path)
        logger.info(f"Connected to database: {db_path}")
    except sqlite3.Error as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        return 1
    
    # Create the top cities table if it doesn't exist
    if not create_artist_top_cities_table(conn):
        conn.close()
        return 1
    
    # Update the artist data
    if not update_artist_data(conn, artist_id, metrics, full_data):
        conn.close()
        return 1
    
    # Close the database connection
    conn.close()
    logger.info("Successfully updated artist data")
    return 0

if __name__ == "__main__":
    sys.exit(main())
