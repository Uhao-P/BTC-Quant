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


@router.get("/price-history")
async def get_price_history(
    symbol: str = Query("BTC-USDT-SWAP"),
    max_points: int = Query(2500, ge=100, le=5000),
    start: datetime = Query(None),
    end: datetime = Query(None),
):
    """获取覆盖全部本地分钟线历史的有界价格概览。"""
    overview = store.get_price_history_overview(
        symbol, max_points=max_points, start=start, end=end
    )
    return {
        "symbol": symbol,
        "source_count": overview["source_count"],
        "count": len(overview["data"]),
        "oldest": overview["oldest"].isoformat() if overview["oldest"] else None,
        "latest": overview["latest"].isoformat() if overview["latest"] else None,
        "bucket_seconds": overview["bucket_seconds"],
        "data": [
            {"timestamp": point.timestamp.isoformat(), "close": point.close}
            for point in overview["data"]
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
