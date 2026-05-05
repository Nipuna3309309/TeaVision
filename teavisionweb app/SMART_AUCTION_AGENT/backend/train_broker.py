"""
train_broker.py — Train Broker Agent (PPO)
"""

import time
import os
import warnings
import logging
from tqdm import tqdm

warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
logging.getLogger("stable_baselines3").setLevel(logging.WARNING)

from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import BaseCallback, EvalCallback

from src.data_loader import DataLoader
from src.broker_env import BrokerEnv


class Bar(BaseCallback):
    def __init__(self, n):
        super().__init__()
        self.n = n
        self.pbar = None

    def _on_training_start(self):
        self.pbar = tqdm(total=self.n, desc="Broker PPO", unit="step", colour="cyan")

    def _on_step(self):
        self.pbar.update(1)
        return True

    def _on_training_end(self):
        if self.pbar:
            self.pbar.close()


def main():
    print("=" * 55)
    print("  Training Broker Agent (PPO) — v3 Anti-Collapse")
    print("=" * 55)

    model_path = "models/broker_agent_ppo.zip"
    os.makedirs("models", exist_ok=True)
    os.makedirs("logs/broker", exist_ok=True)

    if os.path.exists(model_path):
        print("[WARN] Removing old broker model.")
        os.remove(model_path)

    dl = DataLoader("data", "models")
    print("[INFO] Loading data...")
    dl.load_data()

    env = Monitor(BrokerEnv(dl))
    assert env.observation_space.shape == (10,), f"Bad obs: {env.observation_space.shape}"
    print(f"[OK]  Obs: {env.observation_space.shape} | Actions: MultiDiscrete([3,4])")

    agent = PPO(
        "MlpPolicy",
        env,
        verbose=0,
        learning_rate=8e-5,
        n_steps=8192,
        batch_size=512,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.3,
        ent_coef=0.10,
        vf_coef=0.5,
        max_grad_norm=0.5,
        policy_kwargs=dict(net_arch=dict(pi=[256, 256, 128], vf=[256, 256, 128])),
    )

    TRAIN_STEPS = 600_000
    best_dir = "./models/broker_best/"
    os.makedirs(best_dir, exist_ok=True)

    eval_env = Monitor(BrokerEnv(dl, seed=123))
    eval_cb = EvalCallback(
        eval_env,
        best_model_save_path=best_dir,
        log_path="./logs/broker/",
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