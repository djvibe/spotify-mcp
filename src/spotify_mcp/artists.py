import logging
from typing import List, Optional, Dict

from .models import Artist, ArtistAlbum, AlbumType, ExternalUrl, Followers, Image

class ArtistAPI:
    """Enhanced Artist-specific functionality"""
    
    def __init__(self, sp_client, logger: logging.Logger):
        self.sp = sp_client
        self.logger = logger
    
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
        
        Args:
            artist_id: Spotify artist ID
            
        Returns:
            Dict: Artist data in dictionary format
            
        Raises:
            SpotifyException: If artist not found or API error occurs
        """
        try:
            artist_data = self.sp.artist(artist_id)
            
            artist = Artist(
                id=artist_data['id'],
                name=artist_data['name'],
                external_urls=ExternalUrl(
                    spotify=artist_data['external_urls']['spotify']
                ),
                followers=Followers(
                    href=artist_data['followers']['href'],
                    total=artist_data['followers']['total']
                ),
                genres=artist_data['genres'],
                href=artist_data['href'],
                images=self._convert_image_data(artist_data['images']),
                popularity=artist_data['popularity'],
                uri=artist_data['uri']
            )
            return artist.to_dict()
        except Exception as e:
            self.logger.error(f"Error fetching artist {artist_id}: {str(e)}")
            raise

    def get_artist_albums(
        self, 
        artist_id: str,
        album_type: Optional[List[AlbumType]] = None,
        limit: int = 20,
        offset: int = 0,
        market: Optional[str] = None
    ) -> List[Dict]:
        """
        Get artist's albums with filtering options.
        
        Args:
            artist_id: Spotify artist ID
            album_type: Optional list of album types to include
            limit: Maximum number of albums to return (1-50)
            offset: Offset for pagination
            market: Optional market code for availability filtering
            
        Returns:
            List of artist's albums matching criteria in dictionary format
        """
        try:
            # Convert enum values to strings for API
            album_types = None
            if album_type:
                album_types = ','.join(t.value for t in album_type)
                
            albums = self.sp.artist_albums(
                artist_id,
                album_type=album_types,
                limit=min(50, max(1, limit)),
                offset=offset,
                market=market
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
        """
        Get artist's top tracks in specified market.
        
        Args:
            artist_id: Spotify artist ID
            market: Market code for availability (default US)
            
        Returns:
            List of top tracks in dictionary format
        """
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
        """
        Get artists related to specified artist.
        
        Args:
            artist_id: Spotify artist ID
            
        Returns:
            List of related artists in dictionary format
        """
        try:
            results = self.sp.artist_related_artists(artist_id)
            related_artists = [
                Artist(
                    id=artist['id'],
                    name=artist['name'],
                    external_urls=ExternalUrl(
                        spotify=artist['external_urls']['spotify']
                    ),
                    followers=Followers(
                        href=artist['followers']['href'],
                        total=artist['followers']['total']
                    ),
                    genres=artist['genres'],
                    href=artist['href'],
                    images=self._convert_image_data(artist['images']),
                    popularity=artist['popularity'],
                    uri=artist['uri']
                )
                for artist in results['artists']
            ]
            return [artist.to_dict() for artist in related_artists]
        except Exception as e:
            self.logger.error(
                f"Error fetching related artists for {artist_id}: {str(e)}"
            )
            raise