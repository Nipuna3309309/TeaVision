"""
Roboflow Sync + Retrain Script
===============================
Downloads the latest labeled dataset from Roboflow,
retrains YOLOv8 locally, and registers the new model
in detection.py automatically.

Usage:
    python roboflow_sync.py                  # Download latest version + retrain
    python roboflow_sync.py --version 4      # Download a specific version
    python roboflow_sync.py --download-only  # Only download dataset, no training
    python roboflow_sync.py --epochs 200     # Custom epochs
"""

import os
import sys
import argparse
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
API_KEY = os.getenv("ROBOFLOW_API_KEY")

WORKSPACE  = os.getenv("ROBOFLOW_WORKSPACE", "nipuna-ivado")
PROJECT    = os.getenv("ROBOFLOW_PROJECT",   "tea-leaf-freshness-detection")

BASE_DIR   = Path(r"C:\Nipuna\TEST")
MODELS_DIR = BASE_DIR / "runs" / "detect"
DETECTION_PY = BASE_DIR / "presentation-app" / "backend" / "detection.py"


# ─────────────────────────────────────────────
# STEP 1 — Download latest dataset from Roboflow
# ─────────────────────────────────────────────

def download_dataset(version=None):
    if not API_KEY or API_KEY == "paste_your_new_key_here":
        print("[ERROR] No API key found. Add ROBOFLOW_API_KEY to your .env file.")
        sys.exit(1)

    try:
        from roboflow import Roboflow
    except ImportError:
        print("[ERROR] roboflow not installed. Run: pip install roboflow")
        sys.exit(1)

    print(f"\n[1] Connecting to Roboflow...")
    rf = Roboflow(api_key=API_KEY)
    project = rf.workspace(WORKSPACE).project(PROJECT)

    # List all versions and pick latest if not specified
    if version is None:
        versions = project.versions()
        version = max(v.version for v in versions)
        print(f"    Latest version: v{version}")
    else:
        print(f"    Using version: v{version}")

    print(f"    Downloading dataset (YOLOv8 format)...")
    dataset = project.version(version).download("yolov8", location=str(BASE_DIR / f"roboflow_v{version}"))

    print(f"    Downloaded to: {dataset.location}")
    return dataset, version


# ─────────────────────────────────────────────
# STEP 2 — Retrain YOLOv8 on the new dataset
# ─────────────────────────────────────────────

def retrain(dataset_location, version, epochs=150, imgsz=640, batch=8):
    try:
        import torch
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics not installed. Run: pip install ultralytics")
        sys.exit(1)

    data_yaml = Path(dataset_location) / "data.yaml"
    if not data_yaml.exists():
        print(f"[ERROR] data.yaml not found at {data_yaml}")
        sys.exit(1)

    device = 0 if torch.cuda.is_available() else "cpu"
    run_name = f"tea_roboflow_v{version}_{datetime.now().strftime('%Y%m%d_%H%M')}"

    print(f"\n[2] Starting training...")
    print(f"    Run name : {run_name}")
    print(f"    Data     : {data_yaml}")
    print(f"    Epochs   : {epochs}")
    print(f"    Device   : {'GPU' if device == 0 else 'CPU'}")

    model = YOLO("yolov8s.pt")
    model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project=str(MODELS_DIR),
        name=run_name,
        exist_ok=True,
        amp=True,
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        weight_decay=0.0005,
        box=10.0,
        cls=1.0,
        dfl=2.0,
        mosaic=0.7,
        close_mosaic=15,
        mixup=0.05,
        scale=0.3,
        fliplr=0.5,
        patience=30,
        save=True,
        save_period=25,
        plots=True,
        seed=42,
        workers=2,
    )

    best_pt = MODELS_DIR / run_name / "weights" / "best.pt"
    print(f"\n    Model saved: {best_pt}")
    return run_name, best_pt


# ─────────────────────────────────────────────
# STEP 3 — Register new model in detection.py
# ─────────────────────────────────────────────

def register_model_in_detection_py(run_name, best_pt, version):
    if not DETECTION_PY.exists():
        print(f"[WARN] detection.py not found at {DETECTION_PY}, skipping auto-register.")
        return

    new_key   = f"teanet_rf_v{version}"
    new_entry = (
        f"    '{new_key}': {{\n"
        f"        'name': 'TeaNet Roboflow v{version}',\n"
        f"        'description': 'Retrained on Roboflow v{version} labels - {run_name}',\n"
        f"        'path': r\"{best_pt}\",\n"
        f"        'tag': 'Latest',\n"
        f"    }},\n"
    )

    content = DETECTION_PY.read_text(encoding="utf-8")

    # Check if already registered
    if new_key in content:
        print(f"[3] Model '{new_key}' already in detection.py, skipping.")
        return

    # Insert as first entry in YOLO_MODELS dict
    marker = "YOLO_MODELS = {"
    if marker not in content:
        print(f"[WARN] Could not find YOLO_MODELS dict in detection.py, skipping auto-register.")
        return

    content = content.replace(
        marker,
        marker + "\n" + new_entry,
        1
    )

    # Also update default_yolo_key so new model is used first
    content = re.sub(
        r"(default_yolo_key\s*=\s*)['\"][\w]+['\"]",
        f"\\1'{new_key}'",
        content,
        count=1
    )

    DETECTION_PY.write_text(content, encoding="utf-8")
    print(f"[3] Registered '{new_key}' as first model in detection.py")
    print(f"    Path: {best_pt}")


# ─────────────────────────────────────────────
# ALSO: Download Roboflow-trained model directly
# (if you trained on Roboflow platform instead)
# ─────────────────────────────────────────────

def download_roboflow_model(version=None):
    """
    If you trained the model ON Roboflow (not locally),
    this downloads the trained weights directly.
    """
    if not API_KEY or API_KEY == "paste_your_new_key_here":
        print("[ERROR] No API key. Add ROBOFLOW_API_KEY to .env")
        sys.exit(1)

    try:
        from roboflow import Roboflow
    except ImportError:
        print("[ERROR] pip install roboflow")
        sys.exit(1)

    rf = Roboflow(api_key=API_KEY)
    project = rf.workspace(WORKSPACE).project(PROJECT)

    if version is None:
        versions = project.versions()
        version = max(v.version for v in versions)

    v = project.version(version)
    save_dir = BASE_DIR / "roboflow_models" / f"v{version}"
    save_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[Roboflow Model] Downloading trained model v{version}...")
    try:
        v.model.download("yolov8", location=str(save_dir))
        print(f"    Saved to: {save_dir}")

        # Find the .pt file
        pts = list(save_dir.glob("**/*.pt"))
        if pts:
            best_pt = pts[0]
            print(f"    Model weights: {best_pt}")
            register_model_in_detection_py(f"roboflow_v{version}", best_pt, version)
        else:
            print("    No .pt file found in download.")
    except Exception as e:
        print(f"    [WARN] Could not download trained model: {e}")
        print("    (This only works if you trained ON Roboflow platform.)")
        print("    Use --retrain flag to train locally instead.")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Sync Roboflow dataset and retrain")
    parser.add_argument("--version",       type=int, help="Roboflow dataset version (default: latest)")
    parser.add_argument("--epochs",        type=int, default=150)
    parser.add_argument("--imgsz",         type=int, default=640)
    parser.add_argument("--batch",         type=int, default=8)
    parser.add_argument("--download-only", action="store_true", help="Only download dataset, skip training")
    parser.add_argument("--model-only",    action="store_true", help="Download Roboflow-trained model directly (no local training)")
    args = parser.parse_args()

    os.chdir(BASE_DIR)

    if args.model_only:
        # Download model trained ON Roboflow platform
        download_roboflow_model(args.version)
        return

    # Download dataset
    dataset, version = download_dataset(args.version)

    if args.download_only:
        print(f"\nDataset downloaded. To train manually:\n  python train.py")
        print(f"  Update data.yaml to point to: {dataset.location}/data.yaml")
        return

    # Retrain locally
    run_name, best_pt = retrain(
        dataset_location=dataset.location,
        version=version,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
    )

    # Register in detection.py
    register_model_in_detection_py(run_name, best_pt, version)

    print("\n" + "="*55)
    print(" DONE")
    print("="*55)
    print(f"  New model : {best_pt}")
    print(f"  Registered in detection.py as 'teanet_rf_v{version}'")
    print(f"  Restart backend to use the new model.")
    print("="*55)


if __name__ == "__main__":
    main()
