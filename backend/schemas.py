from pydantic import BaseModel, Field


class TargetResult(BaseModel):
    rcsb_id: str
    title: str | None = None
    source_url: str


class ResolvedTarget(BaseModel):
    chembl_id: str
    pref_name: str
    organism: str | None = None
    target_type: str | None = None
    uniprot_accession: str | None = None
    match_score: float | None = None
    source_url: str


class LigandResult(BaseModel):
    chembl_id: str
    name: str | None = None
    smiles: str
    source_url: str


class ActivityEvidence(BaseModel):
    """Measured potency against the resolved target, aggregated per molecule."""

    pchembl_value: float
    standard_type: str
    measurement_count: int


class DescriptorSet(BaseModel):
    molecular_weight: float
    logp: float
    tpsa: float
    h_bond_donors: int
    h_bond_acceptors: int


class RankedLigand(BaseModel):
    ligand: LigandResult
    descriptors: DescriptorSet
    activity: ActivityEvidence | None = None
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
    resolved_target: ResolvedTarget | None = None
    targets: list[TargetResult]
    ligands: list[RankedLigand]
    warnings: list[WorkflowWarning] = Field(default_factory=list)
