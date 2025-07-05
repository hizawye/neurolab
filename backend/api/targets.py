from fastapi import APIRouter
from ..modules.target_selector import TargetSelector

router = APIRouter()

target_selector = TargetSelector()

@router.get("/targets/{condition_or_disease}")
async def get_targets(condition_or_disease: str):
    targets = target_selector.find_targets(condition_or_disease)
    return {"condition_or_disease": condition_or_disease, "targets": targets}
