from __future__ import annotations

import os
import traceback
import logging
from typing import Optional

from stable_baselines3 import DQN, PPO

from src.data_loader import DataLoader
from src.environment import TeaAuctionEnv
from src.factory_env import FactoryEnv
from src.broker_env import BrokerEnv
from src.auction_simulator import AuctionMAS

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


class AppState:
    def __init__(self):
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        self.data_dir = os.path.join(self.base_dir, "data")
        self.models_dir = os.path.join(self.base_dir, "models")

        self.data_loader: Optional[DataLoader] = None

        self.buyer_env: Optional[TeaAuctionEnv] = None
        self.factory_env: Optional[FactoryEnv] = None
        self.broker_env: Optional[BrokerEnv] = None

        self.buyer_model = None
        self.factory_model = None
        self.broker_model = None

        self.mas: Optional[AuctionMAS] = None

        self.last_error: Optional[str] = None
        self.initialized: bool = False

    def reset(self):
        self.data_loader = None

        self.buyer_env = None
        self.factory_env = None
        self.broker_env = None

        self.buyer_model = None
        self.factory_model = None
        self.broker_model = None

        self.mas = None

        self.last_error = None
        self.initialized = False

    def _require_file(self, path: str, label: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"{label} not found: {path}")

    def load_all(self):
        self.reset()

        try:
            logging.info("=" * 60)
            logging.info("Starting backend model/data initialization")
            logging.info(f"BASE_DIR   : {self.base_dir}")
            logging.info(f"DATA_DIR   : {self.data_dir}")
            logging.info(f"MODELS_DIR : {self.models_dir}")

            if not os.path.isdir(self.data_dir):
                raise FileNotFoundError(f"Data directory not found: {self.data_dir}")

            if not os.path.isdir(self.models_dir):
                raise FileNotFoundError(f"Models directory not found: {self.models_dir}")

            # --------------------------------------------------
            # Load tabular data + ARIMA access layer
            # --------------------------------------------------
            dl = DataLoader(
                data_dir=self.data_dir,
                model_dir=self.models_dir,
            )
            dl.load_data()
            self.data_loader = dl
            logging.info("[OK] Data loader initialized")

            # --------------------------------------------------
            # Create RL environments
            # --------------------------------------------------
            self.buyer_env = TeaAuctionEnv(dl)
            self.factory_env = FactoryEnv(dl)
            self.broker_env = BrokerEnv(dl)
            logging.info("[OK] RL environments created")

            # --------------------------------------------------
            # Load trained RL models
            # --------------------------------------------------
            buyer_model_path = os.path.join(self.models_dir, "buyer_agent_dqn.zip")
            factory_model_path = os.path.join(self.models_dir, "factory_agent_ppo.zip")
            broker_model_path = os.path.join(self.models_dir, "broker_agent_ppo.zip")

            self._require_file(buyer_model_path, "Buyer model")
            self._require_file(factory_model_path, "Factory model")
            self._require_file(broker_model_path, "Broker model")

            self.buyer_model = DQN.load(buyer_model_path)
            self.factory_model = PPO.load(factory_model_path)
            self.broker_model = PPO.load(broker_model_path)
            logging.info("[OK] RL models loaded")

            # attach envs for learning
            try:
                self.buyer_model.set_env(self.buyer_env)
            except Exception:
                pass

            try:
                self.factory_model.set_env(self.factory_env)
            except Exception:
                pass

            try:
                self.broker_model.set_env(self.broker_env)
            except Exception:
                pass

            # --------------------------------------------------
            # MAS orchestrator
            # --------------------------------------------------
            self.mas = AuctionMAS(model_dir=self.models_dir)

            # force MAS to use the exact same in-memory models as the app state
            self.mas.factory_rl = self.factory_model
            self.mas.broker_rl = self.broker_model

            if self.mas.factory_rl is None:
                raise RuntimeError("MAS factory RL model failed to load")
            if self.mas.broker_rl is None:
                raise RuntimeError("MAS broker RL model failed to load")

            logging.info("[OK] MAS initialized")
            logging.info("[OK] Initialization complete")
            logging.info("=" * 60)

            self.initialized = True
            self.last_error = None

        except Exception as e:
            self.last_error = f"{type(e).__name__}: {e}"
            logging.error("[INIT FAILED] %s", self.last_error)
            logging.error(traceback.format_exc())
            self.initialized = False
            raise

    def status(self):
        return {
            "initialized": self.initialized,
            "data_loader": self.data_loader is not None,
            "buyer_env": self.buyer_env is not None,
            "factory_env": self.factory_env is not None,
            "broker_env": self.broker_env is not None,
            "buyer_model": self.buyer_model is not None,
            "factory_model": self.factory_model is not None,
            "broker_model": self.broker_model is not None,
            "mas": self.mas is not None,
            "last_error": self.last_error,
            "base_dir": self.base_dir,
            "data_dir": self.data_dir,
            "models_dir": self.models_dir,
        }


state = AppState()