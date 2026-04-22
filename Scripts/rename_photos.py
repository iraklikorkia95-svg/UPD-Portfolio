from pathlib import Path
import sys

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}

if len(sys.argv) < 3:
    print("Usage:")
    print('  python3 scripts/rename_photos.py "<folder_path>" "<prefix>"')
    sys.exit(1)

folder = Path(sys.argv[1]).expanduser()
prefix = sys.argv[2]

if not folder.exists() or not folder.is_dir():
    print(f"Folder not found: {folder}")
    sys.exit(1)

files = sorted(
    [
        p for p in folder.iterdir()
        if p.is_file()
        and p.suffix.lower() in IMAGE_EXTS
        and not p.name.startswith(".")
    ],
    key=lambda p: p.name.lower()
)

if not files:
    print(f"No image files found in {folder}")
    sys.exit(0)

temp_files = []

for i, file in enumerate(files, start=1):
    temp_name = folder / f"__temp_{i:03d}{file.suffix.lower()}"
    file.rename(temp_name)
    temp_files.append(temp_name)

for i, file in enumerate(temp_files, start=1):
    final_name = folder / f"{prefix}_{i:03d}{file.suffix.lower()}"
    file.rename(final_name)

print(f"Renamed {len(temp_files)} files in:")
print(folder)
print(f"Prefix used: {prefix}")
