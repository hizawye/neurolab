"""Blood-brain barrier penetration prediction.

Replaces the hand-tuned descriptor score, which was benchmarked against
measured BBB outcomes (B3DB, 7807 compounds, scaffold split) and lost:

    random forest on ECFP4     ROC-AUC 0.929
    TPSA alone                 ROC-AUC 0.823
    hand-tuned descriptor      ROC-AUC 0.799

The hand-tuned score was significantly worse than a *single descriptor* — a
paired bootstrap on the difference gave [-0.037, -0.009], entirely below zero.
Its molecular-weight, LogP and hydrogen-bond terms were not merely redundant
with TPSA, they were actively harmful. It was displayed to users for months as
a BBB read-out without ever having been tested.

Note the contrast with activity prediction, where the same evaluation approach
sent the opposite way and similarity search shipped over the ML. The principle
is the same in both cases — the evidence decides — and here the margin is
decisive rather than marginal, which is what justifies the model artifact.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .predictor import fingerprint

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODEL_DIR / "bbb_rf.joblib"
METADATA_PATH = MODEL_DIR / "bbb_rf.json"

_model = None
_metadata = None


class ModelUnavailable(RuntimeError):
    """Raised when the artifact or its evaluation record is missing."""


def _load():
    """Load lazily, and refuse a model that arrives without its track record.

    A prediction whose accuracy cannot be quoted has no place being shown to a
    user, so the metadata is a hard requirement rather than a nicety.
    """
    global _model, _metadata
    if _model is not None:
        return _model, _metadata

    if not MODEL_PATH.exists() or not METADATA_PATH.exists():
        raise ModelUnavailable(
            f"BBB model not found at {MODEL_PATH}. "
            "Run: uv run python -m backend.science.train_bbb"
        )

    import joblib

    _model = joblib.load(MODEL_PATH)
    _metadata = json.loads(METADATA_PATH.read_text())
    return _model, _metadata


def available() -> bool:
    try:
        _load()
        return True
    except ModelUnavailable:
        return False


def validation_record() -> dict:
    """Held-out numbers and the baselines this model had to beat."""
    _, metadata = _load()
    return {
        "method": "random forest over ECFP4, trained on B3DB",
        "dataset": f"{metadata['dataset']} ({metadata['n_total']} compounds)",
        "split": metadata["split"],
        "roc_auc": metadata["roc_auc"],
        "roc_auc_ci": metadata["roc_auc_ci"],
        "beats": metadata["baselines"],
        "caveat": (
            "Predicts BBB penetration class, not brain concentration. Trained on "
            "curated literature values whose assay conditions vary. Says nothing "
            "about efflux liability, metabolism, or free-fraction in brain tissue."
        ),
    }


def predict_batch(smiles_list: list[str]) -> list[float | None]:
    """P(BBB+) per compound; None where the SMILES will not parse."""
    model, _ = _load()

    fingerprints = [fingerprint(s) for s in smiles_list]
    usable = [i for i, fp in enumerate(fingerprints) if fp is not None]
    out: list[float | None] = [None] * len(smiles_list)
    if not usable:
        return out

    from rdkit import DataStructs

    matrix = np.zeros((len(usable), model.n_features_in_), dtype=np.uint8)
    for row, index in enumerate(usable):
        DataStructs.ConvertToNumpyArray(fingerprints[index], matrix[row])

    probabilities = model.predict_proba(matrix)[:, 1]
    for row, index in enumerate(usable):
        out[index] = round(float(probabilities[row]), 4)
    return out
