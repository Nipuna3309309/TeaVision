"""
validate_agents.py — Strong Agent Validation Suite
Updated so Buyer monotonicity matches buyer-style action meaning

Buyer action meaning used here:
0 = WAIT / lowest aggressiveness
1 = CAUTIOUS
2 = COMPETITIVE
3 = AGGRESSIVE

Therefore:
- as future price improves for a buyer,
- buyer aggressiveness should generally stay the same or DECREASE.
"""

import os
import warnings
from collections import Counter

import numpy as np
import pandas as pd
from stable_baselines3 import DQN, PPO
from stable_baselines3.common.monitor import Monitor

warnings.filterwarnings("ignore")

from src.data_loader import DataLoader
from src.environment import TeaAuctionEnv
from src.factory_env import FactoryEnv
from src.broker_env import BrokerEnv
from src.auction_simulator import AuctionMAS


BUYER_PATH = "models/buyer_agent_dqn.zip"
FACTORY_PATH = "models/factory_agent_ppo.zip"
BROKER_PATH = "models/broker_agent_ppo.zip"

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️ WARN"

results = []


def log(test_name, status, detail=""):
    results.append((test_name, status, detail))
    print(f"  {status}  {test_name}")
    if detail:
        for line in str(detail).split("\n"):
            print(f"       {line}")


def safe_volume(x, default=10000.0):
    try:
        v = float(x)
        if not np.isfinite(v) or v <= 0:
            return default
        return float(np.clip(v, 1000.0, 50000.0))
    except Exception:
        return default


def buyer_obs_norm(
    cp,
    fp,
    demand,
    comp,
    elev,
    volume,
    storage,
    broker_sig=0.0,
    budget_norm=0.5,
    has_cp=1.0,
):
    mom = float(fp - cp)
    mom_norm = float(np.clip(mom / 300.0, -1.0, 1.0))
    return np.array(
        [
            float(budget_norm),
            float(cp) / 5000.0,
            float(fp) / 5000.0,
            float(broker_sig),
            mom_norm,
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


def normalize_elev_label(v):
    s = str(v).strip().upper()
    if s.startswith("LOW"):
        return "LOW"
    if s.startswith("MID") or s.startswith("MED"):
        return "MID"
    if s.startswith("HIGH"):
        return "HIGH"
    return "LOW"


def load_real_transition_scenarios(dl: DataLoader) -> pd.DataFrame:
    df = dl.historical_data.copy()
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

            cp = float(cur["PRICE"])
            fp = float(nxt["PRICE"])
            if cp <= 0 or fp <= 0:
                continue

            rows.append(
                {
                    "elevation": elev,
                    "grade": str(grade),
                    "cp": cp,
                    "fp": fp,
                    "demand": 1,
                    "comp": 1,
                    "storage": 5.0,
                    "volume": safe_volume(cur.get("QTY", 10000.0)),
                    "elev": int(cur.get("ELEV_CODE", 0)),
                    "prod_cost": min(cp, fp) * 0.92,
                }
            )

    return pd.DataFrame(rows)


print("\n" + "=" * 72)
print("  TEA BROKER AI — STRONG AGENT VALIDATION SUITE")
print("=" * 72)

print("\n[SETUP] Loading data and environments...")
dl = DataLoader("data", "models")
dl.load_data()

buyer_env = Monitor(TeaAuctionEnv(dl))
factory_env = Monitor(FactoryEnv(dl))
broker_env = Monitor(BrokerEnv(dl))

print("\n── Section 1: Model Loading ──────────────────────────────────────────────")

buyer_model = factory_model = broker_model = None

for name, path, env, cls in [
    ("Buyer DQN", BUYER_PATH, buyer_env, DQN),
    ("Factory PPO", FACTORY_PATH, factory_env, PPO),
    ("Broker PPO", BROKER_PATH, broker_env, PPO),
]:
    if not os.path.exists(path):
        log(f"{name} loads cleanly", FAIL, f"Missing: {path}")
        continue

    try:
        m = cls.load(path, env=env)
        log(
            f"{name} loads cleanly",
            PASS,
            f"Obs={m.policy.observation_space.shape} | Act={m.policy.action_space}",
        )
        if name == "Buyer DQN":
            buyer_model = m
        elif name == "Factory PPO":
            factory_model = m
        else:
            broker_model = m
    except Exception as e:
        log(f"{name} loads cleanly", FAIL, str(e))

if not all([buyer_model, factory_model, broker_model]):
    print("\n[FATAL] One or more models failed to load.")
    raise SystemExit(1)

print("\n── Section 2: Observation Shape Verification ───────────────────────────")

shape_checks = [
    ("Buyer obs shape", buyer_model.policy.observation_space.shape, (11,)),
    ("Factory obs shape", factory_model.policy.observation_space.shape, (10,)),
    ("Broker obs shape", broker_model.policy.observation_space.shape, (10,)),
]

for label, actual, expected in shape_checks:
    if actual == expected:
        log(label, PASS)
    else:
        log(label, FAIL, f"Got {actual}, expected {expected}")

print("\n── Section 3: Environment Smoke Tests ──────────────────────────────────")


def smoke_env(name, env, n=20):
    try:
        obs, _ = env.reset()
        if not np.all(np.isfinite(obs)):
            log(f"{name} env smoke test", FAIL, "Non-finite reset observation")
            return

        for _ in range(n):
            action = env.action_space.sample()
            obs, reward, done, trunc, _ = env.step(action)

            if not np.all(np.isfinite(obs)):
                log(f"{name} env smoke test", FAIL, "Non-finite step observation")
                return
            if not np.isfinite(float(reward)):
                log(f"{name} env smoke test", FAIL, "Non-finite reward")
                return

            if done or trunc:
                obs, _ = env.reset()

        log(f"{name} env smoke test", PASS)
    except Exception as e:
        log(f"{name} env smoke test", FAIL, str(e))


smoke_env("Buyer", TeaAuctionEnv(dl))
smoke_env("Factory", FactoryEnv(dl))
smoke_env("Broker", BrokerEnv(dl))

print("\n── Section 4: Determinism Checks ───────────────────────────────────────")


def check_determinism(name, model, obs, n=20):
    try:
        first, _ = model.predict(obs, deterministic=True)
        ok = True
        for _ in range(n - 1):
            cur, _ = model.predict(obs, deterministic=True)
            if not np.array_equal(np.asarray(cur), np.asarray(first)):
                ok = False
                break

        if ok:
            log(f"{name} deterministic on fixed input", PASS)
        else:
            log(f"{name} deterministic on fixed input", FAIL)
    except Exception as e:
        log(f"{name} deterministic on fixed input", FAIL, str(e))


check_determinism(
    "Buyer",
    buyer_model,
    buyer_obs_norm(1500, 1650, 1, 1, 1, 10000, 5, broker_sig=0.0),
)
check_determinism(
    "Factory",
    factory_model,
    factory_obs_norm(1650, 1500, 1, 1, 5, 10000, 1, 1380),
)
check_determinism(
    "Broker",
    broker_model,
    broker_obs_norm(1650, 1500, 1, 1, 5, 10000, 1, 1650),
)

print("\n── Section 5: Prediction Safety on Random Scenarios ────────────────────")

rng = np.random.RandomState(42)


def random_scenarios(n=200):
    rows = []
    for _ in range(n):
        cp = float(rng.uniform(800, 3000))
        fp = float(rng.uniform(800, 3000))
        rows.append(
            {
                "cp": cp,
                "fp": fp,
                "demand": int(rng.randint(0, 3)),
                "comp": int(rng.randint(0, 3)),
                "elev": int(rng.randint(0, 3)),
                "volume": float(rng.uniform(5000, 20000)),
                "storage": float(rng.uniform(2, 12)),
                "prod_cost": cp * float(rng.uniform(0.85, 0.97)),
            }
        )
    return rows


safe_ok = True
buyer_actions = []
factory_actions = []
broker_actions = []

try:
    for sc in random_scenarios(200):
        b_obs = buyer_obs_norm(
            sc["cp"], sc["fp"], sc["demand"], sc["comp"], sc["elev"], sc["volume"], sc["storage"]
        )
        f_obs = factory_obs_norm(
            sc["fp"], sc["cp"], sc["demand"], sc["comp"], sc["storage"], sc["volume"], sc["elev"], sc["prod_cost"]
        )
        br_obs = broker_obs_norm(
            sc["fp"], sc["cp"], sc["demand"], sc["comp"], sc["storage"], sc["volume"], sc["elev"], sc["fp"]
        )

        ba, _ = buyer_model.predict(b_obs, deterministic=True)
        fa, _ = factory_model.predict(f_obs, deterministic=True)
        bra, _ = broker_model.predict(br_obs, deterministic=True)

        ba = int(ba)
        fa = np.asarray(fa).astype(int)
        bra = np.asarray(bra).astype(int)

        if ba not in [0, 1, 2, 3]:
            safe_ok = False
        if len(fa) != 2:
            safe_ok = False
        if len(bra) != 2:
            safe_ok = False

        buyer_actions.append(ba)
        factory_actions.append(tuple(fa.tolist()))
        broker_actions.append(tuple(bra.tolist()))
except Exception as e:
    safe_ok = False
    log("Prediction safety on random scenarios", FAIL, str(e))

if safe_ok:
    log("Prediction safety on random scenarios", PASS)
    log("Buyer action diversity", PASS if len(set(buyer_actions)) >= 2 else WARN, dict(Counter(buyer_actions)))
    log("Factory action diversity", PASS if len(set(factory_actions)) >= 3 else WARN, dict(Counter(factory_actions)))
    log("Broker action diversity", PASS if len(set(broker_actions)) >= 3 else WARN, dict(Counter(broker_actions)))

print("\n── Section 6: Real-Data Action Diversity ───────────────────────────────")

real_df = load_real_transition_scenarios(dl)

if len(real_df) == 0:
    log("Real historical transition scenarios available", FAIL)
else:
    log("Real historical transition scenarios available", PASS, f"{len(real_df):,} rows")

    reserve_lookup = [0.95, 0.98, 1.02, 1.06]
    signal_lookup = [-1, 0, 1]

    sample_df = real_df.sample(min(300, len(real_df)), random_state=42)

    buyer_real = []
    factory_real = []
    broker_real = []

    for _, sc in sample_df.iterrows():
        b_obs = buyer_obs_norm(
            sc["cp"], sc["fp"], sc["demand"], sc["comp"], sc["elev"], sc["volume"], sc["storage"]
        )
        f_obs = factory_obs_norm(
            sc["fp"], sc["cp"], sc["demand"], sc["comp"], sc["storage"], sc["volume"], sc["elev"], sc["prod_cost"]
        )
        br_obs = broker_obs_norm(
            sc["fp"], sc["cp"], sc["demand"], sc["comp"], sc["storage"], sc["volume"], sc["elev"], sc["fp"]
        )

        ba, _ = buyer_model.predict(b_obs, deterministic=True)
        fa, _ = factory_model.predict(f_obs, deterministic=True)
        bra, _ = broker_model.predict(br_obs, deterministic=True)

        buyer_real.append(int(ba))
        factory_real.append(reserve_lookup[int(fa[0])])
        broker_real.append(signal_lookup[int(bra[0])])

    log("Buyer real-data diversity", PASS if len(set(buyer_real)) >= 2 else WARN, dict(Counter(buyer_real)))
    log("Factory real-data reserve diversity", PASS if len(set(factory_real)) >= 2 else WARN, dict(Counter(factory_real)))
    log("Broker real-data signal diversity", PASS if len(set(broker_real)) >= 2 else WARN, dict(Counter(broker_real)))

print("\n── Section 7: Buyer Monotonicity vs Improving Future Price ─────────────")

# Correct logic for current buyer action semantics:
# As future price improves, buyer should become LESS aggressive or stay same.
# So actions should be generally non-increasing.
cp = 1500.0
forecast_grid = [1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
buyer_line = []

for fp in forecast_grid:
    obs = buyer_obs_norm(
        cp, fp, demand=1, comp=1, elev=1, volume=10000, storage=5, broker_sig=0.0
    )
    action, _ = buyer_model.predict(obs, deterministic=True)
    buyer_line.append(int(action))

upward_violations = sum(
    1 for i in range(1, len(buyer_line))
    if buyer_line[i] > buyer_line[i - 1]
)

if upward_violations == 0:
    log(
        "Buyer monotonicity vs improving future price",
        PASS,
        f"Actions={buyer_line}",
    )
elif upward_violations <= 1:
    log(
        "Buyer monotonicity vs improving future price",
        WARN,
        f"Minor upward violation count={upward_violations} | Actions={buyer_line}",
    )
else:
    log(
        "Buyer monotonicity vs improving future price",
        FAIL,
        f"Upward violation count={upward_violations} | Actions={buyer_line}",
    )

print("\n── Section 8: Broker Monotonicity vs Momentum ──────────────────────────")

signal_lookup = [-1, 0, 1]
broker_line = []

for fp in forecast_grid:
    obs = broker_obs_norm(
        fp, cp, demand=1, comp=1, storage=5, volume=10000, elev=1, reserve_price=fp
    )
    a, _ = broker_model.predict(obs, deterministic=True)
    signal = signal_lookup[int(a[0])]
    broker_line.append(signal)

down_jumps = sum(1 for i in range(1, len(broker_line)) if broker_line[i] < broker_line[i - 1])

if down_jumps == 0:
    log("Broker monotonicity vs stronger upside", PASS, f"Signals={broker_line}")
elif down_jumps <= 2:
    log("Broker monotonicity vs stronger upside", WARN, f"Signals={broker_line}")
else:
    log("Broker monotonicity vs stronger upside", FAIL, f"Signals={broker_line}")

print("\n── Section 9: Factory Response to Stronger Market Conditions ───────────")

factory_line = []
for demand in [0, 1, 2]:
    obs = factory_obs_norm(
        fp=1700,
        cp=1500,
        demand=demand,
        comp=1,
        storage=5,
        volume=10000,
        elev=1,
        prod_cost=1380,
    )
    a, _ = factory_model.predict(obs, deterministic=True)
    reserve_factor = reserve_lookup[int(a[0])]
    factory_line.append(reserve_factor)

non_decreasing = all(factory_line[i] >= factory_line[i - 1] for i in range(1, len(factory_line)))
if non_decreasing:
    log("Factory reserve response vs higher demand", PASS, f"Reserve factors={factory_line}")
else:
    log("Factory reserve response vs higher demand", WARN, f"Reserve factors={factory_line}")

print("\n── Section 10: Full MAS Canonical Scenario Checks ──────────────────────")

try:
    mas = AuctionMAS(model_dir="models")

    scenarios = [
        {"name": "Bull market", "fp": 1800, "cp": 1400, "demand": 2, "comp": 0, "storage": 4, "vol": 10000, "pc": 1280, "elev": 1},
        {"name": "Bear market", "fp": 1200, "cp": 1600, "demand": 0, "comp": 2, "storage": 8, "vol": 10000, "pc": 1100, "elev": 1},
        {"name": "Flat market", "fp": 1500, "cp": 1500, "demand": 1, "comp": 1, "storage": 5, "vol": 10000, "pc": 1380, "elev": 1},
    ]

    for sc in scenarios:
        b_obs = buyer_obs_norm(
            sc["cp"], sc["fp"], sc["demand"], sc["comp"], sc["elev"], sc["vol"], sc["storage"], broker_sig=0.0
        )
        res = mas.run_one_round(
            buyer_model=buyer_model,
            buyer_obs=b_obs,
            forecast_price=sc["fp"],
            current_price_used=sc["cp"],
            lot_volume=sc["vol"],
            storage_cost_per_kg=sc["storage"],
            demand_level=sc["demand"],
            competition=sc["comp"],
            production_cost_per_unit=sc["pc"],
        )

        ok = (
            np.isfinite(float(res.reserve_price))
            and np.isfinite(float(res.bid_price))
            and np.isfinite(float(res.factory_profit))
        )

        if ok:
            log(
                f"MAS canonical: {sc['name']}",
                PASS,
                f"buyer_action={res.buyer_action}, broker_signal={res.broker_signal}, sold={res.sold}, factory_profit={res.factory_profit:,.2f}",
            )
        else:
            log(f"MAS canonical: {sc['name']}", FAIL)
except Exception as e:
    log("MAS canonical scenario checks", FAIL, str(e))

print("\n── Section 11: MAS Stress Test ─────────────────────────────────────────")

stress_ok = True
stress_rows = []
stress_failures = 0

try:
    mas = AuctionMAS(model_dir="models")

    sample_stress = real_df.sample(min(150, len(real_df)), random_state=77)

    for _, sc in sample_stress.iterrows():
        b_obs = buyer_obs_norm(
            sc["cp"], sc["fp"], sc["demand"], sc["comp"], sc["elev"], sc["volume"], sc["storage"], broker_sig=0.0
        )
        try:
            res = mas.run_one_round(
                buyer_model=buyer_model,
                buyer_obs=b_obs,
                forecast_price=sc["fp"],
                current_price_used=sc["cp"],
                lot_volume=sc["volume"],
                storage_cost_per_kg=sc["storage"],
                demand_level=sc["demand"],
                competition=sc["comp"],
                production_cost_per_unit=sc["prod_cost"],
            )

            stress_rows.append(
                {
                    "sold": bool(res.sold),
                    "factory_profit": float(res.factory_profit),
                    "broker_profit": float(res.broker_profit),
                }
            )
        except Exception:
            stress_ok = False
            stress_failures += 1

    if stress_ok:
        df_stress = pd.DataFrame(stress_rows)
        log(
            "MAS stress test (150 random rounds)",
            PASS,
            f"sold_rate={df_stress['sold'].mean()*100:.1f}% | "
            f"factory_profit_pos={(df_stress['factory_profit'] > 0).mean()*100:.1f}% | "
            f"broker_profit_pos={(df_stress['broker_profit'] > 0).mean()*100:.1f}%",
        )
    else:
        log("MAS stress test (150 random rounds)", FAIL, f"Failures={stress_failures}")
except Exception as e:
    log("MAS stress test (150 random rounds)", FAIL, str(e))

print("\n" + "=" * 72)
print("  VALIDATION SUMMARY")
print("=" * 72)

n_pass = sum(1 for _, s, _ in results if "PASS" in s)
n_warn = sum(1 for _, s, _ in results if "WARN" in s)
n_fail = sum(1 for _, s, _ in results if "FAIL" in s)
total = len(results)

print(f"\n  Total tests : {total}")
print(f"  ✅ PASS     : {n_pass}")
print(f"  ⚠️ WARN     : {n_warn}")
print(f"  ❌ FAIL     : {n_fail}")

if n_fail == 0 and n_warn == 0:
    print("\n  Strong validation result: all 27 checks passed.")
elif n_fail == 0:
    print("\n  Usable validation result: no hard failures, but warnings remain.")
else:
    print("\n  Release-blocking issues remain. Fix the failed items before claiming strong accuracy.")