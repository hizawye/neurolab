"""Train and persist the BBB penetration model.

    uv run python -m backend.science.train_bbb

Writes backend/models/bbb_rf.joblib plus a sidecar JSON recording the held-out
numbers, the training data, and the seed. The API refuses to load a model
without that record, so a prediction can always be traced to the evaluation
that justifies it.

100 trees rather than 300: the difference is 0.929 vs 0.931 ROC-AUC while the
artifact goes from 2.9 MB to 8.6 MB. Not a trade worth making for 0.002.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

from . import bbb, metrics, provenance, splits
from .featurizers import FP_BITS, FP_RADIUS, fingerprint_matrix

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODEL_DIR / "bbb_rf.joblib"
METADATA_PATH = MODEL_DIR / "bbb_rf.json"

N_ESTIMATORS = 100


def main(seed: int = provenance.DEFAULT_SEED) -> None:
    pairs = bbb.load_b3db()
    smiles = [s for s, _ in pairs]
    labels = np.array([y for _, y in pairs])

    # Scaffold split, so the reported numbers describe performance on
    # structurally novel compounds rather than memorised analogs.
    train_idx, test_idx = splits.scaffold_split(smiles, seed=seed)

    train_matrix, kept_train = fingerprint_matrix([smiles[i] for i in train_idx])
    model = RandomForestClassifier(
        n_estimators=N_ESTIMATORS,
        n_jobs=-1,
        random_state=seed,
        class_weight="balanced",
    )
    model.fit(train_matrix, labels[train_idx][kept_train])

    test_smiles = [smiles[i] for i in test_idx]
    test_matrix, kept_test = fingerprint_matrix(test_smiles)
    scores = np.zeros(len(test_smiles))
    scores[kept_test] = model.predict_proba(test_matrix)[:, 1]
    y_test = labels[test_idx]

    evaluation = metrics.evaluate(y_test, scores)
    ci = metrics.bootstrap_ci(
        y_test, scores, lambda t, s: float(roc_auc_score(t, s)), n_boot=500, seed=seed
    )

    # The baselines this had to beat to be worth shipping.
    tpsa = np.array([bbb.tpsa_score_of(s) for s in test_smiles])
    descriptor = np.array([bbb.descriptor_score_of(s) for s in test_smiles])

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH, compress=3)

    METADATA_PATH.write_text(
        json.dumps(
            {
                **provenance.run_metadata(seed=seed),
                "dataset": "B3DB classification",
                "source": bbb.B3DB_URL,
                "n_total": len(pairs),
                "n_train": len(train_idx),
                "n_test": len(test_idx),
                "test_positive_rate": float(y_test.mean()),
                "split": "Bemis-Murcko scaffold",
                "featurisation": {"type": "ECFP4", "radius": FP_RADIUS, "bits": FP_BITS},
                "n_estimators": N_ESTIMATORS,
                "roc_auc": evaluation["roc_auc"],
                "roc_auc_ci": list(ci),
                "pr_auc": evaluation["pr_auc"],
                "baselines": {
                    "tpsa_only": float(roc_auc_score(y_test, tpsa)),
                    "hand_tuned_descriptor_score": float(roc_auc_score(y_test, descriptor)),
                },
            },
            indent=2,
        )
    )

    print(f"model    -> {MODEL_PATH} ({MODEL_PATH.stat().st_size / 1e6:.1f} MB)")
    print(f"metadata -> {METADATA_PATH}")
    print(f"ROC-AUC {evaluation['roc_auc']:.3f} {tuple(round(c, 3) for c in ci)}")
    print(f"  beats tpsa_only        {roc_auc_score(y_test, tpsa):.3f}")
    print(f"  beats descriptor score {roc_auc_score(y_test, descriptor):.3f}")


if __name__ == "__main__":
    main()
