import unittest

from fastapi.testclient import TestClient

from backend.main import app


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


if __name__ == "__main__":
    unittest.main()
