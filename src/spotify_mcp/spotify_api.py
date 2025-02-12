import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from .artists import ArtistDatabase
from .models import Artist

class Client:
    """Spotify API Client with batch processing capabilities"""
    
    def __init__(self, logger: logging.Logger, db_path: str):
        self.logger = logger
        self.db_path = db_path
        self.MAX_BATCH_SIZE = 50
        # Initialize Spotify client with environment variables
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
            scope="user-library-read playlist-read-private"
        ))
        # Initialize artist database
        self.db = ArtistDatabase(db_path, logger)


    async def get_info(self, item_id: str, qtype: str = "track") -> Dict[str, Any]:
        """Get information about a Spotify item"""
        self.logger.info(f"Getting info for {qtype} with ID {item_id}")
        
        try:
            if qtype == "artist":
                # Check if it's a batch request (comma-separated IDs)
                if ',' in item_id:
                    artist_ids = [aid.strip() for aid in item_id.split(',')]
                    self.logger.info(f"Batch request detected for {len(artist_ids)} artists")
                    return await self.get_artists_batch(artist_ids)
                
                # Single artist request
                self.logger.info(f"Getting info for single artist {item_id}")
                artist_data = self.sp.artist(item_id)
                
                try:
                    # Convert to Artist model
                    artist = Artist.from_spotify_data(artist_data)
                    self.logger.info(f"Converting Spotify data to Artist model for {artist.name}")
                    
                    # Save to database
                    if self.db.save_artist(artist):
                        self.logger.info(f"Successfully saved artist {artist.name} to database")
                    else:
                        self.logger.warning(f"Failed to save artist {artist.name} to database")
                        
                except Exception as e:
                    self.logger.error(f"Error processing artist data: {str(e)}")
                    # Still return the data even if saving fails
                    
                return artist_data
        
        except Exception as e:
            self.logger.error(f"Error fetching artist(s): {str(e)}")
            raise

    def search(self, query: str, qtype: str = "track", limit: int = 10) -> Dict[str, Any]:
        """Search for items on Spotify"""
        self.logger.info(f"Searching for {qtype} with query: {query}")
        try:
            return self.sp.search(q=query, type=qtype, limit=limit)
        except Exception as e:
            self.logger.error(f"Search error: {str(e)}")
            raise

    async def get_artists_batch(self, artist_ids: List[str]) -> Dict[str, Any]:
        """Get multiple artists in one request"""
        if not artist_ids:
            raise ValueError("Artist IDs list cannot be empty")
            
        if len(artist_ids) > self.MAX_BATCH_SIZE:
            self.logger.warning(f"Request exceeds maximum batch size of {self.MAX_BATCH_SIZE}")
            artist_ids = artist_ids[:self.MAX_BATCH_SIZE]
            
        try:
            # Use Spotify's artists endpoint
            response = self.sp.artists(artist_ids)
            
            self.logger.info(f"Successfully retrieved {len(response['artists'])} artists")
            return response
            
        except Exception as e:
            self.logger.error(f"Error in batch artist fetch: {str(e)}")
            raise

    # Playback control methods
    def get_current_track(self):
        try:
            return self.sp.current_playback()
        except:
            return None

    def start_playback(self, track_id=None):
        if track_id:
            self.sp.start_playback(uris=[f"spotify:track:{track_id}"])
        else:
            self.sp.start_playback()

    def pause_playback(self):
        self.sp.pause_playback()

    def skip_track(self, n=1):
        for _ in range(n):
            self.sp.next_track()

    def add_to_queue(self, track_id):
        self.sp.add_to_queue(uri=f"spotify:track:{track_id}")

    def get_queue(self):
        try:
            return self.sp.queue()
        except:
            return {"queue": []}