"""K-line backtesting with perpetual-contract accounting and risk exits."""
from dataclasses import dataclass, field
from typing import Callable, Optional, Union

import numpy as np
import pandas as pd


@dataclass
class Trade:
    entry_time: str
    entry_price: float
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    direction: str = "long"
    size: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    fee: float = 0.0
    reason: str = ""
    hold_bars: int = 0


@dataclass
class BacktestResult:
    total_trades: int = 0
    win_trades: int = 0
    loss_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    max_drawdown: float = 0.0
    sharpe: float = 0.0
    avg_hold_bars: float = 0.0
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)


Signal = Optional[Union[str, dict]]


class BacktestEngine:
    """Single-position backtester using linear perpetual-contract PnL."""

    def __init__(
        self,
        df: pd.DataFrame,
        initial_capital: float = 10000.0,
        maker_fee: float = 0.0002,
        taker_fee: float = 0.0005,
        slippage: float = 0.0002,
        position_fraction: float = 0.25,
    ):
        self.df = df.reset_index(drop=True)
        self.initial_capital = initial_capital
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.slippage = slippage
        self.position_fraction = position_fraction

    def run(self, signal_func: Callable[[int, pd.DataFrame], Signal]) -> BacktestResult:
        cash = self.initial_capital
        position = None
        trades: list[Trade] = []
        equity_curve = [cash]

        def execution_price(price: float, side: str) -> float:
            return price * (1 + self.slippage if side == "buy" else 1 - self.slippage)

        def close_position(price: float, index: int, reason: str) -> None:
            nonlocal cash, position
            if position is None:
                return
            side = "sell" if position["direction"] == "long" else "buy"
            exit_price = execution_price(float(price), side)
            sign = 1 if position["direction"] == "long" else -1
            gross_pnl = sign * (exit_price - position["entry_price"]) * position["size"]
            exit_fee = exit_price * position["size"] * self.taker_fee
            net_pnl = gross_pnl - position["entry_fee"] - exit_fee
            cash += gross_pnl - exit_fee
            notional = position["entry_price"] * position["size"]
            trades.append(
                Trade(
                    entry_time=str(self.df.iloc[position["entry_idx"]]["timestamp"]),
                    entry_price=position["entry_price"],
                    exit_time=str(self.df.iloc[index]["timestamp"]),
                    exit_price=exit_price,
                    direction=position["direction"],
                    size=position["size"],
                    pnl=net_pnl,
                    pnl_pct=net_pnl / notional * 100 if notional else 0.0,
                    fee=position["entry_fee"] + exit_fee,
                    reason=reason,
                    hold_bars=index - position["entry_idx"],
                )
            )
            position = None

        def open_position(direction: str, price: float, index: int, config: dict) -> None:
            nonlocal cash, position
            side = "buy" if direction == "long" else "sell"
            entry_price = execution_price(float(price), side)
            size = cash * self.position_fraction / entry_price
            entry_fee = entry_price * size * self.taker_fee
            cash -= entry_fee
            position = {
                "direction": direction,
                "entry_price": entry_price,
                "entry_idx": index,
                "size": size,
                "entry_fee": entry_fee,
                "stop_loss": config.get("stop_loss"),
                "take_profit": config.get("take_profit"),
            }

        for i, row in self.df.iterrows():
            if position is not None:
                stop = position["stop_loss"]
                target = position["take_profit"]
                if position["direction"] == "long":
                    if stop is not None and row["low"] <= stop:
                        close_position(stop, i, "stop_loss")
                    elif target is not None and row["high"] >= target:
                        close_position(target, i, "take_profit")
                else:
                    if stop is not None and row["high"] >= stop:
                        close_position(stop, i, "stop_loss")
                    elif target is not None and row["low"] <= target:
                        close_position(target, i, "take_profit")

            raw_signal = signal_func(i, self.df)
            config = raw_signal if isinstance(raw_signal, dict) else {}
            direction = config.get("direction") if config else raw_signal

            if position is not None and (
                direction == "close" or direction in ("long", "short") and direction != position["direction"]
            ):
                close_position(row["close"], i, "signal_close" if direction == "close" else "reverse")

            if position is None and direction in ("long", "short"):
                open_position(direction, row["close"], i, config)

            if position is None:
                equity_curve.append(cash)
            else:
                sign = 1 if position["direction"] == "long" else -1
                unrealized = sign * (row["close"] - position["entry_price"]) * position["size"]
                equity_curve.append(cash + unrealized)

        if position is not None:
            close_position(self.df.iloc[-1]["close"], len(self.df) - 1, "end_of_data")
            equity_curve[-1] = cash

        result = BacktestResult(trades=trades, equity_curve=equity_curve)
        result.total_trades = len(trades)
        result.win_trades = sum(t.pnl > 0 for t in trades)
        result.loss_trades = result.total_trades - result.win_trades
        result.win_rate = result.win_trades / result.total_trades if result.total_trades else 0.0
        result.total_pnl = cash - self.initial_capital
        result.total_pnl_pct = result.total_pnl / self.initial_capital * 100
        peaks = np.maximum.accumulate(np.asarray(equity_curve, dtype=float))
        drawdowns = (peaks - equity_curve) / np.maximum(peaks, 1e-12)
        result.max_drawdown = float(np.max(drawdowns)) if len(drawdowns) else 0.0
        returns = np.diff(equity_curve) / np.maximum(np.asarray(equity_curve[:-1]), 1e-12)
        if len(returns) > 1 and np.std(returns) > 0:
            result.sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(365))
        result.avg_hold_bars = float(np.mean([t.hold_bars for t in trades])) if trades else 0.0
        return result
