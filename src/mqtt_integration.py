"""MQTT integration for Home Assistant discovery"""
import json
import logging
import asyncio
import time
from typing import Dict, Optional, Callable
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTIntegration:
    """Handles MQTT discovery and communication with Home Assistant"""
    
    def __init__(self, config: Dict, state_change_callback: Optional[Callable] = None):
        """
        Initialize MQTT integration
        
        Args:
            config: MQTT configuration dictionary
            state_change_callback: Callback function when switch state changes
        """
        self.config = config
        self.state_change_callback = state_change_callback
        self.client = None
        self.connected = False
        self.switches = {}
        self.switch_states = {}
        
    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        rc_messages = {
            0: "Connection successful",
            1: "Connection refused - incorrect protocol version",
            2: "Connection refused - invalid client identifier",
            3: "Connection refused - server unavailable",
            4: "Connection refused - bad username or password",
            5: "Connection refused - not authorized"
        }
        
        if rc == 0:
            logger.info(f"✓ MQTT broker connection successful")
            self.connected = True
            # Subscribe to all command topics
            if len(self.switches) > 0:
                for switch_id in self.switches:
                    command_topic = f"homeassistant/switch/forewarned/{switch_id}/set"
                    client.subscribe(command_topic)
                logger.debug(f"Subscribed to {len(self.switches)} switch command topics")
            else:
                logger.debug("No switches configured yet - will subscribe after discovery")
        else:
            error_msg = rc_messages.get(rc, f"Unknown error code {rc}")
            logger.error(f"✗ MQTT connection failed: {error_msg}")
            self.connected = False
            
    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        logger.warning(f"Disconnected from MQTT broker (rc={rc})")
        self.connected = False
        
    def on_message(self, client, userdata, msg):
        """Callback when message received"""
        try:
            # Extract switch ID from topic
            # Topic format: homeassistant/switch/forewarned/{switch_id}/set
            parts = msg.topic.split('/')
            if len(parts) >= 4 and parts[0] == 'homeassistant' and parts[1] == 'switch':
                switch_id = parts[3]
                state = msg.payload.decode('utf-8').upper()
                
                if switch_id in self.switches:
                    logger.info(f"Switch {switch_id} state changed to {state}")
                    self.switch_states[switch_id] = (state == 'ON')
                    
                    # Publish state confirmation
                    state_topic = f"homeassistant/switch/forewarned/{switch_id}/state"
                    client.publish(state_topic, state, retain=True)
                    
                    # Call state change callback if provided
                    if self.state_change_callback:
                        asyncio.create_task(self.state_change_callback(switch_id, state == 'ON'))
                        
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
            
    async def connect(self):
        """Connect to MQTT broker"""
        # Prevent multiple simultaneous connections
        if self.client is not None:
            logger.warning("MQTT client already exists - skipping duplicate connection")
            return self.connected
            
        try:
            broker = self.config.get('broker', 'core-mosquitto')
            port = self.config.get('port', 1883)
            username = self.config.get('username', '')
            password = self.config.get('password', '')
            
            logger.info(f"MQTT Configuration: broker={broker}, port={port}, username={'(set)' if username else '(none)'}")
            
            # Use unique client ID with timestamp to prevent conflicts on restart
            client_id = f"forewarned_addon_{int(time.time())}"
            self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
            logger.info(f"MQTT client ID: {client_id}")
            
            # Disable automatic reconnection to prevent loops
            self.client.reconnect_delay_set(min_delay=1, max_delay=120)
            
            if username and password:
                logger.info("Setting MQTT authentication credentials")
                self.client.username_pw_set(username, password)
            elif username:
                logger.warning("MQTT username set but no password provided")
                
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message
            
            logger.info(f"Attempting to connect to MQTT broker at {broker}:{port}...")
            try:
                self.client.connect_async(broker, port, 60)
                self.client.loop_start()
            except Exception as conn_err:
                logger.error(f"Failed to initiate MQTT connection: {conn_err}")
                logger.error(f"Check that the broker '{broker}' is reachable and port {port} is correct")
                return False
            
            # Wait for connection
            for i in range(30):  # 30 second timeout
                if self.connected:
                    logger.info(f"MQTT connection established after {i+1} seconds")
                    return True
                await asyncio.sleep(1)
                
            logger.error(f"Timeout waiting for MQTT connection to {broker}:{port}")
            logger.error("Possible issues: broker not running, incorrect hostname/IP, firewall blocking connection")
            logger.error("Try using the broker's IP address instead of hostname if using 'core-mosquitto'")
            return False
            
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}", exc_info=True)
            return False
            
    def publish_discovery(self, switch_id: str, name: str, icon: str = "mdi:alert"):
        """
        Publish MQTT discovery message for a switch
        
        Args:
            switch_id: Unique identifier for the switch (e.g., 'manual_advisory')
            name: Friendly name for the switch
            icon: Material Design Icon for the switch
        """
        if not self.connected:
            logger.error("Cannot publish discovery - not connected to MQTT")
            return False
            
        try:
            # Discovery topic
            discovery_topic = f"homeassistant/switch/forewarned/{switch_id}/config"
            
            # Command and state topics
            command_topic = f"homeassistant/switch/forewarned/{switch_id}/set"
            state_topic = f"homeassistant/switch/forewarned/{switch_id}/state"
            
            # Build discovery payload
            discovery_payload = {
                "name": name,
                "unique_id": f"forewarned_{switch_id}",
                "command_topic": command_topic,
                "state_topic": state_topic,
                "payload_on": "ON",
                "payload_off": "OFF",
                "state_on": "ON",
                "state_off": "OFF",
                "icon": icon,
                "device": {
                    "identifiers": ["forewarned_addon"],
                    "name": "Forewarned",
                    "model": "Weather & EOC Alert System",
                    "manufacturer": "Forewarned",
                    "sw_version": "1.0.50"
                }
            }
            
            # Publish discovery message
            result = self.client.publish(
                discovery_topic,
                json.dumps(discovery_payload),
                qos=1,
                retain=True
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published discovery for {switch_id}")
                self.switches[switch_id] = {
                    'name': name,
                    'command_topic': command_topic,
                    'state_topic': state_topic
                }
                
                # Initialize state as OFF
                self.switch_states[switch_id] = False
                self.client.publish(state_topic, "OFF", retain=True)
                
                return True
            else:
                logger.error(f"Failed to publish discovery for {switch_id}: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing discovery: {e}")
            return False
            
    def publish_state(self, switch_id: str, state: bool):
        """
        Publish switch state update
        
        Args:
            switch_id: Switch identifier
            state: True for ON, False for OFF
        """
        if not self.connected:
            logger.warning(f"Cannot publish state for {switch_id} - not connected")
            return False
            
        if switch_id not in self.switches:
            logger.error(f"Unknown switch: {switch_id}")
            return False
            
        try:
            state_topic = self.switches[switch_id]['state_topic']
            payload = "ON" if state else "OFF"
            
            result = self.client.publish(state_topic, payload, retain=True)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.switch_states[switch_id] = state
                return True
            else:
                logger.error(f"Failed to publish state for {switch_id}: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing state: {e}")
            return False
            
    def get_state(self, switch_id: str) -> Optional[bool]:
        """Get current switch state"""
        return self.switch_states.get(switch_id)
        
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("Disconnected from MQTT broker")
