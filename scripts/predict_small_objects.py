"""
Inference script optimized for small object detection using SAHI (Sliced Inference)
This helps detect small damage spots more accurately by processing image in tiles.

Install SAHI first: pip install sahi
"""

import os
os.chdir(r'C:\Nipuna\TEST')

from ultralytics import YOLO


def predict_standard(image_path, model_path=None):
    """Standard prediction with larger image size"""
    if model_path is None:
        model_path = 'runs/detect/tea_leaf_small_obj/weights/best.pt'

    model = YOLO(model_path)

    # Use larger image size and lower confidence for small objects
    results = model.predict(
        source=image_path,
        imgsz=1280,          # Match training image size
        conf=0.25,           # Lower confidence threshold
        iou=0.4,             # Lower IoU for small objects
        max_det=100,         # Allow more detections
        save=True,
        show=False,
    )

    return results


def predict_with_sahi(image_path, model_path=None):
    """
    Sliced prediction using SAHI - best for very small objects.
    The image is divided into overlapping tiles, predictions are made on each tile,
    then merged together.
    """
    try:
        from sahi import AutoDetectionModel
        from sahi.predict import get_sliced_prediction
        from sahi.utils.cv import visualize_object_predictions
        import cv2
    except ImportError:
        print("SAHI not installed. Run: pip install sahi")
        print("Falling back to standard prediction...")
        return predict_standard(image_path, model_path)

    if model_path is None:
        model_path = 'runs/detect/tea_leaf_small_obj/weights/best.pt'

    # Load model with SAHI
    detection_model = AutoDetectionModel.from_pretrained(
        model_type="yolov8",
        model_path=model_path,
        confidence_threshold=0.25,
        device="cuda:0"  # Use "cpu" if no GPU
    )

    # Sliced prediction - this is key for small objects
    result = get_sliced_prediction(
        image_path,
        detection_model,
        slice_height=416,        # Tile height
        slice_width=416,         # Tile width
        overlap_height_ratio=0.3,  # 30% overlap between tiles
        overlap_width_ratio=0.3,
    )

    # Save visualization
    output_path = image_path.replace('.jpg', '_sahi_result.jpg').replace('.png', '_sahi_result.png')

    # Read original image
    image = cv2.imread(image_path)

    # Draw predictions
    visualize_object_predictions(
        image=image,
        object_prediction_list=result.object_prediction_list,
        output_dir='runs/detect/sahi_results/',
        file_name=os.path.basename(image_path),
        export_format='png'
    )

    print(f"Found {len(result.object_prediction_list)} objects")
    for pred in result.object_prediction_list:
        print(f"  - {pred.category.name}: {pred.score.value:.2f}")

    return result


def predict_folder(folder_path, model_path=None, use_sahi=True):
    """Process all images in a folder"""
    import glob

    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
    images = []
    for ext in image_extensions:
        images.extend(glob.glob(os.path.join(folder_path, ext)))

    print(f"Found {len(images)} images in {folder_path}")

    for img_path in images:
        print(f"\nProcessing: {os.path.basename(img_path)}")
        if use_sahi:
            predict_with_sahi(img_path, model_path)
        else:
            predict_standard(img_path, model_path)

    print("\nDone! Results saved.")


if __name__ == '__main__':
    import sys

    # Example usage:
    # python predict_small_objects.py path/to/image.jpg
    # python predict_small_objects.py path/to/folder/

    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.isdir(path):
            predict_folder(path)
        else:
            # Try SAHI first, fallback to standard
            predict_with_sahi(path)
    else:
        print("Usage:")
        print("  python predict_small_objects.py <image_path>")
        print("  python predict_small_objects.py <folder_path>")
        print("\nExample:")
        print("  python predict_small_objects.py test/images/image1.jpg")
