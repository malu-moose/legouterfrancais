#!/usr/bin/env bash
# One-time VPS setup: nginx + HTTPS + firewall + fail2ban + auto security updates
# + SSH hardening, for legouterfrancais.com on Ubuntu (OVH).
#
# Run as: sudo bash setup-vps.sh
# Review each step before running on a production box.

set -euo pipefail

DOMAIN="legouterfrancais.com"
WWW_ROOT="/var/www/legouterfrancais"

if [[ $EUID -ne 0 ]]; then
  echo "Run this with sudo: sudo bash setup-vps.sh" >&2
  exit 1
fi

echo "==> Updating system packages"
apt-get update
apt-get upgrade -y

echo "==> Installing nginx, certbot, fail2ban, ufw, unattended-upgrades"
apt-get install -y nginx certbot python3-certbot-nginx fail2ban ufw unattended-upgrades

echo "==> Firewall: allow only SSH, HTTP, HTTPS"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> fail2ban for SSH brute-force protection"
cat > /etc/fail2ban/jail.local <<'EOF'
[sshd]
enabled = true
port = ssh
maxretry = 5
findtime = 10m
bantime = 1h
EOF
systemctl enable fail2ban
systemctl restart fail2ban

echo "==> Automatic security updates"
dpkg-reconfigure -f noninteractive unattended-upgrades

echo "==> SSH hardening (key-only login, no root login)"
SSHD_CONF=/etc/ssh/sshd_config
cp "$SSHD_CONF" "$SSHD_CONF.bak.$(date +%s)"
sed -i \
  -e 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' \
  -e 's/^#\?PermitRootLogin.*/PermitRootLogin no/' \
  -e 's/^#\?PubkeyAuthentication.*/PubkeyAuthentication yes/' \
  -e 's/^#\?X11Forwarding.*/X11Forwarding no/' \
  "$SSHD_CONF"
systemctl restart ssh

echo "==> Site directory"
mkdir -p "$WWW_ROOT"
chown -R www-data:www-data "$WWW_ROOT"

echo "==> nginx: HTTP-only config first (so certbot can issue the cert)"
cat > /etc/nginx/sites-available/legouterfrancais <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN} www.${DOMAIN};
    root ${WWW_ROOT};
    index index.html;
    location / { try_files \$uri \$uri/ =404; }
}
EOF
ln -sf /etc/nginx/sites-available/legouterfrancais /etc/nginx/sites-enabled/legouterfrancais
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "==> Requesting HTTPS certificate (requires DNS already pointing here)"
certbot --nginx -d "${DOMAIN}" -d "www.${DOMAIN}" --redirect --non-interactive --agree-tos -m contact@legouterfrancais.com

echo "==> Installing hardened nginx config with security headers"
cp "$(dirname "$0")/nginx/legouterfrancais.conf" /etc/nginx/sites-available/legouterfrancais
nginx -t
systemctl reload nginx

echo "==> Certbot auto-renewal check (systemd timer, installed by the certbot package)"
systemctl list-timers | grep certbot || true

echo "==> Done. Site should now be live at https://${DOMAIN}"
