import requests
from fastapi import APIRouter, HTTPException, Query

from ..schemas import TargetResult
from ..modules.target_selector import TargetSelector

router = APIRouter(prefix="/targets", tags=["targets"])

target_selector = TargetSelector()


@router.get("/search", response_model=list[TargetResult])
async def search_targets(query: str = Query(min_length=1, max_length=120), limit: int = Query(default=10, ge=1, le=50)):
    try:
        return target_selector.find_targets(query, limit=limit)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"RCSB search failed: {exc}") from exc
