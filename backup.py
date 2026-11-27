"""
backup.py — Zip the entire project folder into a timestamped backup.
"""
import os, zipfile, datetime

PROJECT_DIR = r"D:\foot"
TIMESTAMP   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_NAME = f"foot_backup_{TIMESTAMP}.zip"
BACKUP_PATH = os.path.join(PROJECT_DIR, BACKUP_NAME)

# Folders/files to skip
SKIP = {"__pycache__", ".git", BACKUP_NAME}

count = 0
with zipfile.ZipFile(BACKUP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(PROJECT_DIR):
        # Skip unwanted dirs
        dirs[:] = [d for d in dirs if d not in SKIP]
        for f in files:
            if f.startswith("foot_backup_") and f.endswith(".zip"):
                continue  # don't include old backups
            full = os.path.join(root, f)
            arc  = os.path.relpath(full, PROJECT_DIR)
            zf.write(full, arc)
            count += 1

size_mb = os.path.getsize(BACKUP_PATH) / (1024 * 1024)
print(f"Backup created: {BACKUP_PATH}")
print(f"  {count} files, {size_mb:.1f} MB")
