"""指标 API 路由"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
import numpy as np

from data.store.store import store
from indicators.technical import compute_all

router = APIRouter()


@router.get("/latest")
async def get_latest_indicators(
    symbol: str = Query("BTC-USDT-SWAP"),
    timeframe: str = Query("1h"),
    lookback: int = Query(100, le=500),
):
    """计算最新技术指标"""
    klines = store.get_klines(symbol, timeframe, limit=lookback)
    if len(klines) < 30:
        return {"error": "Not enough data", "need_bars": 30, "have": len(klines)}

    klines = list(reversed(klines))  # chronological
    close = np.array([k.close for k in klines])
    high = np.array([k.high for k in klines])
    low = np.array([k.low for k in klines])

    ind = compute_all(close, high, low)

    result = {}
    for k, v in ind.items():
        if isinstance(v, np.ndarray) and len(v) > 0:
            latest_val = v[-1]
            if not (isinstance(latest_val, float) and np.isnan(latest_val)):
                result[k] = float(latest_val)

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": klines[-1].timestamp.isoformat(),
        "close": float(close[-1]),
        "indicators": result,
    }
