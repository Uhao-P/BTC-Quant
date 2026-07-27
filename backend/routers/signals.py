"""信号 API 路由"""
from datetime import datetime
from fastapi import APIRouter, Query
import numpy as np

from data.store.store import store
from strategies.signal import MultiFactorSignal

router = APIRouter()


@router.get("/latest")
async def get_latest_signal(
    symbol: str = Query("BTC-USDT-SWAP"),
    timeframe: str = Query("1h"),
    lookback: int = Query(150, le=500),
):
    """生成最新多因子信号"""
    klines = store.get_klines(symbol, timeframe, limit=lookback)
    generator = MultiFactorSignal()
    if len(klines) < generator.minimum_bars:
        return {"error": "Not enough data", "need_bars": generator.minimum_bars, "have": len(klines)}

    klines = list(reversed(klines))
    close = np.array([k.close for k in klines])
    high = np.array([k.high for k in klines])
    low = np.array([k.low for k in klines])
    volume = np.array([k.volume for k in klines])

    funding_rates_data = store.get_funding_rates(symbol, limit=20)
    funding_rates = [r.funding_rate for r in funding_rates_data]

    signal = generator.generate(close, high, low, volume, funding_rates=funding_rates)

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": klines[-1].timestamp.isoformat(),
        "close": float(close[-1]),
        "signal": signal,
    }
