#!/usr/bin/env python3
import os
import sys
import json
import time
import sqlite3
import argparse
import logging
import requests
import spotipy
from datetime import datetime
from spotipy.oauth2 import SpotifyOAuth

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("direct_update.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("direct_artist_update")

# Database Operations
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

def update_artist_in_db(conn, artist_data, extended_data=None):
    """Update artist data in the database."""
    try:
        cursor = conn.cursor()
        
        # Check if artist exists
        cursor.execute("SELECT id, name, last_updated FROM artists WHERE id = ?", (artist_data["id"],))
        existing = cursor.fetchone()
        
        # Prepare artist data
        if existing:
            logger.info(f"Updating existing artist: {artist_data['name']} ({artist_data['id']})")
            
            # Get existing data for smart merge
            cursor.execute("SELECT * FROM artists WHERE id = ?", (artist_data["id"],))
            existing_full = cursor.fetchone()
            
            # Convert to dict for easier access
            existing_dict = dict(existing_full)
            
            # Prepare data for update
            update_data = {
                "name": artist_data["name"],
                "external_urls": json.dumps(artist_data.get("external_urls", {})),
                "followers": json.dumps(artist_data.get("followers", {})),
                "genres": json.dumps(artist_data.get("genres", [])),
                "href": artist_data.get("href", ""),
                "images": json.dumps(artist_data.get("images", [])),
                "popularity": artist_data.get("popularity", 0),
                "uri": artist_data.get("uri", ""),
                "type": artist_data.get("type", "artist"),
                "last_updated": datetime.now().isoformat()
            }
            
            # Smart merge: preserve extended data if not provided in update
            if extended_data:
                update_data["monthly_listeners"] = extended_data.get("monthly_listeners")
                update_data["social_links_json"] = json.dumps(extended_data.get("social_links", {}))
                update_data["upcoming_tours_count"] = len(extended_data.get("upcoming_concerts", []))
                update_data["upcoming_tours_json"] = json.dumps(extended_data.get("upcoming_concerts", []))
                update_data["enhanced_data_updated"] = datetime.now().isoformat()
            else:
                # Preserve existing extended data
                if existing_dict.get("monthly_listeners") is not None:
                    update_data["monthly_listeners"] = existing_dict.get("monthly_listeners")
                
                if existing_dict.get("social_links_json"):
                    update_data["social_links_json"] = existing_dict.get("social_links_json")
                
                if existing_dict.get("upcoming_tours_count") is not None:
                    update_data["upcoming_tours_count"] = existing_dict.get("upcoming_tours_count")
                
                if existing_dict.get("upcoming_tours_json"):
                    update_data["upcoming_tours_json"] = existing_dict.get("upcoming_tours_json")
                
                if existing_dict.get("enhanced_data_updated"):
                    update_data["enhanced_data_updated"] = existing_dict.get("enhanced_data_updated")
            
            # Build the SQL update statement
            fields = []
            values = []
            
            for key, value in update_data.items():
                fields.append(f"{key} = ?")
                values.append(value)
            
            # Add the ID for the WHERE clause
            values.append(artist_data["id"])
            
            # Execute the update
            cursor.execute(
                f"UPDATE artists SET {', '.join(fields)} WHERE id = ?",
                values
            )
            
        else:
            logger.info(f"Inserting new artist: {artist_data['name']} ({artist_data['id']})")
            
            # Prepare data for insert
            insert_data = {
                "id": artist_data["id"],
                "name": artist_data["name"],
                "external_urls": json.dumps(artist_data.get("external_urls", {})),
                "followers": json.dumps(artist_data.get("followers", {})),
                "genres": json.dumps(artist_data.get("genres", [])),
                "href": artist_data.get("href", ""),
                "images": json.dumps(artist_data.get("images", [])),
                "popularity": artist_data.get("popularity", 0),
                "uri": artist_data.get("uri", ""),
                "type": artist_data.get("type", "artist"),
                "last_updated": datetime.now().isoformat()
            }
            
            # Add extended data if available
            if extended_data:
                insert_data["monthly_listeners"] = extended_data.get("monthly_listeners")
                insert_data["social_links_json"] = json.dumps(extended_data.get("social_links", {}))
                insert_data["upcoming_tours_count"] = len(extended_data.get("upcoming_concerts", []))
                insert_data["upcoming_tours_json"] = json.dumps(extended_data.get("upcoming_concerts", []))
                insert_data["enhanced_data_updated"] = datetime.now().isoformat()
            
            # Build the SQL insert statement
            fields = ", ".join(insert_data.keys())
            placeholders = ", ".join(["?"] * len(insert_data))
            
            # Execute the insert
            cursor.execute(
                f"INSERT INTO artists ({fields}) VALUES ({placeholders})",
                list(insert_data.values())
            )
        
        # Commit the transaction
        conn.commit()
        logger.info(f"Successfully updated artist in database: {artist_data['name']}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating artist: {str(e)}")
        conn.rollback()
        return False

# Spotify Standard API
def get_artist_from_standard_api(artist_id, client_id, client_secret, redirect_uri):
    """Get artist data from standard Spotify API."""
    logger.info(f"Getting artist data from standard Spotify API: {artist_id}")
    
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="user-library-read",
            open_browser=False
        ))
        
        # Get the artist data
        artist_data = sp.artist(artist_id)
        logger.info(f"Successfully retrieved data for artist: {artist_data['name']}")
        return artist_data
    
    except Exception as e:
        logger.error(f"Error getting artist from standard API: {str(e)}")
        return None

# Spotify Partner API
class SpotifyPartnerAPI:
    """Handles Spotify Partner API interactions."""
    
    def __init__(self, token_file=None):
        self.token_file = token_file
        self._access_token = None
        self._token_expiry = None
        self.headers = {
            "accept": "application/json",
            "accept-language": "en",
            "app-platform": "WebPlayer",
            "content-type": "application/json;charset=UTF-8",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        }
    
    def get_token(self, force_refresh=False):
        """Get a valid Spotify Partner API token."""
        current_time = time.time()
        
        # Check if we need to get a new token
        if (force_refresh or 
            self._access_token is None or 
            self._token_expiry is None or 
            current_time >= self._token_expiry):
            
            logger.info("Getting new Partner API token")
            success = self._get_new_token()
            if not success:
                logger.error("Failed to get Partner API token")
                return None
        else:
            remaining = self._token_expiry - current_time
            logger.info(f"Using existing Partner API token (expires in {remaining:.0f} seconds)")
        
        return self._access_token
    
    def _get_new_token(self):
        """Get a new token from open.spotify.com."""
        try:
            response = requests.get("https://open.spotify.com/get_access_token", headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to get token: HTTP {response.status_code}")
                return False
            
            data = response.json()
            
            if "accessToken" not in data:
                logger.error("No accessToken in response")
                return False
            
            # Store the token
            self._access_token = data["accessToken"]
            
            # Calculate expiry time
            if "accessTokenExpirationTimestampMs" in data:
                self._token_expiry = data["accessTokenExpirationTimestampMs"] / 1000  # ms to seconds
            else:
                self._token_expiry = time.time() + 3600  # Default 1 hour
            
            logger.info(f"Got new token, expires in {(self._token_expiry - time.time()):.0f} seconds")
            
            # Save to file if specified
            if self.token_file:
                self._save_token(data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error getting token: {str(e)}")
            return False
    
    def _save_token(self, data):
        """Save token data to file."""
        try:
            token_data = {
                "auth_token": data["accessToken"],
                "expiry_timestamp": data.get("accessTokenExpirationTimestampMs", time.time() * 1000 + 3600 * 1000),
                "last_updated": time.time() * 1000
            }
            
            with open(self.token_file, "w") as f:
                json.dump(token_data, f, indent=2)
                
            logger.info(f"Saved token to {self.token_file}")
            
        except Exception as e:
            logger.error(f"Error saving token: {str(e)}")
    
    def get_artist_details(self, artist_id):
        """Get artist details from Partner API."""
        logger.info(f"Getting artist details from Partner API: {artist_id}")
        
        # Get token
        token = self.get_token()
        if not token:
            return None
        
        try:
            # Construct the URL for the Partner API
            artist_uri = f"spotify:artist:{artist_id}"
            
            variables = {
                "uri": artist_uri,
                "locale": ""
            }
            
            extensions = {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "591ed473fa2f5426186f8ba52dee295fe1ce32b36820d67eaadbc957d89408b0"
                }
            }
            
            # Construct query parameters
            params = {
                "operationName": "queryArtistOverview",
                "variables": json.dumps(variables),
                "extensions": json.dumps(extensions)
            }
            
            # Add authorization header
            headers = dict(self.headers)
            headers["Authorization"] = f"Bearer {token}"
            
            # Make the request
            url = "https://api-partner.spotify.com/pathfinder/v1/query"
            logger.info(f"Making Partner API request to {url}")
            response = requests.get(url, headers=headers, params=params)
            
            logger.info(f"Partner API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                # Log a portion of the response to verify structure
                try:
                    # Check if the response has the expected structure
                    artist_name = data["data"]["artistUnion"]["profile"]["name"]
                    monthly_listeners = data["data"]["artistUnion"]["stats"]["monthlyListeners"]
                    logger.info(f"Partner API data received for {artist_name}, monthly listeners: {monthly_listeners}")
                except (KeyError, TypeError) as e:
                    logger.error(f"Partner API response missing expected fields: {e}")
                    logger.debug(f"Response structure: {json.dumps(data)[:500]}...")
                
                return data
            elif response.status_code == 401:
                # Authentication error - force token refresh and try again
                logger.warning("Authentication error (401), refreshing token and trying again")
                token = self.get_token(force_refresh=True)
                
                if not token:
                    logger.error("Failed to refresh token")
                    return None
                
                # Update the headers and try again
                headers["Authorization"] = f"Bearer {token}"
                response = requests.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Successfully got Partner API data after token refresh")
                    return data
                else:
                    logger.error(f"Request failed with status {response.status_code} after token refresh")
                    logger.debug(f"Response: {response.text[:500]}")
                    return None
            else:
                logger.error(f"Request failed with status {response.status_code}")
                logger.debug(f"Response: {response.text[:500]}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting artist details: {str(e)}")
            return None
    
    def extract_metrics(self, artist_data):
        """Extract metrics from Partner API response."""
        try:
            logger.debug(f"Extracting metrics from Partner API response - structure: {json.dumps(artist_data)[:1000]}...")
            
            if not artist_data or "data" not in artist_data or "artistUnion" not in artist_data["data"]:
                logger.error("Invalid artist data format")
                return None
            
            artist = artist_data["data"]["artistUnion"]
            
            # Check for required fields
            if "profile" not in artist:
                logger.error("Missing 'profile' in artist data")
                return None
            
            if "stats" not in artist:
                logger.error("Missing 'stats' in artist data")
                return None
            
            profile = artist["profile"]
            stats = artist["stats"]
            
            # Extract metrics
            metrics = {
                "name": profile.get("name"),
                "monthly_listeners": stats.get("monthlyListeners"),
                "social_links": {},
                "upcoming_concerts": []
            }
            
            # Log the extracted metrics
            logger.info(f"Extracted metrics - Name: {metrics['name']}, Monthly Listeners: {metrics['monthly_listeners']}")
            
            # Extract social links
            if "externalLinks" in profile and "items" in profile["externalLinks"]:
                for link in profile["externalLinks"]["items"]:
                    if "name" in link and "url" in link:
                        metrics["social_links"][link.get("name").lower()] = link.get("url")
                logger.info(f"Extracted {len(metrics['social_links'])} social links")
            
            # Extract upcoming concerts
            if "goods" in artist and "concerts" in artist["goods"] and "items" in artist["goods"]["concerts"]:
                for concert in artist["goods"]["concerts"]["items"]:
                    if "data" in concert and concert["data"].get("__typename") == "ConcertV2":
                        concert_data = concert["data"]
                        location = concert_data.get("location", {})
                        metrics["upcoming_concerts"].append({
                            "title": concert_data.get("title"),
                            "date": concert_data.get("startDateIsoString"),
                            "location": {
                                "name": location.get("name"),
                                "city": location.get("city")
                            },
                            "festival": concert_data.get("festival", False)
                        })
                logger.info(f"Extracted {len(metrics['upcoming_concerts'])} upcoming concerts")
            
            logger.info(f"Complete metrics extracted successfully for {metrics['name']}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error extracting metrics: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

async def update_artist(artist_id, db_path, client_id, client_secret, redirect_uri, tokens_file,
                   use_standard=True, use_partner=True):
    """Update a single artist with both APIs as needed."""
    # Connect to database
    conn = connect_db(db_path)
    if not conn:
        return False, f"Failed to connect to database: {db_path}"
    
    try:
        # Update with standard API
        standard_data = None
        if use_standard:
            if not all([client_id, client_secret, redirect_uri]):
                logger.error("Standard API credentials not found in configuration")
                return False, "Standard API credentials missing"
            
            standard_data = get_artist_from_standard_api(artist_id, client_id, client_secret, redirect_uri)
            if not standard_data:
                logger.error(f"Failed to get artist data from standard API for {artist_id}")
                if not use_partner:
                    return False, "Failed to get standard API data"
        
        # Update with Partner API
        extended_data = None
        if use_partner:
            partner_api = SpotifyPartnerAPI(tokens_file)
            partner_data = partner_api.get_artist_details(artist_id)
            
            if partner_data:
                logger.info("Successfully retrieved Partner API data, extracting metrics...")
                extended_data = partner_api.extract_metrics(partner_data)
                if extended_data:
                    logger.info(f"Successfully extracted metrics from Partner API data")
                else:
                    logger.error("Failed to extract metrics from Partner API data")
            else:
                logger.error("Failed to get artist data from Partner API")
        
        # Prepare data for database update
        if standard_data:
            artist_data = standard_data
            artist_name = artist_data['name']
            logger.info(f"Updating database with standard API data for {artist_name}")
        elif extended_data:
            # Partner-only mode - create minimal artist data
            artist_data = {
                "id": artist_id,
                "name": extended_data["name"],
                "external_urls": {},
                "followers": {"total": 0},
                "genres": [],
                "popularity": 0,
                "type": "artist"
            }
            artist_name = extended_data["name"]
            logger.info(f"Updating database with minimal artist data + extended data for {artist_name}")
        else:
            logger.error(f"No data available to update the database for {artist_id}")
            return False, "No API data retrieved"
        
        # Update the database
        success = update_artist_in_db(conn, artist_data, extended_data)
        
        if success:
            return True, f"Successfully updated {artist_name}"
        else:
            return False, f"Database update failed for {artist_name}"
            
    except Exception as e:
        logger.error(f"Error updating artist {artist_id}: {str(e)}")
        return False, f"Exception: {str(e)}"
    finally:
        # Close database connection
        if conn:
            conn.close()

async def batch_update_artists(artist_ids, db_path, client_id, client_secret, redirect_uri, tokens_file,
                            use_standard=True, use_partner=True, concurrency=3, delay=0.5):
    """Update multiple artists with concurrency control."""
    results = {
        "successful": [],
        "failed": [],
        "total": len(artist_ids)
    }
    
    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(concurrency)
    
    async def update_with_semaphore(artist_id):
        async with semaphore:
            # Add delay to avoid rate limiting
            if delay > 0:
                await asyncio.sleep(delay)
                
            success, message = await update_artist(
                artist_id, db_path, client_id, client_secret, redirect_uri, tokens_file,
                use_standard, use_partner
            )
            
            return artist_id, success, message
    
    # Create tasks for all artists
    tasks = [update_with_semaphore(artist_id) for artist_id in artist_ids]
    
    # Wait for all tasks to complete
    task_results = await asyncio.gather(*tasks)
    
    # Process results
    for artist_id, success, message in task_results:
        if success:
            results["successful"].append((artist_id, message))
        else:
            results["failed"].append((artist_id, message))
    
    return results
    
# Main function
async def main():
    parser = argparse.ArgumentParser(description="Direct artist update tool for Spotify")
    
    # Artist selection (mutually exclusive)
    artist_group = parser.add_mutually_exclusive_group(required=True)
    artist_group.add_argument("--artist-id", "-a", help="Single Spotify artist ID to update")
    artist_group.add_argument("--artist-ids", "-ids", help="Comma-separated list of Spotify artist IDs")
    artist_group.add_argument("--file", "-f", help="File containing artist IDs, one per line")
    
    # Configuration option
    parser.add_argument("--config", "-c", required=True, help="Path to configuration file")
    
    # Batch processing options
    parser.add_argument("--concurrency", type=int, default=3, help="Maximum number of concurrent updates (default: 3)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between API requests in seconds (default: 0.5)")
    
    # Update options
    parser.add_argument("--standard-only", "-s", action="store_true", help="Only update with standard API")
    parser.add_argument("--partner-only", "-p", action="store_true", help="Only update with Partner API")
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
    
    # Determine which APIs to use
    use_standard = not args.partner_only
    use_partner = not args.standard_only
    
    # Connect to database
    conn = connect_db(db_path)
    if not conn:
        return 1
    
    # Update with standard API
    standard_data = None
    if use_standard:
        if not all([client_id, client_secret, redirect_uri]):
            logger.error("Standard API credentials not found in configuration")
            return 1
        
        standard_data = get_artist_from_standard_api(args.artist_id, client_id, client_secret, redirect_uri)
        if not standard_data:
            logger.error("Failed to get artist data from standard API")
            if not use_partner:
                return 1
    
    # Update with Partner API
    extended_data = None
    if use_partner:
        partner_api = SpotifyPartnerAPI(tokens_file)
        partner_data = partner_api.get_artist_details(args.artist_id)
        
        if partner_data:
            logger.info("Successfully retrieved Partner API data, extracting metrics...")
            extended_data = partner_api.extract_metrics(partner_data)
            if extended_data:
                logger.info(f"Successfully extracted metrics from Partner API data")
            else:
                logger.error("Failed to extract metrics from Partner API data")
        else:
            logger.error("Failed to get artist data from Partner API")
    
    # Update the database
    if standard_data:
        artist_data = standard_data
        logger.info(f"Updating database with standard API data for {artist_data['name']}")
    elif extended_data:
        # Partner-only mode - create minimal artist data
        artist_data = {
            "id": args.artist_id,
            "name": extended_data["name"],
            "external_urls": {},
            "followers": {"total": 0},
            "genres": [],
            "popularity": 0,
            "type": "artist"
        }
        logger.info(f"Updating database with minimal artist data + extended data for {artist_data['name']}")
    else:
        logger.error("No data available to update the database")
        return 1
    
    success = update_artist_in_db(conn, artist_data, extended_data)
    
    # Report results
    print("\nUpdate Results:")
    print(f"Artist ID: {args.artist_id}")
    print(f"Artist Name: {artist_data['name']}")
    
    if use_standard:
        print(f"Standard API: {'SUCCESS' if standard_data else 'FAILED'}")
    
    if use_partner:
        print(f"Partner API: {'SUCCESS' if extended_data else 'FAILED'}")
    
    if success:
        print("Database Update: SUCCESS")
        print("Overall: SUCCESS")
        return 0
    else:
        print("Database Update: FAILED")
        print("Overall: FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
