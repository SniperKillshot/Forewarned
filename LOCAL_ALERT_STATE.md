# Local Alert State System

## Overview
The Local Alert State system provides a unified alert level that triggers Home Assistant routines. Instead of reacting to individual weather alerts or EOC state changes, this system evaluates all active conditions and determines a single alert level that drives all automations.

## Alert Levels

The system uses five alert levels with increasing severity:

1. **none** (0) - No active alerts
2. **advisory** (1) - Minor alerts, informational only
3. **watch** (2) - Moderate alerts, prepare for potential action
4. **warning** (3) - Severe alerts, take protective action
5. **emergency** (4) - Extreme alerts, immediate action required

## How It Works

### 1. Evaluation Process
The system continuously monitors:
- **Weather Alerts** from BOM (Bureau of Meteorology)
- **LDMG States** (Local Disaster Management Group)

When either source updates, the Local Alert Manager evaluates all conditions and determines the highest applicable alert level.

### 2. Alert Level Mapping

**Weather Severity → Alert Level:**
- Minor → Advisory
- Moderate → Watch
- Severe → Warning
- Extreme → Emergency

**LDMG State → Alert Level:**
- Alert → Advisory
- Lean Forward → Watch
- Stand Up → Emergency
- Stand Down → Advisory
- Inactive → None

### 3. Home Assistant Integration

The system creates a binary sensor in Home Assistant:
```
binary_sensor.forewarned_local_alert
```

**Attributes:**
- `alert_level`: Current level (none/advisory/watch/warning/emergency)
- `reason`: Human-readable explanation
- `triggered_by`: List of conditions causing the alert
- `timestamp`: When the state last changed

### 4. Triggering Routines

Configure routines in your Home Assistant addon options:

```json
{
  "routines": {
    "advisory_alert": ["scene.weather_advisory", "script.notify_family"],
    "watch_alert": ["scene.weather_watch", "script.close_blinds"],
    "warning_alert": ["scene.severe_weather", "script.emergency_lights"],
    "emergency_alert": ["scene.emergency_mode", "script.sound_alarm"],
    "alert_cleared": ["scene.normal_mode", "script.all_clear_notification"]
  }
}
```

**Routine Types:**
- Scenes: `scene.entity_id`
- Scripts: `script.entity_id`

### 5. API Endpoints

**Get Local Alert State:**
```
GET /api/local_alert
```

Returns:
```json
{
  "active": true,
  "level": "warning",
  "reason": "Severe Thunderstorm Warning (severe), LDMG lean forward",
  "timestamp": "2025-11-26T12:00:00",
  "triggered_by": [
    "Weather: Severe Thunderstorm Warning",
    "LDMG: LEAN FORWARD"
  ]
}
```

**Get All Status (includes local alert):**
```
GET /api/status
```

Returns weather alerts, EOC states, and local alert state.

## Automation Examples

### Example 1: Basic Alert Response
```yaml
automation:
  - alias: "Forewarned Alert Level Changed"
    trigger:
      - platform: state
        entity_id: binary_sensor.forewarned_local_alert
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state == 'on' }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Weather Alert: {{ state_attr('binary_sensor.forewarned_local_alert', 'alert_level') }}"
          message: "{{ state_attr('binary_sensor.forewarned_local_alert', 'reason') }}"
```

### Example 2: Emergency Level Response
```yaml
automation:
  - alias: "Emergency Alert Actions"
    trigger:
      - platform: state
        entity_id: binary_sensor.forewarned_local_alert
        attribute: alert_level
        to: 'emergency'
    action:
      - service: light.turn_on
        target:
          entity_id: all
        data:
          color_name: red
          brightness: 255
      - service: media_player.play_media
        target:
          entity_id: media_player.all_speakers
        data:
          media_content_id: "alert_emergency.mp3"
          media_content_type: "music"
```

### Example 3: All Clear Notification
```yaml
automation:
  - alias: "All Clear Notification"
    trigger:
      - platform: state
        entity_id: binary_sensor.forewarned_local_alert
        from: 'on'
        to: 'off'
    action:
      - service: notify.all_devices
        data:
          title: "All Clear"
          message: "Weather alerts have been cleared"
      - service: scene.turn_on
        target:
          entity_id: scene.normal_mode
```

## Benefits

1. **Unified Control**: One alert level instead of managing multiple individual alerts
2. **Priority-Based**: Automatically uses the highest severity level
3. **Flexible Mapping**: Customize how weather/LDMG conditions map to alert levels
4. **State Tracking**: Know exactly what triggered the current alert level
5. **Home Assistant Native**: Works seamlessly with HA automations

## Configuration

The system is configured in the addon `config.json`:

```json
{
  "routines": {
    "advisory_alert": [],
    "watch_alert": [],
    "warning_alert": [],
    "emergency_alert": [],
    "alert_cleared": []
  }
}
```

Add scenes or scripts to trigger at each alert level. The system will:
1. Evaluate all conditions
2. Determine the alert level
3. Update the HA sensor
4. Execute the appropriate routines
5. Send notifications

## Dashboard Integration

The local alert state is displayed on the Forewarned web dashboard and available via API for custom integrations.
