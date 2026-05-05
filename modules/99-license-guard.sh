#!/usr/bin/env bash
set -euo pipefail

CORE_URL="${CORE_URL:-http://cbn.digitalasphalt.my.id:8806/core/check}"
LICENSE_FILE="/etc/digitalasphalt/license.json"

echo "[INFO] Installing Digital Asphalt runtime license guard..."

apt-get update -y >/dev/null 2>&1 || true
apt-get install -y jq curl >/dev/null 2>&1 || true

mkdir -p /etc/digitalasphalt

tee /usr/local/sbin/da-license-check > /dev/null <<EOF
#!/usr/bin/env bash
set -euo pipefail

CORE_URL="${CORE_URL}"
LICENSE_FILE="${LICENSE_FILE}"

fail() {
  echo "❌ DIGITAL ASPHALT LICENSE BLOCKED: \$*" >&2
  exit 1
}

[[ -s "\$LICENSE_FILE" ]] || fail "license file missing"

code="\$(jq -r '.code // empty' "\$LICENSE_FILE" 2>/dev/null || true)"
token="\$(jq -r '.token // empty' "\$LICENSE_FILE" 2>/dev/null || true)"

domain="\$(
  if [[ -s /etc/xray/domain ]]; then head -n1 /etc/xray/domain
  elif [[ -s /etc/digitalasphalt/domain ]]; then head -n1 /etc/digitalasphalt/domain
  else hostname -f 2>/dev/null || hostname
  fi
)"

ip="\$(curl -4fsS --max-time 8 https://api.ipify.org || true)"

[[ -n "\$code" ]] || fail "empty license code"
[[ -n "\$token" ]] || fail "empty license token"
[[ -n "\$ip" ]] || fail "cannot get public IP"
[[ -n "\$domain" ]] || fail "empty domain"

resp="\$(curl -fsS --max-time 12 --get "\$CORE_URL" \
  --data-urlencode "code=\$code" \
  --data-urlencode "ip=\$ip" \
  --data-urlencode "domain=\$domain" \
  --data-urlencode "token=\$token" || true)"

echo "\$resp" | grep -Eq '"ok"[[:space:]]*:[[:space:]]*true' || fail "\$resp"

exit 0
EOF

chmod +x /usr/local/sbin/da-license-check

# inject guard ke script penting
for f in \
  /usr/local/sbin/menu \
  /usr/local/sbin/da-api \
  /usr/local/sbin/ssh-create \
  /usr/local/sbin/vmess-create.sh \
  /usr/local/sbin/vless-create.sh \
  /usr/local/sbin/trojan-create.sh \
  /usr/local/sbin/zivpn-menu
do
  [[ -f "$f" ]] || continue
  grep -q "da-license-check" "$f" && continue
  cp -a "$f" "$f.bak-license-guard-$(date +%Y%m%d-%H%M%S)" || true

  python3 - "$f" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(errors="ignore")
guard = 'command -v da-license-check >/dev/null 2>&1 && da-license-check || exit 1'

if "da-license-check" in s:
    raise SystemExit

lines = s.splitlines()
if lines and lines[0].startswith("#!"):
    lines.insert(1, guard)
else:
    lines.insert(0, guard)

p.write_text("\n".join(lines) + "\n")
PY

  chmod +x "$f" || true
done

# systemd guard service penting
for svc in xray nginx dropbear zivpn da-ws-proxy; do
  systemctl cat "$svc" >/dev/null 2>&1 || continue
  mkdir -p "/etc/systemd/system/${svc}.service.d"

  tee "/etc/systemd/system/${svc}.service.d/10-license-guard.conf" > /dev/null <<'EOF'
[Service]
ExecStartPre=/usr/local/sbin/da-license-check
EOF
done

systemctl daemon-reload || true

echo "[OK] Runtime license guard installed."
