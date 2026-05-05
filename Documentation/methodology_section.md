# III. METHODOLOGY

This section presents the methodology adopted for Objective 1: Tea Leaf Freshness Grading. The approach follows a two-track pipeline — a classical machine learning pipeline using hand-crafted features for binary quality classification, and a YOLOv8-based deep learning pipeline for multi-class leaf component detection — supported by a RAG-based advisory system for domain-specific guidance.

---

## A. Data Collection and Mobile Capture

Tea leaf images were captured using the **TeaVision** mobile application, a custom-built Android app developed in Kotlin with Jetpack Compose. The app enforces five real-time quality gates during image capture to ensure data consistency: blur score (Laplacian variance >= 40), brightness (mean pixel value between 40 and 220), glare ratio (<= 5% of pixels), tilt angle (< 15 degrees from horizontal), and stability (< 0.5 m/s squared accelerometer reading). This sensor-guided approach reduced blur-related rejections from approximately 25% during unguided pilot captures to 8% after deployment.

A white background cloth was placed beneath the tea leaves to ensure clean segmentation, and a QR code of known dimensions served as a spatial calibration reference, yielding 80-150 pixels per cm at a 25-35 cm capture distance with an accuracy of plus or minus 2 mm.

A total of **275 original images** were collected across 66 capture sessions from mid-country Sri Lankan tea estates. All 275 labels were manually audited by domain experts for consistency. The overall image quality pass rate was 78.4%, with failures tending to cluster in poor capture conditions — for example, capturing in a shaded spot can cause both brightness and background failures simultaneously.

## B. Image Preprocessing and Segmentation

Each captured image underwent brightness normalization to correct for outdoor lighting shifts of approximately plus or minus 30 units on the 0-255 scale. The system employs **dual segmentation** to ensure device coverage: a TensorFlow Lite model (256x256 input) achieving 94.2% detection rate with 3.1% false positives on supported devices, and a colour-based HSV fallback achieving 82.7% detection rate with 8.5% false positives on older devices. Morphological post-processing (erosion followed by dilation) was applied to remove noise, reducing false positive rates by approximately 40%.

## C. Feature Extraction

From each segmented leaf image, **25 hand-crafted features** were extracted, selected from an initial pool of 56 candidates using SelectKBest with ANOVA F-test scoring. These features span four categories: colour features (11 features including rgb_R_median, hsv channel statistics, Lab colour space means, green_ratio, and browning_ratio), texture features (3 features: glcm_correlation, lbp_std, lbp_energy), shape features (7 features: shape_num_objects, shape_mean_area, shape_std_area, shape_mean_eccentricity, shape_mean_solidity, shape_area_ratio, shape_mean_aspect_ratio), and quality features (3 features: quality_brightness, quality_brightness_std, quality_contrast).

Correlation analysis revealed that Lab colour space components (lab_a_mean and lab_b_mean) exhibit strong positive correlation, while colour features and shape features show moderate negative correlations, confirming that these feature categories capture complementary information about leaf quality.

## D. Classical ML Pipeline — Binary Quality Classification

Images were automatically labelled into two quality classes — **high_quality** and **medium_quality** — using a composite scoring function, then manually audited. The dataset was split using **session-based stratification** (80/20 train/test) to prevent data leakage, as images from the same capture session share lighting and arrangement.

Ten classical machine learning models were trained and evaluated using 5-fold stratified cross-validation. The results are summarized in Table I.

**TABLE I: Comparison of Machine Learning Models for Tea Leaf Quality Classification**

| Model | Train Acc. | Test Acc. | Precision | Recall | F1 Score | CV Mean |
|---|---|---|---|---|---|---|
| **AdaBoost** | **100%** | **96.36%** | **96.56%** | **96.36%** | **96.31%** | **96.36%** |
| Random Forest | 100% | 94.55% | 94.54% | 94.55% | 94.51% | 94.09% |
| Gradient Boosting | 100% | 94.55% | 94.97% | 94.55% | 94.42% | 96.36% |
| Decision Tree | 100% | 94.55% | 94.97% | 94.55% | 94.42% | 95.45% |
| Logistic Regression | 92.27% | 90.91% | 91.74% | 90.91% | 91.04% | 89.09% |
| SVM (RBF) | 96.36% | 89.09% | 89.57% | 89.09% | 89.21% | 86.36% |
| SVM (Linear) | 93.64% | 85.45% | 86.90% | 85.45% | 85.72% | 90.45% |
| KNN | 92.73% | 85.45% | 85.29% | 85.45% | 85.25% | 86.36% |
| MLP Neural Network | 100% | 85.45% | 86.90% | 85.45% | 85.72% | 88.64% |
| Naive Bayes | 84.55% | 80.00% | 85.24% | 80.00% | 80.49% | 85.45% |

The comparative performance is visualized in Fig. 1.

![Fig. 1. Model accuracy and F1 score comparison across all ten classifiers.](methodology_figures/Fig03_Model_Comparison.png)

**Fig. 1.** Train/test accuracy comparison (left) and F1 score comparison (right) across all ten models. AdaBoost achieves the highest test accuracy (96.36%) and F1 score (96.31%). Ensemble methods consistently outperform single-model classifiers.

**AdaBoost** was selected as the best-performing model. On the held-out test set of 55 samples, it correctly classified 17 out of 19 high_quality samples and all 36 medium_quality samples, with only 2 false negatives and 0 false positives. Its cross-validation mean matched the test accuracy (96.36% with standard deviation of 2.32%), indicating stable generalization.

Feature importance analysis revealed that the most discriminative features are lab_a_mean (importance: 0.22), shape_mean_solidity (0.21), and lab_b_mean (0.15), indicating that Lab colour space chromaticity and leaf shape compactness are the strongest indicators of tea leaf quality. Shape-related features (shape_area_ratio: 0.11) and quality metrics (quality_brightness_std: 0.10) also contribute significantly.

## E. YOLOv8 Deep Learning Pipeline — Multi-Class Detection

For fine-grained leaf component detection, images were annotated using Roboflow with bounding boxes for seven classes: Fresh_Bud_1 (newly emerged single bud), Fresh_Bud_2 (two leaves and a bud — standard pluck), Old_Leaf (mature, darkened leaves), Damaged_Leaf (leaves with physical damage), Damage_Spot (localized disease or pest marks), Coarse_pluck (roughly plucked leaves exceeding standard size), and stems (exposed stem material).

The annotated dataset comprised 148 original images, augmented to 726 training images via Roboflow preprocessing, with 17 validation and 10 test images. The class distribution is shown in Fig. 2, with Fresh_Bud_2 (4,638 instances) and Old_Leaf (4,361) being the most frequent classes, while stems (48) is severely underrepresented.

![Fig. 2. Dataset class distribution and bounding box statistics for the YOLOv8 detection task.](methodology_figures/Fig06_Dataset_Label_Distribution.jpg)

**Fig. 2.** YOLOv8 dataset statistics. Top-left: class instance distribution across seven categories. Top-right: bounding box spatial overlay. Bottom-left: object centre distribution. Bottom-right: bounding box width vs. height scatter, with most objects clustered at small sizes.

A **YOLOv8s** (small) model pre-trained on COCO was fine-tuned with image size 1280x1280, batch size 16, for 20 epochs using the AdamW optimizer (lr=0.01) with early stopping patience of 10. Training was performed on CPU due to hardware constraints.

The model achieved an overall **mAP@0.5 of 0.325**. Per-class average precision varied significantly: Fresh_Bud_2 (0.578), Coarse_pluck (0.553), Old_Leaf (0.431), Damaged_Leaf (0.213), Fresh_Bud_1 (0.154), and Damage_Spot (0.018). The best overall F1 score of 0.29 was achieved at a confidence threshold of 0.109. The normalized confusion matrix revealed that a significant portion of ground truth objects were misclassified as background across all classes, indicating that the model struggles with detection due to the limited dataset size and training epochs. However, where objects are detected, Damaged_Leaf achieves 86% correct classification and Fresh_Bud_2 achieves 30%.

To improve detection of small leaf components, **Slicing Aided Hyper Inference (SAHI)** was integrated into the deployment pipeline. SAHI divides high-resolution images into overlapping tiles, runs inference on each tile independently, and merges predictions using Non-Maximum Suppression (NMS), enabling detection of smaller objects that would otherwise be missed in full-image inference.

## F. RAG-Based Advisory System

To complement automated grading with domain-specific guidance, a Retrieval-Augmented Generation (RAG) advisory system was built. A tea domain knowledge corpus of **156 documents** spanning 13 categories (cultivar, grading, disease, processing, regional practices, etc.) was curated from TRI publications, estate records, and tea science literature.

Documents were split into **473 chunks** (mean: 51 words) and embedded using **Sentence-BERT (all-MiniLM-L6-v2)**, producing 384-dimensional dense vectors. t-SNE visualization confirmed semantic clustering, with processing, disease, and cultivar chunks forming distinct groups in embedding space.

The system employs **hybrid retrieval** combining dense retrieval (FAISS index with cosine similarity), sparse retrieval (BM25 keyword matching), and Reciprocal Rank Fusion (RRF) with alpha = 0.5 weighting. Evaluation showed perfect retrieval performance: MRR = 1.0, Precision@1 = 1.0, Recall@5 = 1.0, and NDCG@5 = 1.0 for the hybrid method, marginally outperforming standalone BM25 (NDCG@5 = 0.984).

## G. Deployment

The complete system is deployed using a **Streamlit** web dashboard for YOLOv8 detection with SAHI integration, a **FastAPI** backend for the RAG advisory system, and the **TeaVision mobile app** for field data capture. The Streamlit interface accepts uploaded tea leaf images, runs SAHI-enhanced YOLOv8 inference, counts detected components per class, computes a freshness score based on the ratio of fresh to damaged/old components, and displays the grading result alongside RAG-generated advisory recommendations.

## H. Summary

| Component | Method | Key Metric |
|---|---|---|
| Mobile Capture | TeaVision app with 5 quality gates | 78.4% image pass rate |
| Segmentation | TF Lite + colour fallback | 94.2% detection rate |
| Feature Extraction | 25 features from 56 via ANOVA | 4 categories |
| Binary Classification | AdaBoost (best of 10 models) | **96.36% test accuracy** |
| Object Detection | YOLOv8s (7 classes, 20 epochs) | **32.5% mAP@0.5** |
| Small Object Detection | SAHI tiling | Improved recall |
| RAG Advisory | Sentence-BERT + FAISS + BM25 | **MRR = 1.0** |
