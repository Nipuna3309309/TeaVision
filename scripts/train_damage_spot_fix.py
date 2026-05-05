"""
Training script optimized for Damage_Spot detection.
Key fixes:
1. single_cls=False (CRITICAL - enables multi-class detection)
2. Larger image size for tiny objects
3. Strong augmentation for small objects
4. Copy-paste augmentation to increase small object samples
"""

import os
os.chdir(r'C:\Nipuna\TEST')

from ultralytics import YOLO
import torch

# Check GPU availability
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"Using device: {device}")
if device == 'cpu':
    print("WARNING: Training on CPU will be very slow!")
    print("Consider using Google Colab or a GPU machine.")

# Load pretrained YOLOv8s (small model - good balance)
model = YOLO('yolov8s.pt')

print("="*60)
print("TRAINING WITH CORRECT SETTINGS FOR DAMAGE_SPOT DETECTION")
print("="*60)
print("Key fixes applied:")
print("  - single_cls=False (multi-class classification enabled)")
print("  - imgsz=1280 (large images for tiny objects)")
print("  - copy_paste=0.3 (augment small objects)")
print("  - mosaic=1.0 + close_mosaic=20 (better small object learning)")
print("="*60)

results = model.train(
    data='data.yaml',
    epochs=20,
    imgsz=1280,
    batch=4 if device == 'cpu' else 8,
    device=device,
    name='tea_leaf_damage_fix_20ep',

    # CRITICAL FIX - Enable multi-class detection
    single_cls=False,

    # Optimizer settings
    optimizer='AdamW',
    lr0=0.001,
    lrf=0.01,
    weight_decay=0.0005,

    # Loss weights - emphasize box precision for small objects
    box=10.0,  # Higher box loss weight
    cls=1.0,
    dfl=2.0,

    # Small object augmentations
    mosaic=1.0,          # Full mosaic for more context
    close_mosaic=20,     # Disable mosaic later for fine-tuning
    mixup=0.1,           # Some mixup
    copy_paste=0.3,      # Copy-paste augmentation (great for small objects!)

    # Standard augmentations
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
    degrees=10.0,        # Some rotation
    translate=0.1,
    scale=0.5,           # More scale variation
    fliplr=0.5,
    erasing=0.4,

    # Training settings
    patience=10,         # Early stopping patience
    save=True,
    plots=True,
    verbose=True,
    seed=42,
    deterministic=True,

    # Validation
    val=True,
    iou=0.5,             # Lower IoU threshold for small objects
    max_det=500,         # More detections allowed
)

print("="*60)
print("Training complete!")
print("="*60)
print(f"Best model saved at: runs/detect/tea_leaf_damage_fix/weights/best.pt")
print("\nTo test the model, run:")
print("  from ultralytics import YOLO")
print("  model = YOLO('runs/detect/tea_leaf_damage_fix/weights/best.pt')")
print("  results = model.predict('test/images', save=True, conf=0.25)")
