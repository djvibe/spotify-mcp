import pytest
from unittest.mock import Mock, patch
from spotify_mcp.batch import ArtistBatchProcessor
from spotify_mcp.models import Artist, Image, ExternalUrl, Followers

def create_mock_artist(artist_id: str, name: str) -> dict:
    """Helper to create mock artist data"""
    return {
        'id': artist_id,
        'name': name,
        'external_urls': {'spotify': f'https://open.spotify.com/artist/{artist_id}'},
        'followers': {'total': 1000},
        'genres': ['pop'],
        'href': f'https://api.spotify.com/v1/artists/{artist_id}',
        'images': [{'height': 640, 'url': 'http://example.com/image.jpg', 'width': 640}],
        'popularity': 80,
        'uri': f'spotify:artist:{artist_id}',
        'type': 'artist'
    }

@pytest.fixture
def mock_spotify():
    """Create mock Spotify client"""
    mock = Mock()
    mock.artists.return_value = {
        'artists': [
            create_mock_artist('id1', 'Artist 1'),
            create_mock_artist('id2', 'Artist 2'),
            None  # Simulate missing artist
        ]
    }
    return mock

@pytest.fixture
def mock_db():
    """Create mock database"""
    mock = Mock()
    mock.save_artist.return_value = True
    return mock

@pytest.fixture
def mock_logger():
    """Create mock logger"""
    return Mock()

def test_batch_processor_initialization(mock_spotify, mock_db, mock_logger):
    processor = ArtistBatchProcessor(mock_spotify, mock_logger, mock_db)
    assert processor.MAX_BATCH_SIZE == 50
    assert processor.sp == mock_spotify
    assert processor.logger == mock_logger
    assert processor.db == mock_db

@pytest.mark.asyncio
async def test_empty_batch(mock_spotify, mock_db, mock_logger):
    processor = ArtistBatchProcessor(mock_spotify, mock_logger, mock_db)
    with pytest.raises(ValueError) as exc_info:
        await processor.process_artist_batch([])
    assert str(exc_info.value) == "Artist IDs list cannot be empty"

@pytest.mark.asyncio
async def test_successful_batch_processing(mock_spotify, mock_db, mock_logger):
    processor = ArtistBatchProcessor(mock_spotify, mock_logger, mock_db)
    result = await processor.process_artist_batch(['id1', 'id2', 'id3'])
    
    assert result['total_processed'] == 3
    assert result['success_count'] == 2
    assert result['failure_count'] == 1
    assert 'id1' in result['successful']
    assert 'id2' in result['successful']
    assert 'id3' in result['failed']

@pytest.mark.asyncio
async def test_large_batch_handling(mock_spotify, mock_db, mock_logger):
    processor = ArtistBatchProcessor(mock_spotify, mock_logger, mock_db)
    large_batch = [f'id{i}' for i in range(75)]  # Create batch larger than MAX_BATCH_SIZE
    result = await processor.process_artist_batch(large_batch)
    
    assert result['total_processed'] == 75
    assert mock_spotify.artists.call_count == 2  # Should be called twice for 75 items

@pytest.mark.asyncio
async def test_database_failure(mock_spotify, mock_db, mock_logger):
    mock_db.save_artist.return_value = False  # Simulate database save failure
    processor = ArtistBatchProcessor(mock_spotify, mock_logger, mock_db)
    result = await processor.process_artist_batch(['id1'])
    
    assert result['total_processed'] == 1
    assert result['success_count'] == 0
    assert result['failure_count'] == 1
    assert 'id1' in result['failed']
    assert 'Database save failed' in result['errors']['id1']