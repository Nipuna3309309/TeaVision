# Component IT22154576: Problem Statement & Novelty

## The Problem
The Sri Lankan tea industry currently relies heavily on manual, subjective visual inspection when accepting fresh tea leaves at factory intake stations. This causes several critical issues:
1. **Human Error & Inconsistency:** Fatigue and subjectivity lead to inspectors accepting poor-quality raw material (e.g., coarse plucks, old leaves, stem-heavy batches). 
2. **Quality Degradation:** Accepting substandard raw material irreversibly degrades the final manufactured tea grade, leading to direct revenue losses and brand damage.
3. **Flawed Existing AI Solutions:** Standard Deep Learning object detection models shrink down high-resolution 4K smartphone photos to small squares (e.g., 640x640px). When this happens, microscopic features crucial to tea quality—like tiny fresh buds or small damage spots—are mathematically compressed out of existence.
4. **"Black-Box" AI:** Factory managers and farmers distrust AI algorithms that simply output a binary "High Quality" or "Poor Quality" label without providing any physical evidence or logical explanation as to *why* the batch was rejected.
5. **Inaccessible Knowledge:** Critical standard operating procedures (SOPs) and agricultural treatment guidelines are trapped in heavy textbooks or physical manuals, completely inaccessible to farmers out in the field.

---

## The Novelty (Your Innovation)
Your component (IT22154576) introduces a multi-tiered, highly transparent AI architecture that solves these problems with four major technical novelties:

### 1. SAHI Integration for Microscopic Object Preservation
Instead of blindly resizing massive images, your YOLOv8 detection engine is integrated with **Slicing Aided Hyper Inference (SAHI)**. The algorithm dynamically slices a large source image into smaller grids, runs the YOLO detection independently on each uncompressed slice, and then logically merges the intersecting bounding boxes back together. This ensures tiny tea buds and minor damage spots are never lost during image scaling.

### 2. Transparent, Explainable Machine Learning (OpenCV Pipeline)
To solve the "black-box" trust issue, your grading system rejects pure end-to-end Deep Learning in favor of an explainable pipeline. Your backend runs custom OpenCV scripts to meticulously extract **25 mathematically verifiable hand-crafted features** from the leaves:
- **11 Color Features** (RGB, HSV, LAB averages and standard deviations)
- **3 Texture Features** (Gray Level Co-occurrence Matrix, Local Binary Patterns)
- **7 Shape Features** (Contour Area, Solidity, Aspect Ratio, Eccentricity)
- **4 Quality Metrics** (Brightness and Contrast ratios)
These explicit numbers are fed into classical Machine Learning models (like Random Forest, SVM, or MLP Neural Networks), allowing the frontend to show the user exactly which physical trait triggered a downgrade.

### 3. Edge-Ready Environmental QA Gate
Before running heavy AI inference, your API algorithmically parses the image. By combining embedded EXIF metadata (Exposure Time, ISO, APEX Brightness Value) with localized pixel variance, it calculates a 0-100 score for the real-world lighting condition. It prevents "garbage-in, garbage-out" by warning users if an image is underexposed or completely washed out before burning compute cycles.

### 4. Semantic RAG Architecture in an Agricultural Context
Rather than building a standard keyword search, you built a **Retrieval-Augmented Generation (RAG)** vector search engine specifically for Sri Lankan tea literature. By mathematically converting human questions into vector embeddings (`all-MiniLM-L6-v2`) and searching against a pre-embedded corpus using similarity search and a BM25 index, it instantly retrieves the exact contextual paragraph a farmer needs, bridging the gap between computer vision analysis and actionable agricultural knowledge.
