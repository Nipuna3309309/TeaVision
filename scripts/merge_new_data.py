"""
Script to merge new Ceylon tea data into the existing RAG corpus
"""
import json
import os
from pathlib import Path

# Paths
NEW_FOLDER = r"C:\Nipuna\TEST\New folder"
RAG_SYSTEM = r"C:\Nipuna\TEST\RAG_SYSTEM"
CORPUS_FILE = os.path.join(RAG_SYSTEM, "tea_corpus.json")
JSONL_FILE = os.path.join(NEW_FOLDER, "ceylon_tea_rag_sources.jsonl")
TEXT_FOLDER = os.path.join(NEW_FOLDER, "corpus", "text")

# Category mapping from source categories to corpus categories
CATEGORY_MAP = {
    "cultivar": "cultivar",
    "region": "region",
    "processing": "processing",
    "plucking standards": "plucking",
    "disease/pests": "disease_pest",
    "quality": "quality",
    "sustainability": "sustainability",
    "history": "history",
    "economics": "economics",
    "trade": "trade",
    "grades/sales": "grade",
    "grades/standards": "grade",
    "trade/compliance": "trade",
    "trade/branding": "trade",
    "production": "production",
    "compliance": "quality"
}

def load_metadata():
    """Load metadata from JSONL file"""
    metadata = {}
    with open(JSONL_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    doc = json.loads(line)
                    metadata[doc['id']] = doc
                except json.JSONDecodeError:
                    continue
    return metadata

def load_text_content(doc_id):
    """Load text content from corresponding text file"""
    # Find matching text file
    for filename in os.listdir(TEXT_FOLDER):
        if filename.startswith(doc_id):
            filepath = os.path.join(TEXT_FOLDER, filename)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().strip()
            return content
    return None

def get_primary_category(categories_str):
    """Extract primary category from semicolon-separated list"""
    if not categories_str:
        return "general"

    categories = [c.strip().lower() for c in categories_str.split(';')]
    for cat in categories:
        if cat in CATEGORY_MAP:
            return CATEGORY_MAP[cat]
    return "general"

def get_tags(doc):
    """Generate tags from document metadata"""
    tags = []

    # Add source type
    if doc.get('publisher'):
        if 'TRI' in doc['publisher']:
            tags.append('TRI')
        if 'Tea Board' in doc['publisher'] or 'SLTB' in doc['publisher']:
            tags.append('SLTB')

    # Add year if available
    if doc.get('year') and doc['year'] != 'n.d.':
        tags.append(doc['year'])

    # Add document type
    if doc.get('type'):
        if 'PDF' in doc['type']:
            tags.append('official document')
        if 'HTML' in doc['type']:
            tags.append('web source')

    # Add categories as tags
    if doc.get('categories'):
        cats = [c.strip() for c in doc['categories'].split(';')]
        tags.extend(cats[:3])  # Add first 3 categories

    return tags

def chunk_content(content, max_words=300):
    """Split long content into chunks"""
    if not content:
        return []

    # Clean content - remove excessive whitespace and empty lines
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    content = ' '.join(lines)

    words = content.split()
    if len(words) <= max_words:
        return [content]

    chunks = []
    current_chunk = []
    word_count = 0

    for word in words:
        current_chunk.append(word)
        word_count += 1

        if word_count >= max_words:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            word_count = 0

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

def create_new_documents():
    """Create new documents from the new folder data"""
    metadata = load_metadata()
    new_documents = []
    doc_counter = 1

    for doc_id, meta in metadata.items():
        content = load_text_content(doc_id)

        if not content or len(content.strip()) < 50:
            print(f"Skipping {doc_id}: No content or too short")
            continue

        category = get_primary_category(meta.get('categories', ''))
        tags = get_tags(meta)

        # Chunk long content
        chunks = chunk_content(content)

        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 30:
                continue

            new_doc = {
                "doc_id": f"SLTEA_{doc_counter:03d}",
                "category": category,
                "title": meta.get('title', f'Ceylon Tea Document {doc_id}'),
                "content": chunk,
                "tags": tags,
                "source": meta.get('publisher', 'Sri Lanka Tea Authority'),
                "source_id": doc_id
            }

            if len(chunks) > 1:
                new_doc["title"] += f" (Part {i+1})"

            new_documents.append(new_doc)
            doc_counter += 1

    return new_documents

def merge_corpus():
    """Merge new documents with existing corpus"""
    # Load existing corpus
    with open(CORPUS_FILE, 'r', encoding='utf-8') as f:
        corpus = json.load(f)

    existing_docs = corpus['documents']
    existing_count = len(existing_docs)

    print(f"Existing corpus: {existing_count} documents")

    # Create new documents
    new_docs = create_new_documents()
    print(f"New documents to add: {len(new_docs)}")

    # Merge
    all_docs = existing_docs + new_docs

    # Update corpus
    corpus['documents'] = all_docs
    corpus['metadata']['total_documents'] = len(all_docs)
    corpus['metadata']['version'] = "3.0"
    corpus['metadata']['source'] += ", Ceylon Tea Board Official Publications, TRI Circulars"

    # Save updated corpus
    with open(CORPUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(corpus, f, indent=2, ensure_ascii=False)

    print(f"\nUpdated corpus saved!")
    print(f"Total documents: {len(all_docs)}")

    # Also copy to raw data folder for preprocessing
    raw_data_path = os.path.join(RAG_SYSTEM, "data", "raw")
    os.makedirs(raw_data_path, exist_ok=True)
    raw_corpus_path = os.path.join(raw_data_path, "tea_corpus.json")

    with open(raw_corpus_path, 'w', encoding='utf-8') as f:
        json.dump(corpus, f, indent=2, ensure_ascii=False)

    print(f"Also saved to: {raw_corpus_path}")

if __name__ == "__main__":
    merge_corpus()
