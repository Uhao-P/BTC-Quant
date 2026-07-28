"""信号 API 路由"""
import json
from datetime import datetime
from fastapi import APIRouter, Query
import numpy as np

from data.store.store import store
from strategies.signal import MultiFactorSignal

router = APIRouter()


def _calculate_signal(symbol: str, timeframe: str, lookback: int):
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


@router.get("/latest")
async def get_latest_signal(
    symbol: str = Query("BTC-USDT-SWAP"),
    timeframe: str = Query("1h"),
    lookback: int = Query(150, le=500),
):
    """计算最新多因子信号，但不写入历史。"""
    return _calculate_signal(symbol, timeframe, lookback)


@router.post("/generate")
async def generate_signal(
    symbol: str = Query("BTC-USDT-SWAP"),
    timeframe: str = Query("1h"),
    lookback: int = Query(150, le=500),
):
    """计算并持久化一条新交易信号。"""
    result = _calculate_signal(symbol, timeframe, lookback)
    signal = result.get("signal")
    if not signal:
        return result

    with store.get_session() as session:
        store.save_signal(session, {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": datetime.fromisoformat(result["timestamp"]),
            "direction": signal["direction"],
            "strength": signal["strength"],
            "strategy": signal["strategy"],
            "features": json.dumps(signal, ensure_ascii=False),
        })
        session.commit()
    return result


@router.get("/history")
async def get_signal_history(
    symbol: str = Query("BTC-USDT-SWAP"),
    limit: int = Query(50, le=200),
):
    """读取已生成并保存的交易信号。"""
    rows = store.get_signals(symbol, limit=limit)
    data = []
    for row in rows:
        signal = json.loads(row.features) if row.features else {
            "direction": row.direction,
            "strength": row.strength,
            "strategy": row.strategy,
            "score": 0,
            "reasons": [],
            "indicators": {},
        }
        data.append({
            **signal,
            "id": row.id,
            "timestamp": row.timestamp.isoformat(),
            "timeframe": row.timeframe,
        })
    return {"symbol": symbol, "count": len(data), "data": data}
