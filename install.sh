#!/usr/bin/env bash
set -Eeuo pipefail

BRAND="Digital Asphalt"
INSTALLER_VERSION="2026.05.11-prod"
REPO_URL="https://github.com/harnov-34/digitalasphalt.git"
WORKDIR="/tmp/digitalasphalt-install"
LICENSE_API="${LICENSE_API:-http://cbn.digitalasphalt.my.id:3559}"
CURL_TIMEOUT="${CURL_TIMEOUT:-20}"

cleanup() {
  rm -rf "$WORKDIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

die() {
  echo
  echo "[ERROR] $*" >&2
  exit 1
}

need_root() {
  [ "$(id -u)" -eq 0 ] || die "Installer wajib dijalankan sebagai root."
}

need_cmds() {
  for c in curl python3 tar gzip; do
    command -v "$c" >/dev/null 2>&1 || die "Command belum ada: $c"
  done
}

curl_get() {
  curl -fsSL \
    --connect-timeout 8 \
    --max-time "$CURL_TIMEOUT" \
    --retry 2 \
    --retry-delay 2 \
    --retry-connrefused \
    -H "Cache-Control: no-cache" \
    -H "Pragma: no-cache" \
    "$@"
}

get_public_ip() {
  local ip=""
  ip="$(curl_get https://api.ipify.org || true)"
  [ -n "$ip" ] || ip="$(curl_get https://ipv4.icanhazip.com | tr -d '[:space:]' || true)"
  [ -n "$ip" ] || ip="$(curl_get https://ifconfig.me | tr -d '[:space:]' || true)"
  echo "$ip"
}

validate_domain() {
  local d="$1"

  [[ "$d" =~ ^[A-Za-z0-9.-]+$ ]] || return 1
  [[ "$d" == *.* ]] || return 1
  [[ "$d" != .* && "$d" != *. ]] || return 1
  [[ "$d" != *..* ]] || return 1
  [[ ${#d} -le 253 ]] || return 1

  IFS='.' read -ra parts <<< "$d"
  for p in "${parts[@]}"; do
    [[ -n "$p" ]] || return 1
    [[ ${#p} -le 63 ]] || return 1
    [[ "$p" != -* && "$p" != *- ]] || return 1
  done

  return 0
}

save_domain() {
  local d="$1"
  mkdir -p /etc/digitalasphalt /etc/xray
  printf '%s\n' "$d" > /etc/digitalasphalt/domain
  printf '%s\n' "$d" > /etc/xray/domain
  chmod 644 /etc/digitalasphalt/domain /etc/xray/domain
}

is_trusted_owner_domain() {
  local d="${1:-}"
  case "$d" in
    nam.engineering|*.nam.engineering|digitalasphalt.my.id|*.digitalasphalt.my.id)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

internet_check() {
  echo "[INFO] Checking internet connectivity..."
  curl_get https://api.github.com >/dev/null || die "Internet/GitHub tidak bisa diakses."
  curl_get "${LICENSE_API}/health" >/dev/null 2>&1 || true
}

clear
echo "======================================"
echo "      DIGITAL ASPHALT INSTALLER"
echo "======================================"
echo "Version : ${INSTALLER_VERSION}"
echo

need_root
need_cmds
internet_check

read -rp "Domain VPS VPN : " DOMAIN
DOMAIN="$(echo "$DOMAIN" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
validate_domain "$DOMAIN" || die "Format domain tidak valid: $DOMAIN"

if is_trusted_owner_domain "$DOMAIN"; then
  LICENSE_CODE="OWNER-TRUSTED"
  OWNER_MODE=1
  echo "[OK] Trusted owner domain detected."
  echo "[INFO] License Code tidak diperlukan."
else
  read -rp "License Code   : " LICENSE_CODE
  LICENSE_CODE="$(echo "$LICENSE_CODE" | tr -d '[:space:]')"
  [ -n "$LICENSE_CODE" ] || die "License code kosong."
  OWNER_MODE=0
fi

IPVPS="$(get_public_ip)"
[ -n "$IPVPS" ] || die "Gagal deteksi public IPv4 VPS."

# Generate request metadata once and reuse for both owner and licensed flows.
NONCE="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
TS="$(date +%s)"

echo
echo "[INFO] Public IP : $IPVPS"
echo "[INFO] Domain    : $DOMAIN"
if [ "${OWNER_MODE:-0}" -eq 1 ]; then
  echo "[OK] Owner mode active."
  echo "[INFO] License verification skipped for trusted owner domain."
  TOKEN=""
else
  echo "[INFO] Checking license..."

  VERIFY_URL="${LICENSE_API}/verify?code=${LICENSE_CODE}&ip=${IPVPS}&domain=${DOMAIN}&ts=${TS}&nonce=${NONCE}"

  RESP="$(curl_get "$VERIFY_URL" || true)"
  [ -n "$RESP" ] || die "License server tidak merespon."

  OK="$(python3 - <<PY
import json,sys
try:
    r=json.loads("""$RESP""")
    print("1" if r.get("ok") is True else "0")
except Exception:
    print("0")
PY
)"

  [ "$OK" = "1" ] || die "License invalid / expired / tidak cocok IP-domain. Response: $RESP"

  TOKEN="$(python3 - <<PY
import json
r=json.loads("""$RESP""")
print(r.get("token",""))
PY
)"

  [ -n "$TOKEN" ] || die "Token bootstrap kosong dari license server."

  echo "[OK] License valid."
fi

echo "[INFO] Saving domain..."
save_domain "$DOMAIN"

echo "[INFO] Preparing workspace..."
rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"

if [ "${OWNER_MODE:-0}" -eq 1 ]; then
  echo "[INFO] Downloading owner core..."
  OWNER_URL="${LICENSE_API}/owner/core/install-core.sh?ip=${IPVPS}&domain=${DOMAIN}&ts=${TS}&nonce=${NONCE}"
  curl_get "$OWNER_URL" -o "$WORKDIR/install-core.sh"
else
  echo "[INFO] Download protected core..."
  CORE_URL="${LICENSE_API}/core/install-core.sh?token=${TOKEN}&ip=${IPVPS}&domain=${DOMAIN}&ts=${TS}&nonce=${NONCE}"
  curl_get "$CORE_URL" -o "$WORKDIR/install-core.sh"
fi

[ -s "$WORKDIR/install-core.sh" ] || die "Protected core kosong/gagal download."

chmod +x "$WORKDIR/install-core.sh"

echo "[INFO] Running protected core..."
LICENSE_CODE="$LICENSE_CODE" \
DA_CORE_TOKEN="$TOKEN" \
DA_LICENSE_URL="$LICENSE_API" \
DOMAIN="$DOMAIN" \
IPVPS="$IPVPS" \
BRAND="$BRAND" \
bash "$WORKDIR/install-core.sh"

echo
echo "======================================"
echo " DIGITAL ASPHALT INSTALL COMPLETE"
echo "======================================"
echo "Domain : $DOMAIN"
echo "IP     : $IPVPS"
echo "Run    : menu"
echo "======================================"
