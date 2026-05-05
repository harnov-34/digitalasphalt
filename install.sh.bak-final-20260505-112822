#!/usr/bin/env bash
set -euo pipefail

LICENSE_API="http://cbn.digitalasphalt.my.id:3559"
WORK="/tmp/digitalasphalt-install"
CORE="$WORK/da-core.tar.gz"

clear
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "        DIGITAL ASPHALT INSTALLER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

read -rp "License Code : " CODE
read -rp "Domain       : " DOMAIN

mkdir -p "$WORK"

echo
echo "[INFO] DOMAIN : $DOMAIN"
echo "[INFO] Checking license..."

RESP="$(curl -s "$LICENSE_API/verify?code=$CODE&domain=$DOMAIN")"
OK="$(echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("ok"))' 2>/dev/null || echo false)"

if [[ "$OK" != "True" && "$OK" != "true" ]]; then
  echo "[ERROR] License invalid."
  echo "$RESP"
  exit 1
fi

TOKEN="$(echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')"

echo "[OK] License valid"
echo "[INFO] Downloading core..."

curl -fL "$LICENSE_API/core?token=$TOKEN" -o "$CORE"

echo "[INFO] Extracting core..."
tar -xzf "$CORE" -C /

echo "[INFO] Running core installer..."

if [[ -x /digitalasphalt-compiled/install.sh ]]; then
  cd /digitalasphalt-compiled
  printf "%s\n" "$CODE" | ./install.sh "$DOMAIN"
else
  echo "[ERROR] Core installer not found."
  exit 1
fi

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "INSTALLATION SUCCESS"
echo "Run: menu"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
