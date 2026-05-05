"""
Classical ML Pipeline for Tea Leaf Quality Classification
Extracts 25 hand-crafted features from tea leaf images,
auto-labels into high_quality / medium_quality,
trains 10 ML models with 5-fold cross-validation.
"""

import os
import glob
import numpy as np
import cv2
import warnings
import json
from datetime import datetime
from scipy import stats
from skimage.feature import graycomatrix, graycoprops, local_binary_pattern
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)
from sklearn.ensemble import (
    AdaBoostClassifier, RandomForestClassifier, GradientBoostingClassifier
)
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.naive_bayes import GaussianNB

warnings.filterwarnings('ignore')

# ============================================================
# 1. COLLECT ORIGINAL IMAGES (exclude augmented copies)
# ============================================================
def get_original_images(base_dir):
    """Get original images only (no _hflip, _vflip, _rot* augmented copies)."""
    all_images = []
    for split in ['train', 'valid', 'test']:
        img_dir = os.path.join(base_dir, split, 'images')
        if not os.path.exists(img_dir):
            continue
        for f in os.listdir(img_dir):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                # Skip augmented copies
                if any(aug in f for aug in ['_hflip', '_vflip', '_rot90', '_rot180', '_rot270', '_flip']):
                    continue
                all_images.append(os.path.join(img_dir, f))
    return all_images


# ============================================================
# 2. FEATURE EXTRACTION (25 features)
# ============================================================
def extract_features(img_path):
    """Extract 25 hand-crafted features from a tea leaf image."""
    img = cv2.imread(img_path)
    if img is None:
        return None

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    img_lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # --- Segmentation (HSV-based) ---
    lower_green = np.array([20, 30, 30])
    upper_green = np.array([90, 255, 255])
    mask = cv2.inRange(img_hsv, lower_green, upper_green)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # If mask is too small, use full image
    if np.sum(mask > 0) < 500:
        mask = np.ones(gray.shape, dtype=np.uint8) * 255

    masked_rgb = cv2.bitwise_and(img_rgb, img_rgb, mask=mask)
    masked_hsv = cv2.bitwise_and(img_hsv, img_hsv, mask=mask)
    masked_lab = cv2.bitwise_and(img_lab, img_lab, mask=mask)

    # Get pixel values where mask is active
    mask_bool = mask > 0
    r_vals = img_rgb[:, :, 0][mask_bool].astype(float)
    g_vals = img_rgb[:, :, 1][mask_bool].astype(float)
    b_vals = img_rgb[:, :, 2][mask_bool].astype(float)
    h_vals = img_hsv[:, :, 0][mask_bool].astype(float)
    s_vals = img_hsv[:, :, 1][mask_bool].astype(float)
    v_vals = img_hsv[:, :, 2][mask_bool].astype(float)
    l_vals = img_lab[:, :, 0][mask_bool].astype(float)
    a_vals = img_lab[:, :, 1][mask_bool].astype(float)
    lab_b_vals = img_lab[:, :, 2][mask_bool].astype(float)

    if len(r_vals) == 0:
        return None

    features = {}

    # --- COLOUR FEATURES (11) ---
    features['rgb_R_median'] = np.median(r_vals)
    features['rgb_B_std'] = np.std(b_vals)
    features['hsv_H_std'] = np.std(h_vals)
    features['hsv_H_skew'] = stats.skew(h_vals) if len(h_vals) > 2 else 0
    features['hsv_S_std'] = np.std(s_vals)
    features['hsv_V_skew'] = stats.skew(v_vals) if len(v_vals) > 2 else 0
    features['lab_a_mean'] = np.mean(a_vals)
    features['lab_a_std'] = np.std(a_vals)
    features['lab_b_mean'] = np.mean(lab_b_vals)
    features['lab_b_std'] = np.std(lab_b_vals)
    features['green_ratio'] = np.mean(g_vals) / (np.mean(r_vals) + np.mean(g_vals) + np.mean(b_vals) + 1e-6)
    features['browning_ratio'] = np.mean(r_vals) / (np.mean(g_vals) + 1e-6)

    # --- TEXTURE FEATURES (3) ---
    gray_masked = cv2.bitwise_and(gray, gray, mask=mask)
    gray_resized = cv2.resize(gray_masked, (256, 256))
    # GLCM
    glcm = graycomatrix(gray_resized, distances=[1], angles=[0], levels=256, symmetric=True, normed=True)
    features['glcm_correlation'] = graycoprops(glcm, 'correlation')[0, 0]
    # LBP
    lbp = local_binary_pattern(gray_resized, P=8, R=1, method='uniform')
    features['lbp_std'] = np.std(lbp)
    lbp_hist, _ = np.histogram(lbp.ravel(), bins=10, density=True)
    features['lbp_energy'] = np.sum(lbp_hist ** 2)

    # --- SHAPE FEATURES (7) ---
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Filter small contours
    contours = [c for c in contours if cv2.contourArea(c) > 100]

    if len(contours) > 0:
        areas = [cv2.contourArea(c) for c in contours]
        features['shape_num_objects'] = len(contours)
        features['shape_mean_area'] = np.mean(areas)
        features['shape_std_area'] = np.std(areas) if len(areas) > 1 else 0

        eccentricities = []
        solidities = []
        aspect_ratios = []
        for c in contours:
            if len(c) >= 5:
                ellipse = cv2.fitEllipse(c)
                ma, MA = ellipse[1]  # (width, height) of the ellipse
                ecc = np.sqrt(1 - (min(ma, MA) / (max(ma, MA) + 1e-6)) ** 2)
                eccentricities.append(ecc)
            hull = cv2.convexHull(c)
            hull_area = cv2.contourArea(hull)
            solidities.append(cv2.contourArea(c) / (hull_area + 1e-6))
            x, y, w, h = cv2.boundingRect(c)
            aspect_ratios.append(w / (h + 1e-6))

        features['shape_mean_eccentricity'] = np.mean(eccentricities) if eccentricities else 0
        features['shape_mean_solidity'] = np.mean(solidities)
        features['shape_area_ratio'] = np.sum(areas) / (img.shape[0] * img.shape[1])
        features['shape_mean_aspect_ratio'] = np.mean(aspect_ratios)
    else:
        features['shape_num_objects'] = 0
        features['shape_mean_area'] = 0
        features['shape_std_area'] = 0
        features['shape_mean_eccentricity'] = 0
        features['shape_mean_solidity'] = 0
        features['shape_area_ratio'] = 0
        features['shape_mean_aspect_ratio'] = 0

    # --- QUALITY FEATURES (4) ---
    features['quality_brightness'] = np.mean(v_vals)
    features['quality_brightness_std'] = np.std(v_vals)
    features['quality_contrast'] = np.std(gray[mask_bool].astype(float))

    return features


# ============================================================
# 3. AUTO-LABELLING (composite scoring)
# ============================================================
def compute_quality_score(features):
    """
    Composite quality score: higher = better freshness.
    Uses greenness, low browning, solidity, brightness consistency, Lab chromaticity.
    """
    score = 0.0
    # Greenness (higher = fresher)
    score += features['green_ratio'] * 10
    # Low browning (invert: lower browning_ratio = better)
    score += max(0, 2.0 - features['browning_ratio']) * 3
    # Solidity (higher = more compact leaves)
    score += features['shape_mean_solidity'] * 3
    # Brightness consistency (lower std = more uniform)
    score += max(0, 100 - features['quality_brightness_std']) / 30
    # Lab_a (lower = greener, less red/brown)
    score += max(0, 140 - features['lab_a_mean']) / 20
    # Lab_b (moderate values preferred)
    score += max(0, 150 - abs(features['lab_b_mean'] - 128)) / 30
    return score


def auto_label_batch(all_features_list):
    """
    Label images using median-split on composite quality score.
    Top ~35% = high_quality, rest = medium_quality (matching ~34/66 class ratio).
    """
    scores = [compute_quality_score(f) for f in all_features_list]
    # Use 65th percentile as threshold (~35% high_quality)
    threshold = np.percentile(scores, 65)
    labels = ['high_quality' if s >= threshold else 'medium_quality' for s in scores]
    return labels, scores


# ============================================================
# 4. MAIN PIPELINE
# ============================================================
def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    print("=" * 60)
    print("TEA LEAF QUALITY CLASSIFICATION - ML PIPELINE")
    print("=" * 60)

    # Collect images
    images = get_original_images(base_dir)
    print(f"\nFound {len(images)} original images")

    # Extract features
    print("\nExtracting features...")
    all_features = []
    all_features_dicts = []
    valid_paths = []

    for i, img_path in enumerate(images):
        feat = extract_features(img_path)
        if feat is not None:
            all_features.append(list(feat.values()))
            all_features_dicts.append(feat)
            valid_paths.append(img_path)
            if (i + 1) % 20 == 0:
                print(f"  Processed {i + 1}/{len(images)}")

    # Auto-label using batch median-split
    all_labels, quality_scores = auto_label_batch(all_features_dicts)

    feature_names = list(extract_features(images[0]).keys())
    X = np.array(all_features)
    y = np.array(all_labels)

    print(f"\nTotal valid images: {len(X)}")
    print(f"Classes: high_quality={np.sum(y == 'high_quality')}, medium_quality={np.sum(y == 'medium_quality')}")

    # Train/test split (80/20 stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train: {len(X_train)}, Test: {len(X_test)}")

    # Standardize
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ============================================================
    # 5. TRAIN 10 MODELS
    # ============================================================
    models = {
        'AdaBoost': AdaBoostClassifier(
            n_estimators=20, learning_rate=0.3, random_state=42),
        'Random Forest': RandomForestClassifier(
            n_estimators=30, max_depth=3, min_samples_split=8,
            min_samples_leaf=5, max_features='sqrt', random_state=42),
        'Gradient Boosting': GradientBoostingClassifier(
            n_estimators=30, max_depth=2, learning_rate=0.1,
            subsample=0.7, min_samples_leaf=5, random_state=42),
        'Decision Tree': DecisionTreeClassifier(
            max_depth=3, min_samples_split=10, min_samples_leaf=5,
            random_state=42),
        'Logistic Regression': LogisticRegression(
            C=0.1, max_iter=1000, random_state=42),
        'SVM (RBF)': SVC(
            kernel='rbf', C=0.5, gamma='scale', random_state=42),
        'SVM (Linear)': SVC(
            kernel='linear', C=0.1, random_state=42),
        'KNN': KNeighborsClassifier(n_neighbors=9),
        'MLP Neural Network': MLPClassifier(
            hidden_layer_sizes=(32,), alpha=0.5,
            max_iter=1000, random_state=42),
        'Naive Bayes': GaussianNB()
    }

    print("\n" + "=" * 60)
    print("MODEL TRAINING & EVALUATION")
    print("=" * 60)

    results = []
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    for name, model in models.items():
        # Train
        model.fit(X_train_scaled, y_train)

        # Train accuracy
        train_acc = accuracy_score(y_train, model.predict(X_train_scaled))

        # Test predictions
        y_pred = model.predict(X_test_scaled)
        test_acc = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)

        # Cross-validation
        cv_scores = []
        for train_idx, val_idx in cv.split(X_train_scaled, y_train):
            clone_model = type(model)(**model.get_params())
            clone_model.fit(X_train_scaled[train_idx], y_train[train_idx])
            cv_scores.append(accuracy_score(y_train[val_idx], clone_model.predict(X_train_scaled[val_idx])))

        cv_mean = np.mean(cv_scores)
        cv_std = np.std(cv_scores)

        results.append({
            'Model': name,
            'Train Acc': f"{train_acc * 100:.2f}%",
            'Test Acc': f"{test_acc * 100:.2f}%",
            'Precision': f"{precision * 100:.2f}%",
            'Recall': f"{recall * 100:.2f}%",
            'F1 Score': f"{f1 * 100:.2f}%",
            'CV Mean': f"{cv_mean * 100:.2f}% ± {cv_std * 100:.2f}%",
            'train_acc_raw': train_acc,
            'test_acc_raw': test_acc
        })

        print(f"\n{name}:")
        print(f"  Train: {train_acc * 100:.2f}%  |  Test: {test_acc * 100:.2f}%  |  F1: {f1 * 100:.2f}%  |  CV: {cv_mean * 100:.2f}% ± {cv_std * 100:.2f}%")

    # Sort by test accuracy
    results.sort(key=lambda x: x['test_acc_raw'], reverse=True)

    # ============================================================
    # 6. PRINT RESULTS TABLE
    # ============================================================
    print("\n" + "=" * 60)
    print("TABLE I: ACCURACY WITH EXPERIMENTED MODELS")
    print("=" * 60)
    print(f"{'Model':<22} {'Train Acc':>12} {'Test Acc':>12} {'Precision':>12} {'Recall':>12} {'F1 Score':>12} {'CV Mean':>20}")
    print("-" * 110)
    for r in results:
        print(f"{r['Model']:<22} {r['Train Acc']:>12} {r['Test Acc']:>12} {r['Precision']:>12} {r['Recall']:>12} {r['F1 Score']:>12} {r['CV Mean']:>20}")

    # ============================================================
    # 7. BEST MODEL DETAILS
    # ============================================================
    best = results[0]
    print(f"\n{'=' * 60}")
    print(f"BEST MODEL: {best['Model']}")
    print(f"{'=' * 60}")

    # Re-train best model for detailed analysis
    best_model = models[best['Model']]
    y_pred_best = best_model.predict(X_test_scaled)
    print(f"\nClassification Report:")
    print(classification_report(y_test, y_pred_best))
    print(f"Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred_best, labels=['high_quality', 'medium_quality'])
    print(f"  high_quality    -> TP={cm[0][0]}, FN={cm[0][1]}")
    print(f"  medium_quality  -> FP={cm[1][0]}, TN={cm[1][1]}")

    # Feature importance (if available)
    if hasattr(best_model, 'feature_importances_'):
        importances = best_model.feature_importances_
        sorted_idx = np.argsort(importances)[::-1]
        print(f"\nTop 5 Features:")
        for i in range(min(5, len(sorted_idx))):
            idx = sorted_idx[i]
            print(f"  {feature_names[idx]}: {importances[idx]:.3f}")

    # Save results to JSON
    save_results = {
        'timestamp': datetime.now().isoformat(),
        'total_images': len(X),
        'train_size': len(X_train),
        'test_size': len(X_test),
        'class_distribution': {
            'high_quality': int(np.sum(y == 'high_quality')),
            'medium_quality': int(np.sum(y == 'medium_quality'))
        },
        'results': [{k: v for k, v in r.items() if not k.endswith('_raw')} for r in results]
    }
    with open(os.path.join(base_dir, 'ml_results.json'), 'w') as f:
        json.dump(save_results, f, indent=2)
    print(f"\nResults saved to ml_results.json")


if __name__ == '__main__':
    main()
