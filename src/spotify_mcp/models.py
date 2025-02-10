from dataclasses import dataclass, asdict
from json import JSONEncoder, dumps, loads
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime

@dataclass
class Image:
    height: Optional[int]
    url: str
    width: Optional[int]

    def to_dict(self) -> Dict:
        return {
            'height': self.height,
            'url': self.url,
            'width': self.width
        }

    def __repr__(self):
        return str(self.to_dict())

    def __str__(self):
        return self.__repr__()

@dataclass
class ExternalUrl:
    spotify: str

    def to_dict(self) -> Dict:
        return {'spotify': self.spotify}

    def __repr__(self):
        return str(self.to_dict())

    def __str__(self):
        return self.__repr__()

@dataclass
class Followers:
    href: Optional[str]
    total: int

    def to_dict(self) -> Dict:
        return {
            'href': self.href,
            'total': self.total
        }

    def __repr__(self):
        return str(self.to_dict())

    def __str__(self):
        return self.__repr__()

@dataclass
class Artist:
    """Complete Artist object matching Spotify API spec with database support"""
    id: str
    name: str
    external_urls: ExternalUrl
    followers: Followers
    genres: List[str]
    href: str
    images: List[Image]
    popularity: int
    uri: str
    type: str = "artist"
    last_updated: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert Artist to dictionary format."""
        return {
            'id': self.id,
            'name': self.name,
            'external_urls': self.external_urls.to_dict(),
            'followers': self.followers.to_dict(),
            'genres': self.genres,
            'href': self.href,
            'images': [img.to_dict() for img in self.images],
            'popularity': self.popularity,
            'uri': self.uri,
            'type': self.type,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

    def to_db_dict(self) -> Dict:
        """Convert Artist to database-friendly format."""
        return {
            'id': self.id,
            'name': self.name,
            'external_urls': dumps(self.external_urls.to_dict()),
            'followers': dumps(self.followers.to_dict()),
            'genres': dumps(self.genres),
            'href': self.href,
            'images': dumps([img.to_dict() for img in self.images]),
            'popularity': self.popularity,
            'uri': self.uri,
            'type': self.type,
            'last_updated': self.last_updated.isoformat() if self.last_updated else datetime.utcnow().isoformat()
        }

    @classmethod
    def from_db_dict(cls, data: Dict) -> 'Artist':
        """Create Artist instance from database record."""
        return cls(
            id=data['id'],
            name=data['name'],
            external_urls=ExternalUrl(**loads(data['external_urls'])),
            followers=Followers(**loads(data['followers'])),
            genres=loads(data['genres']),
            href=data['href'],
            images=[Image(**img) for img in loads(data['images'])],
            popularity=data['popularity'],
            uri=data['uri'],
            type=data['type'],
            last_updated=datetime.fromisoformat(data['last_updated']) if data.get('last_updated') else None
        )

    @classmethod
    def from_spotify_data(cls, data: Dict) -> 'Artist':
        """Create Artist instance from Spotify API response."""
        return cls(
            id=data['id'],
            name=data['name'],
            external_urls=ExternalUrl(spotify=data['external_urls']['spotify']),
            followers=Followers(
                href=data['followers'].get('href'),
                total=data['followers']['total']
            ),
            genres=data['genres'],
            href=data['href'],
            images=[Image(**img) for img in data['images']],
            popularity=data['popularity'],
            uri=data['uri'],
            type=data.get('type', 'artist'),
            last_updated=datetime.utcnow()
        )

    def __repr__(self):
        return str(self.to_dict())

    def __str__(self):
        return self.__repr__()

@dataclass
class ArtistAlbum:
    """Album release by an artist"""
    id: str
    name: str
    release_date: str
    total_tracks: int
    album_type: str
    images: List[Image]

    def to_dict(self) -> Dict:
        """Convert album to dictionary format."""
        return {
            'id': self.id,
            'name': self.name,
            'release_date': self.release_date,
            'total_tracks': self.total_tracks,
            'album_type': self.album_type,
            'images': [img.to_dict() for img in self.images]
        }

    def __repr__(self):
        return str(self.to_dict())

    def __str__(self):
        return self.__repr__()

class AlbumType(Enum):
    ALBUM = "album"
    SINGLE = "single"
    COMPILATION = "compilation"
    APPEARS_ON = "appears_on"