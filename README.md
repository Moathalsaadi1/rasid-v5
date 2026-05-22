# 🛡️ RASID — Reconnaissance Automation System
### راصد — منصة أتمتة الاستطلاع الأمني

> منصة ويب تعليمية متكاملة لأتمتة أدوات الـ Reconnaissance الأمني خلف واجهة موحّدة،
> مع عزل كامل عبر Docker لكل عملية فحص، ونظام تقييم مخاطر تلقائي، ومجموعة من
> الوحدات المتقدمة لتحليل الأسطح الهجومية.

[![Backend](https://img.shields.io/badge/backend-Flask%203.0-blue.svg)](https://flask.palletsprojects.com/)
[![Frontend](https://img.shields.io/badge/frontend-React%2019%20+%20TypeScript-61dafb.svg)](https://react.dev/)
[![Database](https://img.shields.io/badge/db-PostgreSQL%2016-336791.svg)](https://www.postgresql.org/)
[![Queue](https://img.shields.io/badge/queue-Celery%20+%20Redis-red.svg)](https://docs.celeryq.dev/)
[![Containers](https://img.shields.io/badge/isolation-Docker%20in%20Docker-2496ed.svg)](https://docs.docker.com/)
[![License](https://img.shields.io/badge/use-academic%20%2F%20educational-orange.svg)](#️-legal--ethical-use)

---

## 📋 جدول المحتويات

1. [الفكرة والهدف](#-الفكرة-والهدف)
2. [الميزات الرئيسية](#-الميزات-الرئيسية)
3. [الوحدات المتقدمة](#-الوحدات-المتقدمة-advanced-modules)
4. [المعمارية](#-المعمارية)
5. [الأدوات المدعومة](#-الأدوات-المدعومة)
6. [التقنيات المستخدمة](#-التقنيات-المستخدمة)
7. [التشغيل السريع](#-التشغيل-السريع)
8. [متغيرات البيئة](#️-متغيرات-البيئة)
9. [API Endpoints](#-ملخّص-api-endpoints)
10. [بنية المشروع](#-بنية-المشروع)
11. [نظام تقييم المخاطر](#-نظام-تقييم-المخاطر)
12. [الأمان](#️-الأمان)
13. [الاختبارات](#-الاختبارات)
14. [الاستخدام القانوني والأخلاقي](#️-legal--ethical-use)
15. [المقارنة مع الإصدار السابق](#-الفروقات-مع-v4)
16. [الشكر والمراجع](#-الشكر-والمراجع)

---

## 🎯 الفكرة والهدف

**راصد** يحلّ مشكلتين شائعتين في الاستطلاع الأمني:

**1. تشتّت الأدوات:**
`nmap`, `httpx`, `nuclei`, `subfinder`, `amass`, `masscan`, `massdns` — كلها تعمل من سطر الأوامر بصيغ مختلفة ومستويات تعقيد مختلفة.

**2. مخاطر التشغيل المباشر:**
تشغيل أدوات الفحص مباشرة على نظام التطوير قد يُخرّب البيئة أو يستهلك الموارد أو يفتح ثغرات.

**الحل:**
واجهة ويب موحّدة تُشغّل كل أداة داخل حاوية Docker معزولة، تُحلّل المخرجات تلقائياً، تدمج النتائج من مصادر متعددة، وتعرضها في Dashboard مرتّب مع نظام تقييم مخاطر واقتراحات للمعالجة.

---

## ✨ الميزات الرئيسية

| الميزة | الحالة |
|---|---|
| 7 أدوات فحص أمني في حاويات Docker معزولة | ✅ |
| 3 أدوار: Admin / Registered User / Guest | ✅ |
| نظام تقييم مخاطر تلقائي (Severity + Port + Web Bonus) | ✅ |
| تقارير قابلة للتنزيل بـ 3 صيغ (JSON / HTML / Markdown) | ✅ |
| تعديل أوامر الأدوات وحفظها لكل مستخدم (FR-12) مع Whitelist للحماية | ✅ |
| إشعارات فورية عند اكتشاف ثغرات Critical / High (FR-10) | ✅ |
| سجل تدقيق Audit Log كامل لكل عملية حساسة (NFR-7) | ✅ |
| قبول شروط قانونية إلزامي قبل أول فحص (NFR-9) | ✅ |
| إلغاء وحذف عمليات الفحص + عارض المخرجات الخام | ✅ |
| Rate Limiting على Login وإنشاء الفحوصات | ✅ |
| تحقق متقدم من الأهداف (يحجب RFC1918, Loopback, Metadata IPs) | ✅ |
| **Aggregator / Deduplication** — دمج نتائج الأدوات تلقائياً | ✅ |
| **Vulnerability Intelligence** — معلومات تعليمية من NVD API | ✅ |
| **Scan Diffing** — مقارنة فحصين لنفس الهدف | ✅ |
| **Google Dorking** — مكتبة dorks مصنّفة مع واجهة بحث | ✅ |

---

## 🔬 الوحدات المتقدمة (Advanced Modules)

### 1. 🔀 Aggregator / Deduplication Layer

تعمل **تلقائياً في الخلفية** بعد كل فحص ناجح — تجمع نتائج الأدوات المتشابهة وتحذف المكرر.

```
subfinder + amass + massdns  →  Subdomains مدمجة
nmap + masscan               →  Ports مدمجة
httpx                        →  HTTP Endpoints
nuclei                       →  Vulnerabilities
```

كل نتيجة تحمل:
- **Sources**: أي أدوات اكتشفتها (مثل: `["subfinder", "amass"]`)
- **Confidence**: `high` لو 3+ مصادر / `medium` لو 2 / `low` لو 1
- **first_seen / last_seen**: تتبع زمني للنتيجة
- **Metadata**: IPs، اسم الخدمة، وغيرها

```
GET /api/aggregate/{target}   →  نتائج مدمجة مصنّفة وبدون تكرار
```

---

### 2. 📚 Vulnerability Intelligence Module

عند اكتشاف ثغرة بواسطة nuclei، يعرض النظام **بطاقة تعليمية** شاملة مستمدة من:
- **NVD API** (National Vulnerability Database)
- **مكتبة YAML محلية** تغطي OWASP Top 10 + ثغرات شائعة

كل بطاقة تحتوي على:

| القسم | المحتوى |
|---|---|
| ملخص سريع | شرح مبسط للثغرة |
| كيف تعمل | شرح تقني تفصيلي |
| التأثير المتوقع | ما الضرر المحتمل |
| سيناريوهات الهجوم | خطوات توضيحية (تعليمي فقط) |
| Display-only Payloads | أمثلة نصية داخل code block — بدون تنفيذ |
| طرق الحماية | مع code examples للمطورين |
| المراجع | روابط CVE, CWE, OWASP |

> ⚠️ الـ Payloads تُعرض كنص قراءة فقط — لا يوجد زر "Test" ولا أي تنفيذ فعلي.

```
GET /api/vuln/{finding_id}        →  بطاقة تعليمية لـ finding محدد
GET /api/vuln/library             →  تصفح المكتبة كاملة
GET /api/vuln/library/{vuln_id}   →  بطاقة ثغرة محددة
GET /api/vuln/search?q=...        →  بحث في المكتبة
POST /api/vuln/bookmark           →  حفظ ثغرة للرجوع لها
```

---

### 3. ⚖️ Scan Diffing

مقارنة **فحصين مختلفين لنفس الهدف** لرصد التغييرات في الـ Attack Surface.

**مثال عملي:**

```
فحص A (قديم — الأسبوع الماضي):     فحص B (جديد — اليوم):
  22/tcp  ssh                          22/tcp  ssh
  80/tcp  http                         80/tcp  http
  8080/tcp http-proxy                  443/tcp  https      ← جديد
                                       9929/tcp nping      ← جديد
```

**النتيجة في واجهة الـ Diff:**

```
🟢 Added (2)
   NEW  443/tcp  (https)       ← Port جديد فُتح
   NEW  9929/tcp (nping)       ← خدمة جديدة

🔴 Removed (1)
   GONE 8080/tcp (http-proxy)  ← Port أُغلق

⚪ Unchanged (2)
   SAME 22/tcp  (ssh)
   SAME 80/tcp  (http)
```

يعمل على جميع أنواع النتائج: Ports، Subdomains، Vulnerabilities، HTTP Endpoints.

```
GET /api/scans/diff?scan_a={id}&scan_b={id}   →  نتيجة المقارنة
```

---

### 4. 🔍 Google Dorking Module

واجهة بحث أمني بأسلوب **DorkSearch** — تولّد Google Dorks تلقائياً وتشغّلها عبر محرك بحث.

**الفئات المدعومة:**

| الفئة | أمثلة |
|---|---|
| 📁 Exposed Files | `filetype:pdf site:target`, `filetype:xls` |
| 🔐 Login Pages | `inurl:admin site:target`, `inurl:login` |
| ⚠️ Vulnerabilities | `inurl:phpinfo site:target`, `inurl:wp-admin` |
| 📧 Email Harvesting | `site:target "@gmail.com"` |
| 🔍 Subdomains | `site:*.target.com` |
| ⚙️ Config Leaks | `filetype:env site:target`, `inurl:config` |

**آلية العمل:**
1. المستخدم يختار الهدف + الفئة
2. النظام يولّد الـ Dorks تلقائياً من المكتبة
3. Celery task يشغّل الـ Dorks عبر SearXNG (self-hosted أو public instance)
4. النتائج تظهر مع الروابط والـ Snippets

```
GET  /api/dorking/categories          →  قائمة الفئات المتاحة
POST /api/dorking/search              →  تشغيل dork {target, category}
GET  /api/dorking/results/{task_id}   →  استرجاع النتائج
GET  /api/dorking/library             →  تصفح مكتبة الـ Dorks
```

---

## 🏗 المعمارية

```
                    ┌──────────────────────────────┐
                    │    React 19 + TypeScript     │
                    │    (Vite, port 5173)         │
                    │    HTML / CSS / AJAX         │
                    └──────────────┬───────────────┘
                                   │ X-API-Key (HTTPS/JSON)
                                   ▼
        ┌───────────────────────────────────────────────────┐
        │              Flask API  (port 8000)               │
        │  • blueprints/ (auth, scans, tools, vuln, dork…) │
        │  • validation, audit, legal modules               │
        │  • Flask-Limiter  (rate limiting)                 │
        │  • SQLAlchemy ORM                                 │
        └──────────┬──────────────────────┬────────────────┘
                   │                      │
                   ▼                      ▼
        ┌──────────────────┐    ┌──────────────────────┐
        │  PostgreSQL 16   │    │   Redis (Broker)     │
        │  • users         │    │   • Task queue       │
        │  • scans         │    │   • Result backend   │
        │  • findings      │    └──────────┬───────────┘
        │  • assets        │               │
        │  • aggregated    │               ▼
        │  • vuln_bookmarks│    ┌──────────────────────────┐
        │  • audit_logs    │    │     Celery Worker(s)     │
        │  • notifications │    │  • scan tasks            │
        │  • legal_accept  │    │  • aggregate trigger     │
        └──────────────────┘    │  • dorking tasks         │
                                └──────────┬───────────────┘
                                           │ Docker SDK
                                           ▼
                                ┌──────────────────────────┐
                                │    Docker-in-Docker      │
                                │    (DinD, port 2375)     │
                                │  ┌──────────────────┐   │
                                │  │ nmap container   │   │
                                │  │ httpx container  │   │
                                │  │ nuclei container │   │
                                │  │ subfinder …      │   │
                                │  │ amass …          │   │
                                │  │ masscan …        │   │
                                │  │ massdns …        │   │
                                │  └──────────────────┘   │
                                └──────────────────────────┘
```

---

## 🛠 الأدوات المدعومة

| الأداة | الوظيفة | الحاوية الافتراضية |
|---|---|---|
| **nmap** | فحص المنافذ المفتوحة وكشف الخدمات وإصداراتها | `instrumentisto/nmap` |
| **httpx** | كشف نقاط HTTP/HTTPS الفعّالة على الهدف | `projectdiscovery/httpx` |
| **nuclei** | فحص الثغرات المعروفة باستخدام Templates جاهزة | `projectdiscovery/nuclei` |
| **subfinder** | استخراج النطاقات الفرعية (Passive) | `projectdiscovery/subfinder` |
| **amass** | استخراج النطاقات الفرعية (Passive + Active) | `caffix/amass` |
| **masscan** | فحص منافذ سريع جداً للنطاقات الكبيرة | `ilyaglow/masscan` |
| **massdns** | حل DNS عالي الأداء للتحقق من السجلات | `rasid/massdns` (مبني محلياً) |

كل أداة في `app/tools/registry.py` تملك:
- **صورة Docker** قابلة للتعديل عبر `TOOL_<NAME>_IMAGE`
- **`default_args`** — الإعدادات الافتراضية
- **`allowed_flags`** — Whitelist للإعدادات القابلة للتخصيص
- **`timeout_seconds`** — حد زمني أقصى لكل تشغيل

---

## 💻 التقنيات المستخدمة

### الواجهة الأمامية (Frontend)
| التقنية | الغرض |
|---|---|
| **React 19 + TypeScript** | بناء واجهة تفاعلية ديناميكية |
| **Vite** | بيئة تطوير سريعة وبناء مُحسَّن |
| **HTML / CSS / JavaScript** | البنية الأساسية للعرض |
| **AJAX** | إرسال طلبات الفحص واستقبال النتائج بدون إعادة تحميل |

### الواجهة الخلفية (Backend)
| التقنية | الغرض |
|---|---|
| **Python** | لغة البرمجة الأساسية للمنطق والتحكم |
| **Flask 3.0** | إطار عمل خفيف لبناء RESTful API |
| **SQLAlchemy** | ORM للتعامل مع قاعدة البيانات |
| **Celery** | إدارة مهام الفحص والـ Dorking بشكل غير متزامن |
| **Flask-Limiter** | Rate Limiting لحماية الـ API |
| **Subprocess / OS Modules** | التحكم بتشغيل الأدوات ومخرجاتها |

### قاعدة البيانات والبنية التحتية
| التقنية | الغرض |
|---|---|
| **PostgreSQL 16** | قاعدة البيانات الرئيسية العلائقية |
| **Redis** | Message Broker لـ Celery + تخزين نتائج المهام |
| **Docker + DinD** | عزل أدوات الفحص في حاويات مستقلة |
| **Alembic** | إدارة هجرات قاعدة البيانات |
| **NVD API** | مصدر بيانات الثغرات للـ Vulnerability Intelligence |

### أدوات التطوير والاختبار
| التقنية | الغرض |
|---|---|
| **Git / GitHub** | إدارة النسخ والتحكم بالشيفرة المصدرية |
| **Postman** | اختبار واجهات API والتحقق من سلامة الاتصال |
| **pytest** | اختبارات وحدة لـ Critical Paths |
| **Docker Compose** | تنسيق تشغيل جميع الخدمات معاً |

---

## 🚀 التشغيل السريع

### المتطلبات الأساسية
- Docker و Docker Compose v2
- Node.js 18+ و npm
- ذاكرة RAM: 4GB كحد أدنى (DinD يحتاج مساحة)
- المنافذ 8000 (API) و 5173 (UI) يجب أن تكون فارغة

### خطوات التشغيل

```bash
# 1) فك المشروع وادخل إلى مجلد الـ backend
cd rasid-v5/backend

# 2) انسخ ملف الإعدادات وعدّله
cp .env.example .env
# (عدّل DATABASE_URL والـ SECRET_KEY قبل الإنتاج)

# 3) شغّل سكريبت الإعداد
chmod +x setup.sh
./setup.sh

# 4) في terminal منفصل، شغّل الـ frontend
cd ../frontend
npm install
npm run dev
```

افتح المتصفح على: **http://localhost:5173**

> أول حساب يُسجَّل يصبح **Admin** تلقائياً.

### إيقاف وإعادة تشغيل

```bash
cd backend
docker compose down            # إيقاف كامل
docker compose up -d           # إعادة تشغيل في الخلفية
docker compose logs -f api     # مراقبة سجلات الـ API
docker compose logs -f worker  # مراقبة سجلات Celery
```

---

## ⚙️ متغيرات البيئة (ENV Variables)

| المتغير | الوصف | القيمة الافتراضية |
|---|---|---|
| `DATABASE_URL` | رابط اتصال PostgreSQL | `postgresql://rasid:rasid@db:5432/rasid` |
| `REDIS_BROKER_URL` | Broker لـ Celery | `redis://redis:6379/0` |
| `REDIS_RESULT_BACKEND` | تخزين نتائج الـ Tasks | `redis://redis:6379/1` |
| `SECRET_KEY` | مفتاح التشفير للجلسات | *(يجب تغييره)* |
| `DOCKER_HOST` | DinD endpoint | `tcp://docker:2375` |
| `ALLOW_PRIVATE_TARGETS` | السماح بفحص RFC1918/Loopback | `false` ⚠️ |
| `LOG_LEVEL` | مستوى التسجيل | `INFO` |
| `CORS_ORIGINS` | Origins المسموحة | `http://localhost:5173` |
| `RATE_LIMIT_STORAGE_URI` | تخزين حدود الطلبات | `memory://` |
| `NVD_API_KEY` | مفتاح NVD API (للـ Vuln Intelligence) | اختياري |
| `SEARXNG_URL` | رابط SearXNG للـ Dorking | `https://searx.be` |
| `TOOL_<NAME>_IMAGE` | تعديل صورة Docker لأداة محددة | حسب الجدول |

> ⚠️ لا تضع `ALLOW_PRIVATE_TARGETS=true` إلا في مختبر معزول تماماً.

---

## 📡 ملخّص API Endpoints

> كل الـ Endpoints (عدا `/register` و `/login`) تتطلّب:
> `X-API-Key: <your_api_key>` في الـ Header.

### 🔐 Authentication
```
POST   /api/register                    — تسجيل (أول مستخدم → Admin)
POST   /api/login                       — تسجيل دخول
GET    /api/me                          — بيانات الحساب الحالي
```

### 🔍 Scans
```
GET    /api/scans                       — قائمة الفحوصات (مع فلاتر)
POST   /api/scans                       — إنشاء فحص {target, tool}
GET    /api/scans/:id                   — تفاصيل + Findings + Assets
DELETE /api/scans/:id                   — حذف
POST   /api/scans/:id/cancel            — إلغاء
GET    /api/scans/:id/raw               — stdout/stderr الخام
GET    /api/scans/:id/report            — تقرير ?format=json|html|md
GET    /api/scans/diff?scan_a=&scan_b=  — مقارنة فحصين (Scan Diff)
```

### 📊 Data & Analytics
```
GET    /api/findings                    — قائمة الثغرات
GET    /api/assets                      — قائمة الأصول المكتشفة
GET    /api/dashboard                   — إحصائيات شاملة
GET    /api/aggregate/{target}          — نتائج مدمجة بدون تكرار
```

### 🔧 Tool Commands (FR-12)
```
GET    /api/tools                       — قائمة الأدوات + Flags المسموحة
GET    /api/tools/commands              — أوامر المستخدم المحفوظة
POST   /api/tools/commands              — إنشاء/تعديل {tool_name, args, name}
DELETE /api/tools/commands/:id          — حذف
POST   /api/tools/commands/:id/toggle   — تفعيل/إيقاف
```

### 📚 Vulnerability Intelligence
```
GET    /api/vuln/{finding_id}           — بطاقة تعليمية لـ finding
GET    /api/vuln/library                — تصفح المكتبة كاملة
GET    /api/vuln/library/{vuln_id}      — بطاقة ثغرة محددة
GET    /api/vuln/search?q=              — بحث في المكتبة
POST   /api/vuln/bookmark               — حفظ ثغرة
```

### 🔍 Google Dorking
```
GET    /api/dorking/categories          — فئات الـ Dorks المتاحة
POST   /api/dorking/search              — تشغيل bork {target, category}
GET    /api/dorking/results/{task_id}   — استرجاع نتائج الـ Dork
GET    /api/dorking/library             — تصفح مكتبة الـ Dorks
```

### 🔔 Notifications (FR-10)
```
GET    /api/notifications               — قائمة الإشعارات
PUT    /api/notifications/:id/read      — تعليم كمقروء
PUT    /api/notifications/read-all      — تعليم الكل
```

### ⚖️ Legal
```
GET    /api/legal/terms                 — نص الشروط + حالة القبول
POST   /api/legal/accept                — تسجيل القبول
```

### ⚙️ Settings
```
POST   /api/settings/change-password    — تغيير كلمة المرور
POST   /api/settings/rotate-api-key     — تجديد الـ API Key
DELETE /api/settings/account            — حذف الحساب
```

### 👑 Admin
```
GET    /api/admin/users                 — قائمة المستخدمين
PUT    /api/admin/users/:id             — تعديل role / is_active
DELETE /api/admin/users/:id             — حذف مستخدم
GET    /api/admin/stats                 — إحصائيات النظام
GET    /api/admin/audit-logs            — سجل التدقيق
```

---

## 🗂 بنية المشروع

```
rasid-v5/
├── backend/
│   ├── app/
│   │   ├── api/                          # Flask Blueprints
│   │   │   ├── auth.py
│   │   │   ├── scans.py                  # + diff endpoint
│   │   │   ├── findings.py
│   │   │   ├── assets.py
│   │   │   ├── dashboard.py
│   │   │   ├── tools.py
│   │   │   ├── aggregate.py              # ← Aggregator API
│   │   │   ├── vuln_intel.py             # ← Vulnerability Intelligence API
│   │   │   ├── dorking.py                # ← Google Dorking API
│   │   │   ├── notifications.py
│   │   │   ├── legal.py
│   │   │   ├── settings.py
│   │   │   └── admin.py
│   │   ├── tools/
│   │   │   ├── parsers/                  # Parser لكل أداة
│   │   │   │   ├── nmap_parser.py
│   │   │   │   ├── httpx_parser.py
│   │   │   │   ├── nuclei_parser.py
│   │   │   │   ├── subfinder_parser.py
│   │   │   │   ├── amass_parser.py
│   │   │   │   ├── masscan_parser.py
│   │   │   │   └── massdns_parser.py
│   │   │   ├── registry.py
│   │   │   ├── runner.py
│   │   │   └── persistence.py
│   │   ├── modules/
│   │   │   └── vuln_intel/               # ← Vuln Intelligence Module
│   │   │       ├── mapper.py             # ربط findings بالمكتبة
│   │   │       ├── composer.py           # بناء الـ Card التعليمية
│   │   │       ├── nvd_client.py         # تكامل مع NVD API
│   │   │       └── library/              # ملفات YAML للثغرات
│   │   │           ├── sql_injection.yaml
│   │   │           ├── xss.yaml
│   │   │           ├── rce.yaml
│   │   │           ├── ssrf.yaml
│   │   │           └── ...
│   │   ├── aggregator.py                 # ← منطق الدمج وإزالة التكرار
│   │   ├── dork_library.py               # ← مكتبة Google Dorks
│   │   ├── dorking_engine.py             # ← محرك تشغيل الـ Dorks
│   │   ├── audit.py
│   │   ├── auth.py
│   │   ├── legal.py
│   │   ├── logging_setup.py
│   │   ├── main.py
│   │   ├── models.py                     # + AggregatedFinding, VulnBookmark
│   │   ├── serializers.py
│   │   ├── tasks.py                      # + aggregate_task, dork_task
│   │   ├── tool_args_validator.py
│   │   └── validation.py
│   ├── migrations/
│   ├── tests/
│   ├── Dockerfile
│   ├── Dockerfile.nuclei
│   ├── Dockerfile.massdns
│   ├── docker-compose.yml
│   ├── requirements.txt
│   ├── setup.sh
│   └── .env.example
└── frontend/
    └── src/
        ├── api/
        ├── components/
        │   ├── Sidebar.tsx
        │   ├── Topbar.tsx
        │   ├── Badge.tsx
        │   ├── Modal.tsx
        │   └── Pagination.tsx
        ├── hooks/
        │   ├── useSession.ts
        │   └── useNotifications.ts
        ├── types/
        ├── utils/
        ├── views/                        # 15 صفحة
        │   ├── Login.tsx
        │   ├── Register.tsx
        │   ├── Dashboard.tsx
        │   ├── Scans.tsx
        │   ├── ScanDetail.tsx
        │   ├── Findings.tsx
        │   ├── Assets.tsx
        │   ├── Tools.tsx
        │   ├── AggregateView.tsx         # ← عرض النتائج المدمجة
        │   ├── DiffView.tsx              # ← Scan Diff
        │   ├── VulnIntel.tsx             # ← Vulnerability Intelligence
        │   ├── DorkingView.tsx           # ← Google Dorking
        │   ├── Notifications.tsx
        │   ├── Settings.tsx
        │   └── Admin.tsx
        ├── App.tsx
        └── main.tsx
```

---

## 🧠 نظام تقييم المخاطر (Risk Scoring)

```
Risk Score = Severity Base + Port Bonus + Web Bonus
```

| المكوّن | القيمة |
|---|---|
| `severity_base` | info=10, low=30, medium=60, high=85, critical=100 |
| `port_bonus` | منافذ {23, 445, 3389} → +10 / منافذ {21, 3306, 5432, 5900} → +5 |
| `web_bonus` | +5 إذا جاء الـ Finding من سياق ويب |

ثم يُحوَّل الـ Score إلى **Priority**:

| النقاط | الأولوية |
|---|---|
| ≥ 85 | 🔴 critical |
| ≥ 60 | 🟠 high |
| ≥ 25 | 🟡 medium |
| < 25 | 🟢 low |

يُرسَل **إشعار فوري** عند اكتشاف أي ثغرة بمستوى `critical` أو `high`.

---

## 🛡️ الأمان

### الحماية من SSRF
يحجب تلقائياً: RFC1918، Loopback، Link-local (Metadata IPs)، أسماء مضيف خطرة، ومحارف Shell Injection. يحل اسم المضيف ويفحص **كل** العناوين المُرجَعة.

### Custom Args Whitelisting
كل Flag يجب أن يكون ضمن `allowed_flags` — محارف Shell Injection محظورة — حد أقصى 32 Token بـ 200 حرف لكل Token.

### Rate Limiting
| الـ Endpoint | الحد |
|---|---|
| `POST /api/login` | 10 طلبات / دقيقة |
| `POST /api/register` | 5 طلبات / دقيقة |
| `POST /api/scans` | 30 فحص / ساعة |
| `POST /api/dorking/search` | 20 بحث / ساعة |

### Audit Logging
كل عملية حساسة تُسجَّل مع IP، User-Agent، Timestamp، والمستخدم. السجل **Append-Only**.

---

## 🧪 الاختبارات

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

تغطية الاختبارات: المصادقة، الفحوصات وحدود الصلاحيات، التحقق من الهدف (RFC1918 + Shell Injection)، Custom Args Whitelist، Legal Gate، Rate Limiting.

---

## ⚖️ Legal & Ethical Use

> **هذا مشروع أكاديمي وتعليمي.** الاستخدام مسؤوليتك الكاملة.

عند أول فحص، القبول إلزامي:
1. أنت تفحص أهدافاً تملكها أو لديك إذن خطّي صريح.
2. عواقب الاستخدام مسؤوليتك وفق قوانين بلدك (CFAA, GDPR...).
3. لن تستخدم المنصة لاستغلال ثغرات أو حجب خدمات.

كل قبول يُسجَّل في `legal_acceptances` مع IP والإصدار والـ Timestamp.

---

## 🆚 الفروقات مع v4

| العنصر | v4 | v5 (الحالي) |
|---|---|---|
| عدد الأدوات | 3 | **7** |
| Custom Tool Args | ❌ | ✅ FR-12 |
| إشعارات فورية | ❌ | ✅ FR-10 |
| Audit Logging | ❌ | ✅ NFR-7 |
| Legal Gating | ❌ | ✅ NFR-9 |
| حماية SSRF | بسيطة | ✅ متقدمة |
| Rate Limiting | ❌ | ✅ |
| صيغ التقارير | JSON, HTML | ✅ + Markdown |
| إلغاء/حذف الفحص | ❌ | ✅ |
| اختبارات | ❌ | ✅ pytest |
| قاعدة البيانات | SQLite | ✅ PostgreSQL 16 |
| **Aggregator/Dedup** | ❌ | ✅ **جديد** |
| **Vulnerability Intel** | ❌ | ✅ **جديد** |
| **Scan Diffing** | ❌ | ✅ **جديد** |
| **Google Dorking** | ❌ | ✅ **جديد** |

---

## 🙏 الشكر والمراجع

**الأدوات:** ProjectDiscovery (httpx, nuclei, subfinder) — OWASP Amass — masscan — massdns

**مصادر البيانات:** NVD (National Vulnerability Database) — SearXNG

**المراجع التقنية:** Flask — Docker — Redis — Celery — SQLAlchemy — React

---

## 👥 فريق التطوير

| الاسم | الدور |
|---|---|
| معاذ أحمد السعدي | مطوّر |
| أحمد ماهر فروان | مطوّر |

**المشرف الأكاديمي:** د. روني ربيع القسام

---

<div align="center">

**RASID — Reconnaissance Automation System**

*Built with ❤️ for Security Education | 2025-2026*

[![Academic Use Only](https://img.shields.io/badge/use-academic%20only-orange.svg)](#️-legal--ethical-use)

</div>
