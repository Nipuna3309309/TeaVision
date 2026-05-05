"""
train_all.py

Train ALL 3 agents:
  1) Buyer (DQN)
  2) Factory (PPO)
  3) Broker (PPO)

Run:
  python train_all.py
"""

import time


def _run_stage(name: str, fn):
    print("\n" + "=" * 55)
    print(f"  TRAINING STAGE: {name}")
    print("=" * 55)
    t0 = time.time()
    fn()
    dt = time.time() - t0
    print("-" * 55)
    print(f"[DONE] {name} in {dt:.0f}s ({dt/60:.1f} min)")
    print("-" * 55)


def main():
    print("=" * 55)
    print("  TEA BROKER AI — Full Training Pipeline")
    print("  Training: Buyer + Factory + Broker")
    print("=" * 55)

    t_all = time.time()

    import train_buyer
    import train_factory
    import train_broker

    _run_stage("Buyer Agent (DQN)", train_buyer.main)
    _run_stage("Factory Agent (PPO)", train_factory.main)
    _run_stage("Broker Agent (PPO)", train_broker.main)

    total = time.time() - t_all
    print("\n" + "=" * 55)
    print(f"  ALL TRAINING DONE in {total:.0f}s ({total/60:.1f} min)")
    print()
    


if __name__ == "__main__":
    main()