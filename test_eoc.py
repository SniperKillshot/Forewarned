"""Test EOC monitoring standalone"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_eoc_fetch():
    """Test fetching LDMG page"""
    base_url = "http://liveapi.guardianims.com/api/v1"
    endpoints_to_try = [
        "",
        "/status",
        "/dashboard?group_id=6126",
        "/incidents?group_id=6126",
    ]
    
    try:
        async with aiohttp.ClientSession() as session:
            for path in endpoints_to_try:
                url = base_url + path
                logger.info(f"\n{'='*60}")
                logger.info(f"Fetching {url}")
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        logger.info(f"Response status: {response.status}")
                        content = await response.text()
                        logger.info(f"Content length: {len(content)} bytes")
                        
                        # If it looks like JSON, try parsing it
                        if content.strip().startswith('{') or content.strip().startswith('['):
                            import json
                            try:
                                data = json.loads(content)
                                logger.info(f"JSON data:\n{json.dumps(data, indent=2)[:2000]}")
                            except:
                                logger.info(f"Content: {content[:500]}")
                        else:
                            logger.info(f"First 500 chars: {content[:500]}")
                                        
                except Exception as e:
                    logger.error(f"Error fetching {url}: {e}")
                    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_eoc_fetch())
