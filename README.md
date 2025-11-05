# DIY WiFi Wardriving System

A comprehensive WiFi network mapping and wardriving system designed for defensive security research and network analysis.

## 🚀 Quick Install (Ubuntu/Debian)

### For Public Repository:
**One-line installation:**
```bash
wget -O - https://raw.githubusercontent.com/lozaning/diywigle/main/install.sh | sudo bash
```

### For Private Repository:
**Method 1: Clone and run locally**
```bash
git clone https://github.com/lozaning/diywigle.git /opt/wigle-server
cd /opt/wigle-server
chmod +x install.sh
sudo ./install.sh
```

**Method 2: Quick manual install**
```bash
sudo apt update && sudo apt install -y python3 python3-pip git
git clone https://github.com/lozaning/diywigle.git /opt/wigle-server
cd /opt/wigle-server
pip3 install flask flask-sqlalchemy --break-system-packages
python3 enhanced_app_production.py
```

After installation completes, access the dashboard at `http://your-server-ip:5001`

**Default credentials:**
- Username: `Admin`
- Password: `Wigler`

⚠️ **Important:** Change the default password in production environments!

---

## 📋 System Overview

This project consists of three main components:

### 🌐 Web Application (Flask)
- **File:** `enhanced_app_production.py`
- Real-time WiFi network visualization with interactive maps
- Device management and health monitoring
- WiGLE.net integration for data contribution
- RESTful API for device data ingestion

### 📡 ESP32 Cellular Device
- **File:** `WiFi_Wardriving_Production.ino`
- LilyGO T-SIM7000G hardware platform
- Cellular connectivity for remote deployments
- GPS-tagged WiFi network scanning
- HTTP API communication

### 🛰️ ESP32 LoRaWAN Device
- **File:** `The_International_Wigle_Space_Balloon_copy_20250618000042.ino`
- T-Beam hardware platform
- LoRaWAN connectivity for long-range deployments
- Helium Network integration
- Ideal for balloon/drone deployments

---

## 📦 Features

- ✅ **Real-time Network Mapping** - Live visualization of discovered WiFi networks
- ✅ **Multiple Device Support** - Track data from multiple scanning devices
- ✅ **GPS Integration** - Accurate location tagging for all network discoveries
- ✅ **WiGLE.net Upload** - Contribute to the global WiFi database
- ✅ **Device Health Monitoring** - Battery, signal quality, GPS status tracking
- ✅ **Data Export** - CSV export in WiGLE-compatible format
- ✅ **Batch Data Upload** - Efficient bulk data ingestion
- ✅ **LoRaWAN Support** - Long-range, low-power connectivity
- ✅ **Cellular Support** - Wide-area coverage with LTE connectivity
- ✅ **Production Logging** - Proper logging infrastructure

---

## 🖥️ Installation Options

### Option 1: Automated Install (Recommended)
```bash
wget -O - https://raw.githubusercontent.com/lozaning/diywigle/main/install.sh | sudo bash
```

### Option 2: Manual Installation

**1. Install dependencies:**
```bash
sudo apt update
sudo apt install -y python3 python3-pip git
```

**2. Clone repository:**
```bash
git clone https://github.com/lozaning/diywigle.git
cd diywigle
```

**3. Install Python packages:**
```bash
pip3 install flask flask-sqlalchemy
```

**4. Run the server:**
```bash
python3 enhanced_app_production.py
```

### Option 3: Proxmox LXC Container
See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive Proxmox deployment guide including:
- LXC container setup
- Systemd service configuration
- Nginx reverse proxy
- SSL/TLS setup
- Production WSGI server configuration

---

## 🎮 Usage

### Web Dashboard

**Access:** `http://localhost:5001`

**Features:**
- Interactive map showing all discovered networks
- Device status and health monitoring
- Network statistics and time-series graphs
- Database management (clear, export, upload)
- WiGLE.net API configuration

### API Endpoints

**Data submission:**
```bash
# Single network
POST /api/wigle_data
{
  "mac": "AA:BB:CC:DD:EE:FF",
  "ssid": "NetworkName",
  "auth_mode": "WPA2",
  "channel": 6,
  "rssi": -45,
  "latitude": 37.7749,
  "longitude": -122.4194,
  "altitude": 50.0,
  "accuracy": 10.0
}

# Batch upload
POST /api/wigle_data_batch
{
  "device_mac": "AA:BB:CC:DD:EE:FF",
  "networks": [...]
}

# Device heartbeat
POST /api/heartbeat
{
  "mac": "AA:BB:CC:DD:EE:FF",
  "battery": 3.7,
  "gps_active": true,
  "gps_satellites": 8
}
```

**Helium webhook (LoRaWAN):**
```bash
POST /payload
# Configure Helium Console to send decoded payloads here
```

---

## 🔧 Configuration

### Server Settings
Edit `enhanced_app_production.py`:
```python
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change in production!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wigle_data.db'
```

### Hardware Device Settings
Edit the respective `.ino` files:
```cpp
// Server configuration
char server[] = "your-server-ip";
int port = 5001;

// Network credentials
const char* apn = "h2g2";  // Cellular APN
```

---

## 📊 Database

**Location:** `instance/wigle_data.db` (SQLite)

**Tables:**
- `wigle_data` - WiFi network discoveries
- `heartbeat` - Device health data
- `device` - Registered devices
- `settings` - System configuration

**Backup:**
```bash
cp instance/wigle_data.db instance/wigle_data_backup.db
```

**Export to CSV:**
Access web dashboard → Download CSV (WiGLE-compatible format)

---

## 🛠️ Management

### Service Control (Systemd)
```bash
# View status
sudo systemctl status wigle-server

# View logs
sudo journalctl -u wigle-server -f

# Restart
sudo systemctl restart wigle-server

# Stop
sudo systemctl stop wigle-server

# Start
sudo systemctl start wigle-server
```

### Quick Scripts
After installation, use the convenience scripts:
```bash
/opt/wigle-server/status.sh   # Check status
/opt/wigle-server/logs.sh     # View live logs
/opt/wigle-server/restart.sh  # Restart service
```

---

## 🔒 Security Considerations

- ✅ **Defensive Purpose Only** - For legitimate security research and mapping
- ⚠️ **Change Default Credentials** - Update login credentials in production
- ⚠️ **Secure WiGLE API Keys** - Store API keys securely in database
- ✅ **No Network Intrusion** - Only collects public beacon information
- ⚠️ **Use HTTPS** - Consider SSL/TLS for production deployments (see DEPLOYMENT.md)

---

## 📡 Hardware Requirements

### Cellular Device (LilyGO T-SIM7000G)
- ESP32 microcontroller
- SIM7000G cellular modem (LTE Cat-M1/NB-IoT)
- GPS module
- Compatible SIM card

### LoRaWAN Device (T-Beam)
- ESP32 microcontroller
- LoRa radio (915MHz or 868MHz depending on region)
- GPS module
- Helium Network coverage (or other LoRaWAN network)

### Server Requirements
- **Minimum:** 512 MB RAM, 1 CPU core, 8 GB storage
- **Recommended:** 1 GB RAM, 2 CPU cores, 16 GB storage
- Ubuntu 20.04+ or Debian 11+

---

## 📚 Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Comprehensive Proxmox LXC deployment guide
- [CLAUDE.md](CLAUDE.md) - Project overview and architecture for AI assistance

---

## 🤝 Contributing

This is a personal defensive security research project. If you find issues or have improvements:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

## ⚖️ Legal & Ethics

**Important:** This system is designed for:
- ✅ Defensive security research
- ✅ Network coverage mapping
- ✅ Personal education
- ✅ Contributing to public databases (WiGLE.net)

**Not intended for:**
- ❌ Unauthorized network access
- ❌ Malicious activities
- ❌ Privacy violations

Only collect publicly broadcast beacon information. Respect privacy and local regulations.

---

## 📞 Support

For issues and questions:
- Check the logs: `journalctl -u wigle-server -f`
- Review [DEPLOYMENT.md](DEPLOYMENT.md) troubleshooting section
- Check device serial output for hardware debugging

---

## 🎯 Quick Start Checklist

- [ ] Install server using one-line command
- [ ] Access web dashboard at `http://server-ip:5001`
- [ ] Change default login credentials
- [ ] Configure WiGLE.net API key (optional)
- [ ] Flash firmware to ESP32 device(s)
- [ ] Configure device server IP address
- [ ] Test device connectivity (check heartbeat dashboard)
- [ ] Begin scanning!

---

**Made for defensive security research and network mapping.**
