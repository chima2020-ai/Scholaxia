# Scholaxia — Local Testing Guide

## Prerequisites

- Python 3.11+ (already installed)
- PostgreSQL 16
- Redis for Windows
- Ollama (optional — only needed for AI endpoints)

---

## 1. Install PostgreSQL (Windows)

1. Download from https://www.postgresql.org/download/windows/
   - Click "Download the installer" → pick version 16 → Windows x86-64
2. Run the installer
   - Keep default port: **5432**
   - Set a password for the `postgres` superuser — remember it
   - Keep all default components checked
3. After install, open **pgAdmin** or **SQL Shell (psql)** from the Start menu
4. Create the database:

```sql
-- In SQL Shell (psql), connect as postgres then run:
CREATE USER scholaxia WITH PASSWORD 'scholaxia123';
CREATE DATABASE scholaxia OWNER scholaxia;
```

Or using psql command line (after adding PostgreSQL to PATH):
```
psql -U postgres -c "CREATE USER scholaxia WITH PASSWORD 'scholaxia123';"
psql -U postgres -c "CREATE DATABASE scholaxia OWNER scholaxia;"
```

---

## 2. Install Redis (Windows)

Redis doesn't have an official Windows build, but Memurai is a drop-in replacement:

1. Download **Memurai** (free) from https://www.memurai.com/get-memurai
2. Run the installer — it installs as a Windows service and starts automatically on port **6379**
3. Verify it's running: open Command Prompt and type `memurai-cli ping` — should return `PONG`

Alternative: use the unofficial Redis Windows port from https://github.com/microsoftarchive/redis/releases
- Download `Redis-x64-3.0.504.msi` and install it — also runs as a Windows service on port 6379

---

## 3. Install Python dependencies

Your venv is already created and most packages are installed. Run this to make sure everything is complete:

```
cd "C:\Users\EMMA\New folder (2)\scholaxia"
venv\Scripts\activate
pip install -r requirements.txt
```

---

## 4. Configure .env

The `.env` file is already created with local defaults.

Fill in only what you need to test:

| Service | Required for | Where to get |
|---|---|---|
| `CLOUDINARY_*` | Book/image upload | cloudinary.com (free account) |
| `BREVO_API_KEY` | OTP emails | app.brevo.com (free: 300/day) |
| `STRIPE_SECRET_KEY` | Payments | dashboard.stripe.com/test/apikeys |
| `FIREBASE_CREDENTIALS_PATH` | Push notifications | Firebase Console |

> For testing auth, CBT, community, library browsing — you do NOT need Cloudinary, Brevo, or Stripe.
> The app will start and most endpoints will work without them.

---

## 5. Start the AI (optional)

If you want to test the AI tutor endpoints:

1. Download Ollama from https://ollama.com/download/windows
2. Install and run it — it starts automatically
3. Open a new terminal and run:
```
ollama pull mistral
```
Ollama runs at `http://localhost:11434` — matches the `.env` default.

---

## 6. Run the server

```
cd "C:\Users\EMMA\New folder (2)\scholaxia"
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

On first startup it will:
- Create all database tables automatically
- Create the admin account (`admin@scholaxia.com` / `Admin1234!`)
- Create the two community channels (General + Teacher Announcements)

---

## 7. Open the API docs

```
http://localhost:8000/docs
```

This is Swagger UI — you can test every endpoint directly from the browser.

Also available:
```
http://localhost:8000/redoc
```

---

## 8. Testing flow — step by step

### Step 1 — Login as Admin
```
POST /api/v1/auth/login
{
  "email": "admin@scholaxia.com",
  "password": "Admin1234!"
}
```
Copy the `access_token`. Click **Authorize** in Swagger and paste it.

---

### Step 2 — Create a Teacher (Admin only)
```
POST /api/v1/admin/teachers
{
  "email": "teacher@test.com",
  "password": "Teacher123!",
  "full_name": "Mr. Emeka",
  "subjects": ["Mathematics", "Physics"],
  "bio": "10 years experience"
}
```

---

### Step 3 — Student Signup
```
POST /api/v1/auth/student/signup
{
  "email": "student@test.com",
  "password": "Student123!",
  "full_name": "Chidi Okafor"
}
```
> If Brevo is not configured, the signup will fail at the OTP send step.
> To bypass OTP for local testing, temporarily set `is_verified=True` directly in the DB,
> or use a DB client like TablePlus / DBeaver to update the users table.

---

### Step 4 — Verify Email (if Brevo is configured)
```
POST /api/v1/auth/verify-email
{
  "email": "student@test.com",
  "otp": "123456"
}
```

---

### Step 5 — Student Login
```
POST /api/v1/auth/login
{
  "email": "student@test.com",
  "password": "Student123!"
}
```

---

### Step 6 — Setup Exam
```
POST /api/v1/students/setup-exam
Authorization: Bearer <student_token>
{
  "exam_type": "JAMB",
  "subjects": ["Mathematics", "English", "Physics", "Chemistry"],
  "education_level": "SS3"
}
```

---

### Step 7 — Get Student Profile
```
GET /api/v1/students/me
Authorization: Bearer <student_token>
```

---

### Step 8 — Community: List Channels
```
GET /api/v1/community/channels
```

---

### Step 9 — Community: Join General Channel
```
POST /api/v1/community/join
Authorization: Bearer <student_token>
{
  "channel_id": "<id from list channels>"
}
```
> Requires active subscription. To bypass locally, update `has_active_subscription=true`
> in the `student_profiles` table directly.

---

### Step 10 — Community: Send Message
```
POST /api/v1/community/messages
Authorization: Bearer <student_token>
{
  "channel_id": "<channel_id>",
  "content": "Hello everyone, can someone explain Newton's third law?"
}
```

---

### Step 11 — Teacher Login
```
POST /api/v1/auth/login
{
  "email": "teacher@test.com",
  "password": "Teacher123!"
}
```

---

### Step 12 — Create a Live Class
```
POST /api/v1/live-classes/
Authorization: Bearer <teacher_token>
{
  "subject": "Mathematics",
  "title": "Quadratic Equations",
  "start_time": "2026-05-20T10:00:00"
}
```

---

### Step 13 — Start the Live Class
```
POST /api/v1/live-classes/<class_id>/start
Authorization: Bearer <teacher_token>
```
This sends notifications to all students who selected Mathematics.

---

### Step 14 — Student Joins Live Class
```
POST /api/v1/live-classes/<class_id>/join
Authorization: Bearer <student_token>
```

---

### Step 15 — WebSocket: Live Class
Connect to:
```
ws://localhost:8000/ws/live-class/<room_id>?user_id=<user_id>&role=student
```
Send JSON events:
```json
{ "event": "chat", "text": "Hello teacher!" }
{ "event": "raise_hand" }
{ "event": "whiteboard", "action": "draw", "data": {...} }
```

---

### Step 16 — Admin: Add a Book to Student Library
```
# First get upload signature
POST /api/v1/admin/library/upload-url
Authorization: Bearer <admin_token>

# Upload PDF directly to Cloudinary using the returned signature
# Then register the book:
POST /api/v1/admin/library/books
Authorization: Bearer <admin_token>
{
  "title": "JAMB Mathematics Past Questions",
  "subject": "Mathematics",
  "exam_type": "JAMB",
  "file_key": "<cloudinary_public_id>",
  "library_target": "student"
}
```

---

### Step 17 — Student: Browse Library
```
GET /api/v1/library/student?subject=Mathematics
Authorization: Bearer <student_token>
```

---

### Step 18 — Student: Open a Book (get signed read URL)
```
GET /api/v1/library/<book_id>/read
Authorization: Bearer <student_token>
```
Returns a 30-minute signed URL. DRM flags are in the `drm` object.

---

### Step 19 — Student: Save a Book
```
POST /api/v1/library/<book_id>/save
Authorization: Bearer <student_token>
```

---

### Step 20 — CBT: Start an Exam Session
First create an exam as admin/teacher, then:
```
POST /api/v1/cbt/sessions/<exam_id>/start
Authorization: Bearer <student_token>
```

---

### Step 21 — CBT: Submit Answers
```
POST /api/v1/cbt/sessions/submit
Authorization: Bearer <student_token>
{
  "session_id": "<session_id>",
  "answers": {
    "<question_id>": "A",
    "<question_id>": "C"
  },
  "is_auto_submit": false
}
```

---

### Step 22 — AI Tutor
```
POST /api/v1/ai/ask
Authorization: Bearer <student_token>
{
  "question": "Explain Newton's third law of motion",
  "subject": "Physics",
  "education_level": "SS2",
  "language": "english"
}
```
> Requires Ollama running locally with `ollama serve`.

---

### Step 23 — Teacher AI
```
POST /api/v1/teacher-ai/ask
Authorization: Bearer <teacher_token>
{
  "task": "quiz",
  "subject": "Mathematics",
  "education_level": "SS3",
  "details": "Create 5 multiple choice questions on quadratic equations"
}
```

---

### Step 24 — Developer Portal: Register
```
POST /api/v1/developer/auth/signup
{
  "email": "dev@myapp.com",
  "password": "Dev123!",
  "full_name": "John Dev",
  "company_name": "MyApp Ltd"
}
```

---

### Step 25 — Developer Portal: Create API Key
```
POST /api/v1/developer/keys/
Authorization: Bearer <developer_token>
{
  "name": "My App Key",
  "tier": "free"
}
```
Save the `key` — it is shown only once.

---

### Step 26 — Public AI API (external developer)
```
POST /api/v1/ai/ask
x-api-key: sxa_live_...
{
  "question": "What is photosynthesis?",
  "subject": "Biology",
  "education_level": "JSS3",
  "language": "english"
}
```

---

### Step 27 — Payments: Create Checkout
```
POST /api/v1/payments/checkout
Authorization: Bearer <student_token>
{
  "plan": "premium"
}
```
Returns a Stripe `client_secret`. Use Stripe test card `4242 4242 4242 4242` in the frontend.

---

### Step 28 — Reviews: Submit Teacher Review
```
POST /api/v1/reviews-reports/reviews
Authorization: Bearer <student_token>
{
  "teacher_id": "<teacher_id>",
  "rating": 5,
  "comment": "Great teacher, very clear explanations",
  "is_anonymous": false
}
```

---

### Step 29 — Reports: Submit a Report
```
POST /api/v1/reviews-reports/reports
Authorization: Bearer <student_token>
{
  "target_id": "<user_id>",
  "target_type": "student",
  "reason": "spam",
  "description": "Keeps sending off-topic messages"
}
```

---

## 9. Health check

```
GET http://localhost:8000/health
```
Should return: `{ "status": "ok", "app": "Scholaxia" }`

---

## 10. Stop local services

PostgreSQL and Redis run as Windows services — they stay running in the background.
To stop them: open **Services** (search in Start menu), find `postgresql-x64-16` and `Memurai`, right-click → Stop.

---

## 11. Deploying to Render

1. Push code to GitHub
2. Go to [render.com](https://render.com) and create a new Web Service
3. Connect your GitHub repo
4. Render will detect `render.yaml` and configure everything automatically
5. Add your secret env vars (Cloudinary, Brevo, Stripe, Firebase) in the Render dashboard
6. Deploy

