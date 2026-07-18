import requests

from ..schemas import LiteWorkflowRequest, LiteWorkflowResponse, RankedLigand, WorkflowWarning
from . import target_resolver
from .descriptors import calculate_descriptors
from .errors import ExternalServiceError
from .ligand_finder import LigandFinder
from .ranker import score_descriptors
from .target_selector import TargetSelector

# ChEMBL relevance below this is reported as a weak match. Calibrated loosely:
# real hits observed at 21-32, a nonsense query matching one stray word at 18.
# It flags the obvious misses, not a guarantee the match is correct.
LOW_CONFIDENCE_MATCH_SCORE = 20.0


class LiteWorkflowRunner:
    def __init__(self):
        self.target_selector = TargetSelector()
        self.ligand_finder = LigandFinder()

    def run(self, request: LiteWorkflowRequest) -> LiteWorkflowResponse:
        warnings: list[WorkflowWarning] = []
        ligand_query = request.ligand_query or request.query

        try:
            structures = self.target_selector.find_targets(request.query, limit=min(request.limit, 10))
        except (ExternalServiceError, requests.RequestException) as exc:
            structures = []
            warnings.append(WorkflowWarning(stage="targets", message=f"Structure search failed: {exc}"))

        resolved_target = None
        try:
            resolved_target = target_resolver.resolve_by_name(ligand_query)
            if resolved_target is None:
                warnings.append(
                    WorkflowWarning(
                        stage="target_resolution",
                        message=(
                            f"No ChEMBL target matched '{ligand_query}'. "
                            "Try a specific protein name, e.g. 'dopamine D2 receptor'."
                        ),
                    )
                )
            elif (resolved_target.match_score or 0) < LOW_CONFIDENCE_MATCH_SCORE:
                # ChEMBL's search is fuzzy enough to match a stray word, so a
                # weak hit gets flagged for the user rather than silently used.
                warnings.append(
                    WorkflowWarning(
                        stage="target_resolution",
                        message=(
                            f"Weak match: '{ligand_query}' resolved to "
                            f"{resolved_target.pref_name}. Confirm this is the intended target."
                        ),
                    )
                )
        except ExternalServiceError as exc:
            warnings.append(
                WorkflowWarning(stage="target_resolution", message=f"{exc.service} lookup failed: {exc}")
            )

        pairs = []
        if resolved_target is not None:
            try:
                pairs = self.ligand_finder.find_for_target(resolved_target, limit=request.limit)
                if not pairs:
                    warnings.append(
                        WorkflowWarning(
                            stage="ligands",
                            message=(
                                f"{resolved_target.pref_name} resolved, but ChEMBL holds no "
                                "binding-affinity records for it."
                            ),
                        )
                    )
            except ExternalServiceError as exc:
                warnings.append(
                    WorkflowWarning(stage="ligands", message=f"{exc.service} activity lookup failed: {exc}")
                )

        ranked: list[RankedLigand] = []
        for ligand, activity in pairs:
            descriptors = calculate_descriptors(ligand.smiles)
            if descriptors is None:
                warnings.append(
                    WorkflowWarning(
                        stage="descriptors",
                        message=f"Skipped {ligand.chembl_id}: RDKit could not parse its SMILES.",
                    )
                )
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

        # Measured affinity orders the list; the descriptor score rides along as
        # a developability read-out rather than the ranking signal.
        ranked.sort(key=lambda item: item.activity.pchembl_value, reverse=True)

        return LiteWorkflowResponse(
            query=request.query,
            ligand_query=ligand_query,
            resolved_target=resolved_target,
            targets=structures,
            ligands=ranked,
            warnings=warnings,
        )
