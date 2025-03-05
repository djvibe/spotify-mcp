import sys
import logging
import json
import os
from pathlib import Path

# Add the project directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from spotify_partner_api import SpotifyPartnerAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("partner_api_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("partner_api_test")

def test_artist_details():
    """Test fetching enhanced artist details"""
    logger.info("=== TESTING PARTNER API CLIENT ===")
    
    # Create API client with token file in output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    token_file = os.path.join(output_dir, "partner_api_token.json")
    logger.info(f"Token will be saved to: {token_file}")
    
    api = SpotifyPartnerAPI(token_file)
    
    # Test with deadmau5
    artist_id = "2CIMQHirSU0MQqyYHq0eOx"
    
    logger.info(f"Fetching details for artist ID: {artist_id}")
    artist_data = api.get_artist_details(artist_id)
    
    if artist_data:
        logger.info("Successfully retrieved artist data")
        
        # Save full response
        response_file = os.path.join(output_dir, "test_artist_response.json")
        with open(response_file, "w") as f:
            json.dump(artist_data, f, indent=2)
        logger.info(f"Full response saved to {response_file}")
        
        # Extract and print metrics
        metrics = api.extract_artist_metrics(artist_data)
        
        if metrics:
            logger.info("\n=== Artist Metrics ===")
            logger.info(f"Name: {metrics['name']}")
            logger.info(f"Monthly Listeners: {metrics['monthly_listeners']:,}")
            logger.info(f"Followers: {metrics['followers']:,}")
            logger.info(f"Verified: {'Yes' if metrics['verified'] else 'No'}")
            
            if metrics['top_cities']:
                logger.info("\nTop Cities:")
                for city in metrics['top_cities'][:3]:  # Show top 3
                    logger.info(f"• {city['city']}, {city['country']}: {city['listeners']:,}")
                    
            if metrics['social_links']:
                logger.info("\nSocial Links:")
                for platform, url in list(metrics['social_links'].items())[:3]:  # Show first 3
                    logger.info(f"• {platform}: {url}")
                    
            # Save metrics to file
            metrics_file = os.path.join(output_dir, "test_artist_metrics.json")
            with open(metrics_file, "w") as f:
                json.dump(metrics, f, indent=2)
            logger.info(f"\nMetrics saved to {metrics_file}")
            
            logger.info("\n✓ TEST PASSED: Successfully retrieved and extracted enhanced artist data!")
            return True
        else:
            logger.error("✗ Failed to extract metrics from response")
            return False
    else:
        logger.error("✗ Failed to retrieve artist data")
        return False

if __name__ == "__main__":
    test_artist_details()
