from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

# Signal constants used throughout the project
SIGNAL_BULLISH = "Bullish (Kırmızı Mum)"
SIGNAL_BEARISH = "Bearish (Sarı Mum)"
SIGNAL_NONE = "Yok"

# Valid sort fields for whitelist validation
VALID_SORT_FIELDS = frozenset({
    "ticker", "name", "sector", "industry", "close_price", "market_cap",
    "date", "signal", "rsi_14", "atr_pct", "bb_width_pct", "macd_hist",
})


@dataclass(frozen=True)
class CompanyInfo:
    name: str = "Bilinmiyor"
    sector: str = "Bilinmiyor"
    industry: str = "Bilinmiyor"
    market_cap: float = 0.0


@dataclass(frozen=True)
class StockSignalResult:
    ticker: str
    date: str
    close_price: float
    signal: str
    prev_signal_1: str
    prev_signal_2: str
    prev_signal_3: str
    prev_signal_4: str
    name: str
    sector: str
    industry: str
    market_cap: float
    trend_view: str = "-"
    trend_level: str = "neutral"
    momentum_view: str = "-"
    momentum_level: str = "neutral"
    timing_view: str = "-"
    timing_level: str = "neutral"
    breakout_view: str = "-"
    breakout_level: str = "neutral"
    risk_view: str = "-"
    risk_level: str = "neutral"
    ema_9: float = 0.0
    ema_20: float = 0.0
    ema_50: float = 0.0
    macd_line: float = 0.0
    macd_signal: float = 0.0
    macd_hist: float = 0.0
    rsi_14: float = 50.0
    kdj_j: float = 50.0
    bb_upper: float = 0.0
    bb_lower: float = 0.0
    bb_width_pct: float = 0.0
    atr_14: float = 0.0
    atr_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScanFilters:
    sector: str = "all"
    industry: str = "all"
    signal: str = "all"
    market_cap_min: float | None = None
    market_cap_max: float | None = None
    sort_by: str = "ticker"
    sort_dir: str = "asc"
    trend_level: str = "all"
    momentum_level: str = "all"
    timing_level: str = "all"
    breakout_level: str = "all"
    risk_level: str = "all"
    rsi_min: float | None = None
    rsi_max: float | None = None
    atr_pct_min: float | None = None
    atr_pct_max: float | None = None
    bb_width_max: float | None = None

    @classmethod
    def from_form(cls, form: Any) -> "ScanFilters":
        def parse_float(value: str | None) -> float | None:
            if not value:
                return None
            try:
                return float(value)
            except ValueError:
                return None

        return cls(
            sector=(form.get("sector") or "all").strip() or "all",
            industry=(form.get("industry") or "all").strip() or "all",
            signal=(form.get("signal") or "all").strip() or "all",
            market_cap_min=parse_float(form.get("market_cap_min")),
            market_cap_max=parse_float(form.get("market_cap_max")),
            sort_by=(form.get("sort_by") or "ticker").strip() or "ticker",
            sort_dir=(form.get("sort_dir") or "asc").strip() or "asc",
            trend_level=(form.get("trend_level") or "all").strip() or "all",
            momentum_level=(form.get("momentum_level") or "all").strip() or "all",
            timing_level=(form.get("timing_level") or "all").strip() or "all",
            breakout_level=(form.get("breakout_level") or "all").strip() or "all",
            risk_level=(form.get("risk_level") or "all").strip() or "all",
            rsi_min=parse_float(form.get("rsi_min")),
            rsi_max=parse_float(form.get("rsi_max")),
            atr_pct_min=parse_float(form.get("atr_pct_min")),
            atr_pct_max=parse_float(form.get("atr_pct_max")),
            bb_width_max=parse_float(form.get("bb_width_max")),
        )

    def to_form_dict(self) -> dict[str, str]:
        return {
            "sector": self.sector,
            "industry": self.industry,
            "signal": self.signal,
            "market_cap_min": "" if self.market_cap_min is None else f"{self.market_cap_min:g}",
            "market_cap_max": "" if self.market_cap_max is None else f"{self.market_cap_max:g}",
            "sort_by": self.sort_by,
            "sort_dir": self.sort_dir,
            "trend_level": self.trend_level,
            "momentum_level": self.momentum_level,
            "timing_level": self.timing_level,
            "breakout_level": self.breakout_level,
            "risk_level": self.risk_level,
            "rsi_min": "" if self.rsi_min is None else f"{self.rsi_min:g}",
            "rsi_max": "" if self.rsi_max is None else f"{self.rsi_max:g}",
            "atr_pct_min": "" if self.atr_pct_min is None else f"{self.atr_pct_min:g}",
            "atr_pct_max": "" if self.atr_pct_max is None else f"{self.atr_pct_max:g}",
            "bb_width_max": "" if self.bb_width_max is None else f"{self.bb_width_max:g}",
        }
