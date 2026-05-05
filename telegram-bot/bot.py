#!/usr/bin/env python3
import os
import time
import json
import hmac
import hashlib, json, random, string, asyncio, re
from pathlib import Path
import httpx
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

BOT_TOKEN=os.getenv("BOT_TOKEN","")
ADMIN_ID=int(os.getenv("ADMIN_ID","0"))
BRAND=os.getenv("BRAND","DIGITAL ASPHALT")
DATA_DIR=Path(os.getenv("DATA_DIR","/opt/da-telegram-bot/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS=DATA_DIR/"users.json"
SERVERS=DATA_DIR/"servers.json"
ORDERS=DATA_DIR/"orders.json"
PAYMENTS=DATA_DIR/"payments.json"

PAYMENT_PROVIDER=os.getenv("PAYMENT_PROVIDER","")
IPAYMU_BASE_URL=os.getenv("IPAYMU_BASE_URL","https://my.ipaymu.com").rstrip("/")
IPAYMU_VA=os.getenv("IPAYMU_VA","")
IPAYMU_API_KEY=os.getenv("IPAYMU_API_KEY","")
IPAYMU_RETURN_URL=os.getenv("IPAYMU_RETURN_URL","https://cbn.digitalasphalt.my.id/payment/success")
IPAYMU_CANCEL_URL=os.getenv("IPAYMU_CANCEL_URL","https://cbn.digitalasphalt.my.id/payment/cancel")
IPAYMU_NOTIFY_URL=os.getenv("IPAYMU_NOTIFY_URL","https://cbn.digitalasphalt.my.id/payment/ipaymu/callback")


PROTOS=["SSH","VMESS","VLESS","TROJAN","ZIVPN"]
PLANS={
 "15": {"days":15, "price":4995, "ip":2, "quota":150},
 "30": {"days":30, "price":9990, "ip":2, "quota":250},
 "TRIAL": {"days":1, "price":0, "ip":2, "quota":10},
}

def load(p, default):
    if not p.exists():
        p.write_text(json.dumps(default, indent=2))
    try:
        return json.loads(p.read_text())
    except:
        return default

def save(p,d):
    p.write_text(json.dumps(d, indent=2))

def clean_output(text):
    text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)
    text = re.sub(r"Warning: Permanently added .*known hosts\.\n?", "", text)
    for x in ["[0m","[0;32m","[0;36m","[1;33m"]:
        text = text.replace(x,"")
    text = text.replace("\r","")

    stop_words=[
        "DIGITAL ASPHALT SCRIPT","Select menu","Invalid option",
        "OS      :","RAM     :","LOAD AVG:","UPTIME  :",
        "NGINX:[","VERSION","SCRIPT BY","WEBSITE","YOUTUBE","TELEGRAM",
    ]

    lines=[]
    for line in text.splitlines():
        if any(w in line for w in stop_words):
            break
        if line.strip():
            lines.append(line.rstrip())

    return "\n".join(lines).strip() or "Account created, tapi output kosong."

def rupiah(n):
    return f"{int(n):,}".replace(",",".")

def randuser(proto):
    return "da"+proto.lower()+''.join(random.choices(string.ascii_lowercase+string.digits,k=6))

def randpass():
    return ''.join(random.choices(string.ascii_letters+string.digits,k=10))

def get_user(uid, name=""):
    db=load(USERS,{})
    sid=str(uid)
    if sid not in db:
        db[sid]={"id":uid,"name":name,"saldo":0,"accounts":[],"trials":{}}
        save(USERS,db)
    return db[sid], db


def server_flag(label):
    x = (label or "").upper()
    if "INDONESIA" in x or "TELKOM" in x or "ID-" in x:
        return "🇮🇩"
    if "SINGAPORE" in x or "SG-" in x:
        return "🇸🇬"
    if "USA" in x or "UNITED STATES" in x or "US-" in x:
        return "🇺🇸"
    if "JAPAN" in x or "JP-" in x:
        return "🇯🇵"
    return "🌐"


def get_server_by_label(label):
    for srv in active_servers():
        if (srv.get("label") or srv.get("name") or "") == label:
            return srv
    return None

def live_zivpn_password(username, server_label):
    srv = get_server_by_label(server_label)
    if not srv:
        return None

    host = srv.get("host")
    port = str(srv.get("port") or srv.get("ssh_port") or 22)
    rootuser = srv.get("user") or srv.get("ssh_user") or "root"
    auth = srv.get("password") or srv.get("ssh_password") or srv.get("key") or "/root/.ssh/id_rsa"

    remote_cmd = (
        "awk -F':' -v u='" + username.replace("'", "'\\''") + "' "
        "'$1==u{print $2; exit}' /etc/zivpn/user.db 2>/dev/null"
    )

    if auth.startswith("/") or auth.startswith("~"):
        cmd = [
            "ssh", "-i", auth,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-p", port,
            f"{rootuser}@{host}",
            remote_cmd
        ]
    else:
        cmd = [
            "sshpass", "-p", auth,
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-p", port,
            f"{rootuser}@{host}",
            remote_cmd
        ]

    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=7)
        val = out.decode(errors="ignore").strip()
        return val or None
    except Exception:
        return None

def active_servers():
    return [s for s in load(SERVERS,[]) if s.get("active",True)]

async def start(update:Update, context:ContextTypes.DEFAULT_TYPE):
    u=update.effective_user
    user,db=get_user(u.id,u.first_name or "")
    acc=len(user.get("accounts",[]))
    text=f"""👋 Halo {u.first_name}
━━━━━━━━━━━━━━━━━━━━
💰 Saldo: Rp {rupiah(user.get('saldo',0))}
📦 Active Accounts: {acc}

🚀 Selamat datang di *BOT AUTO ORDER DIGITAL ASPHALT*

Untuk melakukan transaksi silakan topup saldo terlebih dahulu.
Setelah saldo terisi, kamu bisa langsung membeli layanan VPN secara otomatis.

Pilih layanan:"""
    kb=[]
    for i in range(0, len(PROTOS), 2):
        row=[]
        for p in PROTOS[i:i+2]:
            row.append(InlineKeyboardButton(f"🛒 BUY {p}", callback_data=f"proto:{p}"))
        kb.append(row)
    kb.append([
        InlineKeyboardButton("💰 TOPUP SALDO", callback_data="topup"),
        InlineKeyboardButton("📦 AKUN SAYA", callback_data="my_accounts")
    ])
    kb.append([InlineKeyboardButton("📞 ADMIN", url="https://t.me/d_asphalt")])
    await update.message.reply_text(text,parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(kb))

async def cb(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    try:
        await q.answer()
    except:
        pass

    uid=q.from_user.id
    user,db=get_user(uid,q.from_user.first_name or "")
    data=q.data


    if data == "topup":
        uid = update.effective_user.id

        kb = [
            [InlineKeyboardButton("💵 Rp 5.000", callback_data="topup_nominal:5000")],
            [InlineKeyboardButton("💵 Rp 10.000", callback_data="topup_nominal:10000")],
            [InlineKeyboardButton("💵 Rp 25.000", callback_data="topup_nominal:25000")],
            [InlineKeyboardButton("💵 Rp 50.000", callback_data="topup_nominal:50000")],
            [InlineKeyboardButton("💵 Rp 100.000", callback_data="topup_nominal:100000")],
            [InlineKeyboardButton("⬅️ Kembali", callback_data="back_start")],
        ]

        await q.message.edit_text(
            "💰 TOPUP SALDO DIGITAL ASPHALT\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Pilih nominal topup.\n\n"
            "Invoice otomatis via iPaymu.\n"
            "Saldo masuk otomatis setelah bayar.\n\n"
            f"User ID kamu: {uid}",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return


    if data.startswith("topup_nominal:"):
        amount = int(data.split(":")[1])
        uid = str(q.from_user.id)
        name = q.from_user.first_name or ""

        if amount < 5000:
            await q.message.edit_text("Minimal topup Rp 5.000")
            return

        pdb = payment_load()
        now = int(time.time())
        EXPIRE = 1800

        for ref, trx in pdb.items():
            if str(trx.get("uid")) != uid:
                continue
            if trx.get("status") != "PENDING":
                continue

            created = int(trx.get("created", 0))
            if created and now - created > EXPIRE:
                trx["status"] = "EXPIRED"
                continue

            pay_url = trx.get("pay_url", "")

            msg = (
                f"⚠️ Kamu masih punya invoice PENDING\n\n"
                f"Ref: `{ref}`\n"
                f"Nominal: Rp {rupiah(trx.get('amount',0))}\n\n"
            )

            if pay_url:
                msg += f"{pay_url}\n\n"

            msg += f"/cekbayar {ref}"

            await q.message.edit_text(msg, parse_mode="Markdown")
            payment_save(pdb)
            return

        ref, data = await ipaymu_create_payment(uid, name, amount)

        ddata = data.get("Data") if isinstance(data.get("Data"), dict) else {}
        pay_url = ddata.get("Url") or ddata.get("url") or data.get("Url") or data.get("url")

        pdb[ref] = {
            "ref": ref,
            "uid": uid,
            "amount": amount,
            "status": "PENDING",
            "gateway": "ipaymu",
            "pay_url": pay_url or "",
            "raw": data,
            "created": int(time.time()),
        }

        payment_save(pdb)

        if not pay_url:
            await q.message.edit_text("Gagal buat invoice")
            return

        await q.message.edit_text(
            "✅ Invoice topup berhasil dibuat.\n\n"
            f"Ref: `{ref}`\n"
            f"Nominal: Rp {rupiah(amount)}\n\n"
            f"Bayar di link ini:\n{pay_url}\n\n"
            f"Setelah bayar, gunakan:\n/cekbayar {ref}",
            parse_mode="Markdown"
        )
        return




    if data == "back_start":
        await start(update, context)
        return

    if data == "my_accounts":
        accs = user.get("accounts", [])
        if not accs:
            await q.message.reply_text("📦 AKUN SAYA\n━━━━━━━━━━━━━━━━━━━━\nBelum ada akun aktif.")
            return

        accounts = accs

        txt = "📦 *AKUN SAYA*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, a in enumerate(accounts, 1):
            service = str(a.get("service", "VPN")).upper()
            server = a.get("server") or a.get("server_label") or "-"
            username = a.get("password") or a.get("pass") or a.get("username") or "-"
            if service == "ZIVPN":
                username = live_zivpn_password(a.get("username", ""), server) or username
            domain = a.get("domain") or "telkom.nam.engineering"
            days = str(a.get("days") or a.get("expired") or "-")

            if days.isdigit():
                expired = f"{days} Hari Lagi"
            elif "jam" in days.lower():
                expired = days.replace("jam", "Jam").replace("lagi", "Lagi")
            else:
                expired = days

            txt += (
                f"{i}. 🟢 *{service}*\n"
                f"👤 Password : `{username}`\n"
                f"🌐 Domain   : `{domain}`\n"
                f"🖥️ Server   : *{server}*\n"
                f"⏳ Expired  : *{expired}*\n\n"
            )
        await q.message.reply_text(txt[:3900], parse_mode="Markdown")
        return

    
    if data == "paid":
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text="💰 REQUEST TOPUP\nUser: " + str(uid)
        )
        await q.message.reply_text("⏳ Menunggu konfirmasi admin...")
        return

    if data.startswith("proto:"):
        proto=data.split(":",1)[1]
        servers=active_servers()
        if not servers:
            await q.edit_message_text("❌ Server belum tersedia. Admin harus /addserver dulu.")
            return
        kb=[]
        for i,srv in enumerate(servers):
            label=srv.get("label",srv.get("name","SERVER"))
            kb.append([InlineKeyboardButton(f"{server_flag(label)} {label}", callback_data=f"server:{proto}:{i}")])
        await q.edit_message_text(f"🌐 Pilih server untuk *{proto}*:",parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("server:"):
        _,proto,idx=data.split(":")
        idx=int(idx)
        servers=active_servers()
        if idx>=len(servers):
            await q.edit_message_text("❌ Server tidak valid.")
            return
        trial_label = "🎁 Trial 2 Jam" if proto == "ZIVPN" else "🎁 Trial 1 Hari"
        kb=[
            [InlineKeyboardButton(trial_label, callback_data=f"buy:{proto}:{idx}:TRIAL")],
            [InlineKeyboardButton("👥 2 IP / 150GB - 15 Hari - Rp 4.995", callback_data=f"buy:{proto}:{idx}:15")],
            [InlineKeyboardButton("👥 2 IP / 250GB - 30 Hari - Rp 9.990", callback_data=f"buy:{proto}:{idx}:30")],
        ]
        await q.edit_message_text(f"📦 Pilih paket *{proto}*:",parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("buy:"):
        _,proto,idx,plan_id=data.split(":")
        idx=int(idx)
        plan=PLANS[plan_id]
        servers=active_servers()
        srv=servers[idx]

        if plan["price"] > 0 and user.get("saldo",0) < plan["price"]:
            await q.edit_message_text(f"❌ Saldo kurang.\nSaldo kamu: Rp {rupiah(user.get('saldo',0))}\nHarga: Rp {rupiah(plan['price'])}")
            return

        username=randuser(proto)
        password=randpass()

        await q.edit_message_text("⏳ Membuat akun, tunggu sebentar...")

        auth=srv.get("key") or srv.get("password") or srv.get("ssh_password") or "/root/.ssh/id_rsa"
        host=srv.get("host")
        port=str(srv.get("port") or srv.get("ssh_port") or 22)
        rootuser=srv.get("user") or srv.get("ssh_user") or "root"

        cmd=[
            "/opt/da-telegram-bot/bin/da-bot-create-remote",
            host, port, rootuser, auth,
            proto.lower(), username, password,
            ("TRIAL2H" if proto == "ZIVPN" and plan_id == "TRIAL" else str(plan["days"])), str(plan["ip"]), str(plan["quota"])
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            stdout, _ = await proc.communicate()
            out = stdout.decode(errors="ignore")
        except Exception as e:
            await q.edit_message_text("❌ Error:\n\n"+str(e))
            return

        if proc.returncode != 0:
            await q.edit_message_text("❌ Gagal membuat akun:\n\n"+clean_output(out)[-3500:])
            return

        if plan["price"] > 0:
            user["saldo"]=int(user.get("saldo",0))-plan["price"]

        label=srv.get("label") or srv.get("name") or "SERVER"
        user.setdefault("accounts",[]).append({
            "service":proto,
            "username":username,
            "password":password,
            "server":label,
            "days":("2 Jam" if proto == "ZIVPN" and plan_id == "TRIAL" else plan["days"]),
            "created":datetime.now().isoformat()
        })
        db[str(uid)]=user
        save(USERS,db)

        orders=load(ORDERS,[])
        orders.append({"uid":uid,"proto":proto,"server":label,"username":username,
            "password":password,"plan":plan_id,"time":datetime.now().isoformat()})
        save(ORDERS,orders)

        out=clean_output(out)
        await q.edit_message_text(f"✅ *{proto} Account Created*\n\n```{out[-3500:]}```",parse_mode="Markdown")
        return


def payment_load():
    return load(PAYMENTS, {})

def payment_save(db):
    save(PAYMENTS, db)



def get_pending_invoice(uid):
    pdb = payment_load()
    now = int(time.time())
    EXPIRE = 1800  # 30 menit

    for ref, trx in pdb.items():
        if trx.get("uid") == uid and trx.get("status") == "PENDING":
            created = trx.get("created", 0)

            # cek expired
            if now - created > EXPIRE:
                trx["status"] = "EXPIRED"
                continue

            return ref, trx

    payment_save(pdb)
    return None, None

def ipaymu_signature(method, endpoint, body_json):
    body_hash = hashlib.sha256(body_json.encode("utf-8")).hexdigest().lower()
    string_to_sign = f"{method.upper()}:{IPAYMU_VA}:{body_hash}:{IPAYMU_API_KEY}"
    return hmac.new(
        IPAYMU_API_KEY.encode("latin-1"),
        string_to_sign.encode("latin-1"),
        hashlib.sha256
    ).hexdigest()



def find_pending_invoice(uid):
    pdb = payment_load()
    now = int(time.time())
    expire_sec = 1800

    for ref, trx in list(pdb.items()):
        if str(trx.get("uid")) != str(uid):
            continue
        if str(trx.get("status", "")).upper() != "PENDING":
            continue

        created = int(trx.get("created", 0))
        if created and now - created > expire_sec:
            trx["status"] = "EXPIRED"
            pdb[ref] = trx
            payment_save(pdb)
            continue

        return ref, trx

    return None, None

async def ipaymu_create_payment(uid, name, amount):
    endpoint = "/api/v2/payment"
    ref = f"DA{uid}{int(time.time())}"
    payload = {
        "product": ["Topup Saldo Digital Asphalt"],
        "qty": ["1"],
        "price": [str(int(amount))],
        "description": ["Topup Saldo Digital Asphalt"],
        "returnUrl": IPAYMU_RETURN_URL,
        "cancelUrl": IPAYMU_CANCEL_URL,
        "notifyUrl": IPAYMU_NOTIFY_URL,
        "referenceId": ref
    }

    body = json.dumps(payload, separators=(",", ":"))
    sig = ipaymu_signature("POST", endpoint, body)
    headers = {
        "Content-Type": "application/json",
        "va": IPAYMU_VA,
        "signature": sig,
        "timestamp": time.strftime("%Y%m%d%H%M%S"),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(IPAYMU_BASE_URL + endpoint, content=body, headers=headers)
        txt = r.text
        try:
            data = r.json()
        except Exception:
            data = {"Status": 0, "Message": txt, "Data": None}

    return ref, data
async def topup(update:Update, context:ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    name = update.effective_user.first_name or ""

    if len(context.args) < 1:
        await update.message.reply_text("Format: /topup 10000")
        return

    try:
        amount = int(context.args[0])
    except Exception:
        await update.message.reply_text("Nominal harus angka.")
        return

    if amount < 5000:
        await update.message.reply_text("Minimal topup Rp 5.000")
        return

    pdb = payment_load()
    now = int(time.time())

    EXPIRE = 1800
    COOLDOWN = 20
    MAX_UNPAID_DAY = 3

    today = datetime.now().strftime("%Y-%m-%d")
    unpaid_today = 0
    last_created = 0

    for ref, trx in pdb.items():
        if str(trx.get("uid")) != uid:
            continue

        status = str(trx.get("status","PENDING")).upper()
        created = int(trx.get("created",0) or 0)

        if created > last_created:
            last_created = created

        trx_day = datetime.fromtimestamp(created).strftime("%Y-%m-%d") if created else ""

        # auto expire
        if status == "PENDING" and created and now - created > EXPIRE:
            trx["status"] = "EXPIRED"
            status = "EXPIRED"

        # masih pending
        if status == "PENDING":
            pay_url = trx.get("pay_url","")

            if not pay_url:
                raw = trx.get("raw",{})
                if isinstance(raw, dict):
                    ddata = raw.get("Data") if isinstance(raw.get("Data"), dict) else {}
                    pay_url = ddata.get("Url") or ddata.get("url") or raw.get("Url") or raw.get("url") or ""

            payment_save(pdb)

            msg = f"⚠️ Kamu masih punya invoice PENDING\n\nRef: `{ref}`\nNominal: Rp {rupiah(int(trx.get('amount',0)))}\n\n"

            if pay_url:
                msg += f"Bayar di sini:\n{pay_url}\n\n"

            msg += f"/cekbayar {ref}"

            await update.message.reply_text(msg, parse_mode="Markdown")
            return

        # hitung abuse
        if trx_day == today and status in ["EXPIRED","FAILED","CANCEL","CANCELED","CANCELLED"]:
            unpaid_today += 1

    payment_save(pdb)

    # cooldown
    if last_created and now - last_created < COOLDOWN:
        await update.message.reply_text(
            f"⏳ Tunggu {COOLDOWN - (now - last_created)} detik"
        )
        return

    # limit harian
    if unpaid_today >= MAX_UNPAID_DAY:
        await update.message.reply_text(
            "🚫 Limit invoice harian tercapai"
        )
        return

    if PAYMENT_PROVIDER != "ipaymu":
        await update.message.reply_text("Payment gateway belum aktif.")
        return

    if not IPAYMU_VA or not IPAYMU_API_KEY:
        await update.message.reply_text("Config iPaymu belum lengkap.")
        return

    ref, data = await ipaymu_create_payment(uid, name, amount)

    ddata = data.get("Data") if isinstance(data.get("Data"), dict) else {}
    pay_url = ddata.get("Url") or ddata.get("url") or data.get("Url") or data.get("url")

    pdb[ref] = {
        "ref": ref,
        "uid": uid,
        "amount": amount,
        "status": "PENDING",
        "gateway": "ipaymu",
        "pay_url": pay_url or "",
        "raw": data,
        "created": int(time.time()),
    }

    payment_save(pdb)

    if not pay_url:
        await update.message.reply_text(f"Gagal buat invoice\nRef: {ref}")
        return

    await update.message.reply_text(
        f"✅ Invoice dibuat\n\nRef: `{ref}`\nNominal: Rp {rupiah(amount)}\n\n{pay_url}",
        parse_mode="Markdown"
    )

async def cekbayar(update:Update, context:ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if len(context.args) < 1:
        await update.message.reply_text("Format: /cekbayar REF")
        return

    ref = context.args[0].strip()
    pdb = payment_load()
    trx = pdb.get(ref)

    if not trx:
        await update.message.reply_text("Invoice tidak ditemukan.")
        return

    if trx.get("uid") != uid and update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Invoice bukan milik kamu.")
        return

    await update.message.reply_text(
        f"Status invoice {ref}: {trx.get('status','PENDING')}\n"
        f"Nominal: Rp {rupiah(int(trx.get('amount',0)))}"
    )

async def addsaldo(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if len(context.args)<2:
        await update.message.reply_text("Format: /addsaldo USER_ID NOMINAL")
        return
    uid,amount=context.args[0],int(context.args[1])
    db=load(USERS,{})
    db.setdefault(uid,{"id":int(uid),"name":"","saldo":0,"accounts":[]})
    db[uid]["saldo"]=int(db[uid].get("saldo",0))+amount
    save(USERS,db)
    await update.message.reply_text(f"✅ Saldo user {uid} ditambah Rp {rupiah(amount)}")

async def addserver(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if len(context.args)<4:
        await update.message.reply_text("Format:\n/addserver LABEL HOST PORT PASSWORD_OR_KEY")
        return
    label,host,port,auth=context.args[0],context.args[1],int(context.args[2]),context.args[3]
    servers=load(SERVERS,[])
    servers=[s for s in servers if s.get("label")!=label]
    item={"label":label,"host":host,"port":port,"user":"root","active":True}
    if auth.startswith("/"):
        item["key"]=auth
    else:
        item["password"]=auth
    servers.append(item)
    save(SERVERS,servers)
    await update.message.reply_text(f"✅ Server ditambahkan: {label}")

async def listserver(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    servers=load(SERVERS,[])
    txt="🌐 LIST SERVER\n\n"
    for s in servers:
        txt+=f"- {s.get('label',s.get('name','SERVER'))} | {s.get('host')}:{s.get('port',s.get('ssh_port',22))}\n"
    await update.message.reply_text(txt or "Belum ada server.")

async def listuser(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    db=load(USERS,{})
    txt="👥 LIST USER BOT\n\n"
    for uid,u in db.items():
        txt+=f"{uid} | {u.get('name','-')} | Saldo Rp {rupiah(u.get('saldo',0))} | Akun {len(u.get('accounts',[]))}\n"
    await update.message.reply_text(txt[:3900] or "Kosong.")



async def get_photo_id(update, context):
    if not update.message or not update.message.photo:
        return

    photo = update.message.photo[-1]
    fid = photo.file_id

    await update.message.reply_text(
        "✅ QRIS PHOTO FILE_ID:\n\n"
        f"`{fid}`\n\n"
        "Copy file_id ini.",
        parse_mode="Markdown"
    )




async def approve(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) < 2:
        await update.message.reply_text("Format: /approve USER_ID NOMINAL")
        return

    uid = context.args[0]
    amount = int(context.args[1])

    db = load(USERS, {})
    db.setdefault(uid, {"id":int(uid),"name":"","saldo":0,"accounts":[]})
    db[uid]["saldo"] += amount
    save(USERS, db)

    await context.bot.send_message(
        chat_id=int(uid),
        text=f"✅ Topup berhasil! Saldo masuk Rp {amount:,}"
    )

    await update.message.reply_text("✅ Saldo berhasil ditambahkan")

def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("topup",topup))
    app.add_handler(CommandHandler("cekbayar",cekbayar))
    app.add_handler(MessageHandler(filters.PHOTO, get_photo_id))
    app.add_handler(CommandHandler("addsaldo",addsaldo))
    app.add_handler(CommandHandler("addserver",addserver))
    app.add_handler(CommandHandler("listserver",listserver))
    app.add_handler(CommandHandler("listuser",listuser))
    app.add_handler(CommandHandler("approve",approve))
    app.add_handler(CallbackQueryHandler(cb))
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
