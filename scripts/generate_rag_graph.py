import json
import os
import matplotlib.pyplot as plt
from collections import Counter

corpus_path = r"C:\Nipuna\TEST\RAG_SYSTEM\tea_corpus.json"

categories = Counter()

if os.path.exists(corpus_path):
    with open(corpus_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        docs = data.get('documents', [])
        for doc in docs:
            cat = doc.get('category', 'unknown')
            categories[cat] += 1
else:
    print(f"Error: {corpus_path} not found.")

if categories:
    # Sort categories by count
    sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
    labels = [x[0].replace('_', ' ').title() for x in sorted_cats]
    counts = [x[1] for x in sorted_cats]

    # Pick a nice color palette
    colors = ['#4CAF50', '#8BC34A', '#2196F3', '#03A9F4', '#00BCD4', '#009688', 
              '#FF9800', '#FFC107', '#FF5722', '#F44336', '#E91E63', '#9C27B0', '#673AB7']
    # Cycle colors if needed
    colors = colors * (len(labels) // len(colors) + 1)

    plt.figure(figsize=(14, 7))
    bars = plt.bar(labels, counts, color=colors[:len(labels)])

    plt.title('Ceylon Tea Knowledge Base: Document Distribution by Category', fontsize=16, fontweight='bold', pad=20)
    plt.ylabel('Number of Documents', fontsize=12, fontweight='bold')
    plt.xlabel('Knowledge Category', fontsize=12, fontweight='bold')
    plt.xticks(rotation=45, ha='right', fontsize=11)
    
    # Get max count to set dynamic ylim
    max_count = max(counts)
    plt.ylim(0, max_count * 1.15)
    plt.grid(axis='y', linestyle='--', alpha=0.6)

    # Add value labels on top of bars
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + (max_count * 0.02), 
                 f'{int(yval)}', ha='center', va='bottom', fontweight='bold', fontsize=10)

    plt.tight_layout()
    plt.savefig(r'c:\Nipuna\TEST\rag_knowledge_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"RAG graph generated successfully at c:\\Nipuna\\TEST\\rag_knowledge_distribution.png")
else:
    print("No categories found to plot.")
