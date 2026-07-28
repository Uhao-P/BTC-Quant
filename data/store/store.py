"""
数据存储层
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Optional
from sqlalchemy import func, text
from sqlalchemy.orm import Session as DBSession

from data.schema.models import (
    Kline, FundingRate, IndicatorValue, Signal, init_db,
)
from config.settings import settings


TIMEFRAME_MINUTES = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}


@dataclass
class AggregatedKline:
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: Optional[float] = None


@dataclass(frozen=True)
class PricePoint:
    timestamp: datetime
    close: float


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
        """Insert/update a page without issuing one existence query per candle."""
        if not rows:
            return 0
        new = 0
        grouped = {}
        for row in rows:
            grouped.setdefault((row["symbol"], row["timeframe"]), []).append(row)

        for (symbol, timeframe), group in grouped.items():
            existing = {}
            timestamps = [row["timestamp"] for row in group]
            for start in range(0, len(timestamps), 400):
                chunk = timestamps[start:start + 400]
                found = session.query(Kline).filter(
                    Kline.symbol == symbol,
                    Kline.timeframe == timeframe,
                    Kline.timestamp.in_(chunk),
                ).all()
                existing.update({row.timestamp: row for row in found})

            for row in group:
                saved = existing.get(row["timestamp"])
                if saved is None:
                    session.add(Kline(**row, created_at=datetime.utcnow()))
                    new += 1
                    continue
                saved.open = row["open"]
                saved.high = row["high"]
                saved.low = row["low"]
                saved.close = row["close"]
                saved.volume = row["volume"]
                saved.quote_volume = row.get("quote_volume")
                if "oi" in row:
                    saved.oi = row["oi"]
        return new

    def get_klines(self, symbol: str, timeframe: str,
                   limit: int = 500, offset: int = 0) -> list[Kline]:
        if timeframe != "1m":
            return self._get_aggregated_klines(symbol, timeframe, limit, offset)
        with self.get_session() as s:
            return (
                s.query(Kline)
                .filter(Kline.symbol == symbol, Kline.timeframe == timeframe)
                .order_by(Kline.timestamp.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

    def _get_aggregated_klines(self, symbol: str, timeframe: str,
                               limit: int, offset: int = 0) -> list[AggregatedKline]:
        minutes = TIMEFRAME_MINUTES.get(timeframe)
        if minutes is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        source_limit = (limit + offset + 1) * minutes
        source = self.get_klines(symbol, "1m", limit=source_limit)
        buckets = {}
        bucket_seconds = minutes * 60
        for row in reversed(source):
            epoch = int(row.timestamp.replace(tzinfo=timezone.utc).timestamp())
            bucket_time = datetime.utcfromtimestamp(epoch - epoch % bucket_seconds)
            candle = buckets.get(bucket_time)
            if candle is None:
                buckets[bucket_time] = AggregatedKline(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=bucket_time,
                    open=row.open,
                    high=row.high,
                    low=row.low,
                    close=row.close,
                    volume=row.volume,
                    quote_volume=row.quote_volume,
                )
                continue
            candle.high = max(candle.high, row.high)
            candle.low = min(candle.low, row.low)
            candle.close = row.close
            candle.volume += row.volume
            if candle.quote_volume is not None and row.quote_volume is not None:
                candle.quote_volume += row.quote_volume

        result = list(reversed(list(buckets.values())))
        return result[offset:offset + limit]

    def get_oldest_kline_timestamp(self, symbol: str, timeframe: str = "1m"):
        with self.get_session() as session:
            row = session.query(Kline.timestamp).filter(
                Kline.symbol == symbol,
                Kline.timeframe == timeframe,
            ).order_by(Kline.timestamp.asc()).first()
            return row[0] if row else None

    def get_price_history_overview(self, symbol: str, max_points: int = 2500,
                                   start: datetime = None,
                                   end: datetime = None) -> dict:
        """Return indexed samples for a range; narrow ranges retain every minute."""
        max_points = max(2, max_points)
        with self.get_session() as session:
            query = session.query(
                func.count(Kline.id),
                func.min(Kline.timestamp),
                func.max(Kline.timestamp),
            ).filter(
                Kline.symbol == symbol,
                Kline.timeframe == "1m",
            )
            if start:
                query = query.filter(Kline.timestamp >= start)
            if end:
                query = query.filter(Kline.timestamp <= end)
            bounds = query.one()
            source_count, oldest, latest = bounds
            if not source_count:
                return {
                    "source_count": 0,
                    "oldest": None,
                    "latest": None,
                    "bucket_seconds": 60,
                    "data": [],
                }

            if source_count <= max_points:
                rows_query = session.query(Kline).filter(
                    Kline.symbol == symbol,
                    Kline.timeframe == "1m",
                )
                if start:
                    rows_query = rows_query.filter(Kline.timestamp >= start)
                if end:
                    rows_query = rows_query.filter(Kline.timestamp <= end)
                rows = rows_query.order_by(Kline.timestamp.asc()).all()
                data = [PricePoint(timestamp=row.timestamp, close=row.close) for row in rows]
                return {
                    "source_count": source_count,
                    "oldest": oldest,
                    "latest": latest,
                    "bucket_seconds": 60,
                    "data": data,
                }

            span_seconds = max(60, int((latest - oldest).total_seconds()))
            bucket_seconds = max(60, ceil(span_seconds / (max_points - 1) / 60) * 60)
            sampled = session.execute(text("""
                WITH digits(n) AS (
                    VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9)
                ), numbers(n) AS (
                    SELECT a.n + 10*b.n + 100*c.n + 1000*d.n
                    FROM digits a CROSS JOIN digits b CROSS JOIN digits c CROSS JOIN digits d
                ), targets(epoch) AS (
                    SELECT :start_epoch + n * :bucket
                    FROM numbers
                    WHERE n < :steps AND :start_epoch + n * :bucket < :end_epoch
                    UNION ALL SELECT :end_epoch
                )
                SELECT k.timestamp, k.close, k.volume, k.quote_volume
                FROM targets t
                JOIN klines k
                  ON k.id = (
                    SELECT candidate.id
                    FROM klines candidate
                    WHERE candidate.symbol = :symbol
                      AND candidate.timeframe = '1m'
                      AND candidate.timestamp >= datetime(t.epoch, 'unixepoch')
                      AND candidate.timestamp <= :latest
                    ORDER BY candidate.timestamp ASC
                    LIMIT 1
                  )
                ORDER BY k.timestamp ASC
            """), {
                "symbol": symbol,
                "bucket": bucket_seconds,
                "steps": max_points - 1,
                "start_epoch": int(oldest.replace(tzinfo=timezone.utc).timestamp()),
                "end_epoch": int(latest.replace(tzinfo=timezone.utc).timestamp()),
                "latest": latest,
            }).all()
            by_timestamp = {}
            for row in sampled:
                timestamp = (row.timestamp if isinstance(row.timestamp, datetime)
                             else datetime.fromisoformat(row.timestamp))
                by_timestamp[timestamp] = PricePoint(timestamp=timestamp, close=row.close)
            endpoint_rows = session.query(Kline).filter(
                Kline.symbol == symbol,
                Kline.timeframe == "1m",
                Kline.timestamp.in_([oldest, latest]),
            ).all()
            for row in endpoint_rows:
                by_timestamp[row.timestamp] = PricePoint(
                    timestamp=row.timestamp, close=row.close
                )
            data = [by_timestamp[key] for key in sorted(by_timestamp)]
            if len(data) > max_points:
                interior = data[1:-1]
                slots = max_points - 2
                indexes = {
                    round(index * (len(interior) - 1) / max(slots - 1, 1))
                    for index in range(slots)
                }
                data = [data[0]] + [
                    point for index, point in enumerate(interior) if index in indexes
                ][:slots] + [data[-1]]
            return {
                "source_count": source_count,
                "oldest": oldest,
                "latest": latest,
                "bucket_seconds": bucket_seconds,
                "data": data,
            }

    def delete_derived_klines(self) -> int:
        """Remove legacy materialized candles; every higher interval is derived from 1m."""
        with self.get_session() as session:
            deleted = session.query(Kline).filter(Kline.timeframe != "1m").delete(
                synchronize_session=False
            )
            session.commit()
            return deleted

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
        existing = session.query(Signal).filter(
            Signal.symbol == row["symbol"],
            Signal.timeframe == row["timeframe"],
            Signal.timestamp == row["timestamp"],
            Signal.strategy == row["strategy"],
        ).first()
        if existing:
            existing.direction = row["direction"]
            existing.strength = row["strength"]
            existing.features = row.get("features")
            existing.created_at = datetime.utcnow()
            return False
        sg = Signal(**row, created_at=datetime.utcnow())
        session.add(sg)
        return True

    def get_signals(self, symbol: str, strategy: str = None,
                    limit: int = 100) -> list[Signal]:
        with self.get_session() as s:
            q = s.query(Signal).filter(Signal.symbol == symbol)
            if strategy:
                q = q.filter(Signal.strategy == strategy)
            return q.order_by(Signal.timestamp.desc(), Signal.id.desc()).limit(limit).all()

    def prune_research_data(self, signal_days: int = 365,
                            indicator_days: int = 90) -> dict:
        """Expire research caches and remove legacy duplicate signal rows."""
        now = datetime.utcnow()
        with self.get_session() as session:
            old_signals = session.query(Signal).filter(
                Signal.timestamp < now - timedelta(days=signal_days)
            ).delete(synchronize_session=False)
            old_indicators = session.query(IndicatorValue).filter(
                IndicatorValue.timestamp < now - timedelta(days=indicator_days)
            ).delete(synchronize_session=False)

            duplicate_signals = 0
            seen = set()
            rows = session.query(Signal).order_by(
                Signal.created_at.desc(), Signal.id.desc()
            ).all()
            for row in rows:
                key = (row.symbol, row.timeframe, row.timestamp, row.strategy)
                if key in seen:
                    session.delete(row)
                    duplicate_signals += 1
                else:
                    seen.add(key)
            session.commit()
            return {
                "old_signals": old_signals,
                "old_indicators": old_indicators,
                "duplicate_signals": duplicate_signals,
            }


store = DataStore()
