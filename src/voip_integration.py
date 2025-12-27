"""VOIP/SIP Integration for Forewarned"""
import logging
import asyncio
from typing import Optional, Dict, Callable
import os
import tempfile
import subprocess

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


class AlertCall(pj.Call):
    """Custom Call class to handle inbound/outbound calls with TTS"""
    
    def __init__(self, account, call_id=pj.PJSUA_INVALID_ID, voip_integration=None):
        pj.Call.__init__(self, account, call_id)
        self.voip = voip_integration
        self.tts_player = None
        
    def onCallState(self, prm):
        """Callback when call state changes"""
        ci = self.getInfo()
        logger.info(f"Call {ci.callIdString} state: {ci.stateText}")
        
        if ci.state == pj.PJSIP_INV_STATE_CONFIRMED:
            # Call answered - play TTS
            logger.info("Call answered, playing TTS message")
            self._play_tts_message()
        elif ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            logger.info(f"Call ended: {ci.lastReason}")
            
            # Clean up TTS player
            if self.tts_player:
                try:
                    self.tts_player = None
                except:
                    pass
            
            # Remove from active calls
            if self.voip and hasattr(self.voip, 'active_calls'):
                call_id = ci.id
                if call_id in self.voip.active_calls:
                    del self.voip.active_calls[call_id]
                    logger.info(f"Removed call {call_id} from active calls")
    
    def onCallMediaState(self, prm):
        """Callback when media state changes"""
        ci = self.getInfo()
        
        for mi in ci.media:
            if mi.type == pj.PJMEDIA_TYPE_AUDIO and mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                # Get audio media
                aud_med = self.getAudioMedia(mi.index)
                
                # Connect to sound device
                aud_med.startTransmit(pj.Endpoint.instance().audDevManager().getPlaybackDevMedia())
                pj.Endpoint.instance().audDevManager().getCaptureDevMedia().startTransmit(aud_med)
                
                logger.info("Audio media connected")
    
    def _play_tts_message(self):
        """Play TTS message on call"""
        if not self.voip:
            return
            
        # Generate message text
        state = self.voip.get_alert_state()
        message = self.voip.generate_status_tts()
        
        logger.info(f"Playing message: {message}")
        
        # For basic implementation, use pico2wave or espeak for TTS
        # Generate WAV file and play it
        try:
            wav_file = self._generate_tts_wav(message)
            if wav_file:
                self._play_wav_file(wav_file)
        except Exception as e:
            logger.error(f"Error playing TTS: {e}")
    
    def _generate_tts_wav(self, text: str) -> Optional[str]:
        """Generate WAV file from text using TTS"""
        try:
            # Create temporary WAV file
            temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_wav.close()
            
            # Use espeak (available in Alpine main repo)
            try:
                subprocess.run([
                    'espeak', '-w', temp_wav.name, text
                ], check=True, capture_output=True)
                logger.info(f"Generated TTS with espeak: {temp_wav.name}")
                return temp_wav.name
            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                logger.error(f"espeak TTS failed: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating TTS WAV: {e}")
            return None
    
    def _play_wav_file(self, wav_path: str):
        """Play WAV file to call"""
        try:
            # Create WAV player
            player = pj.AudioMediaPlayer()
            player.createPlayer(wav_path, pj.PJMEDIA_FILE_NO_LOOP)
            
            # Connect to call
            ci = self.getInfo()
            for mi in ci.media:
                if mi.type == pj.PJMEDIA_TYPE_AUDIO and mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                    aud_med = self.getAudioMedia(mi.index)
                    player.startTransmit(aud_med)
                    self.tts_player = player
                    logger.info(f"Playing WAV file to call: {wav_path}")
                    break
                    
        except Exception as e:
            logger.error(f"Error playing WAV file: {e}")


class AlertAccount(pj.Account):
    """Custom Account class to handle incoming calls"""
    
    def __init__(self, voip_integration=None):
        pj.Account.__init__(self)
        self.voip = voip_integration
        
    def onRegState(self, prm):
        """Callback when registration state changes"""
        ai = self.getInfo()
        logger.info(f"SIP registration status: {ai.regStatusText} (code: {ai.regStatus})")
        if ai.regIsActive:
            if self.voip:
                self.voip.registration_active = True
            logger.info("SIP registration ACTIVE - ready to make and receive calls")
        else:
            if self.voip:
                self.voip.registration_active = False
            logger.warning("SIP registration INACTIVE")
    
    def onIncomingCall(self, prm):
        """Callback for incoming calls"""
        logger.info(f"onIncomingCall triggered - CallId: {prm.callId}")
        
        # Create call object - this takes ownership of the call
        call = AlertCall(self, prm.callId, self.voip)
        
        # Store reference to prevent garbage collection
        if self.voip:
            self.voip.active_calls[prm.callId] = call
        
        # Get call info
        ci = call.getInfo()
        logger.info(f"Incoming call from {ci.remoteUri}")
        
        # Auto-answer incoming calls
        try:
            call_prm = pj.CallOpParam()
            call_prm.statusCode = 200
            call.answer(call_prm)
            logger.info("Incoming call answered automatically")
        except Exception as e:
            logger.error(f"Error answering call: {e}")


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
        self.registration_active = False  # Track SIP registration status
        self.active_calls = {}  # Store references to active Call objects
        
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
    
    def shutdown(self):
        """Cleanup VoIP resources"""
        if self.backend == 'sip' and hasattr(self, 'ep') and self.ep:
            try:
                logger.info("Shutting down SIP endpoint")
                self.ep.libDestroy()
            except Exception as e:
                logger.error(f"Error shutting down SIP: {e}")
    
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
        self.sip_port = self.config.get('sip_port', 5060)  # Default to standard SIP port
        
        if not all([self.sip_server, self.sip_user, self.sip_password, self.sip_domain]):
            logger.error("SIP backend requires server, user, password, and domain to be configured")
            self.enabled = False
            return
        
        # Initialize PJSUA2 library
        self.ep = None
        self.account = None
        
        try:
            # Create endpoint
            self.ep = pj.Endpoint()
            self.ep.libCreate()
            
            # Initialize endpoint with logging and null audio device
            ep_cfg = pj.EpConfig()
            ep_cfg.logConfig.level = 5  # 0=none, 6=max verbosity
            ep_cfg.logConfig.consoleLevel = 5
            ep_cfg.logConfig.msgLogging = 1  # Enable SIP message logging
            
            # Configure null audio device for headless operation
            ep_cfg.medConfig.noVad = True  # Disable voice activity detection
            ep_cfg.medConfig.ecTailLen = 0  # Disable echo cancellation
            
            self.ep.libInit(ep_cfg)
            
            logger.info("PJSUA2 initialized with SIP message logging enabled")
            
            # Set null audio device (no actual hardware needed)
            try:
                aud_dev_mgr = self.ep.audDevManager()
                # Set to null device (-1 for capture, -2 for playback means null device)
                aud_dev_mgr.setNullDev()
                logger.info("Using null audio device for headless operation")
            except Exception as e:
                logger.warning(f"Could not set null audio device: {e}")
            
            # Create SIP transport
            sipTpConfig = pj.TransportConfig()
            sipTpConfig.port = self.sip_port  # Use configured port (default 5060)
            self.ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, sipTpConfig)
            
            logger.info(f"SIP transport created on UDP port {self.sip_port}")
            
            # Start the library
            self.ep.libStart()
            
            # Create and configure account
            acc_cfg = pj.AccountConfig()
            acc_cfg.idUri = f"sip:{self.sip_user}@{self.sip_domain}"
            acc_cfg.regConfig.registrarUri = f"sip:{self.sip_server}"
            
            # Set credentials
            cred = pj.AuthCredInfo("digest", "*", self.sip_user, 0, self.sip_password)
            acc_cfg.sipConfig.authCreds.append(cred)
            
            # Create custom account that handles incoming calls
            self.account = AlertAccount(voip_integration=self)
            self.account.create(acc_cfg)
            
            logger.info(f"SIP registration initiated for {self.sip_user}@{self.sip_domain} via {self.sip_server}")
            logger.info("Ready to accept incoming calls with TTS playback")
            
        except Exception as e:
            logger.error(f"Failed to initialize SIP: {e}")
            self.enabled = False
            if self.ep:
                try:
                    self.ep.libDestroy()
                except:
                    pass
    
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
        if not self.ep or not self.account:
            logger.error("SIP not initialized - cannot make call")
            return False
        
        # Wait for registration with timeout
        if not self.registration_active:
            logger.info("SIP not yet registered. Waiting up to 10 seconds for registration...")
            max_wait = 10  # seconds
            waited = 0
            while not self.registration_active and waited < max_wait:
                await asyncio.sleep(0.5)
                waited += 0.5
            
            if not self.registration_active:
                logger.error(f"SIP registration timeout after {max_wait} seconds - cannot make call")
                return False
            
            logger.info("SIP registration confirmed - proceeding with call")
        
        try:
            # Create call URI
            call_uri = f"sip:{extension}@{self.sip_domain}"
            
            # Create custom call with TTS support
            call = AlertCall(self.account, voip_integration=self)
            call_param = pj.CallOpParam()
            call_param.opt.audioCount = 1
            call_param.opt.videoCount = 0
            
            # Make the call
            call.makeCall(call_uri, call_param)
            
            # Store reference to prevent garbage collection
            ci = call.getInfo()
            self.active_calls[ci.id] = call
            
            logger.info(f"SIP call initiated to {call_uri} with TTS playback")
            
            return True
            
        except Exception as e:
            logger.error(f"Error making SIP call: {e}")
            return False
            
            # Note: In production, you'd want to:
            # 1. Wait for call to be answered
            # 2. Play TTS message
            # 3. Handle call events
            # This is a basic implementation
            
            return True
            
        except Exception as e:
            logger.error(f"Error making SIP call: {e}")
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
