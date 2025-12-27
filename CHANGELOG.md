# Changelog

## [1.0.20] - 2025-12-27

### Added
- Debug logging shows first 500 chars of page content
- Log which keywords are found during state detection
- Log when no EOC keywords found (inactive state)

### Fixed
- Better visibility into why EOC state detection returns inactive
- Helps diagnose keyword matching issues with LDMG website

## [1.0.19] - 2025-12-27

### Fixed
- EOC states now stored on first check, not only on changes
- LDMG status now appears immediately instead of waiting for site change
- Added detailed logging for EOC site checks and state detection
- Log shows detected state, page size, and state changes

### Changed
- EOC state detection happens on every check, not just changes
- eoc_states dictionary populated immediately on first check

## [1.0.18] - 2025-12-27

### Fixed
- Changed from espeak-ng to espeak (available in Alpine stable)
- Removed espeak-ng fallback logic
- TTS now uses standard espeak package

## [1.0.17] - 2025-12-27

### Fixed
- Added debug logging for EOC state updates to shared_state
- Log number of EOC sites and current state when updating
- Added debug log to /api/status endpoint
- Helps diagnose LDMG status not updating issues

## [1.0.16] - 2025-12-27

### Fixed
- Added debug logging for VoIP configuration loading
- Log voip_enabled and voip_alert_numbers from options.json
- Helps diagnose configuration persistence issues

## [1.0.15] - 2025-12-27

### Added
- Custom AlertCall class with TTS playback support
- Custom AlertAccount class to auto-answer incoming calls
- TTS message generation using espeak-ng
- WAV file playback to SIP calls via AudioMediaPlayer
- Automatic incoming call handling with alert status announcement
- Call state and media state callbacks
- espeak-ng TTS engine in Docker image

### Changed
- Outbound calls now play TTS message when answered
- Inbound calls automatically answered and play current alert status
- Full duplex audio support for calls

## [1.0.14] - 2025-12-27

### Fixed
- VoIP calls now use voip_alert_numbers from config
- All configured numbers called for any alert level
- Simplified alert calling logic to match config structure

## [1.0.13] - 2025-12-27

### Added
- Full PJSUA2 SIP registration implementation
- SIP endpoint initialization with UDP transport
- Account registration with digest authentication
- Outbound SIP call capability
- Proper SIP cleanup/shutdown on addon stop
- SIP message trace logging (level 5 verbosity)
- Console logging of all SIP packets for debugging

### Fixed
- VoIP configuration now properly loaded from addon options
- Flat voip_* fields transformed into nested config structure
- SIP backend now actually registers with PBX

## [1.0.12] - 2025-12-27

### Added
- VoIP configuration options in addon config page
- Support for webhook backend (Asterisk/FreePBX)
- Support for SIP backend (direct calling)
- Support for Home Assistant notify service backend
- Authentication options (none, basic, bearer token)
- Configurable alert phone numbers

## [1.0.11] - 2025-12-27

### Fixed
- Package version conflicts by installing only py3-pjsua from edge repository
- lxml symbol errors caused by mixed stable/edge package versions
- Dockerfile now uses --repository flag for targeted edge package installation

## [1.0.10] - 2025-12-27

### Fixed
- API calls in JavaScript now use relative paths for ingress compatibility
- Dashboard and config page now load data correctly through Home Assistant ingress

## [1.0.9] - 2025-12-27

### Added
- Alpine edge repository for access to py3-pjsua package
- py3-pjsua package installed for VoIP integration support
- VoIP calling capabilities now available (requires configuration)

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
