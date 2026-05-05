"""
Tea Knowledge Auto-Scraper
Automatically fetches tea-related content from Wikipedia API and web sources.
No manual downloading required — just run this module or trigger via API.

Project: 25-26J-133
"""

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field, asdict


# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"

# Topics to scrape from Wikipedia (title → category mapping)
WIKIPEDIA_TOPICS: Dict[str, str] = {
    # Core tea topics
    "Tea": "processing",
    "Camellia sinensis": "cultivar",
    "Ceylon tea": "history",
    "Tea production in Sri Lanka": "economics",
    "Tea processing": "processing",
    "Tea culture": "history",
    "Black tea": "processing",
    "Green tea": "processing",
    "White tea": "processing",
    "Oolong": "processing",
    "Tea blending and additives": "processing",

    # Health
    "Health effects of tea": "health",
    "Epigallocatechin gallate": "health",
    "Catechin": "health",
    "Theanine": "health",
    "Caffeine": "health",
    "Polyphenol": "health",
    "Theaflavin": "health",
    "Antioxidant": "health",

    # Sri Lankan regions
    "Nuwara Eliya": "region",
    "Kandy": "region",
    "Uva Province": "region",
    "Sabaragamuwa Province": "region",
    "Southern Province, Sri Lanka": "region",
    "Central Province, Sri Lanka": "region",
    "Dimbula": "region",

    # Tea grading
    "Tea leaf grading": "grade",
    "Orange pekoe": "grade",

    # Diseases & pests
    "Exobasidium vexans": "disease",
    "Pratylenchus": "disease",
    "Helopeltis": "disease",
    "Tea mosquito bug": "disease",
    "Plant pathology": "disease",
    "Integrated pest management": "disease",

    # Agriculture
    "Tea garden": "plucking",
    "Tea estate": "economics",
    "Colombo Tea Auction": "trade",
    "Tea Board of Sri Lanka": "trade",
    "Fair trade tea": "sustainability",
    "Organic tea": "sustainability",
    "Climate change and agriculture": "sustainability",
    "Sustainable agriculture": "sustainability",

    # AI & technology
    "Precision agriculture": "ai_grading",
    "Computer vision": "ai_grading",
    "Object detection": "ai_grading",

    # Quality
    "Tea tasting": "quality",
    "Terroir": "quality",

    # Economics & trade
    "Tea industry": "economics",
    "International Tea Committee": "trade",

    # History
    "History of tea": "history",
    "James Taylor (pioneer)": "history",
    "Thomas Lipton": "history",
}

# Category metadata for auto-tagging
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "cultivar": ["cultivar", "variety", "clone", "TRI", "camellia", "sinensis", "assamica", "plant", "breeding"],
    "region": ["nuwara eliya", "kandy", "uva", "dimbula", "ruhuna", "sabaragamuwa", "elevation", "highland", "lowland"],
    "grade": ["grade", "pekoe", "orange", "broken", "fannings", "dust", "BOPF", "BOP", "OP", "tips", "silver"],
    "processing": ["processing", "withering", "rolling", "oxidation", "fermentation", "drying", "CTC", "orthodox", "black tea", "green tea"],
    "health": ["health", "antioxidant", "catechin", "EGCG", "theanine", "caffeine", "polyphenol", "cardiovascular", "cancer"],
    "plucking": ["plucking", "pluck", "harvest", "two leaves", "bud", "picking", "flush"],
    "disease": ["disease", "blight", "nematode", "pest", "fungal", "mite", "borer", "pathogen", "infection"],
    "ai_grading": ["AI", "machine learning", "computer vision", "deep learning", "YOLO", "detection", "classification", "neural"],
    "quality": ["quality", "tasting", "aroma", "flavor", "liquor", "brightness", "body", "briskness"],
    "economics": ["export", "production", "industry", "price", "auction", "market", "GDP", "employment", "smallholder"],
    "sustainability": ["sustainability", "organic", "climate", "carbon", "fair trade", "certification", "environment"],
    "history": ["history", "colonial", "British", "James Taylor", "Lipton", "1867", "origin", "Ceylon"],
    "trade": ["trade", "auction", "export", "import", "Lion Logo", "Colombo", "certification", "brand"],
}


@dataclass
class ScrapedDocument:
    """A document scraped from the web."""
    doc_id: str
    category: str
    title: str
    content: str
    tags: List[str] = field(default_factory=list)
    source: str = ""


# ─────────────────────────────────────────────────────────
# Wikipedia API Client
# ─────────────────────────────────────────────────────────

class WikipediaClient:
    """Fetch and parse Wikipedia articles via the MediaWiki API."""

    def __init__(self, delay: float = 0.5):
        self.delay = delay  # Polite delay between requests

    def fetch_article(self, title: str) -> Optional[str]:
        """Fetch plain text extract of a Wikipedia article."""
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "explaintext": "true",
            "exlimit": "1",
            "format": "json",
            "redirects": "1",
        }
        url = f"{WIKIPEDIA_API}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "TeaRAGSystem/1.0 (SLIIT Research Project 25-26J-133)"
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            pages = data.get("query", {}).get("pages", {})
            for page_id, page in pages.items():
                if page_id == "-1":
                    return None
                return page.get("extract", "")

        except Exception as e:
            print(f"  [WARN] Failed to fetch '{title}': {e}")
            return None

        finally:
            time.sleep(self.delay)

    def search_articles(self, query: str, limit: int = 5) -> List[str]:
        """Search Wikipedia for article titles matching a query."""
        params = {
            "action": "opensearch",
            "search": query,
            "limit": str(limit),
            "format": "json",
        }
        url = f"{WIKIPEDIA_API}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "TeaRAGSystem/1.0 (SLIIT Research Project 25-26J-133)"
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            return data[1] if len(data) > 1 else []
        except Exception:
            return []


# ─────────────────────────────────────────────────────────
# Content Processing
# ─────────────────────────────────────────────────────────

def clean_wikipedia_text(text: str) -> str:
    """Clean Wikipedia extract text for RAG use."""
    if not text:
        return ""

    # Remove section headers that are just "== Header =="
    text = re.sub(r"={2,}\s*[^=]+\s*={2,}", " ", text)

    # Remove reference markers like [1], [2], etc.
    text = re.sub(r"\[\d+\]", "", text)

    # Remove excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"  +", " ", text)

    # Remove "See also", "References", "External links" sections and everything after
    for section in ["See also", "References", "External links", "Further reading", "Notes", "Bibliography"]:
        idx = text.lower().find(section.lower())
        if idx > 0:
            text = text[:idx]

    return text.strip()


def extract_tags(text: str, title: str, category: str) -> List[str]:
    """Extract relevant tags from content using keyword matching."""
    tags = set()
    combined = (title + " " + text[:500]).lower()

    # Add category-specific keywords found in text
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if cat == category:
            for kw in keywords:
                if kw.lower() in combined:
                    tags.add(kw)

    # Extract proper nouns / key terms from title
    title_words = title.replace("(", "").replace(")", "").split()
    for word in title_words:
        if len(word) > 3 and word[0].isupper():
            tags.add(word)

    # Limit to 6 tags
    return list(tags)[:6]


def auto_categorize(text: str, title: str, default_category: str) -> str:
    """Auto-categorize content based on keyword matching."""
    combined = (title + " " + text[:1000]).lower()

    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in combined)
        if score > 0:
            scores[cat] = score

    if scores:
        best = max(scores, key=scores.get)
        # Only override if significantly better match
        if scores.get(best, 0) >= 2:
            return best

    return default_category


def generate_doc_id(category: str, existing_ids: set) -> str:
    """Generate a unique document ID like 'WEB_CUL_001'."""
    prefix_map = {
        "cultivar": "CUL", "region": "REG", "grade": "GRD",
        "processing": "PRO", "health": "HLT", "plucking": "PLK",
        "disease": "DIS", "ai_grading": "AIG", "quality": "QUA",
        "economics": "ECO", "sustainability": "SUS", "history": "HIS",
        "trade": "TRD",
    }
    prefix = f"WEB_{prefix_map.get(category, 'GEN')}"

    counter = 1
    while True:
        doc_id = f"{prefix}_{counter:03d}"
        if doc_id not in existing_ids:
            return doc_id
        counter += 1


# ─────────────────────────────────────────────────────────
# Main Scraper
# ─────────────────────────────────────────────────────────

class TeaAutoScraper:
    """
    Automated scraper for building the tea knowledge corpus.
    Fetches from Wikipedia API and processes into RAG-ready documents.
    """

    def __init__(self, corpus_path: str):
        self.corpus_path = Path(corpus_path)
        self.wiki = WikipediaClient(delay=0.3)
        self.existing_titles: set = set()
        self.existing_ids: set = set()
        self.progress_callback: Optional[Callable] = None
        self._status = {
            "phase": "idle",
            "progress": 0,
            "total": 0,
            "current_topic": "",
            "new_documents": 0,
            "errors": [],
            "completed": False,
        }

    @property
    def status(self) -> dict:
        return self._status.copy()

    def _update_status(self, **kwargs):
        self._status.update(kwargs)
        if self.progress_callback:
            self.progress_callback(self._status)

    def load_existing_corpus(self) -> dict:
        """Load the existing tea corpus."""
        if self.corpus_path.exists():
            with open(self.corpus_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for doc in data.get("documents", []):
                self.existing_titles.add(doc.get("title", "").lower().strip())
                self.existing_ids.add(doc.get("doc_id", ""))
            return data
        return {"metadata": {}, "documents": []}

    def is_duplicate(self, title: str, content: str) -> bool:
        """Check if content already exists in corpus."""
        title_lower = title.lower().strip()
        if title_lower in self.existing_titles:
            return True
        # Also check for very similar titles
        for existing in self.existing_titles:
            if title_lower in existing or existing in title_lower:
                if len(title_lower) > 10:  # Avoid matching very short strings
                    return True
        return False

    def scrape_wikipedia(self) -> List[ScrapedDocument]:
        """Scrape all configured Wikipedia topics."""
        documents = []
        topics = list(WIKIPEDIA_TOPICS.items())
        total = len(topics)

        self._update_status(phase="scraping_wikipedia", total=total, progress=0)
        print(f"\n📡 Scraping {total} Wikipedia topics...")

        for i, (title, default_category) in enumerate(topics):
            self._update_status(progress=i + 1, current_topic=title)
            print(f"  [{i+1}/{total}] Fetching: {title}...")

            text = self.wiki.fetch_article(title)
            if not text:
                self._status["errors"].append(f"No content: {title}")
                continue

            # Clean and process
            cleaned = clean_wikipedia_text(text)
            if len(cleaned) < 100:
                print(f"    ⚠ Too short, skipping")
                continue

            # Truncate very long articles to keep corpus manageable
            if len(cleaned) > 3000:
                # Keep first 3000 chars but end at sentence boundary
                truncated = cleaned[:3000]
                last_period = truncated.rfind(".")
                if last_period > 2000:
                    cleaned = truncated[:last_period + 1]
                else:
                    cleaned = truncated

            # Check duplicate
            if self.is_duplicate(title, cleaned):
                print(f"    ⏩ Already in corpus, skipping")
                continue

            # Auto-categorize
            category = auto_categorize(cleaned, title, default_category)
            tags = extract_tags(cleaned, title, category)
            doc_id = generate_doc_id(category, self.existing_ids)
            self.existing_ids.add(doc_id)

            doc = ScrapedDocument(
                doc_id=doc_id,
                category=category,
                title=title,
                content=cleaned,
                tags=tags,
                source="Wikipedia"
            )
            documents.append(doc)
            self.existing_titles.add(title.lower().strip())
            print(f"    ✅ Added: {doc_id} [{category}] ({len(cleaned)} chars)")

        self._update_status(
            phase="wikipedia_done",
            new_documents=len(documents),
            current_topic=""
        )
        print(f"\n✅ Scraped {len(documents)} new documents from Wikipedia")
        return documents

    def scrape_additional_topics(self) -> List[ScrapedDocument]:
        """Search for additional tea-related articles not in the predefined list."""
        documents = []
        search_queries = [
            "Sri Lanka tea plantation",
            "Ceylon tea history",
            "tea leaf disease detection",
            "tea quality grading system",
            "Nuwara Eliya tea estates",
            "tea polyphenols health",
            "tea withering process",
            "fair trade tea certification",
        ]

        self._update_status(phase="scraping_additional", total=len(search_queries), progress=0)
        print(f"\n🔍 Searching for additional tea topics...")

        for i, query in enumerate(search_queries):
            self._update_status(progress=i + 1, current_topic=query)
            titles = self.wiki.search_articles(query, limit=3)

            for title in titles:
                if self.is_duplicate(title, ""):
                    continue
                if title in WIKIPEDIA_TOPICS:
                    continue

                text = self.wiki.fetch_article(title)
                if not text:
                    continue

                cleaned = clean_wikipedia_text(text)
                if len(cleaned) < 150:
                    continue

                # Truncate long articles
                if len(cleaned) > 2500:
                    truncated = cleaned[:2500]
                    last_period = truncated.rfind(".")
                    if last_period > 1500:
                        cleaned = truncated[:last_period + 1]

                category = auto_categorize(cleaned, title, "quality")
                tags = extract_tags(cleaned, title, category)
                doc_id = generate_doc_id(category, self.existing_ids)
                self.existing_ids.add(doc_id)

                doc = ScrapedDocument(
                    doc_id=doc_id,
                    category=category,
                    title=title,
                    content=cleaned,
                    tags=tags,
                    source="Wikipedia Search"
                )
                documents.append(doc)
                self.existing_titles.add(title.lower().strip())
                print(f"    ✅ Additional: {doc_id} [{category}] {title}")

        print(f"\n✅ Found {len(documents)} additional documents")
        return documents

    def merge_and_save(self, new_documents: List[ScrapedDocument]) -> dict:
        """Merge new documents with existing corpus and save."""
        self._update_status(phase="merging", current_topic="Saving to corpus...")

        corpus = self.load_existing_corpus()

        # Convert ScrapedDocument to dict format matching corpus
        for doc in new_documents:
            corpus["documents"].append({
                "doc_id": doc.doc_id,
                "category": doc.category,
                "title": doc.title,
                "content": doc.content,
                "tags": doc.tags,
            })

        # Update metadata
        corpus["metadata"]["total_documents"] = len(corpus["documents"])
        corpus["metadata"]["version"] = str(
            float(corpus["metadata"].get("version", "3.0")) + 0.1
        )
        corpus["metadata"]["source"] = (
            corpus["metadata"].get("source", "") +
            ", Wikipedia API (Auto-Scraped)"
        )

        # Save
        with open(self.corpus_path, "w", encoding="utf-8") as f:
            json.dump(corpus, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Saved {len(corpus['documents'])} total documents to {self.corpus_path}")
        return corpus

    def run(self) -> dict:
        """Run the full scraping pipeline."""
        self._update_status(
            phase="starting",
            progress=0,
            total=0,
            new_documents=0,
            errors=[],
            completed=False,
        )

        # Load existing
        self.load_existing_corpus()
        print(f"📚 Existing corpus: {len(self.existing_titles)} documents")

        # Scrape Wikipedia
        wiki_docs = self.scrape_wikipedia()

        # Search for additional topics
        additional_docs = self.scrape_additional_topics()

        # Combine
        all_new = wiki_docs + additional_docs

        if all_new:
            corpus = self.merge_and_save(all_new)
        else:
            corpus = self.load_existing_corpus()
            print("ℹ️ No new documents to add")

        self._update_status(
            phase="done",
            new_documents=len(all_new),
            completed=True,
            current_topic=""
        )

        return {
            "new_documents": len(all_new),
            "total_documents": len(corpus.get("documents", [])),
            "categories_updated": list(set(d.category for d in all_new)) if all_new else [],
            "errors": self._status["errors"],
        }


# ─────────────────────────────────────────────────────────
# Standalone execution
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    corpus_path = str(Path(__file__).parent.parent / "tea_corpus.json")
    print(f"🍵 Tea Auto-Scraper")
    print(f"   Corpus: {corpus_path}")
    print("=" * 60)

    scraper = TeaAutoScraper(corpus_path)
    result = scraper.run()

    print("\n" + "=" * 60)
    print(f"📊 Results:")
    print(f"   New documents: {result['new_documents']}")
    print(f"   Total documents: {result['total_documents']}")
    print(f"   Categories: {', '.join(result['categories_updated'])}")
    if result['errors']:
        print(f"   Errors: {len(result['errors'])}")
