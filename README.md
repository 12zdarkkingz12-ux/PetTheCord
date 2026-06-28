# PetTheCord 🐾

بوت ديسكورد + Web API يحول أفاتار أي مستخدم إلى GIF متحرك بأسلوب "petpet".

> A Discord bot + Web API that turns any user's avatar into an animated petpet GIF.

---

## الهيكل / Structure

```
petbot/
├── main.py            # Entry point
├── bot.py             # Discord slash commands
├── server.py          # Web API + Dashboard
├── petter.py          # GIF generation core
├── cache.py           # Caching layer
├── config.py          # Configuration
├── requirements.txt   # Dependencies
├── render.yaml        # Render deployment
└── assets/
    └── images/        # Static images (if needed)
```

---

## الإعداد / Setup

### 1. المتطلبات / Requirements
```bash
pip install -r requirements.txt
```

### 2. المتغيرات البيئية / Environment Variables

| Variable | Required | Description |
|---|---|---|
| `PETTHECORD_TOKEN` | ✅ | Discord bot token |
| `ORIGIN` | ✅ | Your public URL (e.g. `https://xyz.onrender.com`) |
| `PORT` | auto | Set by Render automatically |
| `CACHE_ENABLED` | — | `true` / `false` (default: `true`) |
| `CACHE_PATH` | — | Cache directory (default: `/tmp/petbot_cache`) |
| `CACHE_LIFETIME` | — | Seconds before a cached GIF expires (default: `86400`) |
| `RATE_LIMIT_MAX` | — | Max requests per window (default: `15`) |
| `RATE_LIMIT_WINDOW` | — | Window in seconds (default: `60`) |

### 3. التشغيل / Run
```bash
export PETTHECORD_TOKEN=your_token_here
export ORIGIN=http://localhost:8000
python main.py
```

---

## النشر على Render / Deploy to Render

1. ارفع المشروع على GitHub
2. في Render: **New → Web Service** → اختر المستودع
3. Render يقرأ `render.yaml` تلقائياً
4. في **Environment Variables**: أضف `PETTHECORD_TOKEN` و `ORIGIN`
5. انشر! 🚀

---

## الاستخدام / Usage

### Web API
```
GET https://your-domain.com/123456789.gif  → returns petpet GIF
GET https://your-domain.com/api/stats      → JSON stats
GET https://your-domain.com/               → Dashboard
```

### Discord Commands
- `/petpet @user` — يرسل الـ GIF مباشرة في المحادثة
- `/petpetlink @user` — يعطيك رابط الـ GIF

---

## التحسينات عن المشروع الأصلي / Improvements over original

- ✅ إصلاح bug الـ Cache (int vs string keys)
- ✅ إصلاح bug الـ URL parsing (missing dot)
- ✅ الـ Petter مشترك صح بين البوت والـ API
- ✅ Rate Limiting
- ✅ دعم الأفاتار الافتراضي
- ✅ لوحة تحكم ثنائية اللغة (عربي / إنجليزي)
- ✅ نشر سهل على Render
