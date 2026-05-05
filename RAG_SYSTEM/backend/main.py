"""
Tea RAG System - FastAPI Backend
Provides API endpoints for tea knowledge search and retrieval
"""

import json
import pickle
import numpy as np
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI(
    title="Tea RAG System API",
    description="API for Sri Lankan Tea Knowledge Retrieval",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data paths
DATA_DIR = Path(__file__).parent.parent
CORPUS_PATH = DATA_DIR / "tea_corpus.json"
CHUNKS_PATH = DATA_DIR / "data" / "processed" / "chunks.csv"
EMBEDDINGS_PATH = DATA_DIR / "data" / "embeddings"

# Global data storage
corpus_data = {}
chunks_data = []
chunk_embeddings = None
bm25_index = None
tokenized_chunks = []
chunk_ids = []


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
    """Load all data files on startup"""
    global corpus_data, chunks_data, chunk_embeddings, bm25_index, tokenized_chunks, chunk_ids

    # Load corpus
    with open(CORPUS_PATH, 'r', encoding='utf-8') as f:
        corpus_data = json.load(f)

    # Load chunks from CSV
    import csv
    chunks_path = DATA_DIR / "data" / "processed" / "chunks.csv"
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

    print(f"Loaded {len(corpus_data.get('documents', []))} documents")
    print(f"Loaded {len(chunks_data)} chunks")


@app.on_event("startup")
async def startup_event():
    """Load data when server starts"""
    load_data()


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Tea RAG System API",
        "version": "1.0.0",
        "endpoints": {
            "/documents": "Get all documents",
            "/categories": "Get category statistics",
            "/search": "Search documents",
            "/document/{doc_id}": "Get specific document"
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


@app.get("/search")
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    method: str = Query(default="keyword", description="Search method: keyword, semantic"),
    top_k: int = Query(default=5, le=20, description="Number of results")
):
    """Search documents using keyword matching"""
    documents = corpus_data.get("documents", [])
    query_lower = q.lower()

    results = []
    for doc in documents:
        content = doc.get("content", "").lower()
        title = doc.get("title", "").lower()
        tags = [t.lower() for t in doc.get("tags", [])]

        # Calculate relevance score
        score = 0
        if query_lower in title:
            score += 3
        if query_lower in content:
            score += 2
        for tag in tags:
            if query_lower in tag:
                score += 1

        # Check for partial word matches
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
                "score": score
            })

    # Sort by score and limit results
    results.sort(key=lambda x: -x["score"])
    results = results[:top_k]

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
        "embedding_dim": 384
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
