"""
FastAPI 后端 — 主入口
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from backend.routers.data import router as data_router
from backend.routers.indicators import router as indicators_router
from backend.routers.signals import router as signals_router
from backend.routers.backtest import router as backtest_router
from backend.routers.ai_prediction import router as ai_prediction_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"[BTC-Quant] Starting on http://{settings.API_HOST}:{settings.API_PORT}")
    yield
    # Shutdown
    print("[BTC-Quant] Shutdown")


app = FastAPI(title="BTC-Quant API", version="0.1.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(data_router, prefix="/api/v1/data", tags=["Data"])
app.include_router(indicators_router, prefix="/api/v1/indicators", tags=["Indicators"])
app.include_router(signals_router, prefix="/api/v1/signals", tags=["Signals"])
app.include_router(backtest_router, prefix="/api/v1/backtest", tags=["Backtest"])
app.include_router(ai_prediction_router, prefix="/api/v1/ai-prediction", tags=["AI Prediction"])


@app.get("/")
async def root():
    return {
        "name": "BTC-Quant",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
