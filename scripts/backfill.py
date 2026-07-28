"""
BTC 历史数据回填脚本
"""
import asyncio
import argparse

from config.settings import settings
from data.collectors import create_collector


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframe", default="1h", help="K line timeframe")
    parser.add_argument("--bars", type=int, default=1000, help="Number of bars")
    parser.add_argument("--symbol", default="BTC-USDT-SWAP")
    args = parser.parse_args()

    c = create_collector(settings.MARKET_DATA_PROVIDER)
    print(f"Backfilling {args.bars} bars of {args.timeframe} for {args.symbol}...")
    await c.backfill_klines(args.symbol, args.timeframe, args.bars)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
