"""
Forewarned - Home Assistant Weather Alerting & EOC State Monitor
"""
import os
import logging
import asyncio
from flask import Flask
from threading import Thread

from src.config import load_config
from src.weather_monitor import WeatherMonitor
from src.eoc_monitor import EOCMonitor
from src.web_ui import create_app, app_state, update_local_alert_state
from src.ha_integration import HomeAssistantClient
from src.local_alert_manager import LocalAlertManager
from src.voip_integration import VOIPIntegration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_monitors():
    """Run the monitoring tasks"""
    config = load_config()
    
    # Initialize Home Assistant client
    ha_client = HomeAssistantClient(
        supervisor_token=os.getenv('SUPERVISOR_TOKEN')
    )
    
    # Initialize VOIP integration (if configured)
    voip_integration = None
    if 'voip' in config and config['voip'].get('enabled', False):
        logger.info("Initializing VOIP integration...")
        voip_integration = VOIPIntegration(
            config.get('voip', {}),
            lambda: app_state.get('local_alert_state', {})
        )
        logger.info(f"VOIP integration initialized with backend: {config['voip'].get('backend', 'webhook')}")
    
    # Initialize local alert manager
    alert_manager = LocalAlertManager(
        config, 
        ha_client, 
        update_local_alert_state,
        voip_integration=voip_integration
    )
    
    # Store alert manager in app state for access by monitors
    app_state['alert_manager'] = alert_manager
    app_state['voip_integration'] = voip_integration
    
    # Initialize monitors with shared state
    weather_monitor = WeatherMonitor(config, ha_client, app_state)
    eoc_monitor = EOCMonitor(config, ha_client, app_state)
    
    # Start monitoring tasks
    await asyncio.gather(
        weather_monitor.start(),
        eoc_monitor.start()
    )


def start_monitoring():
    """Start the monitoring loop in async context"""
    asyncio.run(run_monitors())


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Starting Forewarned - Weather & EOC Monitor")
    logger.info("=" * 60)
    
    try:
        # Load configuration
        config = load_config()
        
        # Start monitoring in background thread
        monitor_thread = Thread(target=start_monitoring, daemon=True)
        monitor_thread.start()
        
        # Start web UI
        app = create_app()
        
        # Store VOIP integration reference in Flask app
        # (will be populated when monitors start)
        app.voip_integration = None
        
        port = int(os.getenv('PORT', 5000))
        logger.info(f"Starting web server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=True)
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
