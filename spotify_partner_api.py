import requests
import json
import logging
import urllib.parse
import time
import traceback
from spotify_token_manager import SpotifyTokenManager

logger = logging.getLogger("spotify_partner_api")

class SpotifyPartnerAPI:
    """
    Client for the Spotify Partner API with automatic token management.
    Provides access to enhanced artist data including monthly listeners.
    """
    
    def __init__(self, tokens_file_path=None, token_manager=None):
        """
        Initialize the API client with token management
        
        Args:
            tokens_file_path: Path to token file (if not using existing token manager)
            token_manager: Existing token manager instance (preferred)
        """
        # Use provided token manager or create a new one
        if token_manager:
            self.token_manager = token_manager
        else:
            self.token_manager = SpotifyTokenManager(tokens_file_path)
            
        self.base_url = "https://api-partner.spotify.com/pathfinder/v1/query"
        self.max_retries = 3
        self.retry_delay = 2  # seconds
    
    def get_artist_details(self, artist_id):
        """
        Get detailed artist information including monthly listeners with retry support
        
        Args:
            artist_id: Spotify artist ID
            
        Returns:
            Dict: Artist data if successful, None otherwise
        """
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    # Add delay between retries with exponential backoff
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    logger.info(f"Retry {attempt+1}/{self.max_retries} for artist {artist_id} in {delay} seconds")
                    time.sleep(delay)
                
                logger.info(f"Getting detailed info for artist: {artist_id}")
                
                # Construct the full artist URI
                artist_uri = f"spotify:artist:{artist_id}"
                
                # Prepare the GraphQL variables
                variables = {
                    "uri": artist_uri,
                    "locale": ""
                }
                
                # Prepare the GraphQL extensions
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
                
                # Set up the headers - get fresh token automatically
                headers = {
                    "accept": "application/json",
                    "accept-language": "en",
                    "app-platform": "WebPlayer",
                    "content-type": "application/json;charset=UTF-8",
                    "origin": "https://open.spotify.com",
                    "referer": "https://open.spotify.com/",
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
                }
                
                # Add authorization header with token
                headers.update(self.token_manager.get_authorization_header())
                
                # Make the request
                response = requests.get(self.base_url, headers=headers, params=params)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    # Authentication error - force token refresh
                    logger.warning(f"Authentication error (401) for artist {artist_id}, refreshing token")
                    self.token_manager.get_token(force_refresh=True)
                    
                    if attempt == self.max_retries - 1:
                        # Last attempt failed
                        logger.error(f"API request failed with status {response.status_code} after token refresh")
                        logger.debug(f"Response: {response.text[:500]}...")
                        return None
                        
                    # Continue to retry with new token
                    continue
                else:
                    logger.error(f"API request failed with status {response.status_code}")
                    logger.debug(f"Response: {response.text[:500]}...")
                    
                    if response.status_code >= 500:
                        # Server error, retry
                        if attempt == self.max_retries - 1:
                            return None
                        continue
                    else:
                        # Client error, don't retry
                        return None
                    
            except Exception as e:
                error_stack = traceback.format_exc()
                logger.error(f"Error getting artist details (attempt {attempt+1}/{self.max_retries}): {str(e)}")
                logger.debug(f"Error details: {error_stack}")
                
                if "token" in str(e).lower():
                    # Token-related error, attempt to refresh
                    try:
                        logger.warning("Token error detected, forcing token refresh")
                        self.token_manager.get_token(force_refresh=True)
                    except Exception as token_error:
                        logger.error(f"Token refresh failed: {str(token_error)}")
                
                if attempt == self.max_retries - 1:
                    # Last attempt failed
                    logger.error(f"All retries failed for artist {artist_id}")
                    return None
        
        # Should not reach here
        return None
    
    def extract_artist_metrics(self, artist_data):
        """
        Extract key metrics from the artist data
        
        Args:
            artist_data: API response data
            
        Returns:
            Dict: Extracted metrics or None if data invalid
        """
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
            
            # Extract key metrics
            metrics = {
                "name": profile.get("name"),
                "monthly_listeners": stats.get("monthlyListeners"),
                "followers": stats.get("followers"),
                "verified": profile.get("verified", False),
                "top_cities": [],
                "social_links": {},
                "upcoming_concerts": []
            }
            
            # Extract top cities
            if "topCities" in stats and "items" in stats["topCities"]:
                for city in stats["topCities"]["items"]:
                    metrics["top_cities"].append({
                        "city": city.get("city"),
                        "country": city.get("country"),
                        "region": city.get("region"),
                        "listeners": city.get("numberOfListeners")
                    })
            
            # Extract social links
            if "externalLinks" in profile and "items" in profile["externalLinks"]:
                for link in profile["externalLinks"]["items"]:
                    if "name" in link and "url" in link:
                        metrics["social_links"][link.get("name").lower()] = link.get("url")
            
            # Extract upcoming concerts if available
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
            
            return metrics
            
        except Exception as e:
            error_stack = traceback.format_exc()
            logger.error(f"Error extracting metrics: {str(e)}")
            logger.debug(f"Error details: {error_stack}")
            return None
