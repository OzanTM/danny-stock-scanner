from __future__ import annotations

import numpy as np
import pandas as pd

from .models import SIGNAL_BULLISH, SIGNAL_BEARISH, SIGNAL_NONE


def rma(series: pd.Series, length: int) -> pd.Series:
    if length <= 0:
        raise ValueError("length must be positive")
    return series.ewm(alpha=1 / length, adjust=False).mean()


def compute_kdj(
    df: pd.DataFrame,
    *,
    length: int = 9,
    signal: int = 3,
    threshold: float = 50.0,
) -> pd.DataFrame:
    if length <= 0 or signal <= 0:
        raise ValueError("length and signal must be positive")

    result = df.copy()
    highest = result["High"].rolling(window=length, min_periods=length).max()
    lowest = result["Low"].rolling(window=length, min_periods=length).min()
    denominator = highest - lowest

    k = np.where(
        denominator.eq(0),
        50.0,
        100.0 * ((result["Close"] - lowest) / denominator),
    )

    result["k"] = pd.Series(k, index=result.index, dtype="float64")
    result["pK"] = rma(result["k"], signal)
    result["pD"] = rma(result["pK"], signal)
    result["j"] = 3 * result["pK"] - 2 * result["pD"]

    prev_j = result["j"].shift(1)
    result["cross_over"] = (result["j"] > threshold) & (prev_j <= threshold)
    result["cross_under"] = (result["j"] < threshold) & (prev_j >= threshold)

    result["signal"] = np.where(
        result["cross_over"],
        SIGNAL_BULLISH,
        np.where(result["cross_under"], SIGNAL_BEARISH, SIGNAL_NONE),
    )
    return result


def add_standard_indicators(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    close = result["Close"]
    high = result["High"]
    low = result["Low"]

    result["ema_9"] = close.ewm(span=9, adjust=False).mean()
    result["ema_20"] = close.ewm(span=20, adjust=False).mean()
    result["ema_50"] = close.ewm(span=50, adjust=False).mean()

    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    result["macd_line"] = ema_12 - ema_26
    result["macd_signal"] = result["macd_line"].ewm(span=9, adjust=False).mean()
    result["macd_hist"] = result["macd_line"] - result["macd_signal"]

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    result["rsi_14"] = 100 - (100 / (1 + rs))
    result["rsi_14"] = result["rsi_14"].fillna(50.0)

    result["bb_mid"] = close.rolling(window=20, min_periods=20).mean()
    bb_std = close.rolling(window=20, min_periods=20).std(ddof=0)
    result["bb_upper"] = result["bb_mid"] + 2 * bb_std
    result["bb_lower"] = result["bb_mid"] - 2 * bb_std
    result["bb_width_pct"] = (
        (result["bb_upper"] - result["bb_lower"]) / result["bb_mid"].replace(0, np.nan) * 100.0
    )

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    result["atr_14"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    result["atr_pct"] = result["atr_14"] / close.replace(0, np.nan) * 100.0
    return result
