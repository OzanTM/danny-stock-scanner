from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import socket
import time

import pandas as pd
import yfinance as yf

from .models import CompanyInfo

logger = logging.getLogger(__name__)

# User-Agent to avoid being blocked as a scraper
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"


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
        """Download price data with retry logic for failed chunks."""
        max_retries = 1
        retry_delay = 1  # second

        for attempt in range(max_retries + 1):
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
                return self._process_download_result(df, tickers)
            except Exception as e:
                if attempt < max_retries:
                    logger.debug("Fiyat verisi retry (chunk: %s, attempt %d/%d)",
                                tickers[:2], attempt + 1, max_retries)
                    time.sleep(retry_delay)
                    continue
                logger.warning("Fiyat verisi indirilemedi (chunk: %s)", tickers[:3], exc_info=True)
                return {}

    def _process_download_result(
        self, df: pd.DataFrame | None, tickers: list[str]
    ) -> dict[str, pd.DataFrame]:
        """Process yfinance download result into normalized OHLC data."""
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
        """Fetch company info with exponential backoff retry logic."""
        max_retries = 2
        retry_delays = [1, 2]  # seconds between retries

        for attempt in range(max_retries + 1):
            try:
                stock = yf.Ticker(ticker, session=None)
                info_raw = stock.info or {}
                return CompanyInfo(
                    name=info_raw.get("longName") or "Bilinmiyor",
                    sector=info_raw.get("sector") or "Bilinmiyor",
                    industry=info_raw.get("industry") or "Bilinmiyor",
                    market_cap=float(info_raw.get("marketCap") or 0.0),
                )
            except TypeError as e:
                # Handle: "argument of type 'NoneType' is not iterable" (HTTP 401 issue)
                if "NoneType" in str(e) and attempt < max_retries:
                    logger.debug("HTTP 401 (NoneType error) for %s, retry %d/%d", ticker, attempt + 1, max_retries)
                    time.sleep(retry_delays[attempt])
                    continue
                logger.warning("Ticker bilgisi alinamadi (HTTP hatas): %s", ticker)
                return CompanyInfo()
            except Exception as e:
                # Handle timeout and network errors with retry
                error_str = str(e).lower()
                is_retryable = any(
                    err in error_str
                    for err in ["401", "429", "timeout", "connection", "temporary"]
                )

                if is_retryable and attempt < max_retries:
                    logger.debug("Retryable error for %s (attempt %d/%d): %s",
                                ticker, attempt + 1, max_retries, type(e).__name__)
                    time.sleep(retry_delays[attempt])
                    continue

                logger.warning("Ticker bilgisi alinamadi: %s (%s)", ticker, type(e).__name__)
                return CompanyInfo()

        return CompanyInfo()
