# PROMPT — ADD METHODOLOGY SECTION TO RESEARCH PAPER

You are an IEEE academic paper writer. Write the **Methodology** section (Section III) for a research paper titled "AI-Driven Tea Freshness Grading for Mid-Country Sri Lanka." Use ONLY the verified data below. Write in formal academic tone, IEEE conference format. Keep it concise — no filler, no repetition.

**Use only 2 figures in this section. Everything else must be described in text or tables.**

---

## FIGURE 1 — INSERT THIS IMAGE:
**File:** `methodology_figures/Fig03_Model_Comparison.png`
**What it shows:** A bar chart comparing train/test accuracy (left panel) and F1 scores (right panel) for 10 ML models. AdaBoost leads with 96.36% test accuracy.
**Caption to use:** "Fig. X. Comparison of train/test accuracy and F1 scores across ten machine learning classifiers. AdaBoost achieves the highest test accuracy (96.36%) and F1 score (96.31%)."
**Where to place:** After the 10-model comparison table in the classical ML subsection.

## FIGURE 2 — INSERT THIS IMAGE:
**File:** `methodology_figures/Fig06_Dataset_Label_Distribution.jpg`
**What it shows:** Four-panel plot — (top-left) bar chart of 7-class instance counts: Coarse_pluck 2214, Damage_Spot 3168, Damaged_Leaf 4332, Fresh_Bud_1 1200, Fresh_Bud_2 4638, Old_Leaf 4361, stems 48. (top-right) bounding box spatial overlay. (bottom-left) object centre xy scatter. (bottom-right) width vs height scatter showing most objects are small (<0.2 normalized).
**Caption to use:** "Fig. X. YOLOv8 dataset statistics showing class distribution, bounding box spatial overlay, object centre positions, and box dimension scatter."
**Where to place:** In the YOLOv8 dataset description subsection.

---

## ALL VERIFIED DATA — USE THESE EXACT NUMBERS

### DATA COLLECTION
- 275 original images, 66 capture sessions, mid-country Sri Lankan tea estates
- TeaVision mobile app (Kotlin, Jetpack Compose, CameraX)
- Quality gates: blur >= 40, brightness 40-220, glare <= 5%, tilt < 15 degrees, stability < 0.5 m/s^2
- Sensor-guided capture reduced blur rejections from 25% to 8%
- White background cloth + QR calibration (80-150 px/cm at 25-35 cm, accuracy +/- 2mm)
- Overall image quality pass rate: 78.4%
- All 275 labels manually audited by domain experts

### PREPROCESSING & SEGMENTATION
- Brightness normalization needed due to +/- 30 unit outdoor lighting shifts
- Dual segmentation: TF Lite model (94.2% detection, 3.1% FP) + colour-based HSV fallback (82.7% detection, 8.5% FP)
- Morphological post-processing (erosion + dilation) reduces FP by ~40%

### FEATURE EXTRACTION — 25 FEATURES FROM 56
- Selected using SelectKBest with ANOVA F-test
- Colour (11): rgb_R_median, rgb_B_std, hsv_H_std, hsv_H_skew, hsv_S_std, hsv_V_skew, lab_a_mean, lab_a_std, lab_b_mean, lab_b_std, green_ratio, browning_ratio
- Texture (3): glcm_correlation, lbp_std, lbp_energy
- Shape (7): shape_num_objects, shape_mean_area, shape_std_area, shape_mean_eccentricity, shape_mean_solidity, shape_area_ratio, shape_mean_aspect_ratio
- Quality (3): quality_brightness, quality_brightness_std, quality_contrast

### AUTO-LABELLING (2 CLASSES)
- high_quality: 94 images (34.2%) — fresh, young, good green colour
- medium_quality: 181 images (65.8%) — mix of fresh and mature
- Composite scoring: greenness, low browning, low yellowing, solidity, blur check, plant coverage
- All labels manually audited for consistency

### 10-MODEL COMPARISON — EXACT RESULTS (PUT THIS AS A TABLE)

| Model | Train Acc | Test Acc | Precision | Recall | F1 Score | CV Mean +/- Std |
|-------|-----------|----------|-----------|--------|----------|-----------------|
| AdaBoost | 100% | 96.36% | 96.56% | 96.36% | 96.31% | 96.36% +/- 2.32% |
| Random Forest | 100% | 94.55% | 94.54% | 94.55% | 94.51% | 94.09% +/- 5.10% |
| Gradient Boosting | 100% | 94.55% | 94.97% | 94.55% | 94.42% | 96.36% +/- 2.32% |
| Decision Tree | 100% | 94.55% | 94.97% | 94.55% | 94.42% | 95.45% +/- 2.49% |
| Logistic Regression | 92.27% | 90.91% | 91.74% | 90.91% | 91.04% | 89.09% +/- 4.85% |
| SVM (RBF) | 96.36% | 89.09% | 89.57% | 89.09% | 89.21% | 86.36% +/- 5.57% |
| SVM (Linear) | 93.64% | 85.45% | 86.90% | 85.45% | 85.72% | 90.45% +/- 5.82% |
| KNN | 92.73% | 85.45% | 85.29% | 85.45% | 85.25% | 86.36% +/- 5.57% |
| MLP Neural Network | 100% | 85.45% | 86.90% | 85.45% | 85.72% | 88.64% +/- 4.77% |
| Naive Bayes | 84.55% | 80.00% | 85.24% | 80.00% | 80.49% | 85.45% +/- 5.86% |

- Split: 80/20 train/test, session-based stratification
- 5-fold stratified cross-validation
- Feature standardization: StandardScaler (z-score)

### ADABOOST DETAILS (DESCRIBE IN TEXT, NO FIGURE)
- Confusion matrix: 17 TP, 2 FN, 0 FP, 36 TN (55 test samples)
- high_quality precision 100%, recall 89.47%
- medium_quality precision 94.74%, recall 100%
- Top features: lab_a_mean (0.22), shape_mean_solidity (0.21), lab_b_mean (0.15), shape_area_ratio (0.11), quality_brightness_std (0.10)
- CV mean = test accuracy (96.36%) confirms no overfitting

### YOLOv8 OBJECT DETECTION
- 7 classes: Fresh_Bud_1, Fresh_Bud_2, Old_Leaf, Damaged_Leaf, Damage_Spot, Coarse_pluck, stems
- 148 original images annotated in Roboflow, augmented to 726 train / 17 valid / 10 test
- Model: YOLOv8s, pre-trained on COCO, fine-tuned
- Image size: 1280, epochs: 20, batch: 16, optimizer: AdamW (lr=0.01), patience: 10
- Trained on CPU (hardware constraint)

### YOLOv8 RESULTS (DESCRIBE IN TEXT, NO FIGURE)
- Overall mAP@0.5: 0.325 (32.5%)
- Per-class AP: Fresh_Bud_2 (0.578), Coarse_pluck (0.553), Old_Leaf (0.431), Damaged_Leaf (0.213), Fresh_Bud_1 (0.154), Damage_Spot (0.018)
- Best F1: 0.29 at confidence threshold 0.109
- High background confusion across all classes (model misses many objects)
- SAHI integration: slice 512x512, overlap 0.3, improves small object detection

### RAG ADVISORY SYSTEM (DESCRIBE IN TEXT, NO FIGURE)
- 156 documents, 13 categories, 473 chunks (mean 51 words)
- Embedding: Sentence-BERT all-MiniLM-L6-v2, 384 dimensions
- FAISS flat L2 + BM25 sparse index
- Hybrid retrieval: Reciprocal Rank Fusion, alpha=0.5
- Results: MRR=1.0, Precision@1=1.0, Recall@5=1.0, NDCG@5=1.0
- Backend: FastAPI

### DEPLOYMENT
- Streamlit web dashboard (YOLOv8 + SAHI detection, grading)
- FastAPI backend (RAG advisory)
- TeaVision mobile app (field capture)

---

## WRITING INSTRUCTIONS

1. **Only 2 figures** — the model comparison chart and dataset distribution. Describe EVERYTHING else (confusion matrices, feature importances, PR curves, RAG metrics, training curves) as text paragraphs or tables.

2. **Structure the section as:**
   - A. Data Collection and Mobile Capture
   - B. Image Preprocessing and Segmentation
   - C. Feature Extraction
   - D. Classical ML Pipeline (with TABLE and FIGURE 1)
   - E. YOLOv8 Detection Pipeline (with FIGURE 2)
   - F. RAG Advisory System
   - G. Deployment
   - H. Summary table

3. **Keep it concise.** Each subsection should be 1-2 paragraphs max. No repeating the same information. Total length: 2-3 pages in IEEE format.

4. **Use IEEE formatting:** Roman numeral section headers, table numbering (TABLE I, TABLE II), figure numbering (Fig. 1, Fig. 2), formal academic language.

5. **Be honest about limitations inline** — mention the small dataset sizes, YOLOv8's modest performance, auto-labelling approach. Don't oversell.

6. **Mark where to insert figures** with: `[INSERT Fig. X HERE]` so the user knows exactly where to paste the image.
