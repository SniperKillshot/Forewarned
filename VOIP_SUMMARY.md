# VOIP Integration - Implementation Summary

## What's Been Added

Forewarned now has comprehensive VOIP phone system integration that allows you to:

1. **Receive alert calls on your phone** - When alert levels are reached, Forewarned can call configured extensions
   - Example: Emergency alert → calls your bedside phone to wake you up
   - Example: Warning alert → calls your office phone

2. **Check alert status by phone** - Dial an extension and hear the current alert level
   - Example: Dial *411 to hear "Current alert level is WARNING. Severe thunderstorm approaching."

## Files Created/Modified

### New Files

1. **`src/voip_integration.py`** (434 lines)
   - `VOIPIntegration` class - Main VOIP integration logic
   - `VOIPWebhookHandler` class - Flask webhook endpoints
   - Supports multiple backends:
     * Asterisk/FreePBX (via AMI webhook)
     * Twilio (via REST API)
     * Home Assistant notify services
     * Future: Direct SIP/PJSUA2

2. **`VOIP_INTEGRATION.md`** (425 lines)
   - Complete technical documentation
   - Asterisk/FreePBX setup guide
   - Twilio configuration
   - Dialplan examples
   - AGI script examples
   - Troubleshooting guide

3. **`VOIP_QUICKSTART.md`** (240 lines)
   - Quick setup guide for Asterisk/FreePBX
   - Configuration examples
   - Testing instructions
   - Common use cases

4. **`VOIP_SUMMARY.md`** (this file)
   - Implementation overview
   - Usage instructions
   - Next steps

### Modified Files

1. **`src/local_alert_manager.py`**
   - Added `voip_integration` parameter to constructor
   - Added `_make_voip_calls()` method to trigger phone calls
   - Calls VOIP after HA notification in `_trigger_routines()`
   - Reads extension lists from `config['alert_calls']`

2. **`src/web_ui.py`**
   - Added VOIP webhook endpoints:
     * `GET/POST /voip/status` - JSON status with TTS message
     * `GET/POST /voip/twiml` - Twilio inbound call handler
     * `POST /voip/menu` - Twilio menu (press 1 to repeat, 2 to hang up)
     * `GET /voip/agi` - Asterisk AGI script
     * `POST /api/voip/test-call` - Manual test call trigger
   - Added `app.voip_integration` reference

3. **`main.py`**
   - Imports `VOIPIntegration`
   - Initializes VOIP if `config['voip']['enabled'] = true`
   - Passes VOIP integration to `LocalAlertManager`
   - Stores reference in `app_state['voip_integration']`

4. **`config_data.json`**
   - Added VOIP configuration section with example:
     ```json
     "voip": {
       "enabled": false,
       "backend": "webhook",
       "webhook_url": "http://asterisk-ip:5038/ami",
       "webhook_auth": {...},
       "alert_calls": {
         "emergency": ["100", "bedside"],
         "warning": ["100"],
         "watch": [],
         "advisory": []
       }
     }
     ```

## How It Works

### Outbound Calls (Alerts)

1. Alert level changes (e.g., emergency)
2. `LocalAlertManager._trigger_routines()` is called
3. Checks `config['alert_calls']['emergency']` for extension list
4. For each extension, calls `voip_integration.make_alert_call()`
5. VOIP backend initiates call:
   - **Asterisk**: HTTP POST to AMI with Originate action
   - **Twilio**: HTTP POST to Twilio API
   - **HA Notify**: Calls HA service
6. Phone rings, user answers
7. Asterisk connects to dialplan context `forewarned-alerts`
8. Text-to-speech plays: "EMERGENCY ALERT. Severe thunderstorm approaching. This is an emergency. Take immediate action."

### Inbound Calls (Status Checks)

1. User dials *411 (or configured extension)
2. Asterisk matches dialplan extension
3. Asterisk makes HTTP GET to `http://forewarned:5000/voip/status`
4. Forewarned returns JSON with current alert level and TTS message
5. Asterisk plays message via SayText()
6. User hangs up

## Configuration

### Enable VOIP

Edit `config_data.json`:

```json
"voip": {
  "enabled": true,
  "backend": "webhook",
  "webhook_url": "http://192.168.1.100:5038/ami",
  "webhook_auth": {
    "username": "forewarned",
    "secret": "your-secret-password"
  },
  "alert_calls": {
    "emergency": ["100", "bedside"],
    "warning": ["100"],
    "watch": [],
    "advisory": []
  }
}
```

### Extension Mappings

- **emergency**: High-priority calls (wake you up)
  - Example: `["100", "bedside", "mobile"]`
  - Calls all three when emergency level reached

- **warning**: Important but not critical
  - Example: `["100"]`
  - Calls office phone only

- **watch**: Monitor conditions
  - Example: `[]`
  - No automatic calls

- **advisory**: Informational
  - Example: `[]`
  - No automatic calls

## Testing

### Test VOIP Status Endpoint

```bash
curl http://localhost:5000/voip/status
```

Expected response:
```json
{
  "active": true,
  "level": "advisory",
  "reason": "Flood Watch",
  "message": "Current alert level is ADVISORY. Flood Watch. This is an advisory. Be aware of conditions."
}
```

### Test Call Manually

```bash
curl -X POST http://localhost:5000/api/voip/test-call \
  -H "Content-Type: application/json" \
  -d '{
    "extension": "100",
    "alert_level": "emergency",
    "reason": "Test emergency call"
  }'
```

### Test via Manual Switch

In Home Assistant:
```yaml
service: input_boolean.turn_on
target:
  entity_id: input_boolean.forewarned_manual_emergency
```

This will:
1. Activate emergency alert level
2. Trigger Home Assistant routines
3. **Call all extensions in `alert_calls.emergency`**
4. Update binary sensors

## Next Steps

### 1. Configure Asterisk (Required for Outbound Calls)

See **VOIP_QUICKSTART.md** for detailed setup:
- Configure AMI in `/etc/asterisk/manager.conf`
- Create dialplan in `/etc/asterisk/extensions.conf`
- Reload Asterisk: `asterisk -rx "manager reload"`

### 2. Test Outbound Calls

- Enable VOIP in config (`"enabled": true`)
- Restart Forewarned
- Trigger alert (manual switch or real weather alert)
- Verify phone rings

### 3. Add Status Check Extension (Optional)

Add to your dialplan:
```ini
[from-internal]
exten => *411,1,NoOp(Forewarned Status)
 same => n,Answer()
 same => n,Set(STATUS=${CURL(http://forewarned-ip:5000/voip/status)})
 same => n,Set(MSG=${JSON_DECODE(${STATUS},message)})
 same => n,SayText(${MSG})
 same => n,Hangup()
```

### 4. Security Hardening

- Restrict AMI to specific IP ranges in `manager.conf`
- Use strong passwords
- Consider HTTPS for webhook calls
- Run on isolated VLAN if possible

### 5. Advanced Features (Future)

- **Call acknowledgment** - Press 1 to acknowledge alert
- **Call retry logic** - Retry if no answer
- **Escalation chains** - Call A, then B if no answer
- **Multi-language support** - TTS in different languages
- **Custom audio files** - Use recordings instead of TTS
- **SIP direct dialing** - Use PJSUA2 for direct SIP calls

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Alert Trigger (Weather/EOC/Manual Switch)                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      v
┌─────────────────────────────────────────────────────────────┐
│ LocalAlertManager.evaluate_alert_state()                    │
│  ├─ Check manual overrides (input_boolean)                  │
│  ├─ Check weather conditions                                │
│  ├─ Check EOC states                                        │
│  └─ Determine alert level (emergency/warning/watch/advisory)│
└─────────────────────┬───────────────────────────────────────┘
                      │
                      v
┌─────────────────────────────────────────────────────────────┐
│ LocalAlertManager._trigger_routines()                       │
│  ├─ Update Home Assistant binary sensor                     │
│  ├─ Call HA routines/automations                            │
│  └─ Call _make_voip_calls() ◄─── NEW                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      v
┌─────────────────────────────────────────────────────────────┐
│ LocalAlertManager._make_voip_calls()                        │
│  ├─ Get extensions from config['alert_calls'][level]        │
│  └─ For each extension:                                     │
│      └─ voip_integration.make_alert_call(ext, level, reason)│
└─────────────────────┬───────────────────────────────────────┘
                      │
                      v
┌─────────────────────────────────────────────────────────────┐
│ VOIPIntegration.make_alert_call()                           │
│  ├─ webhook backend: HTTP POST to Asterisk AMI              │
│  ├─ twilio backend: HTTP POST to Twilio API                 │
│  └─ ha_notify backend: Call HA notify service               │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      v
┌─────────────────────────────────────────────────────────────┐
│ Asterisk PBX                                                │
│  ├─ Receives AMI Originate command                          │
│  ├─ Dials extension (e.g., PJSIP/100)                       │
│  ├─ Connects to dialplan [forewarned-alerts]                │
│  ├─ Plays alert message via SayText()                       │
│  └─ Hangs up after message                                  │
└─────────────────────────────────────────────────────────────┘
                      │
                      v
                 ┌─────────┐
                 │  Phone  │ ← User answers
                 │ Extension│    "EMERGENCY ALERT..."
                 └─────────┘
```

## Support

For issues, questions, or feature requests:
- Check **VOIP_INTEGRATION.md** for detailed documentation
- Check **VOIP_QUICKSTART.md** for setup guide
- Review Asterisk logs: `asterisk -rvvv`
- Check Forewarned logs for VOIP errors

## License

Same as Forewarned project (see main README.md)
