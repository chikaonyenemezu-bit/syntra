from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (assistant, audit, auth, changes, incidents, integrations, lifecycle, monitoring, recalls,
                     systems)
from app.config import settings
from app.bootstrap import prepare_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    prepare_database()  # serialised with the worker: see app/bootstrap.py
    yield


app = FastAPI(
    title="Syntra API",
    version="0.4.0",
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

for r in (auth.router, systems.router, monitoring.router, incidents.router, audit.router,
          integrations.router, recalls.router, lifecycle.router, changes.router, assistant.router,
          assistant.knowledge_router):
    app.include_router(r)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "version": app.version}
