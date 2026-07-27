import unittest

import numpy as np

from indicators.technical import rsi


class IndicatorTests(unittest.TestCase):
    def test_flat_market_rsi_is_neutral(self):
        values = rsi(np.full(30, 100.0))
        self.assertEqual(values[-1], 50.0)


if __name__ == "__main__":
    unittest.main()
