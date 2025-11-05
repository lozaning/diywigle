#!/bin/bash
#
# WiFi Wardriving Server - One-Line Installer
# Usage: wget -O - https://raw.githubusercontent.com/lozaning/diywigle/main/install.sh | bash
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/wigle-server"
SERVICE_NAME="wigle-server"
REPO_URL="https://github.com/lozaning/diywigle.git"
REPO_BRANCH="main"

echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     WiFi Wardriving Server - Automated Installer        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}✗ Please run as root or with sudo${NC}"
    exit 1
fi

echo -e "${YELLOW}► Detecting operating system...${NC}"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
    echo -e "${GREEN}✓ Detected: $PRETTY_NAME${NC}"
else
    echo -e "${RED}✗ Cannot detect operating system${NC}"
    exit 1
fi

# Verify supported OS
case $OS in
    ubuntu|debian)
        echo -e "${GREEN}✓ Supported OS detected${NC}"
        ;;
    *)
        echo -e "${YELLOW}⚠ Warning: This installer is tested on Ubuntu/Debian${NC}"
        echo -e "${YELLOW}  Your OS: $OS - proceeding anyway...${NC}"
        ;;
esac

# Update system
echo ""
echo -e "${YELLOW}► Updating package lists...${NC}"
apt update -qq

# Install dependencies
echo -e "${YELLOW}► Installing dependencies...${NC}"
DEBIAN_FRONTEND=noninteractive apt install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create installation directory
echo ""
echo -e "${YELLOW}► Creating installation directory...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}⚠ Directory $INSTALL_DIR already exists${NC}"
    read -p "Remove and reinstall? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        systemctl stop $SERVICE_NAME 2>/dev/null || true
        rm -rf $INSTALL_DIR
        echo -e "${GREEN}✓ Removed existing installation${NC}"
    else
        echo -e "${RED}✗ Installation cancelled${NC}"
        exit 1
    fi
fi

mkdir -p $INSTALL_DIR
echo -e "${GREEN}✓ Directory created: $INSTALL_DIR${NC}"

# Clone repository
echo ""
echo -e "${YELLOW}► Cloning repository...${NC}"
git clone -b $REPO_BRANCH $REPO_URL $INSTALL_DIR --quiet
echo -e "${GREEN}✓ Repository cloned${NC}"

# Install Python dependencies
echo ""
echo -e "${YELLOW}► Installing Python packages...${NC}"
cd $INSTALL_DIR
pip3 install -q flask flask-sqlalchemy --break-system-packages 2>/dev/null || \
pip3 install -q flask flask-sqlalchemy
echo -e "${GREEN}✓ Python packages installed${NC}"

# Create systemd service
echo ""
echo -e "${YELLOW}► Creating systemd service...${NC}"
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
echo -e "${GREEN}✓ Systemd service created${NC}"

# Enable and start service
echo ""
echo -e "${YELLOW}► Enabling and starting service...${NC}"
systemctl daemon-reload
systemctl enable $SERVICE_NAME.service --quiet
systemctl start $SERVICE_NAME.service

# Wait for service to start
sleep 2

# Check if service is running
if systemctl is-active --quiet $SERVICE_NAME.service; then
    echo -e "${GREEN}✓ Service started successfully${NC}"
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo -e "${YELLOW}  Check logs: journalctl -u $SERVICE_NAME.service -n 50${NC}"
    exit 1
fi

# Get IP address
IP_ADDR=$(hostname -I | awk '{print $1}')

# Create convenience scripts
echo ""
echo -e "${YELLOW}► Creating management scripts...${NC}"

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

echo -e "${GREEN}✓ Management scripts created${NC}"

# Final output
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            Installation Complete! 🎉                     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}📍 Access your server at:${NC}"
echo -e "   ${YELLOW}http://$IP_ADDR:5001${NC}"
echo ""
echo -e "${GREEN}🔐 Default login credentials:${NC}"
echo -e "   ${YELLOW}Username: Admin${NC}"
echo -e "   ${YELLOW}Password: Wigler${NC}"
echo ""
echo -e "${GREEN}📊 Useful commands:${NC}"
echo -e "   ${YELLOW}View status:  systemctl status wigle-server${NC}"
echo -e "   ${YELLOW}View logs:    journalctl -u wigle-server -f${NC}"
echo -e "   ${YELLOW}Restart:      systemctl restart wigle-server${NC}"
echo -e "   ${YELLOW}Stop:         systemctl stop wigle-server${NC}"
echo ""
echo -e "${GREEN}📁 Installation directory:${NC}"
echo -e "   ${YELLOW}$INSTALL_DIR${NC}"
echo ""
echo -e "${GREEN}💡 Quick scripts available:${NC}"
echo -e "   ${YELLOW}$INSTALL_DIR/status.sh  - Check service status${NC}"
echo -e "   ${YELLOW}$INSTALL_DIR/logs.sh    - View live logs${NC}"
echo -e "   ${YELLOW}$INSTALL_DIR/restart.sh - Restart service${NC}"
echo ""
echo -e "${YELLOW}⚠️  Remember to change the default password in production!${NC}"
echo ""
