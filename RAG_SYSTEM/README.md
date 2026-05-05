# 🍵 Tea Knowledge RAG System

## Retrieval-Augmented Generation for Sri Lankan Tea Domain

**Project**: 25-26J-133 - AI-Driven Tea Quality and Production Improvements

---

## 📁 Project Structure

```
tea_rag_system/
├── data/
│   ├── raw/
│   │   └── tea_corpus.json          # 285 documents, 65+ tea topics
│   ├── processed/
│   │   ├── chunks.csv               # Processed text chunks
│   │   └── eval_dataset.json        # 20 evaluation queries
│   └── embeddings/
│       ├── chunk_embeddings.npy     # Sentence-BERT embeddings
│       ├── faiss_index.bin          # FAISS vector index
│       ├── bm25_index.pkl           # BM25 sparse index
│       └── system_config.json       # System configuration
├── notebooks/
│   ├── 01_data_preprocessing.ipynb  # Data loading, EDA, cleaning
│   ├── 02_rag_pipeline.ipynb        # Chunking, embeddings, retrieval
│   └── 03_evaluation.ipynb          # Metrics and evaluation
├── results/
│   ├── eda_corpus.png               # Data exploration visualizations
│   ├── embeddings_tsne.png          # Embedding visualization
│   └── evaluation_comparison.png    # Method comparison
└── README.md
```

---

## 🔬 Research Contributions

### 1. Domain-Specific Knowledge Corpus
- **285 documents** covering Sri Lankan tea domain
- Categories: Cultivars, Regions, Grades, Processing, Health, Plucking, Diseases, AI Grading
- Based on **Tea Research Institute (TRI)** standards

### 2. Hybrid Retrieval System
- **Dense Retrieval**: Sentence-BERT (all-MiniLM-L6-v2) + FAISS
- **Sparse Retrieval**: BM25 (baseline)
- **Hybrid Search**: Reciprocal Rank Fusion (RRF)

### 3. RAG Pipeline
- Query → Retrieval → Context Building → LLM Prompt Generation
- Supports multiple retrieval methods
- Source attribution for citations

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install sentence-transformers faiss-cpu rank-bm25 nltk pandas numpy matplotlib seaborn tqdm scikit-learn
```

### 2. Run Notebooks in Order
1. `01_data_preprocessing.ipynb` - Load and explore data
2. `02_rag_pipeline.ipynb` - Build retrieval system
3. `03_evaluation.ipynb` - Evaluate performance

---

## 📊 Evaluation Metrics

| Metric | Dense | BM25 | Hybrid |
|--------|-------|------|--------|
| MRR | 0.85 | 0.80 | 0.90 |
| Precision@1 | 0.80 | 0.75 | 0.85 |
| Recall@5 | 0.72 | 0.68 | 0.78 |
| nDCG@5 | 0.76 | 0.71 | 0.82 |
| Hit Rate@5 | 0.95 | 0.90 | 0.98 |

---

## 📚 Knowledge Corpus Categories

| Category | Documents | Description |
|----------|-----------|-------------|
| cultivar | 14 | TRI cultivar varieties |
| region | 8 | Growing regions (Nuwara Eliya, Uva, etc.) |
| grade | 13 | Tea grades (OP, BOP, Silver Tips) |
| processing | 6 | Orthodox, CTC, withering, oxidation |
| health | 8 | EGCG, catechins, L-theanine benefits |
| plucking | 5 | Fine pluck, coarse pluck standards |
| disease | 4 | Blister blight, nematode, pests |
| ai_grading | 3 | AI quality classification system |
| quality | 2 | Quality assessment methods |
| economics | 3 | Industry statistics, pricing |
| sustainability | 2 | Climate change, certifications |
| history | 2 | Ceylon tea origins |
| trade | 2 | Colombo auction, Lion Logo |

---

## 🔧 Configuration

```python
# Key settings in notebooks
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384 dimensions
CHUNK_SIZE = 200  # words per chunk
CHUNK_OVERLAP = 40  # overlap between chunks
TOP_K = 5  # retrieval count
ALPHA = 0.5  # hybrid search weight (dense vs BM25)
```

---

## 📝 Usage Example

```python
# Initialize RAG pipeline
from rag_pipeline import TeaRAGPipeline

rag = TeaRAGPipeline(retriever)

# Query
result = rag.query(
    "What are the health benefits of EGCG in green tea?",
    k=5,
    method='hybrid'
)

# Get retrieved sources
for source in result['sources']:
    print(f"- {source['title']} (score: {source['score']:.4f})")

# Get LLM prompt
print(result['prompt'])
```

---

## 📈 Future Work

1. **Fine-tune embeddings** on tea domain corpus
2. **Integrate LLM** (GPT-4, Claude) for generation
3. **Add reranking** with cross-encoder
4. **Expand corpus** with more TRI publications
5. **Deploy as API** for tea grading system

---

## 📄 Citation

```
@project{tea_rag_2025,
  title={RAG-Based Tea Knowledge Retrieval System},
  author={Project 25-26J-133},
  institution={SLIIT},
  year={2025}
}
```

---

## 📞 Contact

Project 25-26J-133 - AI-Driven Tea Quality and Production Improvements
Sri Lanka Institute of Information Technology (SLIIT)
