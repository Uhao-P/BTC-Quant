"""
数据采集调度器 — 定时拉取 OKX 数据
"""
import asyncio
import time
from datetime import datetime

from config.settings import settings
from data.collectors.okx_collector import OKXCollector
from data.store.store import store


class CollectorScheduler:
    """定时采集调度器"""

    def __init__(self):
        self.collector = OKXCollector()
        self._running = False

    async def run_once(self):
        """拉取一次所有配置的数据"""
        print(f"[{datetime.now().isoformat()}] Collecting data...")
        for symbol in settings.SYMBOLS:
            for tf in settings.COLLECTION_TIMEFRAMES:
                try:
                    rows = await self.collector.fetch_historical_klines(
                        symbol, tf, limit=5
                    )
                    with store.get_session() as session:
                        new = store.save_klines_batch(session, rows)
                        session.commit()
                    print(f"  {symbol} {tf}: +{new} klines")
                except Exception as e:
                    print(f"  ERROR {symbol} {tf}: {e}")
                await asyncio.sleep(0.3)

        # Funding rate
        for symbol in settings.SYMBOLS:
            try:
                fr = await self.collector.fetch_funding_rate(symbol)
                with store.get_session() as session:
                    store.save_funding_rate(session, fr)
                    session.commit()
                print(f"  {symbol} funding rate: {fr['funding_rate']:.6f}")
            except Exception as e:
                print(f"  ERROR {symbol} funding: {e}")

    async def run_loop(self, interval_sec: int = 60):
        """定时循环"""
        self._running = True
        print(f"[Scheduler] Starting collection loop every {interval_sec}s")
        while self._running:
            await self.run_once()
            await asyncio.sleep(interval_sec)


if __name__ == "__main__":
    scheduler = CollectorScheduler()
    asyncio.run(scheduler.run_loop(interval_sec=60))
