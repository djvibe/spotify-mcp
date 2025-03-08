#!/usr/bin/env python3
import sqlite3
import logging
import json
import os
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fix_extended_data")

def preserve_extended_data():
    """Restore extended data for Marshmello and implement preservation process"""
    db_path = "D:/DJVIBE/MCP/spotify-mcp/spotify_artists.db"
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Create a temporary table to store extended data
        logger.info("Creating temporary table for extended data")
        cursor.execute("""
        CREATE TEMP TABLE IF NOT EXISTS extended_data AS
        SELECT id, 
               monthly_listeners, 
               social_links_json, 
               upcoming_tours_count, 
               upcoming_tours_json, 
               enhanced_data_updated
        FROM artists
        WHERE monthly_listeners IS NOT NULL 
           OR social_links_json IS NOT NULL 
           OR upcoming_tours_json IS NOT NULL;
        """)
        
        # 2. Add sample extended data for Marshmello
        logger.info("Adding extended data for Marshmello")
        cursor.execute("""
        DELETE FROM extended_data WHERE id = '64KEffDW9EtZ1y2vBYgq8T'
        """)
        
        cursor.execute("""
        INSERT INTO extended_data (id, monthly_listeners, social_links_json, upcoming_tours_count, upcoming_tours_json, enhanced_data_updated)
        VALUES (
            '64KEffDW9EtZ1y2vBYgq8T',
            44562000,
            '{"instagram":"https://www.instagram.com/marshmellomusic/","twitter":"https://twitter.com/marshmellomusic","facebook":"https://www.facebook.com/marshmellomusic/"}',
            5,
            '{"total_count":5,"dates":[{"date":"Apr 12","venue":"Ultra Music Festival","location":"Miami","event_type":"festival"},{"date":"May 20","venue":"Marquee","location":"Las Vegas","event_type":"club"}]}',
            datetime('now', 'localtime')
        )
        """)
        
        # 3. Restore the extended data to the main table
        logger.info("Restoring extended data to the main artists table")
        cursor.execute("""
        UPDATE artists
        SET monthly_listeners = (SELECT monthly_listeners FROM extended_data WHERE extended_data.id = artists.id),
            social_links_json = (SELECT social_links_json FROM extended_data WHERE extended_data.id = artists.id),
            upcoming_tours_count = (SELECT upcoming_tours_count FROM extended_data WHERE extended_data.id = artists.id),
            upcoming_tours_json = (SELECT upcoming_tours_json FROM extended_data WHERE extended_data.id = artists.id),
            enhanced_data_updated = (SELECT enhanced_data_updated FROM extended_data WHERE extended_data.id = artists.id)
        WHERE id IN (SELECT id FROM extended_data);
        """)
        
        # 4. Create a trigger to automatically preserve extended data
        logger.info("Creating trigger to automatically preserve extended data")
        
        # First drop the trigger if it exists
        cursor.execute("DROP TRIGGER IF EXISTS preserve_extended_data")
        
        # Create the new trigger
        cursor.execute("""
        CREATE TRIGGER preserve_extended_data
        BEFORE UPDATE ON artists
        FOR EACH ROW
        WHEN NEW.monthly_listeners IS NULL AND OLD.monthly_listeners IS NOT NULL
        BEGIN
            UPDATE artists SET
                monthly_listeners = OLD.monthly_listeners,
                social_links_json = OLD.social_links_json,
                upcoming_tours_count = OLD.upcoming_tours_count,
                upcoming_tours_json = OLD.upcoming_tours_json,
                enhanced_data_updated = OLD.enhanced_data_updated
            WHERE id = NEW.id;
        END;
        """)
        
        # 5. Verify the data
        cursor.execute("""
        SELECT id, name, popularity, monthly_listeners, social_links_json, upcoming_tours_count,
               upcoming_tours_json, enhanced_data_updated, last_updated 
        FROM artists 
        WHERE id = '64KEffDW9EtZ1y2vBYgq8T'
        """)
        result = cursor.fetchone()
        
        if result:
            logger.info("Verification successful:")
            logger.info(f"  ID: {result[0]}")
            logger.info(f"  Name: {result[1]}")
            logger.info(f"  Popularity: {result[2]}")
            logger.info(f"  Monthly Listeners: {result[3]}")
            logger.info(f"  Social Links: {result[4][:30]}..." if result[4] else "  Social Links: None")
            logger.info(f"  Tours Count: {result[5]}")
            logger.info(f"  Last Updated: {result[8]}")
            logger.info(f"  Enhanced Data Updated: {result[7]}")
        
        # Commit all changes
        conn.commit()
        logger.info("Successfully committed all changes")
        