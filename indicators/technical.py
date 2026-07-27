"""
技术指标计算模块
"""
import numpy as np
import pandas as pd
from typing import Optional


def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """RSI 相对强弱指标"""
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = np.full_like(close, np.nan, dtype=float)
    avg_loss = np.full_like(close, np.nan, dtype=float)

    avg_gain[period] = np.mean(gain[:period])
    avg_loss[period] = np.mean(loss[:period])

    for i in range(period + 1, len(close)):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gain[i - 1]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + loss[i - 1]) / period

    rs = avg_gain / np.maximum(avg_loss, 1e-10)
    rsi_val = 100 - (100 / (1 + rs))
    flat = (avg_gain == 0) & (avg_loss == 0)
    only_gains = (avg_gain > 0) & (avg_loss == 0)
    rsi_val[flat] = 50.0
    rsi_val[only_gains] = 100.0
    return rsi_val


def ema(data: np.ndarray, period: int) -> np.ndarray:
    """指数移动平均"""
    result = np.full_like(data, np.nan, dtype=float)
    alpha = 2 / (period + 1)
    result[period - 1] = np.mean(data[:period])
    for i in range(period, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
    return result


def macd(close: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """MACD 指标"""
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    diff = ema_fast - ema_slow
    dea = ema(diff[~np.isnan(diff)], signal)
    macd_val = 2 * (diff[-len(dea):] - dea)

    # pad back to full length
    full_dea = np.full_like(close, np.nan)
    full_macd = np.full_like(close, np.nan)
    n = len(dea)
    full_dea[-n:] = dea
    full_macd[-n:] = macd_val

    return {"diff": diff, "dea": full_dea, "macd": full_macd}


def bollinger_bands(close: np.ndarray, period: int = 20, std_mult: float = 2.0) -> dict:
    """布林带"""
    middle = np.full_like(close, np.nan)
    upper = np.full_like(close, np.nan)
    lower = np.full_like(close, np.nan)

    for i in range(period - 1, len(close)):
        window = close[i - period + 1:i + 1]
        m = np.mean(window)
        s = np.std(window)
        middle[i] = m
        upper[i] = m + std_mult * s
        lower[i] = m - std_mult * s

    return {"middle": middle, "upper": upper, "lower": lower}


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """平均真实波幅 (ATR)"""
    tr = np.full_like(close, np.nan)
    for i in range(1, len(close)):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr[i] = max(hl, hc, lc)

    atr_val = np.full_like(close, np.nan)
    atr_val[period] = np.mean(tr[1:period + 1])
    for i in range(period + 1, len(close)):
        atr_val[i] = (atr_val[i - 1] * (period - 1) + tr[i]) / period
    return atr_val


def compute_all(close: np.ndarray, high: np.ndarray = None,
                low: np.ndarray = None) -> dict:
    """计算一组基础指标"""
    results = {
        "rsi_14": rsi(close, 14),
    }

    macd_vals = macd(close)
    results["macd_diff"] = macd_vals["diff"]
    results["macd_dea"] = macd_vals["dea"]
    results["macd"] = macd_vals["macd"]

    bb = bollinger_bands(close)
    results["bb_middle"] = bb["middle"]
    results["bb_upper"] = bb["upper"]
    results["bb_lower"] = bb["lower"]
    results["bb_width"] = (bb["upper"] - bb["lower"]) / np.maximum(bb["middle"], 1e-10)

    results["ema_9"] = ema(close, 9)
    results["ema_21"] = ema(close, 21)
    results["ema_50"] = ema(close, 50)

    if high is not None and low is not None:
        results["atr_14"] = atr(high, low, close, 14)

    return results
