"""
BTC-Quant 全局配置
"""
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")
    # --- OKX API ---
    OKX_API_KEY: str = ""
    OKX_SECRET_KEY: str = ""
    OKX_PASSPHRASE: str = ""
    OKX_PROXY: Optional[str] = None  # e.g. "http://127.0.0.1:7890"
    MARKET_DATA_PROVIDER: str = "okx"

    # --- Data ---
    SYMBOLS: list[str] = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "DOGE-USDT-SWAP"]
    TIMEFRAMES: list[str] = ["1m", "5m", "15m", "1h", "4h", "1d"]
    COLLECTION_TIMEFRAMES: list[str] = ["1m", "5m", "1h"]

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./data/btc_quant.db"

    # --- Collection ---
    COLLECTOR_INTERVAL_SEC: int = 60  # kline collector interval
    FUNDING_INTERVAL_SEC: int = 3600  # funding rate collector interval

    # --- Prediction ---
    PREDICTION_HORIZON: int = 12  # forecast steps (in units of timeframe)
    DEFAULT_TIMEFRAME: str = "1h"

    # --- Backtest ---
    BACKTEST_INITIAL_CAPITAL: float = 10000.0
    BACKTEST_MAKER_FEE: float = 0.0002  # 0.02%
    BACKTEST_TAKER_FEE: float = 0.0005  # 0.05%

    # --- API ---
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8700
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

settings = Settings()
