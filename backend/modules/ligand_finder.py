from cachetools import cached, TTLCache
import requests

from ..schemas import LigandResult
from .errors import ExternalServiceError

cache = TTLCache(maxsize=200, ttl=3600)


class LigandFinder:
    def __init__(self):
        self.base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
        self.timeout_seconds = 12

    def find_ligands(self, query: str, limit: int = 8) -> list[LigandResult]:
        names = self._candidate_names(query)[:limit]
        ligands: list[LigandResult] = []

        for name in names:
            try:
                ligands.extend(self._fetch_by_name(name, remaining=limit - len(ligands)))
            except ExternalServiceError:
                if name == query:
                    raise

            if len(ligands) >= limit:
                break

        return ligands[:limit]

    def _candidate_names(self, query: str) -> list[str]:
        normalized = query.strip().lower()
        candidates = [query.strip()]

        if "mao-b" in normalized or "maob" in normalized:
            candidates.extend(["selegiline", "rasagiline", "safinamide"])
        if "dopamine" in normalized:
            candidates.extend(["selegiline", "rasagiline", "bupropion"])
        if "nmda" in normalized:
            candidates.extend(["memantine", "ketamine", "dextromethorphan"])

        seen: set[str] = set()
        unique: list[str] = []
        for candidate in candidates:
            key = candidate.lower()
            if candidate and key not in seen:
                unique.append(candidate)
                seen.add(key)
        return unique

    @cached(cache)
    def _fetch_by_name(self, name: str, remaining: int) -> tuple[LigandResult, ...]:
        try:
            cids_response = requests.get(
                f"{self.base_url}/compound/name/{name}/cids/JSON",
                timeout=self.timeout_seconds,
            )
            if cids_response.status_code == 404:
                return ()
            cids_response.raise_for_status()
            cids = cids_response.json().get("IdentifierList", {}).get("CID", [])[:remaining]
            if not cids:
                return ()

            properties = "CanonicalSMILES,ConnectivitySMILES,MolecularFormula,IUPACName"
            props_response = requests.get(
                f"{self.base_url}/compound/cid/{','.join(str(cid) for cid in cids)}/property/{properties}/JSON",
                timeout=self.timeout_seconds,
            )
            props_response.raise_for_status()
        except requests.RequestException as exc:
            raise ExternalServiceError("PubChem", str(exc)) from exc

        results = []
        for item in props_response.json().get("PropertyTable", {}).get("Properties", []):
            cid = item.get("CID")
            smiles = item.get("CanonicalSMILES") or item.get("ConnectivitySMILES")
            if not cid or not smiles:
                continue

            results.append(
                LigandResult(
                    cid=cid,
                    name=item.get("IUPACName") or name,
                    smiles=smiles,
                    molecular_formula=item.get("MolecularFormula"),
                    source_url=f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
                )
            )

        return tuple(results)
