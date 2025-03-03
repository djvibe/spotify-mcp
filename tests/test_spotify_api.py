import requests
import json
import urllib.parse
import logging
import argparse
import os
import sys

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("spotify_api_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("spotify_api_test")

def test_spotify_partner_api(artist_id, auth_token, client_token):
    """
    Test Spotify partner API access with the provided tokens.
    
    Args:
        artist_id: Spotify artist ID (without the 'spotify:artist:' prefix)
        auth_token: Spotify OAuth token (Bearer token)
        client_token: Spotify client token
        
    Returns:
        Dictionary containing the artist details
    """
    try:
        logger.info(f"Testing Spotify partner API for artist ID: {artist_id}")
        logger.debug(f"Auth token (first 10 chars): {auth_token[:10]}...")
        logger.debug(f"Client token (first 10 chars): {client_token[:10]}...")
        
        # Construct the full artist URI
        artist_uri = f"spotify:artist:{artist_id}"
        logger.debug(f"Artist URI: {artist_uri}")
        
        # Base URL for the API
        url = "https://api-partner.spotify.com/pathfinder/v1/query"
        
        # Prepare the GraphQL variables
        variables = {
            "uri": artist_uri,
            "locale": ""
        }
        
        # Prepare the GraphQL extensions (uses persisted query for optimization)
        extensions = {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "591ed473fa2f5426186f8ba52dee295fe1ce32b36820d67eaadbc957d89408b0"
            }
        }
        
        # Construct query parameters
        params = {
            "operationName": "queryArtistOverview",
            "variables": json.dumps(variables),
            "extensions": json.dumps(extensions)
        }
        
        # Log the constructed URL for debugging
        query_string = "&".join([f"{k}={urllib.parse.quote(v)}" for k, v in params.items()])
        full_url = f"{url}?{query_string}"
        logger.debug(f"Request URL: {full_url}")
        
        # Set up the headers
        headers = {
            "accept": "application/json",
            "accept-language": "en",
            "app-platform": "WebPlayer",
            "authorization": f"Bearer {auth_token}",
            "client-token": client_token,
            "content-type": "application/json;charset=UTF-8",
            "origin": "https://open.spotify.com",
            "referer": "https://open.spotify.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        }
        logger.debug("Headers prepared (auth tokens not shown in logs)")
        
        # Make the request
        logger.info("Sending request to Spotify partner API...")
        response = requests.get(url, headers=headers, params=params)
        
        # Check if request was successful
        logger.info(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("Request successful")
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                logger.debug(f"Response text: {response.text[:500]}...")  # Log first 500 chars
                return None
        else:
            logger.error(f"Request failed with status code: {response.status_code}")
            logger.debug(f"Response text: {response.text[:500]}...")  # Log first 500 chars
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return None

def extract_key_metrics(data):
    """Extract and print key metrics from the response data"""
    try:
        if not data:
            logger.error("No data to extract metrics from")
            return
            
        if "data" not in data:
            logger.error("Response missing 'data' field")
            logger.debug(f"Response keys: {list(data.keys())}")
            return
            
        if "artistUnion" not in data["data"]:
            logger.error("Response missing 'artistUnion' field")
            logger.debug(f"Data keys: {list(data['data'].keys())}")
            return
        
        artist = data["data"]["artistUnion"]
        
        # Extract basic info
        profile = artist["profile"]
        stats = artist["stats"]
        
        logger.info("\n==== Artist Metrics ====")
        logger.info(f"Name: {profile['name']}")
        logger.info(f"Monthly Listeners: {stats.get('monthlyListeners', 'N/A'):,}")
        logger.info(f"Followers: {stats.get('followers', 'N/A'):,}")
        logger.info(f"Verified: {'Yes' if profile.get('verified') else 'No'}")
        
        # Extract top cities
        if "topCities" in stats and "items" in stats["topCities"]:
            logger.info("\n==== Top Cities ====")
            for city in stats["topCities"]["items"]:
                logger.info(f"• {city['city']}, {city['country']}: {city['numberOfListeners']:,} listeners")
        
        # Extract social media links
        if "externalLinks" in profile and "items" in profile["externalLinks"]:
            logger.info("\n==== Social Links ====")
            for link in profile["externalLinks"]["items"]:
                logger.info(f"• {link['name']}: {link['url']}")
        
        # Extract upcoming concerts if available
        if "goods" in artist and "concerts" in artist["goods"] and "items" in artist["goods"]["concerts"]:
            logger.info("\n==== Upcoming Concerts ====")
            for concert in artist["goods"]["concerts"]["items"]:
                if "data" in concert and concert["data"].get("__typename") == "ConcertV2":
                    concert_data = concert["data"]
                    location = concert_data.get("location", {})
                    date = concert_data.get("startDateIsoString", "").split("T")[0] if concert_data.get("startDateIsoString") else "N/A"
                    logger.info(f"• {date}: {location.get('name')} in {location.get('city')}")
    
    except Exception as e:
        logger.error(f"Error extracting metrics: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())

def try_different_approach(artist_id, auth_token, client_token):
    """Alternative approach using direct URL construction"""
    try:
        logger.info("Trying alternative approach with direct URL construction")
        
        # Construct the full artist URI
        artist_uri = f"spotify:artist:{artist_id}"
        
        # Base URL and parameters
        url = "https://api-partner.spotify.com/pathfinder/v1/query"
        operation_name = "queryArtistOverview"
        variables = json.dumps({"uri": artist_uri, "locale": ""})
        extensions = json.dumps({
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "591ed473fa2f5426186f8ba52dee295fe1ce32b36820d67eaadbc957d89408b0"
            }
        })
        
        # URL encode manually
        variables_encoded = urllib.parse.quote(variables)
        extensions_encoded = urllib.parse.quote(extensions)
        
        # Construct the full URL
        full_url = f"{url}?operationName={operation_name}&variables={variables_encoded}&extensions={extensions_encoded}"
        logger.debug(f"Alternative URL: {full_url}")
        
        # Set up the headers
        headers = {
            "accept": "application/json",
            "accept-language": "en",
            "app-platform": "WebPlayer",
            "authorization": f"Bearer {auth_token}",
            "client-token": client_token,
            "content-type": "application/json;charset=UTF-8",
            "origin": "https://open.spotify.com",
            "referer": "https://open.spotify.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        }
        
        # Make the request
        logger.info("Sending alternative request...")
        response = requests.get(full_url, headers=headers)
        
        # Check response
        logger.info(f"Alternative approach status code: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("Alternative approach successful")
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response in alternative approach: {str(e)}")
                return None
        else:
            logger.error(f"Alternative approach failed with status: {response.status_code}")
            logger.debug(f"Response text: {response.text[:500]}...")
            return None
    
    except Exception as e:
        logger.error(f"Error in alternative approach: {str(e)}")
        return None

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Fetch enhanced Spotify artist metrics")
    parser.add_argument("--artist-id", "-a", help="Spotify artist ID to fetch data for", default="76M2Ekj8bG8W7X2nbx2CpF")
    parser.add_argument("--tokens-file", "-t", help="Path to tokens JSON file", 
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "spotify_tokens.json"))
    parser.add_argument("--output-dir", "-o", help="Directory to save output files",
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "output"))
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    output_dir = args.output_dir
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Artist ID from command line argument
    artist_id = args.artist_id
    
    # Load tokens from file
    tokens_file = args.tokens_file
    try:
        with open(tokens_file, 'r') as f:
            tokens = json.load(f)
            auth_token = tokens.get("auth_token", "")
            client_token = tokens.get("client_token", "")
            if not auth_token or not client_token:
                logger.error("Missing or empty tokens in tokens file")
        logger.info(f"Loaded authentication tokens from {tokens_file}")
    except FileNotFoundError:
        logger.error(f"Tokens file not found: {tokens_file}")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in tokens file: {tokens_file}")
        sys.exit(1)
    
    logger.info("Starting Spotify Partner API test")
    logger.info("==================================")
    
    # Make the request using primary approach
    response_data = test_spotify_partner_api(artist_id, auth_token, client_token)
    
    # If primary approach fails, try alternative
    if not response_data or "data" not in response_data or "artistUnion" not in response_data.get("data", {}):
        logger.warning("Primary approach failed, trying alternative approach")
        response_data = try_different_approach(artist_id, auth_token, client_token)
    
    # Process the result
    if response_data:
        # Save the full response to a file using artist_id in the filename
        output_file = os.path.join(output_dir, f"{artist_id}_spotify_response.json")
        with open(output_file, 'w') as f:
            json.dump(response_data, f, indent=2)
        logger.info(f"Full response saved to {output_file}")
        
        # Also save a copy of just the key metrics in a more concise file
        metrics = {
            "name": response_data.get("data", {}).get("artistUnion", {}).get("profile", {}).get("name"),
            "monthly_listeners": response_data.get("data", {}).get("artistUnion", {}).get("stats", {}).get("monthlyListeners"),
            "followers": response_data.get("data", {}).get("artistUnion", {}).get("stats", {}).get("followers"),
            "verified": response_data.get("data", {}).get("artistUnion", {}).get("profile", {}).get("verified"),
            "top_cities": [{
                "city": city.get("city"),
                "country": city.get("country"),
                "region": city.get("region"),
                "listeners": city.get("numberOfListeners")
            } for city in response_data.get("data", {}).get("artistUnion", {}).get("stats", {}).get("topCities", {}).get("items", [])],
            "social_links": {link.get("name").lower(): link.get("url") for link in response_data.get("data", {}).get("artistUnion", {}).get("profile", {}).get("externalLinks", {}).get("items", [])},
            "upcoming_concerts": [{
                "title": concert.get("data", {}).get("title"),
                "date": concert.get("data", {}).get("startDateIsoString"),
                "location": {
                    "name": concert.get("data", {}).get("location", {}).get("name"),
                    "city": concert.get("data", {}).get("location", {}).get("city")
                },
                "festival": concert.get("data", {}).get("festival", False)
            } for concert in response_data.get("data", {}).get("artistUnion", {}).get("goods", {}).get("concerts", {}).get("items", [])]
        }
        
        metrics_file = os.path.join(output_dir, f"{artist_id}_metrics.json")
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        logger.info(f"Key metrics saved to {metrics_file}")
        
        
        # Extract and print key metrics
        extract_key_metrics(response_data)
        
        logger.info("Test completed successfully")
    else:
        logger.error("Failed to get valid response from Spotify Partner API")
        logger.info("Test completed with errors")
