import unittest
from datetime import datetime
from tempfile import TemporaryDirectory
from unittest.mock import patch

from data.collectors import create_collector
from data.collectors.binance_collector import BinanceCollector
from data.collectors.okx_collector import OKXCollector
from data.store.store import DataStore


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

    async def test_full_backfill_stops_at_exchange_listing_boundary(self):
        collector = BinanceCollector()
        newest = datetime(2026, 1, 1, 0, 1)
        pages = [
            [
                {
                    "symbol": "DOGE-USDT-SWAP",
                    "timeframe": "1m",
                    "timestamp": newest,
                    "open": 1.0,
                    "high": 1.1,
                    "low": 0.9,
                    "close": 1.0,
                    "volume": 10.0,
                    "quote_volume": 10.0,
                },
                {
                    "symbol": "DOGE-USDT-SWAP",
                    "timeframe": "1m",
                    "timestamp": newest.replace(minute=0),
                    "open": 1.0,
                    "high": 1.1,
                    "low": 0.9,
                    "close": 1.0,
                    "volume": 10.0,
                    "quote_volume": 10.0,
                },
            ],
            [],
        ]

        async def fake_fetch(*args, **kwargs):
            return pages.pop(0)

        collector.fetch_historical_klines = fake_fetch
        with TemporaryDirectory() as temp_dir:
            history_store = DataStore(f"sqlite:///{temp_dir}/history.db")
            with patch("data.collectors.binance_collector.store", history_store):
                result = await collector.backfill_all_1m("DOGE-USDT-SWAP", pause_sec=0)

            self.assertEqual(result["stored"], 2)
            self.assertEqual(result["oldest"], datetime(2026, 1, 1, 0, 0))


if __name__ == "__main__":
    unittest.main()
