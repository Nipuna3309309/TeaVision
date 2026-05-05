# Component IT22154576 (Objective 1): Automated Tea Leaf Freshness Grading and Tea Type Classification

## What Have You Done Here?
Currently, your local development environment for the **Tea Analysis Application** is fully up and running at the same time:
1. **Backend Server** (`c:\Nipuna\TEST\presentation-app\backend`): You are running either FastAPI or Flask with `python main.py` holding your Artificial Intelligence inference engines and API routes (such as YOLOv8 implementations).
2. **Frontend React Application** (`c:\Nipuna\TEST\presentation-app\frontend`): You ran `npm run dev` with Vite. Because port `3000` was likely in use by another service, Vite dynamically mapped to port `3001`. You can access your frontend at **http://localhost:3001/**.

## What is Component IT22154576?
Based on the documentation (`Objective1_DataAnalysis_IT22154576.md`), this component is the **core module responsible for assessing the freshness and the type of freshly plucked tea leaves** using Mobile-based Computer Vision and Machine Learning. 

It aims to replace the subjective manual inspection processes in Sri Lanka's tea industry with standardized, automated metrics. 

### Key Features and Workflow:
1. **Mobile Data Collection (TeaVision App)**
   - Guided image capture relying on phone sensors to align tilt (<15 deg) and stabilization.
   - Quality check gates assessing: Blur, Background luminance (white cloth requirement), Brightness, and Glare. 

2. **Image Processing Pipeline**
   - **Dual Segmentation Options**: It first attempts to segment the leaf from the background using a **TensorFlow Lite/YOLO Model**. If not supported on the device, it falls back to a **colour thresholding algorithm** analyzing brightness, green tint, and shadows.
   - Preprocessing includes scaling down images, converting to HSV, masking the background, and noise reduction (erosion/dilation).

3. **Feature Extraction Engine**
   Once a leaf is segmented out, this component analyzes:
   - **Colour Features:** Computes a `Greenness Index` and a `Brownness Index` based on HSV colors. A high `Greenness Index` means fresh tea, while a high `Brownness Index` measures aging or oxidation.
   - **Texture Features:** Measures blur score using Laplacian variance.
   - **Morphological Size:** Calculates Leaf Area, Width, and Height. This uses QR Code reference cards (e.g., "TEAVISION:3.0cm") to translate pixel area to real-world squared centimeters.

4. **Freshness Grading Assessment**
   The features mapped are categorized into:
   - **Grade A (Fresh)**: High greenness, high uniformity, extremely low brownness.
   - **Grade B (Moderate)**: Medium greenness, lower uniformity, moderate brownness.
   - **Grade C (Stale)**: Little greenness, low uniformity, very high brownness.

By leveraging machine learning (`detection.py`, `yolov8s.pt`), this module guarantees a standard level of confidence (model yielding ~94.2% hit rate with the TF Lite backbone) for small-holder tea farmers.
