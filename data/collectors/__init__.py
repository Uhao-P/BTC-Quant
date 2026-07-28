"""Market-data collector selection."""


def create_collector(provider: str):
    provider = provider.lower().strip()
    if provider == "binance":
        from data.collectors.binance_collector import BinanceCollector

        return BinanceCollector()
    if provider == "okx":
        from data.collectors.okx_collector import OKXCollector

        return OKXCollector()
    raise ValueError(f"Unsupported market data provider: {provider}")

