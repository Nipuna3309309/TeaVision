"""
Rebuild RAG Index
Automatically re-chunks, re-embeds, and re-indexes the tea corpus.
Called after auto-scraping new content.

Project: 25-26J-133
"""

import json
import pickle
import numpy as np
import csv
from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass


# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────

RAG_DIR = Path(__file__).parent.parent
CORPUS_FILE = RAG_DIR / "tea_corpus.json"
PROCESSED_DIR = RAG_DIR / "data" / "processed"
EMBEDDINGS_DIR = RAG_DIR / "data" / "embeddings"

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
SENTENCES_PER_CHUNK = 4

# Create directories
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    content: str
    category: str
    title: str
    chunk_index: int
    total_chunks: int
    tags: List[str]


# ─────────────────────────────────────────────────────────
# Sentence Splitter (no NLTK dependency at import time)
# ─────────────────────────────────────────────────────────

def split_sentences(text: str) -> List[str]:
    """Simple sentence splitter that works without NLTK."""
    import re
    # Split on period/exclamation/question followed by space and capital letter
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    # Filter out very short fragments
    return [s.strip() for s in sentences if len(s.strip()) > 10]


def create_chunks(documents: List[dict], sentences_per_chunk: int = 4) -> List[Chunk]:
    """Split documents into chunks by sentences."""
    all_chunks = []

    for doc in documents:
        text = doc.get("content", "")
        doc_id = doc.get("doc_id", "")
        category = doc.get("category", "")
        title = doc.get("title", "")
        tags = doc.get("tags", [])

        sentences = split_sentences(text)
        if not sentences:
            # If sentence splitting fails, treat whole content as one chunk
            sentences = [text]

        doc_chunks = []
        for i in range(0, len(sentences), sentences_per_chunk):
            chunk_sentences = sentences[i:i + sentences_per_chunk]
            chunk_text = " ".join(chunk_sentences)

            doc_chunks.append(Chunk(
                chunk_id=f"{doc_id}_{i // sentences_per_chunk}",
                doc_id=doc_id,
                content=chunk_text,
                category=category,
                title=title,
                chunk_index=i // sentences_per_chunk,
                total_chunks=-1,
                tags=tags,
            ))

        for chunk in doc_chunks:
            chunk.total_chunks = len(doc_chunks)

        all_chunks.extend(doc_chunks)

    return all_chunks


# ─────────────────────────────────────────────────────────
# Main Rebuild Pipeline
# ─────────────────────────────────────────────────────────

class IndexRebuilder:
    """Rebuilds the full RAG index from the tea corpus."""

    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_callback = progress_callback
        self._status = {
            "phase": "idle",
            "progress": 0,
            "message": "",
            "completed": False,
        }

    @property
    def status(self) -> dict:
        return self._status.copy()

    def _update(self, **kwargs):
        self._status.update(kwargs)
        if self.progress_callback:
            self.progress_callback(self._status)

    def rebuild(self) -> dict:
        """Run the full rebuild pipeline."""
        self._update(phase="loading", progress=10, message="Loading corpus...")

        # 1. Load corpus
        print("1. Loading corpus...")
        with open(CORPUS_FILE, "r", encoding="utf-8") as f:
            corpus = json.load(f)

        documents = corpus.get("documents", [])
        print(f"   Loaded {len(documents)} documents")

        # 2. Create chunks
        self._update(phase="chunking", progress=20, message=f"Chunking {len(documents)} documents...")
        print("2. Creating chunks...")

        all_chunks = create_chunks(documents, SENTENCES_PER_CHUNK)
        print(f"   Created {len(all_chunks)} chunks")

        # Save chunks as CSV
        chunks_csv_path = PROCESSED_DIR / "chunks.csv"
        with open(chunks_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "chunk_id", "doc_id", "content", "category", "title",
                "chunk_index", "total_chunks", "tags", "word_count"
            ])
            writer.writeheader()
            for c in all_chunks:
                writer.writerow({
                    "chunk_id": c.chunk_id,
                    "doc_id": c.doc_id,
                    "content": c.content,
                    "category": c.category,
                    "title": c.title,
                    "chunk_index": c.chunk_index,
                    "total_chunks": c.total_chunks,
                    "tags": json.dumps(c.tags) if isinstance(c.tags, list) else c.tags,
                    "word_count": len(c.content.split()),
                })

        # 3. Generate embeddings
        self._update(phase="embedding", progress=40, message="Loading embedding model...")
        print("3. Loading embedding model...")

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            import subprocess, sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers", "-q"])
            from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        print(f"   Model: {EMBEDDING_MODEL_NAME} ({model.get_sentence_embedding_dimension()}d)")

        self._update(phase="embedding", progress=50, message=f"Embedding {len(all_chunks)} chunks...")
        print("4. Generating embeddings...")

        chunk_texts = [c.content for c in all_chunks]
        embeddings = model.encode(
            chunk_texts,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        print(f"   Generated {len(embeddings)} embeddings, shape: {embeddings.shape}")

        # Save embeddings
        np.save(EMBEDDINGS_DIR / "chunk_embeddings.npy", embeddings)
        chunk_ids = [c.chunk_id for c in all_chunks]
        with open(EMBEDDINGS_DIR / "chunk_ids.json", "w") as f:
            json.dump(chunk_ids, f)

        # 4. Create FAISS index
        self._update(phase="indexing", progress=70, message="Building FAISS index...")
        print("5. Creating FAISS index...")

        try:
            import faiss
        except ImportError:
            import subprocess, sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "faiss-cpu", "-q"])
            import faiss

        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings.astype("float32"))
        faiss.write_index(index, str(EMBEDDINGS_DIR / "faiss_index.bin"))
        print(f"   FAISS index: {index.ntotal} vectors")

        # 5. Create BM25 index
        self._update(phase="indexing", progress=85, message="Building BM25 index...")
        print("6. Creating BM25 index...")

        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            import subprocess, sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "rank-bm25", "-q"])
            from rank_bm25 import BM25Okapi

        import re
        stop_words = {"the", "a", "an", "in", "on", "at", "for", "to", "of", "and", "is", "it", "by", "with", "as", "from", "this", "that", "are", "was", "be", "or", "not"}

        def tokenize_bm25(text: str) -> List[str]:
            tokens = re.findall(r'\b\w+\b', text.lower())
            return [t for t in tokens if t not in stop_words and len(t) > 1]

        tokenized = [tokenize_bm25(t) for t in chunk_texts]
        bm25 = BM25Okapi(tokenized)

        with open(EMBEDDINGS_DIR / "bm25_index.pkl", "wb") as f:
            pickle.dump(bm25, f)
        with open(EMBEDDINGS_DIR / "tokenized_chunks.pkl", "wb") as f:
            pickle.dump(tokenized, f)

        # 6. Save system config
        self._update(phase="saving", progress=95, message="Saving configuration...")
        print("7. Saving system configuration...")

        config = {
            "project": "25-26J-133",
            "embedding_model": EMBEDDING_MODEL_NAME,
            "embedding_dim": int(embeddings.shape[1]),
            "total_documents": len(documents),
            "total_chunks": len(all_chunks),
            "chunk_strategy": "sentence_based",
            "sentences_per_chunk": SENTENCES_PER_CHUNK,
            "retrieval_methods": ["dense", "bm25", "hybrid"],
            "default_top_k": 5,
        }
        with open(EMBEDDINGS_DIR / "system_config.json", "w") as f:
            json.dump(config, f, indent=2)

        # 7. Quick test
        print("8. Quick search test...")
        test_query = "health benefits of Ceylon tea"
        query_emb = model.encode([test_query], normalize_embeddings=True).astype("float32")
        scores, indices = index.search(query_emb, 3)

        print(f"   Query: '{test_query}'")
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            c = all_chunks[idx]
            print(f"     {i+1}. [{c.category}] {c.title[:50]}... (score: {score:.4f})")

        self._update(phase="done", progress=100, message="Index rebuild complete!", completed=True)

        result = {
            "total_documents": len(documents),
            "total_chunks": len(all_chunks),
            "embedding_shape": list(embeddings.shape),
            "faiss_vectors": index.ntotal,
        }
        print(f"\n✅ Index rebuild complete: {result}")
        return result


# ─────────────────────────────────────────────────────────
# Standalone
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔧 Rebuilding RAG Index...")
    print("=" * 60)
    rebuilder = IndexRebuilder()
    result = rebuilder.rebuild()
    print("\n" + "=" * 60)
    print(f"📊 Final: {result}")
