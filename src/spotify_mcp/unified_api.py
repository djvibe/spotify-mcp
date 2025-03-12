
# src/spotify_mcp/unified_api.py
import os
import sys
import json
import logging
import asyncio
from datetime import datetime
import subprocess
from typing import List, Dict, Any, Optional

from .models import Artist
from .spotify_api import Client as SpotifyClient
from .artists import ArtistDatabase

# Import from project root for Partner API
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from spotify_token_manager import SpotifyTokenManager
from spotify_partner_api import SpotifyPartnerAPI

class UnifiedSpotifyAPI:
    """Combined standard and partner Spotify API client."""
    
    def __init__(self, db_path: str, logger: Optional[logging.Logger] = None, tokens_file_path: Optional[str] = None,
                 client_id: Optional[str] = None, client_secret: Optional[str] = None, redirect_uri: Optional[str] = None):
        """Initialize with both standard and partner API clients.
        
        Args:
            db_path: Path to SQLite database
            logger: Optional logger instance
            tokens_file_path: Optional path to tokens file for Partner API
            client_id: Optional Spotify client ID (defaults to env var SPOTIFY_CLIENT_ID)
            client_secret: Optional Spotify client secret (defaults to env var SPOTIFY_CLIENT_SECRET)
            redirect_uri: Optional Spotify redirect URI (defaults to env var SPOTIFY_REDIRECT_URI)
        """
        self.db_path = db_path
        self.logger = logger or logging.getLogger(__name__)
        
        # Set standard API credentials (env vars or provided values)
        self.client_id = client_id or os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("SPOTIFY_REDIRECT_URI")
        
        # Log the Spotify API credentials being used (partial for security)
        if self.client_id and self.client_secret:
            masked_secret = self.client_secret[:4] + "*" * (len(self.client_secret) - 8) + self.client_secret[-4:]
            self.logger.info(f"Using Spotify API credentials - Client ID: {self.client_id}, Secret: {masked_secret}")
        else:
            self.logger.warning("Spotify API credentials not found in environment variables or parameters")
        
        # Initialize standard API client (uses the credentials from env vars or parameters)
        self.standard_client = SpotifyClient(self.logger, db_path)
        
        # Database connection
        self.db = ArtistDatabase(db_path, self.logger)
        
        # Set up token management for Partner API
        # Using a single shared token manager to maximize token reuse
        self.tokens_file_path = tokens_file_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "tokens.json"
        )
        self.logger.info(f"Using tokens file: {self.tokens_file_path}")
        self.token_manager = SpotifyTokenManager(self.tokens_file_path)
        self.partner_api = SpotifyPartnerAPI(token_manager=self.token_manager)
        
        # Partner API tool paths (for legacy/fallback support)
        self.tools_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools")
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "output")
        self.partner_update_script = os.path.join(self.tools_dir, "update_artist_from_enhanced_data.py")
        self.partner_fetch_script = os.path.join(os.path.dirname(self.tools_dir), "tests", "test_spotify_api.py")
        
    async def update_artist(self, artist_id: str, force_standard: bool = False, 
                           force_partner: bool = False) -> Optional[Artist]:
        """
        Update artist with both standard and partner API data as needed.
        
        Args:
            artist_id: Spotify artist ID
            force_standard: Force standard API update regardless of schedule
            force_partner: Force partner API update regardless of schedule
            
        Returns:
            Updated artist object with combined data
        """
        # 1. Get existing artist from database
        existing = self.db.get_artist(artist_id)
        
        # 2. Determine which APIs to call based on update schedule
        needs_standard = force_standard or self._needs_standard_update(existing)
        needs_partner = force_partner or self._needs_partner_update(existing)
        
        update_result = {
            "artist_id": artist_id,
            "standard_updated": False,
            "partner_updated": False,
            "errors": []
        }
        
        # 3. Update with standard API if needed
        if needs_standard:
            self.logger.info(f"Updating artist {artist_id} with standard API")
            try:
                await self.standard_client.get_info(artist_id, qtype="artist")
                update_result["standard_updated"] = True
            except Exception as e:
                error_msg = f"Standard API update failed: {str(e)}"
                self.logger.error(error_msg)
                update_result["errors"].append(error_msg)
        
        # 4. Update with partner API if needed
        if needs_partner:
            self.logger.info(f"Updating artist {artist_id} with partner API")
            try:
                partner_updated = await self._update_with_partner_api(artist_id)
                update_result["partner_updated"] = partner_updated
                if not partner_updated:
                    update_result["errors"].append("Partner API update failed")
            except Exception as e:
                error_msg = f"Partner API update failed: {str(e)}"
                self.logger.error(error_msg)
                update_result["errors"].append(error_msg)
        
        # 5. Get the updated artist from database
        updated_artist = self.db.get_artist(artist_id)
        
        # 6. Add update status to artist data for reference
        if updated_artist and hasattr(updated_artist, 'data_sources'):
            if not updated_artist.data_sources:
                updated_artist.data_sources = {}
            updated_artist.data_sources["update_status"] = update_result
        
        return updated_artist
    
    async def _update_with_partner_api(self, artist_id: str) -> bool:
        """Update artist with partner API data."""
        try:
            # Try direct API method first (preferred approach)
            success = await self._update_with_direct_partner_api(artist_id)
            if success:
                return True
                
            # If direct API fails, fall back to command-line tools
            self.logger.warning(f"Direct Partner API update failed for {artist_id}, falling back to command-line tools")
            return await self._update_with_partner_api_tools(artist_id)
            
        except Exception as e:
            self.logger.error(f"Error updating with Partner API: {str(e)}")
            return False
    
    async def _update_with_direct_partner_api(self, artist_id: str) -> bool:
        """Update artist with Partner API using direct API integration."""
        try:
            # Get artist details from Partner API
            # The token manager will intelligently reuse existing tokens when valid
            self.logger.info(f"Getting Partner API data for artist {artist_id} using token manager")
            token_health = self.token_manager.check_token_health()
            if token_health["has_token"] and token_health["token_valid"]:
                self.logger.info(f"Using existing token with {token_health['time_remaining_sec']} seconds remaining")
            else:
                self.logger.info("No valid token available, will retrieve a new one")
                
            artist_data = self.partner_api.get_artist_details(artist_id)
            if not artist_data:
                self.logger.error(f"Failed to get Partner API data for artist {artist_id}")
                return False
                
            # Extract metrics from API response
            metrics = self.partner_api.extract_artist_metrics(artist_data)
            if not metrics:
                self.logger.error(f"Failed to extract metrics for artist {artist_id}")
                return False
                
            # Get existing artist from database
            artist = self.db.get_artist(artist_id)
            if not artist:
                self.logger.error(f"Artist {artist_id} not found in database")
                return False
                
            # Update artist with enhanced data
            artist.monthly_listeners = metrics.get("monthly_listeners")
            artist.enhanced_data_updated = datetime.now()
            
            # Save social links and upcoming tours as JSON
            social_links = metrics.get("social_links", {})
            if social_links:
                artist.social_links_json = json.dumps(social_links)
                
            upcoming_concerts = metrics.get("upcoming_concerts", [])
            if upcoming_concerts:
                artist.upcoming_tours_json = json.dumps(upcoming_concerts)
                artist.upcoming_tours_count = len(upcoming_concerts)
                
            # Update data sources
            if not hasattr(artist, 'data_sources') or not artist.data_sources:
                artist.data_sources = {}
            artist.data_sources["monthly_listeners"] = "partner_api"
            artist.data_sources["social_links"] = "partner_api"
            artist.data_sources["upcoming_tours"] = "partner_api"
            
            # Save to database
            self.db.save_artist(artist)
            self.logger.info(f"Successfully updated artist {artist.name} with Partner API data")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in direct Partner API update: {str(e)}")
            return False
    
    async def _update_with_partner_api_tools(self, artist_id: str) -> bool:
        """Update artist with partner API data using the existing tools (fallback)."""
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Step 1: Fetch enhanced data
        fetch_success = await self._fetch_partner_data(artist_id)
        if not fetch_success:
            return False
        
        # Step 2: Update database with enhanced data
        metrics_file = os.path.join(self.output_dir, f"{artist_id}_metrics.json")
        response_file = os.path.join(self.output_dir, f"{artist_id}_spotify_response.json")
        
        update_success = await self._update_partner_data(artist_id, metrics_file, response_file)
        return update_success
    
    async def _fetch_partner_data(self, artist_id: str) -> bool:
        """Fetch enhanced data using the test_spotify_api.py script."""
        try:
            command = [
                sys.executable,
                self.partner_fetch_script,
                "--artist-id", artist_id,
                "--output-dir", self.output_dir
            ]
            
            self.logger.debug(f"Running command: {' '.join(command)}")
            
            # Run the process asynchronously
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                self.logger.error(f"Error fetching enhanced data: {stderr.decode()}")
                return False
            
            # Verify output files exist
            metrics_file = os.path.join(self.output_dir, f"{artist_id}_metrics.json")
            response_file = os.path.join(self.output_dir, f"{artist_id}_spotify_response.json")
            
            if not (os.path.exists(metrics_file) and os.path.exists(response_file)):
                self.logger.error(f"Output files not found for artist {artist_id}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in fetch_partner_data: {str(e)}")
            return False
    
    async def _update_partner_data(self, artist_id: str, metrics_file: str, 
                                 response_file: str) -> bool:
        """Update database using the update_artist_from_enhanced_data.py script."""
        try:
            command = [
                sys.executable,
                self.partner_update_script,
                "--artist-id", artist_id,
                "--db-path", self.db_path,
                "--metrics-file", metrics_file,
                "--response-file", response_file
            ]
            
            self.logger.debug(f"Running command: {' '.join(command)}")
            
            # Run the process asynchronously
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                self.logger.error(f"Error updating database: {stderr.decode()}")
                return False
            
            self.logger.info(f"Successfully updated database with partner data for {artist_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in update_partner_data: {str(e)}")
            return False
    
    def _needs_standard_update(self, artist: Optional[Artist]) -> bool:
        """Determine if artist needs standard API update based on tier."""
        if not artist or not artist.last_updated:
            return True
            
        days_since_update = (datetime.now() - artist.last_updated).days
        
        if artist.popularity >= 75 and days_since_update >= 3:
            return True
        elif artist.popularity >= 50 and days_since_update >= 7:
            return True
        elif days_since_update >= 14:
            return True
            
        return False
    
    def _needs_partner_update(self, artist: Optional[Artist]) -> bool:
        """Determine if artist needs partner API update based on tier."""
        if not artist or not artist.enhanced_data_updated:
            return True
            
        days_since_update = (datetime.now() - artist.enhanced_data_updated).days if artist.enhanced_data_updated else float('inf')
        
        if artist.popularity >= 75 and days_since_update >= 7:
            return True
        elif artist.popularity >= 50 and days_since_update >= 14:
            return True
        elif days_since_update >= 30:
            return True
            
        return False
