#!/usr/bin/env bash
# Pi-PM VPS baseline provisioning — Ubuntu (Hostinger KVM4 srv1733992).
# Run ONCE on a fresh box as root (or via sudo -E). Review before running.
#
#   DEPLOY_USER=pipm SSH_PORT=22 bash provision.sh
#
# Does: system update, IST timezone, swap, deploy user, Docker Engine +
# compose plugin, UFW (22 + 80 only), fail2ban, /opt/pi-pm layout.
# Does NOT disable root/password SSH automatically (avoids lockout) — do
# that manually once key-based login for the deploy user is confirmed.
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-pipm}"
SSH_PORT="${SSH_PORT:-22}"

echo "==> System update"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get full-upgrade -y

echo "==> Timezone -> Asia/Kolkata (IST; matches NSE post-close batch)"
timedatectl set-timezone Asia/Kolkata || true

echo "==> Base packages"
apt-get install -y ca-certificates curl gnupg ufw fail2ban git rsync

echo "==> Swap (4G) if absent"
if ! swapon --show | grep -q '/swapfile'; then
  fallocate -l 4G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "==> Deploy user: ${DEPLOY_USER}"
if ! id "${DEPLOY_USER}" &>/dev/null; then
  adduser --disabled-password --gecos "" "${DEPLOY_USER}"
  usermod -aG sudo "${DEPLOY_USER}"
fi

echo "==> Docker Engine + compose plugin"
install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
fi
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker "${DEPLOY_USER}"
systemctl enable --now docker

echo "==> Firewall (UFW): allow SSH(${SSH_PORT}) + HTTP(80) only"
ufw allow "${SSH_PORT}/tcp"
ufw allow 80/tcp
ufw --force enable
ufw status verbose

echo "==> fail2ban"
systemctl enable --now fail2ban

echo "==> /opt/pi-pm layout"
install -d -o "${DEPLOY_USER}" -g "${DEPLOY_USER}" \
  /opt/pi-pm /opt/pi-pm/releases /opt/pi-pm/shared /opt/pi-pm/shared/backups

cat <<EOF

==> Provisioning complete.
Next steps (as ${DEPLOY_USER}):
  1. scp deploy/.env.api.example -> /opt/pi-pm/shared/.env  (fill CHANGE_ME, chmod 600)
  2. scp deploy/.env.web.example -> /opt/pi-pm/shared/.env.web
  3. scp the release tarball (+ .sha256) and the DB dump to /opt/pi-pm/shared/
  4. bash <release>/deploy/scripts/deploy.sh /opt/pi-pm/shared/pi-pm-<tag>.tar.gz
  5. bash <release>/deploy/scripts/restore_db.sh /opt/pi-pm/shared/backups/pipm-<stamp>.dump
SECURITY TODO (manual, after confirming key login): disable root SSH +
password auth in /etc/ssh/sshd_config, then 'systemctl reload ssh'.
EOF
