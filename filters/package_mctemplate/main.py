"""Regolith filter: packages the world template with the behavior pack as a .mctemplate.

Copies data/world_template into a staging directory (Regolith writes the data
folder back to the project, so it must not be modified in place), installs the
processed BP into its behavior_packs folder, registers it in
world_behavior_packs.json, and zips the result to
<project root>/build/EveryBiomeCreative.mctemplate.

Optional filter settings:
    "output": output file path, relative to the project root.
"""
import json
import os
import shutil
import sys
import tempfile
import zipfile

WORLD_TEMPLATE_DIR = os.path.join("data", "world_template")
BP_DIR = "BP"
PACK_FOLDER_NAME = "EveryBiomeCreative"
DEFAULT_OUTPUT = os.path.join("build", "EveryBiomeCreative.mctemplate")


def load_settings():
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return json.loads(sys.argv[1])
    return {}


def install_behavior_pack(world_dir):
    with open(os.path.join(BP_DIR, "manifest.json"), encoding="utf-8") as f:
        header = json.load(f)["header"]

    pack_dir = os.path.join(world_dir, "behavior_packs", PACK_FOLDER_NAME)
    shutil.rmtree(pack_dir, ignore_errors=True)
    shutil.copytree(BP_DIR, pack_dir)

    packs_path = os.path.join(world_dir, "world_behavior_packs.json")
    packs = []
    if os.path.exists(packs_path):
        with open(packs_path, encoding="utf-8") as f:
            packs = json.load(f)
    packs = [p for p in packs if p.get("pack_id") != header["uuid"]]
    packs.append({"pack_id": header["uuid"], "version": header["version"]})
    with open(packs_path, "w", encoding="utf-8") as f:
        json.dump(packs, f, indent=4)
        f.write("\n")


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

    with tempfile.TemporaryDirectory() as staging:
        world_dir = os.path.join(staging, "world_template")
        shutil.copytree(WORLD_TEMPLATE_DIR, world_dir)
        install_behavior_pack(world_dir)
        zip_directory(world_dir, output_path)

    print(f"Packaged world template to {output_path}")


if __name__ == "__main__":
    main()
