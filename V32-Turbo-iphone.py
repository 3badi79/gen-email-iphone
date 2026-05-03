import requests, uuid, time, os
from flask import Flask, render_template_string, jsonify, request
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
API_BASE = "https://api.mail.tm"

# كود الواجهة الاحترافي V32 TURBO - نسخة الجوال
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3BoTheking | Render Mobile Edition</title>
    <style>
        :root { --accent: #ffcc00; --bg: #000000; --panel: #0d0d0d; --border: #1a1a1a; }
        body { margin:0; background: var(--bg); color: #fff; font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        
        #notify-box { position: fixed; bottom: 20px; right: 20px; left: 20px; z-index: 10000; display: flex; flex-direction: column; gap: 10px; }
        .toast { background: #111; border: 1px solid var(--border); padding: 12px 20px; border-right: 4px solid var(--accent); font-weight: 900; animation: slideIn 0.2s; font-size: 14px; text-align: center; }
        @keyframes slideIn { from { transform: translateY(100%); } to { transform: translateY(0); } }

        /* تعديلات الجوال للـ Sidebar */
        .sidebar { width: 100%; background: var(--panel); border-bottom: 1px solid var(--border); display: flex; flex-direction: column; max-height: 40vh; }
        .sidebar-header { padding: 15px; border-bottom: 1px solid var(--border); text-align: center; color: var(--accent); font-weight: 900; font-size: 20px; }
        .settings-box { padding: 10px; background: #050505; border-bottom: 1px solid var(--border); }
        .input-main { width: 100%; background: #000; border: 1px solid var(--border); color: #fff; padding: 10px; font-weight: 900; border-radius: 6px; margin-bottom: 8px; text-align: center; font-size: 16px; box-sizing: border-box; }
        .color-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 8px; }
        .cp { background: #111; padding: 6px; border-radius: 6px; border: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; font-size: 11px; }
        input[type="color"] { border: none; width: 20px; height: 20px; cursor: pointer; background: none; }
        .btn-action { width: 100%; background: var(--accent); color: #000; border: none; padding: 10px; font-weight: 900; cursor: pointer; border-radius: 6px; }
        
        .acc-list { overflow-y: auto; flex-grow: 1; padding: 10px; background: #050505; }
        .acc-item { background: #080808; border: 1px solid var(--border); padding: 10px; margin-bottom: 8px; border-radius: 6px; display: flex; align-items: center; justify-content: space-between; }
        .acc-item.active { border-color: var(--accent); background: rgba(255, 204, 0, 0.05); }
        .email-display { font-size: 11px; font-family: monospace; color: #aaa; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 70%; }

        .main-content { flex-grow: 1; display: flex; flex-direction: column; overflow: hidden; }
        .top-nav { min-height: 60px; background: #000; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 15px; }
        .inbox-scroll { flex-grow: 1; padding: 15px; overflow-y: auto; background: #000; }
        .msg-card { background: #0a0a0a; border: 1px solid var(--border); padding: 15px; margin-bottom: 12px; border-right: 4px solid var(--accent); }
        .msg-title { font-size: 16px; font-weight: 900; color: #fff; margin-bottom: 5px; display: block; }
        .msg-snippet { color: #888; font-size: 13px; line-height: 1.5; word-break: break-word; }
        .msg-snippet a { color: var(--accent) !important; font-weight: bold; }
        .status-dot { width: 8px; height: 8px; background: #444; border-radius: 50%; margin-left: 8px; }
        .status-dot.active { background: #00ff00; box-shadow: 0 0 10px #00ff00; }

        /* تحسين العرض للشاشات الكبيرة (الكمبيوتر) ليبقى متوافقاً */
        @media (min-width: 768px) {
            body { flex-direction: row; }
            .sidebar { width: 380px; max-height: 100vh; border-left: 1px solid var(--border); border-bottom: none; }
            .email-display { font-size: 12px; }
        }
    </style>
</head>
<body>
    <div id="notify-box"></div>
    <div class="sidebar">
        <div class="sidebar-header">3BoTheking <span style="font-size: 12px;">MOBILE V32</span></div>
        <div class="settings-box">
            <input type="number" id="genQty" class="input-main" value="1">
            <div class="color-grid">
                <div class="cp"><label>اللون</label><input type="color" id="colorAcc" value="#ffcc00" onchange="syncUI()"></div>
                <div class="cp"><label>الخلفية</label><input type="color" id="colorBg" value="#000000" onchange="syncUI()"></div>
            </div>
            <button class="btn-action" onclick="startGen()">توليد توربو ⚡</button>
        </div>
        <div id="accList" class="acc-list"></div>
    </div>
    <div class="main-content">
        <div class="top-nav">
            <div style="display: flex; align-items: center; max-width: 60%;">
                <div id="activeDot" class="status-dot"></div>
                <span id="activeAddr" style="font-weight: 900; font-size: 12px; color: #888; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">اختر حساباً</span>
            </div>
            <button class="btn-action" onclick="refreshInbox()" style="width: auto; padding: 6px 15px; font-size: 12px;">تحديث</button>
        </div>
        <div id="inbox" class="inbox-scroll"></div>
    </div>
<script>
    let storage = JSON.parse(localStorage.getItem('3bo_render_v32') || '[]');
    let currentToken = '';

    window.onload = () => { renderList(); syncUI(); };

    function syncUI() {
        const a = document.getElementById('colorAcc').value;
        const b = document.getElementById('colorBg').value;
        document.documentElement.style.setProperty('--accent', a);
        document.documentElement.style.setProperty('--bg', b);
    }

    async function startGen() {
        const n = document.getElementById('genQty').value;
        showToast("جاري التوليد...");
        const r = await fetch(`/api/turbo/gen?n=${n}`);
        const d = await r.json();
        if(d.length) { storage = [...d, ...storage]; updateStorage(); }
    }

    function renderList() {
        document.getElementById('accList').innerHTML = storage.map(a => `
            <div class="acc-item ${currentToken === a.token ? 'active' : ''}" onclick="selectAcc('${a.token}', '${a.address}')">
                <div class="email-display">${a.address}</div>
                <button onclick="event.stopPropagation(); copyText('${a.address}')" style="background:var(--accent); border:none; padding:6px 10px; border-radius:4px; font-weight:900; font-size:10px; color:#000;">نسخ</button>
            </div>`).join('');
    }

    function selectAcc(tk, addr) {
        currentToken = tk;
        document.getElementById('activeAddr').innerText = addr;
        document.getElementById('activeDot').className = "status-dot active";
        renderList(); refreshInbox();
    }

    async function refreshInbox() {
        if(!currentToken) return;
        const box = document.getElementById('inbox');
        box.innerHTML = "<div style='text-align:center; color:var(--accent); font-weight:900;'>جاري الفحص...</div>";
        const r = await fetch('/api/turbo/msgs?token=' + currentToken);
        const msgs = await r.json();
        box.innerHTML = msgs.map(m => `
            <div class="msg-card">
                <span class="msg-title">${m.subject}</span>
                <div class="msg-snippet">${m.intro.replace(/(https?:\/\/[^\\s]+)/g, '<a href="$1" target="_blank">$1</a>')}</div>
            </div>`).join('') || "<div style='text-align:center; color:#333; margin-top:30px; font-weight:900;'>لا توجد رسائل</div>";
    }

    function copyText(t) {
        const i = document.createElement('input'); i.value = t; document.body.appendChild(i);
        i.select(); document.execCommand('copy'); document.body.removeChild(i);
        showToast("تم النسخ");
    }

    function updateStorage() { localStorage.setItem('3bo_render_v32', JSON.stringify(storage)); renderList(); }
    function showToast(m) {
        const b = document.getElementById('notify-box');
        const t = document.createElement('div'); t.className = 'toast'; t.innerText = m;
        b.appendChild(t); setTimeout(() => t.remove(), 3000);
    }
</script>
</body>
</html>
"""

@app.route('/api/turbo/gen')
def api_turbo_gen():
    n = int(request.args.get('n', 1))
    try:
        domains = requests.get(f"{API_BASE}/domains", timeout=5).json()['hydra:member']
        target_domain = domains[0]['domain']
        def create_acc():
            u = uuid.uuid4().hex[:6]
            addr, pw = f"v32_{u}@{target_domain}", f"p_{u}"
            res = requests.post(f"{API_BASE}/accounts", json={"address": addr, "password": pw}, timeout=10)
            if res.status_code == 201:
                tk = requests.post(f"{API_BASE}/token", json={"address": addr, "password": pw}, timeout=10).json()
                return {"address": addr, "token": tk.get('token')}
            return None
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(filter(None, executor.map(lambda _: create_acc(), range(n))))
        return jsonify(results)
    except: return jsonify([])

@app.route('/api/turbo/msgs')
def api_turbo_msgs():
    tk = request.args.get('token')
    try:
        r = requests.get(f"{API_BASE}/messages", headers={"Authorization": f"Bearer {tk}"}, timeout=8)
        return jsonify(r.json().get('hydra:member', []))
    except: return jsonify([])

@app.route('/')
def home(): return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
```[cite: 2]

### التعديلات اللي تمت:
1.  **Viewport Meta Tag:** أضفت سطر `viewport` لضمان أن المتصفح يفهم أبعاد شاشة الجوال.
2.  **Flex-Direction:** جعلت العناصر تترتب عمودياً (`column`) في الجوال، وأفقياً (`row`) في الشاشات الكبيرة[cite: 2].
3.  **Sidebar Height:** حددت ارتفاع القائمة الجانبية (اللي صارت فوق في الجوال) بـ `40vh` كحد أقصى عشان تترك مساحة للرسائل تحت.
4.  **Font Sizes:** صغرت أحجام الخطوط والأزرار قليلاً لتناسب مساحة الجوال الضيقة.
5.  **Text Truncation:** أضفت خاصية النقاط الثلاث للمسافات الطويلة عشان الإيميلات ما تخرّب شكل التصميم.

ارفع الكود الجديد على GitHub، و **Render** بيحدث الموقع تلقائياً[cite: 2]. استمتع بالنسخة الجديدة!