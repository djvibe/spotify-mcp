#!/usr/bin/env python3
"""
DJVIBE Spotify MCP - Update All Artists Tool
This script identifies all artists needing updates and processes them in batches.
"""
import os
import sys
import json
import time
import logging
import sqlite3
import asyncio
import argparse
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("update_all_artists.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("update_all_artists")

# Import the batch_artist_update functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from batch_artist_update import (
    connect_db, 
    batch_update_artists,
    get_artists_needing_update
)

async def main():
    """Main function for the update all artists tool."""
    parser = argparse.ArgumentParser(description="Update all artists needing updates in the DJVIBE Spotify MCP")
    
    # Configuration
    parser.add_argument("--config", "-c", default="D:\\DJVIBE\\MCP\\spotify-mcp\\config.json", 
                       help="Path to configuration file (default: D:\\DJVIBE\\MCP\\spotify-mcp\\config.json)")
    
    # Batch size and processing options
    parser.add_argument("--batch-size", "-b", type=int, default=10, 
                       help="Number of artists to update in each batch (default: 10)")
    parser.add_argument("--concurrency", "-cc", type=int, default=3, 
                       help="Maximum number of concurrent updates (default: 3)")
    parser.add_argument("--delay", "-d", type=float, default=0.5, 
                       help="Delay between API requests in seconds (default: 0.5)")
    
    # Update options
    parser.add_argument("--standard-only", "-s", action="store_true", 
                       help="Only update with standard API")
    parser.add_argument("--partner-only", "-p", action="store_true", 
                       help="Only update with Partner API")
    parser.add_argument("--dry-run", "-dr", action="store_true", 
                       help="Don't actually update, just show what would be updated")
    
    # Tier filtering
    parser.add_argument("--top-tier-only", "-t", action="store_true", 
                       help="Only update top tier artists (popularity >= 75)")
    parser.add_argument("--mid-tier-only", "-m", action="store_true", 
                       help="Only update mid tier artists (popularity 50-74)")
    parser.add_argument("--lower-tier-only", "-l", action="store_true", 
                       help="Only update lower tier artists (popularity < 50)")
    
    # Total limit
    parser.add_argument("--limit", type=int, 
                       help="Maximum total number of artists to update")
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        with open(args.config, "r") as f:
            config = json.load(f)
            logger.info(f"Loaded configuration from {args.config}")
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        return 1
    
    # Extract configuration
    db_path = config.get("database", {}).get("path")
    if not db_path:
        logger.error("Database path not found in configuration")
        return 1
    
    client_id = config.get("standard_api", {}).get("client_id")
    client_secret = config.get("standard_api", {}).get("client_secret")
    redirect_uri = config.get("standard_api", {}).get("redirect_uri")
    
    tokens_file = config.get("partner_api", {}).get("tokens_file")
    if tokens_file and not os.path.isabs(tokens_file):
        tokens_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), tokens_file)
    
    # Connect to database
    conn = connect_db(db_path)
    if not conn:
        logger.error(f"Failed to connect to database: {db_path}")
        return 1
    
    # Determine which APIs to use
    use_standard = not args.partner_only
    use_partner = not args.standard_only
    
    # Get artists needing updates
    try:
        logger.info("Finding artists that need updates based on tier")
        artist_ids = get_artists_needing_update(conn, args.limit, args.standard_only, args.partner_only)
        
        # Filter by tier if specified
        if args.top_tier_only or args.mid_tier_only or args.lower_tier_only:
            # Get popularity values for artists
            artist_id_list = [f"'{aid}'" for aid in artist_ids]
            query = f"""
                SELECT id, popularity 
                FROM artists 
                WHERE id IN ({','.join(artist_id_list)})
            """
            cursor = conn.cursor()
            cursor.execute(query)
            artist_popularity = {row['id']: row['popularity'] for row in cursor.fetchall()}
            
            # Apply tier filters
            filtered_ids = []
            for aid in artist_ids:
                popularity = artist_popularity.get(aid, 0)
                
                if args.top_tier_only and popularity >= 75:
                    filtered_ids.append(aid)
                elif args.mid_tier_only and popularity >= 50 and popularity < 75:
                    filtered_ids.append(aid)
                elif args.lower_tier_only and popularity < 50:
                    filtered_ids.append(aid)
                elif not (args.top_tier_only or args.mid_tier_only or args.lower_tier_only):
                    filtered_ids.append(aid)
            
            artist_ids = filtered_ids
            logger.info(f"After tier filtering: {len(artist_ids)} artists to update")
        
        if not artist_ids:
            logger.info("No artists found needing updates")
            return 0
            
        logger.info(f"Found {len(artist_ids)} artists needing updates")
        
        # Apply limit if specified
        if args.limit and len(artist_ids) > args.limit:
            logger.info(f"Limiting updates to {args.limit} artists (from {len(artist_ids)} total)")
            artist_ids = artist_ids[:args.limit]
        
        # Create report file with initial data
        report_path = f"update_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_data = {
            "started_at": datetime.now().isoformat(),
            "total_artists": len(artist_ids),
            "batches": [],
            "settings": {
                "batch_size": args.batch_size,
                "concurrency": args.concurrency,
                "delay": args.delay,
                "standard_api": use_standard,
                "partner_api": use_partner,
                "dry_run": args.dry_run
            },
            "status": "in_progress",
            "summary": {
                "successful": 0,
                "failed": 0
            }
        }
        
        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=2)
            logger.info(f"Created report file: {report_path}")
            
        # Process in batches
        start_time = time.time()
        all_successful = []
        all_failed = []
        
        # Process in batches
        for i in range(0, len(artist_ids), args.batch_size):
            batch_number = i // args.batch_size + 1
            batch = artist_ids[i:i+args.batch_size]
            
            logger.info(f"Processing batch {batch_number}/{(len(artist_ids) + args.batch_size - 1) // args.batch_size}: {len(batch)} artists")
            
            batch_start = time.time()
            
            if args.dry_run:
                # Simulate successful update
                logger.info(f"DRY RUN: Would update {len(batch)} artists")
                batch_results = {
                    "successful": [(aid, "DRY RUN: Would update") for aid in batch],
                    "failed": [],
                    "total": len(batch)
                }
            else:
                # Actual update
                batch_results = await batch_update_artists(
                    batch, db_path, client_id, client_secret, redirect_uri, tokens_file,
                    use_standard, use_partner, args.concurrency, args.delay
                )
            
            # Track results
            all_successful.extend(batch_results["successful"])
            all_failed.extend(batch_results["failed"])
            
            # Update report file with batch data
            batch_data = {
                "batch_number": batch_number,
                "start_time": batch_start,
                "end_time": time.time(),
                "duration": time.time() - batch_start,
                "artists_count": len(batch),
                "successful": len(batch_results["successful"]),
                "failed": len(batch_results["failed"])
            }
            
            report_data["batches"].append(batch_data)
            report_data["summary"]["successful"] += len(batch_results["successful"])
            report_data["summary"]["failed"] += len(batch_results["failed"])
            
            with open(report_path, "w") as f:
                json.dump(report_data, f, indent=2)
                
            # Print batch summary
            logger.info(f"Batch {batch_number} complete: {len(batch_results['successful'])} successful, {len(batch_results['failed'])} failed")
            
            # Short pause between batches
            if i + args.batch_size < len(artist_ids):
                logger.info(f"Pausing for 5 seconds before next batch...")
                await asyncio.sleep(5)
        
        # Total elapsed time
        elapsed = time.time() - start_time
        
        # Update report with final status
        report_data["status"] = "completed"
        report_data["completed_at"] = datetime.now().isoformat()
        report_data["total_duration"] = elapsed
        
        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=2)
        
        # Print overall summary
        print(f"\nUpdate All Artists Complete!")
        print(f"Total Artists: {len(artist_ids)}")
        print(f"Successful: {len(all_successful)}")
        print(f"Failed: {len(all_failed)}")
        print(f"Total Duration: {elapsed:.2f} seconds")
        print(f"Average Time Per Artist: {elapsed / len(artist_ids):.2f} seconds")
        
        if all_failed:
            print("\nFailed Artists:")
            for artist_id, message in all_failed:
                print(f"  - {artist_id}: {message}")
                
        print(f"\nDetailed report saved to: {report_path}")
        
        return 0 if not all_failed else 1
        
    except Exception as e:
        logger.error(f"Error updating artists: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1
    finally:
        # Close database connection
        if conn:
            conn.close()

if __name__ == "__main__":
    asyncio.run(main())
