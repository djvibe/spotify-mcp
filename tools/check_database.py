#!/usr/bin/env python3
import os
import sys
import json
import sqlite3
import argparse
from datetime import datetime

# Parse arguments
parser = argparse.ArgumentParser(description="Check database structure and artist data")
parser.add_argument("--db-path", required=True, help="Path to SQLite database")
parser.add_argument("--artist-id", help="Artist ID to check (optional)")
args = parser.parse_args()

# Connect to database
conn = sqlite3.connect(args.db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Print database structure
print("\n=== DATABASE TABLES ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
for table in tables:
    table_name = table['name']
    print(f"\n[TABLE: {table_name}]")
    
    # Get columns for this table
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    print("Columns:")
    for col in columns:
        print(f"  - {col['name']} ({col['type']})")

# If artist ID provided, show artist data
if args.artist_id:
    print(f"\n=== ARTIST DATA FOR ID: {args.artist_id} ===")
    
    # Check if artist exists
    cursor.execute("SELECT * FROM artists WHERE id = ?", (args.artist_id,))
    artist = cursor.fetchone()
    
    if artist:
        print("\nArtist Record:")
        for key in artist.keys():
            # Format JSON fields for better readability
            if key in ['external_urls', 'followers', 'genres', 'images', 'social_links_json', 'upcoming_tours_json']:
                try:
                    value = json.dumps(json.loads(artist[key]), indent=2) if artist[key] else None
                except:
                    value = artist[key]
            else:
                value = artist[key]
            
            print(f"  {key}: {value}")
        
        # Check stats history
        print("\nStats History:")
        cursor.execute("SELECT * FROM artist_stats_history WHERE artist_id = ? ORDER BY snapshot_date DESC LIMIT 5", (args.artist_id,))
        stats = cursor.fetchall()
        if stats:
            for stat in stats:
                stat_dict = dict(stat)
                date = stat_dict.get('snapshot_date', 'Unknown')
                popularity = stat_dict.get('popularity', 'Unknown')
                followers = stat_dict.get('follower_count', 'Unknown')
                monthly = stat_dict.get('monthly_listeners', 'Unknown')
                
                print(f"  {date}: Popularity={popularity}, Followers={followers}, Monthly Listeners={monthly}")
        else:
            print("  No stats history found")
    else:
        print("  Artist not found in database")

# Close connection
conn.close()
