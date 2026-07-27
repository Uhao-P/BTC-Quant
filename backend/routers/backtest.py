"""回测 API 路由"""
from fastapi import APIRouter, Query
import numpy as np
import pandas as pd

from data.store.store import store
from strategies.backtest import BacktestEngine
from strategies.signal import MultiFactorSignal

router = APIRouter()

BARS_PER_YEAR = {
    "1m": 365 * 24 * 60, "5m": 365 * 24 * 12, "15m": 365 * 24 * 4,
    "1h": 365 * 24, "4h": 365 * 6, "1d": 365,
}


@router.get("/run")
async def run_backtest(
    symbol: str = Query("BTC-USDT-SWAP"),
    timeframe: str = Query("1h"),
    limit: int = Query(1000, le=5000),
):
    """Backtest the regime-aware strategy with one-bar delayed execution."""
    klines = store.get_klines(symbol, timeframe, limit=limit)
    if len(klines) < 100:
        return {"error": "Not enough data", "need_bars": 100, "have": len(klines)}

    klines = list(reversed(klines))
    df = pd.DataFrame([
        {"timestamp": k.timestamp, "open": k.open, "high": k.high,
         "low": k.low, "close": k.close, "volume": k.volume}
        for k in klines
    ])

    generator = MultiFactorSignal()

    def signal_func(i: int, df: pd.DataFrame):
        # Only completed bars strictly before i are used, preventing look-ahead.
        if i < generator.minimum_bars:
            return None
        history = df.iloc[:i]
        signal = generator.generate(
            history["close"].to_numpy(), history["high"].to_numpy(),
            history["low"].to_numpy(), history["volume"].to_numpy(),
        )
        return signal if signal["direction"] != "neutral" else None

    engine = BacktestEngine(df, bars_per_year=BARS_PER_YEAR.get(timeframe, 365))
    result = engine.run(signal_func)

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "bars": len(df),
        "strategy": generator.strategy_name,
        "result": {
            "total_trades": result.total_trades,
            "win_trades": result.win_trades,
            "loss_trades": result.loss_trades,
            "win_rate": round(result.win_rate, 4),
            "total_pnl_pct": round(result.total_pnl_pct, 2),
            "max_drawdown": round(result.max_drawdown, 4),
            "sharpe": round(result.sharpe, 4),
            "avg_hold_bars": round(result.avg_hold_bars, 1),
            "latest_equity": round(result.equity_curve[-1], 2) if result.equity_curve else 0,
        },
    }
