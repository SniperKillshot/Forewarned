"""Extract JavaScript from LDMG page to find data source"""
import asyncio
import aiohttp
import re

async def find_data_source():
    url = "https://disaster.townsville.qld.gov.au/"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            content = await response.text()
            
            # Find all script tags
            scripts = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL | re.IGNORECASE)
            
            print(f"Found {len(scripts)} script blocks\n")
            
            for i, script in enumerate(scripts):
                if len(script) > 100:  # Only show substantial scripts
                    # Look for fetch, ajax, api calls
                    if any(keyword in script.lower() for keyword in ['fetch', 'ajax', '.get(', 'api/', 'data', 'status']):
                        print(f"\n{'='*60}")
                        print(f"Script {i} (length: {len(script)}):")
                        print('='*60)
                        # Show lines containing interesting keywords
                        for line in script.split('\n'):
                            if any(kw in line.lower() for kw in ['fetch', 'ajax', '.get(', '/api/', 'url:', 'endpoint', 'status']):
                                print(line.strip())

asyncio.run(find_data_source())
