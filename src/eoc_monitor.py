"""EOC (Emergency Operations Center) state monitoring"""
import logging
import asyncio
import aiohttp
import json
from typing import Dict, List
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class EOCMonitor:
    """Monitor EOC websites for status changes"""
    
    def __init__(self, config: Dict, ha_client, shared_state: Dict = None):
        """
        Initialize EOC monitor
        
        Args:
            config: Configuration dictionary
            ha_client: Home Assistant client instance
            shared_state: Shared state dictionary for web UI
        """
        self.config = config
        self.ha_client = ha_client
        self.shared_state = shared_state
        self.check_interval = config.get('check_interval', 300)
        self.eoc_urls = config.get('eoc_urls', [])
        self.eoc_states = {}
        
        # Guardian IMS API endpoint for Townsville LDMG
        self.guardian_api_url = "https://disaster.townsville.qld.gov.au/dashboard/imsOperation"
        
        logger.info(f"EOC Monitor initialized with {len(self.eoc_urls)} URL(s)")
        if self.eoc_urls:
            logger.info(f"Monitoring URLs: {self.eoc_urls}")
        else:
            logger.warning("No EOC URLs configured - LDMG monitoring disabled")
        
    async def start(self):
        """Start the monitoring loop"""
        logger.info("EOC monitor started")
        
        while True:
            try:
                await self.check_eoc_sites()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in EOC monitor: {e}")
                await asyncio.sleep(60)
    
    async def check_eoc_sites(self):
        """Check all configured EOC sites"""
        if not self.eoc_urls:
            logger.debug("No EOC URLs configured, skipping check")
            return
            
        logger.info(f"Checking {len(self.eoc_urls)} EOC site(s)...")
        
        for url in self.eoc_urls:
            if url and 'disaster.townsville.qld.gov.au' in url:
                await self.check_guardian_ims()
            else:
                logger.warning(f"Unsupported EOC URL: {url}")
    
    async def check_guardian_ims(self):
        """Check Guardian IMS API for Townsville LDMG status"""
        # Add timestamp to prevent caching
        url = f"{self.guardian_api_url}?t={int(time.time() * 1000)}"
        
        logger.info(f"Checking Guardian IMS API: {url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Retrieved Guardian IMS data: {len(str(data))} bytes")
                        await self.process_guardian_response(data)
                    else:
                        logger.error(f"Failed to fetch Guardian IMS API: {response.status}")
        except Exception as e:
            logger.error(f"Error checking Guardian IMS: {e}", exc_info=True)
    
    async def process_guardian_response(self, data: Dict):
        """
        Process Guardian IMS API response
        
        Args:
            data: JSON response from Guardian IMS API
        """
        try:
            features = data.get('features', [])
            if not features:
                logger.warning("No features found in Guardian IMS response")
                self.eoc_states.clear()
                await self.update_sensor()
                return
            
            # Extract operation status from first feature
            feature = features[0]
            properties = feature.get('properties', {})
            
            operation_status = properties.get('operationstatus', '').strip()
            operation_name = properties.get('operationname', '').strip()
            status_description = properties.get('statusdescription', '').strip()
            
            logger.info(f"Guardian IMS - Operation: {operation_name}, Status: {operation_status}")
            
            # Map Guardian IMS status to our EOC states
            eoc_state = self.map_guardian_status(operation_status)
            
            # Store state
            url = self.guardian_api_url
            old_state = self.eoc_states.get(url, {}).get('state', 'inactive')
            
            self.eoc_states[url] = {
                'state': eoc_state,
                'activated': eoc_state != 'inactive',
                'last_check': datetime.now().isoformat(),
                'operation_name': operation_name,
                'operation_status': operation_status,
                'description': status_description[:200]  # Truncate long descriptions
            }
            
            # Check for state change
            if old_state != eoc_state:
                logger.warning(f"LDMG STATE CHANGE: {old_state} -> {eoc_state}")
                
                # Send notification
                await self.ha_client.send_notification(
                    message=f"LDMG state changed: {old_state} → {eoc_state}\nOperation: {operation_name}\n\n{status_description[:200]}...",
                    title=f"🚨 LDMG: {eoc_state.upper()}"
                )
                
                # Trigger routine if activated
                if eoc_state != 'inactive':
                    await self.trigger_eoc_routine(eoc_state)
            
            await self.update_sensor()
            
        except Exception as e:
            logger.error(f"Error processing Guardian IMS response: {e}", exc_info=True)
    
    def map_guardian_status(self, status: str) -> str:
        """
        Map Guardian IMS operation status to our EOC states
        
        Args:
            status: Guardian IMS operationstatus value
            
        Returns:
            EOC state string
        """
        status_lower = status.lower().strip()
        
        # Map Guardian IMS statuses to our states
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
        logger.info(f"Mapped Guardian status '{status}' to EOC state '{mapped_state}'")
        
        return mapped_state
    
    async def trigger_eoc_routine(self, state: str):
        """
        Trigger Home Assistant automation for EOC state change
        
        Args:
            state: Current EOC state
        """
        routines = self.config.get('routines', {})
        
        # Try state-specific routine first
        routine_key = f'eoc_{state.replace(" ", "_")}'
        if routine_key not in routines:
            # Fallback to generic activated routine
            routine_key = 'eoc_activated'
        
        if routine_key in routines:
            for action in routines[routine_key]:
                if action.startswith('scene.'):
                    await self.ha_client.activate_scene(action)
                elif action.startswith('script.'):
                    await self.ha_client.run_script(action)
                    
            logger.info(f"Triggered EOC routine: {routine_key}")
    
    async def update_sensor(self):
        """Update the EOC sensor in Home Assistant"""
        activated_count = sum(1 for state in self.eoc_states.values() if state.get('activated', False))
        
        # Get highest priority state
        priority_order = ['stand up', 'lean forward', 'alert', 'stand down', 'inactive']
        current_state = 'inactive'
        for priority_state in priority_order:
            if any(s.get('state') == priority_state for s in self.eoc_states.values()):
                current_state = priority_state
                break
        
        attributes = {
            'monitored_sites': len(self.eoc_urls),
            'activated_sites': activated_count,
            'current_state': current_state,
            'sites': self.eoc_states,
            'last_check': datetime.now().isoformat()
        }
        
        state = 'on' if activated_count > 0 else 'off'
        
        await self.ha_client.set_state(
            'binary_sensor.forewarned_eoc_active',
            state,
            attributes,
            unique_id='forewarned_eoc_active'
        )
        
        # Update web UI shared state
        if self.shared_state is not None:
            self.shared_state['eoc_states'] = self.eoc_states
            self.shared_state['last_update'] = datetime.now().isoformat()
            
            logger.info(f"Updated shared_state with EOC states: {len(self.eoc_states)} sites, current_state={current_state}")
            logger.debug(f"EOC states detail: {self.eoc_states}")
            
            # Trigger local alert manager to evaluate state
            if 'alert_manager' in self.shared_state:
                await self.shared_state['alert_manager'].update_and_trigger(
                    self.shared_state.get('weather_alerts', []),
                    self.eoc_states
                )

