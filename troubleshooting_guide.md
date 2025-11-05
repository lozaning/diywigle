# Troubleshooting Guide - WiFi Wardriving System

## Common Issues and Solutions

### 1. "mustache template render failed" Error
**Symptoms:** Flask backend receives literal string "mustache template render failed" instead of JSON
**Cause:** Helium Console webhook template has syntax errors
**Solution:** Use the working template from `helium_webhook_template_working.json`

### 2. GPS Coordinates Always Zero
**Symptoms:** Backend shows latitude: 0, longitude: 0 even when T-Beam has GPS lock
**Cause:** Helium Console decoder not parsing binary payload correctly
**Solution:** 
- Check byte length in decoder (should be `>= 44` not `>= 45`)
- Use the working decoder from `helium_decoder_working.js`

### 3. JSON Parsing Errors
**Symptoms:** "❌ JSON parsing failed: 400 Bad Request"
**Cause:** Malformed JSON from Helium webhook template
**Common Issues:**
- Missing opening `{` brace
- Empty fields like `"snr": ` with no value
- Missing quotes around string values
**Solution:** Validate template JSON syntax before using

### 4. Firefox Browser Crashes
**Symptoms:** Browser tabs crash when viewing network map
**Cause:** Corrupted GPS coordinates with extreme values (10^27, etc.)
**Solution:** 
- Initialize GPS variables to 0.0 in T-Beam firmware
- Add coordinate validation in Flask backend
- Use pagination to limit data loaded

### 5. T-Beam Not Joining Helium Network
**Symptoms:** "Join Status: NOT_JOINED" in T-Beam logs
**Cause:** Incorrect band configuration or credentials
**Solution:**
- Verify US915 band configuration: `LMIC_selectSubBand(1)`
- Check APPEUI, DEVEUI, APPKEY match Helium Console exactly
- Ensure device is in correct Helium Console organization

### 6. Network Delete Function Not Working
**Symptoms:** Delete buttons don't appear or don't work
**Cause:** User not logged in or missing authentication
**Solution:**
- Login with admin credentials (Admin/Wigler)
- Check Flask session handling

## Debugging Steps

### T-Beam Firmware Debugging
1. Check GPS status in serial output
2. Verify LoRaWAN join status and device address
3. Review hex dump of payload being sent
4. Confirm payload size is exactly 44 bytes

### Flask Backend Debugging
1. Check webhook reception logs for JSON structure
2. Verify payload parsing and GPS coordinate extraction
3. Review database operations and error handling
4. Test individual endpoints with curl

### Helium Console Debugging
1. Check device activity logs for uplinks
2. Verify decoder function execution and output
3. Test webhook template rendering
4. Review hotspot coverage and signal quality

## Log Analysis

### Healthy T-Beam Logs Should Show:
```
Join Status: JOINED, Networks queued: X
*** DETAILED PAYLOAD STRUCTURE ***
   SSID: 'NetworkName' (length: X)
   MAC: 'XX:XX:XX:XX:XX:XX' (length: 17)
   Latitude: XX.XXXXXX (raw bytes: XX XX XX XX)
   Longitude: -XX.XXXXXX (raw bytes: XX XX XX XX)
```

### Healthy Flask Logs Should Show:
```
*** HELIUM WEBHOOK RECEIVED ***
Raw string: {"dev_eui": "...", "decoded": {"payload": {...}}}
*** EXTRACTED WIFI DATA ***
MAC: XX:XX:XX:XX:XX:XX
Final latitude: XX.XXXXXX
✅ Successfully stored LoRaWAN network
```

## Performance Considerations
- Pagination limits to 100 networks per page
- Coordinate validation prevents invalid GPS data
- Network deduplication based on MAC addresses
- Automatic cleanup of old heartbeat data recommended