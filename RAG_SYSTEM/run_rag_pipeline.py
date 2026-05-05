"""
RAG Pipeline Script - Generate embeddings and indexes for the updated corpus
"""
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass
from tqdm import tqdm

import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

# Download NLTK data
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('punkt_tab', quiet=True)

print("=" * 60)
print("Tea Knowledge RAG System - Embedding Generation")
print("=" * 60)

# Check for required packages
try:
    from sentence_transformers import SentenceTransformer
    print("sentence-transformers loaded")
except ImportError:
    print("Installing sentence-transformers...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'sentence-transformers', '-q'])
    from sentence_transformers import SentenceTransformer

try:
    from rank_bm25 import BM25Okapi
    print("rank-bm25 loaded")
except ImportError:
    print("Installing rank-bm25...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'rank-bm25', '-q'])
    from rank_bm25 import BM25Okapi

try:
    import faiss
    print("faiss loaded")
except ImportError:
    print("Installing faiss-cpu...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'faiss-cpu', '-q'])
    import faiss

# Configuration
CORPUS_FILE = './tea_corpus.json'
PROCESSED_DIR = './data/processed'
EMBEDDINGS_DIR = './data/embeddings'
RESULTS_DIR = './results'

# Create directories
Path(PROCESSED_DIR).mkdir(parents=True, exist_ok=True)
Path(EMBEDDINGS_DIR).mkdir(parents=True, exist_ok=True)
Path(RESULTS_DIR).mkdir(parents=True, exist_ok=True)

# =============================================================================
# CHUNKING
# =============================================================================

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

class TextChunker:
    def __init__(self, chunk_size: int = 256, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def sentence_chunks(self, text: str, doc_id: str,
                        category: str, title: str, tags: List[str],
                        sentences_per_chunk: int = 5) -> List[Chunk]:
        """Split text by sentences"""
        sentences = sent_tokenize(text)
        chunks = []

        for i in range(0, len(sentences), sentences_per_chunk):
            chunk_sentences = sentences[i:i + sentences_per_chunk]
            chunk_text = ' '.join(chunk_sentences)

            chunks.append(Chunk(
                chunk_id=f"{doc_id}_{i // sentences_per_chunk}",
                doc_id=doc_id,
                content=chunk_text,
                category=category,
                title=title,
                chunk_index=i // sentences_per_chunk,
                total_chunks=-1,
                tags=tags
            ))

        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        return chunks

# =============================================================================
# MAIN PIPELINE
# =============================================================================

print("\n1. Loading corpus...")
with open(CORPUS_FILE, 'r', encoding='utf-8') as f:
    corpus_data = json.load(f)

documents = corpus_data['documents']
print(f"   Loaded {len(documents)} documents")

# Create chunks
print("\n2. Creating chunks...")
chunker = TextChunker(chunk_size=200, overlap=40)
all_chunks = []

for doc in tqdm(documents, desc="   Chunking"):
    doc_chunks = chunker.sentence_chunks(
        text=doc['content'],
        doc_id=doc['doc_id'],
        category=doc['category'],
        title=doc['title'],
        tags=doc['tags'],
        sentences_per_chunk=4
    )
    all_chunks.extend(doc_chunks)

print(f"   Created {len(all_chunks)} chunks from {len(documents)} documents")

# Convert to DataFrame
chunks_df = pd.DataFrame([
    {
        'chunk_id': c.chunk_id,
        'doc_id': c.doc_id,
        'content': c.content,
        'category': c.category,
        'title': c.title,
        'chunk_index': c.chunk_index,
        'total_chunks': c.total_chunks,
        'tags': c.tags,
        'word_count': len(c.content.split())
    }
    for c in all_chunks
])

# Save chunks
chunks_df.to_csv(f'{PROCESSED_DIR}/chunks.csv', index=False)
print(f"   Saved chunks to {PROCESSED_DIR}/chunks.csv")

# Load embedding model
print("\n3. Loading embedding model...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
print(f"   Model: all-MiniLM-L6-v2")
print(f"   Embedding dimension: {embedding_model.get_sentence_embedding_dimension()}")

# Generate embeddings
print("\n4. Generating embeddings...")
chunk_texts = chunks_df['content'].tolist()

embeddings = embedding_model.encode(
    chunk_texts,
    show_progress_bar=True,
    convert_to_numpy=True,
    normalize_embeddings=True
)

print(f"   Generated {len(embeddings)} embeddings")
print(f"   Shape: {embeddings.shape}")

# Save embeddings
np.save(f'{EMBEDDINGS_DIR}/chunk_embeddings.npy', embeddings)
chunk_ids = chunks_df['chunk_id'].tolist()
with open(f'{EMBEDDINGS_DIR}/chunk_ids.json', 'w') as f:
    json.dump(chunk_ids, f)
print(f"   Saved embeddings to {EMBEDDINGS_DIR}/")

# Create FAISS index
print("\n5. Creating FAISS index...")
dimension = embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)
index.add(embeddings.astype('float32'))
faiss.write_index(index, f'{EMBEDDINGS_DIR}/faiss_index.bin')
print(f"   FAISS index created with {index.ntotal} vectors")

# Create BM25 index
print("\n6. Creating BM25 index...")
stop_words = set(stopwords.words('english'))

def tokenize_for_bm25(text: str) -> List[str]:
    tokens = word_tokenize(text.lower())
    tokens = [t for t in tokens if t.isalnum() and t not in stop_words]
    return tokens

tokenized_chunks = [tokenize_for_bm25(text) for text in tqdm(chunk_texts, desc="   Tokenizing")]
bm25 = BM25Okapi(tokenized_chunks)

with open(f'{EMBEDDINGS_DIR}/bm25_index.pkl', 'wb') as f:
    pickle.dump(bm25, f)
with open(f'{EMBEDDINGS_DIR}/tokenized_chunks.pkl', 'wb') as f:
    pickle.dump(tokenized_chunks, f)
print(f"   BM25 index created")

# Save system config
print("\n7. Saving system configuration...")
system_config = {
    'project': '25-26J-133',
    'embedding_model': 'all-MiniLM-L6-v2',
    'embedding_dim': 384,
    'total_documents': len(documents),
    'total_chunks': len(chunks_df),
    'chunk_strategy': 'sentence_based',
    'sentences_per_chunk': 4,
    'retrieval_methods': ['dense', 'bm25', 'hybrid'],
    'default_top_k': 5
}

with open(f'{EMBEDDINGS_DIR}/system_config.json', 'w') as f:
    json.dump(system_config, f, indent=2)

# Test search
print("\n8. Testing retrieval...")
test_query = "What are Ceylon tea grades?"
query_emb = embedding_model.encode([test_query], normalize_embeddings=True).astype('float32')
scores, indices = index.search(query_emb, 3)

print(f"   Query: '{test_query}'")
print(f"   Top 3 results:")
for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
    chunk = chunks_df.iloc[idx]
    print(f"     {i+1}. [{chunk['category']}] {chunk['title'][:50]}... (score: {score:.4f})")

print("\n" + "=" * 60)
print("RAG Pipeline Complete!")
print("=" * 60)
print(f"\nSummary:")
print(f"  - Documents: {len(documents)}")
print(f"  - Chunks: {len(chunks_df)}")
print(f"  - Embeddings: {embeddings.shape}")
print(f"  - FAISS vectors: {index.ntotal}")
print(f"\nFiles saved:")
print(f"  - {PROCESSED_DIR}/chunks.csv")
print(f"  - {EMBEDDINGS_DIR}/chunk_embeddings.npy")
print(f"  - {EMBEDDINGS_DIR}/faiss_index.bin")
print(f"  - {EMBEDDINGS_DIR}/bm25_index.pkl")
print(f"  - {EMBEDDINGS_DIR}/system_config.json")
