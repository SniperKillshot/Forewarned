"""Local Alert State Manager - Determines when to trigger Home Assistant routines"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class LocalAlertManager:
    """
    Manages the local alert state which triggers Home Assistant routines.
    This provides a single point of control for all automation triggers.
    """
    
    def __init__(self, config: Dict, ha_client, update_callback, voip_integration=None, mqtt_client=None):
        """
        Initialize local alert manager
        
        Args:
            config: Configuration dictionary
            ha_client: Home Assistant client instance
            update_callback: Callback function to update app state
            voip_integration: Optional VOIP integration instance
            mqtt_client: Optional MQTT client instance
        """
        self.config = config
        self.ha_client = ha_client
        self.update_callback = update_callback
        self.voip_integration = voip_integration
        self.mqtt_client = mqtt_client
        self.current_state = {
            'active': False,
            'level': 'none',
            'reason': '',
            'timestamp': None,
            'triggered_by': []
        }
        
        # Define alert levels and their priorities
        self.alert_levels = {
            'none': 0,
            'advisory': 1,
            'watch': 2,
            'warning': 3,
            'emergency': 4
        }
        
        # Manual override switch entity IDs (using switch domain instead of input_boolean)
        self.manual_switches = {
            'advisory': 'switch.forewarned_manual_advisory',
            'watch': 'switch.forewarned_manual_watch',
            'warning': 'switch.forewarned_manual_warning',
            'emergency': 'switch.forewarned_manual_emergency'
        }
    
    async def initialize_manual_switches(self):
        """Initialize manual override switches via MQTT discovery or HA REST API"""
        switch_configs = {
            'manual_advisory': {
                'name': 'Forewarned Manual Advisory',
                'icon': 'mdi:information-outline',
                'level': 'advisory'
            },
            'manual_watch': {
                'name': 'Forewarned Manual Watch',
                'icon': 'mdi:eye-outline',
                'level': 'watch'
            },
            'manual_warning': {
                'name': 'Forewarned Manual Warning',
                'icon': 'mdi:alert',
                'level': 'warning'
            },
            'manual_emergency': {
                'name': 'Forewarned Manual Emergency',
                'icon': 'mdi:alarm-light',
                'level': 'emergency'
            }
        }
        
        # If MQTT is enabled, use discovery for switches
        if self.mqtt_client and self.mqtt_client.connected:
            logger.info("Using MQTT discovery to create manual override switches")
            for switch_id, config in switch_configs.items():
                self.mqtt_client.publish_discovery(
                    switch_id,
                    config['name'],
                    config['icon']
                )
            logger.info("Manual override switches created via MQTT discovery")
            return
        
        # Fallback to REST API (temporary switches without unique IDs)
        logger.warning("MQTT not enabled - creating temporary switches via REST API")
        missing_switches = []
        
        for level, entity_id in self.manual_switches.items():
            # Check if switch already exists
            state = await self.ha_client.get_state(entity_id)
            if not state:
                missing_switches.append(entity_id)
                # Create a temporary state
                switch_id = f"manual_{level}"
                config = switch_configs.get(switch_id)
                if config:
                    await self.ha_client.set_state(
                        entity_id,
                        'off',
                        {
                            'friendly_name': config['name'],
                            'icon': config['icon'],
                            'note': 'Enable MQTT for persistent switches with unique IDs'
                        }
                    )
            else:
                logger.info(f"Found existing manual switch: {entity_id}")
        
        if missing_switches:
            logger.warning("Temporary switches created without unique IDs. Enable MQTT for persistent switches.")
        else:
            logger.info("All manual override switches found")
    
    async def _check_manual_overrides(self) -> tuple[Optional[str], Optional[str]]:
        """
        Check if any manual override switches are active
        
        Returns:
            Tuple of (level, reason) or (None, None) if no overrides active
        """
        # Check switches in priority order (highest to lowest)
        for level in ['emergency', 'warning', 'watch', 'advisory']:
            # Try MQTT first if available
            if self.mqtt_client and self.mqtt_client.connected:
                switch_id = f"manual_{level}"
                state = self.mqtt_client.get_state(switch_id)
                if state:
                    return level, f"Manual override: {level.upper()}"
            
            # Fallback to HA REST API
            entity_id = self.manual_switches.get(level)
            if not entity_id:
                continue
            
            try:
                state = await self.ha_client.get_state(entity_id)
                if state and state.get('state') == 'on':
                    return level, f"Manual override: {level.upper()}"
            except Exception as e:
                logger.debug(f"Could not check manual switch {entity_id}: {e}")
                continue
        
        return None, None
    
    def _evaluate_conditions(self, conditions: Dict, weather_alerts: List[Dict], eoc_states: Dict) -> bool:
        """
        Evaluate a set of conditions (weather or EOC) with and/or logic
        
        Args:
            conditions: Condition dictionary with operator and rules
            weather_alerts: List of active weather alerts
            eoc_states: Dictionary of EOC states
            
        Returns:
            True if conditions are met, False otherwise
        """
        operator = conditions.get('operator', 'or')
        rules = conditions.get('rules', [])
        
        if not rules:
            return False
        
        results = []
        
        for rule in rules:
            # Weather condition
            if 'severity' in rule:
                target_type = rule.get('type', 'any').lower()
                target_severity = rule.get('severity', 'any').lower()
                
                matched = False
                for alert in weather_alerts:
                    alert_type = (alert.get('event', '') or '').lower()
                    alert_severity = (alert.get('severity', '') or '').lower()
                    
                    type_match = (target_type == 'any' or target_type in alert_type)
                    severity_match = (target_severity == 'any' or target_severity == alert_severity)
                    
                    if type_match and severity_match:
                        matched = True
                        break
                
                results.append(matched)
            
            # EOC condition
            elif 'state' in rule:
                target_state = rule.get('state', '').lower()
                
                matched = False
                for url, state_info in eoc_states.items():
                    if state_info.get('activated', False):
                        eoc_state = state_info.get('state', 'inactive').lower()
                        if eoc_state == target_state:
                            matched = True
                            break
                
                results.append(matched)
        
        # Apply operator
        if operator == 'and':
            return all(results)
        else:  # or
            return any(results)
    
    async def evaluate_alert_state(self, weather_alerts: List[Dict], eoc_states: Dict) -> Dict:
        """
        Evaluate all conditions and determine the appropriate local alert state
        
        Args:
            weather_alerts: List of active weather alerts
            eoc_states: Dictionary of EOC states
            
        Returns:
            New alert state dictionary
        """
        # Check for manual overrides first (highest priority)
        manual_level, manual_reason = await self._check_manual_overrides()
        if manual_level:
            return {
                'active': True,
                'level': manual_level,
                'reason': manual_reason,
                'timestamp': datetime.now().isoformat(),
                'triggered_by': [manual_reason]
            }
        
        triggers = []
        max_level = 'none'
        reasons = []
        
        # Get alert rules from config
        alert_rules = self.config.get('alert_rules', {})
        
        # Check each alert level (from highest to lowest priority)
        for level_name in ['emergency', 'warning', 'watch', 'advisory']:
            level_config = alert_rules.get(level_name, {})
            
            # Evaluate weather conditions
            weather_conditions = level_config.get('weather_conditions', {})
            weather_match = self._evaluate_conditions(weather_conditions, weather_alerts, eoc_states)
            
            # Evaluate EOC conditions
            eoc_conditions = level_config.get('eoc_conditions', {})
            eoc_match = self._evaluate_conditions(eoc_conditions, weather_alerts, eoc_states)
            
            # Apply condition logic
            condition_logic = level_config.get('condition_logic', 'or')
            
            if condition_logic == 'and':
                level_triggered = weather_match and eoc_match
            else:  # or
                level_triggered = weather_match or eoc_match
            
            # If this level is triggered and is higher priority than current max
            if level_triggered and self.alert_levels[level_name] > self.alert_levels[max_level]:
                max_level = level_name
                
                # Collect triggers and reasons
                if weather_match:
                    for alert in weather_alerts:
                        event = alert.get('event', 'Unknown')
                        # Extract just the warning type (remove long descriptions and area names)
                        # Split on " for " to remove area lists (e.g., "Severe Heatwave Warning for the Peninsula...")
                        short_event = event.split(' for ')[0] if ' for ' in event else event
                        # Also split on " - " for other formats
                        short_event = short_event.split(' - ')[0] if ' - ' in short_event else short_event
                        if short_event not in reasons:
                            triggers.append(f"Weather: {short_event}")
                            reasons.append(short_event)
                
                if eoc_match:
                    for url, state_info in eoc_states.items():
                        if state_info.get('activated', False):
                            eoc_state = state_info.get('state', 'inactive')
                            trigger_text = f"LDMG: {eoc_state.upper()}"
                            if trigger_text not in triggers:
                                triggers.append(trigger_text)
                                reasons.append(f"LDMG {eoc_state}")
        
        # Determine if alert should be active
        active = max_level != 'none'
        reason = ', '.join(reasons) if reasons else 'No active alerts'
        
        new_state = {
            'active': active,
            'level': max_level,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'triggered_by': triggers
        }
        
        return new_state
    
    async def update_and_trigger(self, weather_alerts: List[Dict], eoc_states: Dict):
        """
        Update alert state and trigger Home Assistant routines if needed
        
        Args:
            weather_alerts: List of active weather alerts
            eoc_states: Dictionary of EOC states
        """
        new_state = await self.evaluate_alert_state(weather_alerts, eoc_states)
        old_state = self.current_state
        
        # Check if state changed
        state_changed = (
            old_state['active'] != new_state['active'] or
            old_state['level'] != new_state['level']
        )
        
        if state_changed:
            logger.info(f"Local alert state changed: {old_state['level']} -> {new_state['level']}")
            logger.info(f"Reason: {new_state['reason']}")
            
            # Update the state
            self.current_state = new_state
            self.update_callback(
                active=new_state['active'],
                level=new_state['level'],
                reason=new_state['reason'],
                triggered_by=new_state['triggered_by']
            )
            
            # Update Home Assistant sensor
            await self._update_ha_sensor(new_state)
            
            # Trigger appropriate routines
            if new_state['active']:
                await self._trigger_routines(new_state, old_state)
            else:
                await self._trigger_clear_routine(old_state)
    
    async def _update_ha_sensor(self, state: Dict):
        """
        Update Home Assistant sensor with current alert state
        
        Args:
            state: Current alert state
        """
        # Main local alert binary sensor (on/off)
        await self.ha_client.set_state(
            'binary_sensor.forewarned_local_alert',
            'on' if state['active'] else 'off',
            {
                'friendly_name': 'Forewarned Local Alert Active',
                'alert_level': state['level'],
                'reason': state['reason'],
                'triggered_by': ', '.join(state['triggered_by']),
                'timestamp': state['timestamp'],
                'device_class': 'safety'
            },
            unique_id='forewarned_local_alert'
        )
        
        # Individual level sensors for easier automation triggers
        for level_name in ['advisory', 'watch', 'warning', 'emergency']:
            entity_id = f'binary_sensor.forewarned_alert_{level_name}'
            is_active = state['active'] and state['level'] == level_name
            
            await self.ha_client.set_state(
                entity_id,
                'on' if is_active else 'off',
                {
                    'friendly_name': f'Forewarned Alert - {level_name.capitalize()}',
                    'icon': 'mdi:alert' if is_active else 'mdi:alert-outline',
                    'reason': state['reason'] if is_active else '',
                    'triggered_by': ', '.join(state['triggered_by']) if is_active else '',
                    'timestamp': state['timestamp'] if is_active else None,
                    'device_class': 'safety'
                },
                unique_id=f'forewarned_alert_{level_name}'
            )
        
        # Alert level as a sensor (text state) - USE THIS FOR AUTOMATIONS
        await self.ha_client.set_state(
            'sensor.forewarned_alert_level',
            state['level'],  # State is the level itself: none, advisory, watch, warning, emergency
            {
                'friendly_name': 'Forewarned Alert Level',
                'icon': self._get_icon_for_level(state['level']),
                'active': state['active'],
                'reason': state['reason'],
                'triggered_by': ', '.join(state['triggered_by']),
                'timestamp': state['timestamp']
            },
            unique_id='forewarned_alert_level'
        )
    
    def _get_icon_for_level(self, level: str) -> str:
        """Get icon for alert level"""
        icons = {
            'none': 'mdi:shield-check',
            'advisory': 'mdi:information',
            'watch': 'mdi:alert-circle',
            'warning': 'mdi:alert',
            'emergency': 'mdi:alarm-light'
        }
        return icons.get(level, 'mdi:help-circle')
    
    async def _trigger_routines(self, new_state: Dict, old_state: Dict):
        """
        Trigger Home Assistant routines based on alert level
        
        Args:
            new_state: New alert state
            old_state: Previous alert state
        """
        level = new_state['level']
        routines = self.config.get('routines', {})
        
        # Map alert levels to routine keys
        routine_mapping = {
            'advisory': 'advisory_alert',
            'watch': 'watch_alert',
            'warning': 'warning_alert',
            'emergency': 'emergency_alert'
        }
        
        routine_key = routine_mapping.get(level)
        if routine_key and routine_key in routines:
            routine_list = routines[routine_key]
            
            for routine in routine_list:
                if routine.startswith('scene.'):
                    await self.ha_client.activate_scene(routine)
                elif routine.startswith('script.'):
                    await self.ha_client.run_script(routine)
                else:
                    logger.warning(f"Unknown routine type: {routine}")
        
        # Send notification
        await self.ha_client.send_notification(
            f"Local alert activated: {new_state['reason']}",
            f"Forewarned - {level.upper()} Alert"
        )
        
        # Make VOIP calls if configured
        if self.voip_integration:
            await self._make_voip_calls(level, new_state['reason'])
    
    async def _make_voip_calls(self, alert_level: str, reason: str):
        """
        Make VOIP calls for alert level
        
        Args:
            alert_level: Alert level (advisory, watch, warning, emergency)
            reason: Reason for alert
        """
        if not self.voip_integration or not self.voip_integration.enabled:
            return
        
        voip_config = self.config.get('voip', {})
        
        # Get alert numbers from config (call all numbers for any alert)
        alert_numbers = voip_config.get('alert_numbers', [])
        
        if not alert_numbers:
            logger.debug(f"No VoIP alert numbers configured")
            return
        
        logger.info(f"Making {len(alert_numbers)} VoIP call(s) for {alert_level} alert")
        
        # Make calls to all configured numbers
        for number in alert_numbers:
            try:
                success = await self.voip_integration.make_alert_call(
                    number, alert_level, reason
                )
                if success:
                    logger.info(f"VoIP call initiated to {number}")
                else:
                    logger.error(f"Failed to initiate VoIP call to {number}")
            except Exception as e:
                logger.error(f"Error making VoIP call to {number}: {e}")
    
    async def _trigger_clear_routine(self, old_state: Dict):
        """
        Trigger clear/all-clear routine when alerts are cleared
        
        Args:
            old_state: Previous alert state
        """
        routines = self.config.get('routines', {})
        clear_routines = routines.get('alert_cleared', [])
        
        for routine in clear_routines:
            if routine.startswith('scene.'):
                await self.ha_client.activate_scene(routine)
            elif routine.startswith('script.'):
                await self.ha_client.run_script(routine)
        
        # Send notification
        await self.ha_client.send_notification(
            "All alerts have been cleared",
            "Forewarned - All Clear"
        )
