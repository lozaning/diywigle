#!/bin/bash
#
# WiFi Wardriving Server - Standalone Installer
# For use when repository is private
# Copy and paste this entire script into your server
#

set -e

echo "=============================================================="
echo "     WiFi Wardriving Server - Standalone Installer"
echo "=============================================================="
echo ""

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root or with sudo"
    exit 1
fi

INSTALL_DIR="/opt/wigle-server"

echo "Enter GitHub Personal Access Token (or press Enter to skip):"
read -s GITHUB_TOKEN
echo ""

if [ -z "$GITHUB_TOKEN" ]; then
    echo "No token provided. Will attempt unauthenticated clone..."
    REPO_URL="https://github.com/lozaning/diywigle.git"
else
    echo "Token provided"
    REPO_URL="https://${GITHUB_TOKEN}@github.com/lozaning/diywigle.git"
fi

echo "Updating package lists..."
apt update -qq

echo "Installing dependencies..."
DEBIAN_FRONTEND=noninteractive apt install -y -qq python3 python3-pip git curl > /dev/null 2>&1
echo "Dependencies installed"

echo "Creating installation directory..."
if [ -d "$INSTALL_DIR" ]; then
    echo "Directory exists. Removing..."
    systemctl stop wigle-server 2>/dev/null || true
    rm -rf $INSTALL_DIR
fi
mkdir -p $INSTALL_DIR
echo "Directory created"

echo "Cloning repository..."
if git clone -b main $REPO_URL $INSTALL_DIR 2>&1 | grep -q "Authentication failed"; then
    echo "ERROR: Authentication failed"
    echo "Need GitHub Personal Access Token:"
    echo "  1. Go to: https://github.com/settings/tokens"
    echo "  2. Generate new token (classic)"
    echo "  3. Select 'repo' scope"
    echo "  4. Run this script again with the token"
    exit 1
fi
echo "Repository cloned"

echo "Installing Python packages..."
cd $INSTALL_DIR
pip3 install -q flask flask-sqlalchemy --break-system-packages 2>/dev/null || pip3 install -q flask flask-sqlalchemy
echo "Packages installed"

echo "Creating systemd service..."
cat > /etc/systemd/system/wigle-server.service << 'EOF'
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
StandardOutput=journal
StandardError=journal
SyslogIdentifier=wigle-server

[Install]
WantedBy=multi-user.target
EOF
echo "Service created"

echo "Starting service..."
systemctl daemon-reload
systemctl enable wigle-server.service --quiet
systemctl start wigle-server.service
sleep 2

if systemctl is-active --quiet wigle-server.service; then
    echo "Service running"
else
    echo "ERROR: Service failed"
    journalctl -u wigle-server.service -n 20
    exit 1
fi

IP_ADDR=$(hostname -I | awk '{print $1}')

echo ""
echo "=============================================================="
echo "            Installation Complete!"
echo "=============================================================="
echo ""
echo "Access: http://$IP_ADDR:5001"
echo "Login:  Admin / Wigler"
echo ""
