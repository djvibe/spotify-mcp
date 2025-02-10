import os
import sqlite3
import logging
from pathlib import Path

def setup_database(db_path: str = "spotify_artists.db"):
    """Initialize the Spotify artists database."""
    try:
        # Create directory if it doesn't exist
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        # Connect and create tables
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create artists table
        cursor.execute('''
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

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_artist_name ON artists(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_updated ON artists(last_updated)')

        conn.commit()
        print(f"Database initialized successfully at {db_path}")
        return True

    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    # Get database path from environment or use default
    db_path = os.getenv("SPOTIFY_DB_PATH", "spotify_artists.db")
    setup_database(db_path)