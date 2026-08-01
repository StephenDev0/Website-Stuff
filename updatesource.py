#!/usr/bin/env python3
"""Update the StikDebug AltSource entry from the latest GitHub release."""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SOURCE_REPOSITORY = "StephenDev0/StikDebug"
APP_BUNDLE_IDENTIFIER = "com.stik.stikdebug"
MINIMUM_IOS_VERSION = "17.4"


def fetch_latest_release():
    request = Request(
        f"https://api.github.com/repos/{SOURCE_REPOSITORY}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "StikDebug-source-updater"},
    )
    try:
        with urlopen(request) as response:
            return json.load(response)
    except (HTTPError, URLError) as error:
        raise RuntimeError(f"Unable to fetch the latest StikDebug release: {error}") from error


def clean_description(description):
    description = description or "No release notes provided."
    description = re.sub(r"<[^>]+>", "", description)
    description = re.sub(r"^#{1,6}\s*", "", description, flags=re.MULTILINE)
    description = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", description)
    description = description.replace("`", '"')
    return description.strip()


def release_version(tag):
    match = re.search(r"(\d+\.\d+\.\d+)", tag)
    if not match:
        raise ValueError(f"Could not find a semantic version in release tag {tag!r}.")
    return match.group(1)


def update_index(index_path, release):
    with index_path.open() as source_file:
        source = json.load(source_file)

    app = next(
        (app for app in source["apps"] if app.get("bundleIdentifier") == APP_BUNDLE_IDENTIFIER),
        None,
    )
    if app is None:
        raise ValueError(f"No app with bundle identifier {APP_BUNDLE_IDENTIFIER} in {index_path}.")

    version = release_version(release["tag_name"])
    ipa_asset = next(
        (asset for asset in release.get("assets", []) if asset["name"].lower().endswith(".ipa")),
        None,
    )
    if ipa_asset is None:
        raise ValueError(f"Release {release['tag_name']} has no IPA asset.")

    published_at = datetime.fromisoformat(release["published_at"].replace("Z", "+00:00"))
    version_entry = {
        "version": version,
        "date": published_at.date().isoformat(),
        "localizedDescription": clean_description(release.get("body")),
        "downloadURL": ipa_asset["browser_download_url"],
        "size": ipa_asset["size"],
        "minOSVersion": MINIMUM_IOS_VERSION,
    }

    if app.get("versions", [None])[0] == version_entry:
        print(f"StikDebug {version} is already current; no changes needed.")
        return False

    # The source deliberately exposes only the current StikDebug build.
    app["versions"] = [version_entry]
    with index_path.open("w") as source_file:
        json.dump(source, source_file, indent=2)
        source_file.write("\n")

    print(f"Updated StikDebug source to {version}.")
    return True


def main():
    index_path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("index.json")
    update_index(index_path, fetch_latest_release())


if __name__ == "__main__":
    main()
