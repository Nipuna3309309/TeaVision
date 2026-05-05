# IV. RESULTS AND DISCUSSION

## A. Binary Quality Classification

Ten ML models were evaluated on 25 ANOVA-selected features with session-based stratified splitting and 5-fold cross-validation. The results are summarized in TABLE I.

**TABLE I: ACCURACY WITH EXPERIMENTED MODELS**

| Model | Train Accuracy | Test Accuracy |
|---|---|---|
| **AdaBoost** | **100%** | **96.36%** |
| Random Forest | 100% | 94.55% |
| Gradient Boosting | 100% | 94.55% |
| Decision Tree | 100% | 94.55% |
| Logistic Regression | 92.27% | 90.91% |
| SVM (RBF) | 96.36% | 89.09% |
| SVM (Linear) | 93.64% | 85.45% |
| KNN | 92.73% | 85.45% |
| MLP Neural Network | 100% | 85.45% |
| Naive Bayes | 84.55% | 80.00% |

Fig. 1 presents the accuracy and F1 score comparison, confirming that ensemble methods outperform single-model classifiers. AdaBoost achieved the highest test accuracy (96.36%) and F1 score (96.31%), with CV mean of 96.36% ± 2.32%, indicating stable generalization.

[INSERT Fig. 1 HERE — methodology_figures/Fig03_Model_Comparison.png]

**Fig. 1.** Accuracy and F1 score comparison across ten classifiers.

On the test set (55 samples), 53 were correctly classified with 0 false positives and 2 false negatives. Feature importance analysis identified lab_a_mean (0.22), shape_mean_solidity (0.21), and lab_b_mean (0.15) as the strongest discriminators, confirming Lab chromaticity and leaf compactness as primary freshness indicators.

## B. YOLOv8 Object Detection

A YOLOv8s model was fine-tuned on 726 augmented images (7 classes, 1280×1280, 20 epochs, AdamW). Per-class results are shown in TABLE II.

**TABLE II: YOLOv8 PER-CLASS DETECTION RESULTS**

| Class | AP@0.5 |
|---|---|
| Fresh_Bud_2 | 0.578 |
| Coarse_pluck | 0.553 |
| Old_Leaf | 0.431 |
| Damaged_Leaf | 0.213 |
| Fresh_Bud_1 | 0.154 |
| Damage_Spot | 0.018 |
| **All Classes** | **0.325** |

Fig. 2 presents the training curves. Box loss decreased from 3.05 to 1.95 and classification loss from 6.0 to 3.95 over 20 epochs, with mAP@50 showing gradual improvement.

[INSERT Fig. 2 HERE — methodology_figures/Fig07_YOLOv8_Training_Curves.png]

**Fig. 2.** Training and validation loss curves over 20 epochs.

Background misclassification ranged from 68% to 100% across classes, attributed to the limited dataset (148 images) and CPU training constraints. SAHI integration (512×512, 0.3 overlap) improved small object recall without retraining.

## C. RAG Advisory System

A corpus of 156 documents (13 categories, 473 chunks) was embedded using Sentence-BERT (384-d). Hybrid retrieval (FAISS + BM25 + RRF) results are shown in TABLE III.

**TABLE III: RETRIEVAL METHOD COMPARISON**

| Method | MRR | Precision@1 | NDCG@5 |
|---|---|---|---|
| BM25 | 1.000 | 1.000 | 0.984 |
| Dense (FAISS) | 1.000 | 1.000 | 0.984 |
| **Hybrid (RRF)** | **1.000** | **1.000** | **1.000** |

The hybrid method achieved perfect scores (MRR = 1.0, NDCG@5 = 1.0), outperforming standalone methods (NDCG@5 = 0.984).
