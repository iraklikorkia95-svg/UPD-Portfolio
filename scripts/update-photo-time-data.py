#!/usr/bin/env python3
"""Generate summed shutter-time data for the portfolio."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PHOTOS_ROOT = ROOT / "Photos"
OUTPUT_PATH = ROOT / "photo-time-data.js"
IMAGE_SUFFIXES = {".jpg", ".jpeg"}

ALBUMS = [
    {"slug": "andalusia", "title": "Andalusia", "directory": "Andalusia"},
    {"slug": "catalonia", "title": "Catalonia", "directory": "Catalonia"},
    {"slug": "corsica", "title": "Corsica", "directory": "Corsica"},
    {"slug": "french-alps", "title": "French Alps", "directory": "French Alps"},
    {"slug": "madrid", "title": "Madrid", "directory": "Madrid"},
    {"slug": "paris", "title": "Paris", "directory": "Paris"},
    {"slug": "strasbourg", "title": "Strasbourg", "directory": "Strasbourg"},
]


def natural_key(path: Path) -> list[object]:
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", path.name)]


def photo_number(path: Path, fallback: int) -> int:
    matches = re.findall(r"\d+", path.stem)
    return int(matches[-1]) if matches else fallback


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def existing_asset_or_source(source: Path, variant_root: str) -> str:
    variant = PHOTOS_ROOT / variant_root / source.parent.name / source.name
    return rel(variant if variant.exists() else source)


def read_exposure_seconds(path: Path) -> float | None:
    try:
        result = subprocess.run(
            ["mdls", "-raw", "-name", "kMDItemExposureTimeSeconds", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit("Could not find macOS mdls. Run this script on macOS, or install exiftool and adapt the reader.") from exc

    raw = result.stdout.strip()
    if result.returncode != 0 or raw in {"", "(null)", "null"}:
        return None

    try:
        return float(raw)
    except ValueError:
        return None


def shutter_label(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    if seconds <= 0:
        return None
    if seconds >= 1:
        label = f"{seconds:.2f}".rstrip("0").rstrip(".")
        return f"{label}s"

    denominator = round(1 / seconds)
    if denominator > 0:
        reciprocal = 1 / denominator
        if abs(reciprocal - seconds) / seconds < 0.025:
            return f"1/{denominator}s"

    label = f"{seconds:.4f}".rstrip("0").rstrip(".")
    return f"{label}s"


def format_duration(seconds: float) -> str:
    if seconds >= 10:
        return f"{seconds:.0f}"
    if seconds >= 1:
        return f"{seconds:.2f}".rstrip("0").rstrip(".")
    if seconds >= 0.1:
        return f"{seconds:.2f}".rstrip("0").rstrip(".")
    return f"{seconds:.3f}".rstrip("0").rstrip(".")


def duration_caption(seconds: float) -> str:
    value = format_duration(seconds)
    unit = "second" if value == "1" else "seconds"
    return f"{value} {unit} of real time"


def short_duration_caption(seconds: float) -> str:
    return f"{format_duration(seconds)}s of real time"


def album_photo_paths(album_directory: str) -> list[Path]:
    directory = PHOTOS_ROOT / album_directory
    if not directory.exists():
        return []
    return sorted(
        [path for path in directory.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES],
        key=natural_key,
    )


def build_data() -> dict[str, object]:
    albums: dict[str, object] = {}
    total_seconds = 0.0
    total_photos = 0
    total_missing = 0

    for album_config in ALBUMS:
        source_paths = album_photo_paths(album_config["directory"])
        photos = []
        album_seconds = 0.0
        missing_count = 0

        for index, source in enumerate(source_paths, start=1):
            exposure_seconds = read_exposure_seconds(source)
            if exposure_seconds is None:
                missing_count += 1
            else:
                album_seconds += exposure_seconds

            photos.append(
                {
                    "number": photo_number(source, index),
                    "file": source.name,
                    "src": rel(source),
                    "displaySrc": existing_asset_or_source(source, "Display"),
                    "thumbnailSrc": existing_asset_or_source(source, "Thumbnails"),
                    "shutterSeconds": exposure_seconds,
                    "shutterText": shutter_label(exposure_seconds),
                }
            )

        total_seconds += album_seconds
        total_photos += len(photos)
        total_missing += missing_count
        albums[album_config["slug"]] = {
            "title": album_config["title"],
            "photoCount": len(photos),
            "exposureSeconds": album_seconds,
            "caption": duration_caption(album_seconds),
            "shortCaption": short_duration_caption(album_seconds),
            "missingExposureCount": missing_count,
            "photos": photos,
        }

    return {
        "source": "Photos/<album> kMDItemExposureTimeSeconds",
        "total": {
            "photoCount": total_photos,
            "exposureSeconds": total_seconds,
            "caption": duration_caption(total_seconds),
            "shortCaption": short_duration_caption(total_seconds),
            "missingExposureCount": total_missing,
        },
        "albums": albums,
    }


def write_data() -> dict[str, object]:
    data = build_data()
    payload = json.dumps(data, indent=2, ensure_ascii=True)
    OUTPUT_PATH.write_text(
        "/* Generated by scripts/update-photo-time-data.py. Do not edit by hand. */\n"
        f"window.PHOTO_TIME_DATA = {payload};\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {OUTPUT_PATH.relative_to(ROOT)}: "
        f"{data['total']['photoCount']} photos, {data['total']['caption']}."
    )
    return data


def snapshot() -> tuple[tuple[str, int, int], ...]:
    entries = []
    for album in ALBUMS:
        for path in album_photo_paths(album["directory"]):
            stat = path.stat()
            entries.append((rel(path), stat.st_mtime_ns, stat.st_size))
    return tuple(entries)


def watch(interval: float) -> None:
    previous = None
    while True:
        current = snapshot()
        if current != previous:
            write_data()
            previous = current
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Update summed shutter-time data for the portfolio.")
    parser.add_argument("--watch", action="store_true", help="Keep watching Photos/<album> and regenerate on changes.")
    parser.add_argument("--interval", type=float, default=2.0, help="Watch polling interval in seconds.")
    args = parser.parse_args()

    if args.watch:
        watch(args.interval)
    else:
        write_data()


if __name__ == "__main__":
    main()
