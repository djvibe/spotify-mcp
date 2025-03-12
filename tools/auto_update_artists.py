#!/usr/bin/env python3
"""
DJVIBE Spotify MCP - Automated Artist Update
This script automatically identifies artists needing updates and processes them in one operation.
"""
import os
import sys
import json
import time
import logging
import sqlite3
import asyncio
import argparse
import subprocess
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("auto_update_artists.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("auto_update_artists")

def connect_db(db_path):
    """Connect to the SQLite database."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        logger.info(f"Connected to database: {db_path}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        return None

def get_artists_needing_update(conn, top_tier_only=False, mid_tier_only=False, lower_tier_only=False, 
                              standard_only=False, partner_only=False, limit=None):
    """Get artists that need updates based on their tier."""
    try:
        cursor = conn.cursor()
        
        # Base conditions for the WHERE clause
        where_clauses = []
        
        # Standard API update criteria if not partner-only
        if not partner_only:
            where_clauses.append("""
                (popularity >= 75 AND (last_updated IS NULL OR last_updated < datetime('now', '-3 days')))
                OR (popularity >= 50 AND popularity < 75 AND (last_updated IS NULL OR last_updated < datetime('now', '-7 days')))
                OR (popularity < 50 AND (last_updated IS NULL OR last_updated < datetime('now', '-14 days')))
            """)
        
        # Partner API update criteria if not standard-only
        if not standard_only:
            where_clauses.append("""
                (popularity >= 75 AND (enhanced_data_updated IS NULL OR enhanced_data_updated < datetime('now', '-7 days')))
                OR (popularity >= 50 AND popularity < 75 AND (enhanced_data_updated IS NULL OR enhanced_data_updated < datetime('now', '-14 days')))
                OR (popularity < 50 AND (enhanced_data_updated IS NULL OR enhanced_data_updated < datetime('now', '-30 days')))
            """)
        
        # Combine where clauses with OR
        where_clause = " OR ".join(f"({clause})" for clause in where_clauses)
        
        # Additional tier filtering if specified
        tier_filter = ""
        if top_tier_only:
            tier_filter = " AND popularity >= 75"
        elif mid_tier_only:
            tier_filter = " AND popularity >= 50 AND popularity < 75"
        elif lower_tier_only:
            tier_filter = " AND popularity < 50"
        
        # Combine with tier filter if needed
        if tier_filter:
            where_clause = f"({where_clause}){tier_filter}"
        
        # Build the complete query
        query = f"""
            SELECT id, name, popularity, last_updated, enhanced_data_updated,
                CASE 
                    WHEN popularity >= 75 THEN 'Top Tier'
                    WHEN popularity >= 50 THEN 'Mid Tier'
                    ELSE 'Lower Tier'
                END as tier
            FROM artists
            WHERE {where_clause}
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
        
        # Group by tier for reporting
        tiers = {"Top Tier": 0, "Mid Tier": 0, "Lower Tier": 0}
        artist_ids = []
        
        for artist in artists:
            artist_ids.append(artist['id'])
            tiers[artist['tier']] += 1
        
        # Log breakdown by tier
        logger.info(f"Found {len(artist_ids)} artists needing updates:")
        for tier, count in tiers.items():
            if count > 0:
                logger.info(f"  - {tier}: {count} artists")
        
        return artist_ids
            
    except Exception as e:
        logger.error(f"Error finding artists needing updates: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []

async def main():
    """Main function for the automated artist update tool."""
    parser = argparse.ArgumentParser(description="Automated artist update tool for DJVIBE Spotify MCP")
    
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
    
    # Extract database path
    db_path = config.get("database", {}).get("path")
    if not db_path:
        logger.error("Database path not found in configuration")
        return 1
    
    # Connect to database
    conn = connect_db(db_path)
    if not conn:
        logger.error(f"Failed to connect to database: {db_path}")
        return 1
    
    # Get artists needing updates
    try:
        logger.info("Finding artists that need updates based on tier")
        artists_to_update = get_artists_needing_update(
            conn, 
            args.top_tier_only, 
            args.mid_tier_only, 
            args.lower_tier_only,
            args.standard_only,
            args.partner_only,
            args.limit
        )
        
        if not artists_to_update:
            logger.info("No artists found needing updates")
            return 0
            
        logger.info(f"Found {len(artists_to_update)} artists needing updates")
        
        # Create a temporary file for artist IDs
        temp_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_artists_to_update.txt")
        try:
            with open(temp_file, "w") as f:
                for artist_id in artists_to_update:
                    f.write(f"{artist_id}\n")
            logger.info(f"Wrote {len(artists_to_update)} artist IDs to temporary file: {temp_file}")
            
            # Prepare the batch_artist_update.py command
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "batch_artist_update.py")
            
            cmd = [
                sys.executable,
                script_path,
                "--file", temp_file,
                "--config", args.config,
                "--concurrency", str(args.concurrency),
                "--delay", str(args.delay)
            ]
            
            if args.standard_only:
                cmd.append("--standard-only")
            if args.partner_only:
                cmd.append("--partner-only")
            if args.dry_run:
                logger.info("DRY RUN: Would have executed the following command:")
                logger.info(" ".join(cmd))
                return 0
            
            # Execute the batch_artist_update.py script
            logger.info(f"Executing batch artist update: {' '.join(cmd)}")
            start_time = time.time()
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Stream and log output in real-time
            for line in process.stdout:
                line = line.strip()
                if line:
                    logger.info(f"BATCH: {line}")
                    print(line)
            
            # Get the exit code
            process.wait()
            exit_code = process.returncode
            
            elapsed = time.time() - start_time
            
            if exit_code == 0:
                logger.info(f"Batch artist update completed successfully in {elapsed:.2f} seconds")
            else:
                logger.error(f"Batch artist update failed with exit code {exit_code}")
                for line in process.stderr:
                    logger.error(f"BATCH ERROR: {line.strip()}")
            
            return exit_code
            
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    logger.info(f"Removed temporary file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file: {e}")
        
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
    # Use asyncio.run for Python 3.7+
    if sys.version_info >= (3, 7):
        sys.exit(asyncio.run(main()))
    else:
        # For older Python versions
        loop = asyncio.get_event_loop()
        sys.exit(loop.run_until_complete(main()))
