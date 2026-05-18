# Scholaxia Backend

FastAPI + PostgreSQL + Redis

## Stack
- **FastAPI** — async REST API + WebSockets
- **PostgreSQL** — primary database (via SQLAlchemy async)
- **Redis** — caching, sessions, Celery broker
- **Celery** — background tasks (notifications, analytics)
- **AWS S3** — media storage (books, videos, notes)
- **Stripe** — payments & subscriptions
- **Firebase FCM** — push notifications
- **OpenAI GPT-4o** — AI tutor

## Setup

```bash
cd scholaxia
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # fill in your values
```

## Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Docs
- Swagger: http://localhost:8000/docs
- Redoc:   http://localhost:8000/redoc

## Project Structure

```
app/
├── core/           # config, database, redis, security, deps
├── models/         # SQLAlchemy ORM models
├── routers/        # FastAPI route handlers
├── services/       # business logic (AI, notifications, moderation, media)
└── websockets/     # WebSocket handlers (live class)
```
