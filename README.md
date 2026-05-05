# 🚀 Digital Asphalt VPN Script

Digital Asphalt adalah **autoscript VPN premium** dengan sistem **license + private core + runtime protection**, dirancang untuk penggunaan production.

Repository ini **bukan full script**, hanya berisi:
- bootstrap installer
- public modules
- runtime guard

👉 Core logic & license system berjalan di server private (VPS-CBN)

---

## 🔐 LICENSE SYSTEM (ANTI BYPASS)

Digital Asphalt menggunakan sistem proteksi berlapis:

- ✅ License check saat install  
- ✅ Runtime check ke server pusat  
- ✅ Token validation (anti edit manual)  
- ✅ Service guard (xray/nginx/dropbear/zivpn)  
- ✅ Menu & API guard  
- ✅ Remote disable dari server pusat  

👉 Jika license invalid:
- ❌ Menu tidak bisa dibuka  
- ❌ Service VPN gagal start  
- ❌ Semua akses di-block otomatis  

---

## ⚙️ SUPPORTED PROTOCOLS

### 🌐 Default Ports

| Service | Transport | TLS | NTLS |
|--------|----------|-----|------|
| VLESS  | gRPC     | 443 | -    |
| VLESS  | WebSocket| 443 | 80   |
| VMESS  | gRPC     | 443 | -    |
| VMESS  | WebSocket| 443 | 80   |
| TROJAN | gRPC     | 443 | -    |
| TROJAN | WebSocket| 443 | 80   |
| SSH    | WebSocket| 443 | 80   |
| SQUID  | Proxy    | 3128| -    |
| OpenVPN| TCP/UDP  | 1194| 2200 |

---

## 🧠 MULTI PATH & CUSTOM PATH

- VMESS / VLESS / TROJAN support:
  - /vmess
  - /vless
  - /trojan
- SSH WS support:
  - /ssh atau bebas (/anypath)
- Custom multi-path tersedia di port tertentu
- Support TLS & Non-TLS

---

## 🔄 SYSTEM ARCHITECTURE

VPS-CBN (PRIVATE CORE)
│
├── License Server (3559)
├── Core Validation (8806)
└── Private Core Logic

        ↓

VPS (VPN SERVER)
│
├── Xray (VMESS/VLESS/TROJAN)
├── SSH / Dropbear / WS
├── ZIVPN (UDP)
└── NGINX (Reverse Proxy)

        ↓

Client User

---

## 🧪 SUPPORTED OS

- Ubuntu 20 / 22 / 24
- Debian 10 / 11 / 12

---

## 🚀 INSTALL

Jalankan di VPS:

\`\`\`bash
git clone https://github.com/harnov-34/digitalasphalt /root/digitalasphalt
cd /root/digitalasphalt
chmod +x install.sh
bash install.sh
\`\`\`

---

## 📦 FEATURES

- Auto install full VPN stack
- License system (anti crack)
- Multi protocol support
- Account management system
- High performance (NGINX + XRAY)
- Modular installer (auto update)

---

## 🛠️ COMMANDS

\`\`\`bash
menu        # Main menu
da-health   # Check service status
da-update   # Update script
\`\`\`

---

## 🔒 SECURITY NOTE

- Script ini tidak full di GitHub  
- Core berjalan di server private  
- License wajib aktif untuk semua fungsi  

Tujuan:
- Anti sharing script  
- Anti bypass  
- Kontrol penuh dari server pusat  

---

## 📩 GET LICENSE

Untuk menggunakan script ini, wajib memiliki License Code.

---

## ⚠️ DISCLAIMER

Script ini dibuat untuk penggunaan legal & edukasi.  
Segala penyalahgunaan bukan tanggung jawab developer.
