from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audit, auth, incidents, monitoring, systems
from app.config import settings
from app.database import SessionLocal, init_db
from app.seed import seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if settings.seed_demo_data:
        with SessionLocal() as db:
            seed(db)
    yield


app = FastAPI(
    title="Syntra API",
    version="0.1.0",
    description=(
        "Syntra — Connected Systems Intelligence. An intelligent enterprise IT platform for monitoring "
        "connected systems, managing integrations and incidents, supporting GxP lifecycle workflows, "
        "and providing AI-assisted knowledge retrieval."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, systems.router, monitoring.router, incidents.router, audit.router):
    app.include_router(r)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "version": app.version}
