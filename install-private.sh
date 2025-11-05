#!/bin/bash
#
# WiFi Wardriving Server - Standalone Installer
# For use when repository is private
# Copy and paste this entire script into your server
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     WiFi Wardriving Server - Standalone Installer       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}✗ Please run as root or with sudo${NC}"
    exit 1
fi

INSTALL_DIR="/opt/wigle-server"

echo -e "${YELLOW}► Enter GitHub Personal Access Token (or press Enter to skip):${NC}"
read -s GITHUB_TOKEN
echo ""

if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${YELLOW}⚠ No token provided. Will attempt unauthenticated clone...${NC}"
    REPO_URL="https://github.com/lozaning/diywigle.git"
else
    echo -e "${GREEN}✓ Token provided${NC}"
    REPO_URL="https://${GITHUB_TOKEN}@github.com/lozaning/diywigle.git"
fi

echo -e "${YELLOW}► Updating package lists...${NC}"
apt update -qq

echo -e "${YELLOW}► Installing dependencies...${NC}"
DEBIAN_FRONTEND=noninteractive apt install -y -qq python3 python3-pip git curl > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}"

echo -e "${YELLOW}► Creating installation directory...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}⚠ Directory exists. Removing...${NC}"
    systemctl stop wigle-server 2>/dev/null || true
    rm -rf $INSTALL_DIR
fi
mkdir -p $INSTALL_DIR
echo -e "${GREEN}✓ Directory created${NC}"

echo -e "${YELLOW}► Cloning repository...${NC}"
if git clone -b main $REPO_URL $INSTALL_DIR 2>&1 | grep -q "Authentication failed"; then
    echo -e "${RED}✗ Authentication failed${NC}"
    echo -e "${YELLOW}Need GitHub Personal Access Token:${NC}"
    echo "  1. Go to: https://github.com/settings/tokens"
    echo "  2. Generate new token (classic)"
    echo "  3. Select 'repo' scope"
    echo "  4. Run this script again with the token"
    exit 1
fi
echo -e "${GREEN}✓ Repository cloned${NC}"

echo -e "${YELLOW}► Installing Python packages...${NC}"
cd $INSTALL_DIR
pip3 install -q flask flask-sqlalchemy --break-system-packages 2>/dev/null || pip3 install -q flask flask-sqlalchemy
echo -e "${GREEN}✓ Packages installed${NC}"

echo -e "${YELLOW}► Creating systemd service...${NC}"
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
echo -e "${GREEN}✓ Service created${NC}"

echo -e "${YELLOW}► Starting service...${NC}"
systemctl daemon-reload
systemctl enable wigle-server.service --quiet
systemctl start wigle-server.service
sleep 2

if systemctl is-active --quiet wigle-server.service; then
    echo -e "${GREEN}✓ Service running${NC}"
else
    echo -e "${RED}✗ Service failed${NC}"
    journalctl -u wigle-server.service -n 20
    exit 1
fi

IP_ADDR=$(hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            Installation Complete! 🎉                     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}📍 Access: ${YELLOW}http://$IP_ADDR:5001${NC}"
echo -e "${GREEN}🔐 Login:  ${YELLOW}Admin / Wigler${NC}"
echo ""
