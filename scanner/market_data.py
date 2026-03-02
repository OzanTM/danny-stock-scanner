from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import socket

import pandas as pd
import yfinance as yf

from .models import CompanyInfo

logger = logging.getLogger(__name__)


@dataclass
class MarketDataset:
    price: pd.DataFrame
    info: CompanyInfo


class YahooMarketDataClient:
    REQUIRED_BASE = ["Open", "High", "Low"]

    @staticmethod
    def is_data_source_reachable() -> bool:
        try:
            socket.getaddrinfo("query1.finance.yahoo.com", 443, type=socket.SOCK_STREAM)
            return True
        except OSError:
            return False

    def fetch_many(
        self,
        tickers: list[str],
        *,
        period: str,
        interval: str,
        timeout_seconds: int,
        max_workers: int,
    ) -> dict[str, MarketDataset]:
        # Faster path: fetch prices in batch chunks instead of one request per ticker.
        unique = []
        seen = set()
        for ticker in tickers:
            if ticker not in seen:
                unique.append(ticker)
                seen.add(ticker)

        datasets: dict[str, MarketDataset] = {}
        if not unique:
            return datasets

        chunk_size = 100
        for i in range(0, len(unique), chunk_size):
            chunk = unique[i : i + chunk_size]
            downloaded = self._download_chunk(
                chunk,
                period=period,
                interval=interval,
                timeout_seconds=timeout_seconds,
            )
            for ticker, prices in downloaded.items():
                datasets[ticker] = MarketDataset(price=prices, info=CompanyInfo())
        return datasets

    def fetch_info_many(
        self,
        tickers: list[str],
        *,
        timeout_seconds: int,
        max_workers: int,
    ) -> dict[str, CompanyInfo]:
        if not tickers:
            return {}

        workers = max(1, min(max_workers, len(tickers)))
        infos: dict[str, CompanyInfo] = {}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {
                executor.submit(self._fetch_one_info, ticker, timeout_seconds=timeout_seconds): ticker
                for ticker in tickers
            }
            for future in as_completed(future_map):
                ticker = future_map[future]
                try:
                    info = future.result()
                except Exception:
                    logger.warning("Ticker bilgisi alinamadi: %s", ticker, exc_info=True)
                    info = CompanyInfo()
                infos[ticker] = info
        return infos

    def _download_chunk(
        self,
        tickers: list[str],
        *,
        period: str,
        interval: str,
        timeout_seconds: int,
    ) -> dict[str, pd.DataFrame]:
        try:
            df = yf.download(
                tickers=tickers,
                period=period,
                interval=interval,
                auto_adjust=False,
                group_by="ticker",
                threads=True,
                progress=False,
                timeout=timeout_seconds,
            )
        except Exception:
            logger.warning("Fiyat verisi indirilemedi (chunk: %s)", tickers[:3], exc_info=True)
            return {}

        result: dict[str, pd.DataFrame] = {}
        if df is None or df.empty:
            return result

        if isinstance(df.columns, pd.MultiIndex):
            top_level = set(df.columns.get_level_values(0))
            for ticker in tickers:
                if ticker not in top_level:
                    continue
                frame = df[ticker]
                parsed = self._normalize_ohlc(frame)
                if parsed is not None:
                    result[ticker] = parsed
            return result

        # Single ticker fallback response shape
        parsed = self._normalize_ohlc(df)
        if parsed is not None and tickers:
            result[tickers[0]] = parsed
        return result

    def _normalize_ohlc(self, frame: pd.DataFrame) -> pd.DataFrame | None:
        if frame is None or frame.empty:
            return None

        close_column = "Adj Close" if "Adj Close" in frame.columns else "Close"
        required = self.REQUIRED_BASE + [close_column]
        if any(col not in frame.columns for col in required):
            return None

        prices = frame[required].rename(columns={close_column: "Close"})
        prices = prices[~prices.index.duplicated(keep="last")].dropna()
        return prices if not prices.empty else None

    def _fetch_one_info(self, ticker: str, *, timeout_seconds: int) -> CompanyInfo:
        try:
            stock = yf.Ticker(ticker)
            info_raw = stock.info or {}
            return CompanyInfo(
                name=info_raw.get("longName") or "Bilinmiyor",
                sector=info_raw.get("sector") or "Bilinmiyor",
                industry=info_raw.get("industry") or "Bilinmiyor",
                market_cap=float(info_raw.get("marketCap") or 0.0),
            )
        except Exception:
            logger.warning("Ticker bilgisi alinamadi: %s", ticker, exc_info=True)
            return CompanyInfo()
