import numpy as np
import torch as th


BUYER_ACTION_LABELS = {
    0: "WAIT / NO BID",
    1: "CAUTIOUS BID",
    2: "COMPETITIVE BID",
    3: "VERY AGGRESSIVE BID",
}


def get_buyer_action_label(action: int) -> str:
    return BUYER_ACTION_LABELS.get(int(action), "UNKNOWN")


def get_buyer_action_explanation(action: int):
    action = int(action)

    if action == 0:
        return {
            "action_idx": 0,
            "title": "WAIT / NO BID",
            "meaning": "The buyer agent chose not to bid aggressively in this round.",
            "reason": "It learned that waiting is better than paying too much under these conditions.",
        }

    if action == 1:
        return {
            "action_idx": 1,
            "title": "CAUTIOUS BID",
            "meaning": "The buyer agent chose a cautious bid.",
            "reason": "It learned there may be value in bidding, but not too aggressively.",
        }

    if action == 2:
        return {
            "action_idx": 2,
            "title": "COMPETITIVE BID",
            "meaning": "The buyer agent chose a stronger bid to improve the chance of winning the lot.",
            "reason": "It learned that buying now may be better than waiting.",
        }

    return {
        "action_idx": 3,
        "title": "VERY AGGRESSIVE BID",
        "meaning": "The buyer agent chose its most aggressive bidding action.",
        "reason": "It learned that securing the lot now has the highest expected value.",
    }


def build_buyer_narrative(
    agent,
    obs_norm,
    action,
    current_price_used,
    forecast_price,
    bid_price,
    sold_volume,
    storage_cost_per_kg,
):
    obs_tensor = th.as_tensor(obs_norm, dtype=th.float32, device=agent.device).unsqueeze(0)
    q_values = agent.policy.q_net(obs_tensor).detach().cpu().numpy()[0]

    exp_q = np.exp(q_values - np.max(q_values))
    probs = exp_q / exp_q.sum()
    confidence = float(probs[int(action)] * 100.0)

    sold_volume = float(max(0.0, sold_volume))
    bid_price = float(bid_price)
    forecast_price = float(forecast_price)
    current_price_used = float(current_price_used)

    price_diff_vs_current = float(forecast_price - current_price_used)
    storage_total = float(storage_cost_per_kg * sold_volume)
    resale_margin = float((forecast_price - bid_price) * sold_volume)
    net_profit = float(resale_margin - storage_total)

    trend_desc = "Flat" if abs(price_diff_vs_current) < 10 else ("Rising" if price_diff_vs_current > 0 else "Falling")

    context = [
        f"Current market price = Rs. {current_price_used:,.2f}",
        f"Forecast price = Rs. {forecast_price:,.2f}",
        f"Buyer bid price = Rs. {bid_price:,.2f}",
        f"Sold volume = {sold_volume:,.0f} kg",
        f"Estimated storage cost = Rs. {storage_total:,.2f}",
    ]

    return {
        "confidence": confidence,
        "net_profit_estimate": net_profit,
        "context": context,
        "action_meta": get_buyer_action_explanation(action),
    }


def factory_explanation(forecast_price, reserve_price, released_total, lot_volume, sold, factory_profit):
    reserve_factor = reserve_price / forecast_price if forecast_price else 1.0
    release_factor = released_total / lot_volume if lot_volume else 0.0

    if reserve_factor >= 1.0:
        reserve_label = "HIGH RESERVE"
        reason = "Factory PPO learned that a higher reserve can improve profit when demand is stronger."
    else:
        reserve_label = "LOW RESERVE"
        reason = "Factory PPO learned that a lower reserve can improve clearance when demand is weaker."

    return {
        "reserve_label": reserve_label,
        "reserve_factor": float(reserve_factor),
        "release_factor": float(release_factor),
        "sold": bool(sold),
        "factory_profit": float(factory_profit),
        "lines": [
            f"RL decision: {reserve_label}",
            f"Reserve factor: {reserve_factor:.3f}x",
            f"Release factor: {release_factor:.2f}x",
            reason,
            "Outcome: cleared" if sold else "Outcome: not cleared",
        ],
    }


def broker_explanation(signal, commission_rate, guidance, sold, broker_profit):
    if signal == 1:
        signal_label = "BULLISH"
    elif signal == -1:
        signal_label = "BEARISH"
    else:
        signal_label = "NEUTRAL"

    return {
        "signal_label": signal_label,
        "commission_rate": float(commission_rate),
        "guidance": str(guidance),
        "sold": bool(sold),
        "broker_profit": float(broker_profit),
        "lines": [
            f"RL decision: {signal_label}",
            f"Commission rate: {commission_rate * 100:.2f}%",
            f"Guidance: {guidance}",
            "Outcome: broker earned commission" if sold else "Outcome: broker earned zero commission",
        ],
    }