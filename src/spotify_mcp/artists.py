import logging
import sqlite3
from typing import List, Optional, Dict, Any
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
                    last_updated TIMESTAMP,
                    monthly_listeners INTEGER,
                    social_links_json TEXT,
                    upcoming_tours_count INTEGER,
                    upcoming_tours_json TEXT,
                    enhanced_data_updated TIMESTAMP,
                    data_sources TEXT
                )
            ''')
            conn.commit()

    def save_artists_batch(self, artists: List[Artist]) -> Dict[str, List[str]]:
        """
        Save multiple artists in one transaction.
        Returns dict with successful and failed IDs.
        """
        results = {
            'successful': [],
            'failed': [],
            'errors': {}
        }
        
        if not artists:
            return results
            
        try:
            with self.get_connection() as conn:
                for artist in artists:
                    try:
                        data = artist.to_db_dict()
                        placeholders = ', '.join('?' * len(data))
                        columns = ', '.join(data.keys())
                        values = tuple(data.values())
                        
                        query = f'''
                            INSERT OR REPLACE INTO artists ({columns})
                            VALUES ({placeholders})
                        '''
                        conn.execute(query, values)
                        results['successful'].append(artist.id)
                        
                    except Exception as e:
                        self.logger.error(f"Error saving artist {artist.id}: {str(e)}")
                        results['failed'].append(artist.id)
                        results['errors'][artist.id] = str(e)
                
                conn.commit()
                self.logger.info(f"Batch save completed: {len(results['successful'])} successful, {len(results['failed'])} failed")
                
        except Exception as e:
            self.logger.error(f"Batch save transaction failed: {str(e)}")
            # If transaction fails, all unsaved artists are considered failed
            pending = [artist.id for artist in artists 
                      if artist.id not in results['successful']]
            results['failed'].extend(pending)
            results['errors']['transaction'] = str(e)
            
        return results

    def save_artist(self, artist: Artist) -> bool:
        """Save or update single artist in database with smart field preservation."""
        try:
            # Check if artist already exists with extended data
            existing = self.get_artist(artist.id)
            
            if existing:
                # Smart merge: preserve extended fields from Partner API
                if artist.data_sources.get('id', 'api') == 'api':
                    # This is a standard API update
                    self.logger.info(f"Smart merging artist {artist.name} to preserve extended data")
                    
                    # Copy extended fields from existing record if they exist
                    if existing.monthly_listeners is not None:
                        artist.monthly_listeners = existing.monthly_listeners
                        artist.data_sources['monthly_listeners'] = existing.data_sources.get('monthly_listeners', 'partner_api')
                        
                    if existing.social_links_json is not None:
                        artist.social_links_json = existing.social_links_json
                        artist.data_sources['social_links_json'] = existing.data_sources.get('social_links_json', 'partner_api')
                        
                    if existing.upcoming_tours_count is not None:
                        artist.upcoming_tours_count = existing.upcoming_tours_count
                        artist.data_sources['upcoming_tours_count'] = existing.data_sources.get('upcoming_tours_count', 'partner_api')
                        
                    if existing.upcoming_tours_json is not None:
                        artist.upcoming_tours_json = existing.upcoming_tours_json
                        artist.data_sources['upcoming_tours_json'] = existing.data_sources.get('upcoming_tours_json', 'partner_api')
                        
                    if existing.enhanced_data_updated is not None:
                        artist.enhanced_data_updated = existing.enhanced_data_updated
                        artist.data_sources['enhanced_data_updated'] = existing.data_sources.get('enhanced_data_updated', 'partner_api')
            
            # Perform the database save
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
                
                if existing and existing.monthly_listeners is not None:
                    self.logger.info(f"Saved artist {artist.name} ({artist.id}) to database while preserving extended data")
                else:    
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

    def get_artists_batch(self, artist_ids: List[str]) -> Dict[str, Any]:
        """
        Retrieve multiple artists from database.
        Returns dict with found artists and missing IDs.
        """
        results = {
            'found': [],
            'missing': [],
            'errors': {}
        }
        
        if not artist_ids:
            return results
            
        try:
            with self.get_connection() as conn:
                # Use single query with IN clause for efficiency
                placeholders = ','.join('?' * len(artist_ids))
                cursor = conn.execute(
                    f'SELECT * FROM artists WHERE id IN ({placeholders})',
                    artist_ids
                )
                
                rows = cursor.fetchall()
                found_ids = set()
                
                for row in rows:
                    try:
                        artist = Artist.from_db_dict(dict(row))
                        results['found'].append(artist)
                        found_ids.add(row['id'])
                    except Exception as e:
                        self.logger.error(f"Error parsing artist {row['id']}: {str(e)}")
                        results['errors'][row['id']] = str(e)
                
                # Identify missing artists
                results['missing'] = [aid for aid in artist_ids 
                                    if aid not in found_ids]
                
        except Exception as e:
            self.logger.error(f"Batch retrieval failed: {str(e)}")
            results['errors']['query'] = str(e)
            results['missing'] = artist_ids
            
        return results