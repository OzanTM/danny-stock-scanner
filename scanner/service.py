from __future__ import annotations

import logging

from .config import ScannerConfig
from .indicators import add_standard_indicators, compute_kdj
from .market_data import YahooMarketDataClient
from .models import SIGNAL_BULLISH, SIGNAL_BEARISH, SIGNAL_NONE, VALID_SORT_FIELDS, ScanFilters, StockSignalResult
from .repository import TickerRepository

logger = logging.getLogger(__name__)

_FLOAT_SORT_FIELDS = frozenset({
    "close_price", "market_cap", "rsi_14", "atr_pct", "bb_width_pct", "macd_hist",
})
_STR_SORT_FIELDS = frozenset({
    "ticker", "name", "sector", "industry", "date", "signal",
})
_UPPER_SORT_FIELDS = frozenset({"ticker", "name", "sector", "industry"})


class StockScannerService:
    def __init__(self, config: ScannerConfig) -> None:
        self._config = config
        self._ticker_repo = TickerRepository(config.ticker_file)
        self._market_client = YahooMarketDataClient()

    def run_scan(self) -> tuple[list[dict], str | None]:
        tickers = self._ticker_repo.read_tickers()
        if not tickers:
            return [], "Ticker dosyası bulunamadı veya boş."

        if not self._market_client.is_data_source_reachable():
            return [], "Yahoo Finance veri kaynağına erişim yok. İnternet/DNS bağlantını kontrol et."

        if self._config.max_tickers and self._config.max_tickers > 0:
            tickers = tickers[: self._config.max_tickers]

        datasets = self._market_client.fetch_many(
            tickers,
            period=self._config.period,
            interval=self._config.interval,
            timeout_seconds=self._config.request_timeout_seconds,
            max_workers=self._config.max_workers,
        )
        if not datasets:
            return [], "Veri kaynaklarına ulaşılamadı veya zaman aşımı oluştu."

        candidates: list[dict] = []
        for ticker, dataset in datasets.items():
            df = dataset.price
            if len(df) < max(self._config.min_bars, self._config.kdj_length + self._config.kdj_signal):
                continue

            kdj_df = compute_kdj(
                df,
                length=self._config.kdj_length,
                signal=self._config.kdj_signal,
                threshold=self._config.signal_level,
            )
            kdj_df = add_standard_indicators(kdj_df)
            last = kdj_df.iloc[-1]
            if not (bool(last["cross_over"]) or bool(last["cross_under"])):
                continue

            signal_tail = kdj_df["signal"].tail(self._config.history_days).tolist()
            if len(signal_tail) < self._config.history_days:
                signal_tail = [SIGNAL_NONE] * (self._config.history_days - len(signal_tail)) + signal_tail

            today_signal = signal_tail[-1]
            prev = list(reversed(signal_tail[:-1]))
            while len(prev) < 4:
                prev.append(SIGNAL_NONE)

            candidates.append(
                {
                    "ticker": ticker,
                    "date": kdj_df.index[-1].strftime("%Y-%m-%d"),
                    "close_price": round(float(last["Close"]), 2),
                    "signal": today_signal,
                    "prev_signal_1": prev[0],
                    "prev_signal_2": prev[1],
                    "prev_signal_3": prev[2],
                    "prev_signal_4": prev[3],
                    **self._build_signal_views(last),
                }
            )

        info_map = self._market_client.fetch_info_many(
            [item["ticker"] for item in candidates],
            timeout_seconds=self._config.request_timeout_seconds,
            max_workers=self._config.max_workers,
        )

        results: list[StockSignalResult] = []
        for item in candidates:
            info = info_map.get(item["ticker"])
            if info is None:
                logger.warning("Ticker bilgisi alinamadi, sonuclardan cikariliyor: %s", item["ticker"])
                continue
            results.append(
                StockSignalResult(
                    ticker=item["ticker"],
                    date=item["date"],
                    close_price=item["close_price"],
                    signal=item["signal"],
                    prev_signal_1=item["prev_signal_1"],
                    prev_signal_2=item["prev_signal_2"],
                    prev_signal_3=item["prev_signal_3"],
                    prev_signal_4=item["prev_signal_4"],
                    name=info.name,
                    sector=info.sector,
                    industry=info.industry,
                    market_cap=info.market_cap,
                    trend_view=item["trend_view"],
                    trend_level=item["trend_level"],
                    momentum_view=item["momentum_view"],
                    momentum_level=item["momentum_level"],
                    timing_view=item["timing_view"],
                    timing_level=item["timing_level"],
                    breakout_view=item["breakout_view"],
                    breakout_level=item["breakout_level"],
                    risk_view=item["risk_view"],
                    risk_level=item["risk_level"],
                    ema_9=item["ema_9"],
                    ema_20=item["ema_20"],
                    ema_50=item["ema_50"],
                    macd_line=item["macd_line"],
                    macd_signal=item["macd_signal"],
                    macd_hist=item["macd_hist"],
                    rsi_14=item["rsi_14"],
                    kdj_j=item["kdj_j"],
                    bb_upper=item["bb_upper"],
                    bb_lower=item["bb_lower"],
                    bb_width_pct=item["bb_width_pct"],
                    atr_14=item["atr_14"],
                    atr_pct=item["atr_pct"],
                )
            )

        result_dicts = [item.to_dict() for item in results]
        result_dicts.sort(key=lambda item: (item["signal"], item["ticker"]))
        return result_dicts, None

    @staticmethod
    def _safe_float(value, fallback: float = 0.0) -> float:
        try:
            if value is None:
                return fallback
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def _build_signal_views(self, last) -> dict[str, str | float]:
        close_price = self._safe_float(last.get("Close"))
        ema9 = self._safe_float(last.get("ema_9"))
        ema20 = self._safe_float(last.get("ema_20"))
        ema50 = self._safe_float(last.get("ema_50"))
        macd_line = self._safe_float(last.get("macd_line"))
        macd_signal = self._safe_float(last.get("macd_signal"))
        macd_hist = self._safe_float(last.get("macd_hist"))
        rsi14 = self._safe_float(last.get("rsi_14"), 50.0)
        j_value = self._safe_float(last.get("j"), 50.0)
        bb_width = self._safe_float(last.get("bb_width_pct"))
        bb_upper = self._safe_float(last.get("bb_upper"))
        bb_lower = self._safe_float(last.get("bb_lower"))
        atr_pct = self._safe_float(last.get("atr_pct"))

        if close_price > ema50 and ema20 > ema50:
            trend_view, trend_level = "Trend Var (Yukarı)", "good"
        elif close_price < ema50 and ema20 < ema50:
            trend_view, trend_level = "Trend Aşağı", "bad"
        else:
            trend_view, trend_level = "Trend Nötr", "neutral"

        if macd_line > macd_signal and macd_hist > 0:
            momentum_view, momentum_level = "Güçleniyor", "good"
        elif macd_line < macd_signal and macd_hist < 0:
            momentum_view, momentum_level = "Zayıflıyor", "bad"
        else:
            momentum_view, momentum_level = "Nötr", "neutral"

        if rsi14 > 70 or j_value > 85:
            timing_view, timing_level = "Geç / Isınmış", "bad"
        elif rsi14 < 35 and j_value < 20:
            timing_view, timing_level = "Erken / Zayıf", "warn"
        elif 45 <= rsi14 <= 65 and 40 <= j_value <= 70:
            timing_view, timing_level = "Uygun", "good"
        else:
            timing_view, timing_level = "Nötr", "neutral"

        if close_price > bb_upper > 0:
            breakout_view, breakout_level = "Yukarı Patlama", "good"
        elif close_price < bb_lower and bb_lower > 0:
            breakout_view, breakout_level = "Aşağı Patlama", "bad"
        elif bb_width > 0 and bb_width < 6:
            breakout_view, breakout_level = "Sıkışma (Aday)", "warn"
        else:
            breakout_view, breakout_level = "Normal", "neutral"

        if atr_pct >= 4:
            risk_view, risk_level = "Yüksek Risk", "bad"
        elif atr_pct >= 2:
            risk_view, risk_level = "Orta Risk", "warn"
        else:
            risk_view, risk_level = "Düşük Risk", "good"

        return {
            "trend_view": trend_view,
            "trend_level": trend_level,
            "momentum_view": momentum_view,
            "momentum_level": momentum_level,
            "timing_view": timing_view,
            "timing_level": timing_level,
            "breakout_view": breakout_view,
            "breakout_level": breakout_level,
            "risk_view": risk_view,
            "risk_level": risk_level,
            "ema_9": round(ema9, 4),
            "ema_20": round(ema20, 4),
            "ema_50": round(ema50, 4),
            "macd_line": round(macd_line, 6),
            "macd_signal": round(macd_signal, 6),
            "macd_hist": round(macd_hist, 6),
            "rsi_14": round(rsi14, 2),
            "kdj_j": round(j_value, 2),
            "bb_upper": round(bb_upper, 4),
            "bb_lower": round(bb_lower, 4),
            "bb_width_pct": round(bb_width, 2),
            "atr_14": round(self._safe_float(last.get("atr_14")), 4),
            "atr_pct": round(atr_pct, 2),
        }

    @staticmethod
    def build_filter_options(results: list[dict]) -> tuple[list[str], list[str]]:
        sectors = sorted({r["sector"] for r in results if r["sector"] != "Bilinmiyor"})
        industries = sorted({r["industry"] for r in results if r["industry"] != "Bilinmiyor"})
        return sectors, industries

    @staticmethod
    def apply_filters(results: list[dict], filters: ScanFilters) -> list[dict]:
        filtered: list[dict] = []
        for item in results:
            if filters.sector != "all" and item["sector"] != filters.sector:
                continue
            if filters.industry != "all" and item["industry"] != filters.industry:
                continue
            if filters.signal != "all" and item["signal"] != filters.signal:
                continue
            mcap = float(item["market_cap"])
            if filters.market_cap_min is not None and mcap < filters.market_cap_min:
                continue
            if filters.market_cap_max is not None and mcap > filters.market_cap_max:
                continue
            if filters.trend_level != "all" and item.get("trend_level") != filters.trend_level:
                continue
            if filters.momentum_level != "all" and item.get("momentum_level") != filters.momentum_level:
                continue
            if filters.timing_level != "all" and item.get("timing_level") != filters.timing_level:
                continue
            if filters.breakout_level != "all" and item.get("breakout_level") != filters.breakout_level:
                continue
            if filters.risk_level != "all" and item.get("risk_level") != filters.risk_level:
                continue
            rsi = float(item.get("rsi_14", 0.0))
            if filters.rsi_min is not None and rsi < filters.rsi_min:
                continue
            if filters.rsi_max is not None and rsi > filters.rsi_max:
                continue
            atr = float(item.get("atr_pct", 0.0))
            if filters.atr_pct_min is not None and atr < filters.atr_pct_min:
                continue
            if filters.atr_pct_max is not None and atr > filters.atr_pct_max:
                continue
            if filters.bb_width_max is not None and float(item.get("bb_width_pct", 0.0)) > filters.bb_width_max:
                continue
            filtered.append(item)

        sort_by = filters.sort_by if filters.sort_by in VALID_SORT_FIELDS else "ticker"
        descending = (filters.sort_dir or "asc").lower() == "desc"

        if sort_by in _FLOAT_SORT_FIELDS:
            filtered.sort(key=lambda item: float(item.get(sort_by, 0.0)), reverse=descending)
        elif sort_by in _UPPER_SORT_FIELDS:
            filtered.sort(key=lambda item: str(item.get(sort_by, "")).upper(), reverse=descending)
        else:
            filtered.sort(key=lambda item: str(item.get(sort_by, "")), reverse=descending)
        return filtered

    @staticmethod
    def default_form_state() -> dict[str, str]:
        return ScanFilters().to_form_dict()

    @staticmethod
    def build_signal_summary(results: list[dict]) -> dict:
        total = 0
        bullish = 0
        bearish = 0
        sector_buckets: dict[str, dict] = {}
        industry_buckets: dict[str, dict] = {}
        sector_industry_map: dict[str, dict[str, dict]] = {}

        def _inc(bucket: dict, is_bull: bool, is_bear: bool) -> None:
            bucket["total"] += 1
            if is_bull:
                bucket["bullish"] += 1
            elif is_bear:
                bucket["bearish"] += 1

        def _ensure(store: dict[str, dict], key: str) -> dict:
            if key not in store:
                store[key] = {"name": key, "total": 0, "bullish": 0, "bearish": 0}
            return store[key]

        for item in results:
            total += 1
            signal = item.get("signal")
            is_bull = signal == SIGNAL_BULLISH
            is_bear = signal == SIGNAL_BEARISH
            if is_bull:
                bullish += 1
            elif is_bear:
                bearish += 1

            sector = item.get("sector") or "Bilinmiyor"
            industry = item.get("industry") or "Bilinmiyor"

            _inc(_ensure(sector_buckets, sector), is_bull, is_bear)
            _inc(_ensure(industry_buckets, industry), is_bull, is_bear)

            si_bucket = sector_industry_map.setdefault(sector, {})
            _inc(_ensure(si_bucket, industry), is_bull, is_bear)

        def _sorted_rows(buckets: dict[str, dict]) -> list[dict]:
            rows = list(buckets.values())
            rows.sort(key=lambda r: (-r["total"], r["name"]))
            return rows

        grouped_industry: list[dict] = []
        for sector, industries in sector_industry_map.items():
            rows = _sorted_rows(industries)
            grouped_industry.append({
                "sector": sector,
                "total": sum(r["total"] for r in rows),
                "bullish": sum(r["bullish"] for r in rows),
                "bearish": sum(r["bearish"] for r in rows),
                "industries": rows,
            })
        grouped_industry.sort(key=lambda r: (-r["total"], r["sector"]))

        return {
            "total": total,
            "bullish": bullish,
            "bearish": bearish,
            "by_sector": _sorted_rows(sector_buckets),
            "by_industry": _sorted_rows(industry_buckets),
            "by_sector_industry": grouped_industry,
        }
