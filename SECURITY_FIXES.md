# 🔧 RASID — تقرير إصلاحات الأمان والأعطال

> تم تطبيق هذه الإصلاحات على نسخة `rasid-v5`. كل تعديل مُعلَّق عليه في الكود بـ comment يوضح السبب.
> **النتيجة: 82/82 اختبار ناجح** (71 اختبار موجود + 11 اختبار جديد).

---

## 🔴 ثغرات حرجة (Critical)

### 1. SSRF / Shell-Injection يُسجَّل في DB قبل الرفض
**الملف:** `backend/app/api/scan_routes.py`

**المشكلة:**
`create_scan` كان يُنشئ صف `ScanJob` ويزيد `scan_count` ويكتب audit log قبل أن يتحقق Celery worker من الهدف. مهاجم يستطيع إغراق DB بسجلات scans لأهداف مثل `127.0.0.1` أو `169.254.169.254` (cloud metadata) أو `example.com; rm -rf /`.

**الإصلاح:**
استدعاء `validate_target()` قبل أي عملية كتابة على DB. كما أعدنا ترتيب الفحوصات (legal acceptance, guest limit) لتسبق إنشاء أي صف.

```python
# قبل إنشاء أي صف:
target_check = validate_target(target)
if not target_check.ok:
    return jsonify({"ok": False, "error": target_check.reason}), 400
```

---

### 2. XSS في تقارير HTML
**الملف:** `backend/app/api/report_routes.py`

**المشكلة:**
الـ findings تأتي من مخرجات أدوات scanning خارجية (httpx titles, nuclei evidence). كانت تُحقَن في HTML report بدون escaping:
```python
<td>{f.title}</td>   # f.title يمكن أن يكون <script>alert(1)</script>
```

**الإصلاح:**
- استخدام `html.escape()` على كل قيمة قبل الـ interpolation
- إضافة Content-Security-Policy header (`default-src 'none'; style-src 'unsafe-inline'`)
- إضافة `X-Content-Type-Options: nosniff` لكل الـ download responses

---

### 3. XML External Entity (XXE) / Billion Laughs
**الملفات:** `backend/app/tools/parsers/nmap_parser.py` + `requirements.txt`

**المشكلة:**
`xml.etree.ElementTree.fromstring` على مدخلات نصف موثوقة. حتى لو كان مصدر XML داخل DinD، أي تأثير من الـ target على XML المُنتَج يمكن استغلاله.

**الإصلاح:**
استخدام `defusedxml` (مع fallback إلى stdlib).

---

### 4. تنزيل التقارير معطّل
**الملفات:** `frontend/src/api/client.ts` + `frontend/src/views/ScanModal.tsx`

**المشكلة:**
`reportUrl()` كانت ترجع رابط مباشر، لكن endpoint محمي بـ `X-API-Key`. عند `window.open(reportUrl)` المستخدم يحصل على 401.

**الإصلاح:**
دالة `downloadReport()` مركزية تستخدم `fetch` مع API key header + blob download:
```typescript
const res = await fetch(url, { headers: { "X-API-Key": apiKey } });
const blob = await res.blob();
const objectUrl = URL.createObjectURL(blob);
// trigger anchor download...
```

---

## 🟠 ثغرات أمنية مهمة

### 5. Timing Attack على Login (Account Enumeration)
**الملف:** `backend/app/api/auth_routes.py`

**المشكلة:**
عند email غير موجود، `verify_password` لا يُنفَّذ. الفرق في وقت الاستجابة (scrypt بطيء عمداً) يكشف وجود المستخدم.

**الإصلاح:**
ثابت hash مُسبق + تنفيذ `verify_password` ضده عندما لا يوجد مستخدم. وقت الاستجابة متقارب لـ "email غير موجود" و "كلمة المرور خاطئة".

```python
_DUMMY_PASSWORD_HASH = hash_password("...")
if user is None:
    verify_password(password, _DUMMY_PASSWORD_HASH)
    return ..., 401
```

---

### 6. DoS عبر طلبات كبيرة
**الملف:** `backend/app/main.py`

**المشكلة:**
لا حد لحجم JSON body. مهاجم يرسل 1GB body فيستهلك RAM/CPU.

**الإصلاح:**
`MAX_CONTENT_LENGTH = 1 MiB` + handler لـ 413.

---

### 7. Suspended Admin لا يفقد صلاحياته
**الملف:** `backend/app/auth.py`

**المشكلة:**
`require_admin` يفحص `role == admin` لكن لا يفحص `is_active`. admin مُعلَّق يستطيع استخدام endpoints حساسة.

**الإصلاح:**
إضافة `if not user.is_active: return 403` في `require_admin` (كان موجود في `require_api_key` فقط).

---

### 8. JSON مكسور يُسبّب 500
**الملف:** `backend/app/auth.py` + جميع الـ routes

**المشكلة:**
`request.get_json(force=True)` يرفع `BadRequest` على JSON مكسور.

**الإصلاح:**
Helper مركزي `get_json_body()`:
```python
data = request.get_json(force=True, silent=True)
if not isinstance(data, dict):
    return {}
return data
```

---

### 9. IP Spoofing في Audit Logs
**الملفات:** `backend/app/audit.py` + `backend/app/api/legal_routes.py`

**المشكلة:**
`X-Forwarded-For` يُؤخذ بثقة دائماً. أي client يرسل `X-Forwarded-For: 1.2.3.4` فيُسجَّل في audit log كمصدر الطلب.

**الإصلاح:**
- بدون متغير بيئي → استخدام `request.remote_addr` فقط (لا يُمكن انتحاله)
- مع `TRUST_PROXY_HEADERS=true` → أخذ أول عنوان من `X-Forwarded-For` (للنشر خلف reverse proxy موثوق فقط)

---

### 10. Exception Leakage عبر API
**الملف:** `backend/app/tasks.py`

**المشكلة:**
```python
job.error_message = f"{type(e).__name__}: {e}"
```
رسالة الخطأ تحتوي على `str(e)` الذي قد يكشف paths, SQL queries, container IDs… ويُعرض للمستخدم عبر `/scans/:id` و `/scans/:id/raw`.

**الإصلاح:**
- Full traceback في server log فقط (`logger.exception`)
- المستخدم يرى `"Internal error (ClassName)"` فقط

---

### 11. Hash Algorithm غير صريح
**الملف:** `backend/app/security.py`

**المشكلة:**
`generate_password_hash(password)` يعتمد على default werkzeug، الذي قد يتغير في الإصدارات القادمة.

**الإصلاح:**
Pin algorithm + salt length صراحة:
```python
_HASH_METHOD = "scrypt:32768:8:1"
_SALT_LENGTH = 16
```

---

### 12. Rate Limiting موسّع
**الملف:** `backend/app/main.py`

**الإضافات:**
- `settings.change_password` → 10/hour
- `settings.rotate_api_key` → 10/hour
- `settings.delete_account` → 10/hour
- `reports.download_report` → 60/hour

---

## 🧪 الاختبارات

### الموجودة (لا تزال تنجح)
- `test_auth.py` — 11 ✅
- `test_legal.py` — 3 ✅
- `test_scans.py` — 11 ✅
- `test_tool_args_validator.py` — 12 ✅
- `test_validation.py` — 34 ✅

### الجديدة (`test_security_fixes.py`) — 11 اختبار ✅
1. `test_private_ip_target_rejected_before_scanjob_created` — يثبت أن `10.0.0.1` يُرفض قبل إنشاء أي صف DB
2. `test_loopback_target_rejected_up_front` — `127.0.0.1`
3. `test_metadata_hostname_rejected_up_front` — `metadata.google.internal`
4. `test_shell_metachars_target_rejected_up_front` — `example.com; rm -rf /`
5. `test_html_report_escapes_finding_fields` — يحقن `<script>`, `<img onerror>`, `&` في finding ويتأكد أن HTML report يحتوي على نسخها المُهرَّبة فقط
6. `test_suspended_admin_loses_admin_access` — admin مُعلَّق → 403
7. `test_malformed_json_body_returns_400_not_500`
8. `test_non_object_json_body_returns_400` — JSON array بدل dict
9. `test_oversized_request_rejected` — 2MB body → 413
10. `test_report_download_requires_api_key` — بدون header → 401
11. `test_login_unknown_email_still_returns_401`

**النتيجة الإجمالية: 82/82 ✅**

---

## ⚠️ مشاكل أمنية متبقية (تتطلب إعادة هندسة لمعالجتها)

| # | المشكلة | الأثر | الحل المُقترح |
|---|---------|-------|---------------|
| A | API key في `localStorage` | XSS = سرقة كامل الـ session | httpOnly cookie + CSRF token |
| B | Docker socket عبر TCP بدون TLS (`tcp://docker:2375`) | container على نفس الـ network يتحكم بالـ host | `DOCKER_TLS_VERIFY=1` + certificates، أو Unix socket مع volume |
| C | DNS Rebinding بعد validation | DNS قد يُحلّ لـ public IP وقت التحقق، ثم private IP وقت التنفيذ | تثبيت الـ IP المُحلَّل وتمريره مباشرة للأداة |
| D | لا يوجد cancel فعلي للـ containers | الـ "Cancel" حالياً soft فقط (يُعلّم scan كـ FAILED بدون قتل container) | Celery `revoke` + `container.kill` |
| E | لا يوجد session expiry | API key لا ينتهي تلقائياً | إضافة `expires_at` + refresh flow |

---

## 🚀 طريقة التشغيل بعد الإصلاحات

نفس الخطوات السابقة، مع ملاحظتين:

1. **إعادة تثبيت dependencies** (لإضافة `defusedxml`):
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **خلف reverse proxy؟** عيّن:
   ```bash
   export TRUST_PROXY_HEADERS=true
   ```
   وإلا سيُسجَّل IP الـ proxy بدل IP العميل في audit logs (وهذا آمن لكنه ليس ما تريده).

3. **تشغيل الاختبارات للتحقق:**
   ```bash
   cd backend
   pytest tests/
   # 82 passed
   ```
