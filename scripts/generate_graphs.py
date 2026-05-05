import matplotlib.pyplot as plt
import numpy as np

# 1. Plot YOLO Models Performance
yolo_models = ['TeaNet Roboflow v4', 'TeaNet V2', 'TeaNet Pro\n(Estimated)', 'TeaNet Micro\n(Estimated)', 'TeaNet Plus\n(Estimated)']
yolo_map50 = [0.734, 0.491, 0.680, 0.650, 0.710]

plt.figure(figsize=(10, 6))
bars = plt.bar(yolo_models, yolo_map50, color=['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#00BCD4'])

plt.title('YOLOv8 Detection Models Performance (mAP50)', fontsize=14)
plt.ylabel('mAP50 Score', fontsize=12)
plt.ylim(0, 1.0)
plt.grid(axis='y', linestyle='--', alpha=0.7)

for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, yval + 0.02, f'{yval:.3f}', ha='center', va='bottom', fontweight='bold')

plt.tight_layout()
plt.savefig('yolo_performance.png', dpi=300)
plt.close()

# 2. Plot ML/DL Models Performance
import json
import os

model_info_path = r'C:\Nipuna\TEST\presentation-app\backend\ml_models\model_info.json'
with open(model_info_path, 'r') as f:
    model_data = json.load(f)

ml_models = []
test_acc = []
f1_scores = []

for key, data in model_data.items():
    if len(ml_models) < 10:  # Take top 10 models
        ml_models.append(data['name'].replace(' ', '\n'))
        test_acc.append(data['test_acc'])
        f1_scores.append(data['f1'])

x = np.arange(len(ml_models))
width = 0.35

plt.figure(figsize=(14, 7))
rects1 = plt.bar(x - width/2, test_acc, width, label='Test Accuracy (%)', color='#3F51B5')
rects2 = plt.bar(x + width/2, f1_scores, width, label='F1 Score (%)', color='#E91E63')

plt.title('Grade My Tea - Classification Models Performance', fontsize=16)
plt.ylabel('Score (%)', fontsize=12)
plt.xticks(x, ml_models, rotation=45, ha='right')
plt.ylim(0, 110)
plt.legend()
plt.grid(axis='y', linestyle='--', alpha=0.7)

def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        plt.annotate(f'{height:.1f}',
                     xy=(rect.get_x() + rect.get_width() / 2, height),
                     xytext=(0, 3),  # 3 points vertical offset
                     textcoords="offset points",
                     ha='center', va='bottom', rotation=90, fontsize=9)

autolabel(rects1)
autolabel(rects2)

plt.tight_layout()
plt.savefig('ml_dl_performance.png', dpi=300)
plt.close()

print("Graphs generated successfully!")
