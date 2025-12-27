"""Test Guardian IMS API integration"""
import asyncio
import aiohttp
import json
import time
from datetime import datetime

async def test_guardian_api():
    """Test the Guardian IMS API endpoint"""
    base_url = "https://disaster.townsville.qld.gov.au/dashboard/imsOperation"
    url = f"{base_url}?t={int(time.time() * 1000)}"
    
    print(f"Testing Guardian IMS API")
    print(f"URL: {url}\n")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                print(f"Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"\n✓ Successfully retrieved JSON data")
                    print(f"Response size: {len(str(data))} bytes\n")
                    
                    # Pretty print the response
                    print("Full JSON Response:")
                    print(json.dumps(data, indent=2))
                    print("\n" + "="*60 + "\n")
                    
                    # Parse the data like our code will
                    features = data.get('features', [])
                    if features:
                        feature = features[0]
                        properties = feature.get('properties', {})
                        
                        operation_status = properties.get('operationstatus', '').strip()
                        operation_name = properties.get('operationname', '').strip()
                        status_description = properties.get('statusdescription', '').strip()
                        
                        print("Parsed Data:")
                        print(f"  Operation Name: {operation_name}")
                        print(f"  Operation Status: {operation_status}")
                        print(f"  Description: {status_description[:200]}...")
                        print()
                        
                        # Test status mapping
                        status_lower = operation_status.lower().strip()
                        status_map = {
                            'stand up': 'stand up',
                            'standup': 'stand up',
                            'lean forward': 'lean forward',
                            'leanforward': 'lean forward',
                            'alert': 'alert',
                            'stand down': 'stand down',
                            'standdown': 'stand down',
                            'inactive': 'inactive',
                            'closed': 'inactive',
                            'complete': 'inactive'
                        }
                        
                        mapped_state = status_map.get(status_lower, 'inactive')
                        print(f"Mapped EOC State: {mapped_state}")
                        print()
                        
                        # Determine if activated
                        is_activated = mapped_state != 'inactive'
                        print(f"Is Activated: {is_activated}")
                        print()
                        
                        # Show what would be stored
                        state_data = {
                            'state': mapped_state,
                            'activated': is_activated,
                            'last_check': datetime.now().isoformat(),
                            'operation_name': operation_name,
                            'operation_status': operation_status,
                            'description': status_description[:200]
                        }
                        
                        print("State Data (what would be stored):")
                        print(json.dumps(state_data, indent=2))
                        
                        print("\n✓ API integration test PASSED")
                        print(f"✓ Current LDMG status: {operation_status.upper()}")
                        
                    else:
                        print("✗ No features found in response")
                        print("This might indicate no active operations")
                else:
                    print(f"✗ HTTP Error: {response.status}")
                    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_guardian_api())
