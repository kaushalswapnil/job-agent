from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager
import structlog

from app.core.config import get_settings
from app.api import onboarding, dashboard, approvals, agents
from app.agents.discovery.runner import run_discovery

logger = structlog.get_logger()
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background scheduler
    scheduler.add_job(run_discovery, "interval", hours=4, id="discovery")
    scheduler.start()
    logger.info("scheduler_started", jobs=["discovery every 4h"])
    yield
    scheduler.shutdown()


app = FastAPI(
    title="Job Agent API",
    description="Autonomous AI Job Search & Application Agent",
    version="1.0.0",
    lifespan=lifespan,
)

s = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[s.frontend_url, "http://localhost:8081", "http://localhost:3000", "exp://localhost:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(onboarding.router)
app.include_router(dashboard.router)
app.include_router(approvals.router)
app.include_router(agents.router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
