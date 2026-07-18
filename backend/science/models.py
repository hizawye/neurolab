"""Scoring methods under test, and the baselines they must beat.

Every method exposes the same interface: fit on training compounds, then emit a
score per test compound where higher means more likely active. That uniformity
is what lets the benchmark compare a Random Forest against plain similarity
search on identical footing.

The similarity baseline is the one that matters. A large share of published
QSAR models never beat it, and reporting a win over random alone is the most
common way this kind of work misleads.
"""

from __future__ import annotations

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC

from ..modules.ranker import score_descriptors
from ..modules.descriptors import calculate_descriptors
from . import provenance
from .featurizers import ecfp4, fingerprint_matrix, tanimoto


class ScoringMethod:
    name = "base"
    is_baseline = False

    def fit(self, smiles: list[str], labels: np.ndarray) -> None:
        raise NotImplementedError

    def score(self, smiles: list[str]) -> np.ndarray:
        raise NotImplementedError


class RandomBaseline(ScoringMethod):
    """Floor. Anything that fails to beat this is broken."""

    name = "random"
    is_baseline = True

    def __init__(self, seed: int = provenance.DEFAULT_SEED):
        self._rng = np.random.default_rng(seed)

    def fit(self, smiles, labels):
        return None

    def score(self, smiles):
        return self._rng.random(len(smiles))


class DescriptorScoreBaseline(ScoringMethod):
    """The platform's current ranking function, as shipped.

    Included to measure exactly how much the descriptor score does or does not
    contribute. It is target-independent by construction: it never sees the
    training labels, so it cannot know anything about this particular protein.
    """

    name = "descriptor_score"
    is_baseline = True

    def fit(self, smiles, labels):
        return None

    def score(self, smiles):
        scores = []
        for entry in smiles:
            descriptors = calculate_descriptors(entry)
            if descriptors is None:
                scores.append(0.0)
                continue
            value, _ = score_descriptors(descriptors)
            scores.append(value)
        return np.asarray(scores, dtype=float)


class SimilarityBaseline(ScoringMethod):
    """Max ECFP4 Tanimoto to any training active.

    The honest bar for ligand-based virtual screening: no model, no fitting,
    just "does this look like something already known to bind?"
    """

    name = "max_tanimoto"
    is_baseline = True

    def __init__(self):
        self._active_fps = []

    def fit(self, smiles, labels):
        labels = np.asarray(labels)
        self._active_fps = [
            fp
            for fp in (ecfp4(s) for s, y in zip(smiles, labels) if y == 1)
            if fp is not None
        ]

    def score(self, smiles):
        scores = []
        for entry in smiles:
            fingerprint = ecfp4(entry)
            if fingerprint is None or not self._active_fps:
                scores.append(0.0)
                continue
            scores.append(max(tanimoto(fingerprint, fp) for fp in self._active_fps))
        return np.asarray(scores, dtype=float)


class _SklearnModel(ScoringMethod):
    """Shared plumbing for fingerprint-based classifiers."""

    def __init__(self, estimator):
        self._estimator = estimator
        self._fitted = False

    def fit(self, smiles, labels):
        matrix, kept = fingerprint_matrix(smiles)
        labels = np.asarray(labels)[kept]
        if len(set(labels.tolist())) < 2:
            self._fitted = False
            return
        self._estimator.fit(matrix, labels)
        self._fitted = True

    def score(self, smiles):
        scores = np.zeros(len(smiles), dtype=float)
        if not self._fitted:
            return scores
        matrix, kept = fingerprint_matrix(smiles)
        if not kept:
            return scores
        # Unparseable molecules keep their 0.0, ranking last.
        scores[kept] = self._estimator.predict_proba(matrix)[:, 1]
        return scores


class RandomForestModel(_SklearnModel):
    name = "random_forest"

    def __init__(self, seed: int = provenance.DEFAULT_SEED):
        super().__init__(
            RandomForestClassifier(
                n_estimators=300,
                n_jobs=-1,
                random_state=seed,
                class_weight="balanced",
            )
        )


class SVMModel(_SklearnModel):
    """Linear SVM over ECFP4.

    Linear rather than RBF for two reasons. An RBF kernel is O(n^2)-O(n^3) and
    becomes intractable on Track B, where the decoy padding pushes the training
    set past 15k compounds on CPU. And linear kernels are the conventional
    choice for high-dimensional sparse binary fingerprints, where the data is
    close to linearly separable already, so little is given up.

    Wrapped in calibration because LinearSVC emits decision-function margins,
    and the benchmark ranks on probabilities.
    """

    name = "svm_linear"

    def __init__(self, seed: int = provenance.DEFAULT_SEED):
        super().__init__(
            CalibratedClassifierCV(
                LinearSVC(random_state=seed, class_weight="balanced", dual="auto"),
                ensemble=False,
            )
        )


def all_methods(seed: int = provenance.DEFAULT_SEED) -> list[ScoringMethod]:
    """Baselines first, so reports read bar-then-candidates."""
    return [
        RandomBaseline(seed),
        DescriptorScoreBaseline(),
        SimilarityBaseline(),
        RandomForestModel(seed),
        SVMModel(seed),
    ]
