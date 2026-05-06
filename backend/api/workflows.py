from fastapi import APIRouter

from ..modules.workflow import LiteWorkflowRunner
from ..schemas import LiteWorkflowRequest, LiteWorkflowResponse

router = APIRouter(prefix="/workflows", tags=["workflows"])

workflow_runner = LiteWorkflowRunner()


@router.post("/run-lite", response_model=LiteWorkflowResponse)
async def run_lite_workflow(request: LiteWorkflowRequest):
    return workflow_runner.run(request)
