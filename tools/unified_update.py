#!/usr/bin/env python3
import os
import sys
import asyncio
import argparse
import logging
import sqlite3
from datetime import datetime
import json
from typing import List, Dict, Any

# Add src directory to the path 
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the UnifiedSpotifyAPI class
from src.spotify_mcp.unified_api import UnifiedSpotifyAPI

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("unified_update.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("unified_update")


def load_config(config_file: str = None) -> Dict[str, Any]:
    """Load configuration from file."""
    # Default config file path
    if not config_file:
        config_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config.json"
        )
    
    # Default configuration
    config = {
        "standard_api": {},
        "partner_api": {},
        "database": {}
    }
    
    try:
        if os.path.exists(config_file):
            logger.info(f"Loading configuration from {config_file}")
            with open(config_file, 'r') as f:
                loaded_config = json.load(f)
                config.update(loaded_config)
                logger.info(f"Configuration loaded successfully")
        else:
            logger.warning(f"Config file {config_file} not found, using defaults and environment variables")
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        
    return config

async def update_single_artist(artist_id: str, db_path: str, tokens_file: str = None,
                              client_id: str = None, client_secret: str = None, redirect_uri: str = None,
                              force_standard: bool = False, force_partner: bool = False):
    """Update a single artist with both APIs as needed."""
    api = UnifiedSpotifyAPI(db_path, logger, tokens_file_path=tokens_file,
                           client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)
    
    logger.info(f"Updating artist {artist_id}")
    artist = await api.update_artist(artist_id, force_standard, force_partner)
    
    if artist:
        logger.info(f"Successfully updated artist: {artist.name}")
        return True, artist.name, artist.id
    else:
        logger.error(f"Failed to update artist {artist_id}")
        return False, None, artist_id

async def batch_update_artists(artist_ids: List[str], db_path: str, tokens_file: str = None,
                              client_id: str = None, client_secret: str = None, redirect_uri: str = None,
                              force_standard: bool = False, force_partner: bool = False,
                              concurrency: int = 3):
    """Update multiple artists with both APIs as needed."""
    results = {
        "successful": [],
        "failed": [],
        "total": len(artist_ids)
    }
    
    # Process artists in batches to control concurrency
    for i in range(0, len(artist_ids), concurrency):
        batch = artist_ids[i:i+concurrency]
        tasks = []
        
        for artist_id in batch:
            tasks.append(update_single_artist(artist_id, db_path, tokens_file, 
                                            client_id, client_secret, redirect_uri,
                                            force_standard, force_partner))
        
        # Wait for all tasks in the batch to complete
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                # Handle exceptions
                logger.error(f"Exception during update: {str(result)}")
                results["failed"].append(("unknown", "exception"))
            else:
                success, name, aid = result
                if success:
                    results["successful"].append((name, aid))
                else:
                    results["failed"].append((name or "unknown", aid))
    
    return results

def get_artists_needing_update(db_path: str, limit: int = None, 
                              standard_only: bool = False, partner_only: bool = False):
    """Get artists that need updates based on their tier."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Build the query based on what updates are needed
        where_clauses = []
        
        if not partner_only:  # Include standard API update criteria
            where_clauses.append("""(
                (popularity >= 75 AND last_updated < datetime('now', '-3 days'))
                OR (popularity >= 50 AND popularity < 75 AND last_updated < datetime('now', '-7 days')) 
                OR (popularity < 50 AND last_updated < datetime('now', '-14 days'))
                OR last_updated IS NULL
            )""")
        
        if not standard_only:  # Include partner API update criteria
            where_clauses.append("""(
                (popularity >= 75 AND enhanced_data_updated < datetime('now', '-7 days'))
                OR (popularity >= 50 AND popularity < 75 AND enhanced_data_updated < datetime('now', '-14 days'))
                OR (popularity < 50 AND enhanced_data_updated < datetime('now', '-30 days'))
                OR enhanced_data_updated IS NULL
            )""")
        
        # Combine with OR if both types of updates are included
        where_clause = " OR ".join(where_clauses)
        
        query = f"""
            SELECT id, name, popularity, last_updated, enhanced_data_updated
            FROM artists
            WHERE {where_clause}
            ORDER BY popularity DESC, last_updated ASC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        artists = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in artists]  # Return just the IDs
            
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Error getting artists: {str(e)}")
        return []

async def main():
    parser = argparse.ArgumentParser(description="Unified artist update tool for Spotify")
    
    # Configuration file
    parser.add_argument("--config", "-c", help="Path to configuration file")
    
    # Artist selection options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--artist-id", "-a", help="Single Spotify artist ID")
    group.add_argument("--artist-ids", "-ids", help="Comma-separated list of Spotify artist IDs")
    group.add_argument("--needs-update", "-n", action="store_true", help="Update artists needing updates")
    
    # Database options
    parser.add_argument("--db-path", "-d", required=True, help="Path to SQLite database")
    parser.add_argument("--tokens-file", "-t", help="Path to tokens file for Partner API")
    
    # Standard API credentials
    parser.add_argument("--client-id", help="Spotify API client ID (overrides env var)")
    parser.add_argument("--client-secret", help="Spotify API client secret (overrides env var)")
    parser.add_argument("--redirect-uri", help="Spotify API redirect URI (overrides env var)")
    
    # Update options
    parser.add_argument("--force-standard", "-fs", action="store_true", help="Force standard API update")
    parser.add_argument("--force-partner", "-fp", action="store_true", help="Force partner API update")
    parser.add_argument("--standard-only", "-so", action="store_true", help="Only perform standard API updates")
    parser.add_argument("--partner-only", "-po", action="store_true", help="Only perform partner API updates")
    
    # Batch options
    parser.add_argument("--concurrency", "-c", type=int, default=3, help="Max concurrent updates")
    parser.add_argument("--limit", "-l", type=int, help="Limit number of artists to update")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Override config with command-line arguments where provided
    db_path = args.db_path or config.get("database", {}).get("path")
    tokens_file = args.tokens_file or config.get("partner_api", {}).get("tokens_file")
    client_id = args.client_id or config.get("standard_api", {}).get("client_id")
    client_secret = args.client_secret or config.get("standard_api", {}).get("client_secret")
    redirect_uri = args.redirect_uri or config.get("standard_api", {}).get("redirect_uri")
    
    # Validate required parameters
    if not db_path:
        logger.error("Database path is required")
        return 1
    
    # Set up force flags
    force_standard = args.force_standard or args.standard_only
    force_partner = args.force_partner or args.partner_only
    
    # Process the request
    if args.artist_id:
        # Single artist update
        success, name, _ = await update_single_artist(
            args.artist_id, db_path, tokens_file, 
            client_id, client_secret, redirect_uri,
            force_standard, force_partner
        )
        if success:
            print(f"Successfully updated artist: {name}")
            return 0
        else:
            print(f"Failed to update artist: {args.artist_id}")
            return 1
    
    elif args.artist_ids:
        # Multiple specified artists
        artist_ids = [aid.strip() for aid in args.artist_ids.split(",")]
        
        if args.limit and len(artist_ids) > args.limit:
            artist_ids = artist_ids[:args.limit]
        
        results = await batch_update_artists(
            artist_ids, db_path, tokens_file, 
            client_id, client_secret, redirect_uri,
            force_standard, force_partner, args.concurrency
        )
        
    elif args.needs_update:
        # Artists needing updates
        artist_ids = get_artists_needing_update(
            db_path, args.limit, args.standard_only, args.partner_only
        )
        
        if not artist_ids:
            logger.info("No artists found needing updates")
            return 0
        
        logger.info(f"Found {len(artist_ids)} artists needing updates")
        
        results = await batch_update_artists(
            artist_ids, db_path, tokens_file, 
            client_id, client_secret, redirect_uri,
            force_standard, force_partner, args.concurrency
        )
    
    # Print summary
    print("\nUpdate Summary:")
    print(f"Total Artists: {results['total']}")
    print(f"Successful: {len(results['successful'])}")
    print(f"Failed: {len(results['failed'])}")
    
    if results["failed"]:
        print("\nFailed Artists:")
        for name, aid in results["failed"]:
            print(f"  - {name} ({aid})")
    
    return 0 if not results["failed"] else 1

if __name__ == "__main__":
    asyncio.run(main())
