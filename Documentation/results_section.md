## IV. RESULTS AND DISCUSSION

### A. Tea Leaf Freshness Classification

Ten machine learning models were evaluated on the binary freshness grading task using 148 images with 80/20 class-stratified splitting and 5-fold cross-validation. The results are summarized in TABLE I.

**TABLE I: ACCURACY WITH EXPERIMENTED MODELS**

| Model | Train Accuracy | Test Accuracy | F1 Score | CV Mean |
|---|---|---|---|---|
| **MLP Neural Network** | **100.00%** | **86.67%** | **86.85%** | **94.06% ± 4.28%** |
| AdaBoost | 94.92% | 83.33% | 83.47% | 88.12% ± 4.14% |
| Logistic Regression | 94.07% | 83.33% | 83.62% | 93.22% ± 7.73% |
| SVM (RBF) | 94.92% | 83.33% | 83.47% | 90.65% ± 5.59% |
| SVM (Linear) | 95.76% | 83.33% | 83.62% | 94.06% ± 6.26% |
| Naive Bayes | 90.68% | 83.33% | 83.62% | 88.95% ± 6.83% |
| Random Forest | 94.07% | 80.00% | 80.00% | 83.01% ± 7.09% |
| Gradient Boosting | 99.15% | 76.67% | 75.68% | 88.12% ± 6.70% |
| Decision Tree | 95.76% | 76.67% | 76.86% | 88.99% ± 4.26% |
| KNN | 90.68% | 76.67% | 77.06% | 84.78% ± 5.62% |

The MLP Neural Network achieved the highest test accuracy of 86.67% with a CV mean of 94.06%. Fig. 5 compares the training and test accuracy across all models. Naive Bayes exhibited the smallest train–test gap (7.35%), indicating the healthiest generalization, while Gradient Boosting showed the largest gap (22.48%) due to its high complexity relative to the limited dataset. Regularization was applied across all models to constrain overfitting, reducing training accuracy from 100% to the 90–96% range for most classifiers.

![Fig. 5: Training vs Test Accuracy Comparison](methodology_figures/Fig_ML_Train_vs_Test_Accuracy.png)

*Fig. 5. Training vs test accuracy comparison across all experimented models.*

### B. YOLOv8 Object Detection

The YOLOv8s detector was trained on 148 annotated images (augmented to 726) across seven TRI-defined classes for 13 epochs. The per-class detection performance is summarized in TABLE II.

**TABLE II: PER-CLASS DETECTION PERFORMANCE (YOLOv8s)**

| Class | AP@0.5 |
|---|---|
| Fresh_Bud_2 | 0.578 |
| Coarse_pluck | 0.553 |
| Old_Leaf | 0.431 |
| Damaged_Leaf | 0.213 |
| Fresh_Bud_1 | 0.154 |
| Damage_Spot | 0.018 |
| **All Classes (mAP@0.5)** | **0.325** |

The model achieved an overall mAP@0.5 of 0.325. Fresh_Bud_2 and Coarse_pluck attained the highest AP values, while Damage_Spot (AP 0.018) proved most challenging due to its small object size and limited annotation count. Fig. 6 shows the training vs validation loss over the training epochs, demonstrating steady convergence of the combined loss (box + classification + DFL) with the validation loss stabilizing after epoch 8. SAHI post-processing (512×512 slices, 0.3 overlap) improved small-object recall for underperforming classes.

![Fig. 6: Training vs Validation Loss](methodology_figures/Fig_Train_vs_Validation_Loss.png)

*Fig. 6. Training vs validation loss curves for YOLOv8s detector.*

### C. RAG Advisory Module

The retrieval pipeline was evaluated using BM25, dense (Sentence-BERT + FAISS), and hybrid (Reciprocal Rank Fusion) strategies over the 156-document TRI corpus (473 chunks). Results are presented in TABLE III.

**TABLE III: RAG RETRIEVAL PERFORMANCE**

| Method | Hit Rate@5 | MRR | nDCG@5 | Precision@1 | Recall@5 |
|---|---|---|---|---|---|
| BM25 | 1.00 | 1.00 | 0.98 | 1.00 | 1.00 |
| Dense | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| Hybrid (RRF) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

All three retrieval methods achieved near-perfect scores as shown in Fig. 7. The hybrid RRF strategy matched the dense retriever while providing additional robustness against vocabulary mismatch through the BM25 component. These results confirm reliable document retrieval for the tea advisory module.

![Fig. 7: RAG Evaluation](methodology_figures/Fig15_RAG_Evaluation.png)

*Fig. 7. Retrieval methods comparison and precision-recall trade-off.*
