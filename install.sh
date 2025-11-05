#!/bin/bash
#
# WiFi Wardriving Server - One-Line Installer
# Usage: wget -O - https://raw.githubusercontent.com/lozaning/diywigle/main/install.sh | bash
#

set -e

# Configuration
INSTALL_DIR="/opt/wigle-server"
SERVICE_NAME="wigle-server"
REPO_URL="https://github.com/lozaning/diywigle.git"
REPO_BRANCH="main"

echo "=============================================================="
echo "     WiFi Wardriving Server - Automated Installer"
echo "=============================================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root or with sudo"
    exit 1
fi

echo "Detecting operating system..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
    echo "Detected: $PRETTY_NAME"
else
    echo "ERROR: Cannot detect operating system"
    exit 1
fi

# Verify supported OS
case $OS in
    ubuntu|debian)
        echo "Supported OS detected"
        ;;
    *)
        echo "Warning: This installer is tested on Ubuntu/Debian"
        echo "Your OS: $OS - proceeding anyway..."
        ;;
esac

# Update system
echo ""
echo "Updating package lists..."
apt update -qq

# Install dependencies
echo "Installing dependencies..."
DEBIAN_FRONTEND=noninteractive apt install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    > /dev/null 2>&1
echo "Dependencies installed"

# Create installation directory
echo ""
echo "Creating installation directory..."
if [ -d "$INSTALL_DIR" ]; then
    echo "Warning: Directory $INSTALL_DIR already exists"
    read -p "Remove and reinstall? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        systemctl stop $SERVICE_NAME 2>/dev/null || true
        rm -rf $INSTALL_DIR
        echo "Removed existing installation"
    else
        echo "Installation cancelled"
        exit 1
    fi
fi

mkdir -p $INSTALL_DIR
echo "Directory created: $INSTALL_DIR"

# Clone repository
echo ""
echo "Cloning repository..."
git clone -b $REPO_BRANCH $REPO_URL $INSTALL_DIR --quiet
echo "Repository cloned"

# Install Python dependencies
echo ""
echo "Installing Python packages..."
cd $INSTALL_DIR
pip3 install -q flask flask-sqlalchemy --break-system-packages 2>/dev/null || \
pip3 install -q flask flask-sqlalchemy
echo "Python packages installed"

# Create systemd service
echo ""
echo "Creating systemd service..."
cat > /etc/systemd/system/$SERVICE_NAME.service << 'EOF'
[Unit]
Description=WiFi Wardriving Production Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/wigle-server
ExecStart=/usr/bin/python3 /opt/wigle-server/enhanced_app_production.py
Restart=always
RestartSec=10
Environment="PYTHONUNBUFFERED=1"

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=wigle-server

[Install]
WantedBy=multi-user.target
EOF
echo "Systemd service created"

# Enable and start service
echo ""
echo "Enabling and starting service..."
systemctl daemon-reload
systemctl enable $SERVICE_NAME.service --quiet
systemctl start $SERVICE_NAME.service

# Wait for service to start
sleep 2

# Check if service is running
if systemctl is-active --quiet $SERVICE_NAME.service; then
    echo "Service started successfully"
else
    echo "ERROR: Service failed to start"
    echo "Check logs: journalctl -u $SERVICE_NAME.service -n 50"
    exit 1
fi

# Get IP address
IP_ADDR=$(hostname -I | awk '{print $1}')

# Create convenience scripts
echo ""
echo "Creating management scripts..."

# Status script
cat > $INSTALL_DIR/status.sh << 'EOF'
#!/bin/bash
systemctl status wigle-server.service
EOF
chmod +x $INSTALL_DIR/status.sh

# Logs script
cat > $INSTALL_DIR/logs.sh << 'EOF'
#!/bin/bash
journalctl -u wigle-server.service -f
EOF
chmod +x $INSTALL_DIR/logs.sh

# Restart script
cat > $INSTALL_DIR/restart.sh << 'EOF'
#!/bin/bash
systemctl restart wigle-server.service
echo "Service restarted"
EOF
chmod +x $INSTALL_DIR/restart.sh

echo "Management scripts created"

# Final output
echo ""
echo "=============================================================="
echo "            Installation Complete!"
echo "=============================================================="
echo ""
echo "Access your server at:"
echo "   http://$IP_ADDR:5001"
echo ""
echo "Default login credentials:"
echo "   Username: Admin"
echo "   Password: Wigler"
echo ""
echo "Useful commands:"
echo "   View status:  systemctl status wigle-server"
echo "   View logs:    journalctl -u wigle-server -f"
echo "   Restart:      systemctl restart wigle-server"
echo "   Stop:         systemctl stop wigle-server"
echo ""
echo "Installation directory:"
echo "   $INSTALL_DIR"
echo ""
echo "Quick scripts available:"
echo "   $INSTALL_DIR/status.sh  - Check service status"
echo "   $INSTALL_DIR/logs.sh    - View live logs"
echo "   $INSTALL_DIR/restart.sh - Restart service"
echo ""
echo "Remember to change the default password in production!"
echo ""
