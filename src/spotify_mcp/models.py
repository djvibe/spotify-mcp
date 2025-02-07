from dataclasses import dataclass, asdict
from json import JSONEncoder
from typing import List, Optional
from enum import Enum

@dataclass
class Image:
    def to_dict(self):
        return asdict(self)

    def __repr__(self):
        return str(self.to_dict())

    def __str__(self):
        return self.__repr__()
    height: Optional[int]
    url: str
    width: Optional[int]

@dataclass
class ExternalUrl:
    def to_dict(self):
        return asdict(self)

    def __repr__(self):
        return str(self.to_dict())

    def __str__(self):
        return self.__repr__()
    spotify: str

@dataclass
class Followers:
    def to_dict(self):
        return asdict(self)

    def __repr__(self):
        return str(self.to_dict())

    def __str__(self):
        return self.__repr__()
    href: Optional[str]
    total: int

@dataclass
class Artist:
    def to_dict(self):
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
            'type': self.type
        }

    def __repr__(self):
        return str(self.to_dict())

    def __str__(self):
        return self.__repr__()
    """Complete Artist object matching Spotify API spec"""
    id: str
    name: str
    external_urls: ExternalUrl
    followers: Followers
    genres: List[str]
    href: str
    images: List[Image]
    popularity: int
    uri: str
    type: str = "artist"  # Moved type to the end since it has a default value

@dataclass
class ArtistAlbum:
    """Album release by an artist"""
    id: str
    name: str
    release_date: str
    total_tracks: int
    album_type: str
    images: List[Image]

class AlbumType(Enum):
    ALBUM = "album"
    SINGLE = "single"
    COMPILATION = "compilation"
    APPEARS_ON = "appears_on"