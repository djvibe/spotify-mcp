import sys
import asyncio
import logging
import json
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("batch_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("batch_test")

# Add the project directory to the path
sys.path.append(str(Path(__file__).parent.parent))

# Import the BatchProcessor
from batch_processor import BatchProcessor

async def test_batch_processing():
    """Test the batch processing with a small set of artists"""
    logger.info("=== TESTING BATCH PROCESSOR ===")
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Update this path to your actual database path
    db_path = "D:/DJVIBE/MCP/spotify-mcp/spotify_artists.db"
    
    logger.info(f"Using database: {db_path}")
    logger.info(f"Output directory: {output_dir}")
    
    # Create the batch processor
    processor = BatchProcessor(
        db_path=db_path,
        output_dir=output_dir,
        max_workers=1,
        delay=2
    )
    
    # Test with a single known artist (deadmau5)
    test_artists = [
        {"id": "2CIMQHirSU0MQqyYHq0eOx", "name": "deadmau5", "popularity": 80, "tier": "Test"}
    ]
    
    logger.info(f"Processing {len(test_artists)} test artists")
    results = await processor.process_batch(test_artists)
    
    # Log and save results
    logger.info(f"Batch process complete: {results['success_count']} succeeded, {results['failure_count']} failed")
    
    with open(os.path.join(output_dir, "batch_test_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    
    if results['success_count'] == len(test_artists):
        logger.info("✓ TEST PASSED: Successfully processed all test artists")
        return True
    else:
        logger.error("✗ TEST FAILED: Failed to process all test artists")
        if results['errors']:
            logger.error(f"Errors: {json.dumps(results['errors'], indent=2)}")
        return False

if __name__ == "__main__":
    asyncio.run(test_batch_processing())
