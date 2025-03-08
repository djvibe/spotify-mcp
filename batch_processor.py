import logging
import json
import os
import asyncio
import sys
import glob
import time
from pathlib import Path
from datetime import datetime
import argparse
import sqlite3
import traceback

# Import our modules
from spotify_token_manager import SpotifyTokenManager
from spotify_partner_api import SpotifyPartnerAPI

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("batch_processing.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("batch_processing")

class BatchProcessor:
    """Process multiple artists and update database with enhanced metrics"""
    
    def __init__(self, db_path, output_dir=None, max_workers=1, delay=1):
        """Initialize the batch processor"""
        self.db_path = db_path
        self.output_dir = output_dir or os.path.join(os.getcwd(), "output")
        self.max_workers = max_workers
        self.delay = delay
        
        # Create a single token manager to be shared
        token_path = os.path.join(self.output_dir, "batch_spotify_tokens.json")
        self.token_manager = SpotifyTokenManager(token_path)
        
        # Create SpotifyPartnerAPI instance with the shared token manager
        # Pass token_manager argument explicitly named
        self.api = SpotifyPartnerAPI(token_manager=self.token_manager)
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Verify token health at startup
        self._check_token_health()
    
    def _check_token_health(self):
        """Check and log token health status"""
        try:
            health = self.token_manager.check_token_health()
            if health["has_token"]:
                if health["token_valid"]:
                    logger.info(f"Token is valid for {health['time_remaining_sec']} more seconds")
                else:
                    logger.warning("Token exists but is no longer valid, will refresh when needed")
            else:
                logger.info("No token loaded, will retrieve when needed")
        except Exception as e:
            logger.error(f"Error checking token health: {str(e)}")
    
    async def get_artists_needing_update(self, limit=None):
        """Get artists that need updates based on tier"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = """
            SELECT 
                id, name, popularity, 
                COALESCE(enhanced_data_updated, '1970-01-01') as enhanced_data_updated,
                CASE 
                    WHEN popularity >= 75 THEN 'Top Tier (3 days)'
                    WHEN popularity >= 50 THEN 'Mid Tier (7 days)'
                    ELSE 'Lower Tier (14 days)'
                END as tier
            FROM artists
            WHERE 
                (popularity >= 75 AND (enhanced_data_updated IS NULL OR enhanced_data_updated < datetime('now', '-3 days')))
                OR (popularity >= 50 AND popularity < 75 AND (enhanced_data_updated IS NULL OR enhanced_data_updated < datetime('now', '-7 days')))
                OR (popularity < 50 AND (enhanced_data_updated IS NULL OR enhanced_data_updated < datetime('now', '-14 days')))
            ORDER BY 
                CASE 
                    WHEN popularity >= 75 THEN 1
                    WHEN popularity >= 50 THEN 2
                    ELSE 3
                END,
                popularity DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
                
            cursor.execute(query)
            artists = cursor.fetchall()
            conn.close()
            
            # Format as list of dictionaries
            result = []
            for row in artists:
                result.append({
                    "id": row[0],
                    "name": row[1],
                    "popularity": row[2],
                    "enhanced_data_updated": row[3],
                    "tier": row[4]
                })
                
            return result
                
        except sqlite3.Error as e:
            logger.error(f"Database error: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error getting artists: {str(e)}")
            return []
    
    async def process_artist(self, artist_id, artist_name=None):
        """Process a single artist"""
        try:
            logger.info(f"Processing artist ID: {artist_id} {f'({artist_name})' if artist_name else ''}")
            
            # Get enhanced artist data
            artist_data = self.api.get_artist_details(artist_id)
            
            if not artist_data:
                logger.error(f"Failed to get data for artist ID: {artist_id}")
                return {"success": False, "error": "Failed to retrieve artist data"}
            
            # Extract metrics
            metrics = self.api.extract_artist_metrics(artist_data)
            
            if not metrics:
                logger.error(f"Failed to extract metrics for artist ID: {artist_id}")
                return {"success": False, "error": "Failed to extract metrics"}
            
            # Save data to files
            self.save_artist_data(artist_id, artist_data, metrics)
            
            # Update database
            success = self.update_database(artist_id, metrics)
            
            return {
                "success": success,
                "metrics": metrics,
                "error": None if success else "Database update failed"
            }
            
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"Error processing artist {artist_id}: {str(e)}\n{error_details}")
            return {"success": False, "error": str(e)}
    
    def save_artist_data(self, artist_id, artist_data, metrics):
        """Save artist data to output files"""
        try:
            # Create timestamp for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save full API response
            response_file = os.path.join(self.output_dir, f"{artist_id}_response_{timestamp}.json")
            with open(response_file, "w") as f:
                json.dump(artist_data, f, indent=2)
            
            # Save extracted metrics
            metrics_file = os.path.join(self.output_dir, f"{artist_id}_metrics_{timestamp}.json")
            with open(metrics_file, "w") as f:
                json.dump(metrics, f, indent=2)
                
            logger.info(f"Saved data files for artist {artist_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving data files: {str(e)}")
            return False
    
    def update_database(self, artist_id, metrics):
        """Update the database with the enhanced metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert social links to JSON
            social_links_json = json.dumps(metrics.get("social_links", {}))
            
            # Count upcoming tours
            upcoming_tours_count = len(metrics.get("upcoming_concerts", []))
            
            # Convert upcoming tours to JSON
            upcoming_tours_json = json.dumps({
                "total_count": upcoming_tours_count,
                "dates": metrics.get("upcoming_concerts", [])
            })
            
            # Get current data_sources if they exist
            cursor.execute("SELECT data_sources FROM artists WHERE id = ?", (artist_id,))
            row = cursor.fetchone()
            
            # Parse data sources or create new ones
            data_sources = {}
            if row and row[0]:
                try:
                    data_sources = json.loads(row[0])
                except:
                    data_sources = {}
            
            # Mark these fields as coming from Partner API
            data_sources['monthly_listeners'] = 'partner_api'
            data_sources['social_links_json'] = 'partner_api'
            data_sources['upcoming_tours_count'] = 'partner_api'
            data_sources['upcoming_tours_json'] = 'partner_api'
            data_sources['enhanced_data_updated'] = 'partner_api'
            
            # Update the artist record
            cursor.execute("""
                UPDATE artists SET
                    monthly_listeners = ?,
                    social_links_json = ?,
                    upcoming_tours_count = ?,
                    upcoming_tours_json = ?,
                    data_sources = ?,
                    enhanced_data_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                metrics.get("monthly_listeners"),
                social_links_json,
                upcoming_tours_count,
                upcoming_tours_json,
                json.dumps(data_sources),
                artist_id
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Database updated for artist {artist_id} with Partner API data")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Database error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error updating database: {str(e)}")
            return False
    
    def cleanup_output_files(self, successful_artist_ids):
        """
        Clean up JSON output files after successful processing
        
        Args:
            successful_artist_ids: List of artist IDs that were successfully processed
        """
        try:
            logger.info(f"Cleaning up output files for {len(successful_artist_ids)} successfully processed artists")
            
            cleaned_response_files = 0
            cleaned_metrics_files = 0
            errors = 0
            
            # Immediate cleanup for response and metrics files of successful artists
            for artist_id in successful_artist_ids:
                try:
                    # Find all response and metrics files for this artist
                    response_pattern = os.path.join(self.output_dir, f"{artist_id}_response_*.json")
                    metrics_pattern = os.path.join(self.output_dir, f"{artist_id}_metrics_*.json")
                    
                    # Delete response files (larger files)
                    for filepath in glob.glob(response_pattern):
                        os.remove(filepath)
                        cleaned_response_files += 1
                    
                    # Delete metrics files
                    for filepath in glob.glob(metrics_pattern):
                        os.remove(filepath)
                        cleaned_metrics_files += 1
                        
                except Exception as e:
                    logger.error(f"Error cleaning up files for artist {artist_id}: {str(e)}")
                    errors += 1
            
            # For batch results files, only clean up old ones (older than 7 days)
            batch_pattern = os.path.join(self.output_dir, "batch_results_*.json")
            cutoff_time = time.time() - (7 * 24 * 60 * 60)  # 7 days
            cleaned_batch_files = 0
            
            for filepath in glob.glob(batch_pattern):
                try:
                    file_stats = os.stat(filepath)
                    if file_stats.st_mtime < cutoff_time:
                        os.remove(filepath)
                        cleaned_batch_files += 1
                except Exception as e:
                    logger.error(f"Error cleaning up batch file {filepath}: {str(e)}")
                    errors += 1
            
            logger.info(f"Cleanup complete: {cleaned_response_files} response files and {cleaned_metrics_files} metrics files removed, {cleaned_batch_files} old batch files removed, {errors} errors")
            
        except Exception as e:
            logger.error(f"Error during output file cleanup: {str(e)}")
    
    async def process_batch(self, artist_list):
        """Process a batch of artists with controlled concurrency"""
        results = {
            "successful": [],
            "failed": [],
            "errors": {},
            "total": len(artist_list),
            "success_count": 0,
            "failure_count": 0,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "stopped_early": False,
            "stop_reason": None
        }
        
        # Check token health before starting
        try:
            token = self.token_manager.get_token()
            if not token:
                results["stopped_early"] = True
                results["stop_reason"] = "Failed to retrieve a valid token before starting batch"
                logger.error("Batch processing aborted: Could not retrieve a valid token")
                results["end_time"] = datetime.now().isoformat()
                return results
        except Exception as e:
            results["stopped_early"] = True
            results["stop_reason"] = f"Token error before starting batch: {str(e)}"
            logger.error(f"Batch processing aborted: Token error: {str(e)}")
            results["end_time"] = datetime.now().isoformat()
            return results
        
        # Process based on concurrency settings
        try:
            if self.max_workers > 1:
                # Process with concurrency
                tasks = []
                semaphore = asyncio.Semaphore(self.max_workers)
                stop_processing = asyncio.Event()
                
                async def process_with_semaphore(artist):
                    if stop_processing.is_set():
                        return artist['id'], {"success": False, "error": "Batch processing was stopped due to token error"}
                    
                    async with semaphore:
                        try:
                            # Process and add delay
                            result = await self.process_artist(artist['id'], artist.get('name'))
                            await asyncio.sleep(self.delay)
                            return artist['id'], result
                        except Exception as e:
                            if "token" in str(e).lower():
                                stop_processing.set()
                                logger.error(f"Stopping batch due to token error: {str(e)}")
                                return artist['id'], {"success": False, "error": f"Token error: {str(e)}"}
                            return artist['id'], {"success": False, "error": str(e)}
                
                # Create tasks
                for artist in artist_list:
                    tasks.append(asyncio.create_task(process_with_semaphore(artist)))
                
                # Wait for all tasks to complete
                for completed_task in asyncio.as_completed(tasks):
                    try:
                        artist_id, result = await completed_task
                        
                        if result['success']:
                            results['successful'].append(artist_id)
                            results['success_count'] += 1
                        else:
                            results['failed'].append(artist_id)
                            results['errors'][artist_id] = result['error']
                            results['failure_count'] += 1
                            
                            # Check if processing should stop due to token error
                            if "token" in str(result.get('error', '')).lower():
                                stop_processing.set()
                                results["stopped_early"] = True
                                results["stop_reason"] = f"Token error: {result.get('error')}"
                                logger.warning(f"Stopping batch processing due to token error: {result.get('error')}")
                    except Exception as e:
                        logger.error(f"Error handling task result: {str(e)}")
            else:
                # Process sequentially
                for artist in artist_list:
                    try:
                        result = await self.process_artist(artist['id'], artist.get('name'))
                        await asyncio.sleep(self.delay)
                        
                        if result['success']:
                            results['successful'].append(artist['id'])
                            results['success_count'] += 1
                        else:
                            results['failed'].append(artist['id'])
                            results['errors'][artist['id']] = result['error']
                            results['failure_count'] += 1
                            
                            # Check if processing should stop due to token error
                            if "token" in str(result.get('error', '')).lower():
                                results["stopped_early"] = True
                                results["stop_reason"] = f"Token error: {result.get('error')}"
                                logger.warning(f"Stopping batch processing due to token error: {result.get('error')}")
                                break
                    except Exception as e:
                        # Handle unexpected errors
                        results['failed'].append(artist['id'])
                        results['errors'][artist['id']] = str(e)
                        results['failure_count'] += 1
                        
                        # Stop batch on token errors
                        if "token" in str(e).lower():
                            results["stopped_early"] = True
                            results["stop_reason"] = f"Token error: {str(e)}"
                            logger.warning(f"Stopping batch processing due to token error: {str(e)}")
                            break
        except Exception as e:
            # Handle unexpected batch processing errors
            logger.error(f"Unexpected error in batch processing: {str(e)}")
            results["stopped_early"] = True
            results["stop_reason"] = f"Batch error: {str(e)}"
        
        # Clean up files for successfully processed artists
        if results['success_count'] > 0:
            self.cleanup_output_files(results['successful'])
        
        # Update end time
        results['end_time'] = datetime.now().isoformat()
        
        return results

async def main():
    """Main entry point for the batch processor"""
    parser = argparse.ArgumentParser(description="Process artists with enhanced Spotify data")
    
    # Database options
    parser.add_argument("--db-path", required=True, help="Path to SQLite database file")
    
    # Selection options (choose one)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--artist-ids", help="Comma-separated list of artist IDs")
    group.add_argument("--file", help="File containing artist IDs (one per line)")
    group.add_argument("--needs-update", action="store_true", help="Process artists needing updates")
    group.add_argument("--days", type=int, help="Process artists not updated in this many days")
    
    # Processing options
    parser.add_argument("--output-dir", help="Directory for output files", default="output")
    parser.add_argument("--max-workers", "-w", type=int, default=1, help="Maximum concurrent workers")
    parser.add_argument("--delay", type=float, default=1, help="Delay between API requests in seconds")
    parser.add_argument("--limit", "-l", type=int, help="Limit the number of artists to process")
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = BatchProcessor(
        db_path=args.db_path,
        output_dir=args.output_dir,
        max_workers=args.max_workers,
        delay=args.delay
    )
    
    # Get artist list based on selection method
    artists_to_process = []
    
    if args.artist_ids:
        # Parse comma-separated IDs
        ids = [id.strip() for id in args.artist_ids.split(",")]
        
        # Get basic info from database
        conn = sqlite3.connect(args.db_path)
        cursor = conn.cursor()
        
        for artist_id in ids:
            cursor.execute("SELECT id, name, popularity FROM artists WHERE id = ?", (artist_id,))
            row = cursor.fetchone()
            
            if row:
                artists_to_process.append({
                    "id": row[0],
                    "name": row[1],
                    "popularity": row[2],
                    "enhanced_data_updated": None,
                    "tier": "Manual Selection"
                })
            else:
                logger.warning(f"Artist ID not found in database: {artist_id}")
        
        conn.close()
        
    elif args.file:
        # Read IDs from file
        with open(args.file, "r") as f:
            ids = [line.strip() for line in f if line.strip()]
        
        # Get info from database
        conn = sqlite3.connect(args.db_path)
        cursor = conn.cursor()
        
        for artist_id in ids:
            cursor.execute("SELECT id, name, popularity FROM artists WHERE id = ?", (artist_id,))
            row = cursor.fetchone()
            
            if row:
                artists_to_process.append({
                    "id": row[0],
                    "name": row[1],
                    "popularity": row[2],
                    "enhanced_data_updated": None,
                    "tier": "File Selection"
                })
            else:
                logger.warning(f"Artist ID not found in database: {artist_id}")
        
        conn.close()
        
    elif args.needs_update:
        # Get artists needing updates based on tier
        artists_to_process = await processor.get_artists_needing_update(args.limit)
        
    elif args.days:
        # Get artists not updated in specified days
        conn = sqlite3.connect(args.db_path)
        cursor = conn.cursor()
        
        query = f"""
        SELECT id, name, popularity 
        FROM artists
        WHERE enhanced_data_updated IS NULL OR enhanced_data_updated < datetime('now', '-{args.days} days')
        ORDER BY popularity DESC
        """
        
        if args.limit:
            query += f" LIMIT {args.limit}"
            
        cursor.execute(query)
        rows = cursor.fetchall()
        
        for row in rows:
            artists_to_process.append({
                "id": row[0],
                "name": row[1],
                "popularity": row[2],
                "enhanced_data_updated": None,
                "tier": f"Not updated in {args.days} days"
            })
            
        conn.close()
    
    # Apply limit if specified
    if args.limit and len(artists_to_process) > args.limit:
        artists_to_process = artists_to_process[:args.limit]
    
    # Log info about the batch
    logger.info(f"Starting batch process for {len(artists_to_process)} artists")
    
    if artists_to_process:
        # Group by tier for logging
        tiers = {}
        for artist in artists_to_process:
            tier = artist.get('tier', 'Unknown')
            if tier not in tiers:
                tiers[tier] = 0
            tiers[tier] += 1
        
        for tier, count in tiers.items():
            logger.info(f"  {tier}: {count} artists")
        
        # Log first few artists
        if len(artists_to_process) > 0:
            logger.info("Artists to process (first 5):")
            for artist in artists_to_process[:5]:
                logger.info(f"  {artist['name']} ({artist['id']})")
            
            if len(artists_to_process) > 5:
                logger.info(f"  ... and {len(artists_to_process) - 5} more")
        
        # Process the batch
        results = await processor.process_batch(artists_to_process)
        
        # Log results
        if results.get("stopped_early"):
            logger.warning(f"Batch processing stopped early: {results.get('stop_reason')}")
            logger.info(f"Partial results: {results['success_count']} succeeded, {results['failure_count']} failed, {len(artists_to_process) - results['success_count'] - results['failure_count']} not processed")
        else:
            logger.info(f"Batch processing complete: {results['success_count']} succeeded, {results['failure_count']} failed")
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(args.output_dir, f"batch_results_{timestamp}.json")
        
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"Results saved to {results_file}")
        
        return 0
    else:
        logger.info("No artists to process")
        return 0

if __name__ == "__main__":
    asyncio.run(main())
