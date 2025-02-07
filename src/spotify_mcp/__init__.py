from .models import Artist, ArtistAlbum, AlbumType, Image, ExternalUrl, Followers
from .spotify_api import Client
from . import server
import asyncio

__all__ = ['Artist', 'ArtistAlbum', 'AlbumType', 'Image', 'ExternalUrl', 'Followers', 'Client']

def main():
    """Main entry point for the package."""
    asyncio.run(server.main())