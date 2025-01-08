#!/bin/bash

# Variables
NODE_EXPORTER_VERSION="1.6.1" # Replace with the latest version if needed
NODE_EXPORTER_USER="prometheus"
NODE_EXPORTER_PORT="9100"
CENTRAL_PROM_SERVER="65.21.206.81"

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

# Update the system
# echo "Updating the system..."
# apt update && apt upgrade -y

# Download Node Exporter
echo "Downloading Node Exporter version $NODE_EXPORTER_VERSION..."
wget https://github.com/prometheus/node_exporter/releases/download/v$NODE_EXPORTER_VERSION/node_exporter-$NODE_EXPORTER_VERSION.linux-amd64.tar.gz -O /tmp/node_exporter.tar.gz

# Extract Node Exporter and move to /usr/local/bin
echo "Installing Node Exporter..."
tar -xvf /tmp/node_exporter.tar.gz -C /tmp/
mv /tmp/node_exporter-$NODE_EXPORTER_VERSION.linux-amd64/node_exporter /usr/local/bin/
rm -rf /tmp/node_exporter-$NODE_EXPORTER_VERSION.linux-amd64 /tmp/node_exporter.tar.gz

# Create the prometheus user
echo "Creating user: $NODE_EXPORTER_USER..."
id -u $NODE_EXPORTER_USER &>/dev/null || useradd -rs /bin/false $NODE_EXPORTER_USER

# Create the systemd service file
echo "Creating systemd service file..."
cat <<EOF > /etc/systemd/system/node_exporter.service
[Unit]
Description=Prometheus Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=$NODE_EXPORTER_USER
Group=$NODE_EXPORTER_USER
Type=simple
ExecStart=/usr/local/bin/node_exporter --web.listen-address=:$NODE_EXPORTER_PORT

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start Node Exporter
echo "Starting Node Exporter..."
systemctl daemon-reload
systemctl start node_exporter
systemctl enable node_exporter

# Check if Node Exporter is running
if systemctl is-active --quiet node_exporter; then
  echo "Node Exporter installed and running on port $NODE_EXPORTER_PORT."
else
  echo "Node Exporter installation failed. Check the service status using 'systemctl status node_exporter'."
  exit 1
fi

# Configure UFW to allow access to Node Exporter from central Prometheus server
echo "Configuring UFW to allow access on port $NODE_EXPORTER_PORT from $CENTRAL_PROM_SERVER..."
ufw allow from $CENTRAL_PROM_SERVER to any port $NODE_EXPORTER_PORT comment "Allow Prometheus scraping"
ufw reload

echo "UFW rule added. Only $CENTRAL_PROM_SERVER can access port $NODE_EXPORTER_PORT."