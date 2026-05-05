# Unified Platform Integration — Activity Log

**Project:** 25-26J-133 — AI-Driven Tea Quality and Production Improvements  
**Date:** 2026-02-22 / 2026-02-23  
**Author:** AI Assistant (Antigravity)

---

## 1. Objective

Integrate all standalone project components into a single unified web platform.

---

## 2. Investigation & Discovery

### Components Identified

| # | Component | Location | Tech Stack | Purpose |
|---|-----------|----------|------------|---------|
| 1 | **Tea Leaf Detection** | `c:\Nipuna\TEST\app.py` | Streamlit, YOLOv8, SAHI, OpenCV | Detect & classify 7 tea leaf classes, quality grading (A–D) |
| 2 | **RAG Knowledge Base** | `c:\Nipuna\TEST\RAG_SYSTEM\` | FastAPI backend + Vite/React frontend | Search & browse 285 tea domain documents (hybrid retrieval) |
| 3 | **TeaVision Mobile App** | `c:\Nipuna\TEST\TeaVision\` | Android (Kotlin, Jetpack Compose) | Camera capture, QR calibration, ML leaf segmentation, measurement |
| 4 | **RAG Source Manifest** | `c:\Nipuna\TEST\New folder\` | CSV/JSONL + Python downloader | Curated source list for the RAG corpus |

### Tea Leaf Detection — Key Details

- **Model paths:** `runs/detect/tea_leaf_damage_fix_20ep`, `tea_leaf_small_obj4`, `tea_leaf_augmented`
- **7 Classes:** `Coarse_pluck`, `Damage_Spot`, `Damaged_Leaf`, `Fresh_Bud_1`, `Fresh_Bud_2`, `Old_Leaf`, `stems`
- **Quality grading:** A (≥70% good), B (≥50%), C (≥30%), D (<30%)
- **Features:** Single image detection, batch processing, SAHI for small objects, configurable confidence threshold

### RAG Knowledge Base — Key Details

- **Backend:** FastAPI at `RAG_SYSTEM/backend/main.py` (port 8000)
  - Endpoints: `/documents`, `/search`, `/categories`, `/stats`, `/metadata`, `/document/{doc_id}`
  - CORS enabled for all origins
- **Frontend:** Vite + React 19 at `RAG_SYSTEM/frontend/`
  - Tabs: Search Results, Browse Documents, Categories
  - Category-colored badges, document modal, quick searches
- **Corpus:** 285 documents across 13 categories (cultivar, region, grade, processing, health, plucking, disease, ai_grading, quality, economics, sustainability, history, trade)
- **Retrieval:** Dense (Sentence-BERT + FAISS), Sparse (BM25), Hybrid (RRF)

### TeaVision Android App — Key Details

- **Package:** `com.nipuna.teavision`
- **Architecture:** Jetpack Compose, Material 3
- **ML Pipeline:**
  1. Camera capture with tilt/stability detection
  2. Image quality check (blur, brightness, glare, background clutter)
  3. QR code calibration (`TEAVISION:<size_cm>`)
  4. Leaf segmentation (ML model or color analysis fallback)
  5. Measurement (width, height, area in cm)
  6. Color analysis (greenness, uniformity)
- **Data output:** Saves JPG + JSON metadata to device storage under `TeaVision_DataSet/`
- **Key source files:**
  - `MainActivity.kt` — main entry, capture pipeline, save logic
  - `screens/TeaAnalysisScreen.kt` — results display (batch info, quality, measurement, image preview)
  - `ml/LeafSegmentation.kt` — ML segmentation
  - `utils/MeasurementUtils.kt`, `ImageUtils.kt`, `ReferenceMarkerDetector.kt`

---

## 3. Integration Plan Created

**Target:** Single Vite + React web app at `c:\Nipuna\TEST\unified-platform\`

### Planned Structure

```
unified-platform/
├── index.html
├── package.json
├── vite.config.js
├── src/
│   ├── main.jsx
│   ├── App.jsx              ← router + sidebar navigation
│   ├── index.css             ← premium dark-mode design system
│   ├── pages/
│   │   ├── Dashboard.jsx     ← landing with stats & quick actions
│   │   ├── LeafDetection.jsx ← image upload → detection API
│   │   ├── KnowledgeBase.jsx ← RAG search, browse, categories
│   │   └── DataViewer.jsx    ← view TeaVision mobile capture data
│   └── components/
│       ├── Sidebar.jsx
│       ├── StatCard.jsx
│       └── Modal.jsx
```

### Design Decisions

1. **No modifications to existing backend** — RAG FastAPI already has CORS enabled
2. **Hash-based routing** — avoids react-router dependency
3. **Premium dark mode** — glassmorphism cards, gradients, micro-animations
4. **TeaVision as data viewer** — since native Android code can't run in browser, we show sample/uploaded JSON data
5. **Leaf Detection as frontend** — mirrors Streamlit UI; backend detection API call is prepared but optional

---

## 4. Files Examined

| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | 306 | Tea Leaf Detection Streamlit app |
| `RAG_SYSTEM/README.md` | 167 | RAG system documentation |
| `RAG_SYSTEM/backend/main.py` | 289 | FastAPI backend |
| `RAG_SYSTEM/frontend/src/App.jsx` | 363 | React frontend for RAG |
| `RAG_SYSTEM/frontend/package.json` | 28 | Frontend dependencies |
| `TeaVision/settings.gradle.kts` | 24 | Android project config |
| `TeaVision/app/.../MainActivity.kt` | 342 | Android main activity |
| `TeaVision/app/.../TeaAnalysisScreen.kt` | 310 | Analysis results screen |
| `New folder/README.md` | 29 | RAG source manifest docs |
| `data.yaml` | — | YOLO dataset config |

---

## 5. Artifacts Generated

| Artifact | Path |
|----------|------|
| Task checklist | `<brain>/task.md` |
| Implementation plan | `<brain>/implementation_plan.md` |
| This activity log | `Documentation/Unified_Platform_Integration_Log.md` |

---

## 6. Status

**Current state:** Implementation plan drafted and awaiting approval. Execution (scaffolding + coding the unified platform) has not yet begun.

**Next steps:**
1. Get user approval on the integration plan
2. Scaffold Vite + React project
3. Build shared design system
4. Implement each module page
5. Test in browser
