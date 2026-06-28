from collections import defaultdict
from logging import getLogger
from time import time
from typing import NoReturn

from aiohttp.web import (
    Application, HTTPFound, Request, Response,
    StreamResponse, get, json_response
)

from config import Config
from petter import APIError, AvatarNotFound, Petter, UserNotFound

logger = getLogger(__name__)

# ── Rate Limiter ───────────────────────────────────────────────────────────────

class RateLimiter:
    def __init__(self, max_req: int = Config.RateLimit.MAX_REQUESTS,
                 window: int = Config.RateLimit.WINDOW) -> None:
        self._max = max_req
        self._window = window
        self._hits: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, ip: str) -> bool:
        now = time()
        hits = [t for t in self._hits[ip] if now - t < self._window]
        self._hits[ip] = hits
        if len(hits) >= self._max:
            return False
        self._hits[ip].append(now)
        return True


# ── Dashboard HTML ─────────────────────────────────────────────────────────────

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>PetTheCord</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Silkscreen:wght@400;700&family=Tajawal:wght@300;400;500;700&display=swap" rel="stylesheet"/>
<style>
  :root {
    --bg:       #080810;
    --surface:  #10101e;
    --surface2: #181828;
    --border:   rgba(255,255,255,0.07);
    --pink:     #ff2d6b;
    --purple:   #8b5cf6;
    --cyan:     #00e5ff;
    --text:     #f0f0fa;
    --muted:    #6b7280;
    --radius:   16px;
    --glow:     0 0 32px rgba(255,45,107,0.3);
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Tajawal', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    overflow-x: hidden;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  /* ── Background Orbs ── */
  .orbs {
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    overflow: hidden;
  }
  .orb {
    position: absolute; border-radius: 50%;
    filter: blur(80px); opacity: 0.18;
  }
  .orb-1 { width: 500px; height: 500px; background: var(--pink);   top: -100px; left: -100px; animation: drift1 18s ease-in-out infinite; }
  .orb-2 { width: 400px; height: 400px; background: var(--purple); bottom: -80px; right: -80px; animation: drift2 22s ease-in-out infinite; }
  .orb-3 { width: 300px; height: 300px; background: var(--cyan);   top: 40%; left: 60%; animation: drift3 15s ease-in-out infinite; }

  @keyframes drift1 { 0%,100%{transform:translate(0,0)} 50%{transform:translate(60px,40px)} }
  @keyframes drift2 { 0%,100%{transform:translate(0,0)} 50%{transform:translate(-50px,-30px)} }
  @keyframes drift3 { 0%,100%{transform:translate(0,0)} 50%{transform:translate(-40px,50px)} }

  /* ── Layout ── */
  .wrapper {
    position: relative; z-index: 1;
    width: 100%; max-width: 540px;
    padding: 32px 16px 64px;
    display: flex; flex-direction: column; align-items: center; gap: 24px;
  }

  /* ── Header ── */
  header {
    width: 100%;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 4px;
  }
  .logo {
    font-family: 'Silkscreen', monospace;
    font-size: 22px;
    background: linear-gradient(135deg, var(--pink), var(--purple));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: 1px;
  }
  .lang-btn {
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 6px 14px;
    border-radius: 99px;
    font-family: 'Tajawal', sans-serif;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s;
    letter-spacing: 1px;
  }
  .lang-btn:hover { border-color: var(--pink); color: var(--pink); }

  /* ── Card ── */
  .card {
    width: 100%;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 28px 24px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    transition: box-shadow 0.3s;
  }
  .card:hover { box-shadow: var(--glow); }

  .card-title {
    font-size: 15px;
    font-weight: 500;
    color: var(--muted);
    margin-bottom: 16px;
    letter-spacing: 0.3px;
  }

  /* ── Input Row ── */
  .input-row {
    display: flex; gap: 10px;
  }
  .uid-input {
    flex: 1;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 16px;
    color: var(--text);
    font-family: 'Tajawal', sans-serif;
    font-size: 15px;
    outline: none;
    transition: border-color 0.2s;
    direction: ltr;
    text-align: left;
  }
  .uid-input::placeholder { color: var(--muted); }
  .uid-input:focus { border-color: var(--pink); }

  .gen-btn {
    background: linear-gradient(135deg, var(--pink), var(--purple));
    border: none;
    border-radius: 10px;
    padding: 12px 20px;
    color: white;
    font-family: 'Tajawal', sans-serif;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
    transition: opacity 0.2s, transform 0.1s;
  }
  .gen-btn:hover { opacity: 0.9; }
  .gen-btn:active { transform: scale(0.97); }
  .gen-btn:disabled { opacity: 0.5; cursor: not-allowed; }

  /* ── Error Message ── */
  .error-msg {
    display: none;
    margin-top: 12px;
    padding: 10px 14px;
    background: rgba(255, 45, 107, 0.1);
    border: 1px solid rgba(255, 45, 107, 0.3);
    border-radius: 8px;
    color: #ff6b8a;
    font-size: 14px;
  }

  /* ── Preview Card ── */
  .preview-card {
    width: 100%;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 28px 24px;
    display: none;
    flex-direction: column;
    align-items: center;
    gap: 20px;
    animation: fadeIn 0.4s ease;
  }
  @keyframes fadeIn { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:translateY(0)} }

  .gif-frame {
    width: 160px; height: 160px;
    border-radius: 50%;
    border: 3px solid var(--pink);
    box-shadow: 0 0 24px rgba(255,45,107,0.4);
    overflow: hidden;
    display: flex; align-items: center; justify-content: center;
    background: var(--surface2);
  }
  .gif-frame img {
    width: 100%; height: 100%;
    object-fit: cover;
    border-radius: 50%;
  }

  /* ── Loader ── */
  .loader {
    width: 48px; height: 48px;
    border: 3px solid var(--surface2);
    border-top-color: var(--pink);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Action Buttons ── */
  .actions {
    display: flex; gap: 10px; width: 100%;
  }
  .action-btn {
    flex: 1;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 11px;
    color: var(--text);
    font-family: 'Tajawal', sans-serif;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center; gap: 7px;
    transition: all 0.2s;
  }
  .action-btn:hover { border-color: var(--purple); color: var(--purple); }
  .action-btn.copied { border-color: var(--cyan); color: var(--cyan); }

  /* ── Stats ── */
  .stats-card {
    width: 100%;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px 24px;
    display: flex; align-items: center; justify-content: space-between;
  }
  .stats-label { color: var(--muted); font-size: 14px; }
  .stats-count {
    font-family: 'Silkscreen', monospace;
    font-size: 20px;
    background: linear-gradient(135deg, var(--pink), var(--cyan));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  /* ── Footer ── */
  footer {
    color: var(--muted);
    font-size: 13px;
    text-align: center;
    line-height: 1.6;
  }
  footer a { color: var(--purple); text-decoration: none; }
  footer a:hover { color: var(--pink); }

  /* ── RTL / LTR Adjustments ── */
  html[dir="ltr"] .input-row { direction: ltr; }
</style>
</head>
<body>

<div class="orbs">
  <div class="orb orb-1"></div>
  <div class="orb orb-2"></div>
  <div class="orb orb-3"></div>
</div>

<div class="wrapper">

  <!-- Header -->
  <header>
    <div class="logo">PetTheCord</div>
    <button class="lang-btn" onclick="toggleLang()" id="lang-btn">EN</button>
  </header>

  <!-- Input Card -->
  <div class="card">
    <p class="card-title" id="t-subtitle">أدخل معرف مستخدم ديسكورد</p>
    <div class="input-row">
      <input
        class="uid-input"
        id="uid-input"
        type="text"
        placeholder="ex: 123456789012345678"
        maxlength="20"
        inputmode="numeric"
      />
      <button class="gen-btn" id="gen-btn" onclick="generate()" >
        <span id="t-btn">توليد</span>
      </button>
    </div>
    <div class="error-msg" id="error-msg"></div>
  </div>

  <!-- Preview Card -->
  <div class="preview-card" id="preview-card">
    <div class="gif-frame" id="gif-frame">
      <div class="loader" id="loader"></div>
    </div>
    <div class="actions">
      <button class="action-btn" onclick="downloadGif()" id="t-download">
        ⬇ <span>تحميل</span>
      </button>
      <button class="action-btn" id="copy-btn" onclick="copyLink()">
        🔗 <span id="t-copy">نسخ الرابط</span>
      </button>
    </div>
  </div>

  <!-- Stats -->
  <div class="stats-card">
    <span class="stats-label" id="t-stats">إجمالي الطلبات</span>
    <span class="stats-count" id="stats-count">—</span>
  </div>

  <!-- Footer -->
  <footer>
    <span id="t-footer">مشروع مفتوح المصدر</span> ·
    <a href="https://github.com" target="_blank">GitHub</a>
  </footer>

</div>

<script>
// ── State ───────────────────────────────────────────────────────────────────
let lang     = 'ar';
let currentUid  = null;
let gifUrl   = null;

// ── Translations ────────────────────────────────────────────────────────────
const T = {
  ar: {
    subtitle:  'أدخل معرف مستخدم ديسكورد',
    btn:       'توليد',
    download:  '⬇ تحميل',
    copy:      'نسخ الرابط',
    copied:    'تم النسخ ✓',
    stats:     'إجمالي الطلبات',
    footer:    'مشروع مفتوح المصدر',
    errEmpty:  'الرجاء إدخال معرف مستخدم',
    errInvalid:'معرف غير صالح — أرقام فقط',
    errNotFound:'المستخدم غير موجود',
    errAvatar: 'هذا المستخدم ليس لديه صورة',
    errRate:   'طلبات كثيرة، انتظر قليلاً',
    errGeneric:'حدث خطأ، حاول مجدداً',
  },
  en: {
    subtitle:  'Enter a Discord User ID',
    btn:       'Generate',
    download:  '⬇ Download',
    copy:      'Copy Link',
    copied:    'Copied ✓',
    stats:     'Total Pets',
    footer:    'Open Source Project',
    errEmpty:  'Please enter a User ID',
    errInvalid:'Invalid ID — numbers only',
    errNotFound:'User not found',
    errAvatar: 'This user has no avatar',
    errRate:   'Too many requests, slow down',
    errGeneric:'Something went wrong, try again',
  },
};

// ── Language Toggle ─────────────────────────────────────────────────────────
function toggleLang() {
  lang = lang === 'ar' ? 'en' : 'ar';
  const html = document.documentElement;
  html.setAttribute('lang', lang);
  html.setAttribute('dir', lang === 'ar' ? 'rtl' : 'ltr');
  document.getElementById('lang-btn').textContent = lang === 'ar' ? 'EN' : 'AR';
  applyTranslations();
}

function applyTranslations() {
  const t = T[lang];
  document.getElementById('t-subtitle').textContent  = t.subtitle;
  document.getElementById('t-btn').textContent        = t.btn;
  document.getElementById('t-download').innerHTML     = t.download;
  document.getElementById('t-copy').textContent       = t.copy;
  document.getElementById('t-stats').textContent      = t.stats;
  document.getElementById('t-footer').textContent     = t.footer;
}

// ── Generate ─────────────────────────────────────────────────────────────────
async function generate() {
  const input = document.getElementById('uid-input');
  const uid   = input.value.trim();
  const errEl = document.getElementById('error-msg');
  const t     = T[lang];

  hideError();

  if (!uid) return showError(t.errEmpty);
  if (!/^\\d{15,20}$/.test(uid)) return showError(t.errInvalid);

  setLoading(true);

  try {
    // Probe the GIF endpoint
    const url = `/${uid}.gif`;
    const res  = await fetch(url, { method: 'HEAD' });

    if (res.status === 404)      return showError(t.errNotFound);
    if (res.status === 429)      return showError(t.errRate);
    if (res.status === 403)      return showError(t.errGeneric);
    if (!res.ok)                 return showError(t.errGeneric);

    currentUid = uid;
    gifUrl     = url + '?t=' + Date.now();   // cache-bust for same-uid refresh
    showPreview(gifUrl);

  } catch (_) {
    showError(t.errGeneric);
  } finally {
    setLoading(false);
  }
}

// ── UI Helpers ───────────────────────────────────────────────────────────────
function setLoading(on) {
  const btn = document.getElementById('gen-btn');
  btn.disabled = on;
  if (on) {
    showPreviewCard();
    document.getElementById('gif-frame').innerHTML = '<div class="loader"></div>';
  }
}

function showPreview(url) {
  const frame = document.getElementById('gif-frame');
  const img   = document.createElement('img');
  img.src = url;
  img.alt = 'petpet GIF';
  img.onload = () => { frame.innerHTML = ''; frame.appendChild(img); };
  img.onerror = () => showError(T[lang].errGeneric);
}

function showPreviewCard() {
  document.getElementById('preview-card').style.display = 'flex';
}

function showError(msg) {
  const el = document.getElementById('error-msg');
  el.textContent = msg;
  el.style.display = 'block';
  document.getElementById('preview-card').style.display = 'none';
}

function hideError() {
  document.getElementById('error-msg').style.display = 'none';
}

// ── Actions ──────────────────────────────────────────────────────────────────
function downloadGif() {
  if (!currentUid) return;
  const a = document.createElement('a');
  a.href     = `/${currentUid}.gif`;
  a.download = `petpet_${currentUid}.gif`;
  a.click();
}

function copyLink() {
  if (!currentUid) return;
  const url  = `${location.origin}/${currentUid}.gif`;
  const btn  = document.getElementById('copy-btn');
  const span = document.getElementById('t-copy');
  navigator.clipboard.writeText(url).then(() => {
    btn.classList.add('copied');
    span.textContent = T[lang].copied;
    setTimeout(() => {
      btn.classList.remove('copied');
      span.textContent = T[lang].copy;
    }, 2000);
  });
}

// ── Stats ────────────────────────────────────────────────────────────────────
async function fetchStats() {
  try {
    const res  = await fetch('/api/stats');
    const data = await res.json();
    document.getElementById('stats-count').textContent =
      data.total.toLocaleString();
  } catch (_) {}
}

// ── Enter key support ────────────────────────────────────────────────────────
document.getElementById('uid-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') generate();
});

// ── Init ─────────────────────────────────────────────────────────────────────
fetchStats();
setInterval(fetchStats, 30_000);
</script>
</body>
</html>"""


# ── Server Application ─────────────────────────────────────────────────────────

class PetServer(Application):
    def __init__(self, petter: Petter) -> None:
        super().__init__()
        self._petter  = petter
        self._limiter = RateLimiter() if Config.RateLimit.ENABLED else None
        self.add_routes([
            get("/",            self.dashboard),
            get("/api/stats",   self.stats),
            get("/{uid}",       self.petpet),
        ])

    # ── Routes ─────────────────────────────────────────────────────────────────

    async def dashboard(self, _: Request) -> Response:
        return Response(
            text=DASHBOARD_HTML,
            content_type="text/html",
            charset="utf-8",
        )

    async def stats(self, _: Request) -> Response:
        return json_response(self._petter.stats)

    async def petpet(self, request: Request) -> StreamResponse:
        # Rate limiting
        if self._limiter and not self._limiter.is_allowed(request.remote or ""):
            return Response(status=429)

        # FIX: safe UID extraction — handle missing dot gracefully
        raw = request.match_info["uid"]
        dot = raw.find(".")
        uid_str = raw[:dot] if dot != -1 else raw

        if not uid_str.isdigit():
            return Response(status=400)

        uid = int(uid_str)
        logger.info("API: petpet request uid=%s from %s", uid, request.remote)

        try:
            gif = await self._petter.make(uid)
            return Response(
                body=gif,
                content_type="image/gif",
                headers={"Cache-Control": "public, max-age=3600"},
            )
        except UserNotFound:
            return Response(status=404)
        except AvatarNotFound:
            return Response(status=404)
        except APIError:
            return Response(status=503)
