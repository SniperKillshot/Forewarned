# VOIP/Phone System Integration

Forewarned can integrate with your VOIP phone system to:
1. **Make outbound calls** to notify you when alert levels are reached
2. **Handle inbound calls** where you can dial in to check current alert status

## Important: FreePBX vs Vanilla Asterisk

**If you're using FreePBX:**
- Use `manager_custom.conf` instead of `manager.conf` (won't be overwritten by FreePBX GUI)
- Use `extensions_custom.conf` instead of `extensions.conf` (won't be overwritten by FreePBX GUI)
- Use `[from-internal-custom]` context for user extensions
- AMI is already enabled by default on port 5038

**If you're using vanilla Asterisk:**
- Use `manager.conf` and `extensions.conf` directly
- Use `[from-internal]` or your main dialplan context

Throughout this documentation, we'll specify which file to use for each system.

## Supported VOIP Systems

### 1. Asterisk / FreePBX (Recommended)
- ✅ Outbound calls via AMI (Asterisk Manager Interface)
- ✅ Inbound status checks via AGI or dialplan
- ✅ Most flexible and feature-rich

### 2. Twilio
- ✅ Outbound calls via HTTP API
- ✅ Inbound calls via TwiML webhooks
- ⚠️ Costs money per call

### 3. Home Assistant VOIP Integration
- ✅ Use HA's built-in notify services
- ✅ Works with various VOIP providers
- ℹ️ Simpler setup, fewer features

### 4. Direct SIP (Future)
- 🚧 Planned for future release
- Would use PJSUA2 library

## Configuration

Add to your `config_data.json`:

```json
{
  "voip": {
    "enabled": true,
    "backend": "webhook",
    "webhook_url": "http://your-pbx:8088/ari/channels",
    "webhook_method": "POST",
    "webhook_auth": {
      "type": "basic",
      "username": "admin",
      "password": "your-password"
    },
    "webhook_payload_template": {
      "endpoint": "PJSIP/{{extension}}",
      "extension": "forewarned-alert",
      "context": "forewarned",
      "priority": 1,
      "callerid": "Forewarned Alert",
      "variables": {
        "ALERT_LEVEL": "{{alert_level}}",
        "ALERT_MESSAGE": "{{message}}"
      }
    },
    "alert_calls": {
      "advisory": [],
      "watch": [],
      "warning": ["100", "101"],
      "emergency": ["100", "101", "102", "bedside"]
    }
  }
}
```

## Setup Examples

### Asterisk / FreePBX Setup

#### 1. Configure AMI Access

Edit `/etc/asterisk/manager.conf`:

```ini
[general]
enabled = yes
port = 5038
bindaddr = 0.0.0.0

#### 1. Configure AMI

**For FreePBX:** Edit `/etc/asterisk/manager_custom.conf` (won't be overwritten by FreePBX):

```ini
[forewarned]
secret = your-secure-password
deny = 0.0.0.0/0.0.0.0
permit = 192.168.1.0/255.255.255.0  ; Adjust to your network
read = system,call,log,verbose,command,agent,user,config,originate
write = system,call,log,verbose,command,agent,user,config,originate
```

**For vanilla Asterisk:** Edit `/etc/asterisk/manager.conf`:

```ini
[general]
enabled = yes
port = 5038
bindaddr = 0.0.0.0

[forewarned]
secret = your-secure-password
deny = 0.0.0.0/0.0.0.0
permit = 192.168.1.0/255.255.255.0  ; Adjust to your network
read = system,call,log,verbose,command,agent,user,config,originate
write = system,call,log,verbose,command,agent,user,config,originate
```

Reload: `asterisk -rx "manager reload"`

**Note:** FreePBX has AMI enabled by default on port 5038. Use `manager_custom.conf` to avoid your changes being overwritten.

#### 2. Create Dialplan Context

**For FreePBX:** Edit `/etc/asterisk/extensions_custom.conf`:

**For vanilla Asterisk:** Edit `/etc/asterisk/extensions.conf`:

```ini
[forewarned]
exten => forewarned-alert,1,NoOp(Forewarned Alert Call)
 same => n,Set(CHANNEL(language)=en)
 same => n,Answer()
 same => n,Wait(1)
 
 ; Emergency alert
 same => n,GotoIf($["${ALERT_LEVEL}" = "emergency"]?emergency)
 same => n,GotoIf($["${ALERT_LEVEL}" = "warning"]?warning)
 same => n,GotoIf($["${ALERT_LEVEL}" = "watch"]?watch)
 same => n,Goto(advisory)
 
 same => n(emergency),Playback(important-message)
 same => n,SayText(Emergency alert. ${ALERT_MESSAGE}. Take immediate action!)
 same => n,Wait(1)
 same => n,SayText(This is an emergency. ${ALERT_MESSAGE})
 same => n,Goto(end)
 
 same => n(warning),SayText(Warning alert. ${ALERT_MESSAGE}. Take precautions.)
 same => n,Goto(end)
 
 same => n(watch),SayText(Watch alert. ${ALERT_MESSAGE}. Monitor conditions.)
 same => n,Goto(end)
 
 same => n(advisory),SayText(Advisory alert. ${ALERT_MESSAGE})
 same => n,Goto(end)
 
 same => n(end),Wait(2)
 same => n,SayText(Press 1 to hear this message again. Press 2 to acknowledge.)
 same => n,Read(DIGIT,beep,1,,1,5)
 same => n,GotoIf($["${DIGIT}" = "1"]?repeat)
 same => n,GotoIf($["${DIGIT}" = "2"]?ack)
 same => n,Goto(hangup)
 
 same => n(repeat),Goto(forewarned-alert,1)
 
 same => n(ack),SayText(Alert acknowledged.)
 same => n,System(curl -X POST http://forewarned:5000/api/voip/acknowledge?level=${ALERT_LEVEL})
 same => n,Goto(hangup)
 
 same => n(hangup),SayText(Goodbye)
 same => n,Hangup()
```

#### 3. Create Status Check Extension

**For FreePBX:** Add to `/etc/asterisk/extensions_custom.conf`:

```ini
[from-internal-custom]
; Dial *411 to check Forewarned status
exten => *411,1,NoOp(Check Forewarned Status)
 same => n,Answer()
 same => n,Wait(1)
 same => n,Set(STATUS=${CURL(http://forewarned:5000/voip/status)})
 same => n,Set(MESSAGE=${JSON_DECODE(${STATUS},message)})
 same => n,SayText(${MESSAGE})
 same => n,Hangup()
```

**For vanilla Asterisk:** Add to `/etc/asterisk/extensions.conf`:

```ini
[from-internal]
; Dial *411 to check Forewarned status
exten => *411,1,NoOp(Check Forewarned Status)
 same => n,Answer()
 same => n,Wait(1)
 same => n,Set(STATUS=${CURL(http://forewarned:5000/voip/agi)})
 same => n,System(echo "${STATUS}" | /usr/bin/asterisk -rx "${STATUS}")
 same => n,Hangup()
```

Or use AGI directly:

```ini
exten => *411,1,NoOp(Check Forewarned Status)
 same => n,Answer()
 same => n,AGI(forewarned-status.agi)
 same => n,Hangup()
```

Create `/var/lib/asterisk/agi-bin/forewarned-status.agi`:

```bash
#!/bin/bash
# Forewarned Status AGI Script

# Get status from Forewarned
STATUS=$(curl -s http://forewarned:5000/voip/status)
MESSAGE=$(echo $STATUS | jq -r '.message')

echo "ANSWER"
echo "WAIT 1"
echo "EXEC Set(CHANNEL(language)=en)"
echo "EXEC SayText(\"$MESSAGE\")"
echo "WAIT 2"
echo "HANGUP"
```

Make it executable:
```bash
chmod +x /var/lib/asterisk/agi-bin/forewarned-status.agi
```

#### 4. Configure Forewarned

```json
{
  "voip": {
    "enabled": true,
    "backend": "webhook",
    "webhook_url": "http://your-pbx-ip:5038/ami",
    "webhook_method": "POST",
    "webhook_auth": {
      "type": "basic",
      "username": "forewarned",
      "password": "your-secure-password"
    },
    "webhook_payload_template": {
      "Action": "Originate",
      "Channel": "PJSIP/{{extension}}",
      "Context": "forewarned",
      "Exten": "forewarned-alert",
      "Priority": "1",
      "CallerID": "Forewarned Alert <999>",
      "Variable": "ALERT_LEVEL={{alert_level}},ALERT_MESSAGE={{message}}",
      "Async": "true"
    },
    "alert_calls": {
      "emergency": ["100", "101", "bedside"],
      "warning": ["100"],
      "watch": [],
      "advisory": []
    }
  }
}
```

### Twilio Setup

#### 1. Get Twilio Account
- Sign up at https://www.twilio.com
- Get your Account SID and Auth Token
- Purchase a phone number

#### 2. Configure Webhook in Twilio Console
- Go to Phone Numbers → Your number
- Set Voice webhook to: `http://your-forewarned-url:5000/voip/twiml`

#### 3. Configure Forewarned

```json
{
  "voip": {
    "enabled": true,
    "backend": "webhook",
    "webhook_url": "https://api.twilio.com/2010-04-01/Accounts/YOUR_ACCOUNT_SID/Calls.json",
    "webhook_method": "POST",
    "webhook_auth": {
      "type": "basic",
      "username": "YOUR_ACCOUNT_SID",
      "password": "YOUR_AUTH_TOKEN"
    },
    "webhook_payload_template": {
      "To": "+1{{extension}}",
      "From": "+1234567890",
      "Url": "http://your-forewarned-url:5000/voip/twiml-outbound"
    },
    "alert_calls": {
      "emergency": ["5551234567"],
      "warning": ["5551234567"],
      "watch": [],
      "advisory": []
    }
  }
}
```

### Home Assistant Notify Service

#### 1. Configure HA Notify Service

In Home Assistant configuration.yaml:

```yaml
notify:
  - platform: rest
    name: voip_phone
    resource: http://your-pbx/originate
    method: POST_JSON
    data:
      channel: "PJSIP/{{ extension }}"
      context: "alerts"
```

Or use a dedicated VOIP integration like:
- Asterisk integration
- FreePBX integration
- SIP integration

#### 2. Configure Forewarned

```json
{
  "voip": {
    "enabled": true,
    "backend": "ha_notify",
    "ha_notify_service": "notify.voip_phone",
    "alert_calls": {
      "emergency": ["100", "bedside"],
      "warning": ["100"],
      "watch": [],
      "advisory": []
    }
  }
}
```

## Usage

### Outbound Alert Calls

Calls are automatically made based on your `alert_calls` configuration:

- **Emergency**: Calls all listed extensions immediately
- **Warning**: Calls specified extensions
- **Watch**: Usually no calls (monitoring only)
- **Advisory**: Usually no calls (information only)

### Inbound Status Checks

#### Dial-in Extension (Asterisk)
Dial `*411` (or your configured extension) to hear:
- Current alert level
- Reason for alert
- Recommended actions

#### HTTP API
Query status programmatically:

```bash
curl http://forewarned:5000/voip/status
```

Response:
```json
{
  "active": true,
  "level": "warning",
  "reason": "Severe Weather Warning",
  "message": "Current alert level is WARNING. Severe Weather Warning. This is a warning. Take appropriate precautions."
}
```

#### TwiML (Twilio)
Calls to your Twilio number automatically get routed to Forewarned's TwiML handler.

## Advanced Configuration

### Multiple Phone Numbers for Different Alert Levels

```json
{
  "alert_calls": {
    "emergency": {
      "extensions": ["100", "101", "bedside"],
      "repeat": 3,
      "interval_seconds": 300
    },
    "warning": {
      "extensions": ["100"],
      "repeat": 1
    }
  }
}
```

### Call Scheduling (Don't call at night for low-priority alerts)

Use Home Assistant automations:

```yaml
automation:
  - alias: "Block Advisory Calls at Night"
    trigger:
      - platform: state
        entity_id: binary_sensor.forewarned_local_alert
        to: "on"
    condition:
      - condition: state
        entity_id: binary_sensor.forewarned_local_alert
        attribute: alert_level
        state: "advisory"
      - condition: time
        after: "22:00:00"
        before: "07:00:00"
    action:
      # Disable VOIP temporarily
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.forewarned_voip_enabled
```

### Call Acknowledgment

Add endpoint to track acknowledgments:

```json
POST /api/voip/acknowledge?level=emergency&extension=100
```

## Testing

### Test Outbound Call

```bash
curl -X POST http://forewarned:5000/api/voip/test-call \
  -H "Content-Type: application/json" \
  -d '{
    "extension": "100",
    "alert_level": "warning",
    "reason": "Test alert call"
  }'
```

### Test Inbound Status

Dial your configured status extension or:

```bash
curl http://forewarned:5000/voip/status
```

## Troubleshooting

### Calls Not Going Through

1. Check Asterisk AMI connectivity:
   ```bash
   telnet your-pbx-ip 5038
   ```

2. Check Forewarned logs:
   ```bash
   docker logs forewarned
   ```

3. Verify extension is registered:
   ```bash
   asterisk -rx "pjsip show endpoints"
   ```

### No Audio on Inbound Calls

1. Check firewall allows RTP ports (10000-20000)
2. Verify NAT settings in Asterisk
3. Check codec compatibility

### TwiML Not Working

1. Verify webhook URL is publicly accessible
2. Check Twilio debugger console
3. Ensure HTTPS if required by Twilio

## Security Considerations

- **Use HTTPS** for webhooks when possible
- **Restrict AMI access** to Forewarned's IP only
- **Use strong passwords** for AMI credentials
- **Rate limit** status check endpoints
- **Log all calls** for audit trail

## Future Enhancements

- Call recording
- Multi-language support
- SMS fallback
- Call retry logic
- Escalation chains (call A, if no answer call B)
- Interactive voice menus (press 1 for details, 2 to dismiss)
