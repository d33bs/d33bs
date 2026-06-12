#!/usr/bin/env python3
"""Fetch PyPI package count, Zenodo archive count, and citation count, then update README.md."""

import sys

import requests
from pyalex import Authors

PYPI_PACKAGES_FILE = "pypi_packages.txt"
ORCID = "0000-0001-6041-3665"
README = "README.md"


def get_pypi_packages():
    """Count packages listed in pypi_packages.txt that exist on PyPI."""
    with open(PYPI_PACKAGES_FILE) as f:
        names = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    count = 0
    for name in names:
        resp = requests.get(f"https://pypi.org/pypi/{name}/json", timeout=15)
        if resp.status_code == 200:
            count += 1
        elif resp.status_code == 404:
            print(f"  Warning: {name} not found on PyPI", file=sys.stderr)
        else:
            print(f"  Warning: {name} returned HTTP {resp.status_code}", file=sys.stderr)
    return count


def get_zenodo_archives():
    resp = requests.get(
        "https://zenodo.org/api/records",
        params={"q": f"creators.orcid:{ORCID}", "size": 1},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["hits"]["total"]


def get_citation_count():
    author = Authors()["orcid:" + ORCID]
    return author["cited_by_count"]


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
