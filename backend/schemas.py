from pydantic import BaseModel, Field


class TargetResult(BaseModel):
    rcsb_id: str
    title: str | None = None
    source_url: str


class LigandResult(BaseModel):
    cid: int
    name: str
    smiles: str
    molecular_formula: str | None = None
    source_url: str


class DescriptorSet(BaseModel):
    molecular_weight: float
    logp: float
    tpsa: float
    h_bond_donors: int
    h_bond_acceptors: int


class RankedLigand(BaseModel):
    ligand: LigandResult
    descriptors: DescriptorSet
    score: float
    notes: list[str] = Field(default_factory=list)


class WorkflowWarning(BaseModel):
    stage: str
    message: str


class LiteWorkflowRequest(BaseModel):
    query: str = Field(min_length=1, max_length=120)
    ligand_query: str | None = Field(default=None, min_length=1, max_length=120)
    limit: int = Field(default=8, ge=1, le=25)


class LiteWorkflowResponse(BaseModel):
    query: str
    ligand_query: str
    targets: list[TargetResult]
    ligands: list[RankedLigand]
    warnings: list[WorkflowWarning] = Field(default_factory=list)
