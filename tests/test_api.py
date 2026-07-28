import unittest
from datetime import datetime, timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from data.store.store import DataStore


class AssetApiTests(unittest.TestCase):
    def test_supported_assets_are_available_to_clients(self):
        response = TestClient(app).get("/api/v1/data/assets")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [asset["symbol"] for asset in response.json()["data"]],
            ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "DOGE-USDT-SWAP"],
        )

    def test_research_endpoints_accept_every_supported_asset(self):
        client = TestClient(app)
        for symbol in ("BTC-USDT-SWAP", "ETH-USDT-SWAP", "DOGE-USDT-SWAP"):
            with self.subTest(symbol=symbol):
                for path in ("/api/v1/data/klines", "/api/v1/signals/latest", "/api/v1/backtest/run"):
                    response = client.get(path, params={"symbol": symbol})
                    self.assertEqual(response.status_code, 200)

    def test_generated_signal_is_restored_from_history(self):
        with TemporaryDirectory() as temp_dir:
            signal_store = DataStore(f"sqlite:///{temp_dir}/signals.db")
            start = datetime(2026, 1, 1)
            with signal_store.get_session() as session:
                signal_store.save_klines_batch(session, [
                    {
                        "symbol": "BTC-USDT-SWAP",
                        "timeframe": "1h",
                        "timestamp": start + timedelta(hours=index),
                        "open": 100 + index,
                        "high": 102 + index,
                        "low": 99 + index,
                        "close": 101 + index,
                        "volume": 1000 + index,
                    }
                    for index in range(80)
                ])
                session.commit()

            client = TestClient(app)
            with patch("backend.routers.signals.store", signal_store):
                generated = client.post(
                    "/api/v1/signals/generate",
                    params={"symbol": "BTC-USDT-SWAP"},
                )
                history = client.get(
                    "/api/v1/signals/history",
                    params={"symbol": "BTC-USDT-SWAP"},
                )

            self.assertEqual(generated.status_code, 200)
            self.assertEqual(history.status_code, 200)
            self.assertEqual(history.json()["count"], 1)
            self.assertEqual(
                history.json()["data"][0]["score"],
                generated.json()["signal"]["score"],
            )


if __name__ == "__main__":
    unittest.main()
