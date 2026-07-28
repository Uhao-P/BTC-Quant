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
    parser.add_argument(
        "--all-history",
        action="store_true",
        help="Resume all available 1m history for every configured symbol",
    )
    parser.add_argument(
        "--cleanup-derived",
        action="store_true",
        help="Delete legacy stored 5m/1h candles after a successful full backfill",
    )
    parser.add_argument(
        "--warmup-bars",
        type=int,
        default=10080,
        help="Recent 1m bars loaded for every symbol before deep history (default: 7 days)",
    )
    args = parser.parse_args()

    c = create_collector(settings.MARKET_DATA_PROVIDER)
    try:
        if args.all_history:
            if not hasattr(c, "backfill_all_1m"):
                raise RuntimeError("Full-history mode currently requires MARKET_DATA_PROVIDER=binance")
            for symbol in settings.SYMBOLS:
                print(f"Warming {symbol} with {args.warmup_bars} recent 1m bars...")
                await c.backfill_klines(symbol, "1m", args.warmup_bars)
            for symbol in settings.SYMBOLS:
                result = await c.backfill_all_1m(symbol)
                print(f"Completed {symbol}: {result}")
            if args.cleanup_derived:
                from data.store.store import store
                print(f"Removed {store.delete_derived_klines()} legacy derived candles")
        else:
            print(f"Backfilling {args.bars} bars of {args.timeframe} for {args.symbol}...")
            await c.backfill_klines(args.symbol, args.timeframe, args.bars)
        print("Done.")
    finally:
        await c.close()


if __name__ == "__main__":
    asyncio.run(main())
