"""
Sia AI Capability Test
Tests every Sia mode with real educational questions.
"""
import urllib.request, urllib.error, json, random, string

BASE = "https://scholaxia.onrender.com"

def post(path, data, token=None):
    body = json.dumps(data).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=90)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return 0, str(e)[:100]

def get(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]

def divider(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")

# ── Get student token ─────────────────────────────────────
e = "sia_" + "".join(random.choices(string.ascii_lowercase, k=5)) + "@test.com"
s, r = post("/api/v1/auth/student/signup", {
    "email": e, "password": "Test1234!", "full_name": "Amaka Obi"
})
token = r.get("access_token", "") if isinstance(r, dict) else ""

# Setup exam profile
post("/api/v1/students/setup-exam", {
    "exam_type": "WAEC",
    "subjects": ["Mathematics", "Physics", "Chemistry", "Biology", "English"],
    "education_level": "SS3"
}, token=token)

print("=" * 60)
print("  SIA AI CAPABILITY TEST")
print(f"  Student: Amaka Obi | Level: SS3 | Exam: WAEC")
print("=" * 60)

# ── Mode 1: Ask ───────────────────────────────────────────
divider("MODE 1: ASK — General Question")
s, r = post("/api/v1/sia/ask", {
    "question": "What is Newton's third law of motion?",
    "subject": "Physics",
    "language": "english"
}, token=token)
print(f"Status: {s}")
if isinstance(r, dict):
    print(f"\nSia says:\n{r.get('sia', '')}\n")

# ── Mode 2: Explain ───────────────────────────────────────
divider("MODE 2: EXPLAIN — Step-by-step concept")
s, r = post("/api/v1/sia/explain", {
    "topic": "Photosynthesis",
    "subject": "Biology",
    "language": "english"
}, token=token)
print(f"Status: {s}")
if isinstance(r, dict):
    print(f"\nSia says:\n{r.get('sia', '')}\n")

# ── Mode 3: Solve ─────────────────────────────────────────
divider("MODE 3: SOLVE — Step-by-step problem")
s, r = post("/api/v1/sia/solve", {
    "question": "A car travels 120km in 2 hours. What is its average speed?",
    "subject": "Physics",
    "language": "english"
}, token=token)
print(f"Status: {s}")
if isinstance(r, dict):
    print(f"\nSia says:\n{r.get('sia', '')}\n")

# ── Mode 4: Evaluate ──────────────────────────────────────
divider("MODE 4: EVALUATE — Mark student answer")
s, r = post("/api/v1/sia/evaluate", {
    "question": "What is the chemical formula for water?",
    "student_answer": "H3O",
    "subject": "Chemistry",
    "language": "english"
}, token=token)
print(f"Status: {s}")
if isinstance(r, dict):
    print(f"\nSia says:\n{r.get('sia', '')}\n")

# ── Mode 5: Generate Questions ────────────────────────────
divider("MODE 5: GENERATE QUESTIONS — Practice set")
s, r = post("/api/v1/sia/generate-questions", {
    "topic": "Quadratic Equations",
    "subject": "Mathematics",
    "number": 3,
    "curriculum": "WAEC",
    "language": "english"
}, token=token)
print(f"Status: {s}")
if isinstance(r, dict):
    print(f"\nSia says:\n{r.get('sia', '')}\n")

# ── Mode 6: Explain Wrong Answer ─────────────────────────
divider("MODE 6: EXPLAIN WRONG ANSWER")
s, r = post("/api/v1/sia/explain-wrong", {
    "question": "What is the capital of Nigeria?",
    "wrong_answer": "Lagos",
    "correct_answer": "Abuja",
    "subject": "Geography",
    "language": "english"
}, token=token)
print(f"Status: {s}")
if isinstance(r, dict):
    print(f"\nSia says:\n{r.get('sia', '')}\n")

# ── Mode 7: Feedback ──────────────────────────────────────
divider("MODE 7: PERFORMANCE FEEDBACK")
s, r = post("/api/v1/sia/feedback", {
    "subject": "Mathematics",
    "score": 45.0,
    "language": "english"
}, token=token)
print(f"Status: {s}")
if isinstance(r, dict):
    print(f"\nSia says:\n{r.get('sia', '')}\n")

# ── Language Test: Yoruba ─────────────────────────────────
divider("LANGUAGE TEST: Yoruba")
s, r = post("/api/v1/sia/ask", {
    "question": "What is photosynthesis?",
    "subject": "Biology",
    "language": "yoruba"
}, token=token)
print(f"Status: {s}")
if isinstance(r, dict):
    print(f"\nSia says (Yoruba):\n{r.get('sia', '')}\n")

# ── Language Test: Hausa ──────────────────────────────────
divider("LANGUAGE TEST: Hausa")
s, r = post("/api/v1/sia/ask", {
    "question": "What is 2 + 2?",
    "subject": "Mathematics",
    "language": "hausa"
}, token=token)
print(f"Status: {s}")
if isinstance(r, dict):
    print(f"\nSia says (Hausa):\n{r.get('sia', '')}\n")

# ── Safety Filter Test ────────────────────────────────────
divider("SAFETY FILTER TEST — Off-topic question")
s, r = post("/api/v1/sia/ask", {
    "question": "Who is the president of Nigeria?",
    "subject": "Politics",
    "language": "english"
}, token=token)
print(f"Status: {s}")
if isinstance(r, dict):
    sia_response = r.get("sia", "")
    print(f"\nSia says:\n{sia_response}\n")
    blocked = "only" in sia_response.lower() or "educational" in sia_response.lower()
    print(f"Safety filter working: {'YES' if blocked else 'CHECK MANUALLY'}")

# ── Teacher AI ────────────────────────────────────────────
divider("TEACHER AI — Quiz generation")
# Get teacher token
s2, r2 = post("/api/v1/auth/login", {
    "email": "teacher@scholaxia.com", "password": "Teacher123!"
})
teacher_token = r2.get("access_token", "") if isinstance(r2, dict) else ""

if teacher_token:
    s, r = post("/api/v1/teacher-ai/ask", {
        "task": "quiz",
        "subject": "Chemistry",
        "education_level": "SS2",
        "details": "Create 3 WAEC-style questions on acids and bases with answers"
    }, token=teacher_token)
    print(f"Status: {s}")
    if isinstance(r, dict):
        print(f"\nTeacher Sia says:\n{r.get('result', '')}\n")
else:
    print("No teacher token — skipped")

print("=" * 60)
print("  SIA CAPABILITY TEST COMPLETE")
print("=" * 60)
