from typing import List, Dict, Any
import logging

class SpotifyBatchProcessor:
    def __init__(self, sp_client, logger: logging.Logger):
        self.sp = sp_client
        self.logger = logger
        self.MAX_BATCH_SIZE = 50

    async def get_artists_batch(self, artist_ids: List[str]) -> Dict[str, Any]:
        """
        Get multiple artists' information in one API call
        """
        if not artist_ids:
            raise ValueError("Artist IDs list cannot be empty")
            
        if len(artist_ids) > self.MAX_BATCH_SIZE:
            self.logger.warning(f"Request exceeds maximum batch size of {self.MAX_BATCH_SIZE}")
            artist_ids = artist_ids[:self.MAX_BATCH_SIZE]
            
        try:
            # Spotify API accepts comma-separated IDs
            ids_string = ','.join(artist_ids)
            response = await self.sp.artists(ids_string)
            
            return {
                'artists': response['artists'],
                'total_requested': len(artist_ids),
                'total_received': len(response['artists'])
            }
            
        except Exception as e:
            self.logger.error(f"Batch artist fetch failed: {str(e)}")
            raise