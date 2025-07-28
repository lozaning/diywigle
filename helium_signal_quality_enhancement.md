# Helium LoRaWAN Signal Quality Enhancement

## Overview
Enhanced the webhook template to capture LoRaWAN signal quality metrics (RSSI and SNR) directly from Helium's metadata, providing more accurate signal quality monitoring for device health.

## Changes Made

### Webhook Template Updates
- **Added top-level RSSI**: `"rssi": {{rssi}}` - LoRaWAN signal strength in dBm
- **Added top-level SNR**: `"snr": {{snr}}` - Signal-to-Noise Ratio in dB
- **Simplified structure**: No longer dependent on hotspots array parsing

### Backend Processing Updates
- **Direct extraction**: Gets RSSI and SNR from top-level webhook data
- **Uses SNR for heartbeat**: SNR is more reliable than RSSI for LoRaWAN quality assessment
- **Enhanced logging**: Shows both RSSI and SNR values in debug output

## Benefits

### More Accurate Signal Quality
- **Direct from Helium**: No complex hotspots array parsing required
- **SNR preferred**: SNR is a better indicator of LoRaWAN link quality than RSSI
- **Consistent data**: Always available in Helium webhook metadata

### Simplified Processing
- **No hotspots dependency**: Removes complex array parsing and null checking
- **Cleaner code**: Direct field access instead of nested array traversal
- **Better error handling**: Less prone to template rendering failures

## Signal Quality Interpretation

### SNR (Signal-to-Noise Ratio)
- **> 10 dB**: Excellent signal quality
- **5-10 dB**: Good signal quality  
- **0-5 dB**: Fair signal quality
- **< 0 dB**: Poor signal quality (but still decodable)

### RSSI (Received Signal Strength Indicator)
- **> -90 dBm**: Strong signal
- **-90 to -110 dBm**: Good signal
- **-110 to -120 dBm**: Fair signal
- **< -120 dBm**: Weak signal

## Updated Webhook Template Structure
```json
{
  "dev_eui": "{{dev_eui}}",
  "name": "{{name}}",
  "rssi": {{rssi}},          // LoRaWAN RSSI from Helium
  "snr": {{snr}},            // LoRaWAN SNR from Helium
  "decoded": {
    "payload": {
      "ssid": "{{decoded.payload.ssid}}",
      "mac": "{{decoded.payload.mac}}",
      "rssi": {{decoded.payload.rssi}},    // WiFi RSSI from T-Beam
      // ... other payload fields
    }
  }
}
```

## Data Flow
1. **T-Beam** transmits LoRaWAN packet with WiFi data
2. **Helium hotspot** receives packet and measures RSSI/SNR
3. **Helium Console** includes signal metrics in webhook
4. **Flask backend** extracts both LoRaWAN and WiFi signal data
5. **Heartbeat record** uses LoRaWAN SNR for device health monitoring

## Web Dashboard Impact
- **Device health charts** now show accurate LoRaWAN signal quality
- **Signal quality trends** help identify coverage issues
- **Battery vs. signal correlation** can indicate optimal placement locations