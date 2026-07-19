from cachetools import cached, TTLCache
import requests

from .errors import ExternalServiceError

BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"
TIMEOUT_SECONDS = 20

target_cache = TTLCache(maxsize=200, ttl=3600)
activity_cache = TTLCache(maxsize=200, ttl=3600)


def _get(path: str, params: dict) -> dict:
    try:
        response = requests.get(
            f"{BASE_URL}/{path}",
            params={**params, "format": "json"},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise ExternalServiceError("ChEMBL", str(exc)) from exc


@cached(target_cache)
def search_targets(query: str, limit: int = 10) -> tuple[dict, ...]:
    payload = _get("target/search", {"q": query, "limit": limit})
    return tuple(payload.get("targets", []))


@cached(target_cache)
def targets_by_uniprot(accession: str, limit: int = 5) -> tuple[dict, ...]:
    payload = _get("target", {"target_components__accession": accession, "limit": limit})
    return tuple(payload.get("targets", []))


@cached(activity_cache)
def activities_for_target(
    target_chembl_id: str,
    standard_types: tuple[str, ...],
    limit: int,
) -> tuple[dict, ...]:
    """Most-potent activity records for a target, highest pChEMBL first.

    Only records carrying a pChEMBL value are requested, so every row is a
    comparable -log10(molar) potency rather than a raw mixed-unit number.
    """
    payload = _get(
        "activity",
        {
            "target_chembl_id": target_chembl_id,
            "pchembl_value__isnull": "false",
            "standard_type__in": ",".join(standard_types),
            "order_by": "-pchembl_value",
            "limit": limit,
        },
    )
    return tuple(payload.get("activities", []))

