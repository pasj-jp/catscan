#!/bin/bash
set -e

# ==============================================================================
# CatScan Deployment Script for Linux / AlmaLinux / RHEL
# ==============================================================================
# Configurable Environment Variables:
#   INDICO_BASE_URL   : Base URL of Indico server (default: http://127.0.0.1)
#   INDICO_API_TOKEN  : Indico API bearer token (default: empty / must be configured)
#   CATSCAN_BASE_URL  : Public Web URL for CatScan frontend (default: http://localhost:3000)
#   REPORTS_DIR       : Directory for validation reports (default: /opt/catscan/data/reports)
#   DEPLOY_ARCHIVE    : Path to deployment tarball (default: /tmp/catscan_deploy.tar.gz)
# ==============================================================================

INDICO_BASE_URL="${INDICO_BASE_URL:-https://127.0.0.1}"
INDICO_API_TOKEN="${INDICO_API_TOKEN:-}"
CATSCAN_BASE_URL="${CATSCAN_BASE_URL:-http://localhost:3000}"
CATSCAN_INTERNAL_TOKEN="${CATSCAN_INTERNAL_TOKEN:-}"
CATSCAN_API_PORT="${CATSCAN_API_PORT:-8001}"
REPORTS_DIR="${REPORTS_DIR:-/opt/catscan/data/reports}"
DEPLOY_ARCHIVE="${DEPLOY_ARCHIVE:-/tmp/catscan_deploy.tar.gz}"

echo "=== 1. Creating catscan user & directories ==="
if ! id -u catscan >/dev/null 2>&1; then
    useradd -r -m -d /opt/catscan -s /sbin/nologin catscan
fi
usermod -a -G nginx catscan || true
usermod -a -G catscan nginx || true

mkdir -p "$REPORTS_DIR" /opt/catscan/etc
if [ -f "$DEPLOY_ARCHIVE" ]; then
    echo "Extracting $DEPLOY_ARCHIVE to /opt/catscan..."
    tar -xzf "$DEPLOY_ARCHIVE" -C /opt/catscan/
fi

chown -R catscan:nginx /opt/catscan
chmod 750 /opt/catscan
chmod 700 /opt/catscan/etc
if [ -d "/opt/catscan/frontend" ]; then
    chmod 755 /opt/catscan/frontend
    [ -d "/opt/catscan/frontend/dist" ] && chmod -R 755 /opt/catscan/frontend/dist
fi
chmod -R 770 /opt/catscan/data 2>/dev/null || true

echo "=== 2. Setting up Python virtual environment ==="
if [ ! -d "/opt/catscan/.venv" ]; then
    sudo -u catscan python3 -m venv /opt/catscan/.venv
fi
sudo -u catscan /opt/catscan/.venv/bin/pip install --upgrade pip
sudo -u catscan /opt/catscan/.venv/bin/pip install /opt/catscan/backend

echo "=== 3. Writing environment file & systemd service for CatScan ==="
cat << EOF > /opt/catscan/etc/catscan.env
INDICO_BASE_URL=${INDICO_BASE_URL}
INDICO_API_TOKEN=${INDICO_API_TOKEN}
CATSCAN_BASE_URL=${CATSCAN_BASE_URL}
CATSCAN_INTERNAL_TOKEN=${CATSCAN_INTERNAL_TOKEN}
REPORTS_DIR=${REPORTS_DIR}
EOF
chown catscan:catscan /opt/catscan/etc/catscan.env
chmod 600 /opt/catscan/etc/catscan.env

cat << EOF > /etc/systemd/system/catscan.service
[Unit]
Description=CatScan Paper Validation Backend Service
After=network.target indico-uwsgi.service
Wants=indico-uwsgi.service

[Service]
Type=simple
User=catscan
Group=nginx
WorkingDirectory=/opt/catscan
EnvironmentFile=/opt/catscan/etc/catscan.env
ExecStart=/opt/catscan/.venv/bin/uvicorn catscan.main:app --host 127.0.0.1 --port ${CATSCAN_API_PORT}
Restart=always
RestartSec=5s
PrivateTmp=true
ProtectSystem=full
NoNewPrivileges=true
StandardOutput=journal
StandardError=journal
SyslogIdentifier=catscan

[Install]
WantedBy=multi-user.target
EOF

echo "=== 4. Writing Nginx reverse proxy configuration for CatScan ==="
cat << EOF > /etc/nginx/conf.d/catscan.conf
server {
    listen 3000;
    listen [::]:3000;
    server_name _;

    access_log /var/log/nginx/catscan_access.log combined;
    error_log /var/log/nginx/catscan_error.log;

    location / {
        root /opt/catscan/frontend/dist;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    location ^~ /api/indico/ {
        return 403;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:${CATSCAN_API_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        client_max_body_size 50M;
    }
}
EOF

echo "=== 5. Enabling and starting CatScan systemd service ==="
systemctl daemon-reload
systemctl enable catscan.service
systemctl restart catscan.service

echo "=== 6. Validating and reloading Nginx ==="
nginx -t
systemctl reload nginx

echo "=== 7. Service Verification ==="
sleep 2
systemctl status catscan.service --no-pager
curl -s "http://127.0.0.1:${CATSCAN_API_PORT}/api/health" || true
echo ""
echo "=== CatScan Deployment Finished Successfully! ==="
