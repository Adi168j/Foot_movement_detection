
import os
import re

folder = r"D:\foot\data"

pattern = re.compile(r"^(still|heelstrike|toeoff|step)_(\d+)\.csv$", re.IGNORECASE)

files = {}

for name in os.listdir(folder):
    match = pattern.match(name)
    if match:
        label = match.group(1).lower()
        number = int(match.group(2))
        files.setdefault(label, []).append((number, name))

for label, items in files.items():
    items.sort()

    temp_files = []

    for i, (old_num, old_name) in enumerate(items, start=1):
        temp_name = f"__temp_{label}_{i}.csv"
        os.rename(
            os.path.join(folder, old_name),
            os.path.join(folder, temp_name)
        )
        temp_files.append((temp_name, f"{label}_{i:02d}.csv"))

    for temp_name, new_name in temp_files:
        os.rename(
            os.path.join(folder, temp_name),
            os.path.join(folder, new_name)
        )
        print(f"{temp_name} -> {new_name}")

print("\nAll files renumbered successfully!")
