from fastapi import APIRouter
from ..agents.science_planner import SciencePlanner

router = APIRouter()

science_planner = SciencePlanner()

@router.post("/plan_workflow/{goal}")
async def plan_workflow(goal: str):
    workflow = science_planner.plan_workflow(goal)
    return {"goal": goal, "workflow": workflow}
