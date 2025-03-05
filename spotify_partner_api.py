import requests
import json
import logging
import urllib.parse
from spotify_token_manager import SpotifyTokenManager

logger = logging.getLogger("spotify_partner_api")

class SpotifyPartnerAPI:
    """
    Client for the Spotify Partner API with automatic token management.
    Provides access to enhanced artist data including monthly listeners.
    """
    
    def __init__(self, tokens_file_path=None):
        """Initialize the API client with token management"""
        self.token_manager = SpotifyTokenManager(tokens_file_path)
        self.base_url = "https://api-partner.spotify.com/pathfinder/v1/query"
    
    def get_artist_details(self, artist_id):
        """
        Get detailed artist information including monthly listeners
        
        Args:
            artist_id: Spotify artist ID
            
        Returns:
            Dict: Artist data if successful, None otherwise
        """
        try:
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
            
            # Add authorization header with fresh token
            headers.update(self.token_manager.get_authorization_header())
            
            # Make the request
            response = requests.get(self.base_url, headers=headers, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API request failed with status {response.status_code}")
                logger.debug(f"Response: {response.text[:500]}...")
                return None
                
        except Exception as e:
            logger.error(f"Error getting artist details: {str(e)}")
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
            profile = artist["profile"]
            stats = artist["stats"]
            
            # Extract key metrics
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
                "social_links": {link.get("name").lower(): link.get("url") 
                              for link in profile.get("externalLinks", {}).get("items", [])},
                "upcoming_concerts": []
            }
            
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
            logger.error(f"Error extracting metrics: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
