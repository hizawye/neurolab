from fastapi import APIRouter, HTTPException, Query

from ..modules import target_resolver
from ..modules.errors import ExternalServiceError
from ..modules.ligand_finder import LigandFinder
from ..schemas import RankedLigand
from ..modules.descriptors import calculate_descriptors
from ..modules.ranker import score_descriptors

router = APIRouter(prefix="/ligands", tags=["ligands"])

ligand_finder = LigandFinder()


@router.get("/search", response_model=list[RankedLigand])
async def search_ligands(query: str = Query(min_length=1, max_length=120), limit: int = Query(default=8, ge=1, le=25)):
    """Known binders of the protein target named by `query`, most potent first."""
    try:
        target = target_resolver.resolve_by_name(query)
        if target is None:
            raise HTTPException(status_code=404, detail=f"No ChEMBL target matched '{query}'.")

        pairs = ligand_finder.find_for_target(target, limit=limit)
    except ExternalServiceError as exc:
        raise HTTPException(status_code=502, detail=f"{exc.service} search failed: {exc}") from exc

    ranked = []
    for ligand, activity in pairs:
        descriptors = calculate_descriptors(ligand.smiles)
        if descriptors is None:
            continue
        score, notes = score_descriptors(descriptors)
        ranked.append(
            RankedLigand(
                ligand=ligand,
                descriptors=descriptors,
                activity=activity,
                score=score,
                notes=notes,
            )
        )
    return ranked
