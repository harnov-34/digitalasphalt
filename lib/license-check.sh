#!/usr/bin/env bash
set -euo pipefail

LICENSE_SERVER="${LICENSE_SERVER:-http://cbn.digitalasphalt.my.id:3559}"
LICENSE_FILE="/etc/digitalasphalt/license.json"
mkdir -p /etc/digitalasphalt

get_public_ip() {
  curl -4fsS https://api.ipify.org || curl -4fsS https://ipv4.icanhazip.com | tr -d '[:space:]'
}

get_domain() {
  if [[ -s /etc/xray/domain ]]; then
    cat /etc/xray/domain | head -n1
  elif [[ -s /etc/digitalasphalt/domain ]]; then
    cat /etc/digitalasphalt/domain | head -n1
  else
    hostname -f 2>/dev/null || hostname
  fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " DIGITAL ASPHALT LICENSE VERIFICATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

read -rp "Masukkan License Code: " LICENSE_CODE
[[ -z "$LICENSE_CODE" ]] && echo "License kosong." && exit 1

PUB_IP="$(get_public_ip)"
DOMAIN="$(get_domain)"

echo "IP VPS : $PUB_IP"
echo "Domain : $DOMAIN"
echo "Server : $LICENSE_SERVER"

RESP="$(curl -fsS --connect-timeout 10 --max-time 20 \
  "${LICENSE_SERVER}/verify?code=${LICENSE_CODE}&ip=${PUB_IP}&domain=${DOMAIN}" || true)"

if [[ -z "$RESP" ]]; then
  echo "Gagal konek ke license server."
  exit 1
fi

OK="$(echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("ok"))' 2>/dev/null || echo False)"

if [[ "$OK" != "True" ]]; then
  echo "LICENSE DENIED:"
  echo "$RESP"
  exit 1
fi

echo "$RESP" > "$LICENSE_FILE"
chmod 600 "$LICENSE_FILE"

echo "License OK."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
