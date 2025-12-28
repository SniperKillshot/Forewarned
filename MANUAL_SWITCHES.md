# Manual Alert Level Switches

Forewarned supports manual override switches that allow you to manually activate alert levels regardless of weather or EOC conditions. This is useful for testing, drills, or other manual activations.

## Important: Creating Switches with Unique IDs

**Note:** Switches created via the REST API cannot have unique IDs. To create switches that are manageable through the Home Assistant UI, you must create them manually.

### Method 1: Using Home Assistant UI (Recommended)

1. Go to **Settings** > **Devices & Services** > **Helpers**
2. Click **+ CREATE HELPER**
3. Select **Toggle**
4. Create each switch with these exact entity IDs:

   - **Entity ID:** `switch.forewarned_manual_advisory` (or `input_boolean.forewarned_manual_advisory`)
   - **Entity ID:** `switch.forewarned_manual_watch` (or `input_boolean.forewarned_manual_watch`)
   - **Entity ID:** `switch.forewarned_manual_warning` (or `input_boolean.forewarned_manual_warning`)
   - **Entity ID:** `switch.forewarned_manual_emergency` (or `input_boolean.forewarned_manual_emergency`)

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

- Manual overrides are checked on every evaluation cycle (typically every 5 minutes when weather/EOC states update)
- If a manual switch is active, automatic alert evaluation is completely bypassed
- Manual overrides do NOT persist through Home Assistant restarts unless you enable `initial: true` in the input_boolean configuration
- Clear routines will NOT be triggered when turning off a manual switch - only when the alert state changes from active to inactive
