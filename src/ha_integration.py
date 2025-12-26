"""Home Assistant API integration"""
import os
import logging
import aiohttp
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """Client for Home Assistant Supervisor API"""
    
    def __init__(self, supervisor_token: Optional[str] = None):
        """
        Initialize Home Assistant client
        
        Args:
            supervisor_token: Supervisor API token from environment
        """
        self.token = supervisor_token or os.getenv('SUPERVISOR_TOKEN', '')
        self.base_url = 'http://supervisor/core/api'
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
    async def call_service(self, domain: str, service: str, service_data: Optional[Dict] = None):
        """
        Call a Home Assistant service
        
        Args:
            domain: Service domain (e.g., 'light', 'switch')
            service: Service name (e.g., 'turn_on', 'turn_off')
            service_data: Optional service data
        """
        url = f'{self.base_url}/services/{domain}/{service}'
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=service_data or {}, headers=self.headers) as response:
                    if response.status == 200:
                        logger.info(f"Service call successful: {domain}.{service}")
                        return await response.json()
                    else:
                        logger.error(f"Service call failed: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error calling service {domain}.{service}: {e}")
            return None
    
    async def get_state(self, entity_id: str) -> Optional[Dict]:
        """
        Get state of an entity
        
        Args:
            entity_id: Entity ID to query
            
        Returns:
            Entity state dictionary or None
        """
        url = f'{self.base_url}/states/{entity_id}'
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to get state for {entity_id}: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting state for {entity_id}: {e}")
            return None
    
    async def set_state(self, entity_id: str, state: str, attributes: Optional[Dict] = None):
        """
        Set state of an entity
        
        Args:
            entity_id: Entity ID to update
            state: New state value
            attributes: Optional attributes
        """
        url = f'{self.base_url}/states/{entity_id}'
        data = {
            'state': state,
            'attributes': attributes or {}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=self.headers) as response:
                    if response.status in [200, 201]:
                        logger.info(f"State set for {entity_id}: {state}")
                        return await response.json()
                    else:
                        logger.error(f"Failed to set state for {entity_id}: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error setting state for {entity_id}: {e}")
            return None
    
    async def send_notification(self, message: str, title: str = "Forewarned Alert"):
        """
        Send a persistent notification
        
        Args:
            message: Notification message
            title: Notification title
        """
        await self.call_service(
            'persistent_notification',
            'create',
            {
                'message': message,
                'title': title,
                'notification_id': 'forewarned_alert'
            }
        )
    
    async def activate_scene(self, scene_id: str):
        """
        Activate a scene
        
        Args:
            scene_id: Scene entity ID
        """
        await self.call_service('scene', 'turn_on', {'entity_id': scene_id})
    
    async def run_script(self, script_id: str):
        """
        Run a script
        
        Args:
            script_id: Script entity ID
        """
        await self.call_service('script', 'turn_on', {'entity_id': script_id})
