from fastapi import APIRouter, HTTPException, Query

from ..modules.errors import ExternalServiceError
from ..modules.ligand_finder import LigandFinder
from ..schemas import LigandResult

router = APIRouter(prefix="/ligands", tags=["ligands"])

ligand_finder = LigandFinder()


@router.get("/search", response_model=list[LigandResult])
async def search_ligands(query: str = Query(min_length=1, max_length=120), limit: int = Query(default=8, ge=1, le=25)):
    try:
        return ligand_finder.find_ligands(query, limit=limit)
    except ExternalServiceError as exc:
        raise HTTPException(status_code=502, detail=f"{exc.service} search failed: {exc}") from exc
