import unittest

from data.collectors import create_collector
from data.collectors.binance_collector import BinanceCollector
from data.collectors.okx_collector import OKXCollector


class CollectorFactoryTests(unittest.TestCase):
    def test_provider_selection_is_explicit(self):
        self.assertIsInstance(create_collector("binance"), BinanceCollector)
        self.assertIsInstance(create_collector("okx"), OKXCollector)


class BinanceCollectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_klines_are_normalized_to_project_schema(self):
        collector = BinanceCollector()

        async def fake_get(path, params=None):
            return [[1700000000000, "100", "110", "90", "105", "12", 0, "1260"]]

        collector._get = fake_get
        rows = await collector.fetch_historical_klines("ETH-USDT-SWAP", "1h", limit=1)

        self.assertEqual(rows[0]["symbol"], "ETH-USDT-SWAP")
        self.assertEqual(rows[0]["timeframe"], "1h")
        self.assertEqual(rows[0]["close"], 105.0)
        self.assertEqual(rows[0]["quote_volume"], 1260.0)


if __name__ == "__main__":
    unittest.main()
