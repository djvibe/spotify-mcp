import logging
import sqlite3
from typing import List, Optional, Dict
from datetime import datetime
from contextlib import contextmanager

from .models import Artist, ArtistAlbum, AlbumType, ExternalUrl, Followers, Image

class ArtistDatabase:
    def __init__(self, db_path: str, logger: logging.Logger):
        self.db_path = db_path
        self.logger = logger
        self.initialize_db()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def initialize_db(self):
        """Create artists table if it doesn't exist."""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS artists (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    external_urls TEXT,
                    followers TEXT,
                    genres TEXT,
                    href TEXT,
                    images TEXT,
                    popularity INTEGER,
                    uri TEXT,
                    type TEXT,
                    last_updated TIMESTAMP
                )
            ''')
            conn.commit()

    def save_artist(self, artist: Artist) -> bool:
        """Save or update artist in database."""
        try:
            with self.get_connection() as conn:
                data = artist.to_db_dict()
                placeholders = ', '.join('?' * len(data))
                columns = ', '.join(data.keys())
                values = tuple(data.values())
                
                query = f'''
                    INSERT OR REPLACE INTO artists ({columns})
                    VALUES ({placeholders})
                '''
                conn.execute(query, values)
                conn.commit()
                self.logger.info(f"Saved artist {artist.name} ({artist.id}) to database")
                return True
        except Exception as e:
            self.logger.error(f"Error saving artist {artist.id}: {str(e)}")
            return False

    def get_artist(self, artist_id: str) -> Optional[Artist]:
        """Retrieve artist from database by ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    'SELECT * FROM artists WHERE id = ?',
                    (artist_id,)
                )
                row = cursor.fetchone()
                if row:
                    return Artist.from_db_dict(dict(row))
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving artist {artist_id}: {str(e)}")
            return None

class ArtistAPI:
    """Enhanced Artist-specific functionality with database support"""
    
    def __init__(self, sp_client, logger: logging.Logger, db_path: str):
        self.sp = sp_client
        self.logger = logger
        self.db = ArtistDatabase(db_path, logger)
    
    def _convert_image_data(self, images: List[Dict]) -> List[Image]:
        """Convert raw image data to Image objects"""
        return [
            Image(
                height=img.get('height'),
                url=img['url'],
                width=img.get('width')
            ) for img in images
        ]

    def get_artist(self, artist_id: str) -> Dict:
        """
        Get complete artist details including all available properties.
        Attempts to fetch from database first, falls back to Spotify API.
        """
        try:
            # First try to get from database
            cached_artist = self.db.get_artist(artist_id)
            if cached_artist:
                self.logger.info(f"Retrieved artist {artist_id} from database")
                return cached_artist.to_dict()

            # If not in database, fetch from Spotify
            artist_data = self.sp.artist(artist_id)
            artist = Artist.from_spotify_data(artist_data)
            
            # Save to database
            self.db.save_artist(artist)
            
            return artist.to_dict()
        except Exception as e:
            self.logger.error(f"Error fetching artist {artist_id}: {str(e)}")
            raise

    def get_artist_albums(
        self, 
        artist_id: str,
        album_type: Optional[List[AlbumType]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """Get artist's albums."""
        try:
            # Convert enum values to strings for API
            album_types = None
            if album_type:
                album_types = ','.join(t.value for t in album_type)
                
            albums = self.sp.artist_albums(
                artist_id,
                album_type=album_types,
                limit=limit,
                offset=offset
            )
            
            album_objects = [
                ArtistAlbum(
                    id=album['id'],
                    name=album['name'],
                    release_date=album['release_date'],
                    total_tracks=album['total_tracks'],
                    album_type=album['album_type'],
                    images=self._convert_image_data(album['images'])
                )
                for album in albums['items']
            ]
            
            return [album.to_dict() for album in album_objects]
        except Exception as e:
            self.logger.error(
                f"Error fetching albums for artist {artist_id}: {str(e)}"
            )
            raise

    def get_artist_top_tracks(
        self, 
        artist_id: str,
        market: str = "US"
    ) -> List[Dict]:
        """Get artist's top tracks in specified market."""
        try:
            results = self.sp.artist_top_tracks(artist_id, market)
            return [
                {
                    'id': track['id'],
                    'name': track['name'],
                    'popularity': track['popularity'],
                    'preview_url': track.get('preview_url'),
                    'duration_ms': track['duration_ms']
                }
                for track in results['tracks']
            ]
        except Exception as e:
            self.logger.error(
                f"Error fetching top tracks for artist {artist_id}: {str(e)}"
            )
            raise

    def get_related_artists(self, artist_id: str) -> List[Dict]:
        """Get artists related to specified artist."""
        try:
            results = self.sp.artist_related_artists(artist_id)
            related_artists = []
            
            for artist_data in results['artists']:
                artist = Artist.from_spotify_data(artist_data)
                # Save related artists to database
                self.db.save_artist(artist)
                related_artists.append(artist)
            
            return [artist.to_dict() for artist in related_artists]
        except Exception as e:
            self.logger.error(
                f"Error fetching related artists for {artist_id}: {str(e)}"
            )
            raise