#!/usr/bin/env python3
import os, json, random, string, asyncio, re
from pathlib import Path
from datetime import datetime
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
        db[sid]={"id":uid,"name":name,"saldo":0,"accounts":[]}
        save(USERS,db)
    return db[sid], db

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

        await q.message.reply_photo(
            photo="AgACAgUAAxkBAAIBf2n4Yr1YWYhX77fjKjM5TaqcUuNcAALpEGsbWBvBV3IvB1BgX4dfAQADAgADeQADOwQ",
            caption=(
                "💳 QRIS PAYMENT DIGITAL ASPHALT\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Scan QR di atas untuk bayar topup saldo.\n"
                "Setelah bayar WAJIB kirim screenshot ke admin.\n"
                "Admin: @d_asphalt\n\n"
                f"User ID: {uid}\n\nKirim bukti bayar ke admin: @d_asphalt"
            )
        )

        uid = update.effective_user.id
        kb = [
            [InlineKeyboardButton("💵 Rp 10.000", callback_data="topup_nominal:10000")],
            [InlineKeyboardButton("💵 Rp 25.000", callback_data="topup_nominal:25000")],
            [InlineKeyboardButton("💵 Rp 50.000", callback_data="topup_nominal:50000")],
            [InlineKeyboardButton("⬅️ Kembali", callback_data="back_start")],
        ]
        await q.message.edit_text(
            "💰 TOPUP SALDO DIGITAL ASPHALT\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Payment sementara manual.\n\n"
            "Pilih nominal topup, lalu bayar via QRIS/transfer admin.\n"
            "Setelah bayar WAJIB kirim screenshot ke admin.\n"
                "Admin: @d_asphalt\n\n"
            f"User ID kamu: {uid}",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    if data.startswith("topup_nominal:"):
        amount = int(data.split(":",1)[1])
        uid = update.effective_user.id
        await q.message.edit_text(
            "✅ INVOICE MANUAL TOPUP\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"Nominal : Rp {amount:,}\n"
            f"User ID : {uid}\n\n"
            "Silakan bayar via QRIS/transfer admin.\n"
            "Setelah bayar, kirim screenshot ke admin.\n\n"
            f"Format chat admin:\nTOPUP {amount} {uid}\n\n"
            "Saldo masuk setelah admin approve.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📩 Kirim SS ke Admin", url="https://t.me/d_asphalt")],
                [InlineKeyboardButton("⬅️ Kembali", callback_data="topup")]
            ])
        )
        return

    if data == "back_start":
        await start(update, context)
        return

    if data.startswith("proto:"):
        proto=data.split(":",1)[1]
        servers=active_servers()
        if not servers:
            await q.edit_message_text("❌ Server belum tersedia. Admin harus /addserver dulu.")
            return
        kb=[[InlineKeyboardButton(s.get("label",s.get("name","SERVER")), callback_data=f"server:{proto}:{i}")] for i,s in enumerate(servers)]
        await q.edit_message_text(f"🌐 Pilih server untuk *{proto}*:",parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("server:"):
        _,proto,idx=data.split(":")
        idx=int(idx)
        servers=active_servers()
        if idx>=len(servers):
            await q.edit_message_text("❌ Server tidak valid.")
            return
        kb=[
            [InlineKeyboardButton("🎁 Trial 1 Hari", callback_data=f"buy:{proto}:{idx}:TRIAL")],
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
            str(plan["days"]), str(plan["ip"]), str(plan["quota"])
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
            "server":label,
            "days":plan["days"],
            "created":datetime.now().isoformat()
        })
        db[str(uid)]=user
        save(USERS,db)

        orders=load(ORDERS,[])
        orders.append({"uid":uid,"proto":proto,"server":label,"username":username,"plan":plan_id,"time":datetime.now().isoformat()})
        save(ORDERS,orders)

        out=clean_output(out)
        await q.edit_message_text(f"✅ *{proto} Account Created*\n\n```{out[-3500:]}```",parse_mode="Markdown")
        return

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
    app.add_handler(MessageHandler(filters.PHOTO, get_photo_id))
    app.add_handler(CommandHandler("addsaldo",addsaldo))
    app.add_handler(CommandHandler("addserver",addserver))
    app.add_handler(CommandHandler("listserver",listserver))
    app.add_handler(CommandHandler("listuser",listuser))
    app.add_handler(CallbackQueryHandler(cb))
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
