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
                default_config.update(user_config)
                logger.info("Loaded configuration from Home Assistant")
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
