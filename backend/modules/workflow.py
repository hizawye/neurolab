import requests

from ..schemas import LiteWorkflowRequest, LiteWorkflowResponse, RankedLigand, WorkflowWarning
from .descriptors import calculate_descriptors
from .errors import ExternalServiceError
from .ligand_finder import LigandFinder
from .ranker import score_descriptors
from .target_selector import TargetSelector


class LiteWorkflowRunner:
    def __init__(self):
        self.target_selector = TargetSelector()
        self.ligand_finder = LigandFinder()

    def run(self, request: LiteWorkflowRequest) -> LiteWorkflowResponse:
        warnings: list[WorkflowWarning] = []

        try:
            targets = self.target_selector.find_targets(request.query, limit=min(request.limit, 10))
        except (ExternalServiceError, requests.RequestException) as exc:
            targets = []
            warnings.append(WorkflowWarning(stage="targets", message=f"Target search failed: {exc}"))

        ligand_query = request.ligand_query or request.query
        try:
            ligands = self.ligand_finder.find_ligands(ligand_query, limit=request.limit)
        except ExternalServiceError as exc:
            ligands = []
            warnings.append(WorkflowWarning(stage="ligands", message=f"{exc.service} search failed: {exc}"))

        ranked: list[RankedLigand] = []
        for ligand in ligands:
            descriptors = calculate_descriptors(ligand.smiles)
            if descriptors is None:
                warnings.append(
                    WorkflowWarning(
                        stage="descriptors",
                        message=f"Skipped PubChem CID {ligand.cid}: invalid SMILES.",
                    )
                )
                continue

            score, notes = score_descriptors(descriptors)
            ranked.append(
                RankedLigand(
                    ligand=ligand,
                    descriptors=descriptors,
                    score=score,
                    notes=notes,
                )
            )

        ranked.sort(key=lambda item: item.score, reverse=True)

        return LiteWorkflowResponse(
            query=request.query,
            ligand_query=ligand_query,
            targets=targets,
            ligands=ranked,
            warnings=warnings,
        )
