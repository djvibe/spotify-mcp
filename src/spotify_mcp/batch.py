from typing import List, Dict, Optional
import logging
from datetime import datetime

from .models import Artist
from .artists import ArtistDatabase

class ArtistBatchProcessor:
    """Handles batch processing of artist data"""
    
    def __init__(self, sp_client, logger: logging.Logger, db: ArtistDatabase):
        self.sp = sp_client
        self.logger = logger
        self.db = db
        self.MAX_BATCH_SIZE = 50

    async def process_artist_batch(self, artist_ids: List[str]) -> Dict:
        """Process a batch of artist IDs"""
        if not artist_ids:
            raise ValueError("Artist IDs list cannot be empty")

        results = {
            'successful': [],
            'failed': [],
            'errors': {}
        }

        # Process in chunks of MAX_BATCH_SIZE
        for i in range(0, len(artist_ids), self.MAX_BATCH_SIZE):
            chunk = artist_ids[i:i + self.MAX_BATCH_SIZE]
            try:
                # Get artists from Spotify
                artists_data = self.sp.artists(chunk)
                
                # Process each artist in the chunk
                for artist_data in artists_data['artists']:
                    if artist_data:
                        artist = Artist.from_spotify_data(artist_data, source='api')
                        if self.db.save_artist(artist):
                            results['successful'].append(artist.id)
                        else:
                            results['failed'].append(artist.id)
                            results['errors'][artist.id] = "Database save failed"
                    else:
                        # Handle case where artist data is None
                        failed_id = chunk[len(results['successful'])]
                        results['failed'].append(failed_id)
                        results['errors'][failed_id] = "No data returned from Spotify"
                        
            except Exception as e:
                # If chunk processing fails, mark all IDs as failed
                self.logger.error(f"Error processing chunk: {str(e)}")
                for artist_id in chunk:
                    if artist_id not in results['successful']:
                        results['failed'].append(artist_id)
                        results['errors'][artist_id] = str(e)

        results['total_processed'] = len(artist_ids)
        results['success_count'] = len(results['successful'])
        results['failure_count'] = len(results['failed'])
        
        return results