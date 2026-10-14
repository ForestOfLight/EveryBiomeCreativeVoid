"""Regolith filter: packages the behavior pack as a .mcpack.

Zips the processed BP to <project root>/build/EveryBiomeCreative.mcpack, with
manifest.json at the root of the archive so it can be imported directly.

Optional filter settings:
    "output": output file path, relative to the project root.
"""
import json
import os
import sys
import zipfile

BP_DIR = "BP"
DEFAULT_OUTPUT = os.path.join("build", "EveryBiomeCreative.mcpack")


def load_settings():
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return json.loads(sys.argv[1])
    return {}


def zip_directory(source_dir, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, _, filenames in os.walk(source_dir):
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                zf.write(full_path, os.path.relpath(full_path, source_dir))


def main():
    settings = load_settings()
    root_dir = os.environ.get("ROOT_DIR")
    if not root_dir:
        sys.exit("ROOT_DIR is not set; this filter must be run by Regolith.")
    output_path = os.path.join(root_dir, settings.get("output", DEFAULT_OUTPUT))

    zip_directory(BP_DIR, output_path)

    print(f"Packaged behavior pack to {output_path}")


if __name__ == "__main__":
    main()
