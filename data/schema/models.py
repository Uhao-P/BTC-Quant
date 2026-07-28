"""
数据表结构
"""
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Index, Text, event
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Kline(Base):
    """K 线数据"""
    __tablename__ = "klines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(5), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    quote_volume = Column(Float, nullable=True)
    # derived
    oi = Column(Float, nullable=True)  # open interest
    # metadata
    created_at = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_kline_lookup", "symbol", "timeframe", "timestamp", unique=True),
    )


class FundingRate(Base):
    """资金费率"""
    __tablename__ = "funding_rates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    funding_rate = Column(Float, nullable=False)
    funding_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_funding_lookup", "symbol", "timestamp", unique=True),
    )


class IndicatorValue(Base):
    """指标计算结果"""
    __tablename__ = "indicators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(5), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    indicator_name = Column(String(50), nullable=False)
    indicator_value = Column(Float, nullable=True)
    extra_metadata = Column("metadata", Text, nullable=True)  # JSON extra data
    created_at = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_indicator_lookup", "symbol", "timeframe", "indicator_name", "timestamp"),
    )


class Signal(Base):
    """交易信号"""
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(5), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    direction = Column(String(10), nullable=False)  # long / short / neutral
    strength = Column(Float, nullable=False)  # 0.0 ~ 1.0
    strategy = Column(String(50), nullable=False)
    features = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, nullable=False)


def init_db(db_url: str) -> tuple:
    connect_args = {"timeout": 30} if db_url.startswith("sqlite") else {}
    engine = create_engine(db_url, echo=False, connect_args=connect_args)
    if db_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session
