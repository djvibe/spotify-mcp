#!/usr/bin/env python3
import os
import sys
import json
import sqlite3
import argparse
import spotipy
import logging
import requests
from spotipy.oauth2 import SpotifyOAuth

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("check_system")

def load_config(config_file):
    """Load configuration from file."""
    try:
        if os.path.exists(config_file):
            logger.info(f"Loading configuration from {config_file}")
            with open(config_file, 'r') as f:
                config = json.load(f)
                logger.info(f"Configuration loaded successfully")
                return config
        else:
            logger.error(f"Config file {config_file} not found")
            return {}
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return {}

def check_database(db_path):
    """Check if the database exists and has the expected table structure."""
    logger.info(f"Checking database at {db_path}")
    
    if not os.path.exists(db_path):
        logger.error(f"Database file does not exist: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if artists table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='artists'")
        if not cursor.fetchone():
            logger.error("Required table 'artists' not found in database")
            return False
        
        # Check table structure
        cursor.execute("PRAGMA table_info(artists)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        required_columns = ["id", "name", "popularity", "last_updated", "genres"]
        for col in required_columns:
            if col not in column_names:
                logger.error(f"Required column '{col}' not found in artists table")
                return False
        
        # Check for extended data columns
        extended_columns = ["monthly_listeners", "social_links_json", "upcoming_tours_count"]
        for col in extended_columns:
            if col not in column_names:
                logger.warning(f"Extended data column '{col}' not found in artists table")
        
        # Check if there are any artists
        cursor.execute("SELECT COUNT(*) FROM artists")
        count = cursor.fetchone()[0]
        logger.info(f"Found {count} artists in the database")
        
        conn.close()
        logger.info("Database structure check passed")
        return True
        
    except Exception as e:
        logger.error(f"Error checking database: {str(e)}")
        return False

def check_standard_api(client_id, client_secret, redirect_uri):
    """Check if we can authenticate with the standard Spotify API."""
    logger.info("Checking standard Spotify API authentication")
    
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="user-library-read"
        ))
        
        # Test a simple API call
        results = sp.search(q='electronic', type='track', limit=1)
        if results and 'tracks' in results and 'items' in results['tracks']:
            logger.info("Successfully authenticated with standard Spotify API")
            return True
        else:
            logger.error("Failed to get search results from standard Spotify API")
            return False
            
    except Exception as e:
        logger.error(f"Error authenticating with standard Spotify API: {str(e)}")
        return False

def check_partner_api():
    """Check if we can get a token for the Partner API."""
    logger.info("Checking Partner API token availability")
    
    try:
        headers = requests.utils.default_headers()
        headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        })
        
        response = requests.get("https://open.spotify.com/get_access_token", headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to retrieve token: HTTP {response.status_code}")
            return False
            
        data = response.json()
        
        if 'accessToken' not in data:
            logger.error("No accessToken in response")
            return False
            
        # We got a token!
        token = data['accessToken']
        logger.info(f"Successfully retrieved Partner API token: {token[:10]}...")
        return True
            
    except Exception as e:
        logger.error(f"Error checking Partner API: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Check the DJVIBE Spotify MCP system")
    parser.add_argument("--config", "-c", required=True, help="Path to configuration file")
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    if not config:
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
    
    # Run checks
    print("\n=== DJVIBE System Check ===\n")
    
    # Database check
    db_ok = check_database(db_path)
    print(f"\nDatabase Check: {'✓ PASSED' if db_ok else '✗ FAILED'}")
    
    # Standard API check
    if all([client_id, client_secret, redirect_uri]):
        standard_api_ok = check_standard_api(client_id, client_secret, redirect_uri)
        print(f"Standard API Check: {'✓ PASSED' if standard_api_ok else '✗ FAILED'}")
    else:
        print("Standard API Check: SKIPPED (missing credentials)")
        standard_api_ok = False
    
    # Partner API check
    partner_api_ok = check_partner_api()
    print(f"Partner API Check: {'✓ PASSED' if partner_api_ok else '✗ FAILED'}")
    
    # Overall status
    print("\n=== Summary ===")
    if db_ok and (standard_api_ok or partner_api_ok):
        print("System is operational with at least one working API")
        return 0
    elif db_ok:
        print("Database is OK but both APIs failed")
        return 1
    else:
        print("System check failed - database issues detected")
        return 1

if __name__ == "__main__":
    sys.exit(main())
