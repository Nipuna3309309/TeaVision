"""
src/broker_env.py — Broker Agent (PPO) Environment v5
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces


class BrokerEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, dl, seed=42):
        super().__init__()
        self.dl = dl
        self.rng = np.random.RandomState(seed)

        self.signals = np.array([-1, 0, 1], dtype=np.int32)
        self.commissions = np.array([0.004, 0.008, 0.013, 0.020], dtype=np.float32)

        self.action_space = spaces.MultiDiscrete([len(self.signals), len(self.commissions)])
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(10,), dtype=np.float32)

        self.max_steps = 64
        self.steps = 0

        self.forecast = 1500.0
        self.current = 1500.0
        self.momentum = 0.0
        self.demand = 1
        self.competition = 1
        self.storage_cost = 5.0
        self.volume = 10000.0
        self.elev_code = 0
        self.reserve_price = 1530.0

        self._use_fixed = False
        self._fixed = {}

    def set_scenario(self, forecast_price, current_price, demand_level,
                     competition, storage_cost_per_kg, lot_volume,
                     elev_code, reserve_price=None, use_fixed=True):
        self._use_fixed = bool(use_fixed)
        self._fixed = dict(
            forecast=float(forecast_price),
            current=float(current_price),
            demand=int(demand_level),
            competition=int(competition),
            storage=float(storage_cost_per_kg),
            volume=float(lot_volume),
            elev=int(elev_code),
            reserve=float(reserve_price) if reserve_price is not None else float(forecast_price),
        )

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.steps = 0

        if self._use_fixed and self._fixed:
            self.forecast = self._fixed["forecast"]
            self.current = self._fixed["current"]
            self.demand = self._fixed["demand"]
            self.competition = self._fixed["competition"]
            self.storage_cost = self._fixed["storage"]
            self.volume = self._fixed["volume"]
            self.elev_code = self._fixed["elev"]
            self.reserve_price = self._fixed["reserve"]
        else:
            idx = self.rng.randint(0, max(1, len(self.dl.historical_data)))
            base_price, pred, _, _, elev = self.dl.get_row_data(idx)

            self.current = float(base_price)
            self.forecast = float(pred)
            self.demand = int(self.rng.randint(0, 3))
            self.competition = int(self.rng.randint(0, 3))
            self.storage_cost = float(self.rng.uniform(2.0, 12.0))
            self.volume = float(self.rng.uniform(5000, 25000))
            self.elev_code = int(elev)
            self.reserve_price = self.forecast * float(self.rng.uniform(0.97, 1.06))

        self.momentum = self.forecast - self.current
        return self._get_obs(), {}

    def _get_obs(self):
        return np.array([
            self.forecast / 5000.0,
            self.current / 5000.0,
            self.momentum / 1000.0,
            float(self.demand) / 2.0,
            float(self.competition) / 2.0,
            self.storage_cost / 15.0,
            self.volume / 25000.0,
            float(self.elev_code) / 2.0,
            self.reserve_price / 5000.0,
            float(self.rng.uniform(-0.05, 0.05)),
        ], dtype=np.float32)

    def step(self, action):
        self.steps += 1
        done = self.steps >= self.max_steps

        sig_idx = int(np.clip(action[0], 0, len(self.signals) - 1))
        comm_idx = int(np.clip(action[1], 0, len(self.commissions) - 1))

        signal = int(self.signals[sig_idx])
        commission = float(self.commissions[comm_idx])

        mom_norm = float(np.clip(self.momentum / 150.0, -1.0, 1.0))
        signal_accuracy = float(signal) * mom_norm

        d = float(self.demand - 1)
        c = float(self.competition - 1)
        vol = abs(mom_norm)

        target_pct = 1.0 + 0.35 * d - 0.25 * c + 0.20 * vol
        target_pct = float(np.clip(target_pct, 0.6, 1.6))

        comm_pct = commission * 100.0
        comm_align = 1.0 - abs(comm_pct - target_pct) / 1.0
        comm_align = float(np.clip(comm_align, -1.0, 1.0))

        extreme_penalty = -0.20 if comm_idx in [0, 3] else 0.0

        signal_lift = signal * 0.006
        market_pressure = (
            1.0
            + (self.demand - 1) * 0.04
            - (self.competition - 1) * 0.025
            + signal_lift
        )

        bid_price = self.forecast * float(self.rng.normal(loc=market_pressure, scale=0.03))
        bid_price = max(1.0, bid_price)
        sold = bid_price >= self.reserve_price

        sold_volume = self.volume * 0.9 if sold else 0.0
        commission_earned = commission * bid_price * sold_volume if sold else 0.0

        max_comm = 0.02 * self.forecast * (self.volume * 0.9)
        earned_norm = float(np.clip(commission_earned / max(max_comm, 1.0), 0.0, 1.0))

        accuracy_reward = 0.65 * signal_accuracy
        commission_reward = 0.25 * (comm_align + extreme_penalty)
        earned_reward = 0.07 * earned_norm
        clearance_bonus = 0.03 * (1.0 if sold else -1.0)

        reward = float(np.clip(
            accuracy_reward + commission_reward + earned_reward + clearance_bonus,
            -1.0, 1.0
        ))

        drift = float(self.rng.normal(0, 5))
        self.current = max(1.0, self.current + drift)
        self.forecast = max(1.0, self.forecast + drift * 0.3)
        self.momentum = self.forecast - self.current

        return self._get_obs(), reward, bool(done), False, {
            "sold": sold,
            "commission_earned": commission_earned,
            "signal_accuracy": signal_accuracy,
            "target_pct": target_pct,
            "comm_pct": comm_pct,
            "comm_align": comm_align,
        }