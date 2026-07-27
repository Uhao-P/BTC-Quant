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


if __name__ == "__main__":
    unittest.main()

