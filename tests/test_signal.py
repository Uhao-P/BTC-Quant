import unittest

import numpy as np

from strategies.signal import MultiFactorSignal


class MultiFactorSignalTests(unittest.TestCase):
    def test_trending_market_produces_executable_signal_with_risk_levels(self):
        close = np.linspace(100, 140, 120) + np.sin(np.arange(120))
        high = close + 1.5
        low = close - 1.5
        volume = np.linspace(100, 180, 120)

        signal = MultiFactorSignal().generate(close, high, low, volume)

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

