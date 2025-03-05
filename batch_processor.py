import logging
import json
import os
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import argparse
import sqlite3

# Import our new modules
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
        
        # Create SpotifyPartnerAPI instance with automatic token management
        token_path = os.path.join(self.output_dir, "batch_spotify_tokens.json")
        self.api = SpotifyPartnerAPI(token_path)
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
    
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
            logger.error(f"Error processing artist {artist_id}: {str(e)}")
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
            
            # Update the artist record
            cursor.execute("""
                UPDATE artists SET
                    monthly_listeners = ?,
                    social_links_json = ?,
                    upcoming_tours_count = ?,
                    upcoming_tours_json = ?,
                    enhanced_data_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                metrics.get("monthly_listeners"),
                social_links_json,
                upcoming_tours_count,
                upcoming_tours_json,
                artist_id
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Database updated for artist {artist_id}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Database error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error updating database: {str(e)}")
            return False
    
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
            "end_time": None
        }
        
        if self.max_workers > 1:
            # Process with concurrency
            tasks = []
            semaphore = asyncio.Semaphore(self.max_workers)
            
            async def process_with_semaphore(artist):
                async with semaphore:
                    # Process and add delay
                    result = await self.process_artist(artist['id'], artist.get('name'))
                    await asyncio.sleep(self.delay)
                    return artist['id'], result
            
            # Create tasks
            for artist in artist_list:
                tasks.append(asyncio.create_task(process_with_semaphore(artist)))
            
            # Wait for all tasks to complete
            for completed_task in asyncio.as_completed(tasks):
                artist_id, result = await completed_task
                
                if result['success']:
                    results['successful'].append(artist_id)
                    results['success_count'] += 1
                else:
                    results['failed'].append(artist_id)
                    results['errors'][artist_id] = result['error']
                    results['failure_count'] += 1
        else:
            # Process sequentially
            for artist in artist_list:
                result = await self.process_artist(artist['id'], artist.get('name'))
                await asyncio.sleep(self.delay)
                
                if result['success']:
                    results['successful'].append(artist['id'])
                    results['success_count'] += 1
                else:
                    results['failed'].append(artist['id'])
                    results['errors'][artist['id']] = result['error']
                    results['failure_count'] += 1
        
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
