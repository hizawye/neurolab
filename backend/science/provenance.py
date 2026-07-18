"""Provenance and on-disk caching.

A benchmark result that cannot be re-run is not a result. Every dataset and
report carries the ChEMBL release it was built from and the seeds used, and
every raw API response is cached so a re-run reproduces byte-identical numbers
without touching the network.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_DIR = DATA_DIR / "cache"
BENCHMARK_DIR = DATA_DIR / "benchmarks"

# Threaded through every stochastic step (splits, model init, bootstrap) so a
# re-run is deterministic.
DEFAULT_SEED = 20260718

_STATUS_URL = "https://www.ebi.ac.uk/chembl/api/data/status"


def cache_key(namespace: str, params: dict) -> str:
    """Stable hash of a query, used as the cache filename."""
    payload = json.dumps({"ns": namespace, "params": params}, sort_keys=True)
    digest = hashlib.sha256(payload.encode()).hexdigest()[:24]
    return f"{namespace}-{digest}"


def cache_read(key: str) -> Any | None:
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    with path.open() as handle:
        return json.load(handle)


def cache_write(key: str, value: Any) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{key}.json"
    with path.open("w") as handle:
        json.dump(value, handle)


def offline() -> bool:
    """When set, a cache miss is an error rather than a network call.

    Used to prove reproducibility: a second run with NEUROLAB_OFFLINE=1 must
    produce identical output purely from cache.
    """
    return os.getenv("NEUROLAB_OFFLINE", "").strip().lower() in {"1", "true", "yes"}


def chembl_release() -> str:
    """The ChEMBL version datasets are pinned to, e.g. 'ChEMBL_37'."""
    key = cache_key("status", {})
    cached = cache_read(key)
    if cached is None:
        if offline():
            raise RuntimeError("Offline mode: ChEMBL release not in cache.")
        response = requests.get(_STATUS_URL, params={"format": "json"}, timeout=30)
        response.raise_for_status()
        cached = response.json()
        cache_write(key, cached)
    return cached.get("chembl_db_version", "unknown")


def run_metadata(seed: int = DEFAULT_SEED, **extra: Any) -> dict:
    """Metadata block stamped onto every dataset and report."""
    return {
        "chembl_release": chembl_release(),
        "seed": seed,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **extra,
    }
