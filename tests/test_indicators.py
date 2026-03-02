from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scanner.indicators import add_standard_indicators, compute_kdj, rma
from scanner.models import SIGNAL_BULLISH, SIGNAL_BEARISH, SIGNAL_NONE


def _make_ohlc(n: int = 50, base: float = 100.0, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-01", periods=n)
    close = base + np.cumsum(rng.normal(0, 1, n))
    high = close + rng.uniform(0.5, 2.0, n)
    low = close - rng.uniform(0.5, 2.0, n)
    opn = close + rng.normal(0, 0.5, n)
    return pd.DataFrame(
        {"Open": opn, "High": high, "Low": low, "Close": close},
        index=dates,
    )


class TestRma:
    def test_positive_length(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = rma(s, 3)
        assert len(result) == 5
        assert not result.isna().all()

    def test_zero_length_raises(self):
        with pytest.raises(ValueError, match="length must be positive"):
            rma(pd.Series([1.0]), 0)


class TestComputeKdj:
    def test_basic_output_columns(self):
        df = _make_ohlc(50)
        result = compute_kdj(df, length=9, signal=3, threshold=50.0)
        for col in ["k", "pK", "pD", "j", "cross_over", "cross_under", "signal"]:
            assert col in result.columns, f"Missing column: {col}"

    def test_signal_values(self):
        df = _make_ohlc(50)
        result = compute_kdj(df, length=9, signal=3, threshold=50.0)
        unique_signals = set(result["signal"].dropna().unique())
        assert unique_signals.issubset({SIGNAL_BULLISH, SIGNAL_BEARISH, SIGNAL_NONE})

    def test_j_formula(self):
        df = _make_ohlc(50)
        result = compute_kdj(df, length=9, signal=3, threshold=50.0)
        expected_j = 3 * result["pK"] - 2 * result["pD"]
        pd.testing.assert_series_equal(result["j"], expected_j, check_names=False)

    def test_cross_over_logic(self):
        df = _make_ohlc(50)
        result = compute_kdj(df, length=9, signal=3, threshold=50.0)
        for i in range(1, len(result)):
            if result["cross_over"].iloc[i]:
                assert result["j"].iloc[i] > 50.0
                assert result["j"].iloc[i - 1] <= 50.0

    def test_invalid_params(self):
        df = _make_ohlc(50)
        with pytest.raises(ValueError):
            compute_kdj(df, length=0, signal=3)
        with pytest.raises(ValueError):
            compute_kdj(df, length=9, signal=0)

    def test_short_data(self):
        df = _make_ohlc(5)
        result = compute_kdj(df, length=9, signal=3, threshold=50.0)
        assert len(result) == 5


class TestAddStandardIndicators:
    def test_output_columns(self):
        df = _make_ohlc(60)
        result = add_standard_indicators(df)
        expected = [
            "ema_9", "ema_20", "ema_50",
            "macd_line", "macd_signal", "macd_hist",
            "rsi_14", "bb_mid", "bb_upper", "bb_lower", "bb_width_pct",
            "atr_14", "atr_pct",
        ]
        for col in expected:
            assert col in result.columns, f"Missing column: {col}"

    def test_rsi_range(self):
        df = _make_ohlc(60)
        result = add_standard_indicators(df)
        rsi = result["rsi_14"].dropna()
        assert (rsi >= 0).all() and (rsi <= 100).all()

    def test_bollinger_upper_gte_lower(self):
        df = _make_ohlc(60)
        result = add_standard_indicators(df)
        valid = result.dropna(subset=["bb_upper", "bb_lower"])
        assert (valid["bb_upper"] >= valid["bb_lower"]).all()

    def test_atr_non_negative(self):
        df = _make_ohlc(60)
        result = add_standard_indicators(df)
        atr = result["atr_14"].dropna()
        assert (atr >= 0).all()
