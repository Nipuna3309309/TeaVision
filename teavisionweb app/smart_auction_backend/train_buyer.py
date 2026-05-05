"""
train_buyer.py — Train Buyer Agent (DQN) v4
"""

import time
import os
import warnings
import logging
from tqdm import tqdm

warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
logging.getLogger("statsmodels").setLevel(logging.ERROR)

from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import BaseCallback, EvalCallback
from stable_baselines3.common.monitor import Monitor

from src.data_loader import DataLoader
from src.environment import TeaAuctionEnv


class Bar(BaseCallback):
    def __init__(self, n):
        super().__init__()
        self.n = n
        self.pbar = None

    def _on_training_start(self):
        self.pbar = tqdm(total=self.n, desc="Buyer DQN v4", unit="step", colour="blue")

    def _on_step(self):
        self.pbar.update(1)
        return True

    def _on_training_end(self):
        if self.pbar:
            self.pbar.close()


def main():
    print("=" * 55)
    print("  Training Buyer Agent (DQN) — v4 Synthetic Momentum")
    print("=" * 55)

    model_path = "models/buyer_agent_dqn.zip"
    os.makedirs("models", exist_ok=True)
    os.makedirs("logs/buyer", exist_ok=True)

    if os.path.exists(model_path):
        print("[WARN] Removing old buyer model.")
        os.remove(model_path)

    dl = DataLoader("data", "models")
    print("[INFO] Loading data...")
    dl.load_data()

    env = Monitor(TeaAuctionEnv(dl))
    assert env.observation_space.shape == (11,), f"Bad obs: {env.observation_space.shape}"
    print(f"[OK]  Obs: {env.observation_space.shape} | Actions: {env.action_space.n}")

    agent = DQN(
        "MlpPolicy",
        env,
        verbose=0,
        exploration_fraction=0.55,
        exploration_final_eps=0.10,
        learning_starts=20_000,
        buffer_size=300_000,
        learning_rate=2e-4,
        batch_size=512,
        gamma=0.99,
        train_freq=4,
        target_update_interval=2000,
        policy_kwargs=dict(net_arch=[256, 256, 128]),
    )

    TRAIN_STEPS = 600_000
    best_dir = "./models/buyer_best/"
    os.makedirs(best_dir, exist_ok=True)

    eval_env = Monitor(TeaAuctionEnv(dl))
    eval_cb = EvalCallback(
        eval_env,
        best_model_save_path=best_dir,
        log_path="./logs/buyer/",
        eval_freq=20_000,
        n_eval_episodes=30,
        deterministic=True,
        render=False,
        verbose=0,
    )

    print(f"[INFO] Training {TRAIN_STEPS:,} steps...")
    t0 = time.time()
    agent.learn(total_timesteps=TRAIN_STEPS, callback=[Bar(TRAIN_STEPS), eval_cb])
    dt = time.time() - t0
    print(f"[DONE] {dt:.0f}s ({dt/60:.1f} min)")

    best = os.path.join(best_dir, "best_model.zip")
    if os.path.exists(best):
        print("[INFO] Deploying best model.")
        if os.path.exists(model_path):
            os.remove(model_path)
        os.replace(best, model_path)
    else:
        agent.save(model_path)

    print(f"[SAVED] {model_path}\n")


if __name__ == "__main__":
    main()