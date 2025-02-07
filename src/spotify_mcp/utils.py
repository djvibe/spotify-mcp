from collections import defaultdict
from typing import Optional, Dict, List
import functools
from typing import Callable, TypeVar
from urllib.parse import quote

from .models import Artist, Image, ExternalUrl, Followers

T = TypeVar('T')


def parse_track(track_item: dict, detailed=False) -> Optional[dict]:
    if not track_item:
        return None
    narrowed_item = {
        'name': track_item['name'],
        'id': track_item['id'],
    }

    if 'is_playing' in track_item:
        narrowed_item['is_playing'] = track_item['is_playing']

    if detailed:
        narrowed_item['album'] = parse_album(track_item.get('album'))
        for k in ['track_number', 'duration_ms']:
            narrowed_item[k] = track_item.get(k)

    if not track_item.get('is_playable', True):
        narrowed_item['is_playable'] = False

    artists = [a['name'] for a in track_item['artists']]
    if detailed:
        artists = [parse_artist(a) for a in track_item['artists']]

    if len(artists) == 1:
        narrowed_item['artist'] = artists[0]
    else:
        narrowed_item['artists'] = artists

    return narrowed_item


def parse_artist(artist_item: dict, detailed=False) -> Optional[Dict]:
    """Parse artist data and return as a dictionary for JSON compatibility"""
    if not artist_item:
        return None
        
    if not detailed:
        # For non-detailed views, provide minimal info
        return {
            'id': artist_item['id'],
            'name': artist_item['name'],
            'external_urls': {'spotify': artist_item['external_urls']['spotify']},
            'href': artist_item['href'],
            'uri': artist_item['uri']
        }
    
    # For detailed views, include all available information
    artist = Artist(
        id=artist_item['id'],
        name=artist_item['name'],
        external_urls=ExternalUrl(
            spotify=artist_item['external_urls']['spotify']
        ),
        followers=Followers(
            href=artist_item['followers']['href'],
            total=artist_item['followers']['total']
        ),
        genres=artist_item.get('genres', []),
        href=artist_item['href'],
        images=[Image(
            height=img.get('height'),
            url=img['url'],
            width=img.get('width')
        ) for img in artist_item.get('images', [])],
        popularity=artist_item.get('popularity', 0),
        uri=artist_item['uri']
    )
    
    return artist.to_dict()


def parse_playlist(playlist_item: dict, detailed=False) -> Optional[dict]:
    if not playlist_item:
        return None
    narrowed_item = {
        'name': playlist_item['name'],
        'id': playlist_item['id'],
        'owner': playlist_item['owner']['display_name']
    }
    if detailed:
        narrowed_item['description'] = playlist_item.get('description')
        tracks = []
        for t in playlist_item['tracks']['items']:
            tracks.append(parse_track(t['track']))
        narrowed_item['tracks'] = tracks

    return narrowed_item


def parse_album(album_item: dict, detailed=False) -> dict:
    narrowed_item = {
        'name': album_item['name'],
        'id': album_item['id'],
    }

    artists = [a['name'] for a in album_item['artists']]

    if detailed:
        tracks = []
        for t in album_item['tracks']['items']:
            tracks.append(parse_track(t))
        narrowed_item["tracks"] = tracks
        artists = [parse_artist(a) for a in album_item['artists']]

        for k in ['total_tracks', 'release_date', 'genres']:
            narrowed_item[k] = album_item.get(k)

    if len(artists) == 1:
        narrowed_item['artist'] = artists[0]
    else:
        narrowed_item['artists'] = artists

    return narrowed_item


def parse_search_results(results: Dict, qtype: str):
    _results = defaultdict(list)

    for q in qtype.split(","):
        match q:
            case "track":
                for idx, item in enumerate(results['tracks']['items']):
                    if not item: continue
                    _results['tracks'].append(parse_track(item))
            case "artist":
                for idx, item in enumerate(results['artists']['items']):
                    if not item: continue
                    _results['artists'].append(parse_artist(item))
            case "playlist":
                for idx, item in enumerate(results['playlists']['items']):
                    if not item: continue
                    _results['playlists'].append(parse_playlist(item))
            case "album":
                for idx, item in enumerate(results['albums']['items']):
                    if not item: continue
                    _results['albums'].append(parse_album(item))
            case _:
                raise ValueError(f"unknown qtype {qtype}")

    return dict(_results)


def build_search_query(base_query: str,
                       artist: Optional[str] = None,
                       track: Optional[str] = None,
                       album: Optional[str] = None,
                       year: Optional[str] = None,
                       year_range: Optional[tuple[int, int]] = None,
                       # upc: Optional[str] = None,
                       # isrc: Optional[str] = None,
                       genre: Optional[str] = None,
                       is_hipster: bool = False,
                       is_new: bool = False
                       ) -> str:
    """
    Build a search query string with optional filters.

    Args:
        base_query: Base search term
        artist: Artist name filter
        track: Track name filter
        album: Album name filter
        year: Specific year filter
        year_range: Tuple of (start_year, end_year) for year range filter
        genre: Genre filter
        is_hipster: Filter for lowest 10% popularity albums
        is_new: Filter for albums released in past two weeks

    Returns:
        Encoded query string with applied filters
    """
    filters = []

    if artist:
        filters.append(f"artist:{artist}")
    if track:
        filters.append(f"track:{track}")
    if album:
        filters.append(f"album:{album}")
    if year:
        filters.append(f"year:{year}")
    if year_range:
        filters.append(f"year:{year_range[0]}-{year_range[1]}")
    if genre:
        filters.append(f"genre:{genre}")
    if is_hipster:
        filters.append("tag:hipster")
    if is_new:
        filters.append("tag:new")

    query_parts = [base_query] + filters
    return quote(" ".join(query_parts))


def validate(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator for Spotify API methods that handles authentication and device validation.
    - Checks and refreshes authentication if needed
    - Validates active device and retries with candidate device if needed
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Handle authentication
        if not self.auth_ok():
            self.auth_refresh()

        # Handle device validation
        if not self.is_active_device():
            kwargs['device'] = self._get_candidate_device()

        return func(self, *args, **kwargs)

    return wrapper