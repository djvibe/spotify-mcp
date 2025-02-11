from typing import Union, List, Dict, Any
import logging

class SpotifyGetInfo:
    """Enhanced SpotifyGetInfo tool with batch processing support"""
    
    def __init__(self, spotify_api, db, logger: logging.Logger):
        self.spotify_api = spotify_api
        self.db = db
        self.logger = logger

    async def handle_request(
        self, 
        item_id: Union[str, List[str]], 
        qtype: str = 'artist',
        full_data: bool = True
    ) -> Dict[str, Any]:
        """
        Enhanced handler that supports both single and batch requests
        
        Args:
            item_id: Single ID or list of IDs
            qtype: Type of item ('artist', 'album', etc)
            full_data: Whether to fetch additional data (top tracks, albums)
        """
        try:
            # Handle batch request
            if isinstance(item_id, list):
                if qtype != 'artist':
                    raise ValueError("Batch processing only supported for artists")
                return await self._handle_batch_request(item_id, full_data)
            
            # Handle single request
            return await self._handle_single_request(item_id, qtype, full_data)
            
        except Exception as e:
            self.logger.error(f"Error in handle_request: {str(e)}")
            raise

    async def _handle_batch_request(
        self, 
        artist_ids: List[str],
        full_data: bool = True
    ) -> Dict[str, Any]:
        """Handle batch request for multiple artists"""
        # First check database for existing data
        db_results = self.db.get_artists_batch(artist_ids)
        
        # Identify which artists need to be fetched from Spotify
        to_fetch = db_results['missing']
        
        # If we need to fetch any artists
        if to_fetch:
            try:
                # Choose appropriate fetch method based on full_data flag
                if full_data:
                    spotify_results = await self.spotify_api.get_full_artists_batch(to_fetch)
                else:
                    spotify_results = await self.spotify_api.get_artists_batch(to_fetch)
                
                # Save newly fetched artists to database
                if spotify_results['successful']:
                    save_results = self.db.save_artists_batch(spotify_results['successful'])
                    
                    # Add successfully saved artists to results
                    db_results['found'].extend(save_results['successful'])
                    
                # Update errors with any API errors
                db_results['errors'].update(spotify_results['errors'])
                
            except Exception as e:
                self.logger.error(f"Error fetching artists from Spotify: {str(e)}")
                db_results['errors']['spotify_api'] = str(e)

        return {
            'artists': db_results['found'],
            'missing': db_results['missing'],
            'errors': db_results['errors'],
            'total_requested': len(artist_ids),
            'total_found': len(db_results['found'])
        }

    async def _handle_single_request(
        self, 
        item_id: str,
        qtype: str,
        full_data: bool = True
    ) -> Dict[str, Any]:
        """Handle single item request"""
        if qtype == 'artist':
            # First try database
            artist = self.db.get_artist(item_id)
            if artist:
                return artist.to_dict()
            
            # If not in database, fetch from Spotify
            try:
                if full_data:
                    data = await self.spotify_api.get_full_artist_data(item_id)
                else:
                    data = await self.spotify_api.get_artist(item_id)
                    
                # Save to database
                self.db.save_artist(data)
                return data
                
            except Exception as e:
                self.logger.error(f"Error fetching artist {item_id}: {str(e)}")
                raise
                
        elif qtype == 'album':
            return await self.spotify_api.get_album(item_id)
        elif qtype == 'track':
            return await self.spotify_api.get_track(item_id)
        elif qtype == 'playlist':
            return await self.spotify_api.get_playlist(item_id)
        else:
            raise ValueError(f"Unsupported item type: {qtype}")

    async def handle_rate_limit(self, response: Dict) -> None:
        """Handle rate limiting responses"""
        if 'error' in response and response['error'].get('status') == 429:
            retry_after = int(response.get('headers', {}).get('Retry-After', 1))
            self.logger.warning(f"Rate limited. Waiting {retry_after} seconds")
            await asyncio.sleep(retry_after)