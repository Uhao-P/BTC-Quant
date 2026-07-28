"""Binance USD-M futures collector with the project's normalized schema."""
import asyncio
from datetime import datetime, timezone
from typing import Optional

import httpx

from config.settings import settings
from data.store.store import store


class BinanceCollector:
    REST_BASE = "https://fapi.binance.com"
    RETRY_DELAYS = (0.5, 1.0, 2.0, 4.0)

    def __init__(self, proxy: Optional[str] = settings.OKX_PROXY):
        self.proxy = proxy
        self._http_client: Optional[httpx.AsyncClient] = None

    @staticmethod
    def _symbol(symbol: str) -> str:
        return symbol.replace("-USDT-SWAP", "USDT")

    def _client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            kwargs = {"timeout": httpx.Timeout(30.0)}
            if self.proxy:
                kwargs["proxy"] = self.proxy
            self._http_client = httpx.AsyncClient(**kwargs)
        return self._http_client

    async def _get(self, path: str, params: dict = None):
        for attempt in range(len(self.RETRY_DELAYS) + 1):
            try:
                response = await self._client().get(f"{self.REST_BASE}{path}", params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError:
                if attempt == len(self.RETRY_DELAYS):
                    raise
                await self.close()
                await asyncio.sleep(self.RETRY_DELAYS[attempt])

    async def close(self):
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def fetch_historical_klines(
        self,
        symbol: str = "BTC-USDT-SWAP",
        timeframe: str = "1h",
        limit: int = 300,
        after: Optional[str] = None,
    ) -> list[dict]:
        params = {
            "symbol": self._symbol(symbol),
            "interval": timeframe.lower(),
            "limit": min(limit, 1500),
        }
        if after:
            params["endTime"] = int(after) - 1
        data = await self._get("/fapi/v1/klines", params)
        return [
            {
                "symbol": symbol,
                "timeframe": timeframe.lower(),
                "timestamp": datetime.utcfromtimestamp(int(bar[0]) / 1000),
                "open": float(bar[1]),
                "high": float(bar[2]),
                "low": float(bar[3]),
                "close": float(bar[4]),
                "volume": float(bar[5]),
                "quote_volume": float(bar[7]),
            }
            for bar in data
        ]

    async def backfill_klines(
        self, symbol: str = "BTC-USDT-SWAP", timeframe: str = "1h", total_bars: int = 1000
    ):
        after = None
        collected = 0
        with store.get_session() as session:
            while collected < total_bars:
                rows = await self.fetch_historical_klines(
                    symbol, timeframe, min(1500, total_bars - collected), after
                )
                if not rows:
                    break
                new = store.save_klines_batch(session, rows)
                session.commit()
                collected += len(rows)
                print(f"[backfill] {symbol} {timeframe}: +{new} bars (total {collected})")
                next_after = str(int(min(row["timestamp"] for row in rows).timestamp() * 1000))
                if next_after == after:
                    break
                after = next_after
                await asyncio.sleep(0.2)

    async def backfill_all_1m(
        self, symbol: str, page_size: int = 1500, pause_sec: float = 0.2
    ) -> dict:
        """Resume backwards from the oldest local minute until the listing boundary."""
        oldest = store.get_oldest_kline_timestamp(symbol, "1m")
        after = (
            str(int(oldest.replace(tzinfo=timezone.utc).timestamp() * 1000))
            if oldest else None
        )
        stored = 0
        pages = 0

        while True:
            rows = await self.fetch_historical_klines(
                symbol, "1m", limit=page_size, after=after
            )
            if not rows:
                break
            with store.get_session() as session:
                new = store.save_klines_batch(session, rows)
                session.commit()
            stored += new
            pages += 1
            oldest = min(row["timestamp"] for row in rows)
            next_after = str(int(oldest.replace(tzinfo=timezone.utc).timestamp() * 1000))
            print(
                f"[full-backfill] {symbol}: page={pages} +{new} "
                f"stored={stored} oldest={oldest.isoformat()}"
            )
            if next_after == after:
                break
            after = next_after
            if pause_sec:
                await asyncio.sleep(pause_sec)

        return {"symbol": symbol, "stored": stored, "oldest": oldest, "pages": pages}

    async def fetch_funding_rate(self, symbol: str = "BTC-USDT-SWAP") -> dict:
        row = await self._get("/fapi/v1/premiumIndex", {"symbol": self._symbol(symbol)})
        timestamp_ms = int(row.get("time") or row.get("nextFundingTime"))
        return {
            "symbol": symbol,
            "timestamp": datetime.utcfromtimestamp(timestamp_ms / 1000),
            "funding_rate": float(row["lastFundingRate"]),
        }
