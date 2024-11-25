import asyncio

import aiohttp
import typing as tp

import aiomoex
import ccxt
from functools import cache
from abc import ABC

from ccxt import Exchange
import pandas as pd
import yfinance as yf


class MarketProvider(ABC):

    @property
    def exchange_name(self) -> str:
        return self._exchange_name

    @cache
    def fetch_ohlcv(self, symbol: str, time_frame: str):
        raise NotImplementedError

    @property
    def symbols(self) -> list:
        raise NotImplementedError

    @classmethod
    def new(cls, exchange_name: str) -> tp.Self:
        raise NotImplementedError


class CryptoMarketProvider(MarketProvider):

    def __init__(self, exchange: Exchange) -> None:
        self._exchange: tp.Final = exchange
        # self._time_frame: tp.Final = [
        #     "1h", "4h", "8h", "12h", "1d", "3d", "1w", "1M",
        # ]

    @cache
    def _get_markets(self) -> dict:
        return self._exchange.load_markets()

    @property
    def exchange_name(self) -> str:
        return self._exchange.name

    @property
    def symbols(self) -> list:
        return [k for k in self._get_markets()]

    # @property
    # def time_frame(self) -> list[str]:
    #     return self._time_frame

    @cache
    def fetch_ohlcv(self, symbol: str, time_frame: str):
        # ToDo load all data from since!!!
        # days_back = 365 * 5
        # since = self._exchange.parse8601((datetime.now(UTC) - timedelta(days=days_back)).isoformat())

        df = pd.DataFrame(
            self._exchange.fetch_ohlcv(
                symbol=symbol, timeframe=time_frame
            ),  # , since=since),
            columns=["ms", "open", "high", "low", "close", "volume"],
        )
        df["date"] = df["ms"].map(lambda x: self._exchange.iso8601(x))
        df = df.set_index("ms")
        return df

    @classmethod
    def new(cls, exchange_name) -> tp.Self:
        exchange: Exchange = getattr(ccxt, exchange_name)()
        return cls(exchange=exchange)


class YFinMarketProvider(MarketProvider):
    def __init__(self, exchange_name):
        self._exchange_name = exchange_name
        self._symbols = self._fetch_sp500_symbols()

    @staticmethod
    def _fetch_sp500_symbols() -> list[str]:
        symbols = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )[0]
        return sorted(symbols["Symbol"].to_list())

    @property
    def symbols(self) -> list:
        return self._symbols

    @cache
    def fetch_ohlcv(self, symbol: str, time_frame: str):
        df = yf.download(symbol, interval=time_frame).drop(columns=["Adj Close"])
        df.index = pd.to_datetime(df.index)
        df = df.droplevel("Ticker", axis=1)
        df["date"] = df.index
        df = df.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            },
        )
        return df

    @classmethod
    def new(cls, exchange_name: str) -> tp.Self:
        return cls(exchange_name)


class MoexMarketProvider(MarketProvider):

    def __init__(self, exchange_name):
        self._exchange_name = exchange_name

    @cache
    def fetch_ohlcv(self, symbol: str, time_frame: str):
        async def load_history(name: str):
            async with aiohttp.ClientSession() as session:
                data = await aiomoex.get_board_history(
                    session,
                    name,
                    columns=("TRADEDATE", "OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"),
                    start="2015-01-01",
                    end="2023-12-31",
                )
                df = pd.DataFrame(data)
                df.set_index("TRADEDATE", inplace=True)
                df["date"] = df.index
                df = df.rename(
                    columns={
                        "OPEN": "open",
                        "HIGH": "high",
                        "LOW": "low",
                        "CLOSE": "close",
                        "VOLUME": "volume",
                    },
                )
                return df

        return asyncio.run(load_history(symbol))

    @property
    @cache
    def symbols(self) -> list:
        async def _symbols():
            request_url = (
                "https://iss.moex.com/iss/engines/stock/"
                "markets/shares/boards/TQBR/securities.json"
            )
            arguments = {
                "securities.columns": ("SECID," "REGNUMBER," "LOTSIZE," "SHORTNAME")
            }

            async with aiohttp.ClientSession() as session:
                iss = aiomoex.ISSClient(session, request_url, arguments)
                data = await iss.get()
                df = pd.DataFrame(data["securities"])
                return df["SECID"].to_list()

        return asyncio.run(_symbols())

    @classmethod
    def new(cls, exchange_name: str) -> tp.Self:
        return cls(exchange_name)


class MarketProviderFactory:
    PROVIDERS: dict[tuple[str], type[MarketProvider]] = {
        ("binance", "bybit", "coinbase"): CryptoMarketProvider,
        ("yfinance",): YFinMarketProvider,
        ("moex",): MoexMarketProvider,
    }

    @classmethod
    def new(cls, exchange_name) -> MarketProvider:
        for exchange in cls.PROVIDERS:
            if exchange_name in exchange:
                provider_type: type[MarketProvider] = cls.PROVIDERS[exchange]
                return provider_type.new(exchange_name)
        raise ValueError


class ExchangesProvider:
    def __init__(
        self,
        exchanges: list[str],
    ) -> None:
        self._exchanges: tp.Final[list[str]] = exchanges
        self._market_provider: dict[str, MarketProvider] = {}

    @property
    def exchanges(self) -> list[str]:
        return self._exchanges

    def get_market_provider(self, exchange_name: str) -> MarketProvider:
        if exchange_name not in self._market_provider:
            self._market_provider[exchange_name] = MarketProviderFactory.new(
                exchange_name
            )

        return self._market_provider[exchange_name]

    @classmethod
    def new(cls, exchanges) -> tp.Self:
        return cls(exchanges)
