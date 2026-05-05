import json
import os

# Read the ML model info from the backend JSON file
model_info_path = r'C:\Nipuna\TEST\presentation-app\backend\ml_models\model_info.json'
with open(model_info_path, 'r') as f:
    ml_data = json.load(f)

# Construct the Python source code for the ML Dataframe cell dynamically
ml_source = [
    "import pandas as pd\n",
    "import matplotlib.pyplot as plt\n\n",
    "# Classical ML & DL Models (Extracting exact data from backend)\n",
    "ml_data = [\n"
]

for key, data in ml_data.items():
    # Convert string details to an internal dictionary format for Pandas
    ml_source.append(f"    {{'Model': '{data['name']}', 'Train Accuracy (%)': {data['train_acc']}, 'Test Accuracy (%)': {data['test_acc']}, 'F1 Score (%)': {data['f1']}}},\n")

ml_source.append("]\n")
ml_source.append("ml_df = pd.DataFrame(ml_data).sort_values(by='Test Accuracy (%)', ascending=False).reset_index(drop=True)\n")
ml_source.append("display(ml_df.style.set_caption('Grade My Tea - Classification Models').format(precision=2))\n")

# Build the Jupyter Notebook JSON structure
notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# IT22154576 Model Accuracies\n",
                "This interactive notebook tracks the performance metrics for the **YOLOv8** object detection models and the **OpenCV + Classical ML** grading models utilized in the Tea Analysis System."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import pandas as pd\n",
                "import matplotlib.pyplot as plt\n\n",
                "# YOLOv8 Models (mAP50 Scores)\n",
                "yolo_data = {\n",
                "    'Detection Model': ['TeaNet Roboflow v4', 'TeaNet Plus (Estimated)', 'TeaNet Pro (Estimated)', 'TeaNet Micro (Estimated)', 'TeaNet V2'],\n",
                "    'mAP50 Score': [0.734, 0.710, 0.680, 0.650, 0.491],\n",
                "    'Focus': ['Ultimate Accuracy', 'Augmented Range', 'Damage Optimization', 'Small Object Specialty', 'Legacy Baseline']\n",
                "}\n",
                "yolo_df = pd.DataFrame(yolo_data)\n",
                "display(yolo_df.style.set_caption('Tea Detection - YOLOv8 Models').background_gradient(subset=['mAP50 Score'], cmap='Greens'))\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": ml_source
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Visualizing the ML Models Performance\n",
                "plt.figure(figsize=(14, 6))\n",
                "x = range(len(ml_df))\n",
                "bars = plt.bar(x, ml_df['Test Accuracy (%)'], color='#3F51B5')\n",
                "plt.xticks(x, ml_df['Model'], rotation=45, ha='right', fontsize=11)\n",
                "plt.ylabel('Test Accuracy (%)', fontsize=12)\n",
                "plt.title('ML Classification Models - Test Accuracy Comparison', fontsize=14, fontweight='bold')\n",
                "plt.ylim(0, 105)\n",
                "plt.grid(axis='y', linestyle='--', alpha=0.7)\n\n",
                "for bar in bars:\n",
                "    yval = bar.get_height()\n",
                "    plt.text(bar.get_x() + bar.get_width()/2, yval + 1.5, f'{yval}%', ha='center', va='bottom', fontweight='bold')\n",
                "plt.tight_layout()\n",
                "plt.show()\n"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.8.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

# Save as .ipynb file
output_path = r'C:\Nipuna\TEST\model_accuracies.ipynb'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=2)

print(f"Jupyter Notebook generated successfully at: {output_path}")
