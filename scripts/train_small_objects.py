"""
Training script optimized for small object detection (Damage_Spot)
Goal: reduce the tendency to predict overly large boxes.
"""

import os
os.chdir(r"C:\Nipuna\TEST")

import sys
import torch
from ultralytics import YOLO


def pick_device():
    # Ultralytics accepts device as int or str (0, "cpu", etc.)
    # Keep it explicit and safe.
    if torch.cuda.is_available():
        return 0
    return "cpu"


def train_for_small_objects():
    model = YOLO("yolov8s.pt")

    device = pick_device()
    print("=" * 60)
    print("Training optimized for SMALL OBJECT DETECTION")
    print(f"Device: {device} | torch.cuda.is_available(): {torch.cuda.is_available()}")
    print("Key changes:")
    print("  - YOLOv8s (better than v8n for tiny targets)")
    print("  - Larger imgsz for more pixels per object")
    print("  - Stronger box/DFL emphasis (tighter localization)")
    print("  - Disable mosaic near the end (improves final box tightness)")
    print("=" * 60)

    results = model.train(
        data="data.yaml",
        epochs=100,
        imgsz=1280,
        batch=4,
        name="tea_leaf_small_obj",
        device=device,

        # Optimizer
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,

        # Loss gains (localization)
        box=10.0,
        cls=1.0,
        dfl=2.0,

        # Augmentations (detection-safe)
        mosaic=0.7,          # 1.0 forever can make boxes sloppy
        close_mosaic=10,     # turn off mosaic in last N epochs (helps box tightness)
        mixup=0.05,          # keep light; too much can blur precise localization

        # IMPORTANT: copy_paste is for segmentation, not detection -> remove it
        # copy_paste=0.1,

        # Scale augmentation: keep moderate so you don't shrink tiny objects too much
        scale=0.3,
        translate=0.05,

        # Training settings
        patience=20,
        save=True,
        plots=True,

        workers=4,
        seed=42,
        single_cls=True,     # set True if you truly have 1 class (Damage_Spot)
    )

    print("=" * 60)
    print("Training complete!")
    print("Best model: runs/detect/tea_leaf_small_obj/weights/best.pt")
    print("=" * 60)
    return results


def train_medium_model():
    model = YOLO("yolov8m.pt")
    device = pick_device()

    print("=" * 60)
    print("Training with YOLOv8m (more accurate, slower)")
    print(f"Device: {device}")
    print("=" * 60)

    results = model.train(
        data="data.yaml",
        epochs=100,
        imgsz=1280,
        batch=2,
        name="tea_leaf_medium_model",
        device=device,

        box=10.0,
        dfl=2.0,
        mosaic=0.7,
        close_mosaic=10,
        mixup=0.05,
        scale=0.3,
        translate=0.05,

        patience=20,
        save=True,
        plots=True,
        workers=4,
        seed=42,
        single_cls=True,
    )
    return results


if __name__ == "__main__":
    # Allow quick "fast" mode: python train_small_objects.py fast
    if len(sys.argv) > 1 and sys.argv[1].lower() == "fast":
        def fast_train():
            # Lower-cost configuration for faster epochs
            if torch.cuda.is_available():
                torch.backends.cudnn.benchmark = True

            model = YOLO("yolov8n.pt")
            device = 0 if torch.cuda.is_available() else "cpu"

            # Dynamic workers and batch size
            cpu_count = os.cpu_count() or 1
            workers = max(1, min(8, cpu_count - 1))
            batch = 16 if torch.cuda.is_available() else 2

            print("=" * 60)
            print("Fast training mode: smaller model, fewer epochs, smaller imgsz")
            print(f"Device: {device} | workers: {workers} | batch: {batch}")
            print("=" * 60)

            results = model.train(
                data="data.yaml",
                epochs=30,
                imgsz=640,
                batch=batch,
                name="tea_leaf_fast",
                device=device,
                workers=workers,
                save=True,
                plots=False,
                seed=42,
            )
            return results

        fast_train()
    else:
        train_for_small_objects()
        # train_medium_model()
