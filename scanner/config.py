from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScannerConfig:
    ticker_file: Path
    period: str = "3mo"
    interval: str = "1d"
    kdj_length: int = 9
    kdj_signal: int = 3
    min_bars: int = 30
    signal_level: float = 50.0
    history_days: int = 5
    max_tickers: int | None = None
    request_timeout_seconds: int = 3
    max_workers: int = 12

    @classmethod
    def from_project_root(cls, project_root: Path) -> "ScannerConfig":
        return cls(ticker_file=project_root / "all_tickers.txt")
