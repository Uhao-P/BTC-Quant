"""
资金费率分析 — 多空情绪、累积费率、套利机会
"""
import numpy as np
from typing import Optional


def funding_sentiment(funding_rates: list[float]) -> dict:
    """
    资金费率情绪分析
    Returns: 多空偏向、极端程度、累积成本
    """
    if not funding_rates:
        return {"sentiment": "neutral", "score": 0.0, "avg_rate": 0.0}

    arr = np.array(funding_rates)
    avg = float(np.mean(arr))
    std = float(np.std(arr))
    cumul = float(np.sum(arr))  # cumulative funding cost

    # 阈值: 0.01% = 0.0001
    if avg > 0.0005:
        sentiment = "long_biased"
    elif avg < -0.0005:
        sentiment = "short_biased"
    else:
        sentiment = "neutral"

    # extreme score: how many std away from neutral
    score = float(avg / max(std, 1e-10))

    return {
        "sentiment": sentiment,
        "score": round(score, 3),
        "avg_rate": round(avg * 100, 4),  # percentage
        "std_rate": round(std * 100, 4),
        "cumulative_cost": round(cumul * 100, 4),
        "sample_count": len(funding_rates),
    }


def funding_arbitrage_opportunity(spot_price: float, futures_price: float,
                                   funding_rate: float, days: int = 30) -> dict:
    """评估资金费率套利机会 (现货-合约基差)"""
    basis = (futures_price - spot_price) / spot_price * 100
    annualized_funding = funding_rate * 365 * 100  # 年化资金费率收益

    return {
        "basis_pct": round(basis, 4),
        "annualized_funding_pct": round(annualized_funding, 4),
        "net_annualized": round(annualized_funding - basis, 4),
        "attractive": annualized_funding > abs(basis) * 2,
    }
