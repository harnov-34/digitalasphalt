#!/usr/bin/env bash
set -euo pipefail

BRAND="Digital Asphalt"
REPO_URL="https://github.com/harnov-34/digitalasphalt.git"
WORKDIR="/root/digitalasphalt"
LICENSE_API="http://cbn.digitalasphalt.my.id:3559"

clear
echo "======================================"
echo "      DIGITAL ASPHALT INSTALLER"
echo "======================================"
echo

read -rp "Domain VPS VPN : " DOMAIN
read -rp "License Code   : " LICENSE_CODE

IPVPS=$(curl -s4 ifconfig.me || curl -s4 ipinfo.io/ip || true)

echo
echo "[INFO] Checking license..."
VERIFY_URL="${LICENSE_API}/verify?code=${LICENSE_CODE}&ip=${IPVPS}&domain=${DOMAIN}"
RESP=$(curl -fsSL "$VERIFY_URL" || true)

OK=$(python3 - <<PY
import json,sys
try:
    print(json.loads('''$RESP''').get("ok"))
except Exception:
    print("False")
PY
)

TOKEN=$(python3 - <<PY
import json,sys
try:
    print(json.loads('''$RESP''').get("token",""))
except Exception:
    print("")
PY
)

if [[ "$OK" != "True" || -z "$TOKEN" ]]; then
  echo "[ERROR] License invalid."
  echo "$RESP"
  exit 1
fi

echo "[OK] License valid."

export DOMAIN
export DA_DOMAIN="$DOMAIN"
export LICENSE_CODE
export DA_LICENSE_TOKEN="$TOKEN"

echo "[INFO] Installing dependencies..."
apt update
DEBIAN_FRONTEND=noninteractive apt install -y git curl wget unzip jq python3 python3-pip nginx certbot net-tools socat cron fail2ban

echo "[INFO] Sync public repo..."
rm -rf "$WORKDIR"
git clone --depth=1 "$REPO_URL" "$WORKDIR"
cd "$WORKDIR"

echo "[INFO] Running public modules..."
if compgen -G "modules/*.sh" > /dev/null; then
  for m in modules/*.sh; do
    echo "[RUN] $m"
    bash "$m"
  done
fi

echo "[INFO] Installing private core..."
curl -fsSL "${LICENSE_API}/core/install-core.sh?token=${TOKEN}" -o /tmp/da-install-core.sh
chmod +x /tmp/da-install-core.sh
bash /tmp/da-install-core.sh

echo
echo "======================================"
echo " DIGITAL ASPHALT INSTALL COMPLETE"
echo "======================================"
echo "Domain : $DOMAIN"
echo "IP     : $IPVPS"
echo
echo "Run: menu"
