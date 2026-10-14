#!/usr/bin/env bash
# Baseline security hardening for the VPS that will host the future
# login-protected production app / intranet (on app.legouterfrancais.com).
#
# Does NOT install nginx/Certbot/a site yet — nothing is served publicly
# until the app exists. Re-run is safe (idempotent-ish).
#
# Run as: sudo bash harden-vps.sh

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run this with sudo: sudo bash harden-vps.sh" >&2
  exit 1
fi

echo "==> Updating system packages"
apt-get update
apt-get upgrade -y

echo "==> Installing fail2ban, ufw, unattended-upgrades"
apt-get install -y fail2ban ufw unattended-upgrades

echo "==> Firewall: SSH only for now (open 80/443 later, when the app ships)"
ufw allow OpenSSH
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

echo "==> Done. Baseline hardening applied:"
echo "    - only SSH is open on the firewall (ufw status: $(ufw status | head -1))"
echo "    - fail2ban watching sshd"
echo "    - password SSH login disabled, root login disabled"
echo "    - automatic security updates enabled"
echo ""
echo "Next: when the intranet app is ready, see deploy/README.md section"
echo "'Déploiement futur : app.legouterfrancais.com' to open 80/443 and set"
echo "up nginx + Certbot + auth in front of it."
