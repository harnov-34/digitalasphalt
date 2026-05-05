# 🚀 Digital Asphalt VPN Script

Digital Asphalt adalah **autoscript VPN premium** dengan sistem **license + private core + runtime protection**, dirancang untuk penggunaan production.

Repository ini **bukan full script**, hanya berisi:
- bootstrap installer
- public modules
- runtime guard

👉 Core logic & license system berjalan di server private

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
| ZIVPN  | UDP      | -   | Custom |
| SQUID  | Proxy    | 3128| -    |
| OpenVPN| TCP/UDP  | 1194| 2200 |

---

## 🚀 ZIVPN (UDP TUNNEL)

ZIVPN adalah fitur tambahan untuk koneksi berbasis UDP (lebih stabil untuk jaringan tertentu).

- ⚡ Mode UDP (low latency)
- 📶 Cocok untuk jaringan mobile / gaming
- 🔐 Terintegrasi dengan system license
- 🔄 Auto service management via systemd
- 🧩 Terhubung ke menu (`zivpn-menu`)

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
- Support Enhanced
- Support Wildcard

---

## 🔄 SYSTEM ARCHITECTURE

(PRIVATE CORE)
│
├── License Server
├── Core Validation
└── Private Core Logic

        ↓

VPS (VPN SERVER)
│
├── Xray (VMESS/VLESS/TROJAN)
├── SSH / Dropbear / WS
├── ZIVPN (UDP)
├── NGINX (Reverse Proxy)
└── WS Proxy (SSH WebSocket)


---

## 🧪 SUPPORTED OS

- Ubuntu 20 / 22 / 24
- Debian 10 / 11 / 12

---

## 🚀 INSTALL

Jalankan di VPS:

```bash
git clone https://github.com/harnov-34/digitalasphalt /root/digitalasphalt
cd /root/digitalasphalt
chmod +x install.sh
bash install.sh


## ⚠️ DISCLAIMER

Script ini dibuat untuk penggunaan legal & edukasi.  
Segala penyalahgunaan bukan tanggung jawab developer.
