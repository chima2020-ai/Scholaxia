from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.redis import init_redis, close_redis
from app.core.seed import seed_database

from app.routers import auth, students, admin, live_class, cbt, community, ai_tutor, notifications, payments
from app.routers import developer_auth, developer_keys, public_ai_api, reviews_reports, teacher_ai, library
from app.websockets.live_class_ws import live_class_endpoint


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()
    # Seed default admin + community channels
    async with AsyncSessionLocal() as db:
        await seed_database(db)
    yield
    # Shutdown
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title="Scholaxia API — Powered by Sia",
    description="Scholaxia educational ecosystem. Student AI tutor: Sia (Scholaxia Intelligent Assistant)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(students.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(live_class.router, prefix="/api/v1")
app.include_router(cbt.router, prefix="/api/v1")
app.include_router(community.router, prefix="/api/v1")
app.include_router(ai_tutor.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(reviews_reports.router, prefix="/api/v1")
app.include_router(teacher_ai.router, prefix="/api/v1")
app.include_router(library.router, prefix="/api/v1")

# Developer Portal — API key management
app.include_router(developer_auth.router, prefix="/api/v1")
app.include_router(developer_keys.router, prefix="/api/v1")

# Public AI API — external developers call this with their API key
app.include_router(public_ai_api.router, prefix="/api")


# WebSocket — Live Class
@app.websocket("/ws/live-class/{room_id}")
async def live_class_ws(
    websocket: WebSocket,
    room_id: str,
    user_id: str = Query(...),
    role: str = Query(...),
):
    await live_class_endpoint(websocket, room_id, user_id, role)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
