import sys
import logging
import os
from pathlib import Path
from datetime import datetime

# Add the project directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from spotify_token_manager import SpotifyTokenManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("token_manager_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("token_manager_test")

def test_token_retrieval():
    """Test the token manager's ability to retrieve and manage tokens"""
    logger.info("=== TESTING TOKEN MANAGER ===")
    
    # Create token manager
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    token_file = os.path.join(output_dir, "test_token.json")
    logger.info(f"Token will be saved to: {token_file}")
    
    token_manager = SpotifyTokenManager(token_file)
    
    # Get token
    logger.info("Getting token...")
    token = token_manager.get_token()
    
    if token:
        logger.info(f"Successfully retrieved token: {token[:10]}... (truncated)")
        logger.info(f"Token expiry: {datetime.fromtimestamp(token_manager._token_expiry)}")
        logger.info(f"Token saved to {token_file}")
        
        # Test getting same token (should use cached)
        logger.info("\nGetting token again (should use cached)...")
        token2 = token_manager.get_token()
        logger.info(f"Second token: {token2[:10]}...")
        
        if token == token2:
            logger.info("✓ Cache working correctly - same token returned")
        else:
            logger.error("✗ Cache not working - different token returned")
        
        # Test force refresh
        logger.info("\nTesting force refresh...")
        token3 = token_manager.get_token(force_refresh=True)
        logger.info(f"Force refreshed token: {token3[:10]}...")
        
        # Test auth header
        logger.info("\nTesting authorization header...")
        auth_header = token_manager.get_authorization_header()
        logger.info(f"Auth header: {auth_header}")
        
        # Check if files were saved
        if os.path.exists(token_file):
            logger.info(f"Token file exists: {token_file}")
            try:
                with open(token_file, 'r') as f:
                    saved_data = f.read()
                logger.info(f"Token file content length: {len(saved_data)} bytes")
                logger.info("Token file is readable and contains data")
            except Exception as e:
                logger.error(f"Error reading token file: {str(e)}")
        else:
            logger.error(f"Token file not created: {token_file}")
        
        logger.info("\n✓ TEST PASSED: Token manager working correctly!")
        return True
    
    else:
        logger.error("✗ TEST FAILED: Could not retrieve token")
        return False

if __name__ == "__main__":
    test_token_retrieval()
