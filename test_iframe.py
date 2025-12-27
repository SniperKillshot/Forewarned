"""Test if LDMG site allows iframe embedding"""
import asyncio
import aiohttp

async def check_iframe_headers():
    url = "https://disaster.townsville.qld.gov.au/"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            print(f"URL: {url}")
            print(f"Status: {response.status}\n")
            
            print("Headers that affect iframe embedding:")
            print(f"X-Frame-Options: {response.headers.get('X-Frame-Options', 'Not set (allows iframe)')}")
            print(f"Content-Security-Policy: {response.headers.get('Content-Security-Policy', 'Not set')}")
            
            if 'X-Frame-Options' not in response.headers:
                print("\n✓ Site CAN be embedded in iframe (no X-Frame-Options header)")
            else:
                xfo = response.headers.get('X-Frame-Options')
                if xfo.upper() in ['DENY', 'SAMEORIGIN']:
                    print(f"\n✗ Site CANNOT be embedded in iframe (X-Frame-Options: {xfo})")
                else:
                    print(f"\n? Unknown X-Frame-Options value: {xfo}")

asyncio.run(check_iframe_headers())
