"""
Data Preprocessing Script for Tea Knowledge RAG System
Processes the updated corpus with new SLTEA documents
"""
import os
import json
import re
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd

import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords

# Download NLTK data
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('punkt_tab', quiet=True)

print("=" * 60)
print("Tea Knowledge RAG System - Data Preprocessing")
print("=" * 60)

# Configuration
RAW_DATA = "./data/raw/tea_corpus.json"
PROCESSED_DIR = "./data/processed"
RESULTS_DIR = "./results"

# Create directories
Path(PROCESSED_DIR).mkdir(parents=True, exist_ok=True)
Path(RESULTS_DIR).mkdir(parents=True, exist_ok=True)

# Load corpus
print("\n1. Loading corpus...")
with open(RAW_DATA, 'r', encoding='utf-8') as f:
    corpus = json.load(f)

print(f"   Corpus: {corpus['metadata']['title']}")
print(f"   Version: {corpus['metadata']['version']}")
print(f"   Total documents: {corpus['metadata']['total_documents']}")

# Convert to DataFrame
documents = corpus['documents']
df = pd.DataFrame(documents)
print(f"\n2. Dataset Shape: {df.shape}")
print(f"   Columns: {list(df.columns)}")

# Add computed columns
print("\n3. Computing statistics...")
df['char_count'] = df['content'].apply(len)
df['word_count'] = df['content'].apply(lambda x: len(x.split()))
df['sentence_count'] = df['content'].apply(lambda x: len(sent_tokenize(x)) if x else 0)
df['tag_count'] = df['tags'].apply(len)

print(f"\n   CORPUS STATISTICS")
print(f"   {'-' * 40}")
print(f"   Total Documents: {len(df)}")
print(f"   Total Words: {df['word_count'].sum():,}")
print(f"   Total Sentences: {df['sentence_count'].sum():,}")
print(f"\n   Word Count Stats:")
print(f"     Min: {df['word_count'].min()}")
print(f"     Max: {df['word_count'].max()}")
print(f"     Mean: {df['word_count'].mean():.1f}")
print(f"     Median: {df['word_count'].median():.1f}")

# Category statistics
print("\n4. Category Distribution:")
category_stats = df.groupby('category').agg({
    'doc_id': 'count',
    'word_count': ['sum', 'mean']
}).round(1)
category_stats.columns = ['doc_count', 'total_words', 'avg_words']
category_stats = category_stats.sort_values('doc_count', ascending=False)
print(category_stats.to_string())

# Text cleaning
print("\n5. Cleaning text...")
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = ' '.join(text.split())
    text = re.sub(r'[^a-zA-Z0-9\s\-\.]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

df['content_clean'] = df['content'].apply(clean_text)

# Build vocabulary
print("\n6. Building vocabulary...")
stop_words = set(stopwords.words('english'))

def get_tokens(text):
    if not text:
        return []
    tokens = word_tokenize(text.lower())
    tokens = [t for t in tokens if t.isalnum() and len(t) > 2 and t not in stop_words]
    return tokens

all_tokens = []
for content in df['content']:
    all_tokens.extend(get_tokens(content))

vocab = Counter(all_tokens)

print(f"   Total tokens: {len(all_tokens):,}")
print(f"   Unique tokens: {len(vocab):,}")
print(f"   Vocabulary richness: {len(vocab)/len(all_tokens):.4f}")

print(f"\n   Top 20 Domain Terms:")
for i, (term, count) in enumerate(vocab.most_common(20), 1):
    print(f"     {i:2d}. {term}: {count}")

# Data quality checks
print("\n7. Data Quality Checks:")
missing = df.isnull().sum().sum()
duplicates = df.duplicated(subset=['doc_id']).sum()
empty_content = (df['content'].str.len() == 0).sum()
short_docs = (df['word_count'] < 20).sum()

print(f"   Missing values: {missing}")
print(f"   Duplicate doc_ids: {duplicates}")
print(f"   Empty content: {empty_content}")
print(f"   Very short docs (<20 words): {short_docs}")

# Save processed data
print("\n8. Saving processed data...")

# Save processed dataframe
df.to_csv(f"{PROCESSED_DIR}/documents_processed.csv", index=False)
print(f"   Saved: {PROCESSED_DIR}/documents_processed.csv")

# Save vocabulary
vocab_df = pd.DataFrame(vocab.most_common(), columns=['term', 'count'])
vocab_df.to_csv(f"{PROCESSED_DIR}/vocabulary.csv", index=False)
print(f"   Saved: {PROCESSED_DIR}/vocabulary.csv")

# Save category stats
category_stats.to_csv(f"{PROCESSED_DIR}/category_stats.csv")
print(f"   Saved: {PROCESSED_DIR}/category_stats.csv")

# Save summary
all_tags = [tag for tags in df['tags'] for tag in tags]
summary = {
    'total_documents': len(df),
    'total_words': int(df['word_count'].sum()),
    'total_sentences': int(df['sentence_count'].sum()),
    'vocabulary_size': len(vocab),
    'categories': list(df['category'].unique()),
    'avg_words_per_doc': float(df['word_count'].mean()),
    'total_tags': len(set(all_tags))
}

with open(f"{PROCESSED_DIR}/corpus_summary.json", 'w') as f:
    json.dump(summary, f, indent=2)
print(f"   Saved: {PROCESSED_DIR}/corpus_summary.json")

print("\n" + "=" * 60)
print("Preprocessing Complete!")
print("=" * 60)
