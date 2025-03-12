def get_artists_needing_update(conn, standard_check=True, partner_check=True, limit=None):
    """Find artists needing updates based on their tier and last update time."""
    try:
        cursor = conn.cursor()
        
        # Build query conditions based on update types
        conditions = []
        
        if standard_check:
            # Artists needing standard API updates based on tier
            conditions.append(
                "(" +
                "(popularity >= 75 AND last_updated < datetime('now', '-3 days')) OR " +
                "(popularity >= 50 AND popularity < 75 AND last_updated < datetime('now', '-7 days')) OR " +
                "(popularity < 50 AND last_updated < datetime('now', '-14 days')) OR " +
                "last_updated IS NULL" +
                ")"
            )
        
        if partner_check:
            # Artists needing Partner API updates based on tier
            conditions.append(
                "(" +
                "(popularity >= 75 AND (enhanced_data_updated < datetime('now', '-7 days') OR enhanced_data_updated IS NULL)) OR " +
                "(popularity >= 50 AND popularity < 75 AND (enhanced_data_updated < datetime('now', '-14 days') OR enhanced_data_updated IS NULL)) OR " +
                "(popularity < 50 AND (enhanced_data_updated < datetime('now', '-30 days') OR enhanced_data_updated IS NULL))" +
                ")"
            )
        
        if not conditions:
            return []
        
        # Combine conditions with OR
        where_clause = " OR ".join(conditions)
        
        # Build the query
        query = f"""
        SELECT id, name, popularity, last_updated, enhanced_data_updated,
            CASE 
                WHEN popularity >= 75 THEN 'Top Tier'
                WHEN popularity >= 50 THEN 'Mid Tier'
                ELSE 'Lower Tier'
            END as tier
        FROM artists
        WHERE {where_clause}
        ORDER BY popularity DESC, last_updated ASC
        """
        
        if limit is not None and limit > 0:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        artists = cursor.fetchall()
        
        # Convert to list of artist IDs and log details
        artist_ids = []
        logger.info(f"Found {len(artists)} artists needing updates:")
        
        for artist in artists:
            artist_dict = dict(artist)
            artist_ids.append(artist_dict['id'])
            
            # Determine why this artist needs an update
            needs_standard = False
            needs_partner = False
            
            if standard_check:
                if artist_dict['popularity'] >= 75 and (artist_dict['last_updated'] is None or 
                                                      datetime.fromisoformat(artist_dict['last_updated']) < 
                                                      datetime.now() - timedelta(days=3)):
                    needs_standard = True
                elif artist_dict['popularity'] >= 50 and artist_dict['popularity'] < 75 and (artist_dict['last_updated'] is None or 
                                                                                            datetime.fromisoformat(artist_dict['last_updated']) < 
                                                                                            datetime.now() - timedelta(days=7)):
                    needs_standard = True
                elif artist_dict['popularity'] < 50 and (artist_dict['last_updated'] is None or 
                                                       datetime.fromisoformat(artist_dict['last_updated']) < 
                                                       datetime.now() - timedelta(days=14)):
                    needs_standard = True
            
            if partner_check:
                if artist_dict['popularity'] >= 75 and (artist_dict['enhanced_data_updated'] is None or 
                                                       datetime.fromisoformat(artist_dict['enhanced_data_updated']) < 
                                                       datetime.now() - timedelta(days=7)):
                    needs_partner = True
                elif artist_dict['popularity'] >= 50 and artist_dict['popularity'] < 75 and (artist_dict['enhanced_data_updated'] is None or 
                                                                                             datetime.fromisoformat(artist_dict['enhanced_data_updated']) < 
                                                                                             datetime.now() - timedelta(days=14)):
                    needs_partner = True
                elif artist_dict['popularity'] < 50 and (artist_dict['enhanced_data_updated'] is None or 
                                                        datetime.fromisoformat(artist_dict['enhanced_data_updated']) < 
                                                        datetime.now() - timedelta(days=30)):
                    needs_partner = True
            
            # Log artist details
            update_types = []
            if needs_standard:
                update_types.append("Standard API")
            if needs_partner:
                update_types.append("Partner API")
                
            logger.info(f"  - {artist_dict['name']} ({artist_dict['tier']}): Needs {', '.join(update_types)}")
        
        return artist_ids
        
    except Exception as e:
        logger.error(f"Error finding artists needing updates: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []
        
        # Build where clauses based on tier update schedules
        where_clauses = []
        
        # Standard API update criteria
        if not partner_only:
            where_clauses.append("""
                (popularity >= 75 AND (last_updated IS NULL OR last_updated < datetime('now', '-3 days')))
                OR (popularity >= 50 AND popularity < 75 AND (last_updated IS NULL OR last_updated < datetime('now', '-7 days')))
                OR (popularity < 50 AND (last_updated IS NULL OR last_updated < datetime('now', '-14 days')))
            """)
        
        # Partner API update criteria
        if not standard_only:
            where_clauses.append("""
                (popularity >= 75 AND (enhanced_data_updated IS NULL OR enhanced_data_updated < datetime('now', '-7 days')))
                OR (popularity >= 50 AND popularity < 75 AND (enhanced_data_updated IS NULL OR enhanced_data_updated < datetime('now', '-14 days')))
                OR (popularity < 50 AND (enhanced_data_updated IS NULL OR enhanced_data_updated < datetime('now', '-30 days')))
            """)
        
        # Combine where clauses with OR
        where_clause = " OR ".join(f"({clause})" for clause in where_clauses)
        
        # Build the query
        query = f"""
            SELECT id, name, popularity, 
                   last_updated, enhanced_data_updated,
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
                COALESCE(last_updated, '1970-01-01'),
                COALESCE(enhanced_data_updated, '1970-01-01')
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        artists = cursor.fetchall()
        
        # Extract the artist IDs and additional information
        result = []
        for row in artists:
            # Convert row to dict for easier access
            artist = dict(row)
            result.append({
                "id": artist["id"],
                "name": artist["name"],
                "popularity": artist["popularity"],
                "tier": artist["tier"],
                "last_updated": artist["last_updated"],
                "enhanced_data_updated": artist["enhanced_data_updated"]
            })
        
        conn.close()
        return result
        
    except Exception as e:
        logger.error(f"Error getting artists needing updates: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []#!/usr/bin/env python3
"""
Batch Artist Update Tool for DJVIBE
Updates multiple artists using both standard Spotify API and Partner API.
"""
import os
import sys
import json
import time
import logging
import sqlite3
import asyncio
import argparse
import requests
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("batch_update.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("batch_artist_update")


def get_artists_needing_updates(db_path, limit=None, standard_only=False, partner_only=False):
    """Get artists that need updates based on their tier and last update time."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Build where clauses based on tier update schedules
        where_clauses = []
        
        # Standard API update criteria
        if not partner_only:
            where_clauses.append("""
                (popularity >= 75 AND (last_updated IS NULL OR last_updated < datetime('now', '-3 days')))
                OR (popularity >= 50 AND popularity < 75 AND (last_updated IS NULL OR last_updated < datetime('now', '-7 days')))
                OR (popularity < 50 AND (last_updated IS NULL OR last_updated < datetime('now', '-14 days')))
            """)
        
        # Partner API update criteria
        if not standard_only:
            where_clauses.append("""
                (popularity >= 75 AND (enhanced_data_updated IS NULL OR enhanced_data_updated < datetime('now', '-7 days')))
                OR (popularity >= 50 AND popularity < 75 AND (enhanced_data_updated IS NULL OR enhanced_data_updated < datetime('now', '-14 days')))
                OR (popularity < 50 AND (enhanced_data_updated IS NULL OR enhanced_data_updated < datetime('now', '-30 days')))
            """)
        
        # Combine where clauses with OR
        where_clause = " OR ".join(f"({clause})" for clause in where_clauses)
        
        # Build the query
        query = f"""
            SELECT id, name, popularity, 
                   last_updated, enhanced_data_updated,
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
                COALESCE(last_updated, '1970-01-01'),
                COALESCE(enhanced_data_updated, '1970-01-01')
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        artists = cursor.fetchall()
        
        # Extract the artist IDs and additional information
        result = []
        for row in artists:
            # Convert row to dict for easier access
            artist = dict(row)
            result.append({
                "id": artist["id"],
                "name": artist["name"],
                "popularity": artist["popularity"],
                "tier": artist["tier"],
                "last_updated": artist["last_updated"],
                "enhanced_data_updated": artist["enhanced_data_updated"]
            })
        
        conn.close()
        return result
        
    except Exception as e:
        logger.error(f"Error getting artists needing updates: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []

#
# DATABASE FUNCTIONS
#
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

def get_artists_needing_update(conn, limit=None, standard_only=False, partner_only=False):
    """Get artists that need updates based on their tier."""
    try:
        cursor = conn.cursor()
        
        # Build the query based on what updates are needed
        where_clauses = []
        
        if not partner_only:  # Include standard API update criteria
            where_clauses.append("""
                (popularity >= 75 AND last_updated < datetime('now', '-3 days'))
                OR (popularity >= 50 AND popularity < 75 AND last_updated < datetime('now', '-7 days'))
                OR (popularity < 50 AND last_updated < datetime('now', '-14 days'))
                OR last_updated IS NULL
            """)
        
        if not standard_only:  # Include partner API update criteria
            where_clauses.append("""
                (popularity >= 75 AND enhanced_data_updated < datetime('now', '-7 days'))
                OR (popularity >= 50 AND popularity < 75 AND enhanced_data_updated < datetime('now', '-14 days'))
                OR (popularity < 50 AND enhanced_data_updated < datetime('now', '-30 days'))
                OR enhanced_data_updated IS NULL
            """)
        
        # Combine with OR if both types of updates are included
        where_clause = " OR ".join(where_clauses)
        
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
            ORDER BY popularity DESC, last_updated ASC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query to find artists needing updates")
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
        return []

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

#
# STANDARD SPOTIFY API FUNCTIONS
#
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

#
# PARTNER SPOTIFY API FUNCTIONS
#
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

#
# ARTIST UPDATE FUNCTIONS
#
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

#
# MAIN FUNCTION
#
async def main():
    """Main function for the batch artist update tool."""
    parser = argparse.ArgumentParser(description="Batch artist update tool for DJVIBE Spotify MCP")
    
    # Artist selection (mutually exclusive)
    artist_group = parser.add_mutually_exclusive_group(required=True)
    artist_group.add_argument("--artist-id", "-a", help="Single Spotify artist ID to update")
    artist_group.add_argument("--artist-ids", "-ids", help="Comma-separated list of Spotify artist IDs")
    artist_group.add_argument("--file", "-f", help="File containing artist IDs, one per line")
    artist_group.add_argument("--needs-update", "-n", action="store_true", help="Find and update artists needing updates based on tier rules")
    
    # Configuration
    parser.add_argument("--config", "-c", required=True, help="Path to configuration file")
    
    # Update schedule options
    parser.add_argument("--check-standard", "-cs", action="store_true", help="Check for artists needing standard API updates")
    parser.add_argument("--check-partner", "-cp", action="store_true", help="Check for artists needing Partner API updates")
    parser.add_argument("--limit", "-l", type=int, help="Limit number of artists to update")
    
    # Batch processing options
    parser.add_argument("--concurrency", "-cc", type=int, default=3, help="Maximum number of concurrent updates (default: 3)")
    parser.add_argument("--delay", "-d", type=float, default=0.5, help="Delay between API requests in seconds (default: 0.5)")
    
    # Update options
    parser.add_argument("--standard-only", "-s", action="store_true", help="Only update with standard API")
    parser.add_argument("--partner-only", "-p", action="store_true", help="Only update with Partner API")
    
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
    
    # Determine which APIs to use
    use_standard = not args.partner_only
    use_partner = not args.standard_only
    
    # Get artist IDs to update
    artist_ids = []
    
    if args.artist_id:
        # Single artist
        artist_ids = [args.artist_id]
        logger.info(f"Updating single artist: {args.artist_id}")
    elif args.artist_ids:
        # Multiple specified artists
        artist_ids = [aid.strip() for aid in args.artist_ids.split(",")]
        logger.info(f"Updating {len(artist_ids)} artists from command line")
    elif args.file:
        # Artists from file
        try:
            with open(args.file, "r") as f:
                lines = f.readlines()
                artist_ids = [line.strip() for line in lines if line.strip()]
            logger.info(f"Loaded {len(artist_ids)} artists from file: {args.file}")
        except Exception as e:
            logger.error(f"Error loading artist IDs from file: {str(e)}")
            return 1
    elif args.needs_update:
        # Find artists needing updates
        logger.info("Finding artists that need updates based on tier")
        conn = connect_db(db_path)
        if not conn:
            return 1
        
        try:
            artist_ids = get_artists_needing_update(conn, args.limit, args.standard_only, args.partner_only)
            conn.close()
            
            if not artist_ids:
                logger.info("No artists found needing updates")
                return 0
        except Exception as e:
            logger.error(f"Error finding artists needing updates: {str(e)}")
            return 1
    
    if not artist_ids:
        logger.error("No artists to update")
        return 1
    
    # Apply limit if specified
    if args.limit and len(artist_ids) > args.limit:
        logger.info(f"Limiting updates to {args.limit} artists (from {len(artist_ids)} total)")
        artist_ids = artist_ids[:args.limit]
    
    start_time = time.time()
    
    # Update artists
    if len(artist_ids) == 1:
        # Single artist update
        success, message = await update_artist(
            artist_ids[0], db_path, client_id, client_secret, redirect_uri, tokens_file,
            use_standard, use_partner
        )
        
        # Include elapsed time
        elapsed = time.time() - start_time
        
        print(f"\nUpdate Result:")
        print(f"Artist ID: {artist_ids[0]}")
        print(f"Status: {'SUCCESS' if success else 'FAILED'}")
        print(f"Message: {message}")
        print(f"Duration: {elapsed:.2f} seconds")
        
        return 0 if success else 1
    else:
        # Batch update
        results = await batch_update_artists(
            artist_ids, db_path, client_id, client_secret, redirect_uri, tokens_file,
            use_standard, use_partner, args.concurrency, args.delay
        )
        
        # Include elapsed time
        elapsed = time.time() - start_time
        
        print(f"\nBatch Update Results:")
        print(f"Total: {results['total']}")
        print(f"Successful: {len(results['successful'])}")
        print(f"Failed: {len(results['failed'])}")
        print(f"Duration: {elapsed:.2f} seconds")
        
        if results['failed']:
            print("\nFailed Artists:")
            for artist_id, message in results['failed']:
                print(f"  - {artist_id}: {message}")
        
        return 0 if not results['failed'] else 1

if __name__ == "__main__":
    asyncio.run(main())
