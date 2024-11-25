import typing as tp
from attr import dataclass

from .provider import ExchangesProvider


@dataclass(kw_only=True, frozen=True)
class DataProviderIoC:
    exchanges_provider: tp.Final[ExchangesProvider] = ExchangesProvider.new(
        exchanges=["binance", "bybit", "coinbase", "yfinance", "moex"],
    )


DATA_PROVIDER: tp.Final[DataProviderIoC] = DataProviderIoC()
