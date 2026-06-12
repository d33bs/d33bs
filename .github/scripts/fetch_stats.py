#!/usr/bin/env python3
"""Fetch PyPI package count, Zenodo archive count, and citation count, then update README.md."""

import json
import sys
import urllib.error
import urllib.request

PYPI_PACKAGES_FILE = "pypi_packages.txt"
ORCID = "0000-0001-6041-3665"
README = "README.md"


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-stats-updater/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def get_pypi_packages():
    """Count packages listed in pypi_packages.txt that exist on PyPI."""
    with open(PYPI_PACKAGES_FILE) as f:
        names = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    count = 0
    for name in names:
        try:
            fetch_json(f"https://pypi.org/pypi/{name}/json")
            count += 1
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"  Warning: {name} not found on PyPI", file=sys.stderr)
            else:
                print(f"  Warning: {name} returned HTTP {e.code}", file=sys.stderr)
        except Exception as e:
            print(f"  Warning: {name} check failed: {e}", file=sys.stderr)
    return count


def get_zenodo_archives():
    data = fetch_json(
        f"https://zenodo.org/api/records?q=creators.orcid:{ORCID}&size=1"
    )
    return data["hits"]["total"]


def get_citation_count():
    data = fetch_json(f"https://api.openalex.org/authors/orcid:{ORCID}")
    return data["cited_by_count"]


def main():
    print("Fetching PyPI package count...")
    pypi = get_pypi_packages()
    print(f"  PyPI packages: {pypi}")

    print("Fetching Zenodo archive count...")
    zenodo = get_zenodo_archives()
    print(f"  Zenodo archives: {zenodo}")

    print("Fetching citation count...")
    citations = get_citation_count()
    print(f"  Citations: {citations}")

    with open(README) as f:
        content = f.read()

    content = content.replace("{{ PYPI_PACKAGES }}", str(pypi))
    content = content.replace("{{ ZENODO_ARCHIVES }}", str(zenodo))
    content = content.replace("{{ CITATION_COUNT }}", str(citations))

    with open(README, "w") as f:
        f.write(content)

    print("README.md updated.")


if __name__ == "__main__":
    main()
