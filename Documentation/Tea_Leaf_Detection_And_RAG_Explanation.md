# System Explanations: Tea Leaf Detection & Ceylon Tea Knowledge Base

This document provides a detailed, file-by-file technical explanation of two key modules in your TeaVision application: the AI-powered **Tea Leaf Detection** engine, and the RAG-based **Ceylon Tea Knowledge System**.

---

## 1. Tea Leaf Detection System
This module evaluates the physical health and quality of plucked tea leaves using a trained YOLOv8 computer vision model integrated with SAHI (Slicing Aided Hyper Inference) for high-accuracy small object detection.

### Frontend Interface: `presentation-app/frontend/src/pages/DetectionPage.jsx`
- **Purpose**: The user-facing dashboard for conducting leaf quality analyses.
- **Key Features**:
  - **Dynamic Model Selection**: Users can hot-swap between different trained YOLOv8 weights (like `teanet_rf_v4`) via a dropdown menu.
  - **Tunable Parameters**: Provides sliders to actively control the confidence threshold, and toggle switches for enabling SAHI (which drastically improves the detection of tiny tea buds).
  - **Mobile Sync Integration**: Integrates the "QR Connect" flow to directly import freshly captured leaf photos from the user's mobile device without needing physical cable transfers.
  - **Visual Results**: Once the backend processes the image, this page renders the annotated image (showing bounding boxes around leaves) alongside a statistical breakdown of physical defects (e.g., Damage Spots, Coarse Pluck) and assigns a final Quality Grade.

### Backend Routing: `presentation-app/backend/main.py` -> `@app.post("/detect")`
- **Purpose**: The FastAPI endpoint acting as the gateway for image inference.
- **Key Features**: Safely receives the uploaded image payload from React, temporarily buffers it, and triggers the core AI script block, catching any model errors before passing the final results back over HTTP.

### Core AI Engine: `presentation-app/backend/detection.py`
- **Purpose**: The heavy-lifting neural network inference module.
- **Key Features**:
  - **YOLOv8 & SAHI**: Loads the specific `.pt` weights. If SAHI is triggered by the user, it slices the source image into smaller grids (e.g., 256x256 pixels), runs prediction on every single slice, and algorithmically merges the results. This prevents large images from shrinking and hiding small tea buds from the model.
  - **Classification Mapping**: Translates raw machine class IDs into human-readable agricultural terms (e.g., Mapping ID `2` to `Fresh_Bud_1`).
  - **Quality Algorithm**: Mathematically calculates the ratio of raw high-quality buds against coarse or damaged leaves to determine if the batch is `Good`, `Moderate`, or `Poor`.

---

## 2. Ceylon Tea Knowledge Base (RAG System)
This module acts as a specialized search engine for Sri Lankan tea agriculture, using Retrieval-Augmented Generation (RAG) principles to retrieve document chunks based on semantic relevance.

### Frontend Interface: `presentation-app/frontend/src/pages/KnowledgePage.jsx`
- **Purpose**: The interactive library interface where users can search, browse, and read verified agricultural documents.
- **Key Features**:
  - **Semantic Search Tab**: Provides an intelligent search bar where users can query phrases like "health benefits of black tea" or "TRI 2025". It hits the backend search endpoint and renders cards displaying the most relevant document chunks based on their AI similarity score.
  - **Category Browsing**: Sorts the unstructured knowledge base into distinct agricultural categories like `cultivar`, `plucking`, `disease`, `sustainability`, and `economics`, displaying them via visually distinct color-coded badges.
  - **Live Statistics**: Polls the backend on load to show exactly how many total documents, text chunks, and categories are currently embedded right at the top of the interface.
  - **Document Modal**: When a user clicks a search result or category card, it opens a modal rendering the full, un-chunked document content, the source category, and the associated agricultural metadata tags.

### Backend Routing & Retrieval: `presentation-app/backend/main.py` -> `API_BASE`
- **Purpose**: The endpoints serving the knowledge chunks to the UI.
- **Key Features**:
  - `@app.get("/categories")`, `@app.get("/stats")`, and `@app.get("/documents")`: These endpoints serve the foundational dataset metadata so the React interface knows exactly what documents and categories exist in the system without manually hardcoding them.
  - `@app.get("/search")`: The core Retrieval mechanism. When the React UI submits a search term, the backend runs a vector similarity search across its embedded knowledge chunks (representing all the PDFs and articles regarding Ceylon tea) and returns the top `K` most relevant paragraphs back to the UI along with their confidence scores.
