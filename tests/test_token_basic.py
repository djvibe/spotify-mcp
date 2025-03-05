import requests
import json
import logging
import sys
from datetime import datetime

# Basic logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("token_retrieval_basic_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("token_retrieval_basic_test")

def get_spotify_partner_token():
    """Test just the token retrieval - nothing else"""
    try:
        logger.info("Attempting to retrieve Spotify partner token automatically...")
        
        # Use standard headers to simulate a browser request
        headers = requests.utils.default_headers()
        headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        })
        
        # Make request to the open.spotify.com endpoint
        logger.info("Sending request to https://open.spotify.com/get_access_token")
        resp = requests.get("https://open.spotify.com/get_access_token", headers=headers)
        
        # Check response status
        logger.info(f"Response status code: {resp.status_code}")
        
        # Parse response if successful
        if resp.status_code == 200:
            try:
                data = resp.json()
                logger.info(f"Response keys: {list(data.keys())}")
                
                # Print everything for inspection
                logger.info("Full response content:")
                logger.info(json.dumps(data, indent=2))
                
                # Check if token exists
                if 'accessToken' in data:
                    token = data['accessToken']
                    logger.info(f"Found token! First 10 chars: {token[:10]}...")
                    
                    # Save token to file
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    with open(f"spotify_token_test_{timestamp}.json", 'w') as f:
                        json.dump(data, f, indent=2)
                    logger.info(f"Saved full response to spotify_token_test_{timestamp}.json")
                    
                    return token
                else:
                    logger.error("No accessToken found in response")
                    return None
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                logger.info(f"Raw response: {resp.text[:1000]}")
                return None
        else:
            logger.error(f"Request failed with status code: {resp.status_code}")
            logger.info(f"Response text: {resp.text[:1000]}")
            return None
            
    except Exception as e:
        logger.error(f"Error during token retrieval: {str(e)}")
        import traceback
        logger.info(traceback.format_exc())
        return None

if __name__ == "__main__":
    logger.info("======= BASIC TOKEN RETRIEVAL TEST =======")
    token = get_spotify_partner_token()
    
    if token:
        logger.info("SUCCESS: Retrieved token successfully!")
        logger.info(f"Token (first 20 chars): {token[:20]}...")
        logger.info(f"Token (last 10 chars): ...{token[-10:]}")
        logger.info(f"Token length: {len(token)} characters")
    else:
        logger.info("FAILED: Could not retrieve token")
    
    logger.info("Test complete. Check the log file for details.")
