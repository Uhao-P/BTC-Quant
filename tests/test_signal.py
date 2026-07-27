import unittest

import numpy as np

from strategies.signal import MultiFactorSignal


class MultiFactorSignalTests(unittest.TestCase):
    def test_trending_markets_produce_executable_signals_at_each_asset_scale(self):
        for asset, start in (("BTC", 60_000), ("ETH", 3_000), ("DOGE", 0.15)):
            with self.subTest(asset=asset):
                close = np.linspace(start, start * 1.4, 120) + np.sin(np.arange(120)) * start * 0.002
                signal = MultiFactorSignal().generate(
                    close, close * 1.01, close * 0.99, np.linspace(100, 180, 120)
                )
                self.assertEqual(signal["direction"], "long")
                self.assertGreater(signal["strength"], 0)
                self.assertLess(signal["stop_loss"], close[-1])
                self.assertGreater(signal["take_profit"], close[-1])
                self.assertEqual(signal["strategy"], "regime_multi_factor_v2")

    def test_insufficient_history_returns_neutral_instead_of_crashing(self):
        close = np.array([100.0, 101.0, 102.0])

        signal = MultiFactorSignal().generate(close)

        self.assertEqual(signal["direction"], "neutral")
        self.assertIn("Insufficient history", signal["reasons"][0])


if __name__ == "__main__":
    unittest.main()
