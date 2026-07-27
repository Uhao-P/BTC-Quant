import unittest

import pandas as pd

from strategies.backtest import BacktestEngine


class BacktestEngineTests(unittest.TestCase):
    def test_long_trade_uses_derivative_equity_accounting(self):
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=3, freq="h"),
                "open": [100.0, 110.0, 110.0],
                "high": [101.0, 111.0, 111.0],
                "low": [99.0, 109.0, 109.0],
                "close": [100.0, 110.0, 110.0],
                "volume": [1.0, 1.0, 1.0],
            }
        )
        signals = {0: "long", 1: "close"}

        result = BacktestEngine(
            df, initial_capital=1000, taker_fee=0, slippage=0, position_fraction=1
        ).run(lambda i, _: signals.get(i))

        self.assertEqual(result.total_trades, 1)
        self.assertAlmostEqual(result.trades[0].pnl, 100.0)
        self.assertAlmostEqual(result.total_pnl, 100.0)
        self.assertAlmostEqual(result.equity_curve[-1], 1100.0)

    def test_opposite_signal_closes_and_reverses_position(self):
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=3, freq="h"),
                "open": [100.0, 110.0, 100.0],
                "high": [101.0, 111.0, 101.0],
                "low": [99.0, 109.0, 99.0],
                "close": [100.0, 110.0, 100.0],
                "volume": [1.0, 1.0, 1.0],
            }
        )
        signals = {0: "long", 1: "short"}

        result = BacktestEngine(
            df, initial_capital=1000, taker_fee=0, slippage=0, position_fraction=1
        ).run(lambda i, _: signals.get(i))

        self.assertEqual([t.direction for t in result.trades], ["long", "short"])
        self.assertAlmostEqual(result.total_pnl, 200.0)

    def test_atr_stop_loss_exits_at_configured_level(self):
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=2, freq="h"),
                "open": [100.0, 100.0],
                "high": [101.0, 102.0],
                "low": [99.0, 94.0],
                "close": [100.0, 101.0],
                "volume": [1.0, 1.0],
            }
        )

        result = BacktestEngine(
            df, initial_capital=1000, taker_fee=0, slippage=0, position_fraction=1
        ).run(lambda i, _: {"direction": "long", "stop_loss": 95.0} if i == 0 else None)

        self.assertEqual(result.total_trades, 1)
        self.assertEqual(result.trades[0].reason, "stop_loss")
        self.assertAlmostEqual(result.trades[0].exit_price, 95.0)
        self.assertAlmostEqual(result.total_pnl, -50.0)

    def test_signal_executes_at_bar_open_with_costs(self):
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=3, freq="h"),
                "open": [100.0, 105.0, 110.0],
                "high": [101.0, 111.0, 111.0],
                "low": [99.0, 104.0, 109.0],
                "close": [100.0, 110.0, 110.0],
                "volume": [1.0, 1.0, 1.0],
            }
        )
        signals = {1: "long", 2: "close"}

        result = BacktestEngine(
            df, initial_capital=1000, taker_fee=0.001, slippage=0.001,
            position_fraction=1, bars_per_year=8760,
        ).run(lambda i, _: signals.get(i))

        self.assertAlmostEqual(result.trades[0].entry_price, 105.105)
        self.assertGreater(result.trades[0].fee, 0)
        self.assertLess(result.total_pnl, (110 - 105) / 105 * 1000)

    def test_take_profit_is_recorded_and_updates_final_equity(self):
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=2, freq="h"),
                "open": [100.0, 100.0], "high": [101.0, 106.0],
                "low": [99.0, 99.0], "close": [100.0, 102.0], "volume": [1.0, 1.0],
            }
        )
        result = BacktestEngine(
            df, initial_capital=1000, taker_fee=0, slippage=0, position_fraction=1
        ).run(lambda i, _: {"direction": "long", "take_profit": 105.0} if i == 0 else None)

        self.assertEqual(result.trades[0].reason, "take_profit")
        self.assertEqual(result.equity_curve[-1], 1050.0)


if __name__ == "__main__":
    unittest.main()
