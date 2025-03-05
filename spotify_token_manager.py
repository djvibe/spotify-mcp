import requests
import json
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger("spotify_token_manager")

class SpotifyTokenManager:
    """
    Manages Spotify access tokens with automatic retrieval and renewal.
    Eliminates the need for manual token extraction.
    """
    
    def __init__(self, tokens_file_path=None):
        """Initialize the token manager with optional path to save tokens"""
        self.tokens_file_path = tokens_file_path
        self._access_token = None
        self._token_expiry = None
        self._token_refresh_buffer = 300  # Refresh token 5 minutes before expiry
    
    def get_token(self, force_refresh=False):
        """
        Get a valid access token, retrieving or refreshing as needed
        
        Args:
            force_refresh: If True, forces a new token retrieval regardless of expiry
            
        Returns:
            String: A valid access token
        """
        # Check if we need to retrieve a new token
        if (force_refresh or 
            self._access_token is None or 
            self._token_expiry is None or 
            time.time() >= (self._token_expiry - self._token_refresh_buffer)):
            
            self._retrieve_token()
            
        return self._access_token
    
    def _retrieve_token(self):
        """Retrieve a fresh Spotify token from open.spotify.com"""
        try:
            logger.info("Retrieving fresh Spotify access token...")
            
            headers = requests.utils.default_headers()
            headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            })
            
            response = requests.get("https://open.spotify.com/get_access_token", headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to retrieve token: HTTP {response.status_code}")
                raise Exception(f"Token retrieval failed with status {response.status_code}")
                
            data = response.json()
            
            if 'accessToken' not in data:
                logger.error("No accessToken in response")
                raise Exception("Token retrieval response missing accessToken")
                
            # Store the token and calculate expiry time
            self._access_token = data['accessToken']
            
            # Calculate expiry time in seconds since epoch
            if 'accessTokenExpirationTimestampMs' in data:
                # Convert from milliseconds to seconds
                self._token_expiry = data['accessTokenExpirationTimestampMs'] / 1000
            else:
                # Default to 1 hour from now if no expiry provided
                self._token_expiry = time.time() + 3600
                
            logger.info(f"Token retrieved successfully, expires at {datetime.fromtimestamp(self._token_expiry)}")
            
            # Save token to file if path provided
            if self.tokens_file_path:
                self._save_token_to_file(data)
                
            return True
                
        except Exception as e:
            logger.error(f"Error retrieving token: {str(e)}")
            self._access_token = None
            self._token_expiry = None
            return False
    
    def _save_token_to_file(self, token_data):
        """Save token data to file for debugging/compatibility"""
        try:
            with open(self.tokens_file_path, 'w') as f:
                # Format the data to match the format expected by existing code
                save_data = {
                    "auth_token": token_data['accessToken'],
                    "client_token": ""  # We don't need client token anymore
                }
                json.dump(save_data, f, indent=2)
                
            logger.info(f"Token data saved to {self.tokens_file_path}")
        except Exception as e:
            logger.error(f"Error saving token to file: {str(e)}")
            
    def get_authorization_header(self):
        """
        Get a properly formatted authorization header using the current token
        
        Returns:
            Dict: Header dict with authorization
        """
        token = self.get_token()
        return {"Authorization": f"Bearer {token}"}
