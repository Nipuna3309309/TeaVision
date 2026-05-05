# Subsystem Architecture: Tea Quality & Knowledge Retrieval (MIT22154576)

This document outlines the architecture, flow, and technical implementation of the three primary subsystems developed by **MIT22154576**:
1. **Tea Leaf Detection** (Object Detection)
2. **Grade My Tea** (Machine Learning Classification)
3. **Ceylon Tea Knowledge Base** (Retrieval-Augmented Generation)

---

## 1. Tea Leaf Detection System
This subsystem acts as an automated, fast-pass visual inspector. It counts tea leaves in a batch, identifies if they were coarsely plucked, and spots physical damage directly from high-resolution images.

### Frontend Integration (`DetectionPage.jsx`)
- **Image Acquisition**: Provides an interface for users to upload JPG/PNG images through a dropzone, capture live photos via their device camera, or seamlessly sync images captured directly from their smartphone via the local network `/mobile/upload` bridge.
- **Model Configuration**: Users can select which trained YOLOv8 model weights to apply (`teanet_rf_v4`), adjust confidence thresholds via a slider, and toggle SAHI (Slicing Aided Hyper Inference) on or off.
- **Result Rendering**: Receives the processed Base64 image back from the server and renders it with bounding boxes drawn perfectly around the detected `Fresh_Bud`, `Coarse_pluck`, or `Damage_Spot` regions, complete with a total leaf count.

### Backend Routing & Engine (`detection.py` & `main.py`)
- **The API Gateway**: The FastAPI `@app.post("/detect")` endpoint receives the multipart image upload and parameters. 
- **The Core AI Script (`detection.py`)**: 
  - Loads the YOLOv8 (`.pt`) model into memory.
  - If the SAHI boolean is true, it algorithmically slices the large source image into grids (e.g., 256x256), runs YOLOv8 on each individual slice, and logically merges intersecting bounding boxes. This prevents tiny tea buds from being shrunk out of existence during resizing.
  - Generates an automated "Quality Grade" (Good, Moderate, Poor) by calculating the ratio between the count of high-quality fresh buds versus damaged stems/leaves.

---

## 2. Grade My Tea (ML Classification)
While *Detection* counts and draws boxes, the *Grading* system acts as the mathematical quality classifier, analyzing physical metrics of the leaf to assign a premium or low-grade status using classical Machine Learning models.

### Frontend Integration (`GradingPage.jsx`)
- **Model Comparisons**: The interface pulls directly from `/models` on the backend to dynamically list all available mathematical models (e.g., `Random Forest`, `MLP Neural Network`, `SVM`). It displays a comparison table showing the exact Test Accuracy and F1 Score of each model, allowing the user to pick the most accurate one.
- **Image Input**: Handled via the exact same mobile sync/dropzone workflow as the Detection page to ensure a uniform User Experience.
- **Result Rendering**: The GUI dynamically unpacks the JSON response from the backend to display the core verdict (`High Quality` vs `Medium Quality`), the backend confidence probabilities rendered as colored progress bars, and a list of all 25 mathematical features extracted from the uploaded leaf.

### Backend Routing & Engine (`main.py` -> `@app.post("/classify")`)
- **The Engine**: When an image hits `/classify`, the backend does not rely on Convolutional Networks alone. Instead, it runs OpenCV scripts to meticulously extract **25 hand-crafted features** from the pixel data:
  - 11 Color features (RGB, HSV, LAB averages)
  - 3 Texture features (GLCM, Local Binary Patterns)
  - 7 Shape features (Contour Area, Solidity, Aspect Ratio)
  - 4 Quality features (Brightness, Contrast ratios)
- **The Decision Maker**: Those 25 normalized floating-point numbers are pushed into the structured ML model (e.g., Random Forest or Multi-Layer Perceptron) requested by the frontend. The model returns the binary classification (`high_quality` or `medium_quality`) and its statistical confidence breakdown, firing the JSON payload back to React.

---

## 3. Ceylon Tea Knowledge Base (RAG System)
This subsystem brings an intelligent, semantic search engine to the dashboard, allowing users to query standard operating procedures, historical data, and treatment instructions drawn directly from verified agricultural text.

### Frontend Integration (`KnowledgePage.jsx`)
- **Semantic Search Interface**: Provides a smart search bar where users can query human-readable phrases like "What are the health benefits of black tea?". It pings the backend `/search` endpoint to fetch results.
- **Live Library Statistics**: On mount, it fetches the `/stats` and `/categories` endpoints to calculate exactly how many documents and text chunks exist in the RAG brain, rendering them as dynamic counters and colored category filters (e.g., `cultivar`, `processing`, `disease`).
- **Interactive Reading**: When a user clicks a semantically matched search result, a modal opens overlaying the precise chunk of the document the AI deemed relevant to the query. 

### Backend Engine & Neural Search (`main.py`)
- **The Search Endpoint**: `@app.get("/search")` acts as the Retrieval step in the exact definition of Retrieval-Augmented Generation. 
- **The Mechanics**: The backend utilizes pre-embedded document chunks representing thousands of paragraphs of Sri Lankan Tea literature. When a React query arrives, the text is converted into a vector embedding, mathematically compared via similarity search against the document embeddings, and the top `K=10` closest matches are fired back to the frontend alongside their similarity scores.
