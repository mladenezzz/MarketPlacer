#!/bin/bash

echo "=== Deploying DataCollector to Ubuntu Server ==="

# Create project directory
mkdir -p /opt/marketplacer
cd /opt/marketplacer

# Clone or pull repository
if [ -d ".git" ]; then
    echo "Updating repository..."
    git pull origin main
else
    echo "Cloning repository..."
    git clone https://github.com/mladenezzz/MarketPlacer.git .
fi

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create systemd service
sudo tee /etc/systemd/system/marketplacer-datacollector.service > /dev/null <<EOF
[Unit]
Description=MarketPlacer DataCollector Service
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/marketplacer
Environment="PATH=/opt/marketplacer/venv/bin"
ExecStart=/opt/marketplacer/venv/bin/python datacollector/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable marketplacer-datacollector
sudo systemctl start marketplacer-datacollector

echo "=== Deployment Complete ==="
echo "Check status: sudo systemctl status marketplacer-datacollector"
echo "View logs: sudo journalctl -u marketplacer-datacollector -f"
