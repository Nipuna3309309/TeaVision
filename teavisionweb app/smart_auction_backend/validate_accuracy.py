"""
validate_accuracy.py — Expanded Accuracy / Behavior Validation

Purpose:
- Show real-data directional validation
- Show MAS performance using real historical transitions
- Show per-elevation LOW / MID / HIGH summaries
- End with a simple supervisor-ready summary
"""

import warnings
from collections import Counter

import numpy as np
import pandas as pd
from stable_baselines3 import DQN, PPO

warnings.filterwarnings("ignore")

from src.data_loader import DataLoader
from src.auction_simulator import AuctionMAS
from app.services.tea_price_service import load_metrics_mape, MAPE_BY_KEY


BUYER_PATH = "models/buyer_agent_dqn.zip"
FACTORY_PATH = "models/factory_agent_ppo.zip"
BROKER_PATH = "models/broker_agent_ppo.zip"

DEFAULT_PASS = 70.0
DEFAULT_WARN = 55.0


def grade_pct(pct: float, pass_thr: float = DEFAULT_PASS, warn_thr: float = DEFAULT_WARN) -> str:
    if pct >= pass_thr:
        return "✅ PASS"
    if pct >= warn_thr:
        return "⚠️ WARN"
    return "❌ FAIL"


def safe_float(x, default=0.0):
    try:
        v = float(x)
        return v if np.isfinite(v) else default
    except Exception:
        return default


def safe_volume(x, default=10000.0):
    v = safe_float(x, default)
    if v <= 0:
        return default
    return float(np.clip(v, 1000.0, 50000.0))


def normalize_elev_label(v):
    s = str(v).strip().upper()
    if s.startswith("LOW"):
        return "LOW"
    if s.startswith("MID") or s.startswith("MED"):
        return "MID"
    if s.startswith("HIGH"):
        return "HIGH"
    return "LOW"


def buyer_obs_norm(cp, fp, demand, comp, elev, volume, storage, broker_sig=0.0, has_cp=1.0):
    mom = float(fp - cp)
    return np.array(
        [
            0.5,
            float(cp) / 5000.0,
            float(fp) / 5000.0,
            float(broker_sig),
            float(np.clip(mom / 300.0, -1.0, 1.0)),
            float(demand) / 2.0,
            float(comp) / 2.0,
            float(elev) / 2.0,
            float(volume) / 20000.0,
            float(storage) / 15.0,
            float(has_cp),
        ],
        dtype=np.float32,
    )


def factory_obs_norm(fp, cp, demand, comp, storage, volume, elev, prod_cost):
    mom = float(fp - cp)
    return np.array(
        [
            float(fp) / 5000.0,
            float(cp) / 5000.0,
            float(mom) / 1000.0,
            float(demand) / 2.0,
            float(comp) / 2.0,
            float(storage) / 15.0,
            float(volume) / 25000.0,
            float(elev) / 2.0,
            float(prod_cost) / 5000.0,
            0.0,
        ],
        dtype=np.float32,
    )


def broker_obs_norm(fp, cp, demand, comp, storage, volume, elev, reserve_price):
    mom = float(fp - cp)
    return np.array(
        [
            float(fp) / 5000.0,
            float(cp) / 5000.0,
            float(mom) / 1000.0,
            float(demand) / 2.0,
            float(comp) / 2.0,
            float(storage) / 15.0,
            float(volume) / 25000.0,
            float(elev) / 2.0,
            float(reserve_price) / 5000.0,
            0.0,
        ],
        dtype=np.float32,
    )


def trend_label(cp: float, fp: float) -> str:
    diff = float(fp - cp)
    tol = max(10.0, abs(cp) * 0.005)
    if diff > tol:
        return "RISING"
    if diff < -tol:
        return "FALLING"
    return "FLAT"


def load_real_transition_scenarios(dl: DataLoader) -> pd.DataFrame:
    df = dl.historical_data.copy()
    if df is None or df.empty:
        raise RuntimeError("historical_data is empty")

    required = ["ELEVATION", "GRADE", "DATE", "PRICE", "QTY", "ELEV_CODE"]
    for c in required:
        if c not in df.columns:
            raise RuntimeError(f"Missing required column in historical_data: {c}")

    df["ELEVATION"] = df["ELEVATION"].astype(str).map(normalize_elev_label)
    df = df.sort_values(["ELEVATION", "GRADE", "DATE"]).reset_index(drop=True)

    rows = []
    for (elev, grade), g in df.groupby(["ELEVATION", "GRADE"], sort=False):
        g = g.sort_values("DATE").reset_index(drop=True)
        if len(g) < 2:
            continue

        for i in range(len(g) - 1):
            cur = g.iloc[i]
            nxt = g.iloc[i + 1]

            gap_days = int((pd.Timestamp(nxt["DATE"]) - pd.Timestamp(cur["DATE"])).days)
            if gap_days < 1 or gap_days > 14:
                continue

            cp = safe_float(cur["PRICE"], np.nan)
            fp = safe_float(nxt["PRICE"], np.nan)
            if not np.isfinite(cp) or not np.isfinite(fp) or cp <= 0 or fp <= 0:
                continue

            volume = safe_volume(cur.get("QTY", 10000.0), 10000.0)
            elev_code = int(safe_float(cur.get("ELEV_CODE", 0), 0))
            tr = trend_label(cp, fp)

            rows.append(
                {
                    "elevation": elev,
                    "grade": str(grade),
                    "date_current": str(pd.Timestamp(cur["DATE"]).date()),
                    "date_next": str(pd.Timestamp(nxt["DATE"]).date()),
                    "cp": cp,
                    "fp": fp,
                    "volume": volume,
                    "elev_code": elev_code,
                    "trend": tr,
                    "prod_cost": min(cp, fp) * 0.92,
                    "storage": 5.0,
                    "demand": 1,
                    "comp": 1,
                }
            )

    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("No consecutive real transition scenarios could be built")
    return out


def print_header(title):
    print("\n" + "=" * 72)
    print(f"  {title}")
    print("=" * 72)


def print_section(title):
    print("\n" + "─" * 72)
    print(f"  {title}")
    print("─" * 72)


print_header("TEA BROKER AI — EXPANDED ACCURACY VALIDATION")

print("\n[SETUP] Loading data and models...")
dl = DataLoader("data", "models")
dl.load_data()

buyer_model = DQN.load(BUYER_PATH)
factory_model = PPO.load(FACTORY_PATH)
broker_model = PPO.load(BROKER_PATH)
mas = AuctionMAS(model_dir="models")

print("[OK] Data and models loaded.")

# ---------------------------------------------------------------------
# Section 1 — Existing price model metrics
# ---------------------------------------------------------------------
print_section("Section 1: Existing ARIMA Metrics Summary")
load_metrics_mape()

if len(MAPE_BY_KEY) == 0:
    print("  [WARN] No MAPE metrics loaded from data/metrics")
else:
    mape_rows = []
    for (elev, grade), mape in sorted(MAPE_BY_KEY.items()):
        mape_rows.append(
            {
                "Elevation": elev,
                "Grade": grade,
                "MAPE %": float(mape),
                "Quality": "Excellent"
                if mape <= 3
                else ("Good" if mape <= 6 else ("Fair" if mape <= 10 else "Weak")),
            }
        )

    df_mape = pd.DataFrame(mape_rows)
    print(df_mape.head(20).to_string(index=False))

    overall_mape = float(df_mape["MAPE %"].mean())
    good_share = float((df_mape["MAPE %"] <= 6.0).mean() * 100.0)
    fair_share = float((df_mape["MAPE %"] <= 10.0).mean() * 100.0)

    by_elev = (
        df_mape.groupby("Elevation")["MAPE %"]
        .agg(["count", "mean"])
        .reset_index()
        .rename(columns={"count": "Pairs", "mean": "Avg MAPE %"})
    )
    print("\nMAPE by elevation:")
    print(by_elev.to_string(index=False))

    print(f"\n  Avg MAPE across grade/elevation pairs : {overall_mape:.2f}%")
    print(f"  Share with MAPE <= 6%                 : {good_share:.1f}%")
    print(f"  Share with MAPE <= 10%                : {fair_share:.1f}%")
    print(f"  Price model quality gate              : {grade_pct(good_share, 70, 50)}")

# ---------------------------------------------------------------------
# Section 2 — Real historical transition scenarios
# ---------------------------------------------------------------------
print_section("Section 2: Building REAL Historical Transition Scenarios")
real_df = load_real_transition_scenarios(dl)
print(f"  Real transition rows built: {len(real_df):,}")

for elev in ["LOW", "MID", "HIGH"]:
    print(f"  {elev} rows: {len(real_df[real_df['elevation'] == elev]):,}")

non_flat = real_df[real_df["trend"].isin(["RISING", "FALLING"])].copy()
print(f"  Non-flat rows used for directional checks: {len(non_flat):,}")

# ---------------------------------------------------------------------
# Section 3 — Buyer validation on REAL directional moves
# ---------------------------------------------------------------------
print_section("Section 3: Buyer Directional Accuracy on REAL Transitions")

buyer_rows = []
for _, sc in non_flat.iterrows():
    obs = buyer_obs_norm(
        sc["cp"],
        sc["fp"],
        sc["demand"],
        sc["comp"],
        sc["elev_code"],
        sc["volume"],
        sc["storage"],
        broker_sig=0.0,
        has_cp=1.0,
    )
    action, _ = buyer_model.predict(obs, deterministic=True)
    action = int(action)

    hold_like = action in [0, 1]
    aggressive_like = action in [2, 3]
    correct = (sc["trend"] == "RISING" and hold_like) or (
        sc["trend"] == "FALLING" and aggressive_like
    )

    buyer_rows.append(
        {
            "trend": sc["trend"],
            "action": action,
            "correct": bool(correct),
            "elevation": sc["elevation"],
        }
    )

df_buyer = pd.DataFrame(buyer_rows)

buyer_overall = float(df_buyer["correct"].mean() * 100.0) if len(df_buyer) else 0.0
hold_when_rising = (
    float((df_buyer[df_buyer["trend"] == "RISING"]["action"].isin([0, 1])).mean() * 100.0)
    if (df_buyer["trend"] == "RISING").any()
    else 0.0
)
agg_when_falling = (
    float((df_buyer[df_buyer["trend"] == "FALLING"]["action"].isin([2, 3])).mean() * 100.0)
    if (df_buyer["trend"] == "FALLING").any()
    else 0.0
)

print(f"  Buyer overall directional accuracy : {buyer_overall:.1f}%  ({grade_pct(buyer_overall)})")
print(f"  Hold-like when rising              : {hold_when_rising:.1f}%")
print(f"  Aggressive-like when falling       : {agg_when_falling:.1f}%")
print(f"  Buyer action distribution          : {dict(Counter(df_buyer['action'].tolist()))}")

# ---------------------------------------------------------------------
# Section 4 — Broker validation on REAL directional moves
# ---------------------------------------------------------------------
print_section("Section 4: Broker Signal Accuracy on REAL Transitions")

SIGNAL_VALUES = [-1, 0, 1]

broker_rows = []
for _, sc in non_flat.iterrows():
    reserve_price = sc["fp"] * 1.00
    obs = broker_obs_norm(
        sc["fp"],
        sc["cp"],
        sc["demand"],
        sc["comp"],
        sc["storage"],
        sc["volume"],
        sc["elev_code"],
        reserve_price,
    )
    action, _ = broker_model.predict(obs, deterministic=True)
    sig_idx = int(action[0])
    signal = SIGNAL_VALUES[sig_idx]

    strict_correct = (
        (sc["trend"] == "RISING" and signal == 1)
        or (sc["trend"] == "FALLING" and signal == -1)
    )
    lenient_correct = strict_correct or (signal == 0)

    broker_rows.append(
        {
            "trend": sc["trend"],
            "signal": signal,
            "strict_correct": strict_correct,
            "lenient_correct": lenient_correct,
            "elevation": sc["elevation"],
        }
    )

df_broker = pd.DataFrame(broker_rows)

strict_acc = float(df_broker["strict_correct"].mean() * 100.0) if len(df_broker) else 0.0
lenient_acc = float(df_broker["lenient_correct"].mean() * 100.0) if len(df_broker) else 0.0

print(f"  Broker strict signal accuracy  : {strict_acc:.1f}%  ({grade_pct(strict_acc, 65, 50)})")
print(f"  Broker lenient signal accuracy : {lenient_acc:.1f}%  ({grade_pct(lenient_acc, 80, 65)})")
print(f"  Broker signal distribution     : {dict(Counter(df_broker['signal'].tolist()))}")

# ---------------------------------------------------------------------
# Section 5 — Factory reserve sanity on REAL directional moves
# ---------------------------------------------------------------------
print_section("Section 5: Factory Reserve Sanity on REAL Transitions")

RESERVE_FACTORS = [0.95, 0.98, 1.02, 1.06]

factory_rows = []
for _, sc in non_flat.iterrows():
    obs = factory_obs_norm(
        sc["fp"],
        sc["cp"],
        sc["demand"],
        sc["comp"],
        sc["storage"],
        sc["volume"],
        sc["elev_code"],
        sc["prod_cost"],
    )
    action, _ = factory_model.predict(obs, deterministic=True)
    reserve_idx = int(action[0])
    reserve_factor = RESERVE_FACTORS[reserve_idx]

    correct = (
        (sc["trend"] == "RISING" and reserve_factor >= 1.00)
        or (sc["trend"] == "FALLING" and reserve_factor <= 1.00)
    )

    factory_rows.append(
        {
            "trend": sc["trend"],
            "reserve_factor": reserve_factor,
            "correct": correct,
            "elevation": sc["elevation"],
        }
    )

df_factory = pd.DataFrame(factory_rows)
factory_acc = float(df_factory["correct"].mean() * 100.0) if len(df_factory) else 0.0

print(f"  Factory reserve directional sanity : {factory_acc:.1f}%  ({grade_pct(factory_acc, 65, 50)})")
print(f"  Reserve factor distribution        : {dict(Counter(df_factory['reserve_factor'].tolist()))}")

# ---------------------------------------------------------------------
# Section 6 — Full MAS audit on REAL transitions
# ---------------------------------------------------------------------
print_section("Section 6: Full MAS Audit on REAL Historical Transitions")

mas_rows = []
for _, sc in non_flat.iterrows():
    obs = buyer_obs_norm(
        sc["cp"],
        sc["fp"],
        sc["demand"],
        sc["comp"],
        sc["elev_code"],
        sc["volume"],
        sc["storage"],
        broker_sig=0.0,
        has_cp=1.0,
    )

    res = mas.run_one_round(
        buyer_model=buyer_model,
        buyer_obs=obs,
        forecast_price=float(sc["fp"]),
        current_price_used=float(sc["cp"]),
        lot_volume=float(sc["volume"]),
        storage_cost_per_kg=float(sc["storage"]),
        demand_level=int(sc["demand"]),
        competition=int(sc["comp"]),
        production_cost_per_unit=float(sc["prod_cost"]),
    )

    buyer_ok = (
        (sc["trend"] == "RISING" and int(res.buyer_action) in [0, 1])
        or (sc["trend"] == "FALLING" and int(res.buyer_action) in [2, 3])
    )
    broker_ok = (
        (sc["trend"] == "RISING" and int(res.broker_signal) in [0, 1])
        or (sc["trend"] == "FALLING" and int(res.broker_signal) in [-1, 0])
    )

    mas_rows.append(
        {
            "elevation": sc["elevation"],
            "trend": sc["trend"],
            "sold": bool(res.sold),
            "factory_profit": float(res.factory_profit),
            "broker_profit": float(res.broker_profit),
            "buyer_ok": bool(buyer_ok),
            "broker_ok": bool(broker_ok),
            "buyer_action": int(res.buyer_action),
            "broker_signal": int(res.broker_signal),
            "reserve_price": float(res.reserve_price),
        }
    )

df_mas = pd.DataFrame(mas_rows)

system_clearance = float(df_mas["sold"].mean() * 100.0) if len(df_mas) else 0.0
factory_positive = float((df_mas["factory_profit"] > 0).mean() * 100.0) if len(df_mas) else 0.0
broker_positive = float((df_mas["broker_profit"] > 0).mean() * 100.0) if len(df_mas) else 0.0
buyer_alignment = float(df_mas["buyer_ok"].mean() * 100.0) if len(df_mas) else 0.0
broker_alignment = float(df_mas["broker_ok"].mean() * 100.0) if len(df_mas) else 0.0

print(f"  MAS clearance rate                  : {system_clearance:.1f}%  ({grade_pct(system_clearance, 55, 40)})")
print(f"  Factory profitable rounds           : {factory_positive:.1f}%  ({grade_pct(factory_positive, 55, 40)})")
print(f"  Broker profitable rounds            : {broker_positive:.1f}%  ({grade_pct(broker_positive, 55, 40)})")
print(f"  Buyer alignment with real direction : {buyer_alignment:.1f}%  ({grade_pct(buyer_alignment)})")
print(f"  Broker alignment with real direction: {broker_alignment:.1f}%  ({grade_pct(broker_alignment, 75, 60)})")

# ---------------------------------------------------------------------
# Section 7 — Per elevation summary
# ---------------------------------------------------------------------
print_section("Section 7: Per-Elevation Summary")

summary_rows = []
for elev in ["LOW", "MID", "HIGH"]:
    sub_m = df_mas[df_mas["elevation"] == elev]
    sub_b = df_buyer[df_buyer["elevation"] == elev]
    sub_br = df_broker[df_broker["elevation"] == elev]
    sub_f = df_factory[df_factory["elevation"] == elev]

    summary_rows.append(
        {
            "Elevation": elev,
            "Rows": len(sub_m),
            "Buyer Dir Acc %": round(float(sub_b["correct"].mean() * 100.0), 1) if len(sub_b) else 0.0,
            "Broker Lenient %": round(float(sub_br["lenient_correct"].mean() * 100.0), 1) if len(sub_br) else 0.0,
            "Factory Reserve %": round(float(sub_f["correct"].mean() * 100.0), 1) if len(sub_f) else 0.0,
            "Factory Profit+ %": round(float((sub_m["factory_profit"] > 0).mean() * 100.0), 1) if len(sub_m) else 0.0,
            "Broker Profit+ %": round(float((sub_m["broker_profit"] > 0).mean() * 100.0), 1) if len(sub_m) else 0.0,
            "Buyer Action Dist": str(dict(Counter(sub_m["buyer_action"].tolist()))) if len(sub_m) else "{}",
            "Broker Signal Dist": str(dict(Counter(sub_m["broker_signal"].tolist()))) if len(sub_m) else "{}",
        }
    )

df_summary = pd.DataFrame(summary_rows)
print(df_summary.to_string(index=False))

# ---------------------------------------------------------------------
# Final verdict
# ---------------------------------------------------------------------
print_header("FINAL VALIDATION SNAPSHOT")

print(f"Buyer directional accuracy             : {buyer_overall:.1f}%")
print(f"Broker lenient directional accuracy    : {lenient_acc:.1f}%")
print(f"Factory reserve directional sanity     : {factory_acc:.1f}%")
print(f"MAS factory profitable rounds          : {factory_positive:.1f}%")
print(f"MAS broker profitable rounds           : {broker_positive:.1f}%")

score_components = [
    buyer_overall,
    lenient_acc,
    factory_acc,
    factory_positive,
    broker_positive,
]
overall_score = float(np.mean(score_components))

if overall_score >= 90:
    overall_grade = "EXCELLENT"
    overall_verdict = "Very strong research/demo validation performance."
elif overall_score >= 80:
    overall_grade = "STRONG"
    overall_verdict = "Strong research/demo validation performance."
elif overall_score >= 70:
    overall_grade = "GOOD"
    overall_verdict = "Good validation performance, but some areas still need improvement."
else:
    overall_grade = "MODERATE"
    overall_verdict = "Validation performance is moderate and should be improved further."

real_transition_count = len(real_df)
non_flat_count = len(non_flat)
mas_eval_count = len(df_mas)

print("\n" + "=" * 72)

print(
    f"""
This accuracy validation was performed using:

1. Real historical transition rounds : {real_transition_count:,}
2. Directional evaluation rounds     : {non_flat_count:,}
3. Full MAS evaluation rounds        : {mas_eval_count:,}

Key measured results:
- Buyer directional accuracy         : {buyer_overall:.1f}%
- Broker directional accuracy        : {lenient_acc:.1f}%
- Factory reserve decision accuracy  : {factory_acc:.1f}%
- Factory profitable MAS rounds      : {factory_positive:.1f}%
- Broker profitable MAS rounds       : {broker_positive:.1f}%

Overall research/demo score          : {overall_score:.1f}%
Overall grade                        : {overall_grade}

Final verdict:
{overall_verdict}
""".strip()
)
