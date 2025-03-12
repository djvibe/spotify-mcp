#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import argparse
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("simple_artist_update.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("simple_artist_update")

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
            logger.warning(f"Config file {config_file} not found")
            return {}
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return {}

def update_artist_standard_api(artist_id, db_path, client_id, client_secret, redirect_uri):
    """Update artist using standard Spotify API through existing tools."""
    logger.info(f"Updating artist {artist_id} using standard Spotify API")
    
    # Set environment variables for Spotify API credentials
    env = os.environ.copy()
    env["SPOTIFY_CLIENT_ID"] = client_id
    env["SPOTIFY_CLIENT_SECRET"] = client_secret
    env["SPOTIFY_REDIRECT_URI"] = redirect_uri
    
    # Use the existing spotipy-based script for standard API updates
    try:
        # Find the path to the existing update script (batch_update_artists.py)
        update_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "batch_update_artists.py")
        
        # Execute the command
        command = [
            sys.executable,
            update_script,
            "--artist-ids", artist_id,
            "--db-path", db_path
        ]
        
        logger.info(f"Executing: {' '.join(command)}")
        process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        stdout_text = stdout.decode()
        stderr_text = stderr.decode()
        
        logger.info(f"Standard API stdout: {stdout_text}")
        
        if process.returncode != 0:
            logger.error(f"Standard API update failed with code {process.returncode}")
            logger.error(f"STDERR: {stderr_text}")
            return False
        
        logger.info(f"Standard API update completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during standard API update: {str(e)}")
        return False

def update_artist_partner_api(artist_id, db_path, tokens_file):
    """Update artist using Spotify Partner API."""
    logger.info(f"Updating artist {artist_id} using Partner API")
    
    try:
        # Find the path to the existing Partner API update script
        update_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "update_artist_from_enhanced_data.py")
        
        # First, we need to get the enhanced data from the Partner API
        fetch_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "tests", 
            "test_spotify_api.py"
        )
        
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Step 1: Fetch enhanced data
        logger.info(f"Fetching enhanced data for artist {artist_id}")
        fetch_command = [
            sys.executable,
            fetch_script,
            "--artist-id", artist_id,
            "--output-dir", output_dir
        ]
        
        logger.info(f"Executing: {' '.join(fetch_command)}")
        fetch_process = subprocess.Popen(fetch_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = fetch_process.communicate()
        
        stdout_text = stdout.decode()
        stderr_text = stderr.decode()
        
        logger.info(f"Partner API stdout: {stdout_text}")
        
        if fetch_process.returncode != 0:
            logger.error(f"Enhanced data fetch failed with code {fetch_process.returncode}")
            logger.error(f"STDERR: {stderr_text}")
            return False
        
        logger.info(f"Enhanced data fetch completed successfully")
        
        # List files in output dir to debug
        logger.info(f"Files in output directory: {os.listdir(output_dir)}")
        
        # Step 2: Update database with enhanced data
        metrics_file = os.path.join(output_dir, f"{artist_id}_metrics.json")
        response_file = os.path.join(output_dir, f"{artist_id}_spotify_response.json")
        
        # Try alternate filenames if the expected ones aren't found
        if not os.path.exists(metrics_file) or not os.path.exists(response_file):
            # Look for any files matching the artist ID
            matching_files = [f for f in os.listdir(output_dir) if artist_id in f]
            logger.info(f"Found files matching artist ID: {matching_files}")
            
            # Try to find metrics and response files
            metrics_files = [f for f in matching_files if "metrics" in f.lower()]
            response_files = [f for f in matching_files if "response" in f.lower()]
            
            if metrics_files:
                metrics_file = os.path.join(output_dir, metrics_files[0])
                logger.info(f"Using alternate metrics file: {metrics_file}")
            
            if response_files:
                response_file = os.path.join(output_dir, response_files[0])
                logger.info(f"Using alternate response file: {response_file}")
        
        if not os.path.exists(metrics_file) or not os.path.exists(response_file):
            # As a fallback, just use any two JSON files we can find
            json_files = [f for f in os.listdir(output_dir) if f.endswith(".json")]
            if len(json_files) >= 2:
                metrics_file = os.path.join(output_dir, json_files[0])
                response_file = os.path.join(output_dir, json_files[1])
                logger.info(f"Using fallback files: {metrics_file} and {response_file}")
            else:
                logger.error(f"Enhanced data files not found and no suitable alternates")
                return False
        
        update_command = [
            sys.executable,
            update_script,
            "--artist-id", artist_id,
            "--db-path", db_path,
            "--metrics-file", metrics_file,
            "--response-file", response_file
        ]
        
        logger.info(f"Executing: {' '.join(update_command)}")
        update_process = subprocess.Popen(update_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = update_process.communicate()
        
        stdout_text = stdout.decode()
        stderr_text = stderr.decode()
        
        logger.info(f"Database update stdout: {stdout_text}")
        
        if update_process.returncode != 0:
            logger.error(f"Database update with enhanced data failed with code {update_process.returncode}")
            logger.error(f"STDERR: {stderr_text}")
            return False
        
        logger.info(f"Database update with enhanced data completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during Partner API update: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Simple unified artist update tool for Spotify")
    
    # Configuration file
    parser.add_argument("--config", "-c", required=True, help="Path to configuration file")
    
    # Artist selection
    parser.add_argument("--artist-id", "-a", required=True, help="Spotify artist ID to update")
    
    # Update options
    parser.add_argument("--standard-only", "-s", action="store_true", help="Only update with standard API")
    parser.add_argument("--partner-only", "-p", action="store_true", help="Only update with Partner API")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Extract configuration
    db_path = config.get("database", {}).get("path")
    if not db_path:
        logger.error("Database path not found in configuration")
        return 1
    
    client_id = config.get("standard_api", {}).get("client_id")
    client_secret = config.get("standard_api", {}).get("client_secret")
    redirect_uri = config.get("standard_api", {}).get("redirect_uri")
    
    if not all([client_id, client_secret, redirect_uri]) and not args.partner_only:
        logger.error("Standard API credentials not found in configuration")
        return 1
    
    tokens_file = config.get("partner_api", {}).get("tokens_file")
    if not tokens_file and not args.standard_only:
        logger.error("Partner API tokens file not found in configuration")
        return 1
    
    # Get absolute path for tokens file
    if tokens_file and not os.path.isabs(tokens_file):
        tokens_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), tokens_file)
    
    # Determine which APIs to use
    use_standard = not args.partner_only
    use_partner = not args.standard_only
    
    # Update with standard API if needed
    standard_success = True
    if use_standard:
        standard_success = update_artist_standard_api(
            args.artist_id, db_path, client_id, client_secret, redirect_uri
        )
    
    # Update with Partner API if needed
    partner_success = True
    if use_partner:
        partner_success = update_artist_partner_api(
            args.artist_id, db_path, tokens_file
        )
    
    # Report results
    print("\nUpdate Results:")
    print(f"Artist ID: {args.artist_id}")
    if use_standard:
        print(f"Standard API: {'SUCCESS' if standard_success else 'FAILED'}")
    if use_partner:
        print(f"Partner API: {'SUCCESS' if partner_success else 'FAILED'}")
    
    if standard_success and partner_success:
        print("Overall: SUCCESS")
        return 0
    else:
        print("Overall: PARTIAL SUCCESS" if standard_success or partner_success else "Overall: FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
