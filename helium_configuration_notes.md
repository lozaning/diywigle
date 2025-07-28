# Helium Console Configuration - Working Setup

## Summary
This documents the working configuration for T-Beam LoRaWAN to Flask backend integration via Helium Console.

## Issue Resolution
The main issues were:
1. **Helium Console decoder** - Was checking for `>= 45` bytes but T-Beam sends exactly 44 bytes
2. **Webhook template** - Had malformed JSON due to missing opening brace and empty SNR field
3. **GPS coordinate corruption** - Fixed by initializing GPS variables to 0.0 in T-Beam firmware

## Working Configuration

### 1. Helium Console Decoder Function
Use the decoder in `helium_decoder_working.js` - key change was fixing byte length check from 45 to 44.

### 2. Helium Console Webhook Template
Use the template in `helium_webhook_template_working.json`:
- Properly formatted JSON with all required braces
- Encryption field quoted as string
- Removed problematic SNR field that was causing empty values

### 3. T-Beam Firmware
- Added extensive debugging output showing hex dumps of payload
- Fixed GPS coordinate initialization to prevent corruption
- Maintains exactly 44-byte payload structure

### 4. Flask Backend
- Added comprehensive debugging for webhook analysis
- Handles multiple payload formats (nested and flat)
- Includes coordinate validation to prevent map crashes
- Added individual network deletion functionality

## Network Flow
1. **T-Beam** scans WiFi networks and queues them
2. **T-Beam** sends 44-byte binary payload via LoRaWAN to Helium
3. **Helium Console** decodes binary payload using JavaScript decoder
4. **Helium Console** formats decoded data using Mustache template
5. **Helium Console** posts JSON webhook to Flask backend `/payload` endpoint
6. **Flask Backend** parses JSON and stores network data in SQLite database
7. **Web Interface** displays networks with map visualization and deletion controls

## Debugging Features
- T-Beam firmware logs detailed payload structure and hex dumps
- Flask backend logs complete webhook analysis and processing steps
- Both sides include extensive error handling and context logging