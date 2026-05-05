import numpy as np

from src.data_loader import month_week_to_date, date_to_sale_no
from app.services.explain_service import (
    get_buyer_action_label,
    build_buyer_narrative,
    factory_explanation,
    broker_explanation,
)


def normalize_elevation(elevation: str) -> str:
    e = str(elevation).strip().lower()
    if e.startswith("low"):
        return "Low"
    if e.startswith("mid") or e.startswith("med"):
        return "Mid"
    if e.startswith("high"):
        return "High"
    return "Low"


def normalize_level(value: str) -> str:
    v = str(value).strip().lower()
    if v.startswith("low"):
        return "Low"
    if v.startswith("med") or v.startswith("mid"):
        return "Medium"
    if v.startswith("high"):
        return "High"
    return "Medium"


D_MAP = {"Low": 0, "Medium": 1, "High": 2}
C_MAP = {"Low": 0, "Medium": 1, "High": 2}
E_MAP = {"Low": 0, "Mid": 1, "High": 2}


def run_simulation(state, req):
    elevation = normalize_elevation(req.elevation)
    demand = normalize_level(req.demand)
    competition = normalize_level(req.competition)

    # 1) Forecast
    fc_res, _ = state.dl.forecast_price_month_week(
        elevation_ui=elevation,
        grade=req.grade,
        target_year=req.year,
        target_month=req.month,
        target_week_in_month=req.week_in_month,
        return_last_n_weeks=8,
    )

    forecast_price = float(fc_res.predicted_price)
    target_date = month_week_to_date(req.year, req.month, req.week_in_month)
    target_sale_no = date_to_sale_no(target_date)

    # 2) Actual price
    actual_price = state.dl.get_actual_price_by_sale(
        req.year, target_sale_no, req.grade, elevation
    )

    # 3) Current price used
    current_price_used = (
        float(req.current_price)
        if req.use_current_price and req.current_price is not None and req.current_price > 0
        else float(actual_price) if actual_price is not None else forecast_price
    )

    # 4) Numeric mappings
    demand_val = D_MAP[demand]
    comp_val = C_MAP[competition]
    elev_val = E_MAP[elevation]
    has_cp = 1.0 if req.use_current_price else 0.0

    # 5) Build buyer obs
    mom = forecast_price - current_price_used

    buyer_obs = np.array([
        0.2,
        current_price_used / 5000.0,
        forecast_price / 5000.0,
        0.0,
        np.clip(mom / 300.0, -1.0, 1.0),
        demand_val / 2.0,
        comp_val / 2.0,
        elev_val / 2.0,
        req.lot_volume / 20000.0,
        req.storage_cost / 15.0,
        has_cp,
    ], dtype=np.float32)

    # 6) Production cost
    prod_cost = (
        float(req.production_cost)
        if req.use_production_cost and req.production_cost is not None and req.production_cost > 0
        else float(min(current_price_used, forecast_price) * 0.92)
    )

    # 7) Run MAS
    mas_res = state.mas.run_one_round(
        buyer_model=state.buyer_model,
        buyer_obs=buyer_obs,
        forecast_price=forecast_price,
        current_price_used=current_price_used,
        lot_volume=req.lot_volume,
        storage_cost_per_kg=req.storage_cost,
        demand_level=demand_val,
        competition=comp_val,
        production_cost_per_unit=prod_cost,
    )

    released_total = float(mas_res.sold_volume + mas_res.unsold_volume)
    reserve_factor = float(mas_res.reserve_price / forecast_price) if forecast_price > 0 else 1.0
    release_factor = float(released_total / req.lot_volume) if req.lot_volume > 0 else 0.0

    # 8) Explanations
    # If explanation code fails, do NOT crash the endpoint
    try:
        buyer_meta = build_buyer_narrative(
            state.buyer_model,
            buyer_obs,
            mas_res.buyer_action,
            current_price_used,
            forecast_price,
            req.storage_cost,
            req.lot_volume,
        )
    except Exception as e:
        buyer_meta = {
            "confidence": 0.0,
            "net_profit_estimate": 0.0,
            "context": [f"Buyer explanation failed: {str(e)}"],
            "logic": "Explanation generation failed.",
            "quote": "No explanation available.",
            "action_meta": {
                "title": get_buyer_action_label(mas_res.buyer_action),
                "meaning": "Unavailable",
                "reason": "Unavailable",
            },
        }

    try:
        factory_meta = factory_explanation(
            forecast_price,
            mas_res.reserve_price,
            released_total,
            req.lot_volume,
            mas_res.sold,
            mas_res.factory_profit,
        )
    except Exception as e:
        factory_meta = {
            "reserve_label": "UNKNOWN",
            "reserve_factor": reserve_factor,
            "release_factor": release_factor,
            "sold": bool(mas_res.sold),
            "factory_profit": float(mas_res.factory_profit),
            "lines": [f"Factory explanation failed: {str(e)}"],
        }

    try:
        broker_meta = broker_explanation(
            mas_res.broker_signal,
            mas_res.commission_rate,
            mas_res.broker_guidance,
            mas_res.sold,
            mas_res.broker_profit,
        )
    except Exception as e:
        broker_meta = {
            "signal_label": "UNKNOWN",
            "commission_rate": float(mas_res.commission_rate),
            "guidance": str(mas_res.broker_guidance),
            "sold": bool(mas_res.sold),
            "broker_profit": float(mas_res.broker_profit),
            "lines": [f"Broker explanation failed: {str(e)}"],
        }

    return {
        "forecast_price": float(forecast_price),
        "current_price_used": float(current_price_used),
        "actual_price": float(actual_price) if actual_price is not None else None,
        "target_sale_no": int(target_sale_no),
        "target_date": str(target_date.date()),
        "steps_ahead": int(fc_res.steps_ahead),

        "sold": bool(mas_res.sold),
        "reserve_price": float(mas_res.reserve_price),
        "bid_price": float(mas_res.bid_price),
        "sold_volume": float(mas_res.sold_volume),
        "unsold_volume": float(mas_res.unsold_volume),

        "commission_rate": float(mas_res.commission_rate),
        "broker_signal": int(mas_res.broker_signal),
        "broker_guidance": str(mas_res.broker_guidance),

        "factory_profit": float(mas_res.factory_profit),
        "broker_profit": float(mas_res.broker_profit),

        "buyer_action": int(mas_res.buyer_action),
        "buyer_action_label": get_buyer_action_label(mas_res.buyer_action),

        "reserve_factor": float(reserve_factor),
        "release_factor": float(release_factor),

        "buyer_explanation": buyer_meta,
        "factory_explanation": factory_meta,
        "broker_explanation": broker_meta,

        "production_cost_used": float(prod_cost),
        "demand_level_value": int(demand_val),
        "competition_value": int(comp_val),
        "elevation_code": int(elev_val),
    }