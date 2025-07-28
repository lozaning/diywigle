# Helium LoRaWAN Health Data Integration

## Overview
This system now piggybacks device health data (battery voltage and GPS satellite count) onto regular WiFi network transmissions, eliminating the need for separate heartbeat messages.

## Implementation Details

### T-Beam Firmware Changes
- **WifiNetwork struct expanded** from 44 to 49 bytes
- **Added fields**:
  - `float battery_voltage` - Current device battery voltage
  - `uint8_t gps_satellites` - Number of GPS satellites visible (device health)
- **Health data collection**: Gathered once per scan batch and applied to all networks in that batch
- **Battery reading**: Uses AXP192 `getBattVoltage()` method
- **GPS satellites**: Always reads current satellite count regardless of GPS fix status

### Helium Console Configuration
- **Decoder updated** to parse 49-byte payload (was 44 bytes)
- **New decoder fields**: `battery_voltage` and `gps_satellites`
- **Webhook template** includes health data fields in JSON output

### Flask Backend Processing
- **Extracts health data** from each network payload
- **Creates heartbeat records** using piggybacked health data
- **No separate heartbeat endpoint** needed - health data comes with network data
- **Heartbeat frequency** matches network transmission frequency

## Data Flow

```
1. T-Beam scans WiFi networks
2. T-Beam reads current battery voltage and GPS satellites
3. T-Beam adds health data to each network record in the batch
4. T-Beam transmits 49-byte payload via LoRaWAN
5. Helium Console decodes payload including health fields
6. Webhook delivers network + health data to Flask backend
7. Flask stores network data AND creates heartbeat record
8. Web dashboard shows device health from piggybacked data
```

## Benefits
- **Reduced LoRaWAN usage**: No separate heartbeat transmissions needed
- **Real-time health monitoring**: Health data updated with every network transmission
- **Efficient**: Single transmission carries both network and health information
- **Consistent**: Health data frequency matches network transmission rate

## Configuration Files
- **Firmware**: `The_International_Wigle_Space_Balloon_copy_20250618000042.ino`
- **Decoder**: `helium_decoder_working.js` (49-byte version)
- **Webhook**: `helium_webhook_template_working.json` (includes health fields)
- **Backend**: `enhanced_app_production.py` (extracts health data)

## Payload Structure (49 bytes total)
```
Offset | Size | Field           | Description
-------|------|-----------------|---------------------------
0-10   | 11   | ssid           | WiFi network name
11-28  | 18   | mac            | MAC address (ASCII)
29     | 1    | rssi           | Signal strength
30     | 1    | channel        | WiFi channel
31     | 1    | encryption     | Security type
32-35  | 4    | latitude       | GPS latitude (float32)
36-39  | 4    | longitude      | GPS longitude (float32)
40-41  | 2    | altitude       | GPS altitude (int16)
42     | 1    | sats           | GPS satellites (location)
43     | 1    | hdop           | GPS accuracy
44-47  | 4    | battery_voltage| Device battery (float32) [NEW]
48     | 1    | gps_satellites | GPS sats (health) [NEW]
```

## Health Data Usage
- **Battery Voltage**: Used for device health monitoring and low battery alerts
- **GPS Satellites**: Indicates GPS antenna/receiver health independent of location fix
- **Both fields**: Updated with every network transmission for real-time monitoring
- **Web Dashboard**: Shows current device health status with latest values