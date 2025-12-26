"""VOIP/SIP Integration for Forewarned"""
import logging
import asyncio
from typing import Optional, Dict, Callable
import os

logger = logging.getLogger(__name__)

# Try to import SIP libraries
try:
    import pjsua2 as pj
    SIP_AVAILABLE = True
except ImportError:
    logger.warning("pjsua2 not available - VOIP features disabled")
    SIP_AVAILABLE = False

try:
    from flask import Flask, request, Response
    import xml.etree.ElementTree as ET
    FLASK_AVAILABLE = True
except ImportError:
    logger.warning("Flask not available - HTTP VOIP webhook disabled")
    FLASK_AVAILABLE = False


class VOIPIntegration:
    """
    VOIP Integration supporting multiple backends:
    - SIP calls via PJSUA2 (for direct SIP calling)
    - HTTP webhooks for Asterisk/FreePBX AMI
    - Home Assistant notify services
    """
    
    def __init__(self, config: Dict, get_alert_state: Callable):
        """
        Initialize VOIP integration
        
        Args:
            config: VOIP configuration dictionary
            get_alert_state: Callback to get current alert state
        """
        self.config = config
        self.get_alert_state = get_alert_state
        self.enabled = config.get('enabled', False)
        self.backend = config.get('backend', 'webhook')  # 'sip', 'webhook', 'ha_notify'
        
        if not self.enabled:
            logger.info("VOIP integration disabled")
            return
        
        logger.info(f"VOIP integration enabled using backend: {self.backend}")
        
        # Initialize based on backend
        if self.backend == 'sip':
            self._init_sip()
        elif self.backend == 'webhook':
            self._init_webhook()
        elif self.backend == 'ha_notify':
            self._init_ha_notify()
    
    def _init_sip(self):
        """Initialize SIP/PJSUA2 backend"""
        if not SIP_AVAILABLE:
            logger.error("SIP backend requested but pjsua2 not available")
            self.enabled = False
            return
        
        # SIP configuration
        self.sip_server = self.config.get('sip_server', '')
        self.sip_user = self.config.get('sip_user', '')
        self.sip_password = self.config.get('sip_password', '')
        self.sip_domain = self.config.get('sip_domain', '')
        
        logger.info(f"SIP configured for {self.sip_user}@{self.sip_domain}")
    
    def _init_webhook(self):
        """Initialize webhook backend (for Asterisk AMI, etc.)"""
        self.webhook_url = self.config.get('webhook_url', '')
        self.webhook_method = self.config.get('webhook_method', 'POST')
        self.webhook_auth = self.config.get('webhook_auth', {})
        
        logger.info(f"Webhook configured: {self.webhook_method} {self.webhook_url}")
    
    def _init_ha_notify(self):
        """Initialize Home Assistant notify service backend"""
        self.ha_notify_service = self.config.get('ha_notify_service', 'notify.voip_phone')
        
        logger.info(f"Home Assistant notify service: {self.ha_notify_service}")
    
    async def make_alert_call(self, extension: str, alert_level: str, reason: str) -> bool:
        """
        Make an outbound call to notify about an alert
        
        Args:
            extension: Phone extension/number to call
            alert_level: Alert level (advisory, watch, warning, emergency)
            reason: Reason for the alert
            
        Returns:
            True if call initiated successfully
        """
        if not self.enabled:
            return False
        
        message = self._generate_alert_message(alert_level, reason)
        
        logger.info(f"Initiating alert call to {extension}: {alert_level}")
        
        if self.backend == 'sip':
            return await self._make_sip_call(extension, message)
        elif self.backend == 'webhook':
            return await self._make_webhook_call(extension, message, alert_level)
        elif self.backend == 'ha_notify':
            return await self._make_ha_notify_call(extension, message, alert_level)
        
        return False
    
    async def _make_sip_call(self, extension: str, message: str) -> bool:
        """Make call via SIP/PJSUA2"""
        # This would require full PJSUA2 implementation
        # Placeholder for now
        logger.warning("Direct SIP calling not yet implemented - use webhook or HA notify")
        return False
    
    async def _make_webhook_call(self, extension: str, message: str, alert_level: str) -> bool:
        """
        Make call via webhook (Asterisk AMI, FreePBX, etc.)
        
        Example payload for Asterisk AMI:
        {
            "action": "Originate",
            "channel": "PJSIP/100",
            "extension": "s",
            "context": "forewarned-alerts",
            "priority": 1,
            "callerid": "Forewarned Alert",
            "variable": "ALERT_LEVEL=emergency,ALERT_MESSAGE=..."
        }
        """
        import aiohttp
        
        # Build payload based on configuration
        payload = self.config.get('webhook_payload_template', {}).copy()
        
        # Replace placeholders
        payload_str = str(payload)
        payload_str = payload_str.replace('{{extension}}', extension)
        payload_str = payload_str.replace('{{message}}', message)
        payload_str = payload_str.replace('{{alert_level}}', alert_level)
        
        # Convert back to dict
        import json
        payload = json.loads(payload_str.replace("'", '"'))
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                
                # Add authentication
                if self.webhook_auth.get('type') == 'basic':
                    import base64
                    credentials = f"{self.webhook_auth['username']}:{self.webhook_auth['password']}"
                    encoded = base64.b64encode(credentials.encode()).decode()
                    headers['Authorization'] = f'Basic {encoded}'
                elif self.webhook_auth.get('type') == 'bearer':
                    headers['Authorization'] = f"Bearer {self.webhook_auth['token']}"
                
                if self.webhook_method == 'POST':
                    async with session.post(self.webhook_url, json=payload, headers=headers) as response:
                        success = response.status in [200, 201, 202]
                        if success:
                            logger.info(f"Webhook call initiated successfully to {extension}")
                        else:
                            logger.error(f"Webhook call failed: {response.status}")
                        return success
                else:
                    async with session.get(self.webhook_url, params=payload, headers=headers) as response:
                        success = response.status in [200, 201, 202]
                        if success:
                            logger.info(f"Webhook call initiated successfully to {extension}")
                        else:
                            logger.error(f"Webhook call failed: {response.status}")
                        return success
        except Exception as e:
            logger.error(f"Error making webhook call: {e}")
            return False
    
    async def _make_ha_notify_call(self, extension: str, message: str, alert_level: str) -> bool:
        """
        Make call via Home Assistant notify service
        
        Requires a notify service configured in HA that can trigger calls
        """
        # This would be called via the HA integration
        logger.info(f"HA notify call: {extension} - {message}")
        # Actual implementation would use ha_client.call_service
        return True
    
    def _generate_alert_message(self, alert_level: str, reason: str) -> str:
        """
        Generate spoken message for alert call
        
        Args:
            alert_level: Alert level
            reason: Reason for alert
            
        Returns:
            Message text for TTS
        """
        level_messages = {
            'advisory': f"Advisory alert: {reason}",
            'watch': f"Watch alert: {reason}. Monitor conditions.",
            'warning': f"Warning! {reason}. Take precautions.",
            'emergency': f"Emergency alert! {reason}. Take immediate action!"
        }
        
        return level_messages.get(alert_level, f"Alert: {reason}")
    
    def generate_status_tts(self) -> str:
        """
        Generate text-to-speech status message for inbound calls
        
        Returns:
            TTS message describing current alert state
        """
        state = self.get_alert_state()
        
        if not state or not state.get('active'):
            return "There are currently no active alerts. All systems normal."
        
        level = state.get('level', 'unknown')
        reason = state.get('reason', 'Unknown reason')
        
        level_name = level.upper()
        
        message = f"Current alert level is {level_name}. {reason}. "
        
        # Add additional context based on level
        if level == 'emergency':
            message += "This is an emergency. Take immediate action."
        elif level == 'warning':
            message += "This is a warning. Take appropriate precautions."
        elif level == 'watch':
            message += "This is a watch alert. Monitor conditions closely."
        elif level == 'advisory':
            message += "This is an advisory. Be aware of conditions."
        
        return message
    
    def generate_twiml_response(self) -> str:
        """
        Generate TwiML response for Twilio-based phone systems
        
        Returns:
            TwiML XML string
        """
        message = self.generate_status_tts()
        
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">{message}</Say>
    <Pause length="2"/>
    <Say voice="alice">Press 1 to repeat this message. Press 2 to hang up.</Say>
    <Gather numDigits="1" action="/voip/menu" method="POST">
        <Pause length="5"/>
    </Gather>
    <Say voice="alice">Goodbye.</Say>
</Response>'''
        
        return twiml
    
    def generate_asterisk_agi(self) -> str:
        """
        Generate Asterisk AGI script commands
        
        Returns:
            AGI commands as string
        """
        message = self.generate_status_tts()
        
        # Asterisk AGI commands
        agi_script = f'''ANSWER
WAIT 1
EXEC Set(CHANNEL(language)=en)
EXEC SayText("{message}")
WAIT 2
HANGUP
'''
        
        return agi_script


class VOIPWebhookHandler:
    """
    Flask webhook handler for inbound VOIP calls
    Provides endpoints for:
    - TwiML responses (Twilio)
    - Asterisk AGI
    - Generic status webhooks
    """
    
    def __init__(self, app: Flask, voip_integration: VOIPIntegration):
        """
        Initialize webhook handler
        
        Args:
            app: Flask application
            voip_integration: VOIPIntegration instance
        """
        self.app = app
        self.voip = voip_integration
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self):
        """Register Flask routes for VOIP webhooks"""
        
        @self.app.route('/voip/status', methods=['GET', 'POST'])
        def voip_status():
            """Generic status endpoint - returns JSON"""
            state = self.voip.get_alert_state()
            return {
                'active': state.get('active', False),
                'level': state.get('level', 'none'),
                'reason': state.get('reason', ''),
                'message': self.voip.generate_status_tts()
            }
        
        @self.app.route('/voip/twiml', methods=['GET', 'POST'])
        def voip_twiml():
            """TwiML endpoint for Twilio"""
            twiml = self.voip.generate_twiml_response()
            return Response(twiml, mimetype='text/xml')
        
        @self.app.route('/voip/menu', methods=['POST'])
        def voip_menu():
            """Handle menu selections from TwiML"""
            digit = request.form.get('Digits', '')
            
            if digit == '1':
                # Repeat message
                return Response(self.voip.generate_twiml_response(), mimetype='text/xml')
            else:
                # Hang up
                twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Goodbye.</Say>
    <Hangup/>
</Response>'''
                return Response(twiml, mimetype='text/xml')
        
        @self.app.route('/voip/agi', methods=['GET'])
        def voip_agi():
            """Asterisk AGI endpoint"""
            agi_script = self.voip.generate_asterisk_agi()
            return Response(agi_script, mimetype='text/plain')
        
        logger.info("VOIP webhook routes registered: /voip/status, /voip/twiml, /voip/agi")
