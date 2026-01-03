"""Configuration management for Forewarned"""
import os
import json
import logging

logger = logging.getLogger(__name__)


def load_config():
    """
    Load configuration from Home Assistant addon options
    
    Returns:
        dict: Configuration dictionary
    """
    config_path = '/data/options.json'
    
    # Default configuration
    default_config = {
        'weather_api_key': '',
        'check_interval': 300,  # 5 minutes
        'eoc_urls': [
            'https://disaster.townsville.qld.gov.au/'
        ],
        'weather_sources': {
            'bom': True,  # Australian Bureau of Meteorology
        },
        'location': 'Townsville',  # Primary location to monitor
        'alert_types': [
            'Severe Thunderstorm Warning',
            'Severe Weather Warning',
            'Flood Warning',
            'Fire Weather Warning',
            'Tropical Cyclone Warning',
            'Tsunami Warning',
            'Heatwave Warning'
        ],
        'routines': {
            # Legacy routine keys (deprecated, use local alert levels instead)
            'tornado_warning': [],
            'severe_weather': [],
            'eoc_activated': [],
            'eoc_alert': [],
            'eoc_lean_forward': [],
            'eoc_stand_up': [],
            'eoc_stand_down': [],
            # Local alert state routines (recommended)
            'advisory_alert': [],      # Minor alerts, informational
            'watch_alert': [],          # Moderate alerts, prepare
            'warning_alert': [],        # Severe alerts, take action
            'emergency_alert': [],      # Extreme alerts, immediate action
            'alert_cleared': []         # All alerts cleared
        },
        'alert_rules': {
            'advisory': {
                'weather_conditions': {
                    'operator': 'or',  # 'and' or 'or'
                    'rules': [
                        {'type': 'any', 'severity': 'minor'}
                    ]
                },
                'eoc_conditions': {
                    'operator': 'or',
                    'rules': [
                        {'state': 'alert'},
                        {'state': 'stand down'}
                    ]
                },
                'condition_logic': 'or'  # 'and' or 'or' between weather and eoc
            },
            'watch': {
                'weather_conditions': {
                    'operator': 'or',
                    'rules': [
                        {'type': 'any', 'severity': 'moderate'}
                    ]
                },
                'eoc_conditions': {
                    'operator': 'or',
                    'rules': [
                        {'state': 'lean forward'}
                    ]
                },
                'condition_logic': 'or'
            },
            'warning': {
                'weather_conditions': {
                    'operator': 'or',
                    'rules': [
                        {'type': 'any', 'severity': 'severe'}
                    ]
                },
                'eoc_conditions': {
                    'operator': 'or',
                    'rules': []
                },
                'condition_logic': 'or'
            },
            'emergency': {
                'weather_conditions': {
                    'operator': 'or',
                    'rules': [
                        {'type': 'any', 'severity': 'extreme'},
                        {'type': 'Tropical Cyclone Warning', 'severity': 'any'}
                    ]
                },
                'eoc_conditions': {
                    'operator': 'or',
                    'rules': [
                        {'state': 'stand up'}
                    ]
                },
                'condition_logic': 'or'
            }
        }
    }
    
    try:
        # Try to load from Home Assistant config
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                logger.info(f"Loaded configuration from Home Assistant: {config_path}")
                logger.debug(f"VoIP settings from options.json: voip_enabled={user_config.get('voip_enabled')}, voip_alert_numbers={user_config.get('voip_alert_numbers')}")
                logger.debug(f"MQTT settings from options.json: mqtt_enabled={user_config.get('mqtt_enabled')}, mqtt_broker={user_config.get('mqtt_broker')}, mqtt_username={user_config.get('mqtt_username')}, mqtt_password={'***' if user_config.get('mqtt_password') else '(none)'}")
                default_config.update(user_config)
        else:
            logger.warning(f"Config file not found at {config_path}, using defaults")
            
            # In development mode, try to load from local config file
            local_config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config_data.json')
            if os.path.exists(local_config_path):
                with open(local_config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
                    logger.info(f"Loaded configuration from {local_config_path}")
            
        # Override with environment variables
        if os.getenv('WEATHER_API_KEY'):
            default_config['weather_api_key'] = os.getenv('WEATHER_API_KEY')
        if os.getenv('CHECK_INTERVAL'):
            default_config['check_interval'] = int(os.getenv('CHECK_INTERVAL'))
        
        # Build VoIP configuration from flat addon options
        if any(key.startswith('voip_') for key in default_config.keys()):
            default_config['voip'] = {
                'enabled': default_config.get('voip_enabled', False),
                'backend': default_config.get('voip_backend', 'webhook'),
                'sip_server': default_config.get('voip_sip_server', ''),
                'sip_user': default_config.get('voip_sip_user', ''),
                'sip_password': default_config.get('voip_sip_password', ''),
                'sip_domain': default_config.get('voip_sip_domain', ''),
                'sip_port': default_config.get('voip_sip_port', 5060),
                'webhook_url': default_config.get('voip_webhook_url', ''),
                'webhook_method': default_config.get('voip_webhook_method', 'POST'),
                'webhook_auth': {
                    'type': default_config.get('voip_webhook_auth_type', 'none'),
                    'username': default_config.get('voip_webhook_username', ''),
                    'password': default_config.get('voip_webhook_password', ''),
                    'token': default_config.get('voip_webhook_token', '')
                },
                'alert_numbers': default_config.get('voip_alert_numbers', []),
                'tts_voice': default_config.get('voip_tts_voice', 'en-us'),
                'tts_speed': default_config.get('voip_tts_speed', 160)
            }
            logger.info(f"VoIP configuration loaded: enabled={default_config['voip']['enabled']}, backend={default_config['voip']['backend']}, tts_voice={default_config['voip']['tts_voice']}, tts_speed={default_config['voip']['tts_speed']}")
        
        # Build MQTT configuration from flat addon options
        if any(key.startswith('mqtt_') for key in default_config.keys()):
            default_config['mqtt'] = {
                'enabled': default_config.get('mqtt_enabled', True),
                'broker': default_config.get('mqtt_broker', 'core-mosquitto'),
                'port': default_config.get('mqtt_port', 1883),
                'username': default_config.get('mqtt_username', ''),
                'password': default_config.get('mqtt_password', '')
            }
            logger.info(f"MQTT configuration loaded: enabled={default_config['mqtt']['enabled']}, broker={default_config['mqtt']['broker']}, username={'(set)' if default_config['mqtt']['username'] else '(none)'}, password={'(set)' if default_config['mqtt']['password'] else '(none)'}")
            
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        
    return default_config


def save_config(config):
    """
    Save configuration
    
    Args:
        config: Configuration dictionary to save
    """
    try:
        # Use /data/config.json in production (HA addon), otherwise use local file
        if os.path.exists('/data'):
            config_path = '/data/config.json'
        else:
            # Development mode - save to local directory
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config_data.json')
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Configuration saved to {config_path}")
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
