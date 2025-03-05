import sqlite3
import sys
import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger()

def add_enhanced_data_column(db_path):
    """Add enhanced_data_updated column to the artists table if it doesn't exist"""
    try:
        logger.info(f"Connecting to database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(artists)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "enhanced_data_updated" in columns:
            logger.info("Column 'enhanced_data_updated' already exists")
        else:
            logger.info("Adding 'enhanced_data_updated' column to artists table")
            cursor.execute("ALTER TABLE artists ADD COLUMN enhanced_data_updated TIMESTAMP")
            conn.commit()
            logger.info("Column added successfully")
        
        # Verify table structure
        cursor.execute("PRAGMA table_info(artists)")
        columns = cursor.fetchall()
        logger.info("Current table structure:")
        for col in columns:
            logger.info(f"  {col[1]} ({col[2]})")
        
        conn.close()
        logger.info("Database update completed")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "D:/DJVIBE/MCP/spotify-mcp/spotify_artists.db"
        
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        sys.exit(1)
        
    success = add_enhanced_data_column(db_path)
    sys.exit(0 if success else 1)
