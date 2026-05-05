"""
Unified Tea Analysis System - FastAPI Backend
Combines RAG Knowledge Base + YOLOv8 Detection
Project: 25-26J-133
"""

import os
import sys
import threading
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import json
import pickle
import csv
import socket
import time
import base64
import asyncio
import warnings
import httpx
from dotenv import load_dotenv

load_dotenv()

warnings.filterwarnings(
    "ignore",
    message=r"urllib3 \(.+\) or chardet \(.+\)/charset_normalizer \(.+\) doesn't match a supported version!",
)

import numpy as np
import joblib
import pandas as pd
import tensorflow as tf
import cv2
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, Query, UploadFile, File, Form
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

tf.get_logger().setLevel("ERROR")

from detection import (
    run_detection, run_classification, analyze_environment,
    SAHI_AVAILABLE, CLASS_NAMES, CLASS_COLORS, QUALITY_CLASSES,
    YOLO_MODELS, ML_MODELS_REGISTRY, loaded_yolo_models, loaded_ml_models, ml_model_info
)
from yield_prediction import load_sarimax_models, get_fields, get_field_info, get_best_month, predict_yield, sarimax_models
from logbook_ocr import init_ocr_engine, process_logbook_image, export_to_excel, COL_NAMES
import tempfile

# Add RAG_SYSTEM/backend to path for auto_scraper and rebuild_index
RAG_BACKEND_DIR = str(Path(r"C:\Nipuna\TEST\RAG_SYSTEM\backend"))
if RAG_BACKEND_DIR not in sys.path:
    sys.path.insert(0, RAG_BACKEND_DIR)

from routers.smart_auction_router import router as smart_auction_router
from routers.auth_router import router as auth_router

# Initialize FastAPI
app = FastAPI(
    title="Tea Analysis System API",
    description="Unified API for Tea Leaf Detection + Knowledge Retrieval + Yield Prediction",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(smart_auction_router)
app.include_router(auth_router)

MODEL_DIR = Path(__file__).parent / "ml_models"
print("[AI] Loading CNN and Seasonal Models...")
disease_model = tf.keras.models.load_model(MODEL_DIR / "tea_leaf_disease_cnn_model.keras")
invasive_model = tf.keras.models.load_model(MODEL_DIR / "invasive_species_cnn_model.keras")
seasonal_model = joblib.load(MODEL_DIR / "tea_seosanal_final_ensemble_model.pkl")

print("[AI] Models loaded successfully")

DISEASE_CLASSES = [
    "Blister Blight",
    "Brown Blight",
    "Grey Blight",
    "Healthy",
    "Helopeltis",
    "Red Rust"
]

INVASIVE_CLASSES = [
    "Lantana Camara",
    "Mikania micrantha",
    "Mimosa diplotricha",
    "Sphagneticola trilobata",
    "Tridax Procumbens"
]

INVASIVE_SOLUTIONS = {
    "Lantana Camara": "Mechanically uproot the plant before flowering. Apply selective systemic herbicides on cut stumps. Establish dense native cover crops to suppress regrowth.",
    "Mikania micrantha": "Conduct regular slashing and manual removal. Improve tea canopy shade to naturally suppress its growth. Use approved broadleaf herbicides as a last resort.",
    "Mimosa diplotricha": "Uproot seedlings manually wearing protective gloves before seed set. Controlled grazing or selective post-emergence herbicides can help manage young shoots.",
    "Sphagneticola trilobata": "Carefully remove all stem fragments from the soil to prevent vegetative reproduction. Plant competitive ground covers aggressively. Chemical control may be required.",
    "Tridax Procumbens": "Maintain a healthy and dense ground cover to simply outcompete seedlings. Manually hoe or pull out the weed before it flowers and spreads its seeds."
}


def preprocess_image(image_bytes):
    """Preprocess image for CNN models (256x256, no rescaling - models have built-in Rescaling layers)"""
    file_bytes = np.asarray(bytearray(image_bytes), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (256, 256))
    img = np.expand_dims(img, axis=0)
    return img


CATEGORIZED_TREATMENTS = {
    "Blister Blight": {
        "organic": [
            "Apply Neem oil spray (5ml/L) early morning",
            "Spray baking soda solution (1 tsp in 1L water) to alter leaf pH",
            "Use compost tea to boost leaf-surface microbial competition"
        ],
        "manual": [
            "Prune infected leaves and destroy them away from the estate",
            "Improve shade management to allow more sunlight penetration",
            "Ensure wide spacing between bushes for better air circulation"
        ],
        "chemical": [
            "Spray Copper Oxychloride (0.3%) at 7-10 day intervals",
            "Apply systemic fungicides like Hexaconazole or Bitertanol",
            "Use protective fungicides before the onset of monsoon"
        ]
    },
    "Red Rust": {
        "organic": [
            "Improve soil drainage and aeration",
            "Apply balanced organic compost to strengthen plant immunity",
            "Spray seaweed extract to reduce algal stress"
        ],
        "manual": [
            "Remove and burn heavily infested branches",
            "Prune overhanging shade trees to reduce humidity",
            "Clean the stems with a brush to remove algal growth manually"
        ],
        "chemical": [
            "Apply Bordeaux mixture (1%) during the dormant season",
            "Spray Copper-based fungicides during the early rains",
            "Use specialized Algicides if the infestation is severe"
        ]
    },
    "Brown Blight": {
        "organic": [
            "Apply garlic-chili extract as a mild antifungal barrier",
            "Spray Horsetail tea (rich in silica) to strengthen cell walls",
            "Use Trichoderma viride as a biological control agent"
        ],
        "manual": [
            "Collect and destroy all fallen tea leaves from the ground",
            "Sterilize pruning tools between bushes to prevent spread",
            "Avoid pruning during wet weather to minimize wound infection"
        ],
        "chemical": [
            "Spray Carbendazim (0.1%) or Mancozeb (0.2%)",
            "Use Copper Oxychloride for broad-spectrum protection",
            "Apply Propiconazole for systemic control of spreading patches"
        ]
    },
    "Shot Hole Borer": {
        "organic": [
            "Apply Beauveria bassiana (entomopathogenic fungus) spray",
            "Use pheromone traps to monitor and capture adult beetles",
            "Plant repellent companion crops like Crotalaria"
        ],
        "manual": [
            "Remove and burn all primary 'downtry' branches showing entry holes",
            "Avoid deep pruning during peak borer emergence periods",
            "Apply a paste of cow dung and clay to cover larger entry wounds"
        ],
        "chemical": [
            "Spray systemic insecticides like Imidacloprid (0.05%)",
            "Use Delta-methrin for perimeter control during swarming",
            "Apply Quinalphos around the base of the stems"
        ]
    },
    "Healthy": {
        "organic": [
            "Continue using high-quality organic mulch",
            "Maintain soil health with regular compost application"
        ],
        "manual": [
            "Perform regular monitoring once every 2 weeks",
            "Regular maintenance pruning is sufficient"
        ],
        "chemical": [
            "No chemical intervention required",
            "Save chemicals for curative purposes only"
        ]
    }
}


# =====================================================
# RAG SYSTEM - Data paths and models
# =====================================================

RAG_DATA_DIR = Path(r"C:\Nipuna\TEST\RAG_SYSTEM")
CORPUS_PATH = RAG_DATA_DIR / "tea_corpus.json"
CHUNKS_PATH = RAG_DATA_DIR / "data" / "processed" / "chunks.csv"
EMBEDDINGS_PATH = RAG_DATA_DIR / "data" / "embeddings"

# Global data storage
corpus_data = {}
chunks_data = []
chunk_embeddings = None
bm25_index = None
tokenized_chunks = []
chunk_ids = []

# Semantic search models (loaded lazily)
faiss_index = None
embedding_model = None

# Scraper status (shared across threads)
scraper_status = {
    "running": False,
    "phase": "idle",
    "progress": 0,
    "message": "",
    "new_documents": 0,
    "total_documents": 0,
    "completed": False,
    "error": None,
}


class SearchResult(BaseModel):
    doc_id: str
    chunk_id: str
    title: str
    content: str
    category: str
    tags: List[str]
    score: float


class SearchResponse(BaseModel):
    query: str
    method: str
    results: List[SearchResult]
    total_results: int


class Document(BaseModel):
    doc_id: str
    title: str
    content: str
    category: str
    tags: List[str]


class CategoryStats(BaseModel):
    category: str
    count: int
    documents: List[str]


def load_data():
    """Load all RAG data files on startup"""
    global corpus_data, chunks_data, chunk_embeddings, bm25_index, tokenized_chunks, chunk_ids

    # Load corpus
    with open(CORPUS_PATH, 'r', encoding='utf-8') as f:
        corpus_data = json.load(f)

    # Load chunks from CSV
    chunks_path = RAG_DATA_DIR / "data" / "processed" / "chunks.csv"
    if chunks_path.exists():
        with open(chunks_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            chunks_data = list(reader)

    # Load embeddings
    embeddings_path = EMBEDDINGS_PATH / "chunk_embeddings.npy"
    if embeddings_path.exists():
        chunk_embeddings = np.load(embeddings_path)

    # Load BM25 index
    bm25_path = EMBEDDINGS_PATH / "bm25_index.pkl"
    if bm25_path.exists():
        with open(bm25_path, 'rb') as f:
            bm25_index = pickle.load(f)

    # Load tokenized chunks
    tokenized_path = EMBEDDINGS_PATH / "tokenized_chunks.pkl"
    if tokenized_path.exists():
        with open(tokenized_path, 'rb') as f:
            tokenized_chunks = pickle.load(f)

    # Load chunk IDs
    chunk_ids_path = EMBEDDINGS_PATH / "chunk_ids.json"
    if chunk_ids_path.exists():
        with open(chunk_ids_path, 'r') as f:
            chunk_ids = json.load(f)

    print(f"[RAG] Loaded {len(corpus_data.get('documents', []))} documents")
    print(f"[RAG] Loaded {len(chunks_data)} chunks")


def load_semantic_models():
    """Load FAISS index and embedding model for semantic search."""
    global faiss_index, embedding_model

    faiss_path = EMBEDDINGS_PATH / "faiss_index.bin"
    if faiss_path.exists():
        try:
            import faiss
            faiss_index = faiss.read_index(str(faiss_path))
            print(f"[RAG] FAISS index loaded: {faiss_index.ntotal} vectors")
        except Exception as e:
            print(f"[RAG] FAISS load failed: {e}")

    try:
        from sentence_transformers import SentenceTransformer
        embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        print(f"[RAG] Embedding model loaded: all-MiniLM-L6-v2")
    except Exception as e:
        print(f"[RAG] Embedding model load failed: {e}")


@app.on_event("startup")
async def startup_event():
    """Load data when server starts"""
    load_data()
    load_sarimax_models()
    # Pre-initialize the OCR engine so the first request is faster
    init_ocr_engine()
    # Load semantic search models in background to avoid slowing startup
    threading.Thread(target=load_semantic_models, daemon=True).start()


# =====================================================
# RAG ENDPOINTS
# =====================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Tea Analysis System API",
        "version": "1.0.0",
        "modules": {
            "detection": "YOLOv8 Tea Leaf Detection",
            "rag": "Tea Knowledge Retrieval"
        },
        "endpoints": {
            "/detect": "POST - Run detection on uploaded image",
            "/detection/info": "GET - Detection system info",
            "/documents": "GET - Get all documents",
            "/categories": "GET - Get category statistics",
            "/search": "GET - Search documents",
            "/document/{doc_id}": "GET - Get specific document",
            "/stats": "GET - System statistics"
        }
    }


@app.get("/documents", response_model=List[Document])
async def get_documents(
    category: Optional[str] = None,
    limit: int = Query(default=50, le=100)
):
    """Get all documents, optionally filtered by category"""
    documents = corpus_data.get("documents", [])

    if category:
        documents = [d for d in documents if d.get("category") == category]

    result = []
    for doc in documents[:limit]:
        result.append(Document(
            doc_id=doc.get("doc_id", ""),
            title=doc.get("title", ""),
            content=doc.get("content", ""),
            category=doc.get("category", ""),
            tags=doc.get("tags", [])
        ))

    return result


@app.get("/document/{doc_id}", response_model=Document)
async def get_document(doc_id: str):
    """Get a specific document by ID"""
    documents = corpus_data.get("documents", [])

    for doc in documents:
        if doc.get("doc_id") == doc_id:
            return Document(
                doc_id=doc.get("doc_id", ""),
                title=doc.get("title", ""),
                content=doc.get("content", ""),
                category=doc.get("category", ""),
                tags=doc.get("tags", [])
            )

    return {"error": "Document not found"}


@app.get("/categories", response_model=List[CategoryStats])
async def get_categories():
    """Get category statistics"""
    documents = corpus_data.get("documents", [])

    category_map = {}
    for doc in documents:
        cat = doc.get("category", "unknown")
        if cat not in category_map:
            category_map[cat] = {"count": 0, "documents": []}
        category_map[cat]["count"] += 1
        category_map[cat]["documents"].append(doc.get("title", ""))

    result = []
    for cat, data in sorted(category_map.items(), key=lambda x: -x[1]["count"]):
        result.append(CategoryStats(
            category=cat,
            count=data["count"],
            documents=data["documents"]
        ))

    return result


def keyword_search(query: str, documents: list, top_k: int = 5) -> list:
    """Simple keyword-based search across documents."""
    query_lower = query.lower()
    results = []

    for doc in documents:
        content = doc.get("content", "").lower()
        title = doc.get("title", "").lower()
        tags = [t.lower() for t in doc.get("tags", [])]

        score = 0
        if query_lower in title:
            score += 3
        if query_lower in content:
            score += 2
        for tag in tags:
            if query_lower in tag:
                score += 1

        query_words = query_lower.split()
        for word in query_words:
            if word in content:
                score += 0.5
            if word in title:
                score += 1

        if score > 0:
            results.append({
                "doc_id": doc.get("doc_id", ""),
                "chunk_id": doc.get("doc_id", "") + "_0",
                "title": doc.get("title", ""),
                "content": doc.get("content", "")[:500] + "..." if len(doc.get("content", "")) > 500 else doc.get("content", ""),
                "category": doc.get("category", ""),
                "tags": doc.get("tags", []),
                "score": float(score)
            })

    results.sort(key=lambda x: -x["score"])
    return results[:top_k]


def semantic_search(query: str, top_k: int = 5) -> list:
    """Semantic search using FAISS + SentenceBERT embeddings."""
    global faiss_index, embedding_model, chunk_embeddings, chunks_data

    if embedding_model is None or faiss_index is None or faiss_index.ntotal == 0:
        return []

    try:
        query_emb = embedding_model.encode([query], normalize_embeddings=True).astype("float32")
        scores, indices = faiss_index.search(query_emb, min(top_k * 2, faiss_index.ntotal))

        results = []
        seen_docs = set()

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(chunks_data):
                continue

            chunk = chunks_data[idx]
            doc_id = chunk.get("doc_id", "")

            # Deduplicate by doc_id (return best chunk per doc)
            if doc_id in seen_docs:
                continue
            seen_docs.add(doc_id)

            # Find the full document to get tags
            doc_match = None
            for doc in corpus_data.get("documents", []):
                if doc.get("doc_id") == doc_id:
                    doc_match = doc
                    break

            tags = doc_match.get("tags", []) if doc_match else []
            full_content = doc_match.get("content", chunk.get("content", "")) if doc_match else chunk.get("content", "")

            results.append({
                "doc_id": doc_id,
                "chunk_id": chunk.get("chunk_id", doc_id + "_0"),
                "title": chunk.get("title", ""),
                "content": full_content[:500] + "..." if len(full_content) > 500 else full_content,
                "category": chunk.get("category", ""),
                "tags": tags if isinstance(tags, list) else [],
                "score": round(float(score) * 10, 2),  # Scale FAISS cosine sim to ~0-10
            })

            if len(results) >= top_k:
                break

        return results

    except Exception as e:
        print(f"[RAG] Semantic search error: {e}")
        return []


def hybrid_search(query: str, documents: list, top_k: int = 5, alpha: float = 0.5) -> list:
    """Hybrid search combining keyword + semantic results via Reciprocal Rank Fusion."""
    kw_results = keyword_search(query, documents, top_k=top_k * 2)
    sem_results = semantic_search(query, top_k=top_k * 2)

    # Reciprocal Rank Fusion with k=60
    rrf_k = 60
    fused_scores = {}

    for rank, r in enumerate(kw_results):
        doc_id = r["doc_id"]
        fused_scores[doc_id] = fused_scores.get(doc_id, 0) + (1.0 / (rrf_k + rank + 1))

    for rank, r in enumerate(sem_results):
        doc_id = r["doc_id"]
        fused_scores[doc_id] = fused_scores.get(doc_id, 0) + (1.0 / (rrf_k + rank + 1))

    # Merge results, preferring semantic result data when available
    result_map = {}
    for r in kw_results + sem_results:
        doc_id = r["doc_id"]
        if doc_id not in result_map or r.get("score", 0) > result_map[doc_id].get("score", 0):
            result_map[doc_id] = r

    # Sort by fused score
    sorted_ids = sorted(fused_scores, key=lambda x: -fused_scores[x])
    results = []
    for doc_id in sorted_ids[:top_k]:
        if doc_id in result_map:
            entry = result_map[doc_id].copy()
            entry["score"] = round(fused_scores[doc_id] * 100, 2)  # Scale for display
            results.append(entry)

    return results


async def perform_search(q: str, method: str = "keyword", top_k: int = 5):
    """Helper function to search documents with multiple retrieval methods."""
    documents = corpus_data.get("documents", [])
    query_lower = q.lower()
    results = []

    if method == "semantic" and embedding_model is not None and faiss_index is not None:
        results = semantic_search(q, top_k)
    elif method == "hybrid" and embedding_model is not None and faiss_index is not None:
        results = hybrid_search(q, documents, top_k)
    else:
        # Default keyword search
        results = keyword_search(q, documents, top_k)

    # Internal Fallback (from CATEGORIZED_TREATMENTS)
    if not results:
        for disease, cats in CATEGORIZED_TREATMENTS.items():
            if disease.lower() in query_lower:
                combined_info = " | ".join(cats["organic"] + cats["manual"])
                results.append({
                    "doc_id": "internal_" + disease,
                    "chunk_id": "internal_" + disease + "_0",
                    "title": f"Internal Guide: {disease}",
                    "content": f"Expert treatment options for {disease}: {combined_info}",
                    "category": "Treatment Guidance",
                    "tags": ["internal", disease],
                    "score": 10.0
                })

    results.sort(key=lambda x: -x.get("score", 0))
    return results[:top_k]


@app.get("/search")
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    method: str = Query(default="hybrid", description="Search method: keyword, semantic, hybrid"),
    top_k: int = Query(default=5, le=20, description="Number of results")
):
    """Search documents using keyword, semantic (FAISS), or hybrid retrieval."""
    results = await perform_search(q, method, top_k)

    return SearchResponse(
        query=q,
        method=method,
        results=[SearchResult(**r) for r in results],
        total_results=len(results)
    )


@app.get("/metadata")
async def get_metadata():
    """Get corpus metadata"""
    return corpus_data.get("metadata", {})


@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    documents = corpus_data.get("documents", [])
    categories = set(d.get("category") for d in documents)

    return {
        "total_documents": len(documents),
        "total_chunks": len(chunks_data),
        "total_categories": len(categories),
        "categories": list(categories),
        "embedding_model": "all-MiniLM-L6-v2",
        "embedding_dim": 384,
        "semantic_search_ready": faiss_index is not None and embedding_model is not None,
        "faiss_vectors": faiss_index.ntotal if faiss_index is not None else 0,
    }


# =====================================================
# AUTO-SCRAPER & INDEX REBUILD ENDPOINTS
# =====================================================

def _run_scraper_pipeline():
    """Run scraper + index rebuild in background thread."""
    global scraper_status
    try:
        scraper_status["running"] = True
        scraper_status["error"] = None
        scraper_status["completed"] = False

        # Phase 1: Scrape
        scraper_status.update({"phase": "scraping", "progress": 10, "message": "Scraping tea content from Wikipedia..."})
        from auto_scraper import TeaAutoScraper
        scraper = TeaAutoScraper(str(CORPUS_PATH))

        def on_progress(status):
            scraper_status["phase"] = status.get("phase", "scraping")
            scraper_status["message"] = f"Scraping: {status.get('current_topic', '')} ({status.get('progress', 0)}/{status.get('total', 0)})"
            # Map scraper progress to 10-50% range
            total = status.get("total", 1) or 1
            scraper_status["progress"] = 10 + int((status.get("progress", 0) / total) * 40)

        scraper.progress_callback = on_progress
        result = scraper.run()
        scraper_status["new_documents"] = result.get("new_documents", 0)
        scraper_status["total_documents"] = result.get("total_documents", 0)

        # Phase 2: Rebuild index
        if result.get("new_documents", 0) > 0:
            scraper_status.update({"phase": "rebuilding", "progress": 55, "message": "Rebuilding search index..."})
            from rebuild_index import IndexRebuilder
            rebuilder = IndexRebuilder()

            def on_rebuild_progress(status):
                scraper_status["phase"] = f"rebuild_{status.get('phase', '')}"
                scraper_status["message"] = status.get("message", "Rebuilding...")
                # Map rebuild progress to 55-95% range
                scraper_status["progress"] = 55 + int(status.get("progress", 0) * 0.4)

            rebuilder.progress_callback = on_rebuild_progress
            rebuild_result = rebuilder.rebuild()

            # Reload data into memory
            scraper_status.update({"phase": "reloading", "progress": 96, "message": "Reloading data..."})
            load_data()
            load_semantic_models()

        scraper_status.update({
            "phase": "done",
            "progress": 100,
            "message": f"Done! Added {result.get('new_documents', 0)} new documents.",
            "completed": True,
            "running": False,
        })

    except Exception as e:
        scraper_status.update({
            "phase": "error",
            "error": str(e),
            "running": False,
            "completed": True,
            "message": f"Error: {e}",
        })
        import traceback
        traceback.print_exc()


@app.post("/scrape-and-update")
async def scrape_and_update():
    """Trigger auto-scraper to fetch tea content from Wikipedia and rebuild the RAG index."""
    global scraper_status

    if scraper_status.get("running"):
        return {"status": "already_running", "message": "Scraper is already running.", "progress": scraper_status}

    # Reset status
    scraper_status = {
        "running": True,
        "phase": "starting",
        "progress": 0,
        "message": "Starting auto-scraper...",
        "new_documents": 0,
        "total_documents": 0,
        "completed": False,
        "error": None,
    }

    # Run in background thread
    thread = threading.Thread(target=_run_scraper_pipeline, daemon=True)
    thread.start()

    return {"status": "started", "message": "Auto-scraper started in background."}


@app.get("/scrape-status")
async def get_scrape_status():
    """Get the current status of the auto-scraper pipeline."""
    return scraper_status


# =====================================================
# DETECTION ENDPOINTS
# =====================================================

DAMAGED_CLASSES = ['Damage_Spot', 'Damaged_Leaf']


def crop_and_diagnose_damaged(image_bytes, detections):
    """Crop damaged leaf regions and run disease CNN on each crop."""
    from PIL import Image as PILImage
    from io import BytesIO

    image = PILImage.open(BytesIO(image_bytes))
    image_np = np.array(image)
    if len(image_np.shape) == 2:
        image_np = cv2.cvtColor(image_np, cv2.COLOR_GRAY2RGB)
    elif image_np.shape[2] == 4:
        image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)

    h, w = image_np.shape[:2]
    disease_results = []

    for i, det in enumerate(detections):
        if det['class'] not in DAMAGED_CLASSES:
            continue
        x1, y1, x2, y2 = det['bbox']
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 - x1 < 10 or y2 - y1 < 10:
            continue

        crop = image_np[y1:y2, x1:x2]
        crop_resized = cv2.resize(crop, (256, 256))
        img_array = np.expand_dims(crop_resized, axis=0)

        prediction = disease_model.predict(img_array, verbose=0)[0]
        idx = int(np.argmax(prediction))
        disease_name = DISEASE_CLASSES[idx]
        disease_conf = float(prediction[idx])

        # Encode crop as base64
        crop_bgr = cv2.cvtColor(crop, cv2.COLOR_RGB2BGR)
        _, buffer = cv2.imencode('.jpg', crop_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
        crop_b64 = base64.b64encode(buffer).decode('utf-8')

        all_probs = {DISEASE_CLASSES[j]: round(float(prediction[j]) * 100, 1) for j in range(len(DISEASE_CLASSES))}

        # Get treatment if diseased
        treatment = None
        if disease_name != "Healthy":
            treat_info = CATEGORIZED_TREATMENTS.get(disease_name, {})
            treatment = {
                "organic": treat_info.get("organic", []),
                "manual": treat_info.get("manual", []),
                "chemical": treat_info.get("chemical", []),
            }

        disease_results.append({
            "crop_index": len(disease_results) + 1,
            "crop_image": crop_b64,
            "bbox": [x1, y1, x2, y2],
            "detection_class": det['class'],
            "detection_confidence": det['confidence'],
            "disease": disease_name,
            "disease_confidence": round(disease_conf * 100, 1),
            "all_probabilities": all_probs,
            "has_disease": disease_name != "Healthy",
            "treatment": treatment,
        })

    return disease_results


@app.post("/detect")
async def detect_image(
    file: UploadFile = File(...),
    confidence: float = Form(default=0.20),
    use_sahi: bool = Form(default=False),
    model: str = Form(default="teanet_pro")
):
    """Run YOLOv8 detection on uploaded tea leaf image, then diagnose damaged leaves"""
    image_bytes = await file.read()
    result = run_detection(image_bytes, confidence, use_sahi, model_key=model)

    # If detection found damaged leaves, crop and run disease CNN
    if not result.get('error') and result.get('detections'):
        damaged_count = sum(1 for d in result['detections'] if d['class'] in DAMAGED_CLASSES)
        if damaged_count > 0:
            disease_results = crop_and_diagnose_damaged(image_bytes, result['detections'])
            result['disease_analysis'] = {
                'total_damaged_crops': len(disease_results),
                'crops': disease_results,
            }
        else:
            result['disease_analysis'] = {
                'total_damaged_crops': 0,
                'crops': [],
                'message': 'No damaged leaves found - all leaves appear healthy!',
            }
    return result


@app.post("/classify")
async def classify_image(
    file: UploadFile = File(...),
    model: str = Form(default="mlp")
):
    """Run ML quality classification on uploaded tea leaf image"""
    image_bytes = await file.read()
    result = run_classification(image_bytes, model_key=model)
    return result


@app.get("/models")
async def get_models():
    """Get all available models (YOLO + ML) with friendly names and stats"""
    yolo_list = []
    for key, info in YOLO_MODELS.items():
        yolo_list.append({
            "id": key,
            "name": info["name"],
            "description": info["description"],
            "tag": info.get("tag", ""),
            "available": key in loaded_yolo_models,
        })

    ml_list = []
    for key, info in ML_MODELS_REGISTRY.items():
        ml_list.append({
            "id": key,
            "name": info["name"],
            "description": info["description"],
            "tag": info.get("tag", ""),
            "test_acc": info.get("test_acc"),
            "f1": info.get("f1"),
            "available": key in loaded_ml_models,
        })

    return {
        "yolo_models": yolo_list,
        "ml_models": ml_list,
        "sahi_available": SAHI_AVAILABLE,
    }


@app.post("/analyze-environment")
async def analyze_env(
    file: UploadFile = File(...),
    camera_distance: float = Form(default=0),
):
    """Analyze image environment: lighting conditions + auto leaf dimensions"""
    image_bytes = await file.read()
    dist = camera_distance if camera_distance > 0 else None
    result = analyze_environment(image_bytes, camera_distance_cm=dist)
    return result


@app.get("/detection/info")
async def detection_info():
    """Get detection system information"""
    return {
        "classes": CLASS_NAMES,
        "class_colors": {k: f"rgb({r},{g},{b})" for k, (r, g, b) in CLASS_COLORS.items()},
        "quality_classes": QUALITY_CLASSES,
        "sahi_available": SAHI_AVAILABLE
    }


# =====================================================
# DISEASE / INVASIVE / SEASONAL ENDPOINTS (Dinithi)
# =====================================================

@app.post("/predict-disease")
async def predict_disease(file: UploadFile = File(...)):
    """Predict tea leaf disease using CNN model"""
    image_bytes = await file.read()
    img = preprocess_image(image_bytes)

    prediction = disease_model.predict(img)[0]
    idx = int(np.argmax(prediction))
    disease_name = DISEASE_CLASSES[idx]

    base_info = CATEGORIZED_TREATMENTS.get(disease_name, CATEGORIZED_TREATMENTS["Healthy"])
    treatment_msg = base_info["organic"][0] if base_info["organic"] else "Consult expert"
    prevention_msg = base_info["manual"][0] if base_info["manual"] else "Monitor regularly"

    return {
        "predicted_disease": disease_name,
        "confidence": float(prediction[idx]),
        "treatment": treatment_msg,
        "prevention": prevention_msg,
        "has_issue": disease_name != "Healthy"
    }


@app.post("/predict-invasive")
async def predict_invasive(file: UploadFile = File(...)):
    """Detect invasive species using CNN model"""
    image_bytes = await file.read()
    img = preprocess_image(image_bytes)

    prediction = invasive_model.predict(img)[0]
    idx = int(np.argmax(prediction))
    species_name = INVASIVE_CLASSES[idx]

    return {
        "species": species_name,
        "confidence": float(prediction[idx]),
        "solution": INVASIVE_SOLUTIONS.get(species_name, "No specific management advice available.")
    }


class SeasonalInput(BaseModel):
    month: int
    season: str
    region: str
    temperature: float
    humidity: float
    rainfall: float

@app.post("/seasonal-predict")
async def seasonal_predict(data: SeasonalInput):
    """Predict seasonal tea disease using ensemble ML model"""
    season_map = {"dry": 0, "intermediate": 1, "wet": 2}
    season_encoded = season_map.get(data.season.lower(), 1)

    region_map = {"mid-country": 0, "low-country": 1, "high-country": 2}
    region_encoded = region_map.get(data.region.lower(), 0)

    season_region = season_encoded * region_encoded
    temp_humidity = data.temperature * data.humidity

    input_data = pd.DataFrame([{
        "Month": data.month,
        "Season": season_encoded,
        "Region": region_encoded,
        "Temperature_C": data.temperature,
        "Humidity_%": data.humidity,
        "Rainfall_mm": data.rainfall,
        "Temp_Humidity": temp_humidity,
        "Season_Region": season_region
    }])

    prediction = seasonal_model.predict(input_data)[0]
    risk_level = "Low" if str(prediction) == "Healthy" else "High"

    return {
        "predicted_disease": str(prediction),
        "risk_level": risk_level
    }


class TreatmentRequest(BaseModel):
    disease: str
    spot_color: str
    severity: str
    spread_rate: str
    weather: str
    leaf_stage: str
    preferred_method: str

@app.post("/recommend-treatment")
async def recommend_treatment(data: TreatmentRequest):
    """Rule-based expert system for treatment recommendations"""
    disease = data.disease
    method = data.preferred_method.lower()

    base_info = CATEGORIZED_TREATMENTS.get(disease, CATEGORIZED_TREATMENTS["Healthy"])

    summary = f"Based on your report of {disease} with {data.severity} severity and {data.weather} weather conditions, we recommend the following expert actions."

    if data.severity.lower() == "high":
        summary += " WARNING: High severity requires immediate aggressive intervention."

    if data.weather.lower() == "wet":
        summary += " Rain may wash away topical treatments. Consider systemic options or increasing frequency."

    return {
        "disease": disease,
        "organic": base_info["organic"],
        "manual": base_info["manual"],
        "chemical": base_info["chemical"],
        "summary": summary,
        "recommendation": base_info.get(method, base_info["organic"])
    }


class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_assistant(data: ChatRequest):
    """Conversational NLP assistant using RAG knowledge"""
    query = data.message

    results = await perform_search(q=query, top_k=2)

    if not results:
        return {
            "response": "I couldn't find specific information about that in our tea database. However, generally for tea plantation issues, it's best to monitor humidity levels and inspect leaf undersides for pests.",
            "source": None,
            "actions": ["Consult an agricultural officer", "Check environmental sensors"]
        }

    top_hit = results[0]

    disease_context = ""
    for d in DISEASE_CLASSES:
        if d.lower() in query.lower() or d.lower() in top_hit["title"].lower():
            disease_context = d
            break

    response_text = f"According to our tea knowledge base, '{top_hit['title']}' seems to match your query. {top_hit['content']}"

    actions = ["Improve plantation drainage", "Monitor leaf moisture levels"]
    if disease_context:
        actions.append(f"View treatment for {disease_context}")

    return {
        "response": response_text,
        "source": top_hit["title"],
        "actions": actions,
        "disease_detected": disease_context
    }


# =====================================================
# YIELD PREDICTION ENDPOINTS (Objective 2 - Harsha)
# =====================================================

@app.get("/yield/fields")
async def yield_fields():
    """Get all available field models organized by division"""
    return get_fields()


@app.get("/yield/field/{field_key}")
async def yield_field_info(field_key: str):
    """Get detailed info about a specific field model"""
    info = get_field_info(field_key)
    if info is None:
        return {"error": "Field not found"}
    return info


@app.get("/yield/best/{field_key}")
async def yield_best_month(field_key: str):
    """Get the historical best-performing month for a field"""
    result = get_best_month(field_key)
    if result is None:
        return {"error": "Field not found or no data"}
    return result


@app.post("/yield/predict")
async def yield_predict(
    field_key: str = Form(...),
    months: int = Form(default=1),
    rainfall: float = Form(default=0),
    wet_days: float = Form(default=0),
    plucking_rounds: float = Form(default=0),
    months_after_pruning: float = Form(default=12),
):
    """
    Predict next month's tea yield for a specific field.
    User inputs: rainfall, wet_days, plucking_rounds, months_after_pruning.
    Fertilizer effects are incorporated internally through historical lagged variables.
    """
    return predict_yield(
        field_key=field_key,
        months_ahead=months,
        rainfall=rainfall if rainfall > 0 else None,
        wet_days=wet_days if wet_days > 0 else None,
        plucking_rounds=plucking_rounds if plucking_rounds > 0 else None,
        months_after_pruning=months_after_pruning if months_after_pruning > 0 else None,
    )


@app.get("/yield/stats")
async def yield_stats():
    """Get yield prediction system stats"""
    fields_data = get_fields()
    return {
        "total_models": len(sarimax_models),
        "divisions": list(fields_data.get("divisions", {}).keys()),
        "model_type": "SARIMAX",
        "description": "Monthly Tea Yield Prediction using Seasonal ARIMA with Exogenous Variables",
    }


# =====================================================
# LOGBOOK OCR ENDPOINTS (Objective 2 - IT22222268)
# =====================================================

@app.post("/ocr/extract")
async def ocr_extract(file: UploadFile = File(...)):
    """
    Extract table data from a scanned logbook image using PaddleOCR.
    Pipeline: perspective correction -> grid detection -> cell OCR ->
    fuzzy post-processing -> structured JSON output with template Excel.
    """
    contents = await file.read()

    def _run_ocr(img_bytes):
        try:
            t0 = time.time()
            result = process_logbook_image(img_bytes)
            elapsed = round(time.time() - t0, 1)

            if "error" in result:
                return result

            # Set execution time
            result["processing_time_seconds"] = elapsed
            return result
        except Exception as e:
            return {"error": str(e)}

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _run_ocr, contents)
    return result


@app.get("/ocr/status")
async def ocr_status():
    """Check if OCR engine is available"""
    from logbook_ocr import OCR_ENGINE
    return {
        "available": OCR_ENGINE is not None,
        "engine": "PaddleOCR PP-OCRv5",
        "description": "Logbook OCR - extracts yield data from scanned tea plantation records (optimized single-engine processing)",
    }


@app.post("/ocr/extract-excel")
async def ocr_extract_excel(request: dict):
    """
    Return the Excel file generated by /ocr/extract.
    If an excel_file path exists in the request, return that file directly.
    Otherwise, fall back to generating a simple CSV-based Excel from the table data.
    """
    if "error" in request:
        return request

    # Generate Excel using the actual layout and template
    excel_bytes = export_to_excel(request)
    
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=logbook_ocr_output.xlsx"}
    )




# =====================================================
# MOBILE CAPTURE ENDPOINTS
# =====================================================

# In-memory storage for mobile-captured images
mobile_store = {"image": None, "timestamp": 0, "filename": "", "metadata": None}


def get_lan_ip():
    """Get the machine's LAN IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@app.get("/network-info")
async def network_info():
    """Get LAN IP for mobile QR code connection"""
    return {
        "lan_ip": get_lan_ip(),
        "backend_port": 8000,
        "frontend_port": 3000,
    }


@app.post("/mobile/upload")
async def mobile_upload(file: UploadFile = File(...)):
    """Receive an image from mobile device and store it temporarily"""
    image_bytes = await file.read()
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    mobile_store["image"] = b64
    mobile_store["timestamp"] = time.time()
    mobile_store["filename"] = file.filename or "mobile_capture.jpg"
    mobile_store["metadata"] = None
    return {"status": "ok", "filename": file.filename, "size": len(image_bytes)}


@app.get("/mobile/latest")
async def mobile_latest():
    """Get the latest mobile-captured image (base64)"""
    if not mobile_store["image"]:
        return {"available": False}
    return {
        "available": True,
        "image": mobile_store["image"],
        "filename": mobile_store["filename"],
        "timestamp": mobile_store["timestamp"],
        "metadata": mobile_store.get("metadata"),
    }


@app.delete("/mobile/clear")
async def mobile_clear():
    """Clear the stored mobile image"""
    mobile_store["image"] = None
    mobile_store["timestamp"] = 0
    mobile_store["filename"] = ""
    mobile_store["metadata"] = None
    return {"status": "cleared"}


# =====================================================
# TEAVISION ANDROID APP ENDPOINT
# =====================================================

@app.post("/api/upload")
async def teavision_upload(
    image: UploadFile = File(...),
    metadata: str = Form(default="{}")
):
    """
    Receive image + metadata from TeaVision Android app.
    Stores the image so the web frontend can pick it up,
    and runs detection + classification automatically.
    """
    image_bytes = await image.read()
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    # Parse metadata JSON from TeaVision
    try:
        meta = json.loads(metadata)
    except Exception:
        meta = {}

    # Store for desktop frontend to pick up
    mobile_store["image"] = b64
    mobile_store["timestamp"] = time.time()
    mobile_store["filename"] = image.filename or "teavision_capture.jpg"
    mobile_store["metadata"] = meta

    # Auto-run detection + classification
    detection_result = None
    classification_result = None
    try:
        detection_result = run_detection(image_bytes, confidence=0.20, use_sahi=False, model_key="teanet_pro")
        # Remove the large base64 annotated image from stored response to keep it light
        detection_summary = {
            "total_detections": detection_result.get("total_detections", 0),
            "quality_grade": detection_result.get("quality_grade", "N/A"),
            "class_counts": detection_result.get("class_counts", {}),
        }
    except Exception:
        detection_summary = None

    try:
        classification_result = run_classification(image_bytes, model_key="mlp")
        classification_summary = {
            "prediction": classification_result.get("prediction", "unknown"),
            "confidence": classification_result.get("confidence", {}),
            "model_used": classification_result.get("model_used", ""),
        }
    except Exception:
        classification_summary = None

    return {
        "status": "success",
        "message": "Image received and analyzed",
        "filename": image.filename,
        "size": len(image_bytes),
        "detection": detection_summary,
        "classification": classification_summary,
        "teavision_metadata": {
            "device": meta.get("device", {}),
            "measurement": meta.get("measurement", {}),
            "quality": meta.get("quality", {}),
            "color_analysis": meta.get("color_analysis", {}),
            "light_analysis": meta.get("light_analysis", {}),
            "capture": meta.get("capture", {}),
        }
    }


# =====================================================
# GOOGLE CUSTOM SEARCH - Disease Web Lookup
# =====================================================

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "")


@app.get("/google-disease-search")
async def google_disease_search(
    disease: str = Query(..., description="Disease name to search"),
    num_results: int = Query(default=6, le=10, description="Number of results")
):
    """Search Google for tea leaf disease information and research articles."""
    if not GOOGLE_API_KEY or not GOOGLE_SEARCH_ENGINE_ID:
        return {
            "results": [],
            "error": "Google API not configured. Add GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID to .env"
        }

    query = f"tea leaf {disease} disease treatment causes symptoms"
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_SEARCH_ENGINE_ID,
        "q": query,
        "num": num_results,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            data = resp.json()

        items = data.get("items", [])
        results = []
        for item in items:
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": item.get("displayLink", ""),
                "thumbnail": (item.get("pagemap", {}).get("cse_thumbnail", [{}])[0].get("src", "")
                              if item.get("pagemap", {}).get("cse_thumbnail") else ""),
            })

        return {"disease": disease, "query": query, "results": results}

    except Exception as e:
        return {"results": [], "error": str(e)}


# =====================================================
# AI-GENERATED ANSWER FROM RAG RESULTS
# =====================================================

@app.get("/generate-answer")
async def generate_answer(
    q: str = Query(..., min_length=1, description="Question to answer"),
    method: str = Query(default="hybrid", description="Search method"),
):
    """Generate a comprehensive AI-composed answer from RAG search results."""
    results = await perform_search(q, method, top_k=5)

    if not results:
        return {
            "query": q,
            "answer": "No relevant information found in our tea knowledge base for this query. Try different keywords or browse by category.",
            "sources": [],
            "confidence": 0,
        }

    # Build answer from top results
    source_contents = []
    sources = []
    for r in results[:5]:
        source_contents.append(r["content"])
        sources.append({"title": r["title"], "category": r["category"], "score": r["score"]})

    combined = "\n\n".join(source_contents)

    # Extract key sentences that relate to the query
    query_terms = set(q.lower().split())
    sentences = []
    for text in source_contents:
        for sent in text.replace(". ", ".\n").split("\n"):
            sent = sent.strip()
            if not sent or len(sent) < 20:
                continue
            sent_lower = sent.lower()
            relevance = sum(1 for t in query_terms if t in sent_lower)
            if relevance > 0:
                sentences.append((relevance, sent))

    sentences.sort(key=lambda x: -x[0])
    best_sentences = [s[1] for s in sentences[:6]]

    if best_sentences:
        answer = " ".join(best_sentences)
    else:
        # Fallback: use first 3 content snippets
        answer = " ".join(c[:300] for c in source_contents[:3])

    # Add disease-specific treatment if applicable
    disease_match = None
    for d in DISEASE_CLASSES:
        if d.lower() in q.lower() or d.lower() in answer.lower():
            disease_match = d
            break

    treatment_info = None
    if disease_match and disease_match in CATEGORIZED_TREATMENTS:
        t = CATEGORIZED_TREATMENTS[disease_match]
        treatment_info = {
            "disease": disease_match,
            "organic": t["organic"][:2],
            "chemical": t["chemical"][:1],
        }

    avg_score = sum(r["score"] for r in results[:3]) / min(len(results), 3)
    confidence = min(avg_score / 10.0, 1.0)

    return {
        "query": q,
        "answer": answer,
        "sources": sources,
        "treatment": treatment_info,
        "confidence": round(confidence, 2),
    }


# =====================================================
# SEARCH FEEDBACK (Thumbs Up / Down)
# =====================================================

feedback_log = []


class FeedbackRequest(BaseModel):
    query: str
    doc_id: str
    title: str
    feedback: str  # "up" or "down"


@app.post("/search-feedback")
async def search_feedback(data: FeedbackRequest):
    """Record user feedback on search results for evaluation."""
    entry = {
        "query": data.query,
        "doc_id": data.doc_id,
        "title": data.title,
        "feedback": data.feedback,
        "timestamp": time.time(),
    }
    feedback_log.append(entry)

    # Persist to CSV
    feedback_path = Path(__file__).parent / "search_feedback.csv"
    write_header = not feedback_path.exists()
    with open(feedback_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["query", "doc_id", "title", "feedback", "timestamp"])
        if write_header:
            writer.writeheader()
        writer.writerow(entry)

    return {"status": "recorded", "total_feedback": len(feedback_log)}


@app.get("/search-feedback/stats")
async def feedback_stats():
    """Get aggregated feedback statistics."""
    total = len(feedback_log)
    up = sum(1 for f in feedback_log if f["feedback"] == "up")
    down = total - up
    return {
        "total": total,
        "positive": up,
        "negative": down,
        "satisfaction_rate": round(up / total * 100, 1) if total > 0 else 0,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=600)
