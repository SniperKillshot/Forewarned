# Manual Alert Level Switches

Forewarned supports manual override switches that allow you to manually activate alert levels regardless of weather or EOC conditions. This is useful for testing, drills, or other manual activations.

## MQTT vs. No MQTT: Which Entities You Get

- **MQTT enabled (recommended):** Forewarned creates and manages the switches for
  you automatically via MQTT discovery, as `switch.forewarned_manual_advisory`,
  `switch.forewarned_manual_watch`, `switch.forewarned_manual_warning`, and
  `switch.forewarned_manual_emergency`. You don't need to create anything - skip
  to [How It Works](#how-it-works). Toggles also take effect immediately.
- **MQTT disabled:** Forewarned cannot create a real, toggleable switch through
  the plain REST API, so you must create `input_boolean` helpers yourself (below).
  Overrides are picked up on the next periodic check (up to `check_interval`,
  5 minutes by default) rather than instantly.

The examples below use `input_boolean.*` for the no-MQTT case. If you have MQTT
enabled, use the `switch.forewarned_manual_*` entities instead in your own
dashboards/automations.

## Creating the input_boolean Helpers (No MQTT)

### Method 1: Using Home Assistant UI (Recommended)

1. Go to **Settings** > **Devices & Services** > **Helpers**
2. Click **+ CREATE HELPER**
3. Select **Toggle**
4. Create each switch with these exact entity IDs:

   - **Entity ID:** `input_boolean.forewarned_manual_advisory`
   - **Entity ID:** `input_boolean.forewarned_manual_watch`
   - **Entity ID:** `input_boolean.forewarned_manual_warning`
   - **Entity ID:** `input_boolean.forewarned_manual_emergency`

### Method 2: Using configuration.yaml

Add the following to your Home Assistant `configuration.yaml`:

```yaml
input_boolean:
  forewarned_manual_advisory:
    name: "Forewarned Manual Advisory"
    icon: mdi:alert-circle-outline
    
  forewarned_manual_watch:
    name: "Forewarned Manual Watch"
    icon: mdi:alert
    
  forewarned_manual_warning:
    name: "Forewarned Manual Warning"
    icon: mdi:alert-octagon
    
  forewarned_manual_emergency:
    name: "Forewarned Manual Emergency"
    icon: mdi:alert-octagram
```

After adding these, restart Home Assistant or reload input_boolean entities.

## How It Works

1. **Priority**: Manual overrides have the **highest priority**. If any manual switch is on, it will override automatic alert evaluation.

2. **Level Priority**: If multiple manual switches are on, the highest level wins:
   - Emergency (highest)
   - Warning
   - Watch
   - Advisory (lowest)

3. **Triggering Routines**: Manual overrides will trigger the same Home Assistant scenes/scripts configured for that alert level.

4. **Sensor Updates**: The `binary_sensor.forewarned_local_alert` will update to show:
   - `alert_level`: The manually activated level
   - `reason`: "Manual override: [LEVEL]"
   - `triggered_by`: ["Manual override: [LEVEL]"]

## Usage Examples

### Testing Alert Levels

Use manual switches to test your alert routines without waiting for real alerts:

```yaml
automation:
  - alias: "Test Emergency Alert"
    trigger:
      - platform: state
        entity_id: input_boolean.forewarned_manual_emergency
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "Emergency alert routine activated!"
```

### Temporary Manual Activation

Create an automation to automatically turn off manual switches after a period:

```yaml
automation:
  - alias: "Auto-disable Manual Warning"
    trigger:
      - platform: state
        entity_id: input_boolean.forewarned_manual_warning
        to: "on"
        for:
          hours: 1
    action:
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.forewarned_manual_warning
```

### Dashboard Controls

Add to your Lovelace dashboard for quick access:

```yaml
type: entities
title: Forewarned Manual Controls
entities:
  - entity: input_boolean.forewarned_manual_advisory
  - entity: input_boolean.forewarned_manual_watch
  - entity: input_boolean.forewarned_manual_warning
  - entity: input_boolean.forewarned_manual_emergency
  - type: divider
  - entity: binary_sensor.forewarned_local_alert
    secondary_info: last-changed
```

### Combined Manual Button Card

Using `button-card` custom component:

```yaml
type: custom:button-card
entity: binary_sensor.forewarned_local_alert
name: Alert Level
show_state: true
state:
  - value: "on"
    color: red
    icon: mdi:alert-octagon
  - value: "off"
    color: green
    icon: mdi:check-circle
tap_action:
  action: more-info
hold_action:
  action: call-service
  service: input_boolean.toggle
  service_data:
    entity_id: input_boolean.forewarned_manual_warning
```

## Deactivation

To return to automatic alert evaluation, simply turn off all manual switches:

```yaml
service: input_boolean.turn_off
target:
  entity_id:
    - input_boolean.forewarned_manual_advisory
    - input_boolean.forewarned_manual_watch
    - input_boolean.forewarned_manual_warning
    - input_boolean.forewarned_manual_emergency
```

## Integration with Automations

### Only Allow Manual During Business Hours

```yaml
automation:
  - alias: "Block Manual Alerts Outside Hours"
    trigger:
      - platform: state
        entity_id:
          - input_boolean.forewarned_manual_advisory
          - input_boolean.forewarned_manual_watch
          - input_boolean.forewarned_manual_warning
          - input_boolean.forewarned_manual_emergency
        to: "on"
    condition:
      - condition: time
        after: "17:00:00"
        before: "08:00:00"
    action:
      - service: input_boolean.turn_off
        target:
          entity_id: "{{ trigger.entity_id }}"
      - service: notify.admin
        data:
          message: "Manual alert activation blocked outside business hours"
```

### Require Confirmation

```yaml
script:
  activate_emergency_alert:
    sequence:
      - service: input_boolean.turn_on
        target:
          entity_id: input_boolean.forewarned_manual_emergency
      - delay:
          seconds: 5
      - condition: state
        entity_id: input_boolean.forewarned_manual_emergency_confirm
        state: "on"
      - service: notify.all
        data:
          message: "EMERGENCY ALERT ACTIVATED - This is not a drill"
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.forewarned_manual_emergency_confirm
```

## Monitoring

Track manual override usage:

```yaml
sensor:
  - platform: history_stats
    name: Manual Overrides Today
    entity_id: binary_sensor.forewarned_local_alert
    state: "on"
    type: count
    start: "{{ now().replace(hour=0, minute=0, second=0) }}"
    end: "{{ now() }}"
```

## Notes

- With MQTT enabled, a manual switch toggle is picked up and evaluated immediately.
  Without MQTT, overrides are only checked on the next periodic evaluation cycle
  (typically every 5 minutes, per `check_interval`)
- If a manual switch is active, automatic alert evaluation is completely bypassed
- Manual overrides do NOT persist through Home Assistant restarts unless you enable `initial: true` in the input_boolean configuration
- Turning off the last active manual switch falls through to automatic evaluation.
  If that comes back inactive, the clear/all-clear routine (`alert_cleared`) WILL
  fire, same as any other active-to-inactive transition
