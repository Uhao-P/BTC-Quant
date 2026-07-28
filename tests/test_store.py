from datetime import datetime

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
