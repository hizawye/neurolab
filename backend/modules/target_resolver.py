from . import chembl_client
from ..schemas import ResolvedTarget

PREFERRED_ORGANISM = "Homo sapiens"
PREFERRED_TARGET_TYPE = "SINGLE PROTEIN"


def _uniprot_accession(target: dict) -> str | None:
    for component in target.get("target_components", []):
        accession = component.get("accession")
        if accession:
            return accession
    return None


def _preference_rank(target: dict, relevance_index: int) -> tuple:
    """Rank candidates so a human single-protein target wins ties.

    ChEMBL's search returns cross-species and protein-family entries alongside
    the single human protein. Ranking on bioactivity data intended for human
    drug discovery, so prefer that; relevance order breaks remaining ties.
    """
    is_human = target.get("organism") == PREFERRED_ORGANISM
    is_single_protein = target.get("target_type") == PREFERRED_TARGET_TYPE
    return (not is_human, not is_single_protein, relevance_index)


def _to_resolved(target: dict) -> ResolvedTarget:
    chembl_id = target.get("target_chembl_id")
    return ResolvedTarget(
        chembl_id=chembl_id,
        pref_name=target.get("pref_name") or chembl_id,
        organism=target.get("organism"),
        target_type=target.get("target_type"),
        uniprot_accession=_uniprot_accession(target),
        match_score=target.get("score"),
        source_url=f"https://www.ebi.ac.uk/chembl/target_report_card/{chembl_id}/",
    )


def _best(candidates: tuple[dict, ...]) -> ResolvedTarget | None:
    usable = [t for t in candidates if t.get("target_chembl_id")]
    if not usable:
        return None

    ranked = sorted(
        enumerate(usable),
        key=lambda pair: _preference_rank(pair[1], pair[0]),
    )
    return _to_resolved(ranked[0][1])


def resolve_by_name(query: str) -> ResolvedTarget | None:
    """Resolve free text (e.g. "dopamine D2 receptor") to one ChEMBL target."""
    return _best(chembl_client.search_targets(query.strip(), limit=10))


def resolve_by_uniprot(accession: str) -> ResolvedTarget | None:
    """Resolve a UniProt accession to its ChEMBL target."""
    return _best(chembl_client.targets_by_uniprot(accession, limit=5))
