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
    
    def __init__(self, config: Dict, ha_client, update_callback, voip_integration=None):
        """
        Initialize local alert manager
        
        Args:
            config: Configuration dictionary
            ha_client: Home Assistant client instance
            update_callback: Callback function to update app state
            voip_integration: Optional VOIP integration instance
        """
        self.config = config
        self.ha_client = ha_client
        self.update_callback = update_callback
        self.voip_integration = voip_integration
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
        
        # Manual override switch entity IDs
        self.manual_switches = {
            'advisory': 'input_boolean.forewarned_manual_advisory',
            'watch': 'input_boolean.forewarned_manual_watch',
            'warning': 'input_boolean.forewarned_manual_warning',
            'emergency': 'input_boolean.forewarned_manual_emergency'
        }
    
    async def _check_manual_overrides(self) -> tuple[Optional[str], Optional[str]]:
        """
        Check if any manual override switches are active
        
        Returns:
            Tuple of (level, reason) or (None, None) if no overrides active
        """
        # Check switches in priority order (highest to lowest)
        for level in ['emergency', 'warning', 'watch', 'advisory']:
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
        await self.ha_client.set_state(
            'binary_sensor.forewarned_local_alert',
            'on' if state['active'] else 'off',
            {
                'friendly_name': 'Forewarned Local Alert',
                'alert_level': state['level'],
                'reason': state['reason'],
                'triggered_by': ', '.join(state['triggered_by']),
                'timestamp': state['timestamp']
            }
        )
    
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
        alert_calls = voip_config.get('alert_calls', {})
        
        # Get extensions to call for this alert level
        extensions = alert_calls.get(alert_level, [])
        
        if not extensions:
            logger.debug(f"No VOIP calls configured for {alert_level} level")
            return
        
        logger.info(f"Making {len(extensions)} VOIP call(s) for {alert_level} alert")
        
        # Make calls to all configured extensions
        for extension in extensions:
            try:
                success = await self.voip_integration.make_alert_call(
                    extension, alert_level, reason
                )
                if success:
                    logger.info(f"VOIP call initiated to {extension}")
                else:
                    logger.error(f"Failed to initiate VOIP call to {extension}")
            except Exception as e:
                logger.error(f"Error making VOIP call to {extension}: {e}")
    
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
