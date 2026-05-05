"""
Generate 3 accuracy plots for classical ML models from ml_results.json.
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'methodology_figures')

# Load results from JSON
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml_results.json')) as f:
    data = json.load(f)

models = [r['Model'] for r in data['results']]
train_acc = [float(r['Train Acc'].replace('%', '')) for r in data['results']]
test_acc = [float(r['Test Acc'].replace('%', '')) for r in data['results']]

plt.rcParams.update({
    'font.size': 11,
    'axes.labelsize': 13,
    'axes.titlesize': 14,
    'legend.fontsize': 11,
    'figure.dpi': 150,
})


# ====== PLOT 1: Training Accuracy ======
fig, ax = plt.subplots(figsize=(10, 6))
colors_train = ['#1565C0' if i == 0 else '#64B5F6' for i in range(len(models))]
bars = ax.barh(models[::-1], train_acc[::-1], color=colors_train[::-1], edgecolor='white', height=0.6)
for bar, val in zip(bars, train_acc[::-1]):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
            f'{val:.2f}%', va='center', ha='left', fontweight='bold', fontsize=10)
ax.set_xlabel('Accuracy (%)')
ax.set_title('Training Accuracy by Model')
ax.set_xlim(75, 108)
ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
path1 = os.path.join(OUT_DIR, 'Fig_ML_Training_Accuracy.png')
fig.savefig(path1, bbox_inches='tight')
plt.close(fig)
print(f"Saved: {path1}")


# ====== PLOT 2: Test Accuracy ======
fig, ax = plt.subplots(figsize=(10, 6))
colors_test = ['#C62828' if i == 0 else '#EF9A9A' for i in range(len(models))]
bars = ax.barh(models[::-1], test_acc[::-1], color=colors_test[::-1], edgecolor='white', height=0.6)
for bar, val in zip(bars, test_acc[::-1]):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
            f'{val:.2f}%', va='center', ha='left', fontweight='bold', fontsize=10)
ax.set_xlabel('Accuracy (%)')
ax.set_title('Test Accuracy by Model')
ax.set_xlim(65, 100)
ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
path2 = os.path.join(OUT_DIR, 'Fig_ML_Test_Accuracy.png')
fig.savefig(path2, bbox_inches='tight')
plt.close(fig)
print(f"Saved: {path2}")


# ====== PLOT 3: Train vs Test Accuracy (Grouped Bar Chart) ======
fig, ax = plt.subplots(figsize=(12, 6))
x = np.arange(len(models))
width = 0.35

bars1 = ax.bar(x - width/2, train_acc, width, label='Train Accuracy',
               color='#1976D2', edgecolor='white', zorder=3)
bars2 = ax.bar(x + width/2, test_acc, width, label='Test Accuracy',
               color='#E53935', edgecolor='white', zorder=3)

for bar in bars1:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            f'{bar.get_height():.1f}', ha='center', va='bottom', fontsize=8, color='#1976D2')
for bar in bars2:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            f'{bar.get_height():.1f}', ha='center', va='bottom', fontsize=8, color='#E53935')

ax.set_ylabel('Accuracy (%)')
ax.set_title('Training vs Test Accuracy Comparison')
ax.set_xticks(x)
ax.set_xticklabels(models, rotation=35, ha='right', fontsize=9)
ax.set_ylim(65, 108)
ax.legend(loc='lower left')
ax.grid(axis='y', alpha=0.3, zorder=0)
plt.tight_layout()
path3 = os.path.join(OUT_DIR, 'Fig_ML_Train_vs_Test_Accuracy.png')
fig.savefig(path3, bbox_inches='tight')
plt.close(fig)
print(f"Saved: {path3}")

print("\nDone! All 3 ML accuracy plots saved.")
