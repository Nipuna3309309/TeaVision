"""
src/factory_env.py — Factory Agent (PPO) Environment
Improved version:
- Better aligns reserve strategy with market direction
- Makes release decision meaningful
- Charges storage on ALL unsold volume after the round
- Rewards profit + directional consistency + good reserve/release calibration
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces


class FactoryEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, dl, seed=42):
        super().__init__()
        self.dl = dl
        self.rng = np.random.RandomState(seed)

        # Keep action space same so integration stays simple
        self.reserve_factors = np.array([0.95, 0.98, 1.02, 1.06], dtype=np.float32)
        self.release_factors = np.array([0.70, 0.85, 1.00], dtype=np.float32)

        self.action_space = spaces.MultiDiscrete(
            [len(self.reserve_factors), len(self.release_factors)]
        )
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(10,), dtype=np.float32
        )

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
        self.production_cost = 1380.0

        self._use_fixed = False
        self._fixed = {}

    def set_scenario(self, forecast_price, current_price, demand_level,
                     competition, storage_cost_per_kg, lot_volume,
                     elev_code, production_cost_per_unit, use_fixed=True):
        self._use_fixed = bool(use_fixed)
        self._fixed = dict(
            forecast=float(forecast_price),
            current=float(current_price),
            demand=int(demand_level),
            competition=int(competition),
            storage=float(storage_cost_per_kg),
            volume=float(lot_volume),
            elev=int(elev_code),
            prod=float(production_cost_per_unit),
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
            self.production_cost = self._fixed["prod"]
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
            self.production_cost = float(self.current * self.rng.uniform(0.85, 0.97))

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
            self.production_cost / 5000.0,
            float(self.rng.uniform(-0.02, 0.02)),
        ], dtype=np.float32)

    def _target_reserve_factor(self) -> float:
        """
        Higher reserve when:
        - forecast > current (bullish)
        - demand high
        - competition low

        Lower reserve when:
        - forecast < current (bearish)
        - demand low
        - competition high
        - storage is expensive (want easier sale)
        """
        mom_norm = float(np.clip(self.momentum / 250.0, -1.0, 1.0))
        demand_term = 0.015 * (self.demand - 1)
        comp_term = -0.015 * (self.competition - 1)
        storage_term = -0.010 * np.clip((self.storage_cost - 6.0) / 6.0, -1.0, 1.0)

        target = 1.00 + 0.035 * mom_norm + demand_term + comp_term + storage_term
        return float(np.clip(target, 0.95, 1.06))

    def _target_release_factor(self) -> float:
        """
        Release more when:
        - market is bearish now
        - storage cost is high
        - competition is high

        Release less when:
        - market is bullish
        - storage cost is low
        """
        mom_norm = float(np.clip(self.momentum / 250.0, -1.0, 1.0))
        storage_norm = float(np.clip((self.storage_cost - 6.0) / 6.0, -1.0, 1.0))
        comp_norm = float(np.clip((self.competition - 1.0), -1.0, 1.0))

        target = 0.85 - (0.10 * mom_norm) + (0.07 * storage_norm) + (0.04 * comp_norm)
        return float(np.clip(target, 0.70, 1.00))

    def step(self, action):
        self.steps += 1
        done = self.steps >= self.max_steps

        reserve_idx = int(np.clip(action[0], 0, len(self.reserve_factors) - 1))
        vol_idx = int(np.clip(action[1], 0, len(self.release_factors) - 1))

        reserve_factor = float(self.reserve_factors[reserve_idx])
        release_factor = float(self.release_factors[vol_idx])

        reserve_price = self.forecast * reserve_factor
        offered_volume = self.volume * release_factor

        # Simulated market bid around forecast with directional pressure
        mom_norm = float(np.clip(self.momentum / 250.0, -1.0, 1.0))
        market_pressure = (
            1.0
            + 0.06 * mom_norm
            + 0.04 * (self.demand - 1)
            - 0.03 * (self.competition - 1)
        )
        bid_price = self.forecast * float(self.rng.normal(loc=market_pressure, scale=0.02))
        bid_price = max(1.0, bid_price)

        sold = bid_price >= reserve_price
        sold_volume = offered_volume if sold else 0.0

        # Important: total unsold after this round includes held-back volume too
        unsold_total = self.volume - sold_volume

        gross_profit = (bid_price - self.production_cost) * sold_volume
        storage_bill = self.storage_cost * unsold_total
        net_profit = gross_profit - storage_bill

        # Targets
        target_reserve = self._target_reserve_factor()
        target_release = self._target_release_factor()

        reserve_score = 1.0 - abs(reserve_factor - target_reserve) / (1.06 - 0.95)
        reserve_score = float(np.clip(reserve_score, -1.0, 1.0))

        release_score = 1.0 - abs(release_factor - target_release) / (1.00 - 0.70)
        release_score = float(np.clip(release_score, -1.0, 1.0))

        # Normalize profit safely
        profit_scale = max(self.volume * max(self.forecast * 0.12, 120.0), 1.0)
        profit_score = float(np.tanh(net_profit / profit_scale))

        # Directional consistency
        direction_bonus = 0.0
        if self.momentum >= 0:
            if reserve_factor >= 1.00:
                direction_bonus += 0.12
            else:
                direction_bonus -= 0.12

            if release_factor < 1.00:
                direction_bonus += 0.06
        else:
            if reserve_factor <= 1.00:
                direction_bonus += 0.12
            else:
                direction_bonus -= 0.12

            if release_factor >= 0.85:
                direction_bonus += 0.06

        clearance_bonus = 0.08 if sold else -0.08

        # Extra penalties to reduce bad policy collapse
        overpricing_penalty = 0.0
        if not sold and reserve_factor > target_reserve:
            overpricing_penalty -= 0.12

        underpricing_penalty = 0.0
        if sold and self.momentum > 120 and reserve_factor < 0.98:
            underpricing_penalty -= 0.08

        negative_margin_penalty = 0.0
        if sold and bid_price < self.production_cost:
            negative_margin_penalty -= 0.20

        reward = (
            0.42 * profit_score
            + 0.24 * reserve_score
            + 0.18 * release_score
            + clearance_bonus
            + direction_bonus
            + overpricing_penalty
            + underpricing_penalty
            + negative_margin_penalty
        )
        reward = float(np.clip(reward, -1.0, 1.0))

        drift = float(self.rng.normal(0, 5))
        self.current = max(1.0, self.current + drift)
        self.forecast = max(1.0, self.forecast + drift * 0.25)
        self.momentum = self.forecast - self.current

        return self._get_obs(), reward, bool(done), False, {
            "sold": bool(sold),
            "reserve_factor": reserve_factor,
            "release_factor": release_factor,
            "target_reserve": target_reserve,
            "target_release": target_release,
            "bid_price": bid_price,
            "reserve_price": reserve_price,
            "net_profit": net_profit,
            "unsold_total": unsold_total,
        }