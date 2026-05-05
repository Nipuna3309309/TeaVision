from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException

from app.schemas import (
    SimulationRequest,
    LearningRequest,
    GradesResponse,
    MessageResponse,
    SimulationResponse,
    TeaPriceMetadataResponse,
    TeaPriceRequest,
    TeaPriceResponse,
)
from app.services.model_loader import state
from app.services.tea_price_service import (
    load_metrics_mape,
    get_band_pct,
    band_from_price,
    build_series_with_bands,
)
from app.services.explain_service import (
    get_buyer_action_label,
    build_buyer_narrative,
    factory_explanation,
    broker_explanation,
)
from src.data_loader import date_to_sale_no

router = APIRouter()


def ensure_backend_ready():
    if state.data_loader is None:
        try:
            state.load_all()
        except Exception as e:
            detail = state.last_error or str(e)
            raise HTTPException(
                status_code=500,
                detail=f"Backend initialization failed: {detail}",
            )


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def normalize_elevation_ui(elevation: str) -> str:
    e = str(elevation).strip().lower()
    if e.startswith("low"):
        return "Low"
    if e.startswith("mid") or e.startswith("med"):
        return "Mid"
    if e.startswith("high"):
        return "High"
    return "Low"


def elevation_to_code(elevation: str) -> int:
    e = normalize_elevation_ui(elevation)
    return {"Low": 0, "Mid": 1, "High": 2}.get(e, 0)


def level_to_int(value: str) -> int:
    v = str(value).strip().lower()
    if v == "low":
        return 0
    if v in ("medium", "mid"):
        return 1
    if v == "high":
        return 2
    return 1


def latest_known_price(
    dl,
    grade: str,
    elevation_ui: str,
    before_date=None,
) -> Optional[float]:
    if dl is None or getattr(dl, "historical_data", None) is None:
        return None

    df = dl.historical_data.copy()
    elev_key = normalize_elevation_ui(elevation_ui).upper()
    grade_key = str(grade).strip().upper()

    sub = df[
        (df["GRADE"].astype(str).str.upper().str.strip() == grade_key)
        & (df["ELEVATION"].astype(str).str.upper().str.strip() == elev_key)
    ].copy()

    if before_date is not None:
        cutoff = pd.Timestamp(before_date)
        sub = sub[sub["DATE"] < cutoff]

    sub = sub.sort_values("DATE")

    if sub.empty:
        return None

    try:
        return float(sub.iloc[-1]["PRICE"])
    except Exception:
        return None


def build_buyer_obs(
    current_price: float,
    forecast_price: float,
    demand_level: int,
    competition_level: int,
    elevation_code: int,
    lot_volume: float,
    storage_cost: float,
) -> np.ndarray:
    momentum = float(forecast_price - current_price)
    return np.array(
        [
            0.5,
            float(current_price) / 5000.0,
            float(forecast_price) / 5000.0,
            0.0,  # broker signal filled later inside MAS
            float(np.clip(momentum / 300.0, -1.0, 1.0)),
            float(demand_level) / 2.0,
            float(competition_level) / 2.0,
            float(elevation_code) / 2.0,
            float(lot_volume) / 20000.0,
            float(storage_cost) / 15.0,
            1.0,
        ],
        dtype=np.float32,
    )


def get_simulation_dependencies():
    ensure_backend_ready()

    dl = getattr(state, "data_loader", None)
    mas = getattr(state, "mas", None)
    buyer_model = getattr(state, "buyer_model", None)

    if dl is None:
        raise HTTPException(status_code=500, detail="Data loader not initialized")
    if mas is None:
        raise HTTPException(status_code=500, detail="Auction MAS not initialized")
    if buyer_model is None:
        raise HTTPException(status_code=500, detail="Buyer model not initialized")

    return dl, mas, buyer_model


# ---------------------------------------------------------------------
# Status / utility routes
# ---------------------------------------------------------------------
@router.get("/")
def api_root():
    return {"message": "Tea Broker AI API running"}


@router.get("/health")
def health():
    return {
        "status": "ok",
        "data_loader": getattr(state, "data_loader", None) is not None,
        "buyer_model": getattr(state, "buyer_model", None) is not None,
        "factory_model": getattr(state, "factory_model", None) is not None,
        "broker_model": getattr(state, "broker_model", None) is not None,
        "mas": getattr(state, "mas", None) is not None,
    }


@router.get("/status/init")
def status_init():
    ready = (
        getattr(state, "data_loader", None) is not None
        and getattr(state, "buyer_model", None) is not None
        and getattr(state, "mas", None) is not None
    )
    return {"initialized": ready}


# ---------------------------------------------------------------------
# Existing MAS routes
# ---------------------------------------------------------------------
@router.get("/grades/{elevation}", response_model=GradesResponse)
def get_grades(elevation: str):
    ensure_backend_ready()

    dl = getattr(state, "data_loader", None)
    if dl is None:
        raise HTTPException(status_code=500, detail="Data loader not initialized")

    elevation_ui = normalize_elevation_ui(elevation)
    grades = dl.get_available_arima_grades(elevation_ui)
    return GradesResponse(grades=grades)


@router.post("/simulate", response_model=SimulationResponse)
def simulate(req: SimulationRequest):
    dl, mas, buyer_model = get_simulation_dependencies()

    elevation_ui = normalize_elevation_ui(req.elevation)
    grades = dl.get_available_arima_grades(elevation_ui)
    if req.grade not in grades:
        raise HTTPException(
            status_code=404,
            detail=f"No ARIMA model for elevation={elevation_ui}, grade={req.grade}",
        )

    try:
        forecast_result, _series = dl.forecast_price_month_week(
            elevation_ui=elevation_ui,
            grade=req.grade,
            target_year=req.year,
            target_month=req.month,
            target_week_in_month=req.week_in_month,
            return_last_n_weeks=8,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast failed: {e}")

    forecast_price = float(forecast_result.predicted_price)
    target_sale_no = int(forecast_result.target_sale_no)
    target_date = str(forecast_result.target_date.date())
    steps_ahead = int(forecast_result.steps_ahead)

    actual_price = dl.get_actual_price_by_sale(
        year=req.year,
        sale_no=target_sale_no,
        grade=req.grade,
        elevation_ui=elevation_ui,
    )

    if req.use_current_price and req.current_price is not None and req.current_price > 0:
        current_price_used = float(req.current_price)
    else:
        latest_price = latest_known_price(
            dl,
            req.grade,
            elevation_ui,
            before_date=forecast_result.target_date,
        )
        current_price_used = float(latest_price if latest_price is not None else forecast_price)

    demand_level = level_to_int(req.demand)
    competition_level = level_to_int(req.competition)
    elev_code = elevation_to_code(elevation_ui)

    if req.use_production_cost and req.production_cost is not None and req.production_cost > 0:
        production_cost = float(req.production_cost)
    else:
        production_cost = float(min(current_price_used, forecast_price) * 0.92)

    buyer_obs = build_buyer_obs(
        current_price=current_price_used,
        forecast_price=forecast_price,
        demand_level=demand_level,
        competition_level=competition_level,
        elevation_code=elev_code,
        lot_volume=float(req.lot_volume),
        storage_cost=float(req.storage_cost),
    )

    try:
        result = mas.run_one_round(
            buyer_model=buyer_model,
            buyer_obs=buyer_obs,
            forecast_price=forecast_price,
            current_price_used=current_price_used,
            lot_volume=float(req.lot_volume),
            storage_cost_per_kg=float(req.storage_cost),
            demand_level=demand_level,
            competition=competition_level,
            production_cost_per_unit=production_cost,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auction simulation failed: {e}")

    offered_volume = float(getattr(result, "offered_volume", result.sold_volume + result.unsold_volume))
    reserve_factor = float(result.reserve_price / forecast_price) if forecast_price > 0 else 1.0
    release_factor = float(offered_volume / req.lot_volume) if req.lot_volume > 0 else 0.0

    try:
        buyer_meta = build_buyer_narrative(
            buyer_model,
            buyer_obs,
            result.buyer_action,
            current_price_used,
            forecast_price,
            float(result.bid_price),
            float(result.sold_volume),
            float(req.storage_cost),
        )
    except Exception as e:
        buyer_meta = {
            "confidence": 0.0,
            "net_profit_estimate": 0.0,
            "context": [f"Buyer explanation failed: {str(e)}"],
            "logic": "Explanation generation failed.",
            "quote": "No explanation available.",
            "action_meta": {
                "action_idx": int(result.buyer_action),
                "title": get_buyer_action_label(result.buyer_action),
                "meaning": "Unavailable",
                "reason": "Unavailable",
            },
        }

    try:
        factory_meta = factory_explanation(
            forecast_price,
            float(result.reserve_price),
            offered_volume,
            float(req.lot_volume),
            bool(result.sold),
            float(result.factory_profit),
        )
    except Exception as e:
        factory_meta = {
            "reserve_label": "UNKNOWN",
            "reserve_factor": reserve_factor,
            "release_factor": release_factor,
            "sold": bool(result.sold),
            "factory_profit": float(result.factory_profit),
            "lines": [f"Factory explanation failed: {str(e)}"],
        }

    try:
        broker_meta = broker_explanation(
            int(result.broker_signal),
            float(result.commission_rate),
            str(result.broker_guidance),
            bool(result.sold),
            float(result.broker_profit),
        )
    except Exception as e:
        broker_meta = {
            "signal_label": "UNKNOWN",
            "commission_rate": float(result.commission_rate),
            "guidance": str(result.broker_guidance),
            "sold": bool(result.sold),
            "broker_profit": float(result.broker_profit),
            "lines": [f"Broker explanation failed: {str(e)}"],
        }

    buyer_label = get_buyer_action_label(result.buyer_action)
    confidence_score = float(buyer_meta.get("confidence", 0.0))

    return SimulationResponse(
        forecast_price=forecast_price,
        current_price_used=current_price_used,
        actual_price=actual_price,
        target_sale_no=target_sale_no,
        target_date=target_date,
        steps_ahead=steps_ahead,
        sold=bool(result.sold),
        reserve_price=float(result.reserve_price),
        bid_price=float(result.bid_price),
        sold_volume=float(result.sold_volume),
        unsold_volume=float(result.unsold_volume),
        commission_rate=float(result.commission_rate),
        broker_signal=int(result.broker_signal),
        broker_guidance=str(result.broker_guidance),
        factory_profit=float(result.factory_profit),
        broker_profit=float(result.broker_profit),
        buyer_action=int(result.buyer_action),
        buyer_action_label=buyer_label,
        reserve_factor=reserve_factor,
        release_factor=release_factor,
        buyer_explanation=buyer_meta,
        factory_explanation=factory_meta,
        broker_explanation=broker_meta,
        confidence_score=confidence_score,
    )


@router.post("/learn", response_model=MessageResponse)
def learn(req: LearningRequest):
    dl = getattr(state, "data_loader", None)
    if dl is None:
        raise HTTPException(status_code=500, detail="Data loader not initialized")

    elevation_ui = normalize_elevation_ui(req.elevation)
    demand_level = level_to_int(req.demand)
    competition_level = level_to_int(req.competition)
    elev_code = elevation_to_code(elevation_ui)

    try:
        forecast_result, _series = dl.forecast_price_month_week(
            elevation_ui=elevation_ui,
            grade=req.grade,
            target_year=req.year,
            target_month=req.month,
            target_week_in_month=req.week_in_month,
            return_last_n_weeks=8,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to prepare learning scenario: {e}")

    forecast_price = float(forecast_result.predicted_price)

    if req.use_current_price and req.current_price is not None and req.current_price > 0:
        current_price_used = float(req.current_price)
    else:
        latest_price = latest_known_price(
            dl,
            req.grade,
            elevation_ui,
            before_date=forecast_result.target_date,
        )
        current_price_used = float(latest_price if latest_price is not None else forecast_price)

    if req.use_production_cost and req.production_cost is not None and req.production_cost > 0:
        production_cost = float(req.production_cost)
    else:
        production_cost = float(min(current_price_used, forecast_price) * 0.92)

    messages = []

    buyer_model = getattr(state, "buyer_model", None)
    buyer_env = getattr(state, "buyer_env", None)
    if req.buyer_online_steps > 0:
        if buyer_model is not None and buyer_env is not None:
            try:
                buyer_env.set_scenario(
                    forecast_price=forecast_price,
                    current_price=current_price_used,
                    demand_level=demand_level,
                    competition=competition_level,
                    storage_cost_per_kg=float(req.storage_cost),
                    lot_volume=float(req.lot_volume),
                    elev_code=elev_code,
                    broker_signal=0.0,
                    use_fixed=True,
                )
                buyer_model.set_env(buyer_env)
                buyer_model.learn(
                    total_timesteps=int(req.buyer_online_steps),
                    reset_num_timesteps=False,
                    progress_bar=False,
                )
                state.buyer_model = buyer_model
                messages.append(f"Buyer updated ({req.buyer_online_steps} steps)")
            except Exception as e:
                messages.append(f"Buyer skipped: {e}")
        else:
            messages.append("Buyer skipped: model or environment not available")

    factory_model = getattr(state, "factory_model", None)
    factory_env = getattr(state, "factory_env", None)
    if req.factory_online_steps > 0:
        if factory_model is not None and factory_env is not None:
            try:
                factory_env.set_scenario(
                    forecast_price=forecast_price,
                    current_price=current_price_used,
                    demand_level=demand_level,
                    competition=competition_level,
                    storage_cost_per_kg=float(req.storage_cost),
                    lot_volume=float(req.lot_volume),
                    elev_code=elev_code,
                    production_cost_per_unit=production_cost,
                    use_fixed=True,
                )
                factory_model.set_env(factory_env)
                factory_model.learn(
                    total_timesteps=int(req.factory_online_steps),
                    reset_num_timesteps=False,
                    progress_bar=False,
                )
                state.factory_model = factory_model
                if getattr(state, "mas", None) is not None:
                    state.mas.factory_rl = factory_model
                messages.append(f"Factory updated ({req.factory_online_steps} steps)")
            except Exception as e:
                messages.append(f"Factory skipped: {e}")
        else:
            messages.append("Factory skipped: model or environment not available")

    broker_model = getattr(state, "broker_model", None)
    broker_env = getattr(state, "broker_env", None)
    if req.broker_online_steps > 0:
        if broker_model is not None and broker_env is not None:
            try:
                broker_env.set_scenario(
                    forecast_price=forecast_price,
                    current_price=current_price_used,
                    demand_level=demand_level,
                    competition=competition_level,
                    storage_cost_per_kg=float(req.storage_cost),
                    lot_volume=float(req.lot_volume),
                    elev_code=elev_code,
                    reserve_price=forecast_price,
                    use_fixed=True,
                )
                broker_model.set_env(broker_env)
                broker_model.learn(
                    total_timesteps=int(req.broker_online_steps),
                    reset_num_timesteps=False,
                    progress_bar=False,
                )
                state.broker_model = broker_model
                if getattr(state, "mas", None) is not None:
                    state.mas.broker_rl = broker_model
                messages.append(f"Broker updated ({req.broker_online_steps} steps)")
            except Exception as e:
                messages.append(f"Broker skipped: {e}")
        else:
            messages.append("Broker skipped: model or environment not available")

    if not messages:
        messages.append("No online learning steps requested")

    return MessageResponse(message=" | ".join(messages))


@router.post("/reload", response_model=MessageResponse)
def reload_all():
    try:
        state.load_all()
        load_metrics_mape()
        return MessageResponse(message="Models, data, and tea price metrics reloaded successfully.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reload failed: {e}")


# ---------------------------------------------------------------------
# Tea Price routes
# ---------------------------------------------------------------------
@router.get("/tea-price/metadata", response_model=TeaPriceMetadataResponse)
def get_tea_price_metadata():
    ensure_backend_ready()

    dl = getattr(state, "data_loader", None)
    if dl is None:
        raise HTTPException(status_code=500, detail="Data loader not initialized")

    grades_by = {
        "Low": dl.get_available_arima_grades("Low"),
        "Mid": dl.get_available_arima_grades("Mid"),
        "High": dl.get_available_arima_grades("High"),
    }

    return TeaPriceMetadataResponse(
        elevations=["Low", "Mid", "High"],
        grades_by_elevation=grades_by,
    )


@router.post("/tea-price/predict", response_model=TeaPriceResponse)
def predict_tea_price(req: TeaPriceRequest):
    ensure_backend_ready()

    dl = getattr(state, "data_loader", None)
    if dl is None:
        raise HTTPException(status_code=500, detail="Data loader not initialized")

    elevation_ui = normalize_elevation_ui(req.elevation)

    try:
        forecast_result, series = dl.forecast_price_month_week(
            elevation_ui=elevation_ui,
            grade=req.grade,
            target_year=req.target_year,
            target_month=req.target_month,
            target_week_in_month=req.target_week_in_month,
            return_last_n_weeks=req.return_last_n_weeks,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tea price forecast failed: {e}")

    last_known_date = forecast_result.last_known_date
    band_pct = get_band_pct(elevation_ui, req.grade)

    final_pred = float(forecast_result.predicted_price)
    final_lo, final_hi = band_from_price(final_pred, band_pct)

    series_with_bands = build_series_with_bands(series, band_pct)

    if len(series_with_bands) == 0:
        target_date = forecast_result.target_date
        lo, hi = band_from_price(final_pred, band_pct)
        series_with_bands = [
            {
                "year": int(target_date.year),
                "sale_no": int(forecast_result.target_sale_no),
                "date": str(target_date.date()),
                "predicted_price": final_pred,
                "lower_band": lo,
                "upper_band": hi,
            }
        ]

    return TeaPriceResponse(
        elevation=elevation_ui,
        grade=req.grade,
        model_last_train_date=str(last_known_date.date()),
        model_last_train_year=int(last_known_date.year),
        model_last_train_sale_no=int(date_to_sale_no(last_known_date)),
        target_year=req.target_year,
        target_month=req.target_month,
        target_week_in_month=req.target_week_in_month,
        target_date=str(forecast_result.target_date.date()),
        target_sale_no=int(forecast_result.target_sale_no),
        steps_ahead=int(forecast_result.steps_ahead),
        predicted_price=final_pred,
        band_pct=float(band_pct),
        predicted_lower_band=float(final_lo),
        predicted_upper_band=float(final_hi),
        series=series_with_bands,
    )