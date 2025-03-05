import requests
import json
import logging
import sys
import urllib.parse
from datetime import datetime

# Basic logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("partner_api_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("partner_api_test")

def get_spotify_partner_token():
    """Get a fresh Spotify Partner API token directly from open.spotify.com"""
    try:
        logger.info("Retrieving Spotify partner token automatically...")
        
        headers = requests.utils.default_headers()
        headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        })
        
        resp = requests.get("https://open.spotify.com/get_access_token", headers=headers)
        
        if resp.status_code != 200:
            logger.error(f"Failed to get token, status code: {resp.status_code}")
            return None
            
        data = resp.json()
        
        if 'accessToken' not in data:
            logger.error("No accessToken found in response")
            return None
            
        token = data['accessToken']
        client_id = data.get('clientId', '')
        
        logger.info(f"Successfully retrieved token: {token[:10]}... (truncated)")
        logger.info(f"Client ID: {client_id}")
        
        return {
            "access_token": token,
            "client_id": client_id
        }
        
    except Exception as e:
        logger.error(f"Error getting token: {str(e)}")
        return None

def test_artist_access(token_info, artist_id):
    """
    Test access to the Spotify Partner API using only the access token.
    
    Args:
        token_info: Dict containing access_token and client_id
        artist_id: Spotify artist ID to test with
    """
    try:
        access_token = token_info["access_token"]
        client_id = token_info["client_id"]
        
        logger.info(f"Testing API access for artist ID: {artist_id}")
        
        # Construct the full artist URI
        artist_uri = f"spotify:artist:{artist_id}"
        
        # Construct query parameters for the GraphQL query
        url = "https://api-partner.spotify.com/pathfinder/v1/query"
        
        variables = {
            "uri": artist_uri,
            "locale": ""
        }
        
        extensions = {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "591ed473fa2f5426186f8ba52dee295fe1ce32b36820d67eaadbc957d89408b0"
            }
        }
        
        params = {
            "operationName": "queryArtistOverview",
            "variables": json.dumps(variables),
            "extensions": json.dumps(extensions)
        }
        
        # TEST 1: With only the access token (no client token)
        logger.info("TEST 1: Using only access token")
        headers = {
            "accept": "application/json",
            "accept-language": "en",
            "app-platform": "WebPlayer",
            "authorization": f"Bearer {access_token}",
            "content-type": "application/json;charset=UTF-8",
            "origin": "https://open.spotify.com",
            "referer": "https://open.spotify.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, params=params)
        logger.info(f"Response status code: {response.status_code}")
        
        # Save response to file for examination
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_result_file = f"test1_response_{timestamp}.json"
        
        try:
            result = response.json()
            with open(test_result_file, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info(f"Response saved to {test_result_file}")
            
            # Check if we got artist data
            if "data" in result and "artistUnion" in result["data"]:
                artist_name = result["data"]["artistUnion"]["profile"]["name"]
                monthly_listeners = result["data"]["artistUnion"]["stats"].get("monthlyListeners", "N/A")
                logger.info(f"SUCCESS! Got artist data:")
                logger.info(f"  Name: {artist_name}")
                logger.info(f"  Monthly Listeners: {monthly_listeners:,}")
                logger.info("Test 1 PASSED: Partner API works with only access token!")
                return "SUCCESS"
            else:
                logger.error("Test 1 FAILED: Response doesn't contain artist data")
                logger.info(f"Response keys: {list(result.keys())}")
                
                # Check for errors
                if "errors" in result:
                    logger.error(f"API errors: {result['errors']}")
                
                # TEST 2: Try using client ID as client token
                logger.info("\nTEST 2: Using client ID as client token")
                headers["client-token"] = client_id
                
                response2 = requests.get(url, headers=headers, params=params)
                logger.info(f"Response status code: {response2.status_code}")
                
                test2_result_file = f"test2_response_{timestamp}.json"
                try:
                    result2 = response2.json()
                    with open(test2_result_file, 'w') as f:
                        json.dump(result2, f, indent=2)
                    logger.info(f"Response saved to {test2_result_file}")
                    
                    if "data" in result2 and "artistUnion" in result2["data"]:
                        artist_name = result2["data"]["artistUnion"]["profile"]["name"]
                        monthly_listeners = result2["data"]["artistUnion"]["stats"].get("monthlyListeners", "N/A")
                        logger.info(f"SUCCESS! Got artist data with client ID as client-token:")
                        logger.info(f"  Name: {artist_name}")
                        logger.info(f"  Monthly Listeners: {monthly_listeners:,}")
                        logger.info("Test 2 PASSED: Partner API works with client ID as client-token!")
                        return "SUCCESS_WITH_CLIENT_ID"
                    else:
                        logger.error("Test 2 FAILED: Response doesn't contain artist data")
                        return "FAILED_BOTH_TESTS"
                except json.JSONDecodeError:
                    logger.error("Invalid JSON in Test 2 response")
                    return "FAILED_BOTH_TESTS"
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON in response")
            logger.info(f"Raw response: {response.text[:1000]}")
            return "FAILED"
            
    except Exception as e:
        logger.error(f"Error testing artist access: {str(e)}")
        import traceback
        logger.info(traceback.format_exc())
        return "ERROR"

if __name__ == "__main__":
    logger.info("=== SPOTIFY PARTNER API ACCESS TEST ===")
    
    # Artist ID to test with (deadmau5)
    test_artist_id = "2CIMQHirSU0MQqyYHq0eOx"
    
    # Get token
    token_info = get_spotify_partner_token()
    
    if token_info:
        # Test access
        result = test_artist_access(token_info, test_artist_id)
        
        if result == "SUCCESS":
            logger.info("\n✅ GREAT NEWS! The Partner API works with only the automatically retrieved access token.")
            logger.info("This means we don't need the client token anymore!")
        elif result == "SUCCESS_WITH_CLIENT_ID":
            logger.info("\n✅ The Partner API works when using the client ID as the client-token.")
            logger.info("We can use the automatically retrieved client ID for this purpose.")
        else:
            logger.info("\n❌ The Partner API test failed.")
            logger.info("We may still need the manually extracted client token.")
    else:
        logger.error("Failed to retrieve token")
        
    logger.info("\nTest complete. Check the log file and JSON responses for details.")
