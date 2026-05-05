"""
Yield Prediction Module - SARIMAX Models (Objective 2 - IT22222268)
Field-wise monthly tea yield forecasting using Seasonal ARIMA with Exogenous Variables.
Pre-trained models for 44 fields across 3 divisions (Attabage, Lower, Upper).
"""

import json
import pickle
import csv
import re
import numpy as np
from pathlib import Path

# Relative path — models are inside the backend folder
SARIMAX_DIR = Path(__file__).parent / "sarimax_models"

# Loaded models & metadata
sarimax_models = {}
sarimax_meta = {}
field_list = {}

# Notebook constants (matching Harsha's training pipeline)
ZERO_EPS = 5.0


def load_sarimax_models():
    """Load all SARIMAX models and metadata on startup"""
    global sarimax_models, sarimax_meta, field_list

    index_path = SARIMAX_DIR / "models_index.csv"
    if not index_path.exists():
        print(f"[Yield] models_index.csv not found at {index_path}")
        return

    with open(index_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            field_key = row["FieldKey"]
            pkl_filename = Path(row["pkl"]).name
            meta_filename = Path(row["meta"]).name
            
            pkl_path = SARIMAX_DIR / pkl_filename
            meta_path = SARIMAX_DIR / meta_filename

            if pkl_path.exists() and meta_path.exists():
                try:
                    with open(pkl_path, 'rb') as pf:
                        sarimax_models[field_key] = pickle.load(pf)
                    with open(meta_path, 'r') as mf:
                        sarimax_meta[field_key] = json.load(mf)
                except Exception as e:
                    print(f"[Yield] Failed to load {field_key}: {e}")
            else:
                print(f"[Yield] Missing files for {field_key}")

    # Build organized field list by division
    # Rename Attabage -> Atb for display
    DIVISION_RENAME = {"Attabage": "Atb"}
    # Desired order: Lower first
    DIVISION_ORDER = ["Lower", "Atb", "Upper"]

    raw_divisions = {}
    for key, meta in sarimax_meta.items():
        parts = key.split("_", 1)
        division = parts[0]
        display_div = DIVISION_RENAME.get(division, division)
        field_id = parts[1] if len(parts) > 1 else "Unknown"
        
        m = re.search(r'\d+', field_id)
        field_id_num = int(m.group()) if m else 0

        if display_div not in raw_divisions:
            raw_divisions[display_div] = []
        raw_divisions[display_div].append({
            "field_key": key,
            "field_id": field_id,
            "field_id_num": field_id_num,
            "n_obs": meta.get("n_obs", 0),
            "data_start": meta.get("data_start", ""),
            "data_end": meta.get("data_end", ""),
            "cap_value": round(meta.get("CAP_VALUE", 0), 1),
            "order": meta.get("order", []),
            "seasonal_order": meta.get("seasonal_order", []),
        })

    for div in raw_divisions:
        raw_divisions[div].sort(key=lambda x: (x.get("field_id_num", 0), x.get("field_id", "")))

    # Order divisions: Lower first, then Atb, then Upper
    divisions = {}
    for d in DIVISION_ORDER:
        if d in raw_divisions:
            divisions[d] = raw_divisions[d]
    for d in raw_divisions:
        if d not in divisions:
            divisions[d] = raw_divisions[d]

    field_list = divisions
    print(f"[Yield] Loaded {len(sarimax_models)} SARIMAX models across {len(divisions)} divisions")


def get_fields():
    """Return organized field listing by division"""
    return {
        "total_models": len(sarimax_models),
        "divisions": {
            div: {
                "count": len(fields),
                "fields": fields
            }
            for div, fields in field_list.items()
        }
    }


def get_field_info(field_key: str):
    """Return detailed info about a specific field model"""
    if field_key not in sarimax_meta:
        return None

    meta = sarimax_meta[field_key]
    return {
        "field_key": field_key,
        "order": meta.get("order", []),
        "seasonal_order": meta.get("seasonal_order", []),
        "exog_columns": meta.get("EXOG_COLS", []),
        "uses_exog": meta.get("USE_EXOG", False),
        "uses_log": meta.get("USE_LOG1P", False),
        "cap_value": meta.get("CAP_VALUE", 0),
        "data_start": meta.get("data_start", ""),
        "data_end": meta.get("data_end", ""),
        "n_observations": meta.get("n_obs", 0),
    }


def _build_exog_row(rainfall, wet_days, plucking_rounds, months_after_pruning, model_result, exog_cols):
    """
    Build a single exogenous row matching the model's expected columns.
    The model uses 3-month lags for each variable + is_zero_yield + months_since_zero.

    User inputs: rainfall, wet_days, plucking_rounds, months_after_pruning
    Historical (internal): fertilizer lags are taken from training data averages,
    because fertilizer effect is represented through historical lagged variables
    from the previous 3 months — not as an immediate next-month driver.
    """
    # Get historical fertilizer averages from training data
    fert_pct_avg = 0.0
    fert_ratio_avg = 0.0
    try:
        last_exog = model_result.model.exog
        if last_exog is not None and len(last_exog) > 0:
            col_list = list(exog_cols) if not isinstance(exog_cols, list) else exog_cols
            for i, col in enumerate(col_list):
                if col == "Fertilizer_percentage_lag_1":
                    fert_pct_avg = float(np.mean(last_exog[-12:, i])) if len(last_exog) >= 12 else float(np.mean(last_exog[:, i]))
                if col == "Fertilizer_Ratio_lag_1":
                    fert_ratio_avg = float(np.mean(last_exog[-12:, i])) if len(last_exog) >= 12 else float(np.mean(last_exog[:, i]))
    except Exception:
        pass

    # months_after_pruning maps to months_since_zero (pruning causes zero-yield periods)
    is_zero = 1 if months_after_pruning <= 2 else 0

    col_map = {
        "Rainfall_mm_lag_1": rainfall,
        "Rainfall_mm_lag_2": rainfall,
        "Rainfall_mm_lag_3": rainfall,
        "Wet_Days_Count_lag_1": wet_days,
        "Wet_Days_Count_lag_2": wet_days,
        "Wet_Days_Count_lag_3": wet_days,
        "Plucking_Rounds_lag_1": plucking_rounds,
        "Plucking_Rounds_lag_2": plucking_rounds,
        "Plucking_Rounds_lag_3": plucking_rounds,
        "Fertilizer_percentage_lag_1": fert_pct_avg,
        "Fertilizer_percentage_lag_2": fert_pct_avg,
        "Fertilizer_percentage_lag_3": fert_pct_avg,
        "Fertilizer_Ratio_lag_1": fert_ratio_avg,
        "Fertilizer_Ratio_lag_2": fert_ratio_avg,
        "Fertilizer_Ratio_lag_3": fert_ratio_avg,
        "is_zero_yield": is_zero,
        "months_since_zero": months_after_pruning,
    }
    return [col_map.get(col, 0.0) for col in exog_cols]


def get_best_month(field_key: str):
    """
    Find the historical month with the highest yield for a given field,
    and return its date + the exogenous variable values (rainfall, wet days,
    plucking rounds, months since zero) so the frontend can display
    'optimal conditions' as a reference.
    """
    if field_key not in sarimax_models:
        return None

    model_result = sarimax_models[field_key]
    meta = sarimax_meta[field_key]

    try:
        use_log = meta.get("USE_LOG1P", False)
        cap_value = meta.get("CAP_VALUE", 500)
        exog_cols = meta.get("EXOG_COLS", [])

        # Get fitted values (historical yields)
        fitted = model_result.fittedvalues
        if fitted is None or len(fitted) == 0:
            return None

        fitted_vals = fitted.values.tolist()
        fitted_dates = fitted.index

        # Reverse log transform
        if use_log:
            fitted_vals = [float(np.expm1(max(v, 0))) for v in fitted_vals]
        fitted_vals = [max(0, v) for v in fitted_vals]
        fitted_vals = [0 if v < ZERO_EPS else v for v in fitted_vals]
        fitted_vals = [min(v, cap_value * 1.2) for v in fitted_vals]

        # Find index of highest yield
        best_idx = int(np.argmax(fitted_vals))
        best_yield = round(fitted_vals[best_idx], 2)
        best_date = str(fitted_dates[best_idx].date())

        # Extract exog values for that month
        best_exog = {}
        try:
            exog_data = model_result.model.exog
            if exog_data is not None and best_idx < len(exog_data):
                row = exog_data[best_idx]
                col_list = list(exog_cols) if not isinstance(exog_cols, list) else exog_cols
                for i, col in enumerate(col_list):
                    if col == "Rainfall_mm_lag_1":
                        best_exog["rainfall_mm"] = round(float(row[i]), 1)
                    elif col == "Wet_Days_Count_lag_1":
                        best_exog["wet_days"] = round(float(row[i]), 1)
                    elif col == "Plucking_Rounds_lag_1":
                        best_exog["plucking_rounds"] = round(float(row[i]), 1)
                    elif col == "months_since_zero":
                        best_exog["months_after_pruning"] = round(float(row[i]), 0)
        except Exception:
            pass

        return {
            "date": best_date,
            "yield_kg": best_yield,
            "rainfall_mm": best_exog.get("rainfall_mm", 0),
            "wet_days": best_exog.get("wet_days", 0),
            "plucking_rounds": best_exog.get("plucking_rounds", 0),
            "months_after_pruning": int(best_exog.get("months_after_pruning", 0)),
        }
    except Exception:
        return None


def predict_yield(
    field_key: str,
    months_ahead: int = 6,
    rainfall: float = None,
    wet_days: float = None,
    plucking_rounds: float = None,
    months_after_pruning: float = None,
):
    """
    Generate yield forecast for a specific field.
    Uses user-provided environmental values as exogenous inputs,
    or falls back to historical averages from training data.
    """
    if field_key not in sarimax_models:
        return {"error": f"Model not found for {field_key}"}

    model_result = sarimax_models[field_key]
    meta = sarimax_meta[field_key]
    months_ahead = min(months_ahead, 24)

    try:
        use_log = meta.get("USE_LOG1P", False)
        cap_value = meta.get("CAP_VALUE", 500)
        use_exog = meta.get("USE_EXOG", False)
        exog_cols = meta.get("EXOG_COLS", [])

        # --- Historical fitted values for chart ---
        fitted = model_result.fittedvalues
        if fitted is not None:
            fitted_vals = fitted.values.tolist()
            fitted_dates = [str(d.date()) for d in fitted.index]

            if use_log:
                fitted_vals = [float(np.expm1(max(v, 0))) for v in fitted_vals]
            # Post-process: clip negatives, zero-out small, cap
            fitted_vals = [max(0, v) for v in fitted_vals]
            fitted_vals = [0 if v < ZERO_EPS else v for v in fitted_vals]
            fitted_vals = [min(v, cap_value * 1.2) for v in fitted_vals]
        else:
            fitted_vals = []
            fitted_dates = []

        # --- Build exogenous data for forecast ---
        has_user_input = any(v is not None and v > 0 for v in
                            [rainfall, wet_days, plucking_rounds, months_after_pruning])

        if use_exog and len(exog_cols) > 0:
            if has_user_input:
                # User provided values — build exog row from inputs
                # Fertilizer lags are sourced from training history internally
                exog_row = _build_exog_row(
                    rainfall or 0, wet_days or 0, plucking_rounds or 0,
                    months_after_pruning or 12, model_result, exog_cols
                )
                exog_future = np.tile(exog_row, (months_ahead, 1))
            else:
                # No user input — use average of last 12 months from training
                try:
                    last_exog = model_result.model.exog
                    if last_exog is not None and len(last_exog) >= 12:
                        mean_exog = np.mean(last_exog[-12:], axis=0)
                    elif last_exog is not None and len(last_exog) > 0:
                        mean_exog = np.mean(last_exog, axis=0)
                    else:
                        mean_exog = np.zeros(len(exog_cols))
                    exog_future = np.tile(mean_exog, (months_ahead, 1))
                except Exception:
                    exog_future = np.zeros((months_ahead, len(exog_cols)))

            forecast_result = model_result.get_forecast(steps=months_ahead, exog=exog_future)
        else:
            forecast_result = model_result.get_forecast(steps=months_ahead)

        # --- Process forecast ---
        forecast_mean = forecast_result.predicted_mean.values.tolist()
        forecast_dates = [str(d.date()) for d in forecast_result.predicted_mean.index]

        conf_int = forecast_result.conf_int()
        lower = conf_int.iloc[:, 0].values.tolist()
        upper = conf_int.iloc[:, 1].values.tolist()

        # Reverse log transform (matching notebook: np.expm1)
        if use_log:
            forecast_mean = [float(np.expm1(max(v, 0))) for v in forecast_mean]
            lower = [float(np.expm1(max(v, 0))) for v in lower]
            upper = [float(np.expm1(max(v, 0))) for v in upper]

        # Post-process (matching notebook pipeline)
        forecast_mean = [0 if v < ZERO_EPS else max(0, min(v, cap_value * 1.2)) for v in forecast_mean]
        lower = [max(0, min(v, cap_value * 1.2)) for v in lower]
        upper = [max(0, min(v, cap_value * 1.2)) for v in upper]

        # Summary stats
        avg_forecast = float(np.mean(forecast_mean)) if forecast_mean else 0
        total_forecast = float(np.sum(forecast_mean)) if forecast_mean else 0

        # Send last 24 months of history for chart
        hist_limit = min(len(fitted_vals), 24)

        # Input values used (for display)
        inputs_used = {}
        if has_user_input:
            inputs_used = {
                "rainfall_mm": rainfall or 0,
                "wet_days": wet_days or 0,
                "plucking_rounds": plucking_rounds or 0,
                "months_after_pruning": months_after_pruning or 12,
            }

        return {
            "field_key": field_key,
            "division": field_key.split("_", 1)[0],
            "field_id": field_key.split("_", 1)[1] if "_" in field_key else field_key,
            "model_info": {
                "order": meta.get("order", []),
                "seasonal_order": meta.get("seasonal_order", []),
                "n_observations": meta.get("n_obs", 0),
                "data_range": f"{meta.get('data_start', '')} to {meta.get('data_end', '')}",
                "cap_value": round(cap_value, 1),
                "uses_exog": use_exog,
                "uses_log": use_log,
            },
            "historical": {
                "dates": fitted_dates[-hist_limit:],
                "values": [round(v, 2) for v in fitted_vals[-hist_limit:]],
            },
            "forecast": {
                "dates": forecast_dates,
                "values": [round(v, 2) for v in forecast_mean],
                "lower_ci": [round(v, 2) for v in lower],
                "upper_ci": [round(v, 2) for v in upper],
            },
            "summary": {
                "avg_monthly_yield": round(avg_forecast, 2),
                "total_forecast_yield": round(total_forecast, 2),
                "months_forecasted": months_ahead,
            },
            "inputs_used": inputs_used,
        }

    except Exception as e:
        return {"error": f"Prediction failed: {str(e)}"}
