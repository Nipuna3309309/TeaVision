"""
Generate 3 separate Train / Validation / Combined loss curve images
from the YOLOv8 training results CSV.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from scipy.ndimage import uniform_filter1d

# Use the augmented run (17 epochs, more data)
CSV_PATH = os.path.join(os.path.dirname(__file__),
                        'runs', 'detect', 'tea_leaf_augmented', 'results.csv')
OUT_DIR = os.path.join(os.path.dirname(__file__), 'methodology_figures')

# Read CSV - strip whitespace from column names
df = pd.read_csv(CSV_PATH)
df.columns = df.columns.str.strip()

epochs = df['epoch'].values

# Loss columns
train_box = df['train/box_loss'].values
train_cls = df['train/cls_loss'].values
train_dfl = df['train/dfl_loss'].values

val_box = df['val/box_loss'].values
val_cls = df['val/cls_loss'].values
val_dfl = df['val/dfl_loss'].values

# Total losses
train_total = train_box + train_cls + train_dfl
val_total = val_box + val_cls + val_dfl

# Shared style
plt.rcParams.update({
    'font.size': 12,
    'axes.labelsize': 13,
    'axes.titlesize': 14,
    'legend.fontsize': 11,
    'figure.dpi': 150,
})

COLORS = {
    'box': '#2196F3',    # blue
    'cls': '#F44336',    # red
    'dfl': '#4CAF50',    # green
    'train': '#1976D2',  # dark blue
    'val': '#E53935',    # dark red
}


def smooth_series(y, window=5):
    if len(y) < window:
        return y
    return uniform_filter1d(y, size=window)


# ====== PLOT 1: Training Loss ======
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(epochs, train_box, 'o-', color=COLORS['box'], label='Box Loss', linewidth=2, markersize=5)
ax.plot(epochs, train_cls, 's-', color=COLORS['cls'], label='Classification Loss', linewidth=2, markersize=5)
ax.plot(epochs, train_dfl, '^-', color=COLORS['dfl'], label='DFL Loss', linewidth=2, markersize=5)
ax.plot(epochs, train_total, 'D--', color='#FF9800', label='Total Loss', linewidth=2.5, markersize=5, alpha=0.8)
ax.set_xlabel('Epoch')
ax.set_ylabel('Loss')
ax.set_title('Training Loss Curves')
ax.legend(loc='upper right')
ax.grid(True, alpha=0.3)
ax.set_xlim(epochs[0] - 0.5, epochs[-1] + 0.5)
plt.tight_layout()
path1 = os.path.join(OUT_DIR, 'Fig_Training_Loss.png')
fig.savefig(path1, bbox_inches='tight')
plt.close(fig)
print(f"Saved: {path1}")


# ====== PLOT 2: Validation Loss ======
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(epochs, val_box, 'o-', color=COLORS['box'], label='Box Loss', linewidth=2, markersize=5)
ax.plot(epochs, val_cls, 's-', color=COLORS['cls'], label='Classification Loss', linewidth=2, markersize=5)
ax.plot(epochs, val_dfl, '^-', color=COLORS['dfl'], label='DFL Loss', linewidth=2, markersize=5)
ax.plot(epochs, val_total, 'D--', color='#FF9800', label='Total Loss', linewidth=2.5, markersize=5, alpha=0.8)
ax.set_xlabel('Epoch')
ax.set_ylabel('Loss')
ax.set_title('Validation Loss Curves')
ax.legend(loc='upper right')
ax.grid(True, alpha=0.3)
ax.set_xlim(epochs[0] - 0.5, epochs[-1] + 0.5)
plt.tight_layout()
path2 = os.path.join(OUT_DIR, 'Fig_Validation_Loss.png')
fig.savefig(path2, bbox_inches='tight')
plt.close(fig)
print(f"Saved: {path2}")


# ====== PLOT 3: Train vs Validation (combined total loss) ======
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(epochs, train_total, 'o-', color=COLORS['train'], label='Training Loss', linewidth=2.5, markersize=6)
ax.plot(epochs, val_total, 's-', color=COLORS['val'], label='Validation Loss', linewidth=2.5, markersize=6)

# Add smoothed trend lines
if len(epochs) >= 5:
    smooth_train = smooth_series(train_total, window=3)
    smooth_val = smooth_series(val_total, window=3)
    ax.plot(epochs, smooth_train, '--', color=COLORS['train'], alpha=0.4, linewidth=1.5)
    ax.plot(epochs, smooth_val, '--', color=COLORS['val'], alpha=0.4, linewidth=1.5)

ax.set_xlabel('Epoch')
ax.set_ylabel('Total Loss (Box + Cls + DFL)')
ax.set_title('Training vs Validation Loss')
ax.legend(loc='upper right')
ax.grid(True, alpha=0.3)
ax.set_xlim(epochs[0] - 0.5, epochs[-1] + 0.5)
plt.tight_layout()
path3 = os.path.join(OUT_DIR, 'Fig_Train_vs_Validation_Loss.png')
fig.savefig(path3, bbox_inches='tight')
plt.close(fig)
print(f"Saved: {path3}")


# ====== PLOT 4: IEEE-style YOLOv8 Training Summary ======
fig, axes = plt.subplots(2, 2, figsize=(7.8, 6.0), dpi=300)

def style_ax(ax, title, y_label):
    ax.set_title(title)
    ax.set_xlabel('Epoch')
    ax.set_ylabel(y_label)
    ax.grid(True, alpha=0.2, linestyle='-')
    ax.set_xlim(epochs[0] - 0.5, epochs[-1] + 0.5)

raw_alpha = 0.25
smooth_lw = 2.5

# (1) Train Total Loss
ax = axes[0, 0]
ax.plot(epochs, train_total, color=COLORS['train'], alpha=raw_alpha, linewidth=1.0, label='Raw')
ax.plot(epochs, smooth_series(train_total, 5), color=COLORS['train'], linewidth=smooth_lw, label='Smoothed (w=5)')
style_ax(ax, 'Train Total Loss', 'Loss')
ax.legend(frameon=False, fontsize=9)

# (2) Val Total Loss
ax = axes[0, 1]
ax.plot(epochs, val_total, color=COLORS['val'], alpha=raw_alpha, linewidth=1.0, label='Raw')
ax.plot(epochs, smooth_series(val_total, 5), color=COLORS['val'], linewidth=smooth_lw, label='Smoothed (w=5)')
style_ax(ax, 'Validation Total Loss', 'Loss')
ax.legend(frameon=False, fontsize=9)

# (3) Precision / Recall
ax = axes[1, 0]
prec = df['metrics/precision(B)'].values
rec = df['metrics/recall(B)'].values
ax.plot(epochs, prec, color='#5E35B1', alpha=raw_alpha, linewidth=1.0, label='Precision (raw)')
ax.plot(epochs, smooth_series(prec, 5), color='#5E35B1', linewidth=smooth_lw, label='Precision (smoothed)')
ax.plot(epochs, rec, color='#00897B', alpha=raw_alpha, linewidth=1.0, label='Recall (raw)')
ax.plot(epochs, smooth_series(rec, 5), color='#00897B', linewidth=smooth_lw, label='Recall (smoothed)')
style_ax(ax, 'Precision and Recall', 'Score')
ax.set_ylim(0, 1.02)
ax.legend(frameon=False, fontsize=8, ncol=2)

# (4) mAP50 / mAP50-95
ax = axes[1, 1]
map50 = df['metrics/mAP50(B)'].values
map5095 = df['metrics/mAP50-95(B)'].values
ax.plot(epochs, map50, color='#FB8C00', alpha=raw_alpha, linewidth=1.0, label='mAP50 (raw)')
ax.plot(epochs, smooth_series(map50, 5), color='#FB8C00', linewidth=smooth_lw, label='mAP50 (smoothed)')
ax.plot(epochs, map5095, color='#6D4C41', alpha=raw_alpha, linewidth=1.0, label='mAP50-95 (raw)')
ax.plot(epochs, smooth_series(map5095, 5), color='#6D4C41', linewidth=smooth_lw, label='mAP50-95 (smoothed)')
style_ax(ax, 'mAP Curves', 'Score')
ax.set_ylim(0, 1.02)
ax.legend(frameon=False, fontsize=8, ncol=2)

plt.tight_layout()
path4 = os.path.join(OUT_DIR, 'Fig07_YOLOv8_Training_Curves.png')
fig.savefig(path4, bbox_inches='tight')
plt.close(fig)
print(f"Saved: {path4}")

print("\nDone! Loss plots + IEEE-style YOLO summary saved to methodology_figures/")
