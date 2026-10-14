"""Decides whether Mojang's bedrock-samples warrants a new release and prepares it.

A release is made when bedrock-samples has a release (non-preview) tag that did not
exist at the time of the previous release AND the biome list in mojang-biomes.json has changed since
then. The state of each release (upstream tags and biomes) is stored in
release-state.json, which the workflow attaches to the release so the next run can
compare against it.

When a release is warranted, this script also:
    - writes the release notes (which biomes were added/removed),
    - stamps the release version into the pack manifest,
    - pins the biome URL used by the build_dimension_definitions filter to the
      bedrock-samples commit that was checked, so the build matches the notes.

Results are written to $GITHUB_OUTPUT: release (true/false), tag and version.
"""
import argparse
import json
import os
import re
import subprocess
import urllib.request

UPSTREAM_REPO = "https://github.com/Mojang/bedrock-samples"
UPSTREAM_BRANCH = "main"
BIOMES_PATH = "metadata/vanilladata_modules/mojang-biomes.json"
RAW_URL = "https://raw.githubusercontent.com/Mojang/bedrock-samples/{ref}/" + BIOMES_PATH

CONFIG_PATH = "config.json"
BP_MANIFEST_PATH = os.path.join("packs", "BP", "manifest.json")
DIMENSION_FILTER = "build_dimension_definitions"
RELEASE_PROFILE = "release"


def ls_remote(option, pattern=None):
    command = ["git", "ls-remote", option, UPSTREAM_REPO] + ([pattern] if pattern else [])
    output = subprocess.run(command, check=True, capture_output=True, text=True).stdout
    return [line.split("\t") for line in output.splitlines() if line]


def fetch_upstream_release_tags():
    tags = {ref.removeprefix("refs/tags/").removesuffix("^{}") for _, ref in ls_remote("--tags")}
    return sorted(tag for tag in tags if "preview" not in tag)


def fetch_upstream_commit():
    refs = ls_remote("--heads", f"refs/heads/{UPSTREAM_BRANCH}")
    if len(refs) != 1:
        raise RuntimeError(f"Could not resolve {UPSTREAM_BRANCH} in {UPSTREAM_REPO}")
    return refs[0][0]


def fetch_biomes(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        data = json.load(response)
    return sorted(item["name"] for item in data["data_items"])


def version_key(tag):
    return [int(part) for part in re.findall(r"\d+", tag)]


def newest_tag(tags):
    return max(tags, key=version_key)


def parse_version(text):
    return tuple(int(part) for part in text.lstrip("v").split("."))


def next_version(previous_tag, manifest_version):
    if not previous_tag:
        return manifest_version
    previous = parse_version(previous_tag)
    if manifest_version > previous:
        return manifest_version
    return (*previous[:2], previous[2] + 1)


def display_name(biome):
    return biome.split(":", 1)[1].replace("_", " ").title()


def biome_list(biomes):
    return "\n".join(f"- {display_name(biome)} (`{biome}`)" for biome in biomes)


def build_release_notes(added, removed, upstream_tag, initial):
    sections = []
    if initial:
        sections.append(f"## Supported biomes\n\n{biome_list(added)}")
    else:
        if added:
            sections.append(f"## Added support for\n\n{biome_list(added)}")
        if removed:
            sections.append(f"## Removed biomes\n\nThese biomes no longer exist in vanilla Minecraft:\n\n{biome_list(removed)}")
    sections.append(f"Biome list from [Mojang/bedrock-samples {upstream_tag}]({UPSTREAM_REPO}/tree/{upstream_tag}).")
    return "\n\n".join(sections) + "\n"


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        f.write("\n")


def stamp_version(path, version):
    manifest = read_json(path)
    manifest["header"]["version"] = list(version)
    for module in manifest.get("modules", []):
        module["version"] = list(version)
    write_json(path, manifest)


def pin_biomes_url(url):
    config = read_json(CONFIG_PATH)
    for entry in config["regolith"]["profiles"][RELEASE_PROFILE]["filters"]:
        if entry.get("filter") == DIMENSION_FILTER:
            entry.setdefault("settings", {})["url"] = url
    write_json(CONFIG_PATH, config)


def set_outputs(**outputs):
    lines = [f"{key}={value}" for key, value in outputs.items()]
    print("\n".join(lines))
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous-state", help="release-state.json from the latest release, if any")
    parser.add_argument("--previous-tag", default="", help="tag of the latest release, if any")
    parser.add_argument("--out", required=True, help="directory for release-state.json and release-notes.md")
    args = parser.parse_args()

    previous = None
    if args.previous_state and os.path.exists(args.previous_state):
        previous = read_json(args.previous_state)

    tags = fetch_upstream_release_tags()
    commit = fetch_upstream_commit()
    biomes_url = RAW_URL.format(ref=commit)
    biomes = fetch_biomes(biomes_url)

    if previous is None:
        new_tags, added, removed = tags, biomes, []
    else:
        new_tags = sorted(set(tags) - set(previous["upstreamTags"]))
        added = sorted(set(biomes) - set(previous["biomes"]))
        removed = sorted(set(previous["biomes"]) - set(biomes))

    print(f"New upstream release tags: {', '.join(new_tags) or 'none'}")
    print(f"Biomes added: {', '.join(added) or 'none'}; removed: {', '.join(removed) or 'none'}")

    if not new_tags or not (added or removed):
        set_outputs(release="false")
        return

    version = next_version(args.previous_tag, tuple(read_json(BP_MANIFEST_PATH)["header"]["version"]))
    upstream_tag = newest_tag(new_tags)

    os.makedirs(args.out, exist_ok=True)
    write_json(os.path.join(args.out, "release-state.json"), {
        "upstreamTag": upstream_tag,
        "upstreamCommit": commit,
        "upstreamTags": tags,
        "biomes": biomes,
    })
    with open(os.path.join(args.out, "release-notes.md"), "w", encoding="utf-8") as f:
        f.write(build_release_notes(added, removed, upstream_tag, initial=previous is None))

    stamp_version(BP_MANIFEST_PATH, version)
    pin_biomes_url(biomes_url)

    version_text = ".".join(map(str, version))
    set_outputs(release="true", tag=f"v{version_text}", version=version_text, upstream_tag=upstream_tag)


if __name__ == "__main__":
    main()
