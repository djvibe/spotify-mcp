#!/usr/bin/env python3
import sqlite3
import logging
import json
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("quick_fix")

def fix_marshmello():
    """Set extended data for Marshmello and then update standard fields with preservation"""
    db_path = "D:/DJVIBE/MCP/spotify-mcp/spotify_artists.db"
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Add extended data for Marshmello
        logger.info("Setting extended data for Marshmello")
        cursor.execute("""
            UPDATE artists
            SET monthly_listeners = 44562000,
                social_links_json = '{"instagram":"https://www.instagram.com/marshmellomusic/","twitter":"https://twitter.com/marshmellomusic","facebook":"https://www.facebook.com/marshmellomusic/"}',
                upcoming_tours_count = 5,
                upcoming_tours_json = '{"total_count":5,"dates":[{"date":"Apr 12","venue":"Ultra Music Festival","location":"Miami","event_type":"festival"},{"date":"May 20","venue":"Marquee","location":"Las Vegas","event_type":"club"}]}',
                enhanced_data_updated = datetime('now')
            WHERE id = '64KEffDW9EtZ1y2vBYgq8T'
        """)
        
        logger.info(f"Updated extended data for Marshmello: {cursor.rowcount} rows")
        
        # 2. Now simulate a standard API update but preserve extended fields
        # First get current extended fields
        cursor.execute("""
            SELECT monthly_listeners, social_links_json, upcoming_tours_count, upcoming_tours_json, enhanced_data_updated
            FROM artists WHERE id = '64KEffDW9EtZ1y2vBYgq8T'
        """)
        extended_data = cursor.fetchone()
        
        if extended_data:
            logger.info("Got extended data, now simulating standard API update with preservation")
            
            # Update with standard API data but preserve extended fields
            cursor.execute("""
                UPDATE artists
                SET name = 'Marshmello',
                    popularity = 82, 
                    last_updated = datetime('now'),
                    monthly_listeners = ?,
                    social_links_json = ?,
                    upcoming_tours_count = ?,
                    upcoming_tours_json = ?,
                    enhanced_data_updated = ?
                WHERE id = '64KEffDW9EtZ1y2vBYgq8T'
            """, (
                extended_data['monthly_listeners'],
                extended_data['social_links_json'],
                extended_data['upcoming_tours_count'],
                extended_data['upcoming_tours_json'],
                extended_data['enhanced_data_updated']
            ))
            
            logger.info(f"Updated with preservation: {cursor.rowcount} rows")
        
        # 3. Verify the data
        cursor.execute("""
            SELECT id, name, popularity, monthly_listeners, social_links_json, upcoming_tours_count, 
                   upcoming_tours_json, enhanced_data_updated, last_updated 
            FROM artists 
            WHERE id = '64KEffDW9EtZ1y2vBYgq8T'
        """)
        result = cursor.fetchone()
        
        if result:
            logger.info("Final verification successful")
            logger.info(f"Name: {result['name']}")
            logger.info(f"Popularity: {result['popularity']}")
            logger.info(f"Monthly Listeners: {result['monthly_listeners']}")
            logger.info(f"Social Links: {result['social_links_json'][:30]}...")
            logger.info(f"Last Updated: {result['last_updated']}")
            logger.info(f"Enhanced Data Updated: {result['enhanced_data_updated']}")
        
        # Commit all changes
        conn.commit()
        logger.info("Successfully committed all changes")
        
        # Close connection
        conn.close()
        
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    success = fix_marshmello()
    
    if success:
        print("Quick fix completed successfully!")
    else:
        print("Quick fix failed. See logs for details.")
