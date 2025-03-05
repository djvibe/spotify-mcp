import requests
import json
import logging
import time
import os
from datetime import datetime, timedelta

logger = logging.getLogger("spotify_token_manager")

class SpotifyTokenManager:
    """
    Manages Spotify access tokens with automatic retrieval and renewal.
    Implements intelligent caching, retry logic, and token reuse to avoid rate limiting.
    """
    
    def __init__(self, tokens_file_path=None):
        """Initialize the token manager with optional path to save tokens"""
        self.tokens_file_path = tokens_file_path
        self._access_token = None
        self._token_expiry = None
        self._token_refresh_buffer = 300  # Refresh token 5 minutes before expiry
        self._requests_made = 0  # Track the number of requests made with this token
        
        # Try to load existing token from file if available
        if tokens_file_path and os.path.exists(tokens_file_path):
            self._load_token_from_file()
    
    def _load_token_from_file(self):
        """Load token data from file if available and still valid"""
        try:
            with open(self.tokens_file_path, 'r') as f:
                token_data = json.load(f)
                
            # Check if token exists and is still valid
            if 'auth_token' in token_data:
                self._access_token = token_data['auth_token']
                
                # Get expiry time if available
                if 'expiry_timestamp' in token_data:
                    self._token_expiry = token_data['expiry_timestamp'] / 1000  # Convert ms to seconds
                elif 'expiry_time' in token_data:
                    self._token_expiry = token_data['expiry_time']
                else:
                    # Default to 1 hour from last save if no expiry provided
                    if 'last_updated' in token_data:
                        self._token_expiry = token_data['last_updated'] / 1000 + 3600
                    else:
                        self._token_expiry = time.time() + 3600
                
                # Load request count if available
                if 'requests_made' in token_data:
                    self._requests_made = token_data['requests_made']
                
                time_remaining = self._token_expiry - time.time()
                if time_remaining > self._token_refresh_buffer:
                    logger.info(f"Loaded valid token from file, expires in {time_remaining:.1f} seconds")
                else:
                    logger.info("Loaded token from file but it will expire soon, will refresh when needed")
        except Exception as e:
            logger.error(f"Error loading token from file: {str(e)}")
            # We'll get a new token when needed
    
    def get_token(self, force_refresh=False):
        """
        Get a valid access token, retrieving or refreshing as needed
        
        Args:
            force_refresh: If True, forces a new token retrieval regardless of expiry
            
        Returns:
            String: A valid access token
        """
        current_time = time.time()
        
        # Add more logging to understand token reuse decisions
        if self._access_token and self._token_expiry:
            time_remaining = self._token_expiry - current_time
            logger.debug(f"Current token valid for {time_remaining:.1f} seconds, {self._requests_made} requests made with it")
        
        # Check if we need to retrieve a new token
        if (force_refresh or 
            self._access_token is None or 
            self._token_expiry is None or 
            current_time >= (self._token_expiry - self._token_refresh_buffer)):
            
            success = self._retrieve_token_with_retry()
            if not success:
                # If retrieval fails but we have a valid token, keep using it
                if self._access_token and self._token_expiry and current_time < self._token_expiry:
                    logger.warning("Token retrieval failed but current token still valid. Reusing existing token.")
                    return self._access_token
                logger.error("Token retrieval failed and no valid token available")
                raise Exception("Failed to retrieve valid token")
        
        # Track token usage
        self._requests_made += 1
        if self.tokens_file_path and self._requests_made % 10 == 0:
            # Update the file with request count every 10 requests
            self._update_token_file_metadata()
            
        return self._access_token
    
    def _retrieve_token_with_retry(self):
        """Retrieve a token with retry logic"""
        max_retries = 3
        base_wait = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = base_wait * (2 ** (attempt - 1))
                    logger.info(f"Retrying token retrieval in {wait_time} seconds (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                
                result = self._retrieve_token()
                if result:
                    return True
                    
            except Exception as e:
                logger.error(f"Error during token retrieval attempt {attempt+1}/{max_retries}: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error("All token retrieval attempts failed")
                    return False
        
        return False
    
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
                return False
                
            data = response.json()
            
            if 'accessToken' not in data:
                logger.error("No accessToken in response")
                return False
                
            # Store the token and calculate expiry time
            self._access_token = data['accessToken']
            
            # Calculate expiry time in seconds since epoch
            if 'accessTokenExpirationTimestampMs' in data:
                # Convert from milliseconds to seconds
                self._token_expiry = data['accessTokenExpirationTimestampMs'] / 1000
            else:
                # Default to 1 hour from now if no expiry provided
                self._token_expiry = time.time() + 3600
                
            # Reset request counter for new token
            self._requests_made = 0
                
            logger.info(f"Token retrieved successfully, expires at {datetime.fromtimestamp(self._token_expiry)}")
            
            # Save token to file if path provided
            if self.tokens_file_path:
                self._save_token_to_file(data)
                
            return True
                
        except Exception as e:
            logger.error(f"Error retrieving token: {str(e)}")
            return False
    
    def _save_token_to_file(self, token_data):
        """Save token data to file for debugging/compatibility"""
        try:
            # Add metadata about usage
            metadata = {
                "auth_token": token_data['accessToken'],
                "expiry_timestamp": token_data.get('accessTokenExpirationTimestampMs', time.time() * 1000 + 3600 * 1000),
                "last_updated": time.time() * 1000,
                "client_token": "",  # For backward compatibility
                "requests_made": 0,  # Reset usage count
            }
                
            with open(self.tokens_file_path, 'w') as f:
                json.dump(metadata, f, indent=2)
                
            logger.info(f"Token data saved to {self.tokens_file_path}")
        except Exception as e:
            logger.error(f"Error saving token to file: {str(e)}")
    
    def _update_token_file_metadata(self):
        """Update the token file with latest metadata"""
        try:
            if not self.tokens_file_path or not os.path.exists(self.tokens_file_path):
                return
                
            with open(self.tokens_file_path, 'r') as f:
                data = json.load(f)
            
            # Update metadata
            data['requests_made'] = self._requests_made
            data['last_used'] = time.time() * 1000
            
            with open(self.tokens_file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error updating token file metadata: {str(e)}")
            
    def get_authorization_header(self):
        """
        Get a properly formatted authorization header using the current token
        
        Returns:
            Dict: Header dict with authorization
        """
        token = self.get_token()
        return {"Authorization": f"Bearer {token}"}
        
    def check_token_health(self):
        """Check token health and provide diagnostic information"""
        current_time = time.time() * 1000  # ms
        
        status = {
            "has_token": self._access_token is not None,
            "token_valid": False,
            "time_remaining_sec": 0,
            "requests_since_refresh": self._requests_made,
            "last_used_sec_ago": 0
        }
        
        # Check token validity and time remaining
        if self._access_token and self._token_expiry:
            time_remaining = self._token_expiry - (current_time / 1000)
            status["token_valid"] = time_remaining > 0
            status["time_remaining_sec"] = int(time_remaining)
        
        # Load metadata from file
        if self.tokens_file_path and os.path.exists(self.tokens_file_path):
            try:
                with open(self.tokens_file_path, 'r') as f:
                    data = json.load(f)
                    if 'last_used' in data:
                        status["last_used_sec_ago"] = int((current_time - data.get('last_used', current_time)) / 1000)
            except Exception as e:
                logger.error(f"Error reading token file: {str(e)}")
        
        return status
