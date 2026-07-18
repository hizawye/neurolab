"""Bulk, disk-cached ChEMBL retrieval for benchmark datasets.

Kept out of `backend.modules.chembl_client`, which serves the request path and
only ever fetches a single page into an in-memory TTL cache. Bulk retrieval is
a research concern: it pages through thousands of records and persists them to
disk so a benchmark re-runs offline and reproduces identical numbers.
"""

from __future__ import annotations

from ..modules.chembl_client import _get
from . import provenance

PAGE_SIZE = 1000


def fetch_all(
    path: str,
    params: dict,
    max_records: int = 20000,
    start_offset: int = 0,
) -> list[dict]:
    """Page through a ChEMBL list endpoint, caching the full result to disk.

    Cached by query, so a repeat run is offline and byte-identical. The
    collection key differs per endpoint ('activities', 'targets', ...), so it
    is read from the response rather than assumed.
    """
    key = provenance.cache_key(
        f"page-{path}", {**params, "max": max_records, "start": start_offset}
    )
    cached = provenance.cache_read(key)
    if cached is not None:
        return cached

    if provenance.offline():
        raise RuntimeError(f"Offline mode: {path} {params} not in cache.")

    collected: list[dict] = []
    offset = start_offset
    while len(collected) < max_records:
        payload = _get(
            path,
            {**params, "limit": min(PAGE_SIZE, max_records - len(collected)), "offset": offset},
        )
        records = next(
            (value for key_name, value in payload.items() if key_name != "page_meta"),
            [],
        )
        if not isinstance(records, list) or not records:
            break

        collected.extend(records)
        offset += len(records)
        if not payload.get("page_meta", {}).get("next"):
            break

    provenance.cache_write(key, collected)
    return collected
