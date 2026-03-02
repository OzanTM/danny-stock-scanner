from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TickerRepository:
    def __init__(self, ticker_file: Path) -> None:
        self._ticker_file = ticker_file
        self._cached_tickers: list[str] = []
        self._cached_mtime: float = 0.0

    def read_tickers(self) -> list[str]:
        if not self._ticker_file.exists():
            logger.warning("Ticker dosyasi bulunamadi: %s", self._ticker_file)
            return []

        current_mtime = self._ticker_file.stat().st_mtime
        if self._cached_tickers and current_mtime == self._cached_mtime:
            return self._cached_tickers

        tickers: list[str] = []
        with self._ticker_file.open("r", encoding="utf-8") as file:
            for line in file:
                symbol = line.strip().upper()
                if symbol:
                    tickers.append(symbol)

        self._cached_tickers = tickers
        self._cached_mtime = current_mtime
        logger.info("Ticker dosyasi okundu: %d ticker yuklendi", len(tickers))
        return tickers
