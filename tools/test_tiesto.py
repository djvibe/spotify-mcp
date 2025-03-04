#!/usr/bin/env python3
"""
Special debug script for troubleshooting the Tiësto artist update issue.
This script runs a dedicated test just for Tiësto with extra logging.
"""

import os
import sys
import json
import logging
import requests
import subprocess
import traceback

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tiesto_debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("tiesto_debug")

# Tiësto artist ID
TIESTO_ID = "2o5jDhtHVPhrJdv3cEQ99Z"
DB_PATH = "D:\\DJVIBE\\MCP\\spotify-mcp\\spotify_artists.db"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "output")

def get_artist_info():
    """Get basic info about Tiësto from the database"""
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if artist exists
        cursor.execute("SELECT id, name, popularity, last_updated FROM artists WHERE id = ?", (TIESTO_ID,))
        result = cursor.fetchone()
        
        if result:
            logger.info(f"Tiësto found in database: ID={result[0]}, Name={result[1]}, Popularity={result[2]}, Last Updated={result[3]}")
            return True
        else:
            logger.error("Tiësto not found in database")
            return False
    
    except Exception as e:
        logger.error(f"Error checking database: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def test_fetch_enhanced_data():
    """Test fetching enhanced data for Tiësto"""
    try:
        # Get the path to the test script
        test_script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "test_spotify_api.py")
        
        logger.info(f"Test script path: {test_script_path}")
        logger.info(f"Output directory: {OUTPUT_DIR}")
        
        # Ensure output directory exists
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
            logger.info(f"Created output directory: {OUTPUT_DIR}")
        
        # Run the test script directly for Tiësto
        command = [
            sys.executable,
            test_script_path,
            "--artist-id", TIESTO_ID,
            "--output-dir", OUTPUT_DIR
        ]
        
        logger.info(f"Running command: {' '.join(command)}")
        process = subprocess.run(command, capture_output=True, text=True)
        
        logger.info(f"Process return code: {process.returncode}")
        
        if process.stdout:
            logger.info(f"Process stdout: {process.stdout}")
        
        if process.stderr:
            logger.error(f"Process stderr: {process.stderr}")
        
        # Check if the output files exist
        metrics_file = os.path.join(OUTPUT_DIR, f"{TIESTO_ID}_metrics.json")
        response_file = os.path.join(OUTPUT_DIR, f"{TIESTO_ID}_spotify_response.json")
        
        if os.path.exists(metrics_file):
            logger.info(f"Metrics file exists: {metrics_file}")
            # Check file size
            file_size = os.path.getsize(metrics_file)
            logger.info(f"Metrics file size: {file_size} bytes")
            
            try:
                with open(metrics_file, 'r') as f:
                    content = f.read()
                    logger.info(f"Content length: {len(content)}")
                    
                    if content:
                        try:
                            data = json.loads(content)
                            logger.info("Successfully parsed metrics JSON")
                            logger.info(f"Metrics data: {json.dumps(data, indent=2)}")
                            
                            # Validate required fields
                            required_fields = ["name", "monthly_listeners", "followers"]
                            for field in required_fields:
                                if field not in data or data[field] is None:
                                    logger.error(f"Missing or null field: {field}")
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse metrics JSON: {str(e)}")
                            logger.debug(f"Content sample: {content[:500]}")
                    else:
                        logger.error("Metrics file is empty")
            except Exception as e:
                logger.error(f"Error reading metrics file: {str(e)}")
        else:
            logger.error(f"Metrics file does not exist: {metrics_file}")
        
        if os.path.exists(response_file):
            logger.info(f"Response file exists: {response_file}")
            # Check file size
            file_size = os.path.getsize(response_file)
            logger.info(f"Response file size: {file_size} bytes")
        else:
            logger.error(f"Response file does not exist: {response_file}")
        
        return process.returncode == 0 and os.path.exists(metrics_file) and os.path.exists(response_file)
    
    except Exception as e:
        logger.error(f"Error testing enhanced data fetch: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def test_update_database():
    """Test updating the database with Tiësto's enhanced data"""
    try:
        # Get the path to the update script
        update_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "update_artist_from_enhanced_data.py")
        
        # Get paths to the metrics and response files
        metrics_file = os.path.join(OUTPUT_DIR, f"{TIESTO_ID}_metrics.json")
        response_file = os.path.join(OUTPUT_DIR, f"{TIESTO_ID}_spotify_response.json")
        
        # Check if files exist
        if not os.path.exists(metrics_file):
            logger.error(f"Metrics file not found: {metrics_file}")
            return False
            
        if not os.path.exists(response_file):
            logger.error(f"Response file not found: {response_file}")
            return False
        
        # Run the update script
        command = [
            sys.executable,
            update_script_path,
            "--artist-id", TIESTO_ID,
            "--db-path", DB_PATH,
            "--metrics-file", metrics_file,
            "--response-file", response_file
        ]
        
        logger.info(f"Running command: {' '.join(command)}")
        process = subprocess.run(command, capture_output=True, text=True)
        
        logger.info(f"Process return code: {process.returncode}")
        
        if process.stdout:
            logger.info(f"Process stdout: {process.stdout}")
        
        if process.stderr:
            logger.error(f"Process stderr: {process.stderr}")
        
        return process.returncode == 0
    
    except Exception as e:
        logger.error(f"Error testing database update: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def directly_check_spotify_api():
    """Directly check the Spotify API for Tiësto's data"""
    try:
        # Load tokens
        tokens_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "spotify_tokens.json")
        with open(tokens_file, 'r') as f:
            tokens = json.load(f)
        
        auth_token = tokens.get("auth_token", "")
        client_token = tokens.get("client_token", "")
        
        if not auth_token or not client_token:
            logger.error("Missing or empty tokens in tokens file")
            return False
        
        # Construct the URL
        artist_uri = f"spotify:artist:{TIESTO_ID}"
        url = "https://api-partner.spotify.com/pathfinder/v1/query"
        
        # Set up the headers
        headers = {
            "accept": "application/json",
            "accept-language": "en",
            "app-platform": "WebPlayer",
            "authorization": f"Bearer {auth_token}",
            "client-token": client_token,
            "content-type": "application/json;charset=UTF-8",
            "origin": "https://open.spotify.com",
            "referer": "https://open.spotify.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        }
        
        # Set up the parameters
        params = {
            "operationName": "queryArtistOverview",
            "variables": json.dumps({"uri": artist_uri, "locale": ""}),
            "extensions": json.dumps({
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "591ed473fa2f5426186f8ba52dee295fe1ce32b36820d67eaadbc957d89408b0"
                }
            })
        }
        
        logger.info("Making direct request to Spotify Partner API")
        response = requests.get(url, headers=headers, params=params)
        
        logger.info(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            # Try to parse the response
            try:
                data = response.json()
                logger.info("Successfully parsed response JSON")
                
                # Check for artist data
                if "data" in data and "artistUnion" in data["data"]:
                    artist = data["data"]["artistUnion"]
                    profile = artist.get("profile", {})
                    stats = artist.get("stats", {})
                    
                    logger.info(f"Artist name: {profile.get('name')}")
                    logger.info(f"Monthly listeners: {stats.get('monthlyListeners')}")
                    logger.info(f"Followers: {stats.get('followers')}")
                    
                    # Save the response to a file
                    special_output = os.path.join(OUTPUT_DIR, "tiesto_direct_response.json")
                    with open(special_output, 'w') as f:
                        json.dump(data, f, indent=2)
                    
                    logger.info(f"Response saved to {special_output}")
                    
                    # Try to extract key metrics
                    try:
                        metrics = {
                            "name": profile.get("name"),
                            "monthly_listeners": stats.get("monthlyListeners"),
                            "followers": stats.get("followers"),
                            "verified": profile.get("verified", False),
                            "top_cities": [{
                                "city": city.get("city"),
                                "country": city.get("country"),
                                "region": city.get("region"),
                                "listeners": city.get("numberOfListeners")
                            } for city in stats.get("topCities", {}).get("items", [])],
                            "social_links": {
                                link.get("name", "").lower(): link.get("url") 
                                for link in profile.get("externalLinks", {}).get("items", [])
                            },
                            "upcoming_concerts": []
                        }
                        
                        # Save metrics to a file
                        special_metrics = os.path.join(OUTPUT_DIR, "tiesto_direct_metrics.json")
                        with open(special_metrics, 'w') as f:
                            json.dump(metrics, f, indent=2)
                            
                        logger.info(f"Metrics saved to {special_metrics}")
                        
                        return True
                    except Exception as e:
                        logger.error(f"Error extracting metrics: {str(e)}")
                        logger.debug(traceback.format_exc())
                        return False
                else:
                    logger.error("Response does not contain artist data")
                    return False
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse response JSON: {str(e)}")
                logger.debug(f"Response text: {response.text[:1000]}")
                return False
        else:
            logger.error(f"Request failed with status code: {response.status_code}")
            logger.debug(f"Response text: {response.text[:1000]}")
            return False
    
    except Exception as e:
        logger.error(f"Error making direct API request: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def main():
    """Main function to run all tests"""
    logger.info("Starting Tiësto debug tests")
    
    # Step 1: Check if Tiësto exists in the database
    logger.info("\n=== Step 1: Check Database ===")
    if not get_artist_info():
        logger.error("Step 1 failed: Tiësto not found in database")
        return 1
    
    # Step 2: Test fetching enhanced data
    logger.info("\n=== Step 2: Test Fetch Enhanced Data ===")
    if not test_fetch_enhanced_data():
        # Try a direct API request as fallback
        logger.info("\n=== Fallback: Direct API Request ===")
        if not directly_check_spotify_api():
            logger.error("Direct API request failed")
            return 1
    
    # Step 3: Test updating the database
    logger.info("\n=== Step 3: Test Update Database ===")
    if not test_update_database():
        logger.error("Step 3 failed: Could not update database")
        return 1
    
    logger.info("All tests completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
