#!/usr/bin/env python3
"""Fetch PyPI package count, downloads, Zenodo archive count, and citation count, then update README.md."""

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pyalex
import requests
from pyalex import Authors

pyalex.config.email = "dave.bunten@cuanschutz.edu"

PYPI_PACKAGES_FILE = "pypi_packages.txt"
ORCID = "0000-0001-6041-3665"
README = "README.md"


def _check_pypi_package(name):
    resp = requests.get(f"https://pypi.org/pypi/{name}/json", timeout=15)
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        print(f"  Warning: {name} not found on PyPI", file=sys.stderr)
    else:
        print(f"  Warning: {name} returned HTTP {resp.status_code}", file=sys.stderr)
    return False


def _get_pypi_downloads(name):
    resp = requests.get(f"https://pypistats.org/api/packages/{name}/recent", timeout=15)
    if resp.status_code == 200:
        return resp.json()["data"]["last_month"]
    print(f"  Warning: could not fetch downloads for {name} (HTTP {resp.status_code})", file=sys.stderr)
    return 0


def _load_package_names():
    with open(PYPI_PACKAGES_FILE) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def get_pypi_packages():
    names = _load_package_names()
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_check_pypi_package, name): name for name in names}
        return sum(1 for f in as_completed(futures) if f.result())


def get_pypi_downloads():
    names = _load_package_names()
    total = 0
    for name in names:
        total += _get_pypi_downloads(name)
        time.sleep(0.5)
    return total


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


def fetch_stat(label, fn):
    try:
        value = fn()
        print(f"  {label}: {value}")
        return value
    except Exception as e:
        print(f"  Warning: could not fetch {label}: {e}", file=sys.stderr)
        return None


def main():
    print("Fetching stats...")
    pypi = fetch_stat("PyPI packages", get_pypi_packages)
    downloads = fetch_stat("PyPI downloads (last month)", get_pypi_downloads)
    zenodo = fetch_stat("Zenodo archives", get_zenodo_archives)
    citations = fetch_stat("Citations", get_citation_count)

    with open(README) as f:
        content = f.read()

    if pypi is not None:
        content = content.replace("{{ PYPI_PACKAGES }}", str(pypi))
    if downloads is not None:
        content = content.replace("{{ PYPI_DOWNLOADS }}", f"{downloads:,}")
    if zenodo is not None:
        content = content.replace("{{ ZENODO_ARCHIVES }}", str(zenodo))
    if citations is not None:
        content = content.replace("{{ CITATION_COUNT }}", str(citations))

    with open(README, "w") as f:
        f.write(content)

    print("README.md updated.")


if __name__ == "__main__":
    main()
