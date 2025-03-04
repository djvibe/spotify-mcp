#!/usr/bin/env python3
import os
import sys
import json
import time
import sqlite3
import logging
import subprocess
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("batch_artist_update.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("batch_artist_update")

# Create a specific debug log file for Tiësto issues
tiesto_handler = logging.FileHandler("tiesto_debug.log")
tiesto_handler.setLevel(logging.DEBUG)
tiesto_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(tiesto_handler)

def get_artists_needing_update(db_path, update_threshold_days=None):
    """Get artists that need updating based on their tier and last update date"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if update_threshold_days is not None:
            # Use a fixed threshold for all artists
            query = f"""
                SELECT id, name, popularity, last_updated
                FROM artists
                WHERE last_updated < datetime('now', '-{update_threshold_days} days')
                OR last_updated IS NULL
                ORDER BY last_updated ASC
            """
        else:
            # Use tiered thresholds based on popularity
            query = """
                SELECT id, name, popularity, last_updated,
                    ROUND((JULIANDAY('now') - JULIANDAY(last_updated)) * 24 / 24, 1) as days_since_update,
                    CASE 
                        WHEN popularity >= 75 THEN 'Top Tier (3 days)'
                        WHEN popularity >= 50 THEN 'Mid Tier (7 days)'
                        ELSE 'Lower Tier (14 days)'
                    END as tier,
                    CASE 
                        WHEN popularity >= 75 AND last_updated < datetime('now', '-3 days') THEN 1
                        WHEN popularity >= 50 AND popularity < 75 AND last_updated < datetime('now', '-7 days') THEN 1
                        WHEN popularity < 50 AND last_updated < datetime('now', '-14 days') THEN 1
                        WHEN last_updated IS NULL THEN 1
                        ELSE 0
                    END as needs_update
                FROM artists
                WHERE needs_update = 1
                ORDER BY popularity DESC, last_updated ASC
            """
        
        cursor.execute(query)
        artists = cursor.fetchall()
        conn.close()
        
        if update_threshold_days is not None:
            # Format a simple result with id, name, popularity, last_updated
            return [(row[0], row[1], row[2], row[3]) for row in artists]
        else:
            # Format result with id, name, popularity, last_updated, days_since, tier, needs_update
            return [(row[0], row[1], row[2], row[3], row[4], row[5], row[6]) for row in artists]
            
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Error getting artists: {str(e)}")
        return []

def fetch_enhanced_artist_data(artist_id, output_dir):
    """Run the test script to fetch enhanced artist data"""
    try:
        # Get the path to the test script
        test_script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                       "tests", "test_spotify_api.py")
        
        # Run the test script
        command = [
            sys.executable,
            test_script_path,
            "--artist-id", artist_id,
            "--output-dir", output_dir
        ]
        
        logger.info(f"Fetching enhanced data for artist {artist_id}")
        logger.debug(f"Running command: {' '.join(command)}")
        
        process = subprocess.run(command, capture_output=True, text=True)
        
        if process.returncode != 0:
            logger.error(f"Error fetching enhanced data for artist {artist_id}: {process.stderr}")
            logger.error(f"Process stdout: {process.stdout[:1000]}")
            return False
        
        # Check if the output files exist
        metrics_file = os.path.join(output_dir, f"{artist_id}_metrics.json")
        response_file = os.path.join(output_dir, f"{artist_id}_spotify_response.json")
        
        logger.debug(f"Checking for output files: {metrics_file} and {response_file}")
        
        if not os.path.exists(metrics_file):
            logger.error(f"Metrics file not found for artist {artist_id}: {metrics_file}")
            return False
            
        if not os.path.exists(response_file):
            logger.error(f"Response file not found for artist {artist_id}: {response_file}")
            return False
            
        # Verify the JSON files can be parsed
        try:
            with open(metrics_file, 'r') as f:
                metrics_data = json.load(f)
            logger.debug(f"Successfully loaded metrics file for {artist_id}")
            
            # Check for empty or invalid data
            if not metrics_data or not isinstance(metrics_data, dict):
                logger.error(f"Invalid metrics data for artist {artist_id}: {metrics_data}")
                return False
                
            # Check for required fields
            required_fields = ["name", "monthly_listeners", "followers"]
            missing_fields = [field for field in required_fields if field not in metrics_data]
            
            if missing_fields:
                logger.error(f"Missing required fields in metrics data for artist {artist_id}: {missing_fields}")
                return False
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in metrics file for artist {artist_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error checking metrics file for artist {artist_id}: {str(e)}")
            return False
            
        logger.info(f"Successfully fetched enhanced data for artist {artist_id}")
        return True
    
    except Exception as e:
        logger.error(f"Error fetching enhanced data for artist {artist_id}: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return False

def update_artist_in_database(artist_id, db_path, metrics_file, response_file):
    """Run the update script to update the artist in the database"""
    try:
        # Get the path to the update script
        update_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                         "update_artist_from_enhanced_data.py")
        
        # Run the update script
        command = [
            sys.executable,
            update_script_path,
            "--artist-id", artist_id,
            "--db-path", db_path,
            "--metrics-file", metrics_file,
            "--response-file", response_file
        ]
        
        logger.info(f"Updating database for artist {artist_id}")
        process = subprocess.run(command, capture_output=True, text=True)
        
        if process.returncode != 0:
            logger.error(f"Error updating database for artist {artist_id}: {process.stderr}")
            return False
            
        logger.info(f"Successfully updated database for artist {artist_id}")
        return True
    
    except Exception as e:
        logger.error(f"Error updating database for artist {artist_id}: {str(e)}")
        return False

def process_artist(artist_info, db_path, output_dir, delay=1):
    """Process a single artist"""
    artist_id = artist_info[0]
    artist_name = artist_info[1]
    
    try:
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Step 1: Fetch enhanced data
        if not fetch_enhanced_artist_data(artist_id, output_dir):
            return False, artist_id, artist_name, "Failed to fetch enhanced data"
        
        # Add a small delay to avoid rate limiting
        time.sleep(delay)
        
        # Step 2: Update the database
        metrics_file = os.path.join(output_dir, f"{artist_id}_metrics.json")
        response_file = os.path.join(output_dir, f"{artist_id}_spotify_response.json")
        
        if not update_artist_in_database(artist_id, db_path, metrics_file, response_file):
            return False, artist_id, artist_name, "Failed to update database"
        
        return True, artist_id, artist_name, "Successfully updated"
    
    except Exception as e:
        logger.error(f"Error processing artist {artist_name} ({artist_id}): {str(e)}")
        return False, artist_id, artist_name, str(e)

def batch_update_artists(artist_list, db_path, output_dir, max_workers=3, delay=1):
    """Update multiple artists with enhanced data"""
    results = {
        "successful": [],
        "failed": [],
        "errors": {}
    }
    
    logger.info(f"Starting batch update for {len(artist_list)} artists")
    
    start_time = time.time()
    
    # Process artists in parallel with a thread pool
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_artist = {
            executor.submit(process_artist, artist, db_path, output_dir, delay): artist
            for artist in artist_list
        }
        
        for future in as_completed(future_to_artist):
            artist = future_to_artist[future]
            artist_id = artist[0]
            artist_name = artist[1]
            
            try:
                success, id, name, message = future.result()
                if success:
                    results["successful"].append((id, name))
                    logger.info(f"Successfully processed artist: {name} ({id})")
                else:
                    results["failed"].append((id, name))
                    results["errors"][id] = message
                    logger.error(f"Failed to process artist: {name} ({id}) - {message}")
            
            except Exception as e:
                results["failed"].append((artist_id, artist_name))
                results["errors"][artist_id] = str(e)
                logger.error(f"Exception processing artist: {artist_name} ({artist_id}) - {str(e)}")
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Generate summary
    results["total"] = len(artist_list)
    results["successful_count"] = len(results["successful"])
    results["failed_count"] = len(results["failed"])
    results["duration_seconds"] = duration
    
    logger.info(f"Batch update completed in {duration:.2f} seconds")
    logger.info(f"Successfully updated {results['successful_count']} out of {results['total']} artists")
    
    if results["failed_count"] > 0:
        logger.info(f"Failed to update {results['failed_count']} artists")
    
    return results

def save_results(results, output_file):
    """Save batch update results to a JSON file"""
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")
        return False

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Batch update artists with enhanced data from Spotify")
    
    # Artist selection options (mutually exclusive)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--artist-ids", "-a", help="Comma-separated list of Spotify artist IDs")
    group.add_argument("--file", "-f", help="File containing Spotify artist IDs (one per line)")
    group.add_argument("--all-artists", "-all", action="store_true", help="Process all artists in the database")
    group.add_argument("--needs-update", "-n", action="store_true", help="Process artists that need updates based on their tier")
    group.add_argument("--days", "-d", type=int, help="Process artists not updated in the specified number of days")
    
    # Other options
    parser.add_argument("--db-path", required=True, help="Path to SQLite database file")
    parser.add_argument("--output-dir", help="Directory to save output files", 
                        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "output"))
    parser.add_argument("--max-workers", "-w", type=int, default=3, help="Maximum number of concurrent workers")
    parser.add_argument("--delay", type=int, default=1, help="Delay between API requests in seconds")
    parser.add_argument("--limit", "-l", type=int, help="Limit the number of artists to process")
    
    args = parser.parse_args()
    
    # Get list of artists to process
    artist_list = []
    
    if args.artist_ids:
        # Process specific artist IDs
        artist_ids = [id.strip() for id in args.artist_ids.split(",")]
        
        # Connect to database to get artist info
        try:
            conn = sqlite3.connect(args.db_path)
            cursor = conn.cursor()
            
            for artist_id in artist_ids:
                cursor.execute("SELECT id, name, popularity, last_updated FROM artists WHERE id = ?", (artist_id,))
                result = cursor.fetchone()
                
                if result:
                    artist_list.append(result)
                else:
                    logger.warning(f"Artist with ID {artist_id} not found in database")
            
            conn.close()
        
        except sqlite3.Error as e:
            logger.error(f"Database error: {str(e)}")
            return 1
    
    elif args.file:
        # Read artist IDs from file
        try:
            with open(args.file, 'r') as f:
                artist_ids = [line.strip() for line in f if line.strip()]
            
            # Connect to database to get artist info
            conn = sqlite3.connect(args.db_path)
            cursor = conn.cursor()
            
            for artist_id in artist_ids:
                cursor.execute("SELECT id, name, popularity, last_updated FROM artists WHERE id = ?", (artist_id,))
                result = cursor.fetchone()
                
                if result:
                    artist_list.append(result)
                else:
                    logger.warning(f"Artist with ID {artist_id} not found in database")
            
            conn.close()
        
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            return 1
    
    elif args.all_artists:
        # Process all artists in the database
        try:
            conn = sqlite3.connect(args.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, popularity, last_updated FROM artists ORDER BY popularity DESC")
            artist_list = cursor.fetchall()
            conn.close()
        
        except sqlite3.Error as e:
            logger.error(f"Database error: {str(e)}")
            return 1
    
    elif args.needs_update:
        # Process artists that need updates based on their tier
        artist_list = get_artists_needing_update(args.db_path)
        # Convert the list to just include the fields we need
        artist_list = [(row[0], row[1], row[2], row[3]) for row in artist_list]
    
    elif args.days is not None:
        # Process artists not updated in the specified number of days
        artist_list = get_artists_needing_update(args.db_path, args.days)
    
    # Apply limit if specified
    if args.limit and len(artist_list) > args.limit:
        logger.info(f"Limiting to {args.limit} artists out of {len(artist_list)}")
        artist_list = artist_list[:args.limit]
    
    if not artist_list:
        logger.warning("No artists to process")
        return 0
    
    logger.info(f"Found {len(artist_list)} artists to process")
    
    # Process the artists
    results = batch_update_artists(
        artist_list, 
        args.db_path, 
        args.output_dir, 
        max_workers=args.max_workers,
        delay=args.delay
    )
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(args.output_dir, f"batch_update_results_{timestamp}.json")
    save_results(results, results_file)
    
    # Print summary
    print("\nBatch Update Summary:")
    print(f"Total Artists: {results['total']}")
    print(f"Successful: {results['successful_count']}")
    print(f"Failed: {results['failed_count']}")
    print(f"Duration: {results['duration_seconds']:.2f} seconds")
    
    if results["failed_count"] > 0:
        print("\nFailed Artists:")
        for artist_id, artist_name in results["failed"]:
            error = results["errors"].get(artist_id, "Unknown error")
            print(f"  - {artist_name} ({artist_id}): {error}")
    
    return 0 if results["failed_count"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
