#!/usr/bin/env python3
import os
import sys
import json
import logging
import asyncio
import argparse
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sqlite3
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("unified_update.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("unified_update")

class SpotifyTokenManager:
    """
    Manages Spotify access tokens with automatic retrieval and renewal.
    Implements intelligent caching, retry logic, and token reuse to avoid rate limiting.
    """
    
    def __init__(self, tokens_file_path=None):
        """Initialize the token manager with optional path to save tokens"""
        self.tokens_file_path = tokens_file_path
        self._access_token = None
        self._token_expiry = None
        self._token_refresh_buffer = 300  # Refresh token 5 minutes before expiry
        self._requests_made = 0  # Track the number of requests made with this token
        
        # Try to load existing token from file if available
        if tokens_file_path and os.path.exists(tokens_file_path):
            self._load_token_from_file()
    
    def _load_token_from_file(self):
        """Load token data from file if available and still valid"""
        try:
            with open(self.tokens_file_path, 'r') as f:
                token_data = json.load(f)
                
            # Check if token exists and is still valid
            if 'auth_token' in token_data:
                self._access_token = token_data['auth_token']
                
                # Get expiry time if available
                if 'expiry_timestamp' in token_data:
                    self._token_expiry = token_data['expiry_timestamp'] / 1000  # Convert ms to seconds
                elif 'expiry_time' in token_data:
                    self._token_expiry = token_data['expiry_time']
                else:
                    # Default to 1 hour from last save if no expiry provided
                    if 'last_updated' in token_data:
                        self._token_expiry = token_data['last_updated'] / 1000 + 3600
                    else:
                        self._token_expiry = time.time() + 3600
                
                # Loa