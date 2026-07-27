#!/usr/bin/env python3
"""Fetch PyPI package count, downloads, Zenodo archive count, and citation count, then update README.md."""

import sys
import time
import xmlrpc.client
from functools import lru_cache

import pyalex
import requests
from pyalex import Authors

pyalex.config.email = "dave.bunten@cuanschutz.edu"

PYPI_USER = "d33bs"
PYPI_PACKAGES_FILE = "pypi_packages.txt"
USER_AGENT = "d33bs-profile-readme (dave.bunten@cuanschutz.edu)"
ORCID = "0000-0001-6041-3665"
README = "README.md"


def _get_pypi_downloads(name):
    resp = requests.get(f"https://pypistats.org/api/packages/{name}/recent", timeout=15)
    if resp.status_code == 200:
        return resp.json()["data"]["last_month"]
    print(f"  Warning: could not fetch downloads for {name} (HTTP {resp.status_code})", file=sys.stderr)
    return 0


def _fetch_package_names():
    """Fetch the user's packages via PyPI's XML-RPC ``user_packages`` method.

    Returns the name of every project the user owns or maintains. The HTML
    profile page (https://pypi.org/user/<user>/) sits behind bot mitigation
    and can't be scraped from CI, so XML-RPC is the reliable machine-readable
    source. It is deprecated-but-live; the cached-file fallback in
    ``_load_package_names`` covers the day PyPI turns it off.
    """
    body = xmlrpc.client.dumps((PYPI_USER,), "user_packages")
    resp = requests.post(
        "https://pypi.org/pypi",
        data=body,
        headers={"Content-Type": "text/xml", "User-Agent": USER_AGENT},
        timeout=15,
    )
    resp.raise_for_status()
    (roles,), _method = xmlrpc.client.loads(resp.content)
    return [name for _role, name in roles]


def _read_cache():
    with open(PYPI_PACKAGES_FILE) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def _write_cache(names):
    with open(PYPI_PACKAGES_FILE, "w") as f:
        f.write("# Auto-generated fallback cache of d33bs's PyPI packages.\n")
        f.write("# Refreshed by .github/scripts/fetch_stats.py on each run; do not edit by hand.\n")
        for name in names:
            f.write(name + "\n")


@lru_cache(maxsize=1)
def _load_package_names():
    """Return the user's PyPI package names.

    Fetches the live list from PyPI and refreshes the on-disk cache. Falls
    back to that cache if the fetch fails or returns nothing, so a transient
    PyPI outage never blanks the README stats.
    """
    try:
        names = _fetch_package_names()
    except Exception as e:
        print(f"  Warning: could not fetch PyPI packages: {e}", file=sys.stderr)
        names = []

    if names:
        names = sorted(names)
        _write_cache(names)
        return names

    print("  Falling back to cached package list.", file=sys.stderr)
    return _read_cache()


def get_pypi_packages():
    return len(_load_package_names())


def get_pypi_downloads():
    total = 0
    for name in _load_package_names():
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
    # OpenAlex frequently splits one ORCID across several author entities
    # (this ORCID currently has 5), and the /authors/orcid: resolver may
    # return a sparse duplicate with 0 citations. Sum cited_by_count across
    # every entity carrying the ORCID instead; each work counts toward
    # exactly one entity, so there is no double-counting.
    authors = Authors().filter(orcid=ORCID).get()
    return sum(a["cited_by_count"] for a in authors)


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
