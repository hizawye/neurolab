"""Virtual screening endpoint.

Scores user-supplied compounds against a resolved target using the method the
benchmark validated. This is where prediction earns its keep: the existing
workflow endpoint retrieves what is already known to bind, which is a database
query. Screening asks the question that can actually be wrong.

Every response carries the method's validation record, so a score is never
returned without the evidence for trusting it.
"""

from fastapi import APIRouter, HTTPException

from ..modules import predictor, target_resolver
from ..modules.descriptors import calculate_descriptors
from ..modules.errors import ExternalServiceError
from ..modules.ligand_finder import LigandFinder
from ..modules import bbb_model
from ..schemas import (
    PredictedActivity,
    ScreenedCompound,
    ScreenRequest,
    ScreenResponse,
    WorkflowWarning,
)

router = APIRouter(prefix="/screen", tags=["screen"])

ligand_finder = LigandFinder()


def _canonical(smiles: str) -> str | None:
    """Canonical SMILES, so the same molecule compares equal however it is written."""
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
    return Chem.MolToSmiles(mol) if mol is not None else None


@router.post("", response_model=ScreenResponse)
async def screen_compounds(request: ScreenRequest):
    warnings: list[WorkflowWarning] = []

    try:
        target = target_resolver.resolve_by_name(request.target_query)
    except ExternalServiceError as exc:
        raise HTTPException(status_code=502, detail=f"{exc.service} lookup failed: {exc}") from exc

    if target is None:
        raise HTTPException(
            status_code=404,
            detail=f"No ChEMBL target matched '{request.target_query}'.",
        )

    try:
        pairs = ligand_finder.find_for_target(target, limit=request.reference_limit)
    except ExternalServiceError as exc:
        raise HTTPException(status_code=502, detail=f"{exc.service} lookup failed: {exc}") from exc

    if not pairs:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{target.pref_name} resolved, but ChEMBL holds no binding data for it. "
                "Similarity prediction needs known actives as reference."
            ),
        )

    # Reference set is the target's known binders. Prediction quality depends
    # directly on how well these cover the relevant chemical space, which is
    # why the count is reported back.
    references = predictor.build_references([ligand.smiles for ligand, _ in pairs])

    # Keyed on canonical SMILES, not the raw string. The same molecule has many
    # valid SMILES spellings, and a user typing a non-canonical form of a
    # compound that ChEMBL has measured would otherwise be shown a prediction
    # while its real measurement sat unused.
    measured_by_smiles = {
        canonical: activity
        for canonical, activity in (
            (_canonical(ligand.smiles), activity) for ligand, activity in pairs
        )
        if canonical is not None
    }

    # Batched: the model scores the whole request in one forward pass rather
    # than one per compound.
    if bbb_model.available():
        bbb_scores = bbb_model.predict_batch(request.smiles)
    else:
        bbb_scores = [None] * len(request.smiles)
        warnings.append(
            WorkflowWarning(
                stage="bbb",
                message=(
                    "BBB model artifact missing; penetration not predicted. "
                    "Run: uv run python -m backend.science.train_bbb"
                ),
            )
        )

    results: list[ScreenedCompound] = []
    for index, smiles in enumerate(request.smiles):
        descriptors = calculate_descriptors(smiles)
        if descriptors is None:
            warnings.append(
                WorkflowWarning(stage="parse", message=f"RDKit could not parse: {smiles}")
            )
            results.append(ScreenedCompound(query_smiles=smiles))
            continue

        prediction = predictor.predict_against(smiles, references)

        results.append(
            ScreenedCompound(
                query_smiles=smiles,
                descriptors=descriptors,
                predicted=PredictedActivity(**prediction) if prediction else None,
                # If the compound is already in the reference set it has real
                # data; surfacing that stops a measured value being presented
                # as a prediction.
                measured=measured_by_smiles.get(_canonical(smiles)),
                bbb_probability=bbb_scores[index],
            )
        )

    results.sort(
        key=lambda item: item.predicted.similarity if item.predicted else -1.0,
        reverse=True,
    )

    return ScreenResponse(
        resolved_target=target,
        method={
            **predictor.VALIDATION,
            "n_reference_actives": len(references),
            # The measured field is only populated from the reference set, which
            # is the target's top-N most potent binders. A compound can have
            # real ChEMBL data against this target and still show no measurement
            # here simply by not ranking in the top N — absence of a measurement
            # is not evidence that none exists.
            "measured_coverage": (
                f"Measured values are shown only for compounds among this target's "
                f"top {len(references)} known binders. A blank measurement means "
                f"'not in that set', not 'untested'."
            ),
            # BBB is a separate prediction with its own track record; keeping the
            # records apart stops one method's validation vouching for another.
            "bbb": bbb_model.validation_record() if bbb_model.available() else None,
        },
        results=results,
        warnings=warnings,
    )
