"""
数据存储层
"""
from datetime import datetime
from sqlalchemy.orm import Session as DBSession

from data.schema.models import (
    Kline, FundingRate, IndicatorValue, Signal, init_db,
)
from config.settings import settings


class DataStore:
    def __init__(self, db_url: str = settings.DATABASE_URL):
        self.engine, self.Session = init_db(db_url)

    def get_session(self) -> DBSession:
        return self.Session()

    # --- Klines ---
    def save_kline(self, session: DBSession, row: dict) -> bool:
        """return True if newly inserted, False if duplicate skipped"""
        exists = session.query(Kline).filter(
            Kline.symbol == row["symbol"],
            Kline.timeframe == row["timeframe"],
            Kline.timestamp == row["timestamp"],
        ).first()
        if exists:
            exists.open = row["open"]
            exists.high = row["high"]
            exists.low = row["low"]
            exists.close = row["close"]
            exists.volume = row["volume"]
            exists.quote_volume = row.get("quote_volume")
            if "oi" in row:
                exists.oi = row["oi"]
            return False
        k = Kline(**row, created_at=datetime.utcnow())
        session.add(k)
        return True

    def save_klines_batch(self, session: DBSession, rows: list[dict]):
        new = 0
        for r in rows:
            if self.save_kline(session, r):
                new += 1
        return new

    def get_klines(self, symbol: str, timeframe: str,
                   limit: int = 500, offset: int = 0) -> list[Kline]:
        with self.get_session() as s:
            return (
                s.query(Kline)
                .filter(Kline.symbol == symbol, Kline.timeframe == timeframe)
                .order_by(Kline.timestamp.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

    # --- Funding Rates ---
    def save_funding_rate(self, session: DBSession, row: dict) -> bool:
        exists = session.query(FundingRate).filter(
            FundingRate.symbol == row["symbol"],
            FundingRate.timestamp == row["timestamp"],
        ).first()
        if exists:
            return False
        fr = FundingRate(**row, created_at=datetime.utcnow())
        session.add(fr)
        return True

    def get_funding_rates(self, symbol: str, limit: int = 100) -> list[FundingRate]:
        with self.get_session() as s:
            return (
                s.query(FundingRate)
                .filter(FundingRate.symbol == symbol)
                .order_by(FundingRate.timestamp.desc())
                .limit(limit)
                .all()
            )

    # --- Indicators ---
    def save_indicator(self, session: DBSession, row: dict):
        iv = IndicatorValue(**row, created_at=datetime.utcnow())
        session.add(iv)

    # --- Signals ---
    def save_signal(self, session: DBSession, row: dict):
        sg = Signal(**row, created_at=datetime.utcnow())
        session.add(sg)

    def get_signals(self, symbol: str, strategy: str = None,
                    limit: int = 100) -> list[Signal]:
        with self.get_session() as s:
            q = s.query(Signal).filter(Signal.symbol == symbol)
            if strategy:
                q = q.filter(Signal.strategy == strategy)
            return q.order_by(Signal.timestamp.desc()).limit(limit).all()


store = DataStore()
