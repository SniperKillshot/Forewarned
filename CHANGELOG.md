# Changelog

## [1.0.6] - 2025-12-27

### Added
- Individual alert level entities for Home Assistant
  - `binary_sensor.forewarned_alert_advisory`
  - `binary_sensor.forewarned_alert_watch`
  - `binary_sensor.forewarned_alert_warning`
  - `binary_sensor.forewarned_alert_emergency`
  - `sensor.forewarned_alert_level` (text sensor)
- All entities include reason, triggered_by, and timestamp attributes

## [1.0.5] - 2025-12-27

### Fixed
- Ingress path handling for static files (CSS/JS)
- Custom middleware to properly handle X-Ingress-Path header
- Static files now load correctly in Home Assistant ingress panel

## [1.0.4] - 2025-12-27

### Fixed
- Async event loop error when running FTP in thread pool
- FTP thread now returns data to async context properly
- Added favicon handler to prevent 404 errors

## [1.0.3] - 2025-12-27

### Added
- ProxyFix middleware for Home Assistant ingress compatibility

### Fixed
- Ingress CSS and static file loading issues

## [1.0.2] - 2025-12-26

### Changed
- Replaced aioftp with Python stdlib ftplib for BOM FTP access
- FTP operations run in thread pool via asyncio.to_thread()
- No external pip packages needed for FTP functionality

### Fixed
- Multiple syntax errors and duplicate function definitions
- Docker build issues with PEP 668 restrictions

## [1.0.1] - 2025-12-26

### Changed
- Replaced FTP with HTTP for BOM warnings (switched to aiohttp)
- Changed from aioftp to aiohttp for weather data fetching
- Using only Alpine apk packages (no pip dependencies)

### Fixed
- Docker build failures on Alpine Linux
- PEP 668 externally-managed environment issues
- Ingress compatibility for web UI
- Used Flask url_for() for all paths

### Removed
- pjsua2 dependency (optional VoIP, not available in Alpine)
- All pip-only packages replaced with apk equivalents

## [1.0.0] - 2025-11-26

### Added
- Initial release
- Bureau of Meteorology (BOM) alert monitoring for Queensland
- EOC website monitoring with change detection
- Home Assistant integration with binary sensors
- Web dashboard for real-time status
- Automated routine activation (scenes/scripts)
- Configurable alert types and check intervals
- CSS selector support for targeted EOC monitoring
- REST API endpoints for external integration
- Docker container support
- Home Assistant addon configuration

### Features
- Real-time weather alert notifications
- EOC activation detection
- Customizable automation workflows
- Auto-refresh dashboard (30s interval)
- Mobile-responsive web interface
- Severity-based alert styling
- Content hash-based change detection
