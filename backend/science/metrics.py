"""Virtual-screening metrics.

ROC-AUC is reported but is *not* the primary metric. It weights the whole
ranked list equally, while virtual screening only ever uses the top slice — a
model can post a respectable AUC while its top 100 is worthless. Enrichment
factor and BEDROC weight the top, so they lead.

sklearn provides ROC and PR; EF and BEDROC are implemented here because it
has neither.
"""

from __future__ import annotations

import math

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from . import provenance

BEDROC_ALPHA = 20.0


def _ranked_labels(y_true: np.ndarray, y_score: np.ndarray) -> np.ndarray:
    """Labels sorted by descending score (best-ranked first)."""
    order = np.argsort(-np.asarray(y_score, dtype=float), kind="stable")
    return np.asarray(y_true, dtype=int)[order]


def enrichment_factor(y_true, y_score, fraction: float) -> float:
    """How many times more actives the top `fraction` holds versus random.

    EF = 1.0 is random. The ceiling is 1/fraction, reached when the top slice
    is entirely actives.
    """
    labels = _ranked_labels(y_true, y_score)
    total = len(labels)
    n_active = int(labels.sum())
    if total == 0 or n_active == 0:
        return float("nan")

    cut = max(1, int(round(total * fraction)))
    hits = int(labels[:cut].sum())
    return (hits / cut) / (n_active / total)


def bedroc(y_true, y_score, alpha: float = BEDROC_ALPHA) -> float:
    """Boltzmann-enhanced discrimination of ROC (Truchon & Bayly, 2007).

    Exponentially weights early ranks. Bounded to [0, 1]; ~0.5 is random for
    the usual alpha. Corrects the ceiling/floor for the actual active ratio.
    """
    labels = _ranked_labels(y_true, y_score)
    total = len(labels)
    n_active = int(labels.sum())
    if total == 0 or n_active == 0 or n_active == total:
        return float("nan")

    ratio = n_active / total
    # Ranks are 1-indexed in the published formulation.
    ranks = np.nonzero(labels)[0] + 1
    exponent = float(np.sum(np.exp(-alpha * ranks / total)))

    random_sum = ratio * (1 - math.exp(-alpha)) / (math.exp(alpha / total) - 1)
    scaled = exponent / random_sum

    factor = ratio * math.sinh(alpha / 2) / (math.cosh(alpha / 2) - math.cosh(alpha / 2 - alpha * ratio))
    offset = 1 / (1 - math.exp(alpha * (1 - ratio)))
    return scaled * factor + offset


def random_bedroc(active_ratio: float, alpha: float = BEDROC_ALPHA) -> float:
    """BEDROC a random ranking scores at this active ratio.

    Not 0.5. That figure gets repeated but only holds in a narrow regime; the
    true random baseline depends on both alpha and the active ratio (0.116 at
    10% actives, 0.053 at 0.5%). Reported alongside every BEDROC so the number
    cannot be read against the wrong reference point.
    """
    if not 0 < active_ratio < 1:
        return float("nan")
    rie_max = (1 - math.exp(-alpha * active_ratio)) / (active_ratio * (1 - math.exp(-alpha)))
    rie_min = (1 - math.exp(alpha * active_ratio)) / (active_ratio * (1 - math.exp(alpha)))
    return (1 - rie_min) / (rie_max - rie_min)


def evaluate(y_true, y_score) -> dict:
    """Full metric block for one ranking."""
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)

    if len(set(y_true.tolist())) < 2:
        return {key: float("nan") for key in ("roc_auc", "pr_auc", "ef_1pct", "ef_5pct", "bedroc")}

    return {
        "roc_auc": float(roc_auc_score(y_true, y_score)),
        "pr_auc": float(average_precision_score(y_true, y_score)),
        "ef_1pct": enrichment_factor(y_true, y_score, 0.01),
        "ef_5pct": enrichment_factor(y_true, y_score, 0.05),
        "bedroc": bedroc(y_true, y_score),
    }


def bootstrap_ci(
    y_true,
    y_score,
    metric_fn,
    n_boot: int = 1000,
    seed: int = provenance.DEFAULT_SEED,
) -> tuple[float, float]:
    """Percentile bootstrap 95% CI.

    A difference between two methods that sits inside these bands is not a
    result, which is exactly what the pre-registered criteria require checking.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    rng = np.random.default_rng(seed)

    samples = []
    n = len(y_true)
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        if len(set(y_true[idx].tolist())) < 2:
            continue
        value = metric_fn(y_true[idx], y_score[idx])
        if not math.isnan(value):
            samples.append(value)

    if not samples:
        return (float("nan"), float("nan"))
    return (float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5)))
