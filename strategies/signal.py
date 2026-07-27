"""Regime-aware multi-factor signal generation."""
import numpy as np

from indicators.funding import funding_sentiment
from indicators.technical import compute_all


class MultiFactorSignal:
    """Combine trend, momentum, volatility, volume and crowding evidence."""

    strategy_name = "regime_multi_factor_v2"
    minimum_bars = 60

    def generate(
        self,
        close: np.ndarray,
        high: np.ndarray = None,
        low: np.ndarray = None,
        volume: np.ndarray = None,
        funding_rates: list[float] = None,
    ) -> dict:
        close = np.asarray(close, dtype=float)
        if len(close) < self.minimum_bars:
            return {
                "direction": "neutral",
                "strength": 0.0,
                "score": 0.0,
                "strategy": self.strategy_name,
                "reasons": [f"Insufficient history: need {self.minimum_bars} bars"],
                "indicators": {},
                "stop_loss": None,
                "take_profit": None,
            }

        high = np.asarray(high if high is not None else close, dtype=float)
        low = np.asarray(low if low is not None else close, dtype=float)
        values = compute_all(close, high, low)
        latest = {
            name: float(series[-1])
            for name, series in values.items()
            if isinstance(series, np.ndarray) and len(series) and np.isfinite(series[-1])
        }
        score = 0.0
        reasons = []

        ema9, ema21, ema50 = (latest.get(k) for k in ("ema_9", "ema_21", "ema_50"))
        if ema9 is not None and ema21 is not None and ema50 is not None:
            if ema9 > ema21 > ema50 and close[-1] > ema21:
                score += 3.0
                reasons.append("Bullish EMA regime")
            elif ema9 < ema21 < ema50 and close[-1] < ema21:
                score -= 3.0
                reasons.append("Bearish EMA regime")

        ema21_series = values.get("ema_21")
        if isinstance(ema21_series, np.ndarray) and np.isfinite(ema21_series[-6]):
            if ema21_series[-1] > ema21_series[-6]:
                score += 0.75
                reasons.append("Rising medium-term trend")
            elif ema21_series[-1] < ema21_series[-6]:
                score -= 0.75
                reasons.append("Falling medium-term trend")

        macd_hist = latest.get("macd")
        if macd_hist is not None:
            score += 1.0 if macd_hist > 0 else -1.0
            reasons.append("Positive MACD momentum" if macd_hist > 0 else "Negative MACD momentum")

        rsi_value = latest.get("rsi_14", 50.0)
        if 50 <= rsi_value <= 68:
            score += 1.0
            reasons.append("Constructive RSI")
        elif 32 <= rsi_value < 50:
            score -= 1.0
            reasons.append("Weak RSI")
        elif rsi_value > 78:
            score -= 0.75
            reasons.append("RSI extension risk")
        elif rsi_value < 22:
            score += 0.75
            reasons.append("RSI capitulation risk")

        if volume is not None and len(volume) >= 20:
            volume = np.asarray(volume, dtype=float)
            volume_ratio = float(volume[-1] / max(np.mean(volume[-20:]), 1e-12))
            latest["volume_ratio_20"] = volume_ratio
            price_change = close[-1] - close[-2]
            if volume_ratio >= 1.1 and price_change != 0:
                score += 0.75 if price_change > 0 else -0.75
                reasons.append("Volume confirms move")

        if funding_rates:
            sentiment = funding_sentiment(funding_rates)["sentiment"]
            if sentiment == "long_biased":
                score -= 0.5
                reasons.append("Crowded long funding")
            elif sentiment == "short_biased":
                score += 0.5
                reasons.append("Crowded short funding")

        direction = "long" if score >= 2.5 else "short" if score <= -2.5 else "neutral"
        strength = min(abs(score) / 5.5, 1.0) if direction != "neutral" else 0.0
        atr_value = latest.get("atr_14", max(close[-1] * 0.01, 1e-12))
        stop_loss = take_profit = None
        if direction == "long":
            stop_loss = close[-1] - 2.0 * atr_value
            take_profit = close[-1] + 3.0 * atr_value
        elif direction == "short":
            stop_loss = close[-1] + 2.0 * atr_value
            take_profit = close[-1] - 3.0 * atr_value

        return {
            "direction": direction,
            "strength": round(strength, 3),
            "score": round(score, 3),
            "strategy": self.strategy_name,
            "reasons": reasons,
            "indicators": latest,
            "stop_loss": round(float(stop_loss), 8) if stop_loss is not None else None,
            "take_profit": round(float(take_profit), 8) if take_profit is not None else None,
        }
