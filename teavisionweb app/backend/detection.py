"""
Tea Leaf Detection Module - Multi-Model Support
Supports multiple YOLOv8 models + Classical ML models
Project: 25-26J-133
"""

import os
import cv2
import json
import pickle
import numpy as np
import base64
from PIL import Image
from io import BytesIO
from ultralytics import YOLO
from scipy import stats
from skimage.feature import graycomatrix, graycoprops, local_binary_pattern

# SAHI - optional
SAHI_AVAILABLE = False
try:
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction
    SAHI_AVAILABLE = True
except ImportError:
    pass

# =====================================================
# YOLO MODELS REGISTRY
# =====================================================

YOLO_MODELS = {
    'teanet_rf_v4': {
        'name': 'TeaNet Roboflow v4',
        'description': 'Retrained on Roboflow v4 labels - mAP50: 0.734, mAP50-95: 0.628 (best model)',
        'path': r"C:\Nipuna\TEST\runs\detect\tea_roboflow_v4_20260310_0228\weights\best.pt",
        'tag': 'Recommended',
    },
    'teanet_v2': {
        'name': 'TeaNet V2',
        'description': 'Latest model - 150 epoch GPU trained, mAP50: 0.491 (best accuracy)',
        'path': r"C:\Nipuna\TEST\runs\detect\tea_standard_20260308_1721\weights\best.pt",
        'tag': 'Legacy',
    },
    'teanet_pro': {
        'name': 'TeaNet Pro',
        'description': 'Previous best - optimized for damage & disease detection',
        'path': r"C:\Nipuna\TEST\runs\detect\tea_leaf_damage_fix_20ep\weights\best.pt",
        'tag': 'Legacy',
    },
    'teanet_micro': {
        'name': 'TeaNet Micro',
        'description': 'Optimized for detecting small objects like Damage Spots',
        'path': r"C:\Nipuna\TEST\runs\detect\tea_leaf_small_obj4\weights\best.pt",
        'tag': 'Small Objects',
    },
    'teanet_plus': {
        'name': 'TeaNet Plus',
        'description': 'Trained on augmented dataset for better generalization',
        'path': r"C:\Nipuna\TEST\runs\detect\tea_leaf_augmented\weights\best.pt",
        'tag': 'Augmented',
    },
}

CLASS_NAMES = ['Coarse_pluck', 'Damage_Spot', 'Damaged_Leaf', 'Fresh_Bud_1', 'Fresh_Bud_2', 'Old_Leaf', 'stems']

CLASS_COLORS = {
    'Coarse_pluck': (255, 165, 0),
    'Damage_Spot': (255, 0, 0),
    'Damaged_Leaf': (200, 0, 0),
    'Fresh_Bud_1': (0, 255, 0),
    'Fresh_Bud_2': (0, 200, 0),
    'Old_Leaf': (255, 255, 0),
    'stems': (255, 0, 255)
}

QUALITY_CLASSES = {
    'good': ['Fresh_Bud_1', 'Fresh_Bud_2'],
    'moderate': ['Coarse_pluck', 'Old_Leaf', 'stems'],
    'poor': ['Damage_Spot', 'Damaged_Leaf']
}

# =====================================================
# ML MODELS REGISTRY
# =====================================================

ML_MODELS_DIR = os.path.join(os.path.dirname(__file__), "ml_models")

ML_MODELS_REGISTRY = {
    'mlp': {'name': 'Neural Network (MLP)', 'description': 'Multi-layer perceptron - best accuracy', 'tag': 'Best'},
    'adaboost': {'name': 'AdaBoost', 'description': 'Adaptive boosting ensemble method', 'tag': 'Ensemble'},
    'logistic': {'name': 'Logistic Regression', 'description': 'Fast linear classifier', 'tag': 'Fast'},
    'svm_rbf': {'name': 'SVM (RBF Kernel)', 'description': 'Support vector machine with radial basis', 'tag': 'SVM'},
    'svm_linear': {'name': 'SVM (Linear)', 'description': 'Linear support vector machine', 'tag': 'SVM'},
    'naive_bayes': {'name': 'Naive Bayes', 'description': 'Probabilistic Gaussian classifier', 'tag': 'Fast'},
    'random_forest': {'name': 'Random Forest', 'description': 'Ensemble of decision trees', 'tag': 'Ensemble'},
    'gradient_boost': {'name': 'Gradient Boosting', 'description': 'Gradient boosted decision trees', 'tag': 'Ensemble'},
    'decision_tree': {'name': 'Decision Tree', 'description': 'Single interpretable decision tree', 'tag': 'Simple'},
    'knn': {'name': 'KNN', 'description': 'K-Nearest Neighbors classifier', 'tag': 'Simple'},
}

# =====================================================
# LOAD MODELS
# =====================================================

# Load all YOLO models at startup
loaded_yolo_models = {}
default_yolo_key = None

for key, info in YOLO_MODELS.items():
    if os.path.exists(info['path']):
        try:
            loaded_yolo_models[key] = YOLO(info['path'])
            if default_yolo_key is None:
                default_yolo_key = key
            print(f"[YOLO] Loaded {info['name']}: {os.path.basename(info['path'])}")
        except Exception as e:
            print(f"[YOLO] Failed to load {info['name']}: {e}")

if not loaded_yolo_models:
    print("[YOLO] No custom models found, using yolov8s.pt")
    loaded_yolo_models['yolov8s'] = YOLO('yolov8s.pt')
    default_yolo_key = 'yolov8s'

# Load all ML models at startup
loaded_ml_models = {}
ml_scaler = None
ml_feature_names = None
ml_model_info = {}

if os.path.exists(ML_MODELS_DIR):
    # Load scaler
    scaler_path = os.path.join(ML_MODELS_DIR, "scaler.pkl")
    if os.path.exists(scaler_path):
        with open(scaler_path, 'rb') as f:
            ml_scaler = pickle.load(f)

    # Load feature names
    feat_path = os.path.join(ML_MODELS_DIR, "feature_names.pkl")
    if os.path.exists(feat_path):
        with open(feat_path, 'rb') as f:
            ml_feature_names = pickle.load(f)

    # Load model info
    info_path = os.path.join(ML_MODELS_DIR, "model_info.json")
    if os.path.exists(info_path):
        with open(info_path, 'r') as f:
            ml_model_info = json.load(f)

    # Load each model
    for key in ML_MODELS_REGISTRY:
        pkl_path = os.path.join(ML_MODELS_DIR, f"{key}.pkl")
        if os.path.exists(pkl_path):
            with open(pkl_path, 'rb') as f:
                loaded_ml_models[key] = pickle.load(f)
            print(f"[ML] Loaded {ML_MODELS_REGISTRY[key]['name']}")

    # Merge accuracy info into registry
    for key, info in ml_model_info.items():
        if key in ML_MODELS_REGISTRY:
            ML_MODELS_REGISTRY[key]['test_acc'] = info['test_acc']
            ML_MODELS_REGISTRY[key]['f1'] = info['f1']

print(f"[Detection] SAHI: {'Available' if SAHI_AVAILABLE else 'Not installed'}")
print(f"[Detection] YOLO models: {len(loaded_yolo_models)} | ML models: {len(loaded_ml_models)}")


# =====================================================
# YOLO DETECTION FUNCTIONS
# =====================================================

def create_sahi_model(model_path, confidence):
    if not SAHI_AVAILABLE:
        return None
    try:
        return AutoDetectionModel.from_pretrained(
            model_type='yolov8',
            model_path=model_path,
            confidence_threshold=max(0.05, confidence - 0.05),
            device='cpu'
        )
    except Exception as e:
        print(f"[SAHI] Creation failed: {e}")
        return None


def compute_iou(box1, box2):
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0


def nms_filter(detections, iou_threshold=0.45):
    if not detections:
        return detections
    sorted_dets = sorted(detections, key=lambda d: d['confidence'], reverse=True)
    kept = []
    for det in sorted_dets:
        should_keep = True
        for kept_det in kept:
            if det['class'] == kept_det['class']:
                if compute_iou(det['bbox'], kept_det['bbox']) > iou_threshold:
                    should_keep = False
                    break
        if should_keep:
            kept.append(det)
    return kept


def detect_with_sahi(image_np, model_path, confidence):
    if not SAHI_AVAILABLE:
        return None, {}

    sahi_det_model = create_sahi_model(model_path, confidence)
    if sahi_det_model is None:
        return None, {}

    import tempfile
    from datetime import datetime
    temp_file = os.path.join(tempfile.gettempdir(), f"sahi_{datetime.now().strftime('%H%M%S%f')}.jpg")

    try:
        cv2.imwrite(temp_file, cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR))

        h, w = image_np.shape[:2]
        if max(h, w) > 2000:
            slice_h, slice_w, overlap = 640, 640, 0.3
        elif max(h, w) > 1000:
            slice_h, slice_w, overlap = 512, 512, 0.25
        else:
            slice_h, slice_w, overlap = 320, 320, 0.2

        result = get_sliced_prediction(
            temp_file, sahi_det_model,
            slice_height=slice_h, slice_width=slice_w,
            overlap_height_ratio=overlap, overlap_width_ratio=overlap,
            postprocess_type="GREEDYNMM",
            postprocess_match_metric="IOS",
            postprocess_match_threshold=0.5,
        )

        detections = []
        for pred in result.object_prediction_list:
            cls_name = pred.category.name
            conf = pred.score.value
            if conf < confidence:
                continue
            bbox = pred.bbox.to_xyxy()
            detections.append({
                'class': cls_name, 'confidence': conf,
                'bbox': [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])]
            })

        detections = nms_filter(detections, iou_threshold=0.45)

        class_counts = {name: 0 for name in CLASS_NAMES}
        for det in detections:
            if det['class'] in class_counts:
                class_counts[det['class']] += 1
        return detections, class_counts
    except Exception as e:
        print(f"[SAHI] Error: {e}")
        return None, {}
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def detect(image_np, confidence, use_sahi, model_key=None):
    """Run YOLO detection with selected model"""
    if model_key is None:
        model_key = default_yolo_key

    yolo_model = loaded_yolo_models.get(model_key)
    if yolo_model is None:
        yolo_model = loaded_yolo_models[default_yolo_key]
        model_key = default_yolo_key

    model_path = YOLO_MODELS.get(model_key, {}).get('path', '')

    detections = []
    class_counts = {name: 0 for name in CLASS_NAMES}

    if use_sahi and SAHI_AVAILABLE and model_path:
        det, counts = detect_with_sahi(image_np, model_path, confidence)
        if det:
            detections = det
            class_counts = counts

    if not detections:
        image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        results = yolo_model.predict(source=image_bgr, conf=confidence, iou=0.3, max_det=50, verbose=False)

        img_h, img_w = image_np.shape[:2]
        img_area = img_h * img_w

        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    box_area = (x2 - x1) * (y2 - y1)
                    # Skip oversized boxes (>30% of image = garbage detection)
                    if box_area > img_area * 0.3:
                        continue
                    conf = float(box.conf[0].cpu().numpy())
                    cls_id = int(box.cls[0].cpu().numpy())
                    cls_name = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else f"class_{cls_id}"
                    detections.append({
                        'class': cls_name, 'confidence': conf,
                        'bbox': [int(x1), int(y1), int(x2), int(y2)]
                    })
                    if cls_name in class_counts:
                        class_counts[cls_name] += 1

    # Draw bounding boxes
    annotated = image_np.copy()
    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        cls_name = det['class']
        conf = det['confidence']
        color = CLASS_COLORS.get(cls_name, (0, 255, 0))
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        label = f"{cls_name}: {conf:.2f}"
        cv2.putText(annotated, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    return annotated, detections, class_counts


def quality_grade(class_counts, total):
    if total == 0:
        return "N/A", 0, 0, 0
    good = sum(class_counts.get(c, 0) for c in QUALITY_CLASSES['good'])
    moderate = sum(class_counts.get(c, 0) for c in QUALITY_CLASSES['moderate'])
    poor = sum(class_counts.get(c, 0) for c in QUALITY_CLASSES['poor'])
    good_pct = (good / total) * 100
    if good_pct >= 70:
        grade = "A - EXCELLENT"
    elif good_pct >= 50:
        grade = "B - GOOD"
    elif good_pct >= 30:
        grade = "C - MODERATE"
    else:
        grade = "D - NEEDS IMPROVEMENT"
    return grade, good, moderate, poor


def image_to_base64(image_np):
    img_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
    _, buffer = cv2.imencode('.jpg', img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return base64.b64encode(buffer).decode('utf-8')


def check_leaf_on_white_cloth(image_np, min_white_pct=15.0, min_green_pct=3.0):
    """
    Validate that the image contains tea leaves on a white cloth.
    Checks for:
    1. White/bright background (the white cloth) - at least min_white_pct of the image
    2. Green/plant content (tea leaves) - at least min_green_pct of the image
    Returns (is_valid, reason, details_dict).
    """
    img_hsv = cv2.cvtColor(cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR), cv2.COLOR_BGR2HSV)
    total_pixels = image_np.shape[0] * image_np.shape[1]

    # Check 1: White/bright background (white cloth = high brightness, low saturation)
    # White pixels: V > 180 and S < 60
    v_channel = img_hsv[:, :, 2]
    s_channel = img_hsv[:, :, 1]
    white_mask = (v_channel > 180) & (s_channel < 60)
    white_pct = round((np.sum(white_mask) / total_pixels) * 100, 1)

    # Check 2: Green/plant content (tea leaves)
    lower_green = np.array([20, 25, 25])
    upper_green = np.array([95, 255, 255])
    green_mask = cv2.inRange(img_hsv, lower_green, upper_green)
    green_pct = round((np.sum(green_mask > 0) / total_pixels) * 100, 1)

    details = {'white_pct': white_pct, 'green_pct': green_pct}

    has_white = white_pct >= min_white_pct
    has_green = green_pct >= min_green_pct

    if not has_white and not has_green:
        return False, 'No white cloth background or tea leaves detected. Please place tea leaves on a white cloth and try again.', details
    if not has_white:
        return False, f'White cloth background not detected (only {white_pct}% white). Please place tea leaves on a white cloth for accurate detection.', details
    if not has_green:
        return False, f'No tea leaves detected on the cloth (only {green_pct}% green content). Please make sure tea leaves are visible on the white cloth.', details

    return True, 'OK', details


def run_detection(image_bytes, confidence=0.20, use_sahi=False, model_key=None):
    """Main detection entry point with model selection"""
    image = Image.open(BytesIO(image_bytes))
    image_np = np.array(image)

    if len(image_np.shape) == 2:
        image_np = cv2.cvtColor(image_np, cv2.COLOR_GRAY2RGB)
    elif image_np.shape[2] == 4:
        image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)

    model_info = YOLO_MODELS.get(model_key or default_yolo_key, {})

    # Pre-check: reject images that are NOT tea leaves on a white cloth
    is_valid, reason, check_details = check_leaf_on_white_cloth(image_np)
    if not is_valid:
        return {
            'error': True,
            'message': reason,
            'total_detections': 0,
            'class_counts': {name: 0 for name in CLASS_NAMES},
            'quality_grade': 'N/A',
            'quality_breakdown': {
                'good': 0, 'good_pct': 0,
                'moderate': 0, 'moderate_pct': 0,
                'poor': 0, 'poor_pct': 0,
            },
            'detections': [],
            'annotated_image': image_to_base64(image_np),
            'model_used': model_info.get('name', model_key),
            'sahi_available': SAHI_AVAILABLE,
            'sahi_used': False,
            'validation': check_details,
        }

    annotated, detections, class_counts = detect(image_np, confidence, use_sahi, model_key)
    total = len(detections)
    grade, good, moderate, poor = quality_grade(class_counts, total)

    # If model found no detections even on a green image
    if total == 0:
        return {
            'error': True,
            'message': 'No tea leaves detected in the image. The image contains green content but no recognizable tea leaves were found. Try lowering the confidence threshold.',
            'total_detections': 0,
            'class_counts': class_counts,
            'quality_grade': 'N/A',
            'quality_breakdown': {
                'good': 0, 'good_pct': 0,
                'moderate': 0, 'moderate_pct': 0,
                'poor': 0, 'poor_pct': 0,
            },
            'detections': [],
            'annotated_image': image_to_base64(annotated),
            'model_used': model_info.get('name', model_key),
            'sahi_available': SAHI_AVAILABLE,
            'sahi_used': False,
        }

    return {
        'error': False,
        'total_detections': total,
        'class_counts': class_counts,
        'quality_grade': grade,
        'quality_breakdown': {
            'good': good, 'good_pct': (good / total * 100) if total > 0 else 0,
            'moderate': moderate, 'moderate_pct': (moderate / total * 100) if total > 0 else 0,
            'poor': poor, 'poor_pct': (poor / total * 100) if total > 0 else 0,
        },
        'detections': detections,
        'annotated_image': image_to_base64(annotated),
        'model_used': model_info.get('name', model_key),
        'sahi_available': SAHI_AVAILABLE,
        'sahi_used': use_sahi and SAHI_AVAILABLE and len(detections) > 0,
    }


# =====================================================
# ML CLASSIFICATION FUNCTIONS
# =====================================================

def extract_features_from_image(image_np):
    """Extract 25 hand-crafted features from an image numpy array (RGB)"""
    img = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
    img_rgb = image_np
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
        for k in ['shape_num_objects', 'shape_mean_area', 'shape_std_area',
                   'shape_mean_eccentricity', 'shape_mean_solidity',
                   'shape_area_ratio', 'shape_mean_aspect_ratio']:
            features[k] = 0

    features['quality_brightness'] = np.mean(v_vals)
    features['quality_brightness_std'] = np.std(v_vals)
    features['quality_contrast'] = np.std(gray[mask_bool].astype(float))

    return features


def run_classification(image_bytes, model_key='mlp'):
    """Run ML classification on uploaded image"""
    if model_key not in loaded_ml_models:
        return {'error': f'Model {model_key} not found'}
    if ml_scaler is None:
        return {'error': 'ML scaler not loaded'}

    image = Image.open(BytesIO(image_bytes))
    image_np = np.array(image)

    if len(image_np.shape) == 2:
        image_np = cv2.cvtColor(image_np, cv2.COLOR_GRAY2RGB)
    elif image_np.shape[2] == 4:
        image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)

    features = extract_features_from_image(image_np)
    if features is None:
        return {'error': 'Could not extract features from image'}

    feature_values = [features[name] for name in ml_feature_names]
    X = np.array([feature_values])
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    X_scaled = ml_scaler.transform(X)

    model = loaded_ml_models[model_key]
    prediction = model.predict(X_scaled)[0]

    # Get probability if available
    confidence = None
    if hasattr(model, 'predict_proba'):
        proba = model.predict_proba(X_scaled)[0]
        classes = model.classes_
        confidence = {str(c): round(float(p) * 100, 1) for c, p in zip(classes, proba)}

    model_info = ML_MODELS_REGISTRY.get(model_key, {})

    # Build feature summary for display
    feature_summary = {
        'Green Ratio': round(features['green_ratio'], 4),
        'Browning Ratio': round(features['browning_ratio'], 4),
        'Brightness': round(features['quality_brightness'], 1),
        'Contrast': round(features['quality_contrast'], 1),
        'Texture (LBP)': round(features['lbp_energy'], 4),
        'Leaf Objects': int(features['shape_num_objects']),
        'Solidity': round(features['shape_mean_solidity'], 4),
    }

    return {
        'prediction': prediction,
        'confidence': confidence,
        'model_used': model_info.get('name', model_key),
        'model_accuracy': model_info.get('test_acc'),
        'features': feature_summary,
        'image': image_to_base64(image_np),
    }


# =====================================================
# ENVIRONMENT ANALYSIS (Light + Dimensions)
# =====================================================

def analyze_environment(image_bytes, camera_distance_cm=None):
    """
    Analyze image environment: lighting conditions and leaf dimensions.
    Returns light analysis + auto-estimated leaf size.
    """
    image = Image.open(BytesIO(image_bytes))
    image_np = np.array(image)

    if len(image_np.shape) == 2:
        image_np = cv2.cvtColor(image_np, cv2.COLOR_GRAY2RGB)
    elif image_np.shape[2] == 4:
        image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)

    img_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = image_np.shape[:2]

    # ---- LIGHT ANALYSIS (Multi-signal approach) ----
    # Problem: Tea leaves are dark green, so average brightness is always low.
    # Solution: Combine multiple signals to judge AMBIENT light, not subject color.

    v_channel = img_hsv[:, :, 2].astype(float)
    s_channel = img_hsv[:, :, 1].astype(float)

    # --- Signal 1: EXIF metadata (most reliable) ---
    exif_light_score = None
    exif_info = {}
    try:
        exif_data = image.getexif()
        if exif_data:
            # EXIF tag IDs: 33434=ExposureTime, 34855=ISO, 37379=BrightnessValue, 37380=ExposureBias
            exposure_time = exif_data.get(33434)  # seconds
            iso = exif_data.get(34855)
            brightness_value = exif_data.get(37379)  # APEX BrightnessValue

            if brightness_value is not None:
                # BrightnessValue: higher = brighter scene
                # Typical: -1 to 2 = dark, 3-6 = indoor, 7-10 = outdoor, >10 = very bright
                bv = float(brightness_value)
                exif_info['brightness_value'] = round(bv, 2)
                if bv < 2:
                    exif_light_score = 15
                elif bv < 4:
                    exif_light_score = 35
                elif bv < 7:
                    exif_light_score = 60
                elif bv < 10:
                    exif_light_score = 80
                else:
                    exif_light_score = 95

            elif exposure_time is not None and iso is not None:
                # EV = log2(1/exposure_time) - log2(ISO/100)
                # Higher EV = brighter scene (camera uses faster shutter + lower ISO)
                import math
                et = float(exposure_time)
                iso_val = float(iso)
                exif_info['exposure_time'] = et
                exif_info['iso'] = int(iso_val)
                if et > 0:
                    ev = math.log2(1.0 / et) - math.log2(iso_val / 100.0)
                    exif_info['ev'] = round(ev, 2)
                    if ev < 3:
                        exif_light_score = 15
                    elif ev < 6:
                        exif_light_score = 35
                    elif ev < 9:
                        exif_light_score = 60
                    elif ev < 12:
                        exif_light_score = 80
                    else:
                        exif_light_score = 95
    except Exception:
        pass

    # --- Signal 2: Background/highlights brightness (non-leaf areas) ---
    # Create leaf mask (green areas) and analyze NON-leaf regions
    lower_green_light = np.array([20, 25, 25])
    upper_green_light = np.array([95, 255, 255])
    leaf_mask = cv2.inRange(img_hsv, lower_green_light, upper_green_light)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_CLOSE, kernel)
    leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_OPEN, kernel)

    # Background = everything that's NOT a leaf
    bg_mask = cv2.bitwise_not(leaf_mask)
    bg_pixels = v_channel[bg_mask > 0]

    if len(bg_pixels) > 100:
        bg_brightness = float(np.mean(bg_pixels))
    else:
        # If almost entire image is leaf, fall back to highlight analysis
        bg_brightness = float(np.percentile(v_channel, 90))

    bg_brightness_pct = round(bg_brightness / 255 * 100, 1)

    # --- Signal 3: Highlight percentile (top 5% brightest pixels) ---
    # Well-lit scenes have bright highlights/reflections even on dark subjects
    highlight_brightness = float(np.percentile(v_channel, 95))
    highlight_pct = round(highlight_brightness / 255 * 100, 1)

    # --- Signal 4: Saturation check ---
    # In low light, cameras boost gain → higher noise, colors look washed/desaturated
    # In good light, colors are vivid → higher saturation
    avg_saturation = float(np.mean(s_channel))
    sat_score = min(100, round(avg_saturation / 255 * 100 * 1.3, 1))  # slight boost

    # --- Signal 5: Overexposure check ---
    overexposed_pct = float(np.mean(v_channel > 250) * 100)
    underexposed_pct = float(np.mean(v_channel < 15) * 100)

    # --- Combine signals into final light score (0-100) ---
    if exif_light_score is not None:
        # EXIF is most reliable — weight it heavily
        light_score = (
            exif_light_score * 0.45 +
            bg_brightness_pct * 0.25 +
            highlight_pct * 0.15 +
            sat_score * 0.15
        )
    else:
        # No EXIF — use image-based signals, heavily weight background
        light_score = (
            bg_brightness_pct * 0.40 +
            highlight_pct * 0.30 +
            sat_score * 0.30
        )

    # Clamp
    light_score = max(0, min(100, round(light_score, 1)))

    # Penalize overexposure
    if overexposed_pct > 15:
        light_score = min(light_score, 95)  # cap but keep high

    # Classify based on combined score
    if light_score < 20:
        light_level = 'too_dark'
        light_label = 'Too Dark'
        light_color = '#F44336'
        light_tip = 'Move to a brighter area or use additional lighting.'
    elif light_score < 40:
        light_level = 'poor'
        light_label = 'Poor Lighting'
        light_color = '#FF9800'
        light_tip = 'Lighting is dim. Consider adding more light for better results.'
    elif light_score < 75:
        light_level = 'good'
        light_label = 'Good Lighting'
        light_color = '#4CAF50'
        light_tip = 'Lighting conditions are ideal for analysis.'
    elif light_score < 90:
        light_level = 'bright'
        light_label = 'Bright'
        light_color = '#8BC34A'
        light_tip = 'Slightly bright but acceptable for analysis.'
    else:
        light_level = 'too_bright'
        light_label = 'Too Bright / Overexposed'
        light_color = '#F44336'
        light_tip = 'Image is overexposed. Reduce direct light or move to shade.'

    # Uniformity: check if lighting is even across the image (use background regions)
    grid_h, grid_w = h // 3, w // 3
    grid_vals = []
    for gi in range(3):
        for gj in range(3):
            patch = v_channel[gi * grid_h:(gi + 1) * grid_h, gj * grid_w:(gj + 1) * grid_w]
            grid_vals.append(np.mean(patch))
    light_uniformity = round(1.0 - (np.std(grid_vals) / (np.mean(grid_vals) + 1e-6)), 3)
    light_uniformity = max(0.0, min(1.0, light_uniformity))

    # Contrast
    contrast = float(np.std(gray))

    # Color temperature estimate (warm/neutral/cool via avg R vs B)
    avg_r = float(np.mean(image_np[:, :, 0]))
    avg_b = float(np.mean(image_np[:, :, 2]))
    if avg_r > avg_b * 1.2:
        color_temp = 'warm'
        color_temp_label = 'Warm (yellowish)'
    elif avg_b > avg_r * 1.2:
        color_temp = 'cool'
        color_temp_label = 'Cool (bluish)'
    else:
        color_temp = 'neutral'
        color_temp_label = 'Neutral (balanced)'

    # Determine which method was used
    method_used = 'exif' if exif_light_score is not None else 'image_analysis'

    light_analysis = {
        'brightness': round(light_score, 1),
        'brightness_pct': light_score,
        'bg_brightness_pct': bg_brightness_pct,
        'highlight_pct': highlight_pct,
        'level': light_level,
        'label': light_label,
        'color': light_color,
        'tip': light_tip,
        'uniformity': light_uniformity,
        'uniformity_pct': round(light_uniformity * 100, 1),
        'contrast': round(contrast, 1),
        'color_temp': color_temp,
        'color_temp_label': color_temp_label,
        'overexposed_pct': round(overexposed_pct, 1),
        'underexposed_pct': round(underexposed_pct, 1),
        'method': method_used,
        'exif': exif_info if exif_info else None,
    }

    # ---- LEAF DIMENSION ESTIMATION ----
    lower_green = np.array([20, 30, 30])
    upper_green = np.array([90, 255, 255])
    mask = cv2.inRange(img_hsv, lower_green, upper_green)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) > 500]

    dimension_analysis = {
        'detected': False,
        'leaf_count': 0,
        'leaves': [],
        'total_leaf_area_px': 0,
        'image_width_px': w,
        'image_height_px': h,
        'camera_distance_cm': camera_distance_cm,
        'method': 'auto_contour',
    }

    if contours:
        # Sort by area descending
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        dimension_analysis['detected'] = True
        dimension_analysis['leaf_count'] = len(contours)

        total_leaf_area_px = 0
        leaves = []

        for i, cnt in enumerate(contours[:10]):  # Limit to top 10
            area_px = cv2.contourArea(cnt)
            total_leaf_area_px += area_px
            x, y, bw, bh = cv2.boundingRect(cnt)

            leaf_info = {
                'id': i + 1,
                'width_px': int(bw),
                'height_px': int(bh),
                'area_px': int(area_px),
                'center_x': int(x + bw // 2),
                'center_y': int(y + bh // 2),
                'coverage_pct': round(area_px / (w * h) * 100, 2),
            }

            # Estimate real dimensions if camera distance is provided
            # Using a simplified pinhole model with typical smartphone FOV (~60-70 deg)
            # FOV horizontal ~63 deg for typical phone camera
            # real_width = (pixel_width / image_width) * (2 * distance * tan(FOV/2))
            if camera_distance_cm and camera_distance_cm > 0:
                import math
                fov_h_rad = math.radians(63)  # typical smartphone horizontal FOV
                real_scene_width_cm = 2 * camera_distance_cm * math.tan(fov_h_rad / 2)
                px_to_cm = real_scene_width_cm / w
                leaf_info['width_cm'] = round(bw * px_to_cm, 2)
                leaf_info['height_cm'] = round(bh * px_to_cm, 2)
                leaf_info['area_cm2'] = round(area_px * (px_to_cm ** 2), 2)
            else:
                # Provide estimate using a default 30cm distance
                import math
                default_dist = 30
                fov_h_rad = math.radians(63)
                real_scene_width_cm = 2 * default_dist * math.tan(fov_h_rad / 2)
                px_to_cm = real_scene_width_cm / w
                leaf_info['width_cm_est'] = round(bw * px_to_cm, 2)
                leaf_info['height_cm_est'] = round(bh * px_to_cm, 2)
                leaf_info['area_cm2_est'] = round(area_px * (px_to_cm ** 2), 2)
                leaf_info['estimate_note'] = 'Estimated at 30cm distance. Set camera distance for accuracy.'

            leaves.append(leaf_info)

        dimension_analysis['leaves'] = leaves
        dimension_analysis['total_leaf_area_px'] = int(total_leaf_area_px)
        dimension_analysis['total_coverage_pct'] = round(total_leaf_area_px / (w * h) * 100, 2)

        # Summary for the largest leaf
        if leaves:
            biggest = leaves[0]
            dimension_analysis['primary_leaf'] = biggest

    return {
        'light': light_analysis,
        'dimensions': dimension_analysis,
        'image_size': {'width': w, 'height': h},
        'quality_ok': light_level in ('good', 'bright'),
    }
