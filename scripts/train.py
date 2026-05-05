"""
Tea Leaf Detection - Unified Training Script
=============================================
Optimized for small object detection using YOLOv8s

Project: 25-26J-133 - AI-Driven Tea Quality and Production Improvements

Usage:
    python train.py                    # Full training (100 epochs, YOLOv8s)
    python train.py --fast             # Quick training (30 epochs, YOLOv8n)
    python train.py --resume           # Resume from last checkpoint
    python train.py --model yolov8m    # Use medium model
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Set working directory
os.chdir(r"C:\Nipuna\TEST")

import torch
from ultralytics import YOLO

# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG = {
    # Paths
    "data_yaml": "data.yaml",
    "project_dir": "runs/detect",

    # Model options
    "models": {
        "nano": "yolov8n.pt",      # Fastest, lowest accuracy
        "small": "yolov8s.pt",     # Best balance for tea detection
        "medium": "yolov8m.pt",    # More accurate, slower
        "large": "yolov8l.pt",     # High accuracy, slow
    },

    # Classes
    "classes": [
        "Coarse_pluck",
        "Damage_Spot",
        "Damaged_Leaf",
        "Fresh_Bud_1",
        "Fresh_Bud_2",
        "Old_Leaf",
        "stems"
    ],

    # Training presets (optimized for RTX 4060 8GB)
    "presets": {
        "fast": {
            "model": "small",
            "epochs": 150,
            "imgsz": 640,
            "batch": 8,
            "name": "tea_fast",
        },
        "standard": {
            "model": "small",
            "epochs": 150,
            "imgsz": 640,
            "batch": 8,
            "name": "tea_standard",
        },
        "quality": {
            "model": "medium",
            "epochs": 200,
            "imgsz": 640,
            "batch": 4,
            "name": "tea_quality",
        }
    }
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_device():
    """Get best available device"""
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"GPU: {gpu_name} ({gpu_memory:.1f} GB)")
        return 0
    print("No GPU available, using CPU")
    return "cpu"


def get_optimal_workers():
    """Get optimal number of workers (limited to avoid RAM issues)"""
    return 2  # Keep low to avoid RAM exhaustion on 16GB systems


def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_config(config):
    """Print training configuration"""
    print("\nTraining Configuration:")
    print("-" * 40)
    for key, value in config.items():
        print(f"  {key}: {value}")
    print("-" * 40)


# =============================================================================
# TRAINING FUNCTIONS
# =============================================================================

def train_model(
    preset="standard",
    model_type=None,
    epochs=None,
    imgsz=None,
    batch=None,
    resume=False,
    name=None,
    single_cls=False
):
    """
    Train YOLOv8 model for tea leaf detection

    Args:
        preset: Training preset ('fast', 'standard', 'quality')
        model_type: Override model type ('nano', 'small', 'medium', 'large')
        epochs: Override number of epochs
        imgsz: Override image size
        batch: Override batch size
        resume: Resume from last checkpoint
        name: Custom run name
        single_cls: Train as single class (for Damage_Spot only)
    """
    # Get preset configuration
    preset_config = CONFIG["presets"].get(preset, CONFIG["presets"]["standard"])

    # Override with arguments if provided
    model_key = model_type or preset_config["model"]
    model_path = CONFIG["models"].get(model_key, CONFIG["models"]["small"])

    train_epochs = epochs or preset_config["epochs"]
    train_imgsz = imgsz or preset_config["imgsz"]
    train_batch = batch or preset_config["batch"]
    run_name = name or f"{preset_config['name']}_{datetime.now().strftime('%Y%m%d_%H%M')}"

    # Get device and workers
    device = get_device()
    workers = get_optimal_workers()

    # Adjust batch size for CPU
    if device == "cpu":
        train_batch = min(train_batch, 4)

    print_header("Tea Leaf Detection Training")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Preset: {preset}")

    print_config({
        "Model": f"{model_key} ({model_path})",
        "Epochs": train_epochs,
        "Image Size": train_imgsz,
        "Batch Size": train_batch,
        "Device": device,
        "Workers": workers,
        "Run Name": run_name,
        "Single Class": single_cls,
        "Resume": resume,
    })

    # Load model
    if resume:
        last_model = f"runs/detect/{run_name}/weights/last.pt"
        if os.path.exists(last_model):
            print(f"\nResuming from: {last_model}")
            model = YOLO(last_model)
        else:
            print(f"\nNo checkpoint found, starting fresh with {model_path}")
            model = YOLO(model_path)
    else:
        model = YOLO(model_path)

    print(f"\nModel loaded: {model_path}")
    print(f"Classes: {len(CONFIG['classes'])}")
    for i, cls in enumerate(CONFIG['classes']):
        print(f"  {i}: {cls}")

    # Training configuration optimized for small objects
    print_header("Starting Training")

    results = model.train(
        # Data
        data=CONFIG["data_yaml"],

        # Training params
        epochs=train_epochs,
        imgsz=train_imgsz,
        batch=train_batch,
        device=device,
        workers=workers,

        # Run settings
        project=CONFIG["project_dir"],
        name=run_name,
        exist_ok=True,

        # Speed optimizations for GPU
        amp=True,            # Mixed precision (FP16) — 2x faster on RTX 4060
        deterministic=False, # Faster than deterministic mode

        # Optimizer (AdamW works well for detection)
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,

        # Loss weights (emphasis on box localization for small objects)
        box=10.0,    # Higher = tighter boxes
        cls=1.0,     # Classification weight
        dfl=2.0,     # Distribution focal loss

        # Augmentation (tuned for small object detection)
        mosaic=0.7,
        close_mosaic=15,     # Turn off mosaic in last N epochs
        mixup=0.05,
        copy_paste=0.0,      # Not for detection

        # Scale augmentation (don't shrink small objects too much)
        scale=0.3,
        translate=0.05,
        fliplr=0.5,
        flipud=0.0,

        # Training settings
        patience=30,         # Early stopping patience (higher for more epochs)
        save=True,
        save_period=25,      # Save every 25 epochs
        plots=True,

        # Single class option
        single_cls=single_cls,

        # Seed for reproducibility
        seed=42,
    )

    # Print results
    print_header("Training Complete")

    best_model = f"runs/detect/{run_name}/weights/best.pt"
    last_model = f"runs/detect/{run_name}/weights/last.pt"

    print(f"\nModels saved:")
    print(f"  Best: {best_model}")
    print(f"  Last: {last_model}")

    if os.path.exists(best_model):
        print(f"\nTo use this model in app.py, update MODEL_PATH to:")
        print(f'  MODEL_PATH = r"{os.path.abspath(best_model)}"')

    return results


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Train YOLOv8 for tea leaf detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python train.py                     # Standard training (YOLOv8s, 100 epochs)
  python train.py --fast              # Quick training (YOLOv8n, 30 epochs)
  python train.py --quality           # High quality (YOLOv8m, 150 epochs)
  python train.py --model small --epochs 50
  python train.py --resume --name tea_standard_20240105
        """
    )

    parser.add_argument("--fast", action="store_true",
                       help="Fast training preset (30 epochs, YOLOv8n)")
    parser.add_argument("--quality", action="store_true",
                       help="Quality training preset (150 epochs, YOLOv8m)")
    parser.add_argument("--model", choices=["nano", "small", "medium", "large"],
                       help="Model size to use")
    parser.add_argument("--epochs", type=int, help="Number of epochs")
    parser.add_argument("--imgsz", type=int, help="Image size")
    parser.add_argument("--batch", type=int, help="Batch size")
    parser.add_argument("--resume", action="store_true", help="Resume training")
    parser.add_argument("--name", type=str, help="Run name")
    parser.add_argument("--single-cls", action="store_true",
                       help="Train as single class (for damage detection only)")

    args = parser.parse_args()

    # Determine preset
    if args.fast:
        preset = "fast"
    elif args.quality:
        preset = "quality"
    else:
        preset = "standard"

    # Run training
    train_model(
        preset=preset,
        model_type=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        resume=args.resume,
        name=args.name,
        single_cls=args.single_cls,
    )


if __name__ == "__main__":
    main()
