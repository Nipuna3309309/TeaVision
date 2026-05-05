"""
src/data_loader.py
"""

import os
import re
import warnings
import logging
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List

import numpy as np
import pandas as pd
import joblib

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


def month_week_to_date(year: int, month: int, week_in_month: int) -> pd.Timestamp:
    if week_in_month not in [1, 2, 3, 4, 5]:
        raise ValueError("week_in_month must be 1..5")

    start_day = 1 + (week_in_month - 1) * 7
    month_start = pd.Timestamp(year=year, month=month, day=1)
    month_end = month_start + pd.offsets.MonthEnd(1)
    last_day = int(month_end.day)
    day = min(start_day, last_day)
    return pd.Timestamp(year=year, month=month, day=day)


def weeks_between(start_date: pd.Timestamp, target_date: pd.Timestamp) -> int:
    diff_days = (target_date - start_date).days
    if diff_days <= 0:
        return 0
    return int(np.ceil(diff_days / 7.0))


def date_to_sale_no(dt: pd.Timestamp) -> int:
    jan1 = pd.Timestamp(year=dt.year, month=1, day=1)
    return int(((dt - jan1).days // 7) + 1)


@dataclass
class ArimaForecastResult:
    predicted_price: float
    steps_ahead: int
    target_date: pd.Timestamp
    target_sale_no: int
    last_known_date: pd.Timestamp


class DataLoader:
    def __init__(self, data_dir="data", model_dir="models"):
        self.data_dir = data_dir
        self.model_dir = model_dir

        self.historical_data: Optional[pd.DataFrame] = None

        self.price_map: Dict[Tuple[int, int, str, str], float] = {}
        self.trend_map: Dict[Tuple[int, int, str, str], float] = {}
        self.momentum_map: Dict[Tuple[int, int, str, str], float] = {}
        self.ma_map: Dict[Tuple[int, int, str, str], float] = {}

        self.arima_models: Dict[Tuple[str, str], object] = {}
        self.last_date_map: Dict[Tuple[str, str], pd.Timestamp] = {}

        # For hybrid / real-transition factory training
        self.factory_transition_data: Optional[pd.DataFrame] = None

    def find_header_row(self, path: str) -> int:
        try:
            df_preview = pd.read_excel(path, header=None, nrows=15)
            best_score = 0
            best_idx = 0
            keywords = [
                "PRICE", "AVG", "SALE", "WK", "WEEK",
                "LOT", "QTY", "GRADE", "CATEGORY",
                "YEAR", "MONTH"
            ]
            for i, row in df_preview.iterrows():
                row_str = " ".join([str(x).upper() for x in row.values])
                score = sum(1 for k in keywords if k in row_str)
                if score > best_score:
                    best_score = score
                    best_idx = i
            return best_idx if best_score >= 2 else 0
        except Exception:
            return 0

    def _elev_folder_key(self, elev_ui: str) -> str:
        e = str(elev_ui).strip().lower()
        if e.startswith("low"):
            return "low"
        if e.startswith("mid") or e.startswith("med"):
            return "medium"
        if e.startswith("high"):
            return "high"
        return "low"

    def _elev_file_key(self, elev_ui: str) -> str:
        e = str(elev_ui).strip().lower()
        if e.startswith("low"):
            return "Low"
        if e.startswith("mid") or e.startswith("med"):
            return "Medium"
        if e.startswith("high"):
            return "High"
        return "Low"

    def _elev_data_key(self, elev_ui: str) -> str:
        e = str(elev_ui).strip().upper()
        if e.startswith("MID") or e.startswith("MED"):
            return "MID"
        if e.startswith("HIGH"):
            return "HIGH"
        return "LOW"

    def load_data(self, progress_callback=None):
        files = [
            ("DATA TABLE-2023- SALE 50.xlsx", 2023),
            ("DATA TABLE-2024- SALE  51.xlsx", 2024),
            ("DATA TABLE-2025- SALE  46- up to November.xlsx", 2025),
        ]

        dfs = []
        for i, (filename, year) in enumerate(files):
            if progress_callback:
                progress_callback(f"Reading {filename}...", i / len(files))

            path = os.path.join(self.data_dir, filename)
            if not os.path.exists(path):
                logging.warning(f"File not found: {path}")
                continue

            header = self.find_header_row(path)
            df = pd.read_excel(path, header=header)
            df.columns = [str(c).strip().upper() for c in df.columns]
            df = df.loc[:, ~df.columns.duplicated()]

            if "YEAR" not in df.columns:
                df["YEAR"] = year

            rename_map = {
                "AVERAGE": "PRICE",
                "AVG": "PRICE",
                "AVG PRICE": "PRICE",
                "PRICE.1": "PRICE",
                "SOLD QTY": "QTY",
                "QUANTITY": "QTY",
                "QTY.1": "QTY",
                "SALE": "SALE NO",
                "WK": "SALE NO",
                "WEEK": "SALE NO",
                "SALE NO.": "SALE NO",
                "TEA GRADE": "GRADE",
                "TEA_GRADE": "GRADE",
                "GRADE.1": "GRADE",
                "ELEVATION": "ELEVATION",
            }
            df.rename(columns=rename_map, inplace=True)
            df = df.loc[:, ~df.columns.duplicated()]

            if "ELEVATION" not in df.columns:
                df["ELEVATION"] = "LOW"

            keep = [c for c in ["YEAR", "MONTH", "SALE NO", "GRADE", "PRICE", "QTY", "ELEVATION"] if c in df.columns]
            if "PRICE" in keep and "SALE NO" in keep and "GRADE" in keep:
                dfs.append(df[keep])

        if not dfs:
            raise RuntimeError("No Excel data loaded. Check /data folder and filenames.")

        self.historical_data = pd.concat(dfs, ignore_index=True)

        for col in ["PRICE", "QTY", "SALE NO", "YEAR"]:
            if col in self.historical_data.columns:
                self.historical_data[col] = pd.to_numeric(self.historical_data[col], errors="coerce")

        for col in ["MONTH", "GRADE", "ELEVATION"]:
            if col in self.historical_data.columns:
                self.historical_data[col] = self.historical_data[col].astype(str).str.upper().str.strip()

        self.historical_data.dropna(subset=["PRICE"], inplace=True)

        self.historical_data["ELEVATION"] = self.historical_data["ELEVATION"].replace(
            {
                "MEDIUM": "MID",
                "MID-COUNTRY": "MID",
                "MID COUNTRY": "MID",
                "LOW GROWN": "LOW",
                "MID GROWN": "MID",
                "HIGH GROWN": "HIGH",
            }
        )

        elev_map = {"LOW": 0, "MID": 1, "HIGH": 2}
        self.historical_data["ELEV_CODE"] = (
            self.historical_data["ELEVATION"].map(elev_map).fillna(0).astype(int)
        )

        self.historical_data.sort_values(
            ["ELEVATION", "GRADE", "YEAR", "SALE NO"],
            inplace=True
        )

        self.historical_data["DATE"] = self.historical_data.apply(
            lambda r: pd.Timestamp(year=int(r["YEAR"]), month=1, day=1)
            + pd.Timedelta(days=(int(r["SALE NO"]) - 1) * 7),
            axis=1,
        )

        self.historical_data["SMA_4"] = (
            self.historical_data.groupby(["ELEVATION", "GRADE"])["PRICE"]
            .transform(lambda x: x.rolling(window=4, min_periods=1).mean())
        )
        self.historical_data["PREV_PRICE"] = (
            self.historical_data.groupby(["ELEVATION", "GRADE"])["PRICE"].shift(1)
        )
        self.historical_data["MOMENTUM"] = (
            self.historical_data["PRICE"] - self.historical_data["PREV_PRICE"]
        ).fillna(0.0)
        self.historical_data["MATH_PRED"] = (
            self.historical_data["PRICE"] + (self.historical_data["MOMENTUM"] * 0.5)
        )

        grp = self.historical_data.groupby(["ELEVATION", "GRADE"])["DATE"].max()
        self.last_date_map = {
            (str(e).upper(), str(g).upper()): pd.Timestamp(d)
            for (e, g), d in grp.items()
        }

        grouped = (
            self.historical_data.groupby(["YEAR", "SALE NO", "GRADE", "ELEVATION"])
            .mean(numeric_only=True)
            .reset_index()
        )
        for _, row in grouped.iterrows():
            key = (
                int(row["YEAR"]),
                int(row["SALE NO"]),
                str(row["GRADE"]).upper(),
                str(row["ELEVATION"]).upper(),
            )
            self.price_map[key] = float(row["PRICE"])
            self.trend_map[key] = float(row["MATH_PRED"])
            self.momentum_map[key] = float(row["MOMENTUM"])
            self.ma_map[key] = float(row["SMA_4"])

        logging.info(f"Database Ready: {len(self.historical_data):,} rows")

        # Build real consecutive transitions for hybrid factory training
        self.build_factory_transition_data()

    def build_factory_transition_data(self):
        """
        Build real consecutive transition rows for factory training.
        Adds return-based fields for hybrid factory sampling.
        """
        if self.historical_data is None or len(self.historical_data) == 0:
            self.factory_transition_data = pd.DataFrame()
            return self.factory_transition_data

        df = self.historical_data.copy()
        df = df.sort_values(["ELEVATION", "GRADE", "DATE"]).reset_index(drop=True)

        rows = []

        for (elev, grade), g in df.groupby(["ELEVATION", "GRADE"], sort=False):
            g = g.sort_values("DATE").reset_index(drop=True)
            if len(g) < 2:
                continue

            for i in range(len(g) - 1):
                cur = g.iloc[i]
                nxt = g.iloc[i + 1]

                cur_date = pd.Timestamp(cur["DATE"])
                nxt_date = pd.Timestamp(nxt["DATE"])
                gap_days = int((nxt_date - cur_date).days)

                if gap_days < 1 or gap_days > 14:
                    continue

                current_price = float(cur["PRICE"])
                next_price = float(nxt["PRICE"])

                if not np.isfinite(current_price) or not np.isfinite(next_price):
                    continue
                if current_price <= 0 or next_price <= 0:
                    continue

                cur_qty = float(cur["QTY"]) if "QTY" in cur and pd.notna(cur["QTY"]) else np.nan
                nxt_qty = float(nxt["QTY"]) if "QTY" in nxt and pd.notna(nxt["QTY"]) else np.nan

                qty_candidates = [x for x in [cur_qty, nxt_qty] if np.isfinite(x) and x > 0]
                if len(qty_candidates) == 0:
                    avg_qty = 10000.0
                else:
                    avg_qty = float(np.clip(np.mean(qty_candidates), 1000.0, 50000.0))

                if "MATH_PRED" in cur and pd.notna(cur["MATH_PRED"]) and float(cur["MATH_PRED"]) > 0:
                    forecast_proxy = float(cur["MATH_PRED"])
                else:
                    forecast_proxy = current_price

                forecast_proxy = float(
                    np.clip(forecast_proxy, current_price * 0.85, current_price * 1.15)
                )

                elev_code = int(cur["ELEV_CODE"]) if "ELEV_CODE" in cur and pd.notna(cur["ELEV_CODE"]) else 0

                return_pct = (next_price - current_price) / max(current_price, 1.0)
                abs_return = abs(return_pct)

                rows.append(
                    {
                        "elevation": str(elev).upper(),
                        "grade": str(grade).upper(),
                        "date_current": str(cur_date.date()),
                        "date_next": str(nxt_date.date()),
                        "current_price": current_price,
                        "next_price": next_price,
                        "current_qty": cur_qty if np.isfinite(cur_qty) else np.nan,
                        "next_qty": nxt_qty if np.isfinite(nxt_qty) else np.nan,
                        "avg_qty": avg_qty,
                        "forecast_proxy": forecast_proxy,
                        "elev_code": elev_code,
                        "return_pct": float(return_pct),
                        "abs_return": float(abs_return),
                    }
                )

        self.factory_transition_data = pd.DataFrame(rows)

        if len(self.factory_transition_data) > 0:
            counts = self.factory_transition_data["elevation"].value_counts(dropna=False).to_dict()
            logging.info(
                f"Factory transition data ready: {len(self.factory_transition_data):,} rows | {counts}"
            )
        else:
            logging.warning("Factory transition data is empty.")

        return self.factory_transition_data

    def get_row_data(self, index: int):
        if self.historical_data is None or len(self.historical_data) == 0:
            return 1000.0, 1000.0, 0.0, 1000.0, 0

        index = int(np.clip(index, 0, len(self.historical_data) - 1))
        row = self.historical_data.iloc[index]
        return (
            float(row["PRICE"]),
            float(row["MATH_PRED"]),
            float(row["MOMENTUM"]),
            float(row["SMA_4"]),
            int(row["ELEV_CODE"]),
        )

    def get_available_arima_grades(self, elevation_ui: str) -> List[str]:
        folder_key = self._elev_folder_key(elevation_ui)
        folder = os.path.join(self.model_dir, f"saved_models_arima_{folder_key}")

        if not os.path.isdir(folder):
            logging.warning(f"[ARIMA] Folder not found: {folder}")
            return []

        grades = set()

        for fn in os.listdir(folder):
            if not fn.lower().endswith(".pkl"):
                continue

            grade = self._grade_from_pkl_filename(fn)
            if grade:
                grades.add(grade)

        out = sorted(grades)
        logging.info(f"[ARIMA] {elevation_ui} grades found: {len(out)} (folder={folder})")
        return out

    def _grade_from_pkl_filename(self, fn: str) -> Optional[str]:
        base = os.path.basename(fn)

        if not base.upper().startswith("ARIMA_"):
            return None

        name = base[:-4]
        name = name[6:]

        parts = name.split("_", 1)
        if len(parts) < 2:
            return None

        grade_part = parts[1]
        grade_part = re.sub(r"\s*\(\d+\)\s*$", "", grade_part)
        grade_part = grade_part.replace("_", " ")
        grade_part = re.sub(r"\s+", " ", grade_part).strip().upper()

        return grade_part if grade_part else None

    def _model_path_for(self, elevation_ui: str, grade: str) -> Optional[str]:
        folder_key = self._elev_folder_key(elevation_ui)
        folder = os.path.join(self.model_dir, f"saved_models_arima_{folder_key}")
        if not os.path.isdir(folder):
            return None

        target_grade = re.sub(r"\s+", " ", str(grade)).strip().upper()

        for fn in os.listdir(folder):
            if not fn.lower().endswith(".pkl"):
                continue
            g = self._grade_from_pkl_filename(fn)
            if g == target_grade:
                return os.path.join(folder, fn)

        return None

    def load_arima_model(self, elevation_ui: str, grade: str):
        elev_key = self._elev_file_key(elevation_ui).upper()
        grade_key = re.sub(r"\s+", " ", str(grade)).strip().upper()
        key = (elev_key, grade_key)

        if key in self.arima_models:
            return self.arima_models[key]

        path = self._model_path_for(elevation_ui, grade_key)
        if not path:
            raise FileNotFoundError(
                f"No ARIMA model for elevation={elevation_ui}, grade={grade_key}"
            )

        model = joblib.load(path)
        self.arima_models[key] = model
        return model

    def forecast_price_month_week(
        self,
        elevation_ui: str,
        grade: str,
        target_year: int,
        target_month: int,
        target_week_in_month: int,
        return_last_n_weeks: int = 8,
    ) -> Tuple[ArimaForecastResult, List[Tuple[pd.Timestamp, float]]]:

        if self.historical_data is None:
            raise RuntimeError("Call load_data() first.")

        grade_key = re.sub(r"\s+", " ", str(grade)).strip().upper()
        elev_data = self._elev_data_key(elevation_ui).upper()

        last_date = self.last_date_map.get((elev_data, grade_key))
        if last_date is None:
            last_date = pd.Timestamp(self.historical_data["DATE"].max())

        target_date = month_week_to_date(target_year, target_month, target_week_in_month)
        target_sale_no = date_to_sale_no(target_date)

        model = self.load_arima_model(elevation_ui, grade_key)
        steps = weeks_between(last_date, target_date)

        if steps == 0:
            try:
                fv = getattr(model, "fittedvalues", None)
                if fv is not None and len(fv) > 0:
                    pred_val = float(fv.iloc[-1])
                else:
                    pred_val = float(np.asarray(model.forecast(steps=1), dtype=float)[0])
            except Exception:
                pred_val = float(np.asarray(model.forecast(steps=1), dtype=float)[0])

            return (
                ArimaForecastResult(
                    predicted_price=pred_val,
                    steps_ahead=0,
                    target_date=target_date,
                    target_sale_no=target_sale_no,
                    last_known_date=last_date,
                ),
                [(target_date, pred_val)],
            )

        fc_vals = np.asarray(model.forecast(steps=steps), dtype=float)
        dates = pd.date_range(
            start=last_date + pd.Timedelta(days=7),
            periods=steps,
            freq="7D",
        )

        n = max(1, min(int(return_last_n_weeks), steps))
        tail_vals = fc_vals[-n:]
        tail_dates = dates[-n:]

        series = [(pd.Timestamp(d), float(p)) for d, p in zip(tail_dates, tail_vals)]
        pred_val = float(fc_vals[-1])

        return (
            ArimaForecastResult(
                predicted_price=pred_val,
                steps_ahead=steps,
                target_date=target_date,
                target_sale_no=target_sale_no,
                last_known_date=last_date,
            ),
            series,
        )

    def get_actual_price_by_sale(
        self,
        year: int,
        sale_no: int,
        grade: str,
        elevation_ui: str,
    ) -> Optional[float]:
        if self.historical_data is None:
            return None

        elev = self._elev_data_key(elevation_ui).upper()
        grade = re.sub(r"\s+", " ", str(grade)).strip().upper()

        sub = self.historical_data[
            (self.historical_data["YEAR"] == year)
            & (self.historical_data["SALE NO"] == sale_no)
            & (self.historical_data["GRADE"] == grade)
            & (self.historical_data["ELEVATION"] == elev)
        ]["PRICE"]

        if sub.empty:
            return None
        return float(sub.mean())