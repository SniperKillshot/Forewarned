# Forewarned - Project Instructions

## Project Overview
Forewarned is a Home Assistant addon for weather alerting and Emergency Operations Center (EOC) state monitoring. It automatically activates Home Assistant routines based on weather conditions and EOC activations.

## Technology Stack
- **Language:** Python 3
- **Framework:** Flask (web UI)
- **Libraries:** aioftp (async FTP), lxml (XML parsing), BeautifulSoup4 (HTML parsing)
- **Platform:** Home Assistant Addon (Docker-based)
- **Data Sources:** Australian BOM FTP (ftp://ftp.bom.gov.au/anon/gen/fwo/), Home Assistant Supervisor API

## Key Features
1. **Weather Monitoring** - Australian Bureau of Meteorology (BOM) warnings via FTP (XML/CAP formats)
2. **EOC Monitoring** - Website change detection with CSS selector support
3. **Home Assistant Integration** - Binary sensors, service calls, scenes/scripts
4. **Web Dashboard** - Real-time status display with auto-refresh
5. **Automated Routines** - Trigger scenes/scripts based on alert types
6. **Location Filtering** - Monitors Queensland (IDQ prefix) and filters for Townsville area specifically

## Development Guidelines
- Follow async/await patterns for I/O operations
- Use logging extensively for debugging
- Keep configuration flexible via config.json and environment variables
- Maintain Home Assistant addon best practices
- Use semantic versioning for releases

## Project Structure
```
forewarned/
├── src/               # Python modules
├── templates/         # Flask HTML templates
├── static/            # CSS/JS assets
├── config.json        # HA addon config
├── Dockerfile         # Container build
├── main.py            # Entry point
└── requirements.txt   # Dependencies
```

## Home Assistant Integration
- Creates binary sensors for weather and EOC status
- Uses Supervisor API for service calls
- Supports ingress for embedded web UI
- Configurable via addon options
