"""Does the developability score actually predict blood-brain barrier penetration?

The score in `backend/modules/ranker.py` is presented to users as a
BBB-oriented read-out and has never been tested against measured brain
penetration. It is the last unvalidated number the platform displays, and it
sits in the screening table beside a rigorously benchmarked similarity score,
which lends it credibility it has not earned.

This measures it against B3DB, a curated set of compounds with experimentally
determined BBB outcomes. Same protocol as the activity benchmark: scaffold
split so the test set is structurally novel, bootstrap intervals, and honest
baselines the score has to beat to be worth keeping.

The comparison that decides it is `tpsa_only`. If a single descriptor does as
well as the whole hand-tuned scoring function, the function is adding nothing
but the appearance of sophistication.
"""

from __future__ import annotations

import csv
import io

import numpy as np
import requests

from ..modules.descriptors import calculate_descriptors
from ..modules.ranker import score_descriptors
from . import provenance

B3DB_URL = (
    "https://raw.githubusercontent.com/theochem/B3DB/main/B3DB/B3DB_classification.tsv"
)

# A widely cited rule of thumb: polar surface area below ~90 A^2 is compatible
# with passive BBB permeation. Used as the single-descriptor baseline.
TPSA_BBB_CUTOFF = 90.0


def load_b3db() -> list[tuple[str, int]]:
    """(SMILES, label) pairs; 1 = BBB+, 0 = BBB-. Cached like any other source."""
    key = provenance.cache_key("b3db", {"url": B3DB_URL})
    cached = provenance.cache_read(key)
    if cached is None:
        if provenance.offline():
            raise RuntimeError("Offline mode: B3DB not in cache.")
        response = requests.get(B3DB_URL, timeout=120)
        response.raise_for_status()
        cached = response.text
        provenance.cache_write(key, cached)

    rows = csv.DictReader(io.StringIO(cached), delimiter="\t")
    out = []
    for row in rows:
        smiles = (row.get("SMILES") or "").strip()
        label = (row.get("BBB+/BBB-") or "").strip()
        if not smiles or label not in {"BBB+", "BBB-"}:
            continue
        out.append((smiles, 1 if label == "BBB+" else 0))
    return out


def descriptor_score_of(smiles: str) -> float:
    """The shipped developability score. Higher is meant to mean more BBB-friendly."""
    descriptors = calculate_descriptors(smiles)
    if descriptors is None:
        return 0.0
    score, _ = score_descriptors(descriptors)
    return score


def tpsa_score_of(smiles: str) -> float:
    """Single-descriptor baseline: lower TPSA scores higher."""
    descriptors = calculate_descriptors(smiles)
    if descriptors is None:
        return 0.0
    return -float(descriptors.tpsa)


def logp_score_of(smiles: str) -> float:
    """Second single-descriptor baseline; lipophilicity also tracks permeation."""
    descriptors = calculate_descriptors(smiles)
    if descriptors is None:
        return 0.0
    return float(descriptors.logp)


def run(seed: int = provenance.DEFAULT_SEED, n_boot: int = 500) -> dict:
    from . import metrics, splits
    from .featurizers import fingerprint_matrix

    pairs = load_b3db()
    smiles = [s for s, _ in pairs]
    labels = np.array([y for _, y in pairs])

    train_idx, test_idx = splits.scaffold_split(smiles, seed=seed)
    test_smiles = [smiles[i] for i in test_idx]
    y_test = labels[test_idx]

    results = {}

    rng = np.random.default_rng(seed)
    scored = {
        "random": rng.random(len(test_smiles)),
        "tpsa_only": np.array([tpsa_score_of(s) for s in test_smiles]),
        "logp_only": np.array([logp_score_of(s) for s in test_smiles]),
        "descriptor_score": np.array([descriptor_score_of(s) for s in test_smiles]),
    }

    # Random forest on ECFP4, as a reference ceiling for what this data supports.
    from sklearn.ensemble import RandomForestClassifier

    train_matrix, kept_train = fingerprint_matrix([smiles[i] for i in train_idx])
    test_matrix, kept_test = fingerprint_matrix(test_smiles)
    forest = RandomForestClassifier(
        n_estimators=300, n_jobs=-1, random_state=seed, class_weight="balanced"
    )
    forest.fit(train_matrix, labels[train_idx][kept_train])
    rf_scores = np.zeros(len(test_smiles))
    rf_scores[kept_test] = forest.predict_proba(test_matrix)[:, 1]
    scored["random_forest_ecfp4"] = rf_scores

    for name, values in scored.items():
        block = metrics.evaluate(y_test, values)
        block["roc_auc_ci"] = metrics.bootstrap_ci(
            y_test,
            values,
            lambda t, s: float(__import__("sklearn.metrics", fromlist=["roc_auc_score"]).roc_auc_score(t, s)),
            n_boot=n_boot,
            seed=seed,
        )
        results[name] = block

    return {
        "metadata": provenance.run_metadata(seed=seed, dataset="B3DB", source=B3DB_URL),
        "n_total": len(pairs),
        "n_train": len(train_idx),
        "n_test": len(test_idx),
        "test_positive_rate": float(y_test.mean()),
        "results": results,
    }
