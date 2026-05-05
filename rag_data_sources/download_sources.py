#!/usr/bin/env python3
"""
Download + extract a curated set of Sri Lankan tea sources for a RAG corpus.

Usage:
  python download_sources.py --manifest ceylon_tea_rag_sources.jsonl --out corpus

Notes:
- This script is intentionally conservative and transparent:
  it saves raw files, extracted text, and a metadata log including hashes.
- Some sites may block automated downloads; in that case, download manually
  and still use the extraction/hashing steps for reproducibility.
"""
import argparse, json, os, re, hashlib, datetime
from pathlib import Path

import requests

# Optional dependencies:
#   pip install pypdf pdfminer.six beautifulsoup4 trafilatura
try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    import trafilatura
except Exception:
    trafilatura = None


def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def safe_filename(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s).strip("_")
    return s[:180] if len(s) > 180 else s


def download(url: str, dest: Path, timeout: int = 60) -> bytes:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (RAG-corpus-builder)"})
    r.raise_for_status()
    dest.write_bytes(r.content)
    return r.content


def extract_pdf_text(pdf_path: Path) -> str:
    if PdfReader is None:
        raise RuntimeError("pypdf not installed. Run: pip install pypdf")
    reader = PdfReader(str(pdf_path))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def extract_html_text(html_bytes: bytes, url: str) -> str:
    if trafilatura is None:
        raise RuntimeError("trafilatura not installed. Run: pip install trafilatura")
    downloaded = trafilatura.extract(html_bytes, include_comments=False, include_tables=True, url=url)
    return (downloaded or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, help="Path to JSONL manifest")
    ap.add_argument("--out", default="corpus", help="Output folder")
    args = ap.parse_args()

    out = Path(args.out)
    raw_dir = out / "raw"
    text_dir = out / "text"
    meta_dir = out / "metadata"
    raw_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    retrieved_at = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    log_path = meta_dir / f"download_log_{retrieved_at.replace(':','-')}.jsonl"

    with open(args.manifest, "r", encoding="utf-8") as f, open(log_path, "w", encoding="utf-8") as log:
        for line in f:
            item = json.loads(line)
            url = item["url"]
            sid = item["id"]
            title = item["title"]

            ext = ".pdf" if item["type"].lower().startswith("pdf") or url.lower().endswith(".pdf") else ".html"
            raw_name = safe_filename(f"{sid}_{title}") + ext
            raw_path = raw_dir / raw_name

            record = {
                "source_id": sid,
                "title": title,
                "url": url,
                "retrieved_at": retrieved_at,
                "raw_path": str(raw_path),
                "status": "pending",
            }

            try:
                content = download(url, raw_path)
                record["raw_sha256"] = sha256_bytes(content)
                record["raw_bytes"] = len(content)

                # Extract text
                if ext == ".pdf":
                    text = extract_pdf_text(raw_path)
                else:
                    text = extract_html_text(content, url)

                text_name = safe_filename(f"{sid}_{title}") + ".txt"
                text_path = text_dir / text_name
                text_path.write_text(text, encoding="utf-8")

                record["text_path"] = str(text_path)
                record["text_chars"] = len(text)
                record["status"] = "ok"
            except Exception as e:
                record["status"] = "error"
                record["error"] = repr(e)

            log.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f'[{record["status"]}] {sid} {title}')

    print(f"\nDone. Log written to: {log_path}")


if __name__ == "__main__":
    main()
