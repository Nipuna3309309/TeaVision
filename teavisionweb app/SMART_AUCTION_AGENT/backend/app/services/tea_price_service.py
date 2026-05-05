import os
import re
from typing import Dict, Tuple, List

import numpy as np
import pandas as pd

from src.data_loader import date_to_sale_no


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
METRICS_DIR = os.path.join(BASE_DIR, "data", "metrics")

METRICS_FILES: Dict[str, str] = {
    "Low": os.path.join(METRICS_DIR, "metrics_arima_low.xls"),
    "Mid": os.path.join(METRICS_DIR, "metrics_arima_mid.xls"),
    "High": os.path.join(METRICS_DIR, "metrics_arima_high.xls"),
}

MIN_BAND_PCT = 0.5
MAX_BAND_PCT = 25.0

MAPE_BY_KEY: Dict[Tuple[str, str], float] = {}


def norm_grade(g: str) -> str:
    return re.sub(r"\s+", " ", str(g).strip()).upper()


def normalize_elevation(elevation: str) -> str:
    e = str(elevation).strip().lower()
    if e.startswith("low"):
        return "Low"
    if e.startswith("mid") or e.startswith("med"):
        return "Mid"
    if e.startswith("high"):
        return "High"
    return "Low"


def load_metrics_mape() -> None:
    MAPE_BY_KEY.clear()

    for elev, path in METRICS_FILES.items():
        if not os.path.exists(path):
            print(f"[WARN] Tea price metrics file missing: {path}")
            continue

        try:
            df = pd.read_csv(path)
        except Exception:
            df = pd.read_excel(path)

        cols = {str(c).strip().lower(): c for c in df.columns}
        grade_col = cols.get("grade")

        mape_col = None
        for c in df.columns:
            if "mape" in str(c).lower():
                mape_col = c
                break

        if grade_col is None or mape_col is None:
            print(f"[WARN] Invalid metrics file columns in {path}: {list(df.columns)}")
            continue

        df = df.dropna(subset=[grade_col])

        for _, row in df.iterrows():
            grade = norm_grade(row[grade_col])
            try:
                mape = float(row[mape_col])
            except Exception:
                continue

            if not np.isfinite(mape):
                continue

            mape = float(np.clip(mape, MIN_BAND_PCT, MAX_BAND_PCT))
            MAPE_BY_KEY[(elev, grade)] = mape

    print(f"[TeaPrice] Loaded {len(MAPE_BY_KEY)} grade-band pairs")


def get_band_pct(elevation: str, grade: str) -> float:
    elev = normalize_elevation(elevation)
    g = norm_grade(grade)
    band = MAPE_BY_KEY.get((elev, g), np.nan)
    if not np.isfinite(band):
        return 7.5
    return float(band)


def band_from_price(price: float, band_pct: float):
    delta = float(price) * (float(band_pct) / 100.0)
    return float(price - delta), float(price + delta)


def build_series_with_bands(series: List[tuple], band_pct: float):
    out = []
    for d, p in series:
        d = pd.Timestamp(d)
        p = float(p)
        lo, hi = band_from_price(p, band_pct)
        out.append({
            "year": int(d.year),
            "sale_no": int(date_to_sale_no(d)),
            "date": str(d.date()),
            "predicted_price": p,
            "lower_band": lo,
            "upper_band": hi,
        })
    return out


load_metrics_mape()