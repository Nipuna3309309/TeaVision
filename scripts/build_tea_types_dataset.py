"""
==============================================================================
 Tea TYPES Dataset Builder    1000+ Images
 Classes: Black Tea | Green Tea | White Tea | Oolong Tea | Herbal Tea | Peppermint Tea
==============================================================================

 This script downloads images for each tea TYPE (processed beverage form)
 using Bing and Google image search.

 OUTPUT STRUCTURE:
   tea_types_dataset/
    raw/
       Black_Tea/          (200+ images)
       Green_Tea/          (200+ images)
       White_Tea/          (200+ images)
       Oolong_Tea/         (200+ images)
       Herbal_Tea/         (150+ images)
       Peppermint_Tea/     (150+ images)
    train/  val/  test/     (split after manual audit)
    dataset_info.json

 USAGE:
   pip install icrawler pillow
   python build_tea_types_dataset.py --output ./tea_types_dataset --per_class 220

 AFTER DOWNLOAD  MANUAL AUDIT REQUIRED:
     Auto-scraped images MUST be manually checked before training.
     Remove irrelevant/misclassified images.
     Target: 150-200 clean images per class after audit.
     Then run: python build_tea_types_dataset.py --split_only --output ./tea_types_dataset
==============================================================================
"""

import os
import shutil
import argparse
import json
import hashlib
import random
from pathlib import Path
from PIL import Image

#  Search queries per class
# Multiple queries per class = better diversity
TEA_CLASSES = {
    "Black_Tea": [
        "black tea dry leaves close up",
        "Ceylon black tea leaves",
        "Assam black tea CTC leaves",
        "black tea loose leaf product",
        "orthodox black tea leaves",
        "dark tea leaves dried",
    ],
    "Green_Tea": [
        "green tea dry leaves close up",
        "green tea loose leaf",
        "Japanese green tea matcha leaves",
        "Chinese green tea dried leaves",
        "sencha green tea leaves",
        "gunpowder green tea leaves",
    ],
    "White_Tea": [
        "white tea leaves silver tips",
        "white tea buds dried",
        "white peony tea leaves",
        "Ceylon silver tips white tea",
        "white tea loose leaf close up",
        "bai hao white tea",
    ],
    "Oolong_Tea": [
        "oolong tea dry leaves",
        "oolong tea twisted leaves",
        "tieguanyin oolong tea leaves",
        "wulong tea loose leaf",
        "oolong tea rolled leaves close up",
        "Taiwan oolong tea leaves",
    ],
    "Herbal_Tea": [
        "herbal tea dried flowers and herbs",
        "chamomile herbal tea dry",
        "hibiscus herbal tea dry leaves",
        "mixed herbal tea loose",
        "dried herbs tea blend close up",
        "rose herbal tea dried petals",
    ],
    "Peppermint_Tea": [
        "peppermint tea dry leaves",
        "dried peppermint leaves tea",
        "spearmint tea dried leaves",
        "mint herbal tea loose leaf",
        "peppermint leaves dried close up",
    ],
}

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def file_hash(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read(8192))
    return h.hexdigest()


def is_valid_image(path, min_size=64):
    try:
        with Image.open(path) as img:
            w, h = img.size
        return w >= min_size and h >= min_size
    except Exception:
        return False


def download_class(class_name, queries, output_dir, per_query=40):
    """Download images for one class using multiple search queries."""
    try:
        from icrawler.builtin import BingImageCrawler, GoogleImageCrawler
    except ImportError:
        print("  [ERROR] icrawler not installed. Run: pip install icrawler")
        return 0

    class_dir = Path(output_dir) / class_name
    class_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    for i, query in enumerate(queries):
        sub_dir = class_dir / f"q{i:02d}"
        sub_dir.mkdir(exist_ok=True)

        print(f"    Query: '{query}'  {per_query} images")

        # Try Bing first
        try:
            crawler = BingImageCrawler(
                storage={"root_dir": str(sub_dir)},
                log_level=40,  # ERROR only
            )
            crawler.crawl(
                keyword=query,
                max_num=per_query,
                filters={"type": "photo", "size": "medium"},
            )
        except Exception as e:
            print(f"      [Bing failed: {e}] trying Google...")
            try:
                crawler = GoogleImageCrawler(
                    storage={"root_dir": str(sub_dir)},
                    log_level=40,
                )
                crawler.crawl(keyword=query, max_num=per_query)
            except Exception as e2:
                print(f"      [Google also failed: {e2}]")
                continue

        imgs = list(sub_dir.glob("*"))
        total += len(imgs)

    return total


def consolidate_class(class_dir):
    """
    Move all images from subdirectories into class root,
    rename with hash to avoid conflicts, remove duplicates and invalid files.
    """
    class_dir = Path(class_dir)
    seen_hashes = set()
    kept = 0
    removed_dupe = 0
    removed_invalid = 0

    # collect all images in subdirs
    all_imgs = []
    for sub in class_dir.iterdir():
        if sub.is_dir():
            all_imgs.extend(sub.glob("*"))

    for src in all_imgs:
        if src.suffix.lower() not in IMG_EXTS:
            src.unlink(missing_ok=True)
            continue

        if not is_valid_image(src):
            src.unlink(missing_ok=True)
            removed_invalid += 1
            continue

        h = file_hash(src)
        if h in seen_hashes:
            src.unlink(missing_ok=True)
            removed_dupe += 1
            continue

        seen_hashes.add(h)
        dst = class_dir / f"{h[:12]}.jpg"

        try:
            with Image.open(src) as img:
                rgb = img.convert("RGB")
                rgb.save(dst, "JPEG", quality=90)
            src.unlink(missing_ok=True)
            kept += 1
        except Exception:
            try:
                src.unlink(missing_ok=True)
            except Exception:
                pass

    # remove empty subdirs
    for sub in class_dir.iterdir():
        if sub.is_dir():
            try:
                sub.rmdir()
            except Exception:
                shutil.rmtree(sub, ignore_errors=True)

    return kept, removed_dupe, removed_invalid


def split_dataset(raw_dir, output_dir, train_ratio=0.70, val_ratio=0.15, seed=42):
    """Split raw images into train/val/test."""
    random.seed(seed)
    raw_dir = Path(raw_dir)
    output_dir = Path(output_dir)

    stats = {}
    for class_dir in sorted(raw_dir.iterdir()):
        if not class_dir.is_dir():
            continue
        class_name = class_dir.name
        imgs = [f for f in class_dir.glob("*.jpg")]
        random.shuffle(imgs)

        n = len(imgs)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        splits = {
            "train": imgs[:n_train],
            "val": imgs[n_train : n_train + n_val],
            "test": imgs[n_train + n_val :],
        }

        for split_name, split_imgs in splits.items():
            dst_dir = output_dir / split_name / class_name
            dst_dir.mkdir(parents=True, exist_ok=True)
            for img in split_imgs:
                shutil.copy2(img, dst_dir / img.name)

        stats[class_name] = {split: len(imgs) for split, imgs in splits.items()}
        stats[class_name]["total"] = n
        print(
            f"  {class_name:<20} total={n:<5} train={splits['train'].__len__():<5} "
            f"val={splits['val'].__len__():<4} test={splits['test'].__len__()}"
        )

    return stats


def print_summary(output_dir, stats):
    print("\n" + "=" * 60)
    print(" DATASET BUILD COMPLETE")
    print("=" * 60)
    total = sum(v["total"] for v in stats.values())
    print(f"\n  Total images: {total}")
    print(f"  Classes:      {len(stats)}")
    print(f"\n  {'Class':<22} {'Train':>6} {'Val':>5} {'Test':>5} {'Total':>6}")
    print("  " + "-" * 46)
    for cls, s in stats.items():
        print(f"  {cls:<22} {s['train']:>6} {s['val']:>5} {s['test']:>5} {s['total']:>6}")
    print("\n  IMPORTANT  BEFORE TRAINING:")
    print("  1. Manually review raw/ folder and DELETE bad images")
    print("  2. Remove non-tea-leaf images (infused tea cups, packaging etc)")
    print("  3. Re-run with --split_only after audit")
    print("  4. Minimum 100 clean images per class for reliable training")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Tea Types Dataset Builder")
    parser.add_argument("--output", default="./tea_types_dataset")
    parser.add_argument(
        "--per_class", type=int, default=220, help="Target images to download per class"
    )
    parser.add_argument(
        "--split_only", action="store_true", help="Skip download, only do train/val/test split"
    )
    parser.add_argument(
        "--classes", nargs="+", default=None, help="Only download specific classes (default: all)"
    )
    args = parser.parse_args()

    output = Path(args.output)
    raw_dir = output / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    classes_to_build = args.classes if args.classes else list(TEA_CLASSES.keys())
    per_query = max(10, args.per_class // len(list(TEA_CLASSES.values())[0]))

    if not args.split_only:
        print("\n" + "=" * 60)
        print(" Tea Types Dataset Builder")
        print(f" Target: ~{args.per_class} images per class")
        print(f" Classes: {', '.join(classes_to_build)}")
        print("=" * 60)

        for class_name in classes_to_build:
            if class_name not in TEA_CLASSES:
                print(f"[WARN] Unknown class '{class_name}', skipping")
                continue

            queries = TEA_CLASSES[class_name]
            print(f"\n[{class_name}]")
            n_downloaded = download_class(
                class_name, queries, output_dir=raw_dir, per_query=per_query
            )
            print(f"  Downloaded: {n_downloaded} files")

            print(f"  Consolidating + deduplicating...")
            kept, dupes, invalid = consolidate_class(raw_dir / class_name)
            print(f"  Kept: {kept}  |  Removed dupes: {dupes}  |  Invalid: {invalid}")

        print("\n  Download complete. Please review images in:")
        print(f"   {raw_dir}")
        print("\nTo split after manual audit:")
        print(f"   python {__file__} --output {output} --split_only")

    # Always run split
    print("\n[SPLIT] Creating train/val/test splits...")
    stats = split_dataset(raw_dir, output)

    # Save info
    info = {
        "classes": classes_to_build,
        "split_ratios": {"train": 0.70, "val": 0.15, "test": 0.15},
        "class_stats": stats,
        "total": sum(v["total"] for v in stats.values()),
        "notes": [
            "Images scraped from Bing/Google image search",
            "Manual audit required before training",
            "Delete non-representative images from raw/ folder",
            "Use Macro F1 for evaluation due to potential imbalance",
        ],
    }
    with open(output / "dataset_info.json", "w") as f:
        json.dump(info, f, indent=2)

    print_summary(output, stats)


if __name__ == "__main__":
    main()
