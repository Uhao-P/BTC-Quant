"""
数据 API 路由
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Query

from data.store.store import store
from config.settings import settings

router = APIRouter()

ASSET_NAMES = {
    "BTC-USDT-SWAP": "Bitcoin",
    "ETH-USDT-SWAP": "Ethereum",
    "DOGE-USDT-SWAP": "Dogecoin",
}


@router.get("/assets")
async def get_assets():
    """List instruments supported by collection and research APIs."""
    return {
        "data": [
            {"symbol": symbol, "name": ASSET_NAMES.get(symbol, symbol)}
            for symbol in settings.SYMBOLS
        ]
    }


@router.get("/klines")
async def get_klines(
    symbol: str = Query("BTC-USDT-SWAP"),
    timeframe: str = Query("1h"),
    limit: int = Query(200, le=2000),
    hours: int = Query(None),
):
    """获取历史 K 线数据"""
    klines = store.get_klines(symbol, timeframe, limit=limit)
    if hours:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        klines = [k for k in klines if k.timestamp >= cutoff]

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(klines),
        "data": [
            {
                "timestamp": k.timestamp.isoformat(),
                "open": k.open,
                "high": k.high,
                "low": k.low,
                "close": k.close,
                "volume": k.volume,
            }
            for k in klines
        ],
    }


@router.get("/funding")
async def get_funding(
    symbol: str = Query("BTC-USDT-SWAP"),
    limit: int = Query(100, le=500),
):
    """获取资金费率数据"""
    rates = store.get_funding_rates(symbol, limit=limit)
    return {
        "symbol": symbol,
        "count": len(rates),
        "data": [
            {
                "timestamp": r.timestamp.isoformat(),
                "funding_rate": r.funding_rate,
            }
            for r in rates
        ],
    }
