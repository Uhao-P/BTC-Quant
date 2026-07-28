"""
OKX 数据采集器 — WebSocket 实时 + REST 历史回填
"""
import json
import asyncio
from datetime import datetime
from typing import Optional

import httpx

from config.settings import settings
from data.store.store import store
from data.schema.models import Kline, FundingRate


class OKXCollector:
    """OKX 永续合约数据采集器"""

    REST_BASE = "https://openapi.okx.com"
    WS_BASE = "wss://ws.okx.com:8443/ws/v5/public"

    def __init__(self, proxy: Optional[str] = settings.OKX_PROXY):
        self.proxy = proxy
        self._http_client: Optional[httpx.AsyncClient] = None
        self._ws_conn = None

    # ── HTTP helpers ──

    def _client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            kwargs = dict(timeout=httpx.Timeout(30.0))
            if self.proxy:
                kwargs["proxy"] = self.proxy
            self._http_client = httpx.AsyncClient(**kwargs)
        return self._http_client

    async def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self.REST_BASE}{path}"
        r = await self._client().get(url, params=params)
        r.raise_for_status()
        return r.json()

    async def close(self):
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    # ── REST: historical klines ──

    async def fetch_historical_klines(
        self, symbol: str = "BTC-USDT-SWAP",
        timeframe: str = "1H",
        limit: int = 300,
        after: Optional[str] = None,
    ) -> list[dict]:
        """Fetch historical klines. ``after`` requests records older than timestamp."""
        params = {
            "instId": symbol,
            "bar": timeframe,
            "limit": min(limit, 300),
        }
        if after:
            params["after"] = after

        data = await self._get("/api/v5/market/history-candles", params)
        if data.get("code") != "0":
            raise RuntimeError(f"OKX API error: {data}")

        rows = []
        for bar in data.get("data", []):
            # bar: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
            rows.append({
                "symbol": symbol,
                "timeframe": timeframe.lower(),
                "timestamp": datetime.utcfromtimestamp(int(bar[0]) / 1000),
                "open": float(bar[1]),
                "high": float(bar[2]),
                "low": float(bar[3]),
                "close": float(bar[4]),
                "volume": float(bar[5]),
                "quote_volume": float(bar[7]) if len(bar) > 7 else None,
            })
        return rows

    async def backfill_klines(self, symbol: str = "BTC-USDT-SWAP",
                              timeframe: str = "1h", total_bars: int = 1000):
        """回填历史 K 线，每次 300 条向前翻页"""
        after = None
        collected = 0
        with store.get_session() as session:
            while collected < total_bars:
                rows = await self.fetch_historical_klines(
                    symbol, timeframe, limit=min(300, total_bars - collected), after=after
                )
                if not rows:
                    break
                new = store.save_klines_batch(session, rows)
                collected += len(rows)
                session.commit()
                print(f"[backfill] {symbol} {timeframe}: +{new} bars (total {collected})")
                next_after = str(int(min(row["timestamp"] for row in rows).timestamp() * 1000))
                if next_after == after:
                    break
                after = next_after
                await asyncio.sleep(0.2)  # rate limit

    # ── Funding rates ──

    async def fetch_funding_rate(self, symbol: str = "BTC-USDT-SWAP") -> dict:
        """Fetch current funding rate"""
        data = await self._get("/api/v5/public/funding-rate", {"instId": symbol})
        if data.get("code") != "0":
            raise RuntimeError(f"OKX funding rate error: {data}")
        row = data["data"][0]
        return {
            "symbol": symbol,
            "timestamp": datetime.utcfromtimestamp(int(row["fundingTime"]) / 1000),
            "funding_rate": float(row["fundingRate"]),
        }

    # ── WebSocket: real-time klines ──

    async def _subscribe_ws(self, symbol: str, timeframe: str):
        """Subscribe to real-time kline channel"""
        import websockets
        async with websockets.connect(self.WS_BASE) as ws:
            sub = {
                "op": "subscribe",
                "args": [{"channel": f"candle{timeframe}", "instId": symbol}],
            }
            await ws.send(json.dumps(sub))

            # ignore first response (subscription ack)
            _ = await ws.recv()

            while True:
                msg = json.loads(await ws.recv())
                if msg.get("event") == "subscribe":
                    continue
                yield msg

    async def run_realtime_kline(self, symbol: str = "BTC-USDT-SWAP",
                                 timeframe: str = "1m"):
        """Run real-time kline collector (forever loop)"""
        async for msg in self._subscribe_ws(symbol, timeframe):
            try:
                data = msg["data"][0]
                # data: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
                if data[8] != "1":
                    continue  # not confirmed yet
                row = {
                    "symbol": symbol,
                    "timeframe": timeframe.lower(),
                    "timestamp": datetime.utcfromtimestamp(int(data[0]) / 1000),
                    "open": float(data[1]),
                    "high": float(data[2]),
                    "low": float(data[3]),
                    "close": float(data[4]),
                    "volume": float(data[5]),
                    "quote_volume": float(data[7]) if len(data) > 7 else None,
                }
                with store.get_session() as session:
                    store.save_kline(session, row)
                    session.commit()
            except Exception as e:
                print(f"[WS error] {e}")


if __name__ == "__main__":
    async def main():
        c = OKXCollector()
        # backfill 1000 bars of 1h data
        await c.backfill_klines(timeframe="1h", total_bars=1000)
        print("Backfill done. Starting real-time collector...")
        await c.run_realtime_kline(timeframe="1m")

    asyncio.run(main())
