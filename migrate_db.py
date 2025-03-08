#!/usr/bin/env python3
import sqlite3
import logging
import argparse
import os
import json
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db_migration")

def migrate_database(db_path):
    """
    Migrate the database to add extended fields and preserve existing data
    """
    logger.info(f"Starting database migration for {db_path}")
    
    # Check if file exists
    if not os.path.exists(db_path):
        logger.error(f"Database file does not exist: {db_path}")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get current schema to see which columns need to be added
        cursor.execute("PRAGMA table_info(artists)")
        columns = {row[1] for row in cursor.fetchall()}
        logger.info(f"Current schema has {len(columns)} columns")
        
        # Define the columns to add if they're missing
        columns_to_add = {
            'monthly_listeners': 'INTEGER',
            'social_links_json': 'TEXT',
            'upcoming_tours_count': 'INTEGER',
            'upcoming_tours_json': 'TEXT',
            'enhanced_data_updated': 'TIMESTAMP',
            'data_sources': 'TEXT'
        }
        
        # Add missing columns one by one
        for col_name, col_type in columns_to_add.items():
            if col_name not in columns:
                logger.info(f"Adding column {col_name} ({col_type})")
                try:
                    cursor.execute(f"ALTER TABLE artists ADD COLUMN {col_name} {col_type}")
                    logger.info(f"Added column {col_name}")
                except sqlite3.Error as e:
                    logger.error(f"Error adding column {col_name}: {str(e)}")
        
        # Initialize the data_sources column for existing records
        if 'data_sources' in columns_to_add:
            logger.info("Initializing data_sources for existing records")
            try:
                # Get all artists without data_sources
                cursor.execute("SELECT id FROM artists WHERE data_sources IS NULL")
                artist_ids = [row[0] for row in cursor.fetchall()]
                
                if artist_ids:
                    logger.info(f"Setting default data_sources for {len(artist_ids)} artists")
                    
                    # Default data source is 'api' for standard fields
                    default_sources = json.dumps({
                        'id': 'api',
                        'name': 'api',
                        'external_urls': 'api',
                        'followers': 'api',
                        'genres': 'api',
                        'href': 'api',
                        'images': 'api',
                        'popularity': 'api',
                        'uri': 'api',
                        'type': 'api'
                    })
                    
                    # Update in chunks to avoid large transactions
                    CHUNK_SIZE = 100
                    for i in range(0, len(artist_ids), CHUNK_SIZE):
                        chunk = artist_ids[i:i + CHUNK_SIZE]
                        placeholders = ','.join(['?'] * len(chunk))
                        cursor.execute(
                            f"UPDATE artists SET data_sources = ? WHERE id IN ({placeholders})",
                            [default_sources] + chunk
                        )
                        logger.info(f"Updated chunk {i//CHUNK_SIZE + 1}/{(len(artist_ids)-1)//CHUNK_SIZE + 1}")
                        
                else:
                    logger.info("No artists need data_sources initialization")
            
            except sqlite3.Error as e:
                logger.error(f"Error initializing data_sources: {str(e)}")
        
        # If artists have extended data but no enhanced_data_updated date, set it
        if 'enhanced_data_updated' in columns_to_add:
            logger.info("Setting enhanced_data_updated for artists with extended data")
            try:
                cursor.execute("""
                    UPDATE artists 
                    SET enhanced_data_updated = last_updated
                    WHERE monthly_listeners IS NOT NULL 
                    AND enhanced_data_updated IS NULL
                """)
                logger.info(f"Updated enhanced_data_updated for {cursor.rowcount} artists")
            except sqlite3.Error as e:
                logger.error(f"Error setting enhanced_data_updated: {str(e)}")
        
        # Commit all changes
        conn.commit()
        logger.info("Successfully committed all changes")
        
        # Verify the migration
        cursor.execute("PRAGMA table_info(artists)")
        updated_columns = {row[1] for row in cursor.fetchall()}
        logger.info(f"Updated schema has {len(updated_columns)} columns")
        
        # Close connection
        conn.close()
        
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Database error during migration: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during migration: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Migrate DJVIBE SQLite database to include extended fields")
    parser.add_argument("--db-path", required=True, help="Path to SQLite database file")
    
    args = parser.parse_args()
    
    success = migrate_database(args.db_path)
    
    if success:
        print("Migration completed successfully!")
        return 0
    else:
        print("Migration failed. See logs for details.")
        return 1

if __name__ == "__main__":
    exit(main())
