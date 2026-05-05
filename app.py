"""
Tea Leaf Detection App - Streamlit + YOLOv8
Project: 25-26J-133
"""

import streamlit as st
import os
import cv2
import numpy as np
import tempfile
from datetime import datetime
from PIL import Image
from ultralytics import YOLO
import tensorflow as tf

# SAHI
SAHI_AVAILABLE = False
try:
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction
    SAHI_AVAILABLE = True
except:
    pass

# Config
MODEL_PATH = r"C:\Nipuna\TEST\runs\detect\tea_standard_20260308_1721\weights\best.pt"
BACKUP_MODEL_1 = r"C:\Nipuna\TEST\runs\detect\tea_leaf_damage_fix_20ep\weights\best.pt"
BACKUP_MODEL_2 = r"C:\Nipuna\TEST\runs\detect\tea_leaf_small_obj4\weights\best.pt"

# Disease Detection CNN Model
DISEASE_MODEL_PATH = r"C:\Nipuna\TEST\Dinithis model\Tea-app - Copy\presentation-app\backend\ml_models\tea_leaf_disease_cnn_model.keras"

DISEASE_CLASSES = [
    "Blister Blight",
    "Brown Blight",
    "Grey Blight",
    "Healthy",
    "Helopeltis",
    "Red Rust"
]

DAMAGED_CLASSES = ['Damage_Spot', 'Damaged_Leaf']

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

@st.cache_resource
def load_disease_model():
    """Load the disease detection CNN model."""
    if os.path.exists(DISEASE_MODEL_PATH):
        try:
            model = tf.keras.models.load_model(DISEASE_MODEL_PATH)
            return model
        except Exception as e:
            print(f"[Disease Model] Failed to load: {e}")
            return None
    return None


def crop_damaged_leaves(image_np, detections):
    """Crop regions detected as damaged leaves from the original image."""
    crops = []
    h, w = image_np.shape[:2]
    for det in detections:
        if det['class'] in DAMAGED_CLASSES:
            x1, y1, x2, y2 = det['bbox']
            # Clamp to image bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 - x1 > 5 and y2 - y1 > 5:
                crop = image_np[y1:y2, x1:x2]
                crops.append({
                    'image': crop,
                    'bbox': [x1, y1, x2, y2],
                    'detection_class': det['class'],
                    'detection_conf': det['confidence']
                })
    return crops


def predict_disease(disease_model, crop_image):
    """Run disease classification on a cropped leaf image."""
    img = cv2.cvtColor(crop_image, cv2.COLOR_RGB2BGR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (256, 256))
    img_array = np.expand_dims(img, axis=0)
    prediction = disease_model.predict(img_array, verbose=0)[0]
    idx = int(np.argmax(prediction))
    disease_name = DISEASE_CLASSES[idx]
    confidence = float(prediction[idx])
    return disease_name, confidence, {DISEASE_CLASSES[i]: float(prediction[i]) for i in range(len(DISEASE_CLASSES))}


@st.cache_resource
def load_models():
    model_path = None
    if os.path.exists(MODEL_PATH):
        model_path = MODEL_PATH
    elif os.path.exists(BACKUP_MODEL_1):
        model_path = BACKUP_MODEL_1
    elif os.path.exists(BACKUP_MODEL_2):
        model_path = BACKUP_MODEL_2
    else:
        model_path = 'yolov8s.pt'

    model = YOLO(model_path)

    sahi_model = None
    if SAHI_AVAILABLE:
        try:
            sahi_model = AutoDetectionModel.from_pretrained(
                model_type='yolov8',
                model_path=model_path,
                confidence_threshold=0.15,
                device='cpu'
            )
        except:
            pass

    return model, sahi_model, model_path

def detect_with_sahi(image_np, sahi_model, confidence):
    if sahi_model is None:
        return None, {}

    temp_file = os.path.join(tempfile.gettempdir(), f"sahi_{datetime.now().strftime('%H%M%S%f')}.jpg")

    try:
        cv2.imwrite(temp_file, cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR))

        result = get_sliced_prediction(
            temp_file, sahi_model,
            slice_height=512, slice_width=512,
            overlap_height_ratio=0.3, overlap_width_ratio=0.3,
        )

        detections = []
        class_counts = {name: 0 for name in CLASS_NAMES}

        for pred in result.object_prediction_list:
            cls_name = pred.category.name
            conf = pred.score.value
            bbox = pred.bbox.to_xyxy()
            detections.append({
                'class': cls_name,
                'confidence': conf,
                'bbox': [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])]
            })
            if cls_name in class_counts:
                class_counts[cls_name] += 1

        return detections, class_counts
    except Exception as e:
        st.error(f"SAHI error: {e}")
        return None, {}
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

def detect(image_np, model, sahi_model, confidence, use_sahi):
    detections = []
    class_counts = {name: 0 for name in CLASS_NAMES}

    if use_sahi and sahi_model:
        det, counts = detect_with_sahi(image_np, sahi_model, confidence)
        if det:
            detections = det
            class_counts = counts

    if not detections:
        image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        results = model.predict(source=image_bgr, conf=confidence, iou=0.45, verbose=False)

        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    cls_id = int(box.cls[0].cpu().numpy())
                    cls_name = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else f"class_{cls_id}"
                    detections.append({
                        'class': cls_name,
                        'confidence': conf,
                        'bbox': [int(x1), int(y1), int(x2), int(y2)]
                    })
                    if cls_name in class_counts:
                        class_counts[cls_name] += 1

    # Draw boxes
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

def check_leaf_on_white_cloth(image_np, min_white_pct=15.0, min_green_pct=3.0):
    """Check if image contains tea leaves on a white cloth."""
    img_hsv = cv2.cvtColor(cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR), cv2.COLOR_BGR2HSV)
    total_pixels = image_np.shape[0] * image_np.shape[1]
    v_channel = img_hsv[:, :, 2]
    s_channel = img_hsv[:, :, 1]
    white_pct = round((np.sum((v_channel > 180) & (s_channel < 60)) / total_pixels) * 100, 1)
    lower_green = np.array([20, 25, 25])
    upper_green = np.array([95, 255, 255])
    green_mask = cv2.inRange(img_hsv, lower_green, upper_green)
    green_pct = round((np.sum(green_mask > 0) / total_pixels) * 100, 1)
    has_white = white_pct >= min_white_pct
    has_green = green_pct >= min_green_pct
    if not has_white and not has_green:
        return False, 'No white cloth background or tea leaves detected. Please place tea leaves on a white cloth and try again.'
    if not has_white:
        return False, f'White cloth background not detected (only {white_pct}% white). Please place tea leaves on a white cloth.'
    if not has_green:
        return False, f'No tea leaves detected on the cloth (only {green_pct}% green). Make sure tea leaves are visible on the white cloth.'
    return True, 'OK'

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

# Main App
st.set_page_config(page_title="Tea Leaf Detection", layout="wide")
st.title("Tea Leaf Detection System")
st.markdown("**YOLOv8 + SAHI | Project 25-26J-133**")

model, sahi_model, model_path = load_models()
disease_model = load_disease_model()

# Sidebar
st.sidebar.header("Settings")
confidence = st.sidebar.slider("Confidence", 0.1, 0.9, 0.20, 0.05)
use_sahi = st.sidebar.checkbox("Use SAHI (better for small objects)", value=SAHI_AVAILABLE, disabled=not SAHI_AVAILABLE)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Model:** {os.path.basename(model_path)}")
st.sidebar.markdown(f"**SAHI:** {'Enabled' if SAHI_AVAILABLE else 'Not installed'}")
st.sidebar.markdown(f"**Disease Model:** {'Loaded' if disease_model else 'Not available'}")

# Tabs
tab1, tab2, tab3 = st.tabs(["Single Image", "Batch Processing", "Info"])

with tab1:
    uploaded_file = st.file_uploader("Upload Image", type=['jpg', 'jpeg', 'png'])

    if uploaded_file:
        image = Image.open(uploaded_file)
        image_np = np.array(image)

        if len(image_np.shape) == 2:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_GRAY2RGB)
        elif image_np.shape[2] == 4:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)

        col1, col2 = st.columns(2)

        with col1:
            st.image(image_np, caption="Original", use_container_width=True)

        if st.button("Detect", type="primary"):
            # Pre-check: must be tea leaves on a white cloth
            is_valid, reason = check_leaf_on_white_cloth(image_np)
            if not is_valid:
                st.error(reason)
                st.warning("**Only tea leaves on a white cloth are accepted.** Selfies, scenery, or other objects are not supported.")
            else:
                with st.spinner("Detecting..."):
                    annotated, detections, class_counts = detect(image_np, model, sahi_model, confidence, use_sahi)

                total = len(detections)

                if total == 0:
                    st.error("No tea leaves detected. The image has green content but no recognizable tea leaves were found.")
                    st.warning("**Tips:** Try lowering the confidence threshold or use SAHI for better small object detection.")
                else:
                    with col2:
                        st.image(annotated, caption="Detection Result", use_container_width=True)

                    grade, good, moderate, poor = quality_grade(class_counts, total)

                    st.markdown("---")
                    col_a, col_b, col_c = st.columns(3)

                    with col_a:
                        st.metric("Total Detections", total)
                    with col_b:
                        st.metric("Quality Grade", grade.split(" - ")[0])
                    with col_c:
                        mode = "SAHI" if (use_sahi and sahi_model) else "Standard"
                        st.metric("Mode", mode)

                    st.markdown("### Detection Results")
                    for cls, cnt in class_counts.items():
                        if cnt > 0:
                            st.write(f"- **{cls}**: {cnt}")

                    st.markdown("### Quality Breakdown")
                    st.write(f"- Good (Fresh Buds): **{good}** ({good/total*100:.1f}%)")
                    st.write(f"- Moderate: **{moderate}** ({moderate/total*100:.1f}%)")
                    st.write(f"- Poor (Damaged): **{poor}** ({poor/total*100:.1f}%)")

                    # Disease Detection on damaged leaves
                    damaged_crops = crop_damaged_leaves(image_np, detections)
                    if damaged_crops and disease_model:
                        st.markdown("---")
                        st.markdown("### Disease Detection on Damaged Leaves")
                        st.write(f"Found **{len(damaged_crops)}** damaged leaf region(s). Analyzing diseases...")

                        disease_cols = st.columns(min(len(damaged_crops), 3))
                        for i, crop_info in enumerate(damaged_crops):
                            with disease_cols[i % 3]:
                                crop_img = crop_info['image']
                                disease_name, disease_conf, all_probs = predict_disease(disease_model, crop_img)

                                st.image(crop_img, caption=f"Crop #{i+1} ({crop_info['detection_class']})", use_container_width=True)

                                if disease_name == "Healthy":
                                    st.success(f"**{disease_name}** ({disease_conf*100:.1f}%)")
                                else:
                                    st.error(f"**{disease_name}** ({disease_conf*100:.1f}%)")

                                with st.expander("All probabilities"):
                                    for cls, prob in sorted(all_probs.items(), key=lambda x: -x[1]):
                                        bar_pct = prob * 100
                                        st.write(f"- {cls}: {bar_pct:.1f}%")
                    elif damaged_crops and not disease_model:
                        st.warning("Damaged leaves detected but disease model is not available.")
                    elif poor == 0:
                        st.info("No damaged leaves found - all leaves appear healthy!")

with tab2:
    st.markdown("### Batch Processing")
    uploaded_files = st.file_uploader("Upload Multiple Images", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

    if uploaded_files:
        st.write(f"**{len(uploaded_files)} images uploaded**")

        if st.button("Process All", type="primary"):
            results = []
            total_counts = {name: 0 for name in CLASS_NAMES}

            progress = st.progress(0)

            for i, file in enumerate(uploaded_files):
                image = Image.open(file)
                image_np = np.array(image)

                if len(image_np.shape) == 2:
                    image_np = cv2.cvtColor(image_np, cv2.COLOR_GRAY2RGB)
                elif len(image_np.shape) == 3 and image_np.shape[2] == 4:
                    image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)

                annotated, detections, class_counts = detect(image_np, model, sahi_model, confidence, use_sahi)
                results.append((file.name, annotated, len(detections)))

                for cls, cnt in class_counts.items():
                    total_counts[cls] += cnt

                progress.progress((i + 1) / len(uploaded_files))

            failed = [name for name, _, count in results if count == 0]
            passed = [(name, img, count) for name, img, count in results if count > 0]

            if passed:
                st.success(f"Detected tea leaves in {len(passed)} out of {len(results)} images!")
            if failed:
                st.error(f"No tea leaves detected in {len(failed)} image(s): {', '.join(failed)}. These images may not contain tea leaves.")

            # Show results
            st.markdown("### Results")
            cols = st.columns(3)
            for i, (name, img, count) in enumerate(passed):
                with cols[i % 3]:
                    st.image(img, caption=f"{name} ({count} detections)", use_container_width=True)

            st.markdown("### Total Counts")
            for cls, cnt in total_counts.items():
                if cnt > 0:
                    st.write(f"- **{cls}**: {cnt}")

with tab3:
    st.markdown("### Model Info")
    st.write(f"- **Model Path:** `{model_path}`")
    st.write(f"- **SAHI:** {'Enabled' if SAHI_AVAILABLE else 'Not installed'}")
    st.write(f"- **Classes:** 7")

    st.markdown("### Classes")
    st.markdown("""
    | Class | Quality |
    |-------|---------|
    | Fresh_Bud_1, Fresh_Bud_2 | Good |
    | Coarse_pluck, Old_Leaf, stems | Moderate |
    | Damage_Spot, Damaged_Leaf | Poor |
    """)

    st.markdown("### Disease Detection")
    st.write(f"- **Disease Model:** {'Loaded' if disease_model else 'Not available'}")
    st.write(f"- **Model Path:** `{DISEASE_MODEL_PATH}`")
    st.markdown("""
    | Disease | Description |
    |---------|------------|
    | Blister Blight | White blisters on young leaves |
    | Brown Blight | Brown patches on leaf edges |
    | Grey Blight | Grey spots with dark margins |
    | Healthy | No disease detected |
    | Helopeltis | Insect damage causing brown spots |
    | Red Rust | Red-orange algal growth on stems |
    """)

    st.markdown("### How It Works")
    st.write("1. Upload an image of tea leaves on a white cloth")
    st.write("2. YOLO detects all leaves and identifies damaged ones")
    st.write("3. Damaged leaves are automatically cropped")
    st.write("4. Each crop is analyzed by the Disease CNN model")

    st.markdown("### Tips")
    st.write("- Lower confidence (0.15-0.25) for small objects like Damage_Spot")
    st.write("- Enable SAHI for better small object detection")
