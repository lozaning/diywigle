# Deploying WiFi Wardriving Server to Proxmox LXC Container

## Quick Setup Guide

### 1. Create LXC Container in Proxmox

**In Proxmox Web UI:**
1. Click **Create CT** button
2. Configure the container:
   - **General:**
     - Hostname: `wigle-server` (or your choice)
     - Password: Set a root password
     - SSH public key: (optional, recommended)

   - **Template:**
     - Storage: local
     - Template: `debian-12-standard` or `ubuntu-22.04-standard`

   - **Root Disk:**
     - Disk size: `8 GB` (minimum, 16 GB recommended)

   - **CPU:**
     - Cores: `1` (2 recommended for better performance)

   - **Memory:**
     - RAM: `512 MB` (1024 MB recommended)
     - Swap: `512 MB`

   - **Network:**
     - Bridge: `vmbr0` (or your network bridge)
     - IPv4: DHCP or Static (note the IP address)
     - Firewall: Enabled (optional)

3. **Start the container**

### 2. Install Dependencies in Container

**SSH into the container:**
```bash
# From Proxmox host or your workstation
ssh root@<container-ip>
```

**Update system and install dependencies:**
```bash
# Update package lists
apt update && apt upgrade -y

# Install Python and pip
apt install -y python3 python3-pip git

# Optional but recommended
apt install -y nano vim curl wget
```

### 3. Deploy the Application

**Option A: Clone from Git (Recommended)**
```bash
# Create app directory
mkdir -p /opt/wigle-server
cd /opt/wigle-server

# Clone your repository
git clone https://github.com/lozaning/diywigle.git .

# Install Python dependencies
pip3 install flask flask-sqlalchemy --break-system-packages
```

**Option B: Manual Copy**
```bash
# From your local machine, copy files to container
scp -r /path/to/diywigle root@<container-ip>:/opt/wigle-server/
```

### 4. Create Systemd Service (Run on Boot)

Create a systemd service file:

```bash
nano /etc/systemd/system/wigle-server.service
```

**Add this content:**
```ini
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

# Environment variables (optional)
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

**Enable and start the service:**
```bash
# Reload systemd
systemctl daemon-reload

# Enable service to start on boot
systemctl enable wigle-server.service

# Start the service now
systemctl start wigle-server.service

# Check status
systemctl status wigle-server.service
```

### 5. Configure Firewall (if using Proxmox firewall)

**In Proxmox Web UI:**
1. Select your container
2. Go to **Firewall** → **Add** rule
3. Add rule:
   - Direction: `in`
   - Action: `ACCEPT`
   - Protocol: `tcp`
   - Dest. port: `5001`
   - Comment: `WiFi Wardriving Web Interface`

### 6. Access Your Server

Your server should now be accessible at:
- **Local network:** `http://<container-ip>:5001`
- **Login:** `lozaning` / `oneill`

**Check if it's running:**
```bash
curl http://localhost:5001
systemctl status wigle-server.service
journalctl -u wigle-server.service -f  # View live logs
```

---

## Advanced Configuration

### Using Nginx Reverse Proxy (Recommended for Production)

**Install Nginx:**
```bash
apt install -y nginx
```

**Create Nginx configuration:**
```bash
nano /etc/nginx/sites-available/wigle-server
```

**Add this content:**
```nginx
server {
    listen 80;
    server_name wigle.yourdomain.com;  # Or use IP address

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Enable the site:**
```bash
ln -s /etc/nginx/sites-available/wigle-server /etc/nginx/sites-enabled/
nginx -t  # Test configuration
systemctl restart nginx
```

Now access at: `http://<container-ip>` (port 80)

### Adding SSL with Let's Encrypt (Optional)

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d wigle.yourdomain.com
```

### Using Production WSGI Server (Gunicorn)

The Flask development server warns about not using it in production. For better performance:

**Install Gunicorn:**
```bash
pip3 install gunicorn --break-system-packages
```

**Update systemd service:**
```bash
nano /etc/systemd/system/wigle-server.service
```

Change `ExecStart` line to:
```ini
ExecStart=/usr/local/bin/gunicorn -w 4 -b 0.0.0.0:5001 enhanced_app_production:app
```

Then restart:
```bash
systemctl daemon-reload
systemctl restart wigle-server.service
```

---

## Backup and Persistence

### Backup Database
```bash
# Create backup directory
mkdir -p /opt/wigle-server/backups

# Backup script
cat > /opt/wigle-server/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/wigle-server/backups"
DATE=$(date +%Y%m%d_%H%M%S)
cp /opt/wigle-server/instance/wigle_data.db "$BACKUP_DIR/wigle_data_$DATE.db"
# Keep only last 7 backups
ls -t "$BACKUP_DIR"/wigle_data_*.db | tail -n +8 | xargs -r rm
EOF

chmod +x /opt/wigle-server/backup.sh

# Add to crontab (daily backup at 2 AM)
echo "0 2 * * * /opt/wigle-server/backup.sh" | crontab -
```

### Mount External Storage (Optional)

If you want to store database on Proxmox host storage:

**On Proxmox host:**
```bash
pct set <CTID> -mp0 /path/on/host,mp=/mnt/data
```

**In container:**
```bash
# Move database to mounted storage
mkdir -p /mnt/data/wigle
mv /opt/wigle-server/instance /mnt/data/wigle/
ln -s /mnt/data/wigle/instance /opt/wigle-server/instance
```

---

## Monitoring and Maintenance

### View Logs
```bash
# Application logs
journalctl -u wigle-server.service -f

# Last 100 lines
journalctl -u wigle-server.service -n 100

# Nginx logs (if using)
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Update Application
```bash
cd /opt/wigle-server
git pull
systemctl restart wigle-server.service
```

### Resource Monitoring
```bash
# Check container resources
htop

# Check disk usage
df -h

# Check database size
du -sh /opt/wigle-server/instance/
```

---

## Troubleshooting

### Service won't start
```bash
# Check logs
journalctl -u wigle-server.service -xe

# Test manually
cd /opt/wigle-server
python3 enhanced_app_production.py
```

### Can't access web interface
```bash
# Check if port is listening
ss -tlnp | grep 5001

# Check firewall
iptables -L -n

# Test from within container
curl http://localhost:5001
```

### Database permissions
```bash
# Fix permissions if needed
chown -R root:root /opt/wigle-server
chmod -R 755 /opt/wigle-server
```

---

## Quick One-Liner Setup Script

Save this as `setup.sh` and run on fresh LXC container:

```bash
#!/bin/bash
set -e

echo "Installing dependencies..."
apt update && apt upgrade -y
apt install -y python3 python3-pip git

echo "Creating application directory..."
mkdir -p /opt/wigle-server
cd /opt/wigle-server

echo "Cloning repository..."
git clone https://github.com/lozaning/diywigle.git .

echo "Installing Python packages..."
pip3 install flask flask-sqlalchemy --break-system-packages

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

[Install]
WantedBy=multi-user.target
EOF

echo "Starting service..."
systemctl daemon-reload
systemctl enable wigle-server.service
systemctl start wigle-server.service

echo "Deployment complete!"
echo "Access at: http://$(hostname -I | awk '{print $1}'):5001"
echo "Login: lozaning / oneill"
```

Make executable and run:
```bash
chmod +x setup.sh
./setup.sh
```
