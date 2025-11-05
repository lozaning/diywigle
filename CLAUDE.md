# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **DIY WiFi Wardriving System** that consists of:
- **Flask web application** (`enhanced_app_production.py`) - Server for collecting and visualizing WiFi data
- **ESP32 cellular device firmware** (`WiFi_Wardriving_Production.ino`) - Cellular-enabled WiFi scanner
- **ESP32 LoRaWAN device firmware** (`The_International_Wigle_Space_Balloon_copy_20250618000042.ino`) - LoRaWAN-enabled WiFi scanner

The system is designed for **defensive security research** - mapping WiFi networks for security analysis and research purposes.

## Architecture

### Web Application (Flask)
- **Database**: SQLite (`wigle_data.db`) with models for WiFi networks, device heartbeats, device management, and settings
- **Frontend**: Embedded HTML templates with interactive maps using Leaflet.js
- **Authentication**: Simple login system (username: `Admin`, password: `Wigler`)
- **API Integration**: WiGLE.net upload functionality for contributing to the public wardriving database

### Hardware Devices
- **LilyGO T-SIM7000G**: Cellular-enabled device that scans WiFi and reports via HTTP API
- **T-Beam**: LoRaWAN-enabled device for satellite communication scenarios

### Data Flow
1. Hardware devices scan for WiFi networks
2. GPS coordinates are captured when available
3. Data is transmitted to Flask server via HTTP API (cellular) or LoRaWAN
4. Server stores data and provides web dashboard for visualization
5. Optional upload to WiGLE.net for public contribution

## Running the System

### Flask Web Application
```bash
python enhanced_app_production.py
```
- Runs on `http://127.0.0.1:5001`
- Creates SQLite database automatically
- Web dashboard available immediately

### Hardware Programming
- Use Arduino IDE or PlatformIO
- Install required libraries (see `#include` statements in .ino files)
- Configure WiFi and cellular/LoRaWAN credentials as needed

## API Endpoints

### Data Collection
- `POST /api/wigle_data` - Single network entry
- `POST /api/wigle_data_batch` - Batch network upload
- `POST /api/heartbeat` - Device health status

### Management (requires login)
- `POST /api/clear_database` - Clear all data
- `POST /api/upload_to_wigle` - Upload to WiGLE.net
- `GET /csv` - Download data as WiGLE-compatible CSV

## Configuration

### Server Configuration
- Server IP and port configured in firmware: `24.152.185.226:5001`
- Change `server[]` and `port` variables in `.ino` files for different server
- Database path and secret key in Flask app configuration

### Hardware Configuration
- Cellular APN: Primary `h2g2`, Fallback `fast.t-mobile.com`
- GPS update interval: 5 seconds
- WiFi scan interval: 5 seconds
- Heartbeat interval: 2.5 minutes

## Security Considerations

- **Defensive Purpose Only**: This system is for legitimate security research and mapping
- **Credentials**: Change default login credentials in production
- **API Key Storage**: WiGLE API keys stored in database settings table
- **Network Scanning**: Only collects public beacon information, no network intrusion

## Data Models

### WigleData
- MAC, SSID, auth_mode, channel, RSSI
- GPS coordinates (latitude, longitude, altitude, accuracy)  
- Timestamp and WiGLE upload status

### Heartbeat
- Device MAC, battery voltage, solar voltage
- Signal quality, memory usage, GPS status
- Network cache statistics

### Device
- MAC address, optional friendly name
- First seen and last seen timestamps

## Testing and Development

- No formal test framework - manual testing via web interface
- Debug output via serial console on hardware devices
- Flask debug mode disabled in production configuration
- Monitor device health via heartbeat dashboard

## Troubleshooting

- Check cellular connectivity via serial output
- Verify GPS fix before expecting location data
- Monitor battery levels for outdoor deployments
- Database corruption can be resolved by deleting `wigle_data.db`