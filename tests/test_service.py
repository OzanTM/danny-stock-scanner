from __future__ import annotations

import pytest

from scanner.models import SIGNAL_BULLISH, SIGNAL_BEARISH, SIGNAL_NONE, VALID_SORT_FIELDS, ScanFilters
from scanner.service import StockScannerService


def _make_results(n: int = 10) -> list[dict]:
    items = []
    for i in range(n):
        is_bull = i % 3 == 0
        is_bear = i % 3 == 1
        items.append({
            "ticker": f"TICK{i:02d}.IS",
            "date": f"2024-06-{10 + i:02d}",
            "close_price": 100.0 + i * 5,
            "signal": SIGNAL_BULLISH if is_bull else (SIGNAL_BEARISH if is_bear else SIGNAL_NONE),
            "name": f"Company {chr(65 + i)}",
            "sector": "Finans" if i < 5 else "Teknoloji",
            "industry": "Bankacilik" if i < 3 else ("Yazilim" if i >= 7 else "Sigorta"),
            "market_cap": float(1_000_000 * (i + 1)),
            "trend_level": "good" if i % 2 == 0 else "bad",
            "momentum_level": "good" if i % 3 == 0 else "neutral",
            "timing_level": "good",
            "breakout_level": "neutral",
            "risk_level": "good" if i < 5 else "bad",
            "rsi_14": 30.0 + i * 5,
            "atr_pct": 1.0 + i * 0.5,
            "bb_width_pct": 3.0 + i * 0.3,
            "macd_hist": -0.5 + i * 0.1,
            "prev_signal_1": SIGNAL_NONE,
            "prev_signal_2": SIGNAL_NONE,
            "prev_signal_3": SIGNAL_NONE,
            "prev_signal_4": SIGNAL_NONE,
        })
    return items


class TestApplyFilters:
    def test_no_filters_returns_all(self):
        results = _make_results(10)
        filtered = StockScannerService.apply_filters(results, ScanFilters())
        assert len(filtered) == 10

    def test_filter_by_sector(self):
        results = _make_results(10)
        filtered = StockScannerService.apply_filters(results, ScanFilters(sector="Finans"))
        assert all(r["sector"] == "Finans" for r in filtered)
        assert len(filtered) == 5

    def test_filter_by_signal(self):
        results = _make_results(10)
        filtered = StockScannerService.apply_filters(results, ScanFilters(signal=SIGNAL_BULLISH))
        assert all(r["signal"] == SIGNAL_BULLISH for r in filtered)

    def test_filter_by_market_cap_range(self):
        results = _make_results(10)
        filtered = StockScannerService.apply_filters(
            results, ScanFilters(market_cap_min=3_000_000, market_cap_max=7_000_000)
        )
        for r in filtered:
            assert 3_000_000 <= float(r["market_cap"]) <= 7_000_000

    def test_filter_by_rsi_range(self):
        results = _make_results(10)
        filtered = StockScannerService.apply_filters(
            results, ScanFilters(rsi_min=40, rsi_max=60)
        )
        for r in filtered:
            assert 40 <= float(r["rsi_14"]) <= 60

    def test_filter_by_trend_level(self):
        results = _make_results(10)
        filtered = StockScannerService.apply_filters(results, ScanFilters(trend_level="good"))
        assert all(r["trend_level"] == "good" for r in filtered)

    def test_combined_filters(self):
        results = _make_results(10)
        filtered = StockScannerService.apply_filters(
            results, ScanFilters(sector="Finans", risk_level="good")
        )
        for r in filtered:
            assert r["sector"] == "Finans"
            assert r["risk_level"] == "good"

    def test_sort_by_close_price_asc(self):
        results = _make_results(10)
        filtered = StockScannerService.apply_filters(
            results, ScanFilters(sort_by="close_price", sort_dir="asc")
        )
        prices = [r["close_price"] for r in filtered]
        assert prices == sorted(prices)

    def test_sort_by_close_price_desc(self):
        results = _make_results(10)
        filtered = StockScannerService.apply_filters(
            results, ScanFilters(sort_by="close_price", sort_dir="desc")
        )
        prices = [r["close_price"] for r in filtered]
        assert prices == sorted(prices, reverse=True)

    def test_sort_by_name(self):
        results = _make_results(10)
        filtered = StockScannerService.apply_filters(
            results, ScanFilters(sort_by="name", sort_dir="asc")
        )
        names = [r["name"].upper() for r in filtered]
        assert names == sorted(names)

    def test_invalid_sort_field_falls_back_to_ticker(self):
        results = _make_results(10)
        filtered = StockScannerService.apply_filters(
            results, ScanFilters(sort_by="INVALID_FIELD", sort_dir="asc")
        )
        tickers = [r["ticker"].upper() for r in filtered]
        assert tickers == sorted(tickers)

    def test_empty_results(self):
        filtered = StockScannerService.apply_filters([], ScanFilters())
        assert filtered == []


class TestBuildFilterOptions:
    def test_excludes_unknown(self):
        results = _make_results(10)
        results.append({**results[0], "sector": "Bilinmiyor", "industry": "Bilinmiyor"})
        sectors, industries = StockScannerService.build_filter_options(results)
        assert "Bilinmiyor" not in sectors
        assert "Bilinmiyor" not in industries

    def test_sorted(self):
        results = _make_results(10)
        sectors, industries = StockScannerService.build_filter_options(results)
        assert sectors == sorted(sectors)
        assert industries == sorted(industries)


class TestBuildSignalSummary:
    def test_totals(self):
        results = _make_results(10)
        summary = StockScannerService.build_signal_summary(results)
        assert summary["total"] == 10
        assert summary["bullish"] + summary["bearish"] <= summary["total"]

    def test_by_sector_structure(self):
        results = _make_results(10)
        summary = StockScannerService.build_signal_summary(results)
        for row in summary["by_sector"]:
            assert "name" in row
            assert "total" in row
            assert "bullish" in row
            assert "bearish" in row
            assert row["bullish"] + row["bearish"] <= row["total"]

    def test_sector_totals_sum(self):
        results = _make_results(10)
        summary = StockScannerService.build_signal_summary(results)
        sector_total = sum(r["total"] for r in summary["by_sector"])
        assert sector_total == summary["total"]

    def test_empty_results(self):
        summary = StockScannerService.build_signal_summary([])
        assert summary["total"] == 0
        assert summary["bullish"] == 0
        assert summary["bearish"] == 0


class TestValidSortFields:
    def test_all_expected_fields(self):
        expected = {"ticker", "name", "sector", "industry", "close_price", "market_cap",
                    "date", "signal", "rsi_14", "atr_pct", "bb_width_pct", "macd_hist"}
        assert VALID_SORT_FIELDS == expected
