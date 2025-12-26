# VOIP Integration - Quick Start Guide

## Overview
Forewarned now supports VOIP phone system integration, allowing you to:
1. **Receive alert calls** - Get called on specific extensions when alert levels are reached (e.g., emergency alert calls your bedside phone)
2. **Check status by phone** - Dial an extension to hear the current alert level

## Quick Setup (Asterisk/FreePBX)

### 1. Enable VOIP in Configuration

Edit your `config_data.json` (or `/data/options.json` in Home Assistant):

```json
{
  "voip": {
    "enabled": true,
    "backend": "webhook",
    "webhook_url": "http://your-asterisk-ip:5038/ami",
    "webhook_auth": {
      "username": "forewarned",
      "secret": "your-secret-here"
    },
    "webhook_payload_template": {
      "Action": "Originate",
      "Channel": "PJSIP/{extension}",
      "Context": "forewarned-alerts",
      "Exten": "s",
      "Priority": "1",
      "CallerID": "Forewarned Alert <1000>",
      "Timeout": "30000",
      "Variable": ["ALERT_LEVEL={alert_level}", "ALERT_REASON={reason}"]
    },
    "alert_calls": {
      "emergency": ["100", "bedside"],
      "warning": ["100"],
      "watch": [],
      "advisory": []
    }
  }
}
```

### 2. Configure Asterisk Manager Interface (AMI)

**For FreePBX users:** Edit `/etc/asterisk/manager_custom.conf` (this won't be overwritten):

```ini
[forewarned]
secret = your-secret-here
deny = 0.0.0.0/0.0.0.0
permit = 192.168.1.0/255.255.255.0  ; Your Forewarned server IP range
read = system,call,log,verbose,command,agent,user,config,originate
write = system,call,log,verbose,command,agent,user,config,originate
```

**For vanilla Asterisk users:** Edit `/etc/asterisk/manager.conf`:

```ini
[general]
enabled = yes
port = 5038
bindaddr = 0.0.0.0

[forewarned]
secret = your-secret-here
deny = 0.0.0.0/0.0.0.0
permit = 192.168.1.0/255.255.255.0  ; Your Forewarned server IP range
read = system,call,log,verbose,command,agent,user,config,originate
write = system,call,log,verbose,command,agent,user,config,originate
```

**Reload:** `sudo asterisk -rx "manager reload"`

**Note:** FreePBX already has AMI enabled by default, so you only need to add the `[forewarned]` user in `manager_custom.conf`.

### 3. Create Asterisk Dialplan Context

**For FreePBX users:** Edit `/etc/asterisk/extensions_custom.conf` (this won't be overwritten):

```ini
[forewarned-alerts]
; Called when alert triggered
exten => s,1,NoOp(Forewarned Alert - Level: ${ALERT_LEVEL})
 same => n,Set(CHANNEL(language)=en)
 same => n,Answer()
 same => n,Wait(1)
 same => n,GotoIf($["${ALERT_LEVEL}" = "emergency"]?emergency)
 same => n,GotoIf($["${ALERT_LEVEL}" = "warning"]?warning)
 same => n,GotoIf($["${ALERT_LEVEL}" = "watch"]?watch)
 same => n,GotoIf($["${ALERT_LEVEL}" = "advisory"]?advisory)
 same => n,Goto(default)

exten => s,n(emergency),Playback(alert)
 same => n,SayText(EMERGENCY ALERT. ${ALERT_REASON}. This is an emergency. Take immediate action.)
 same => n,Wait(2)
 same => n,Playback(alert)
 same => n,SayText(EMERGENCY ALERT. ${ALERT_REASON})
 same => n,Hangup()

exten => s,n(warning),Playback(attention)
 same => n,SayText(Warning alert. ${ALERT_REASON}. Take appropriate precautions.)
 same => n,Hangup()

exten => s,n(watch),SayText(Watch alert. ${ALERT_REASON}. Monitor conditions closely.)
 same => n,Hangup()

exten => s,n(advisory),SayText(Advisory alert. ${ALERT_REASON}. Be aware of conditions.)
 same => n,Hangup()

exten => s,n(default),SayText(Alert from Forewarned system. ${ALERT_REASON})
 same => n,Hangup()
```

**For vanilla Asterisk users:** Edit `/etc/asterisk/extensions.conf` and add the same context above.

**Reload:** `sudo asterisk -rx "dialplan reload"`

### 4. Add Status Check Extension (Optional)

**For FreePBX users:** Add to `/etc/asterisk/extensions_custom.conf`:

```ini
[from-internal-custom]
; Dial *411 to check Forewarned alert status
exten => *411,1,NoOp(Forewarned Status Check)
 same => n,Answer()
 same => n,Wait(1)
 same => n,Set(STATUS=${CURL(http://your-forewarned-ip:5000/voip/status)})
 same => n,Set(MESSAGE=${JSON_DECODE(${STATUS},message)})
 same => n,SayText(${MESSAGE})
 same => n,Hangup()
```

**For vanilla Asterisk users:** Add to your main dialplan context in `/etc/asterisk/extensions.conf`:

```ini
[from-internal]
; Dial *411 to check Forewarned alert status
exten => *411,1,NoOp(Forewarned Status Check)
 same => n,Answer()
 same => n,Wait(1)
 same => n,AGI(http://your-forewarned-ip:5000/voip/status)
 same => n,Hangup()
```

Or use a simpler HTTP-based approach:

```ini
exten => *411,1,NoOp(Forewarned Status Check)
 same => n,Answer()
 same => n,Wait(1)
 same => n,Set(STATUS=${CURL(http://your-forewarned-ip:5000/voip/status)})
 same => n,Set(MESSAGE=${JSON_DECODE(${STATUS},message)})
 same => n,SayText(${MESSAGE})
 same => n,Hangup()
```

**Note:** Replace `your-forewarned-ip` with your actual Forewarned server IP address.

### 5. Test the Integration

**Test outbound call manually:**
```bash
curl -X POST http://localhost:5000/api/voip/test-call \
  -H "Content-Type: application/json" \
  -d '{"extension": "100", "alert_level": "warning", "reason": "Test alert"}'
```

**Test status check:**
```bash
curl http://localhost:5000/voip/status
```

**Trigger via manual switch in Home Assistant:**
```yaml
# Turn on emergency override switch
service: input_boolean.turn_on
target:
  entity_id: input_boolean.forewarned_manual_emergency
```

## Configuration Options

### Extension Mappings
```json
"alert_calls": {
  "emergency": ["100", "bedside", "mobile"],  // Calls all three
  "warning": ["100"],                         // Calls office only
  "watch": [],                                // No calls
  "advisory": []                              // No calls
}
```

### Backends

**Asterisk/FreePBX (webhook):**
```json
"backend": "webhook",
"webhook_url": "http://asterisk-ip:5038/ami"
```

**Twilio:**
```json
"backend": "twilio",
"twilio_account_sid": "ACxxxxx",
"twilio_auth_token": "your-token",
"twilio_from": "+15551234567",
"twilio_to_numbers": {
  "100": "+15559876543",
  "bedside": "+15559999999"
}
```

**Home Assistant notify service:**
```json
"backend": "ha_notify",
"ha_notify_service": "notify.mobile_app_phone"
```

## VOIP Endpoints

Forewarned exposes these HTTP endpoints for VOIP integration:

- **GET/POST `/voip/status`** - JSON status with TTS message
- **GET/POST `/voip/twiml`** - Twilio TwiML response for inbound calls
- **POST `/voip/menu`** - Twilio menu handler (press 1 to repeat, 2 to hang up)
- **GET `/voip/agi`** - Asterisk AGI script
- **POST `/api/voip/test-call`** - Test call trigger (requires authentication)

## Troubleshooting

**No calls being made:**
1. Check `voip.enabled = true` in config
2. Verify Asterisk AMI is accessible: `telnet asterisk-ip 5038`
3. Check Forewarned logs for VOIP errors
4. Test with `/api/voip/test-call` endpoint

**Calls connecting but no audio:**
1. Verify dialplan context exists: `asterisk -rx "dialplan show forewarned-alerts"`
2. Check Asterisk logs: `asterisk -rvvv`
3. Test TTS manually: `asterisk -rx "console dial 100"`

**Status check not working:**
1. Verify endpoint is accessible: `curl http://forewarned-ip:5000/voip/status`
2. Check extension context matches
3. Enable Asterisk HTTP debugging

## Security Notes

- **Firewall**: Restrict AMI port 5038 to trusted IPs only
- **Authentication**: Use strong AMI passwords
- **TLS**: Consider using HTTPS for webhook calls in production
- **Network**: Run on isolated VLAN if possible

## See Also

- [VOIP_INTEGRATION.md](VOIP_INTEGRATION.md) - Complete technical documentation
- [MANUAL_SWITCHES.md](MANUAL_SWITCHES.md) - Manual override testing guide
- Asterisk AMI: https://wiki.asterisk.org/wiki/display/AST/AMI
- FreePBX: https://www.freepbx.org/
