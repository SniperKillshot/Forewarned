"""Weather monitoring and alerting"""
import logging
import asyncio
from ftplib import FTP
from typing import Dict, List, Optional
from datetime import datetime
from lxml import etree
import io

logger = logging.getLogger(__name__)


class WeatherMonitor:
    """Monitor weather alerts from Australian Bureau of Meteorology"""
    
    def __init__(self, config: Dict, ha_client, shared_state: Dict = None):
        """
        Initialize weather monitor
        
        Args:
            config: Configuration dictionary
            ha_client: Home Assistant client instance
            shared_state: Shared state dictionary for web UI
        """
        self.config = config
        self.ha_client = ha_client
        self.shared_state = shared_state
        self.check_interval = config.get('check_interval', 300)
        self.ftp_host = 'ftp.bom.gov.au'
        self.warnings_path = '/anon/gen/fwo'
        self.alert_types = config.get('alert_types', [])
        self.active_alerts = {}
        self.location = config.get('location', 'Townsville')
        # Keywords to identify Townsville area warnings
        self.location_keywords = [
            'townsville',
            'herbert and lower burdekin',
            'upper flinders',
            'north tropical coast',
            'northern goldfields',
            'townsville waters',
            'palm island',
            'magnetic island'
        ]
        
    async def start(self):
        """Start the monitoring loop"""
        logger.info("Weather monitor started")
        
        while True:
            try:
                await self.check_alerts()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in weather monitor: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def check_alerts(self):
        """Check for active weather alerts from BOM"""
        logger.info("Checking for weather alerts from BOM...")
        
        try:
            await self.check_bom_warnings()
        except Exception as e:
            logger.error(f"Error checking BOM warnings: {e}")
    
    async def check_bom_warnings(self):
        """Check Australian Bureau of Meteorology warnings via FTP"""
        try:
            # Run FTP operations in thread pool to avoid blocking
            current_alerts = await asyncio.to_thread(self._fetch_ftp_warnings)
            
            # Update alerts back in async context
            if current_alerts is not None:
                await self.update_alerts(current_alerts)
                
        except Exception as e:
            logger.error(f"FTP connection error: {e}")
    
    def _fetch_ftp_warnings(self) -> Dict:
        """Fetch warnings from BOM FTP (runs in thread pool)"""
        try:
            with FTP(self.ftp_host) as ftp:
                ftp.login()  # Anonymous login
                ftp.cwd(self.warnings_path)
                
                # List XML warning files - only Queensland (IDQ prefix)
                files = []
                file_list = ftp.nlst()
                for filename in file_list:
                    if filename.endswith('.xml') and filename.upper().startswith('IDQ'):
                        files.append(filename)
                
                logger.info(f"Found {len(files)} Queensland warning files")
                
                # Process warning files
                current_alerts = {}
                parsed_count = 0
                for filename in files:
                    try:
                        result = self._process_ftp_file(ftp, filename, current_alerts)
                        if result:
                            parsed_count += 1
                    except Exception as e:
                        logger.error(f"Error processing {filename}: {e}")
                
                logger.info(f"Successfully parsed {parsed_count} warning files")
                
                return current_alerts
                
        except Exception as e:
            logger.error(f"FTP error: {e}")
            return {}
            logger.error(f"FTP error: {e}")
    
    def _process_ftp_file(self, ftp: FTP, filename: str, current_alerts: Dict) -> bool:
        """
        Download and parse a warning XML file from FTP
        
        Args:
            ftp: FTP client connection
            filename: Warning file name
            current_alerts: Dictionary to store parsed alerts
            
        Returns:
            True if warning was successfully parsed
        """
        try:
            # Download file content
            xml_data = io.BytesIO()
            ftp.retrbinary(f'RETR {filename}', xml_data.write)
            xml_content = xml_data.getvalue()
            
            # Parse XML
            root = etree.fromstring(xml_content)
            
            # Extract alert information (BOM XML structure)
            # Check for CAP format
            namespaces = {'cap': 'urn:oasis:names:tc:emergency:cap:1.2'}
            
            # Try CAP format first
            info_elements = root.findall('.//cap:info', namespaces)
            
            # Also try without namespace
            if not info_elements:
                info_elements = root.findall('.//info')
            
            if info_elements:
                for info in info_elements:
                    alert_id = filename
                    event = info.findtext('cap:event', default='', namespaces=namespaces)
                    logger.info(f"DEBUG {filename}: event from cap:event = '{event}' (len={len(event) if event else 0})")
                    if not event:
                        event = info.findtext('event', default='')
                        logger.info(f"DEBUG {filename}: event from event = '{event}' (len={len(event) if event else 0})")
                    
                    headline = info.findtext('cap:headline', default='', namespaces=namespaces)
                    if not headline:
                        headline = info.findtext('headline', default='')
                        
                    description = info.findtext('cap:description', default='', namespaces=namespaces)
                    if not description:
                        description = info.findtext('description', default='')
                        
                    severity = info.findtext('cap:severity', default='', namespaces=namespaces)
                    urgency = info.findtext('cap:urgency', default='', namespaces=namespaces)
                    
                    # Get area information
                    areas = []
                    for area in info.findall('cap:area', namespaces):
                        area_desc = area.findtext('cap:areaDesc', default='', namespaces=namespaces)
                        if not area_desc:
                            area_desc = area.findtext('areaDesc', default='')
                        if area_desc:
                            areas.append(area_desc)
                    
                    # Get timing
                    onset = info.findtext('cap:onset', default='', namespaces=namespaces)
                    expires = info.findtext('cap:expires', default='', namespaces=namespaces)
                    
                    if event:  # Only add if we have an event type
                        # Skip cancellation messages
                        if 'cancellation' in (event or '').lower() or 'cancellation' in (headline or '').lower():
                            logger.debug(f"Skipping cancellation message: {filename}")
                            return False
                        
                        alert_data = {
                            'event': event,
                            'headline': headline or event,
                            'description': description or '',
                            'severity': severity or 'Unknown',
                            'urgency': urgency or 'Unknown',
                            'areas': ', '.join(areas) if areas else 'Unknown',
                            'onset': onset or '',
                            'expires': expires or '',
                            'source': 'BOM',
                            'filename': filename
                        }
                        
                        # Log heatwave warnings specifically for debugging
                        if 'heatwave' in (event or '').lower() or 'heatwave' in filename.lower():
                            logger.info(f"HEATWAVE DEBUG (CAP) - File: {filename}")
                            logger.info(f"  Event: '{event}'")
                            logger.info(f"  Headline: '{headline}'")
                            logger.info(f"  Areas: {areas}")
                            logger.info(f"  Affects Townsville: {self.affects_townsville(alert_data)}")
                        
                        # Only include if it affects Townsville
                        if self.affects_townsville(alert_data):
                            current_alerts[alert_id] = alert_data
                            logger.info(f"Alert affects Townsville: {event} - {', '.join(areas) if areas else 'Unknown'}")
                            return True
                        
                        return False
            else:
                # Try standard BOM XML format
                # Look for common BOM warning elements
                # Note: product-type is just a code like "F" or "W", not the warning description
                warning_type = (
                    root.findtext('.//warning-type', '') or
                    root.findtext('.//type', '') or
                    root.findtext('.//event', '')
                )
                issue_time = (
                    root.findtext('.//issue-time-local', '') or
                    root.findtext('.//issue-time-utc', '') or
                    root.findtext('.//valid-from', '')
                )
                
                # Try to get title/headline
                headline = (
                    root.findtext('.//title', '') or
                    root.findtext('.//headline', '') or
                    warning_type
                )
                
                if warning_type or headline:
                    # Skip cancellation messages
                    if 'cancellation' in (warning_type or '').lower() or 'cancellation' in (headline or '').lower():
                        logger.debug(f"Skipping cancellation message: {filename}")
                        return False
                    
                    alert_id = filename
                    alert_data = {
                        'event': warning_type or headline,
                        'headline': headline or warning_type,
                        'description': self.extract_text_content(root),
                        'severity': 'Moderate',  # BOM doesn't always provide severity
                        'urgency': 'Expected',
                        'areas': self.extract_areas(root),
                        'onset': issue_time,
                        'expires': '',
                        'source': 'BOM',
                        'filename': filename
                    }
                    
                    logger.debug(f"Parsed {filename}: {warning_type or headline} - Areas: {alert_data['areas']}")
                    
                    # Log heatwave warnings specifically for debugging
                    if 'heatwave' in (warning_type or '').lower() or 'heatwave' in filename.lower():
                        logger.info(f"HEATWAVE DEBUG - File: {filename}")
                        logger.info(f"  Type: '{warning_type}'")
                        logger.info(f"  Headline: '{headline}'")
                        logger.info(f"  Areas: '{alert_data['areas']}'")
                        logger.info(f"  Affects Townsville: {self.affects_townsville(alert_data)}")
                    
                    # Only include if it affects Townsville
                    if self.affects_townsville(alert_data):
                        current_alerts[alert_id] = alert_data
                        logger.info(f"Alert affects Townsville: {warning_type}")
                        return True
                    
                    return False
                    
        except Exception as e:
            logger.error(f"Error parsing {filename}: {e}")
            return False
    
    def extract_text_content(self, root) -> str:
        """Extract warning text from XML"""
        # Try common BOM text fields
        text_fields = [
            './/warning-text',
            './/description', 
            './/synopsis',
            './/text',
            './/headline',
            './/title',
            './/summary',
            './/details'
        ]
        
        texts = []
        for field in text_fields:
            text = root.findtext(field, '')
            if text and text not in texts:
                texts.append(text)
        
        combined = ' '.join(texts)
        return combined[:1000] if combined else ''  # Return more text for better matching
    
    def extract_areas(self, root) -> str:
        """Extract affected areas from XML"""
        areas = []
        
        # Try multiple area tag patterns
        area_tags = [
            './/area',
            './/areaDesc',
            './/area-description',
            './/location',
            './/region',
            './/district'
        ]
        
        for tag in area_tags:
            for area in root.findall(tag):
                area_text = area.text or area.get('description', '') or area.get('areaDesc', '')
                if area_text and area_text not in areas:
                    areas.append(area_text)
        
        # If no areas found, try to extract from text content
        if not areas:
            text = self.extract_text_content(root)
            # Look for common area patterns in text
            for keyword in self.location_keywords:
                if keyword.lower() in text.lower():
                    areas.append(keyword.title())
        
        return ', '.join(areas) if areas else 'Various areas'
    
    def affects_townsville(self, alert: Dict) -> bool:
        """
        Check if the alert affects Townsville area
        
        Args:
            alert: Alert dictionary with areas and description
            
        Returns:
            True if alert affects Townsville area
        """
        # Combine all text fields to search
        search_text = (
            alert.get('areas', '') + ' ' + 
            alert.get('headline', '') + ' ' + 
            alert.get('description', '')
        ).lower()
        
        # Check if any Townsville keywords are present
        for keyword in self.location_keywords:
            if keyword.lower() in search_text:
                return True
        
        return False
    
    async def update_alerts(self, current_alerts: Dict):
        """
        Compare current alerts with previous and trigger actions
        
        Args:
            current_alerts: Dictionary of current active alerts
        """
        # Check for new alerts
        for alert_id, alert in current_alerts.items():
            if alert_id not in self.active_alerts:
                await self.handle_new_alert(alert)
        
        # Check for cleared alerts
        for alert_id in list(self.active_alerts.keys()):
            if alert_id not in current_alerts:
                await self.handle_cleared_alert(self.active_alerts[alert_id])
        
        self.active_alerts = current_alerts
        
        # Update sensor state
        await self.update_sensor()
        
        # Update web UI shared state
        if self.shared_state is not None:
            self.shared_state['weather_alerts'] = list(current_alerts.values())
            self.shared_state['last_update'] = datetime.now().isoformat()
            
            # Trigger local alert manager to evaluate state
            if 'alert_manager' in self.shared_state:
                await self.shared_state['alert_manager'].update_and_trigger(
                    list(current_alerts.values()),
                    self.shared_state.get('eoc_states', {})
                )
    
    async def handle_new_alert(self, alert: Dict):
        """
        Handle a new weather alert
        
        Args:
            alert: Alert data dictionary
        """
        # Check if this is a cancellation message
        headline = alert.get('headline', '').upper()
        event = alert.get('event', '').upper()
        
        if 'CANCELLATION' in headline or 'CANCELLATION' in event:
            logger.info(f"CANCELLATION MESSAGE: {alert['event']} - {alert['headline']}")
            return  # Don't alert on cancellations
        
        logger.warning(f"NEW ALERT: {alert['event']} - {alert['headline']}")
        
        # Send notification
        message = f"{alert['event']}\n{alert['headline']}\nAreas: {alert['areas']}"
        await self.ha_client.send_notification(
            message=message,
            title=f"⚠️ Weather Alert: {alert['event']}"
        )
        
        # Trigger appropriate routine
        await self.trigger_routine(alert)
    
    async def handle_cleared_alert(self, alert: Dict):
        """
        Handle a cleared weather alert
        
        Args:
            alert: Alert data dictionary
        """
        logger.info(f"CLEARED: {alert['event']}")
        
        await self.ha_client.send_notification(
            message=f"Alert cleared: {alert['event']}",
            title="Weather Alert Cleared"
        )
    
    async def trigger_routine(self, alert: Dict):
        """
        Trigger Home Assistant automation based on alert type
        
        Args:
            alert: Alert data dictionary
        """
        event = alert['event'].lower()
        routines = self.config.get('routines', {})
        
        # Determine which routine to trigger
        routine_key = None
        if 'tornado' in event:
            routine_key = 'tornado_warning'
        elif 'severe' in event or 'thunderstorm' in event or 'flood' in event:
            routine_key = 'severe_weather'
        
        if routine_key and routine_key in routines:
            for action in routines[routine_key]:
                if action.startswith('scene.'):
                    await self.ha_client.activate_scene(action)
                elif action.startswith('script.'):
                    await self.ha_client.run_script(action)
                    
            logger.info(f"Triggered routine: {routine_key}")
    
    async def update_sensor(self):
        """Update the weather alert sensor in Home Assistant"""
        alert_count = len(self.active_alerts)
        
        attributes = {
            'alert_count': alert_count,
            'alerts': list(self.active_alerts.values()),
            'last_check': datetime.now().isoformat()
        }
        
        state = 'on' if alert_count > 0 else 'off'
        
        await self.ha_client.set_state(
            'binary_sensor.forewarned_weather_alert',
            state,
            attributes
        )
