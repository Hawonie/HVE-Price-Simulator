"""FastAPI application entry point with lifespan management."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.database import Base, get_engine, get_session_factory, set_session_factory
from app.api.routes import router

# Import models so Base.metadata knows about them
import app.models.product  # noqa: F401
import app.models.snapshot  # noqa: F401
import app.models.change  # noqa: F401
import app.models.simulation  # noqa: F401

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of async resources."""
    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Starting Amazon Tracker MVP")

    # Database engine and session factory
    engine = await get_engine(settings.database_url)

    # Auto-create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    session_factory = await get_session_factory(engine)
    set_session_factory(session_factory)
    app.state.engine = engine
    app.state.session_factory = session_factory
    logger.info("Database ready")

    # Browser manager not needed (using httpx)
    app.state.browser_manager = None
    app.state.scheduler = None
    logger.info("Server ready")

    yield

    # Shutdown
    logger.info("Shutting down Amazon Tracker MVP")

    await engine.dispose()
    logger.info("Database engine disposed")


app = FastAPI(
    title="Amazon Tracker MVP",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(router)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the web dashboard."""
    return templates.TemplateResponse(request=request, name="dashboard.html")
