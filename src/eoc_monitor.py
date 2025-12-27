"""EOC (Emergency Operations Center) state monitoring"""
import logging
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import Dict, List
from datetime import datetime
import hashlib

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
        self.page_hashes = {}  # Store content hashes to detect changes
        self.eoc_states = {}
        
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
        logger.info("Checking EOC sites...")
        
        for url_config in self.eoc_urls:
            if isinstance(url_config, str):
                url = url_config
                selectors = {}
            else:
                url = url_config.get('url', '')
                selectors = url_config.get('selectors', {})
            
            if url:
                await self.check_site(url, selectors)
    
    async def check_site(self, url: str, selectors: Dict):
        """
        Check a single EOC site for changes
        
        Args:
            url: URL to monitor
            selectors: CSS selectors to extract specific content
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        html = await response.text()
                        await self.process_page(url, html, selectors)
                    else:
                        logger.error(f"Failed to fetch {url}: {response.status}")
        except Exception as e:
            logger.error(f"Error checking {url}: {e}")
    
    async def process_page(self, url: str, html: str, selectors: Dict):
        """
        Process page content and detect changes
        
        Args:
            url: Page URL
            html: HTML content
            selectors: CSS selectors for content extraction
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract relevant content based on selectors
        if selectors:
            content = self.extract_content(soup, selectors)
        else:
            # Use full page text if no selectors provided
            content = soup.get_text(strip=True)
        
        # Calculate content hash
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Check if content changed
        if url in self.page_hashes:
            if self.page_hashes[url] != content_hash:
                logger.warning(f"CHANGE DETECTED on {url}")
                await self.handle_change(url, content, soup)
        else:
            logger.info(f"First check for {url}")
        
        self.page_hashes[url] = content_hash
        await self.update_sensor()
    
    def extract_content(self, soup: BeautifulSoup, selectors: Dict) -> str:
        """
        Extract specific content using CSS selectors
        
        Args:
            soup: BeautifulSoup object
            selectors: Dictionary of CSS selectors
            
        Returns:
            Extracted content as string
        """
        content_parts = []
        
        for key, selector in selectors.items():
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text:
                    content_parts.append(text)
        
        return '\n'.join(content_parts)
    
    async def handle_change(self, url: str, content: str, soup: BeautifulSoup):
        """
        Handle detected change on EOC site
        
        Args:
            url: URL where change was detected
            content: New content
            soup: BeautifulSoup object
        """
        # Detect EOC state from content
        eoc_state = self.detect_eoc_state(content)
        old_state = self.eoc_states.get(url, {}).get('state', 'inactive')
        
        # Store state
        self.eoc_states[url] = {
            'state': eoc_state,
            'activated': eoc_state != 'inactive',
            'last_change': datetime.now().isoformat(),
            'content_preview': content[:200]
        }
        
        # Only notify if state actually changed
        if eoc_state != old_state:
            logger.warning(f"EOC STATE CHANGE: {url} - {old_state} → {eoc_state}")
            
            # Send notification
            await self.ha_client.send_notification(
                message=f"EOC state changed: {old_state} → {eoc_state}\n{url}\n\nPreview: {content[:200]}...",
                title=f"🚨 EOC: {eoc_state.upper()}"
            )
            
            # Trigger routine if activated
            if eoc_state != 'inactive':
                await self.trigger_eoc_routine(eoc_state)
    
    def detect_eoc_state(self, content: str) -> str:
        """
        Detect EOC state from page content
        
        Valid states (only shown when EOC is activated):
        - stand up: EOC fully activated and operational (highest priority)
        - lean forward: Preparing to activate
        - alert: Initial activation, monitoring situation
        - stand down: Deactivating or returning to normal
        - inactive: No state keywords present (default)
        
        Args:
            content: Page content to analyze
            
        Returns:
            Detected state as string
        """
        content_lower = content.lower()
        
        # Check for specific states (order matters - check most specific first)
        # These keywords only appear on the page when there's an actual EOC activation
        if 'stand up' in content_lower or 'standup' in content_lower:
            return 'stand up'
        elif 'lean forward' in content_lower or 'leanforward' in content_lower:
            return 'lean forward'
        elif 'stand down' in content_lower or 'standdown' in content_lower:
            return 'stand down'
        # Only match 'alert' if it's specifically about EOC
        elif 'eoc' in content_lower and 'alert' in content_lower:
            return 'alert'
        
        # If none of the state keywords are found, EOC is inactive
        return 'inactive'
    
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
            attributes
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
