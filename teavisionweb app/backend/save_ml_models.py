"""
Train and save all 10 classical ML models + scaler as .pkl files
Run this once before starting the backend.
"""

import os
import sys
import pickle
import numpy as np
import cv2
import warnings
import json
from scipy import stats
from skimage.feature import graycomatrix, graycoprops, local_binary_pattern
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score
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

BASE_DIR = r"C:\Nipuna\TEST"
SAVE_DIR = os.path.join(os.path.dirname(__file__), "ml_models")


def get_original_images(base_dir):
    all_images = []
    for split in ['train', 'valid', 'test']:
        img_dir = os.path.join(base_dir, split, 'images')
        if not os.path.exists(img_dir):
            continue
        for f in os.listdir(img_dir):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                if any(aug in f for aug in ['_hflip', '_vflip', '_rot90', '_rot180', '_rot270', '_flip']):
                    continue
                all_images.append(os.path.join(img_dir, f))
    return all_images


def extract_features(img_path):
    img = cv2.imread(img_path)
    if img is None:
        return None

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    img_lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    lower_green = np.array([20, 30, 30])
    upper_green = np.array([90, 255, 255])
    mask = cv2.inRange(img_hsv, lower_green, upper_green)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    if np.sum(mask > 0) < 500:
        mask = np.ones(gray.shape, dtype=np.uint8) * 255

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

    gray_masked = cv2.bitwise_and(gray, gray, mask=mask)
    gray_resized = cv2.resize(gray_masked, (256, 256))
    glcm = graycomatrix(gray_resized, distances=[1], angles=[0], levels=256, symmetric=True, normed=True)
    features['glcm_correlation'] = graycoprops(glcm, 'correlation')[0, 0]
    lbp = local_binary_pattern(gray_resized, P=8, R=1, method='uniform')
    features['lbp_std'] = np.std(lbp)
    lbp_hist, _ = np.histogram(lbp.ravel(), bins=10, density=True)
    features['lbp_energy'] = np.sum(lbp_hist ** 2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) > 100]

    if len(contours) > 0:
        areas = [cv2.contourArea(c) for c in contours]
        features['shape_num_objects'] = len(contours)
        features['shape_mean_area'] = np.mean(areas)
        features['shape_std_area'] = np.std(areas) if len(areas) > 1 else 0
        eccentricities, solidities, aspect_ratios = [], [], []
        for c in contours:
            if len(c) >= 5:
                ellipse = cv2.fitEllipse(c)
                ma, MA = ellipse[1]
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

    features['quality_brightness'] = np.mean(v_vals)
    features['quality_brightness_std'] = np.std(v_vals)
    features['quality_contrast'] = np.std(gray[mask_bool].astype(float))

    return features


def compute_quality_score(features):
    score = 0.0
    score += features['green_ratio'] * 10
    score += max(0, 2.0 - features['browning_ratio']) * 3
    score += features['shape_mean_solidity'] * 3
    score += max(0, 100 - features['quality_brightness_std']) / 30
    score += max(0, 140 - features['lab_a_mean']) / 20
    score += max(0, 150 - abs(features['lab_b_mean'] - 128)) / 30
    return score


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    print("=" * 60)
    print("TRAINING & SAVING ML MODELS")
    print("=" * 60)

    images = get_original_images(BASE_DIR)
    print(f"Found {len(images)} original images")

    print("Extracting features...")
    all_features = []
    all_features_dicts = []
    for i, img_path in enumerate(images):
        feat = extract_features(img_path)
        if feat is not None:
            all_features.append(list(feat.values()))
            all_features_dicts.append(feat)
        if (i + 1) % 30 == 0:
            print(f"  {i + 1}/{len(images)}")

    # Auto-label
    scores = [compute_quality_score(f) for f in all_features_dicts]
    threshold = np.percentile(scores, 65)
    labels = ['high_quality' if s >= threshold else 'medium_quality' for s in scores]

    feature_names = list(all_features_dicts[0].keys())
    X = np.array(all_features)
    y = np.array(labels)

    print(f"Total: {len(X)} | high_quality={np.sum(y == 'high_quality')}, medium_quality={np.sum(y == 'medium_quality')}")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Save scaler and feature names
    with open(os.path.join(SAVE_DIR, "scaler.pkl"), 'wb') as f:
        pickle.dump(scaler, f)
    with open(os.path.join(SAVE_DIR, "feature_names.pkl"), 'wb') as f:
        pickle.dump(feature_names, f)

    models = {
        'mlp': ('MLP Neural Network', MLPClassifier(hidden_layer_sizes=(32,), alpha=0.5, max_iter=1000, random_state=42)),
        'adaboost': ('AdaBoost', AdaBoostClassifier(n_estimators=20, learning_rate=0.3, random_state=42)),
        'logistic': ('Logistic Regression', LogisticRegression(C=0.1, max_iter=1000, random_state=42)),
        'svm_rbf': ('SVM (RBF)', SVC(kernel='rbf', C=0.5, gamma='scale', random_state=42, probability=True)),
        'svm_linear': ('SVM (Linear)', SVC(kernel='linear', C=0.1, random_state=42, probability=True)),
        'naive_bayes': ('Naive Bayes', GaussianNB()),
        'random_forest': ('Random Forest', RandomForestClassifier(n_estimators=30, max_depth=3, min_samples_split=8, min_samples_leaf=5, max_features='sqrt', random_state=42)),
        'gradient_boost': ('Gradient Boosting', GradientBoostingClassifier(n_estimators=30, max_depth=2, learning_rate=0.1, subsample=0.7, min_samples_leaf=5, random_state=42)),
        'decision_tree': ('Decision Tree', DecisionTreeClassifier(max_depth=3, min_samples_split=10, min_samples_leaf=5, random_state=42)),
        'knn': ('KNN', KNeighborsClassifier(n_neighbors=9)),
    }

    model_info = {}

    for key, (name, model) in models.items():
        model.fit(X_train_scaled, y_train)

        train_acc = accuracy_score(y_train, model.predict(X_train_scaled))
        y_pred = model.predict(X_test_scaled)
        test_acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)

        # Save model
        model_path = os.path.join(SAVE_DIR, f"{key}.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)

        model_info[key] = {
            'name': name,
            'train_acc': round(train_acc * 100, 2),
            'test_acc': round(test_acc * 100, 2),
            'f1': round(f1 * 100, 2),
        }

        print(f"  Saved {key}.pkl | {name} | Test: {test_acc*100:.1f}% | F1: {f1*100:.1f}%")

    # Save model info
    with open(os.path.join(SAVE_DIR, "model_info.json"), 'w') as f:
        json.dump(model_info, f, indent=2)

    print(f"\nAll models saved to: {SAVE_DIR}")
    print(f"Files: {os.listdir(SAVE_DIR)}")


if __name__ == '__main__':
    main()
