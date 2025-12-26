# Forewarned ⚠️

A Home Assistant addon for monitoring weather alerts and Emergency Operations Center (EOC) status, with automated routine activation based on conditions.

## Features

- **Weather Alert Monitoring**
  - Australian Bureau of Meteorology (BOM) integration via FTP
  - Real-time severe weather warnings (XML and CAP formats)
  - Customizable alert types (Severe Thunderstorm, Flood, Fire Weather, Cyclone, etc.)
  - Automatic Home Assistant notifications
  - Location-based filtering (default: Townsville and surrounds)
  - Only processes Queensland warnings (IDQ prefix)

- **EOC Status Monitoring**
  - Monitor multiple EOC websites for status changes
  - Detect activation keywords and status updates
  - CSS selector support for targeted content monitoring
  - Change detection using content hashing

- **Automated Routine Activation**
  - Trigger Home Assistant scenes and scripts based on alerts
  - Separate routines for different alert types:
    - Tornado warnings
    - Severe weather
    - EOC activation
  - Customizable automation workflows

- **Web Dashboard**
  - Real-time alert status display
  - Visual indicators for active alerts
  - EOC activation status tracking
  - Auto-refresh every 30 seconds

## Installation

### Home Assistant Add-on Store

1. Navigate to **Supervisor** → **Add-on Store**
2. Click the **⋮** menu → **Repositories**
3. Add this repository URL: `https://github.com/yourusername/forewarned`
4. Find "Forewarned" in the add-on list
5. Click **Install**

### Manual Installation

1. Copy the `forewarned` folder to `/addons/` on your Home Assistant instance
2. Restart Home Assistant
3. Navigate to **Supervisor** → **Add-on Store**
4. Refresh the page
5. Install "Forewarned"

## Configuration

### Basic Setup

```yaml
check_interval: 300  # Check interval in seconds (default: 5 minutes)
location: "Townsville"  # Location to filter warnings for
alert_entities: []   # Home Assistant entities to monitor
eoc_urls: []         # EOC websites to monitor
```

### Advanced Configuration

```yaml
check_interval: 180

# Location to monitor (filters warnings for this area)
location: "Townsville"

# EOC URLs with CSS selectors for targeted monitoring
eoc_urls:
  - url: "https://county-eoc.example.com/status"
    selectors:
      status: ".eoc-status"
      level: "#activation-level"
  - url: "https://emergency.city.gov"

# Home Assistant routines (scenes/scripts to activate)
routines:
  tornado_warning:
    - script.close_all_blinds
    - scene.basement_lights
  severe_weather:
    - script.secure_outdoor_items
    - scene.all_lights_on
  eoc_activated:
    - script.emergency_prep
    - scene.communication_mode
```

## Home Assistant Integration

Forewarned creates the following entities in Home Assistant:

### Binary Sensors

- `binary_sensor.forewarned_weather_alert` - Weather alert status
  - Attributes: `alert_count`, `alerts`, `last_check`
  
- `binary_sensor.forewarned_eoc_active` - EOC activation status
  - Attributes: `monitored_sites`, `activated_sites`, `sites`, `last_check`

- `binary_sensor.forewarned_local_alert` - Combined alert state (see [LOCAL_ALERT_STATE.md](LOCAL_ALERT_STATE.md))
  - Attributes: `alert_level`, `reason`, `triggered_by`, `timestamp`

### Manual Override Switches (Optional)

You can add input_boolean switches to manually activate alert levels for testing or manual activations. See [MANUAL_SWITCHES.md](MANUAL_SWITCHES.md) for setup instructions.

```yaml
input_boolean:
  forewarned_manual_advisory:
    name: "Forewarned Manual Advisory"
  forewarned_manual_watch:
    name: "Forewarned Manual Watch"
  forewarned_manual_warning:
    name: "Forewarned Manual Warning"
  forewarned_manual_emergency:
    name: "Forewarned Manual Emergency"
```

### Services

Use these entities in your automations:

```yaml
automation:
  - alias: "Notify on Weather Alert"
    trigger:
      platform: state
      entity_id: binary_sensor.forewarned_weather_alert
      to: "on"
    action:
      service: notify.mobile_app
      data:
        message: "Weather alert active!"
```

## API Endpoints

The web interface exposes REST API endpoints:

- `GET /api/status` - Overall status
- `GET /api/weather` - Weather alerts
- `GET /api/eoc` - EOC states
- `GET /health` - Health check

## Development

### Project Structure

```
forewarned/
├── src/
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── weather_monitor.py  # Weather alert monitoring
│   ├── eoc_monitor.py      # EOC website monitoring
│   ├── ha_integration.py   # Home Assistant API client
│   └── web_ui.py           # Flask web interface
├── templates/
│   └── index.html          # Dashboard HTML
├── static/
│   ├── style.css           # Dashboard styles
│   └── script.js           # Dashboard JavaScript
├── config.json             # Addon configuration
├── Dockerfile              # Container build
├── requirements.txt        # Python dependencies
├── run.sh                  # Startup script
└── main.py                 # Application entry point
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SUPERVISOR_TOKEN="your-token"
export WEATHER_API_KEY="your-api-key"

# Run the application
python main.py
```

The web interface will be available at `http://localhost:5000`

## Supported Alert Types

Default monitored weather warnings from BOM:
- Severe Thunderstorm Warning
- Severe Weather Warning
- Flood Warning
- Fire Weather Warning
- Tropical Cyclone Warning
- Tsunami Warning

Customize in configuration to add more types. The system monitors warnings in XML and CAP formats from `ftp://ftp.bom.gov.au/anon/gen/fwo/`.

## EOC Monitoring

The EOC monitor detects activation based on keywords:
- "activated"
- "active"
- "level 1/2/3"
- "emergency operations"
- "eoc active"

Content changes trigger notifications even without these keywords.

## Troubleshooting

### No Weather Alerts Appearing

1. Check NWS API availability: `https://api.weather.gov/alerts/active`
2. Verify internet connectivity
3. Check logs for API errors

### EOC Monitor Not Detecting Changes

1. Verify URL is accessible
2. Test CSS selectors with browser DevTools
3. Check for anti-scraping measures (rate limiting, captchas)

### Home Assistant Integration Not Working

1. Verify `SUPERVISOR_TOKEN` is set
2. Check addon has `homeassistant_api: true` in config
3. Review logs for API call failures

## License

MIT License - See LICENSE file for details

## Support

For issues and feature requests, please use the GitHub issue tracker.

## Credits

Built with:
- Flask - Web framework
- BeautifulSoup4 - HTML parsing
- aiohttp - Async HTTP client
- National Weather Service API
