#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
import unittest
import json
from datetime import datetime, timedelta

# Add src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.spotify_mcp.unified_api import UnifiedSpotifyAPI
from src.spotify_mcp.models import Artist

# Test artist IDs (sample artists)
TEST_ARTISTS = {
    "top_tier": "19SmlbABtI4bXz864MLqOS",  # Carl Cox (high popularity)
    "mid_tier": "5fMUXHkw8R8eOP2RNVYEZX",  # John Summit (medium popularity)
    "low_tier": "1uRxRKC7d9zwYGSRflTKDR"   # Low popularity artist
}

# Test database path
TEST_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "spotify_artists.db")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("test_unified_api.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_unified_api")

class TestUnifiedAPI(unittest.TestCase):
    """Test cases for the UnifiedSpotifyAPI class."""
    
    def setUp(self):
        self.api = UnifiedSpotifyAPI(TEST_DB_PATH, logger)
    
    async def test_single_artist_update(self):
        """Test updating a single artist."""
        artist_id = TEST_ARTISTS["top_tier"]
        artist = await self.api.update_artist(artist_id, force_standard=True, force_partner=True)
        
        self.assertIsNotNone(artist)
        self.assertEqual(artist.id, artist_id)
        self.assertIsNotNone(artist.last_updated)
        
        # Check if the update was recent (within the last hour)
        self.assertTrue(
            (datetime.now() - artist.last_updated).total_seconds() < 3600,
            "Artist was not updated recently"
        )
        
        logger.info(f"Successfully updated artist: {artist.name}")
        return artist
    
    async def test_update_scheduling(self):
        """Test the update scheduling logic."""
        # Create mock artists for each tier with different update times
        now = datetime.now()
        
        # Top tier: needs update after 3 days
        top_tier = Artist(
            id="test_top",
            name="Top Tier Artist",
            external_urls={},
            followers={},
            genres=[],
            href="",
            images=[],
            popularity=80,
            uri="",
            last_updated=now - timedelta(days=4)
        )
        
        # Mid tier: needs update after 7 days
        mid_tier = Artist(
            id="test_mid",
            name="Mid Tier Artist",
            external_urls={},
            followers={},
            genres=[],
            href="",
            images=[],
            popularity=60,
            uri="",
            last_updated=now - timedelta(days=6)
        )
        
        # Low tier: needs update after 14 days
        low_tier = Artist(
            id="test_low",
            name="Low Tier Artist",
            external_urls={},
            followers={},
            genres=[],
            href="",
            images=[],
            popularity=40,
            uri="",
            last_updated=now - timedelta(days=13)
        )
        
        # Test standard API update scheduling
        self.assertTrue(self.api._needs_standard_update(top_tier))
        self.assertFalse(self.api._needs_standard_update(mid_tier))
        self.assertFalse(self.api._needs_standard_update(low_tier))
        
        # Test partner API update scheduling
        top_tier.enhanced_data_updated = now - timedelta(days=8)
        mid_tier.enhanced_data_updated = now - timedelta(days=15)
        low_tier.enhanced_data_updated = now - timedelta(days=29)
        
        self.assertTrue(self.api._needs_partner_update(top_tier))
        self.assertTrue(self.api._needs_partner_update(mid_tier))
        self.assertFalse(self.api._needs_partner_update(low_tier))

async def run_tests():
    """Run the test cases."""
    suite = unittest.TestSuite()
    suite.addTest(TestUnifiedAPI("test_single_artist_update"))
    suite.addTest(TestUnifiedAPI("test_update_scheduling"))
    
    runner = unittest.TextTestRunner()
    runner.run(suite)

if __name__ == "__main__":
    asyncio.run(run_tests())
