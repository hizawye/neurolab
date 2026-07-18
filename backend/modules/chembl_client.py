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

