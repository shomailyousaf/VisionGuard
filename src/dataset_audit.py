
import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, UnidentifiedImageError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"


CLASS_DIRS = {
    "AI-generated": DATA_DIR / "AiArtData" / "AiArtData",
    "Real": DATA_DIR / "RealArt" / "RealArt",
}

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"
}


def sha256_file(path):
    """Calculate the SHA-256 hash of a file."""
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def median(values):
    """Return the median of a non-empty list of numbers."""
    values = sorted(values)
    n = len(values)

    if n == 0:
        return None

    middle = n // 2

    if n % 2:
        return values[middle]

    return (values[middle - 1] + values[middle]) / 2


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    corrupt_files = []
    hashes_by_class = defaultdict(Counter)
    class_counts = Counter()

    for label, folder in CLASS_DIRS.items():
        if not folder.is_dir():
            print(f"WARNING: Directory not found: {folder}")
            continue

        files = sorted(
            path for path in folder.rglob("*")
            if path.is_file()
        )

        for path in files:
           
            if path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue

            class_counts[label] += 1
            file_size = path.stat().st_size
            content_hash = sha256_file(path)

            record = {
                "class": label,
                "path": str(path.relative_to(PROJECT_ROOT)),
                "file_size_bytes": file_size,
                "width": None,
                "height": None,
                "colour_mode": None,
                "format": None,
                "sha256": content_hash,
                "status": "valid",
            }

            try:
               
                with Image.open(path) as image:
                    image.verify()

               
                with Image.open(path) as image:
                    record["width"] = image.width
                    record["height"] = image.height
                    record["colour_mode"] = image.mode
                    record["format"] = image.format

            except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
                record["status"] = "corrupt_or_unreadable"
                corrupt_files.append({
                    "path": str(path.relative_to(PROJECT_ROOT)),
                    "error": str(exc),
                })

            records.append(record)
            hashes_by_class[label][content_hash] += 1

   
    audit_csv = REPORTS_DIR / "dataset_audit.csv"

    fieldnames = [
        "class", "path", "file_size_bytes", "width", "height",
        "colour_mode", "format", "sha256", "status"
    ]

    with audit_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


    summary_csv = REPORTS_DIR / "dataset_summary.csv"
    summary_rows = []

    for label in CLASS_DIRS:
        class_records = [
            record for record in records
            if record["class"] == label
            and record["status"] == "valid"
        ]

        sizes = [record["file_size_bytes"] for record in class_records]
        widths = [record["width"] for record in class_records]
        heights = [record["height"] for record in class_records]

        def stats(values):
            if not values:
                return {"min": None, "median": None, "max": None}

            return {
                "min": min(values),
                "median": median(values),
                "max": max(values),
            }

        size_stats = stats(sizes)
        width_stats = stats(widths)
        height_stats = stats(heights)

        summary_rows.append({
            "class": label,
            "valid_images": len(class_records),
            "corrupt_or_unreadable": sum(
                1 for record in records
                if record["class"] == label
                and record["status"] != "valid"
            ),
            "file_size_min_bytes": size_stats["min"],
            "file_size_median_bytes": size_stats["median"],
            "file_size_max_bytes": size_stats["max"],
            "width_min": width_stats["min"],
            "width_median": width_stats["median"],
            "width_max": width_stats["max"],
            "height_min": height_stats["min"],
            "height_median": height_stats["median"],
            "height_max": height_stats["max"],
        })

    with summary_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=summary_rows[0].keys())
        writer.writeheader()
        writer.writerows(summary_rows)

    duplicate_groups = defaultdict(list)

    for record in records:
        duplicate_groups[record["sha256"]].append(record)

    duplicates = {
        digest: group
        for digest, group in duplicate_groups.items()
        if len(group) > 1
    }

    duplicate_csv = REPORTS_DIR / "dataset_duplicates.csv"

    with duplicate_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["sha256", "class", "path"])

        for digest, group in sorted(duplicates.items()):
            for record in group:
                writer.writerow([
                    digest,
                    record["class"],
                    record["path"],
                ])

    corrupt_csv = REPORTS_DIR / "dataset_corrupt_files.csv"

    with corrupt_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["path", "error"])
        writer.writeheader()
        writer.writerows(corrupt_files)

    print("\n=== DATASET AUDIT RESULTS ===")

    for label in CLASS_DIRS:
        total = class_counts[label]
        valid = sum(
            1 for record in records
            if record["class"] == label and record["status"] == "valid"
        )
        corrupt = sum(
            1 for record in records
            if record["class"] == label and record["status"] != "valid"
        )

        print(f"{label}: {total} image files; {valid} valid; {corrupt} unreadable")

    print(f"Total image files inspected: {len(records)}")
    print(f"Unreadable image files: {len(corrupt_files)}")
    print(f"Duplicate hash groups: {len(duplicates)}")
    print(f"Audit details: {audit_csv}")
    print(f"Class summary: {summary_csv}")
    print(f"Duplicate report: {duplicate_csv}")
    print(f"Unreadable-file report: {corrupt_csv}")


if __name__ == "__main__":
    main()
