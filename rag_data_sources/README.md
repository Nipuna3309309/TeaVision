# Ceylon Tea RAG – Curated Source Manifest (v1)

This folder contains a curated **source manifest** for building a Retrieval-Augmented Generation (RAG) knowledge base about Sri Lankan tea (Ceylon tea).

## Files
- `ceylon_tea_rag_sources.csv` – spreadsheet-friendly manifest
- `ceylon_tea_rag_sources.jsonl` – JSON Lines manifest (recommended for pipelines)
- `download_sources.py` – optional downloader + text extractor scaffold
- `requirements.txt` – suggested Python deps for the downloader

## Recommended pipeline (practical + citation-friendly)
1. **Download raw docs** into `corpus/raw/` (PDF/HTML).
2. **Extract text** into `corpus/text/`.
3. **Chunk** text (e.g., 500–1200 tokens per chunk, 10–20% overlap).
4. **Embed + index** (FAISS / Qdrant / Pinecone / etc).
5. Store **metadata** per chunk:
   - `source_id`, `title`, `publisher`, `year`, `url`, `categories`
   - `retrieved_at` (ISO date)
   - `doc_sha256` and `chunk_sha256` (optional but great for auditability)

## Licensing
Most government/standards and institute PDFs are **copyrighted** unless explicitly stated.
For each downloaded file, keep:
- the PDF front page/license statement (if present)
- the website terms page URL
- your retrieval timestamp

Generated on: 2026-01-05
