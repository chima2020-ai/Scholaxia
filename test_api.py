import urllib.request, json

BASE = "https://scholaxia1.onrender.com"

def post(path, data, token=None):
    body = json.dumps(data).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=30)
        raw = r.read()
        return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode()[:300]

def get(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode()[:300]

def ok(label, status, expected=None):
    exp = expected or [200, 201]
    icon = "PASS" if status in exp else "FAIL"
    print(f"[{icon}] {label} -> HTTP {status}")

results = {}

# 1. Health
s, r = get("/health")
ok("Health check", s)
results["health"] = s

# 2. Admin register
s, r = post("/api/v1/admin/register", {
    "email": "admin@scholaxia.com",
    "password": "ScholaxiaAdmin2026",
    "full_name": "Scholaxia Admin",
    "invite_code": "SCHOLAXIA_ADMIN_2026"
})
ok("Admin register", s, [200, 201, 400])
admin_token = r.get("access_token", "") if isinstance(r, dict) else ""
detail = r.get("detail", "") if isinstance(r, dict) else str(r)
print(f"     {detail or 'Token received'}")

# 3. Admin login fallback
if not admin_token:
    s, r = post("/api/v1/auth/login", {
        "email": "admin@scholaxia.com",
        "password": "ScholaxiaAdmin2026"
    })
    ok("Admin login", s)
    admin_token = r.get("access_token", "") if isinstance(r, dict) else ""

print(f"     Admin token: {'OK' if admin_token else 'MISSING'}")

# 4. Community channels
s, r = get("/api/v1/community/channels")
ok("List channels", s)
channels = r if isinstance(r, list) else []
general_id = next((c["id"] for c in channels if c.get("type") == "general"), None)
print(f"     Channels: {len(channels)}, General ID: {general_id}")

# 5. Student signup
s, r = post("/api/v1/auth/student/signup", {
    "email": "chidi@test.com",
    "password": "Student123!",
    "full_name": "Chidi Okafor"
})
ok("Student signup", s, [200, 201, 400])
msg = r.get("message", r.get("detail", "")) if isinstance(r, dict) else str(r)
print(f"     {msg}")

# 6. Sia about
s, r = get("/api/v1/sia/about")
ok("Sia about", s)
name = r.get("name", "") if isinstance(r, dict) else ""
print(f"     AI name: {name}")

# 7. Sia languages
s, r = get("/api/v1/sia/languages")
ok("Sia languages", s)
total = r.get("total", 0) if isinstance(r, dict) else 0
print(f"     Total languages: {total}")

# 8. Create teacher (admin only)
if admin_token:
    s, r = post("/api/v1/admin/teachers", {
        "email": "teacher@scholaxia.com",
        "password": "Teacher123!",
        "full_name": "Mr Emeka",
        "subjects": ["Mathematics", "Physics"],
        "bio": "Experienced teacher"
    }, token=admin_token)
    ok("Create teacher", s, [200, 201, 400])
    tid = r.get("id", r.get("detail", "")) if isinstance(r, dict) else str(r)
    print(f"     {tid}")

    # 9. List teachers
    s, r = get("/api/v1/admin/teachers", token=admin_token)
    ok("List teachers", s)
    count = len(r) if isinstance(r, list) else 0
    print(f"     Teachers: {count}")

    # 10. Teacher login
    s, r = post("/api/v1/auth/login", {
        "email": "teacher@scholaxia.com",
        "password": "Teacher123!"
    })
    ok("Teacher login", s, [200, 201, 403])
    teacher_token = r.get("access_token", "") if isinstance(r, dict) else ""
    print(f"     Teacher token: {'OK' if teacher_token else r.get('detail', 'MISSING')}")

    # 11. Create live class
    if teacher_token:
        s, r = post("/api/v1/live-classes/", {
            "subject": "Mathematics",
            "title": "Quadratic Equations",
            "start_time": "2026-06-01T10:00:00"
        }, token=teacher_token)
        ok("Create live class", s, [200, 201])
        class_id = r.get("id", "") if isinstance(r, dict) else ""
        print(f"     Class ID: {class_id}")

# 12. Developer signup
s, r = post("/api/v1/developer/auth/signup", {
    "email": "dev@myapp.com",
    "password": "Dev123456!",
    "full_name": "Test Developer",
    "company_name": "TestCo"
})
ok("Developer signup", s, [200, 201, 400])
dev_token = r.get("access_token", "") if isinstance(r, dict) else ""
print(f"     Dev token: {'OK' if dev_token else r.get('detail', 'MISSING')}")

# 13. Create API key
if dev_token:
    s, r = post("/api/v1/developer/keys/", {
        "name": "Test Key",
        "tier": "free"
    }, token=dev_token)
    ok("Create API key", s, [200, 201])
    api_key = r.get("key", "") if isinstance(r, dict) else ""
    print(f"     API key: {api_key[:20] + '...' if api_key else 'MISSING'}")

print()
print("=" * 40)
print("TEST COMPLETE")
