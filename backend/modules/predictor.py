"""Activity prediction for compounds with no measured affinity.

Scores a query compound by its maximum ECFP4 Tanimoto similarity to the known
actives of a resolved target. This is the method the benchmark validated, and
it was chosen over the machine-learning alternatives on evidence rather than
preference:

- It beat random and the descriptor score outside the bootstrap interval on
  every split of every target tested.
- It beat random forest on EF@1% for all three CNS targets, which is the
  metric that matters when only the top slice of a library can be assayed.
- Random forest edged it on BEDROC for two of three targets, but the advantage
  did not hold on MAO-B and did not appear in early enrichment at all. That is
  not enough to justify shipping a trained model, its versioning, and its
  retraining story.

See reports/ for the numbers behind each of those statements.

The score is a similarity, not a probability and not an affinity. It says
"this resembles known binders", which is a prioritisation signal and nothing
more.
"""

from __future__ import annotations

from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import rdFingerprintGenerator

RDLogger.DisableLog("rdApp.*")

FP_RADIUS = 2
FP_BITS = 2048

# Must match the benchmark's featurisation exactly, or the validation numbers
# describe a different method than the one running here.
_generator = rdFingerprintGenerator.GetMorganGenerator(radius=FP_RADIUS, fpSize=FP_BITS)

# Measured on the held-out scaffold split of the Track B (realistic screening)
# benchmark, ChEMBL_37. Surfaced with predictions so a score is never shown
# without its track record.
VALIDATION = {
    "method": "max ECFP4 Tanimoto to known actives",
    "benchmark": "Track B scaffold split, ChEMBL_37",
    "targets_tested": 3,
    "bedroc_range": [0.874, 0.962],
    "ef_1pct_range": [84.1, 92.5],
    "roc_auc_range": [0.962, 0.992],
    "caveat": (
        "Retrospective benchmark performance overestimates prospective performance. "
        "Predicts activity only for targets with existing ChEMBL actives, and says "
        "nothing about selectivity, toxicity, or synthesizability."
    ),
    # Measured, not asserted: ROC-AUC falls from 0.962 against random library
    # compounds to 0.794 against compounds measured inactive on the same target.
    # Users need this to know which question the tool can answer.
    "best_for": "Triaging a diverse library down to the right chemical neighbourhood.",
    "weak_for": (
        "Choosing between close analogs. Similarity cannot see activity cliffs, where one "
        "substituent changes affinity by orders of magnitude while the fingerprint barely "
        "moves (ROC-AUC 0.962 vs random compounds, 0.794 vs measured inactives)."
    ),
}


def fingerprint(smiles: str):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return _generator.GetFingerprint(mol)


def build_references(reference_smiles: list[str]) -> list[tuple[str, object]]:
    """Fingerprint a target's known actives once, for reuse across a batch.

    Screening a library against one target would otherwise re-fingerprint every
    reference for every query — 100 references against 200 compounds is 20,000
    redundant computations of an identical result.
    """
    prepared = ((s, fingerprint(s)) for s in reference_smiles)
    return [(s, fp) for s, fp in prepared if fp is not None]


def predict(query_smiles: str, reference_smiles: list[str]) -> dict | None:
    """Score one compound against a target's known actives.

    Convenience wrapper that prepares references on the spot. For more than one
    query, build the references once with `build_references` and call
    `predict_against` instead.
    """
    return predict_against(query_smiles, build_references(reference_smiles))


def predict_against(query_smiles: str, references: list[tuple[str, object]]) -> dict | None:
    """Score one compound against already-fingerprinted references.

    Returns the best similarity and which reference produced it, so the
    prediction is inspectable rather than a bare number.
    """
    query_fp = fingerprint(query_smiles)
    if query_fp is None or not references:
        return None

    similarities = DataStructs.BulkTanimotoSimilarity(
        query_fp, [fp for _, fp in references]
    )
    best_index = max(range(len(similarities)), key=similarities.__getitem__)

    return {
        "similarity": round(float(similarities[best_index]), 4),
        "nearest_active_smiles": references[best_index][0],
        "n_references": len(references),
    }
