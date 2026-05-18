import urllib.request, json

BASE = "https://scholaxia.onrender.com"

def get(path, expect_json=True):
    req = urllib.request.Request(BASE + path)
    try:
        r = urllib.request.urlopen(req, timeout=30)
        raw = r.read()
        if expect_json:
            return r.status, json.loads(raw)
        return r.status, raw.decode()[:100]
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode()[:200]

def ok(label, status, expected=None):
    exp = expected or [200, 201]
    icon = "PASS" if status in exp else "FAIL"
    print(f"[{icon}] {label} -> HTTP {status}")

print("=" * 50)
print("SCHOLAXIA PUBLIC API TESTS")
print("=" * 50)

# 1. Health
s, r = get("/health")
ok("Health check", s)
print(f"     {r}")

# 2. Swagger docs
s, r = get("/docs", expect_json=False)
ok("Swagger UI", s)

# 3. OpenAPI schema
s, r = get("/openapi.json")
ok("OpenAPI schema", s)
routes = len(r.get("paths", {})) if isinstance(r, dict) else 0
print(f"     Total API routes: {routes}")

# 4. Community channels
s, r = get("/api/v1/community/channels")
ok("Community channels", s)
if isinstance(r, list):
    for ch in r:
        print(f"     - {ch.get('name')} ({ch.get('type')})")

# 5. Sia about
s, r = get("/api/v1/sia/about")
ok("Sia identity", s)
if isinstance(r, dict):
    print(f"     Name: {r.get('name')}")
    print(f"     Tagline: {r.get('tagline')}")
    print(f"     Capabilities: {len(r.get('capabilities', []))}")

# 6. Sia languages
s, r = get("/api/v1/sia/languages")
ok("Sia languages", s)
if isinstance(r, dict):
    print(f"     Total: {r.get('total')} languages")
    for region, langs in r.get("languages_by_region", {}).items():
        print(f"     {region}: {len(langs)}")

# 7. Public AI models
s, r = get("/api/v1/ai/models")
ok("Public AI models", s)
if isinstance(r, dict):
    for m in r.get("models", []):
        print(f"     {m.get('name')} - {m.get('id')}")

# 8. Auth endpoints exist (405 = route exists, wrong method)
s, r = get("/api/v1/auth/login", expect_json=False)
ok("Auth login route exists", s, [200, 201, 405, 422])

s, r = get("/api/v1/auth/student/signup", expect_json=False)
ok("Student signup route exists", s, [200, 201, 405, 422])

s, r = get("/api/v1/admin/register", expect_json=False)
ok("Admin register route exists", s, [200, 201, 405, 422])

# 9. Protected routes return 401/403 without token
s, r = get("/api/v1/students/me")
ok("Students/me requires auth", s, [401, 403, 422])

s, r = get("/api/v1/sia/ask", expect_json=False)
ok("Sia/ask requires auth", s, [401, 403, 405, 422])

s, r = get("/api/v1/admin/teachers")
ok("Admin/teachers requires auth", s, [401, 403, 422])

print()
print("=" * 50)
print("PUBLIC TESTS COMPLETE")
print("=" * 50)
