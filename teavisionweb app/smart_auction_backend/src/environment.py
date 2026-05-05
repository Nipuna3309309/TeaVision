"""
src/environment.py — Buyer Agent (DQN) Environment v5
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np


class TeaAuctionEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, data_loader, budget=10_000_000, seed=42):
        super().__init__()
        self.dl = data_loader
        self.rng = np.random.RandomState(seed)

        self.initial_budget = float(budget)

        self.action_space = spaces.Discrete(4)
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(11,), dtype=np.float32
        )

        self.max_steps = 50

        self.user_demand = 1.0
        self.user_competition = 1.0
        self.is_festival = 0
        self.storage_cost_per_kg = 5.0
        self.current_lot_volume = 10_000.0
        self.user_current_price = None

        self._synthetic_momentum = None
        self._broker_signal = 0.0

        self._use_fixed = False
        self._fixed = {}

        self.budget = self.initial_budget
        self.steps_taken = 0
        self.held_steps = 0

        self.base_price = 1500.0
        self.forecast_price = 1500.0
        self.elev_code = 0

        self.reset()

    def set_user_params(self, demand, competition, festival,
                        storage_cost, volume, current_price=None):
        self.user_demand = float(demand)
        self.user_competition = float(competition)
        self.is_festival = int(festival)
        self.storage_cost_per_kg = float(storage_cost)
        self.current_lot_volume = float(volume)
        self._synthetic_momentum = None
        self._broker_signal = 0.0

        if current_price is None:
            self.user_current_price = None
        else:
            try:
                cp = float(current_price)
                self.user_current_price = cp if cp > 0 else None
            except Exception:
                self.user_current_price = None

        return

    def set_scenario(
        self,
        forecast_price: float,
        current_price: float,
        demand_level: int,
        competition: int,
        storage_cost_per_kg: float,
        lot_volume: float,
        elev_code: int,
        broker_signal: float = 0.0,
        use_fixed: bool = True,
    ):
        self._use_fixed = bool(use_fixed)
        self._fixed = dict(
            fp=float(forecast_price),
            cp=float(current_price),
            demand=int(demand_level),
            comp=int(competition),
            storage=float(storage_cost_per_kg),
            vol=float(lot_volume),
            elev=int(elev_code),
            broker=float(broker_signal),
        )

        self.user_demand = float(demand_level)
        self.user_competition = float(competition)
        self.storage_cost_per_kg = float(storage_cost_per_kg)
        self.current_lot_volume = float(lot_volume)
        self.user_current_price = float(current_price)
        self._broker_signal = float(broker_signal)
        self._synthetic_momentum = None

    def clear_fixed(self):
        self._use_fixed = False
        self._fixed = {}

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.budget = self.initial_budget
        self.steps_taken = 0
        self.held_steps = 0

        if self._use_fixed and self._fixed:
            self.base_price = float(self._fixed["cp"])
            self.forecast_price = float(self._fixed["fp"])
            self.elev_code = int(self._fixed["elev"])

            self.user_demand = float(self._fixed["demand"])
            self.user_competition = float(self._fixed["comp"])
            self.storage_cost_per_kg = float(self._fixed["storage"])
            self.current_lot_volume = float(self._fixed["vol"])
            self.user_current_price = float(self._fixed["cp"])
            self._broker_signal = float(self._fixed["broker"])
            self._synthetic_momentum = None
            return self._get_obs(), {}

        max_idx = max(1, len(self.dl.historical_data) - (self.max_steps + 10))
        idx = int(self.rng.randint(0, max_idx))
        base_price, pred, _, _, elev_code = self.dl.get_row_data(idx)

        self.base_price = float(base_price)
        self.forecast_price = float(pred)
        self.elev_code = int(elev_code)

        self.user_demand = float(self.rng.randint(0, 3))
        self.user_competition = float(self.rng.randint(0, 3))
        self.storage_cost_per_kg = float(self.rng.uniform(2.0, 12.0))
        self.current_lot_volume = float(self.rng.uniform(5000, 20000))
        self.user_current_price = None

        if self.rng.rand() < 0.5:
            self._synthetic_momentum = float(
                self.rng.choice([-1, 1]) * self.rng.uniform(100, 350)
            )
        else:
            self._synthetic_momentum = None

        mom = self._compute_momentum(self.base_price)
        self._broker_signal = self._sample_broker_signal(mom)

        return self._get_obs(), {}

    def _compute_momentum(self, current_used: float) -> float:
        if self._synthetic_momentum is not None:
            return float(self._synthetic_momentum)
        return float(self.forecast_price - float(current_used))

    def _sample_broker_signal(self, momentum: float) -> float:
        mom = float(momentum)
        if abs(mom) < 8:
            base = 0.0
        else:
            base = 1.0 if mom > 0 else -1.0

        r = self.rng.rand()
        if r < 0.15:
            return 0.0
        if r < 0.22:
            return -base
        return base

    def _get_obs(self):
        cp = float(self.user_current_price) if self.user_current_price is not None else float(self.base_price)
        has_cp = 1.0 if self.user_current_price is not None else 0.0

        mom = self._compute_momentum(cp)
        mom_norm = float(np.clip(mom / 300.0, -1.0, 1.0))

        return np.array([
            float(self.budget) / 10_000_000.0,
            cp / 5000.0,
            float(self.forecast_price) / 5000.0,
            float(self._broker_signal),
            mom_norm,
            float(self.user_demand) / 2.0,
            float(self.user_competition) / 2.0,
            float(self.elev_code) / 2.0,
            float(self.current_lot_volume) / 20000.0,
            float(self.storage_cost_per_kg) / 15.0,
            has_cp,
        ], dtype=np.float32)

    def step(self, action):
        cp = float(self.user_current_price) if self.user_current_price is not None else float(self.base_price)
        sc = float(self.storage_cost_per_kg)

        mom = self._compute_momentum(cp)
        mom_norm = float(np.clip(mom / 300.0, -1.0, 1.0))
        storage_norm = float(np.clip(sc / 10.0 - 0.5, -0.5, 0.5))

        self.held_steps += 1
        time_factor = float(np.clip(self.held_steps / (self.max_steps * 3.0), 0.0, 0.15))

        action = int(action)

        if action >= 2:
            reward = (
                - mom_norm * 1.0
                + storage_norm * 0.1
                + time_factor * 0.05
            )
        else:
            reward = (
                + mom_norm * 1.0
                - storage_norm * 0.1
                - time_factor * 0.05
            )

        reward = float(np.clip(reward, -1.0, 1.0))

        if self._synthetic_momentum is not None:
            self._synthetic_momentum *= 0.97

        drift = float(self.rng.normal(0, 4))
        self.base_price = max(1.0, float(self.base_price + drift))
        self.forecast_price = max(1.0, float(self.forecast_price + drift * 0.3))

        if not (self._use_fixed and self._fixed):
            self._broker_signal = self._sample_broker_signal(self._compute_momentum(self.base_price))

        self.steps_taken += 1
        done = self.steps_taken >= self.max_steps

        return self._get_obs(), reward, bool(done), False, {}