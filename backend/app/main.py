import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database.session import engine
from app.database.base import Base
import app.models  # Ensure all models are registered with Base metadata
from app.api.v1.router import api_router

settings = get_settings()

logging.basicConfig(
    level=logging.INFO if not settings.APP_DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("finops_copilot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager initializing async database tables and connections."""
    logger.info("Initializing PayPal FinOps Copilot Backend...")
    try:
        async with engine.begin() as conn:
            # Auto-create tables in development if migrations haven't run
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.warning(f"Database connection deferred or failed on startup: {e}")
    yield
    logger.info("Shutting down database engine...")
    await engine.dispose()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="PayPal FinOps Copilot API",
    description="AI-powered Financial Operations Platform for the PayPal AI Hackathon",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check():
    """Service health and environment status endpoint."""
    return {
        "status": "healthy",
        "service": "paypal-finops-copilot",
        "environment": settings.APP_ENV,
        "paypal_environment": settings.PAYPAL_ENVIRONMENT,
        "gemini_model": settings.GEMINI_MODEL,
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to PayPal FinOps Copilot API",
        "documentation": "/docs",
        "health": "/health",
    }


app.include_router(api_router, prefix="/api/v1")

