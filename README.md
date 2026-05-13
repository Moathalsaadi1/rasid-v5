# 🛡 RASID — Reconnaissance Automation System

> منصة ويب تعليمية لأتمتة أدوات الـ reconnaissance الأمني خلف واجهة موحّدة،
> مع عزل كامل عبر Docker لكل عملية فحص.

[![Backend](https://img.shields.io/badge/backend-Flask%203.0-blue.svg)](https://flask.palletsprojects.com/)
[![Frontend](https://img.shields.io/badge/frontend-React%2019-61dafb.svg)](https://react.dev/)
[![Database](https://img.shields.io/badge/db-PostgreSQL%2016-336791.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/use-academic%20%2F%20educational-orange.svg)](#legal--ethical-use)

---

## 🎯 الفكرة

RASID يحلّ مشكلتين شائعتين في الاستطلاع الأمني:

1. **تشتّت الأدوات**: nmap, httpx, nuclei, subfinder, amass, masscan, massdns
   كلها سطر أوامر مختلفة، صيغ مخرجات مختلفة، مستويات تعقيد مختلفة.
2. **مخاطر التشغيل المباشر**: تشغيل scanner على نظام التطوير قد يُخرّب
   البيئة، يستهلك موارد، أو يفتح ثغرات.

الحل: واجهة موحّدة تُشغّل كل أداة داخل حاوية Docker معزولة، تُحلّل المخرجات،
تخزّنها بشكل علائقي، وتقدّمها للمستخدم في dashboard مرتّب مع نظام
scoring واقتراحات للمعالجة.

---

## ✨ الميزات الرئيسية

| الميزة | الحالة |
|---|---|
| 7 أدوات منفصلة في حاويات Docker معزولة | ✅ |
| 3 أدوار: Admin / Registered User / Guest | ✅ |
| نظام تقييم مخاطر تلقائي (severity + port + web bonus) | ✅ |
| تقارير قابلة للتنزيل بـ 3 صيغ (JSON / HTML / Markdown) | ✅ |
| **تعديل أوامر الأدوات وحفظها** (FR-12) مع whitelist للحماية | ✅ |
| **إشعارات** عند اكتشاف ثغرات critical/high (FR-10) | ✅ |
| **سجل تدقيق** كامل لكل عملية حساسة (NFR-7) | ✅ |
| **قبول شروط قانونية** قبل أول فحص (NFR-9) | ✅ |
| Cancel/Delete scans + Raw output viewer | ✅ |
| Rate limiting على الـ login والـ scan creation | ✅ |
| تحقق متقدم من target (يحجب RFC1918, loopback, metadata IPs) | ✅ |

---

## 🏗 المعمارية

```
                    ┌────────────────────┐
                    │  React 19 + TS UI  │
                    │  (Vite, port 5173) │
                    └──────────┬─────────┘
                               │ X-API-Key
                               ▼
        ┌──────────────────────────────────────────┐
        │           Flask API (port 8000)          │
        │   • blueprints/ (auth, scans, …)         │
        │   • validation, audit, legal modules     │
        │   • Flask-Limiter (rate limiting)        │
        └──────────┬───────────────────┬───────────┘
                   │                   │
                   ▼                   ▼
        ┌──────────────────┐   ┌──────────────────┐
        │  PostgreSQL 16   │   │  Redis (broker)  │
        │  • users, scans  │   │                  │
        │  • findings, …   │   └──────────┬───────┘
        └──────────────────┘              │
                                          ▼
                              ┌───────────────────────┐
                              │  Celery Worker(s)     │
                              │  • per-tool tasks     │
                              └──────────┬────────────┘
                                         │ Docker SDK
                                         ▼
                              ┌───────────────────────┐
                              │  Docker-in-Docker     │
                              │  (port 2375)          │
                              │  ┌─ nmap container ─┐ │
                              │  ┌─ httpx container ┐ │
                              │  ┌─ nuclei …       ┐ │
                              │  └─ amass / mass… ─┘ │
                              └───────────────────────┘
```

**لماذا DinD وليس subprocess؟** عزل قوي — حتى لو أحد الأدوات تعطّل
أو استُغلّ، لا يصل إلى الـ host. كل scan في حاوية منفردة تُحذف بعد الانتهاء.

---

## 🛠 الأدوات المدعومة

| الأداة | الوظيفة | الحاوية الافتراضية |
|---|---|---|
| **nmap** | فحص منافذ + كشف خدمات | `instrumentisto/nmap` |
| **httpx** | كشف نقاط HTTP فعّالة | `projectdiscovery/httpx` |
| **nuclei** | فحص الثغرات حسب templates | `projectdiscovery/nuclei` |
| **subfinder** | استخراج subdomains (passive) | `projectdiscovery/subfinder` |
| **amass** | استخراج subdomains (passive/active) | `caffix/amass` |
| **masscan** | فحص منافذ سريع لشبكات كبيرة | `ilyaglow/masscan` |
| **massdns** | حل DNS عالي الأداء | `rasid/massdns` (مبنى محلياً) |

كل أداة في `app/tools/registry.py` لها:
- صورة Docker قابلة للتعديل عبر env (`TOOL_<NAME>_IMAGE`).
- `default_args` — الأرجومنتس الافتراضية.
- `allowed_flags` — whitelist للأرجومنتس التي يمكن للمستخدم تخصيصها.
- `timeout_seconds` — حد زمني لكل تشغيل.

---

## 🚀 التشغيل السريع

### المتطلبات
- Docker و Docker Compose v2.
- 4GB RAM على الأقل (DinD يستهلك مساحة).
- منفذ 8000 (API) و 5173 (UI) فارغان.

### الخطوات

```bash
# 1) فك المشروع وادخل لمجلد الـ backend
cd backend

# 2) انسخ env template
cp .env.example .env
# (عدّل DATABASE_URL والـ secrets قبل الإنتاج)

# 3) شغّل setup script — يبني الصور ويُهيّئ DinD ويُشغّل migrations
chmod +x setup.sh
./setup.sh

# 4) في terminal منفصل، شغّل الـ frontend
cd ../frontend
npm install
npm run dev
```

افتح http://localhost:5173 — أول حساب يُسجَّل يصبح Admin تلقائياً.

### إيقاف وإعادة تشغيل

```bash
cd backend
docker compose down          # إيقاف
docker compose up -d         # إعادة تشغيل
docker compose logs -f api   # مراقبة السجلات
```

---

## ⚙️ متغيرات البيئة (ENV Variables)

| المتغير | الوصف | القيمة الافتراضية |
|---|---|---|
| `DATABASE_URL` | رابط PostgreSQL | `postgresql://rasid:...@db:5432/rasid` |
| `REDIS_BROKER_URL` | broker لـ Celery | `redis://redis:6379/0` |
| `REDIS_RESULT_BACKEND` | تخزين نتائج tasks | `redis://redis:6379/1` |
| `DOCKER_HOST` | DinD endpoint | `tcp://docker:2375` |
| `ALLOW_PRIVATE_TARGETS` | السماح بفحص RFC1918/loopback | `false` ⚠️ |
| `LOG_LEVEL` | DEBUG/INFO/WARNING/ERROR | `INFO` |
| `CORS_ORIGINS` | origins مسموحة (CSV) | `http://localhost:5173,…` |
| `RATE_LIMIT_STORAGE_URI` | تخزين الـ rate limits | `memory://` |
| `TOOL_<NAME>_IMAGE` | تعديل صورة أداة محددة | حسب الجدول أعلاه |

> ⚠️ **تحذير أمني**: لا تضع `ALLOW_PRIVATE_TARGETS=true` إلا في مختبر معزول.
> هذا الإعداد يُلغي حماية SSRF ويسمح بفحص شبكتك الداخلية.

---

## 📡 ملخّص API Endpoints

### Authentication
- `POST /api/register` — تسجيل (أول مستخدم → Admin).
- `POST /api/login` — تسجيل دخول.
- `GET /api/me` — معلومات الحساب الحالي.

### Scans
- `GET /api/scans?page=&status=&tool=&search=` — قائمة (مع فلاتر).
- `POST /api/scans` — إنشاء `{target, tool}`.
- `GET /api/scans/:id` — تفاصيل + findings + assets + services.
- `DELETE /api/scans/:id` — حذف (يتطلب أن لا يكون RUNNING).
- `POST /api/scans/:id/cancel` — إلغاء soft.
- `GET /api/scans/:id/raw` — stdout/stderr الخام.
- `GET /api/scans/:id/report?format=json|html|md` — تنزيل تقرير.

### Data
- `GET /api/findings?severity=&priority=` — قائمة الثغرات.
- `GET /api/assets` — قائمة الأصول المكتشفة.
- `GET /api/dashboard` — إحصائيات شاملة.

### Tool Commands (FR-12)
- `GET /api/tools` — قائمة الأدوات + flags المسموحة.
- `GET /api/tools/commands` — أوامر المستخدم المحفوظة.
- `POST /api/tools/commands` — إنشاء/تعديل `{tool_name, args, name}`.
- `DELETE /api/tools/commands/:id` — حذف.
- `POST /api/tools/commands/:id/toggle` — تفعيل/إيقاف.

### Notifications
- `GET /api/notifications?unread=1` — قائمة (مع `unread_count`).
- `PUT /api/notifications/:id/read` — تعليم كمقروء.
- `PUT /api/notifications/read-all` — تعليم الكل.

### Legal
- `GET /api/legal/terms` — جلب النص + حالة القبول.
- `POST /api/legal/accept` — تسجيل قبول الشروط.

### Settings
- `POST /api/settings/change-password` — تغيير كلمة المرور.
- `POST /api/settings/rotate-api-key` — تجديد المفتاح.
- `DELETE /api/settings/account` — حذف الحساب (يتطلب password).

### Admin (admin role only)
- `GET /api/admin/users` — قائمة المستخدمين.
- `PUT /api/admin/users/:id` — تعديل role/is_active.
- `GET /api/admin/stats` — إحصائيات.
- `GET /api/admin/audit-logs?action=&page=` — سجل التدقيق.

> كل الـ endpoints (عدا `/register` و `/login`) تتطلّب header
> `X-API-Key: <key>`.

---

## 🗂 بنية المشروع

```
rasid-v5/
├── backend/
│   ├── app/
│   │   ├── api/                # 10 Flask blueprints
│   │   ├── tools/              # registry + runner + parsers + persistence
│   │   │   ├── parsers/        # parser per tool (nmap, httpx, …)
│   │   │   ├── registry.py
│   │   │   ├── runner.py
│   │   │   └── persistence.py
│   │   ├── audit.py            # audit log helper
│   │   ├── auth.py             # API key middleware
│   │   ├── legal.py            # ToS gating
│   │   ├── logging_setup.py
│   │   ├── main.py             # create_app() — thin shell
│   │   ├── models.py           # SQLAlchemy ORM
│   │   ├── serializers.py
│   │   ├── tasks.py            # Celery tasks (one per tool)
│   │   ├── tool_args_validator.py
│   │   └── validation.py       # SSRF-hardened target validation
│   ├── migrations/             # Alembic
│   ├── Dockerfile
│   ├── Dockerfile.nuclei
│   ├── Dockerfile.massdns      # NEW — bundled resolver list
│   ├── docker-compose.yml
│   ├── requirements.txt
│   ├── setup.sh
│   └── .env.example
└── frontend/
    └── src/
        ├── api/                # typed API client
        ├── components/         # Sidebar, Topbar, Badge, Modal, Pagination
        ├── hooks/              # useSession, useNotifications
        ├── types/              # TypeScript definitions
        ├── utils/              # styles, formatters
        ├── views/              # 11 pages (Login, Dashboard, Scans, …)
        ├── App.tsx             # ~ 180 lines — orchestrator
        └── main.tsx
```

---

## 🧠 نظام تقييم المخاطر (Risk Scoring)

```
score = severity_base + port_bonus + web_bonus
```

| المكوّن | القيمة |
|---|---|
| severity_base | info=10, low=30, medium=60, high=85, critical=100 |
| port_bonus | ports {23, 445, 3389} → +10 / {21, 3306, 5432, 5900} → +5 |
| web_bonus | +5 إذا أتى الـ finding من سياق ويب |

ثم يُحوَّل score إلى priority:
- `>= 85` → **critical**
- `>= 60` → **high**
- `>= 25` → **medium**
- وإلا → **low**

---

## 🛡 الأمان

### حماية ضد SSRF
`app/validation.py` يحجب:
- RFC1918 (10/8, 172.16/12, 192.168/16)
- Loopback (127/8, ::1)
- Link-local (169.254/16 — يشمل metadata IPs لـ AWS/GCP)
- أسماء المضيف مثل `localhost`, `metadata.google.internal`
- شخصيات shell injection
- يتم حل اسم المضيف وفحص كل العناوين المُرجَعة

### Custom Args Whitelisting
في `tool_args_validator.py`:
- كل flag يجب أن يكون ضمن `spec.allowed_flags`.
- شخصيات shell injection محظورة في القيم.
- حد أقصى 32 token وكل token ≤ 200 حرف.

### Rate Limiting
- `POST /api/login` → 10/دقيقة
- `POST /api/register` → 5/دقيقة
- `POST /api/scans` → 30/ساعة

### Audit Logging
كل عملية حساسة (login, scan.create, password.change, user.update, …)
تُسجَّل في `audit_logs` مع IP و User-Agent. السجل **append-only**.

---

## 🧪 الاختبارات

```bash
cd backend
pip install -r requirements.txt
pytest tests/
```

التغطية تشمل critical paths:
- المصادقة (register/login/me)
- إنشاء scan + حدود الصلاحيات
- التحقق من target (يحجب RFC1918)
- whitelist للـ custom args
- guest scan limit
- legal acceptance gate

---

## 📜 Legal & Ethical Use

> **هذه أداة تعليمية وأكاديمية**. استخدامها مسؤوليتك الكاملة.

عند أول scan، يطلب النظام منك قبول الشروط:
1. أنت تفحص أهدافاً تملكها أو لديك إذن خطّي صريح بفحصها.
2. عواقب الاستخدام مسؤوليتك (CFAA, GDPR, قوانين بلدك).
3. لن تُستخدم لتجاوز ضوابط أو استغلال ثغرات أو حجب خدمات.

النص الكامل في `backend/app/legal.py`. كل قبول يُسجَّل في
`legal_acceptances` مع IP والإصدار.

---

## 🆚 الفروقات مع v4

| العنصر | v4 | v5 |
|---|---|---|
| عدد الأدوات | 3 (nmap, httpx, nuclei) | **7** (+ subfinder, amass, masscan, massdns) |
| Custom tool args | ❌ | ✅ FR-12 |
| Notifications | ❌ | ✅ FR-10 |
| Audit logging | ❌ | ✅ NFR-7 |
| Legal gating | ❌ | ✅ NFR-9 |
| SSRF protection | فلتر بسيط | تحقق ipaddress + DNS resolution |
| Exception leakage | يُرجع `str(e)` | logged داخلياً + رسالة عامة |
| Rate limiting | ❌ | ✅ Flask-Limiter |
| Frontend structure | 944-line `App.tsx` | 11 views + 5 components + hooks |
| Reports | JSON, HTML | + Markdown |
| Cancel/Delete scan | ❌ | ✅ |
| Tests | ❌ | ✅ pytest critical paths |

---

## 📄 الترخيص

أكاديمي / تعليمي. لا يُسمح بالاستخدام التجاري ولا بإعادة الترخيص.

---

## 🙏 الشكر

- ProjectDiscovery (httpx, nuclei, subfinder)
- OWASP Amass team
- Robert Graham (masscan)
- Blechschmidt (massdns)
- Flask & Celery teams
- React team

Built with ❤️ for security education.
