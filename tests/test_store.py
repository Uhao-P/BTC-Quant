from datetime import datetime, timedelta

from data.store.store import DataStore


def test_existing_kline_is_updated_with_latest_exchange_values(tmp_path):
    store = DataStore(f"sqlite:///{tmp_path / 'store.db'}")
    timestamp = datetime(2026, 7, 28, 10, 0)
    initial = {
        "symbol": "BTC-USDT-SWAP",
        "timeframe": "1m",
        "timestamp": timestamp,
        "open": 100.0,
        "high": 101.0,
        "low": 99.0,
        "close": 100.0,
        "volume": 10.0,
        "quote_volume": 1000.0,
    }
    updated = {
        **initial,
        "high": 110.0,
        "close": 108.0,
        "volume": 25.0,
        "quote_volume": 2700.0,
    }

    with store.get_session() as session:
        assert store.save_kline(session, initial) is True
        session.commit()
        assert store.save_kline(session, updated) is False
        session.commit()

    saved = store.get_klines("BTC-USDT-SWAP", "1m", limit=1)[0]
    assert saved.close == 108.0
    assert saved.high == 110.0
    assert saved.volume == 25.0
    assert saved.quote_volume == 2700.0


def test_higher_timeframes_are_aggregated_from_one_minute_source(tmp_path):
    store = DataStore(f"sqlite:///{tmp_path / 'aggregate.db'}")
    start = datetime(2026, 7, 28, 10, 0)
    rows = [
        {
            "symbol": "BTC-USDT-SWAP",
            "timeframe": "1m",
            "timestamp": start + timedelta(minutes=index),
            "open": 100.0 + index,
            "high": 101.0 + index,
            "low": 99.0 + index,
            "close": 100.5 + index,
            "volume": 10.0 + index,
            "quote_volume": 1000.0 + index,
        }
        for index in range(10)
    ]
    with store.get_session() as session:
        store.save_klines_batch(session, rows)
        session.commit()

    candles = store.get_klines("BTC-USDT-SWAP", "5m", limit=2)

    assert [c.timestamp for c in candles] == [start + timedelta(minutes=5), start]
    assert candles[0].open == 105.0
    assert candles[0].high == 110.0
    assert candles[0].low == 104.0
    assert candles[0].close == 109.5
    assert candles[0].volume == sum(10.0 + index for index in range(5, 10))


def test_cleanup_removes_legacy_derived_candles_only(tmp_path):
    store = DataStore(f"sqlite:///{tmp_path / 'cleanup.db'}")
    timestamp = datetime(2026, 7, 28, 10, 0)
    with store.get_session() as session:
        for timeframe in ("1m", "5m", "1h"):
            store.save_kline(session, {
                "symbol": "BTC-USDT-SWAP",
                "timeframe": timeframe,
                "timestamp": timestamp,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 10.0,
            })
        session.commit()

    assert store.delete_derived_klines() == 2
    assert len(store.get_klines("BTC-USDT-SWAP", "1m", limit=10)) == 1
