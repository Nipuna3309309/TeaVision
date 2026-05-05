"""
auction_simulator.py — Pure RL Multi-Agent System (Improved MAS Logic)

Changes:
- buyer action labels remain buyer-style but bid multipliers are more realistic
- held-back volume is no longer lost
- storage is charged on ALL volume still unsold after this round
- offered_volume is tracked separately for correct release factor
"""

from dataclasses import dataclass
from typing import Optional
import os
import numpy as np
from stable_baselines3 import PPO


@dataclass
class AuctionResult:
    reserve_price: float
    bid_price: float
    sold: bool
    offered_volume: float
    sold_volume: float
    unsold_volume: float
    commission_rate: float
    broker_signal: int
    broker_guidance: str
    factory_store_preference: bool
    factory_profit: float
    broker_profit: float
    buyer_action: int
    used_factory_rl: bool
    used_broker_rl: bool


# Buyer action -> bid aggressiveness
# More realistic than before:
# 0 = wait / no real bid
# 1 = cautious bid
# 2 = competitive bid
# 3 = very aggressive bid
_BUYER_BID_MULTIPLIERS = {
    0: 0.94,
    1: 0.99,
    2: 1.03,
    3: 1.07,
}


def buyer_action_to_bid_multiplier(action: int) -> float:
    return float(_BUYER_BID_MULTIPLIERS.get(int(action), 1.0))


def _fit_obs(model: PPO, obs: np.ndarray) -> np.ndarray:
    obs = np.asarray(obs, dtype=np.float32).reshape(-1)
    try:
        expected = int(model.policy.observation_space.shape[0])
    except Exception:
        return obs

    if obs.shape[0] == expected:
        return obs
    if obs.shape[0] > expected:
        return obs[:expected]

    return np.concatenate(
        [obs, np.zeros(expected - obs.shape[0], dtype=np.float32)]
    )


class AuctionMAS:
    FACTORY_RESERVE_FACTORS = np.array([0.95, 0.98, 1.02, 1.06], dtype=np.float32)
    FACTORY_RELEASE_FACTORS = np.array([0.70, 0.85, 1.00], dtype=np.float32)

    BROKER_SIGNALS = np.array([-1, 0, 1], dtype=np.int32)
    BROKER_COMMISSIONS = np.array([0.004, 0.008, 0.013, 0.020], dtype=np.float32)

    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.factory_rl: Optional[PPO] = None
        self.broker_rl: Optional[PPO] = None
        self._load_rl_models()

    def _load_rl_models(self):
        f_path = os.path.join(self.model_dir, "factory_agent_ppo.zip")
        b_path = os.path.join(self.model_dir, "broker_agent_ppo.zip")

        if os.path.exists(f_path):
            try:
                self.factory_rl = PPO.load(f_path)
                print(f"[MAS] ✅ Factory RL loaded: {f_path}")
            except Exception as e:
                print(f"[MAS] ❌ Factory RL load failed: {e}")
                self.factory_rl = None
        else:
            print(f"[MAS] ⚠️ Factory model not found at {f_path}")

        if os.path.exists(b_path):
            try:
                self.broker_rl = PPO.load(b_path)
                print(f"[MAS] ✅ Broker RL loaded: {b_path}")
            except Exception as e:
                print(f"[MAS] ❌ Broker RL load failed: {e}")
                self.broker_rl = None
        else:
            print(f"[MAS] ⚠️ Broker model not found at {b_path}")

    def _factory_obs(
        self, forecast, current, momentum, demand, competition,
        storage, volume, elev_code, production_cost
    ) -> np.ndarray:
        return np.array([
            forecast / 5000.0,
            current / 5000.0,
            momentum / 1000.0,
            float(demand) / 2.0,
            float(competition) / 2.0,
            storage / 15.0,
            volume / 25000.0,
            float(elev_code) / 2.0,
            production_cost / 5000.0,
            0.0,
        ], dtype=np.float32)

    def _broker_obs(
        self, forecast, current, momentum, demand, competition,
        storage, volume, elev_code, reserve_price
    ) -> np.ndarray:
        return np.array([
            forecast / 5000.0,
            current / 5000.0,
            momentum / 1000.0,
            float(demand) / 2.0,
            float(competition) / 2.0,
            storage / 15.0,
            volume / 25000.0,
            float(elev_code) / 2.0,
            reserve_price / 5000.0,
            0.0,
        ], dtype=np.float32)

    def run_one_round(
        self,
        buyer_model,
        buyer_obs: np.ndarray,
        forecast_price: float,
        current_price_used: float,
        lot_volume: float,
        storage_cost_per_kg: float,
        demand_level: int,
        competition: int,
        production_cost_per_unit: Optional[float] = None,
    ) -> AuctionResult:

        if self.factory_rl is None:
            raise RuntimeError("Factory RL model not found. Run `python train_all.py` first.")
        if self.broker_rl is None:
            raise RuntimeError("Broker RL model not found. Run `python train_all.py` first.")

        fp = float(forecast_price)
        cp = float(current_price_used)
        vol = float(lot_volume)
        sc = float(storage_cost_per_kg)
        mom = fp - cp

        elev_code = 0
        if len(buyer_obs) > 7:
            elev_code = int(np.clip(np.round(float(buyer_obs[7]) * 2.0), 0, 2))

        pc = (
            float(production_cost_per_unit)
            if production_cost_per_unit is not None
            else min(cp, fp) * 0.92
        )

        # STEP 1 — FACTORY RL
        f_obs = self._factory_obs(fp, cp, mom, demand_level, competition, sc, vol, elev_code, pc)
        f_obs = _fit_obs(self.factory_rl, f_obs)
        f_action, _ = self.factory_rl.predict(f_obs, deterministic=True)

        reserve_idx = int(np.clip(f_action[0], 0, len(self.FACTORY_RESERVE_FACTORS) - 1))
        vol_idx = int(np.clip(f_action[1], 0, len(self.FACTORY_RELEASE_FACTORS) - 1))

        reserve_factor = float(self.FACTORY_RESERVE_FACTORS[reserve_idx])
        release_factor = float(self.FACTORY_RELEASE_FACTORS[vol_idx])

        reserve_price = fp * reserve_factor
        offered_volume = vol * release_factor

        # STEP 2 — BROKER RL
        b_obs = self._broker_obs(fp, cp, mom, demand_level, competition, sc, vol, elev_code, reserve_price)
        b_obs = _fit_obs(self.broker_rl, b_obs)
        b_action, _ = self.broker_rl.predict(b_obs, deterministic=True)

        sig_idx = int(np.clip(b_action[0], 0, len(self.BROKER_SIGNALS) - 1))
        comm_idx = int(np.clip(b_action[1], 0, len(self.BROKER_COMMISSIONS) - 1))

        broker_signal = int(self.BROKER_SIGNALS[sig_idx])
        commission_rate = float(self.BROKER_COMMISSIONS[comm_idx])

        guidance_map = {
            -1: "Bearish: market likely falling",
            0: "Neutral: market direction unclear",
            1: "Bullish: market likely rising",
        }
        guidance = guidance_map[broker_signal]

        # STEP 3 — BUYER DQN
        obs = np.array(buyer_obs, dtype=np.float32).copy()
        if len(obs) >= 4:
            obs[3] = float(broker_signal)

        buyer_action, _ = buyer_model.predict(obs, deterministic=True)
        buyer_action = int(buyer_action)

        bid_mult = buyer_action_to_bid_multiplier(buyer_action)
        bid_price = fp * bid_mult

        # STEP 4 — CLEARING
        sold = bool(offered_volume > 0 and bid_price >= reserve_price)
        sold_volume = float(offered_volume if sold else 0.0)

        # unsold_volume = total volume still unsold after this round
        unsold_volume = float(max(0.0, vol - sold_volume))

        revenue = bid_price * sold_volume
        broker_profit = revenue * commission_rate

        # Storage applies to all remaining unsold volume after the round
        storage_bill = sc * unsold_volume
        factory_profit = (bid_price - pc) * sold_volume - broker_profit - storage_bill

        store_pref = sc <= 8.0 and mom > 0

        return AuctionResult(
            reserve_price=float(reserve_price),
            bid_price=float(bid_price),
            sold=sold,
            offered_volume=float(offered_volume),
            sold_volume=float(sold_volume),
            unsold_volume=float(unsold_volume),
            commission_rate=float(commission_rate),
            broker_signal=int(broker_signal),
            broker_guidance=str(guidance),
            factory_store_preference=bool(store_pref),
            factory_profit=float(factory_profit),
            broker_profit=float(broker_profit),
            buyer_action=int(buyer_action),
            used_factory_rl=True,
            used_broker_rl=True,
        )