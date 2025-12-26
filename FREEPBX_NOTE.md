# FreePBX Configuration Note

## Updated Documentation for FreePBX Compatibility

The VOIP integration documentation has been updated to clarify the difference between FreePBX and vanilla Asterisk configurations.

### Key Changes

**FreePBX users should use:**
- `/etc/asterisk/manager_custom.conf` instead of `manager.conf`
- `/etc/asterisk/extensions_custom.conf` instead of `extensions.conf`
- `[from-internal-custom]` context instead of `[from-internal]`

**Why?**
FreePBX overwrites `manager.conf` and `extensions.conf` when you make changes in the web GUI. The `*_custom.conf` files are specifically designed for user customizations and won't be touched by FreePBX.

### What Was Updated

1. **VOIP_QUICKSTART.md**
   - Added FreePBX-specific instructions for each section
   - Clearly marked FreePBX vs vanilla Asterisk paths
   - Added note that FreePBX has AMI enabled by default

2. **VOIP_INTEGRATION.md**
   - Added "Important" section at the top explaining the difference
   - Updated all configuration examples to show both FreePBX and vanilla paths
   - Specified which context to use for each system

### Quick Reference

| File Type | FreePBX Path | Vanilla Asterisk Path |
|-----------|--------------|----------------------|
| AMI Config | `/etc/asterisk/manager_custom.conf` | `/etc/asterisk/manager.conf` |
| Dialplan | `/etc/asterisk/extensions_custom.conf` | `/etc/asterisk/extensions.conf` |
| User Context | `[from-internal-custom]` | `[from-internal]` |
| Alert Context | `[forewarned-alerts]` | `[forewarned-alerts]` |

### Example: Adding Status Check Extension

**FreePBX:**
```ini
# /etc/asterisk/extensions_custom.conf
[from-internal-custom]
exten => *411,1,NoOp(Forewarned Status)
 same => n,Answer()
 same => n,Set(STATUS=${CURL(http://forewarned:5000/voip/status)})
 same => n,Set(MESSAGE=${JSON_DECODE(${STATUS},message)})
 same => n,SayText(${MESSAGE})
 same => n,Hangup()
```

**Vanilla Asterisk:**
```ini
# /etc/asterisk/extensions.conf
[from-internal]
exten => *411,1,NoOp(Forewarned Status)
 same => n,Answer()
 same => n,Set(STATUS=${CURL(http://forewarned:5000/voip/status)})
 same => n,Set(MESSAGE=${JSON_DECODE(${STATUS},message)})
 same => n,SayText(${MESSAGE})
 same => n,Hangup()
```

The dialplan code is identical - only the filename and context name differ!

### After Making Changes

Both systems require a reload:
```bash
asterisk -rx "manager reload"
asterisk -rx "dialplan reload"
```

Or restart Asterisk:
```bash
systemctl restart asterisk
```

---

This documentation update ensures FreePBX users won't have their customizations overwritten by the GUI.
