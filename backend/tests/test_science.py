"""Tests for the validation harness.

The harness is what makes every downstream scientific claim believable, so its
own correctness has to be checked directly. The leakage test at the bottom is
the important one: it catches split bugs that every other test here would pass.
"""

import numpy as np
import pytest

from backend.science import datasets, metrics, models, splits

# A few real, structurally varied drugs.
SMILES = {
    "haloperidol": "OC1(CCN(CCCC(=O)c2ccc(F)cc2)CC1)c1ccc(Cl)cc1",
    "diazepam": "CN1C(=O)CN=C(c2ccccc2)c2cc(Cl)ccc21",
    "caffeine": "CN1C=NC2=C1C(=O)N(C)C(=O)N2C",
    "aspirin": "CC(=O)Oc1ccccc1C(=O)O",
    "selegiline": "CC(Cc1ccccc1)N(C)CC#C",
    "ethanol": "CCO",
}


# --- metrics ---------------------------------------------------------------


def test_enrichment_factor_perfect_and_worst():
    # 100 compounds, 10 actives. EF ceiling is 1/active_ratio = 10, not 1/fraction,
    # because the top 5% cannot hold more actives than exist.
    y = np.array([1] * 10 + [0] * 90)
    best = np.arange(100)[::-1].astype(float)

    assert metrics.enrichment_factor(y, best, 0.05) == pytest.approx(10.0)
    assert metrics.enrichment_factor(y, best[::-1], 0.05) == pytest.approx(0.0)


def test_enrichment_factor_random_is_about_one():
    y = np.array([1] * 100 + [0] * 900)
    rng = np.random.default_rng(0)
    values = [metrics.enrichment_factor(y, rng.random(1000), 0.05) for _ in range(200)]
    assert np.mean(values) == pytest.approx(1.0, abs=0.15)


def test_bedroc_bounds():
    y = np.array([1] * 10 + [0] * 90)
    best = np.arange(100)[::-1].astype(float)

    assert metrics.bedroc(y, best) == pytest.approx(1.0, abs=1e-6)
    assert metrics.bedroc(y, best[::-1]) == pytest.approx(0.0, abs=1e-6)


def test_bedroc_random_matches_closed_form():
    """Random BEDROC is ratio-dependent, not the widely-repeated 0.5."""
    for ratio, n in ((0.1, 1000), (0.005, 2000)):
        n_active = max(1, int(n * ratio))
        y = np.array([1] * n_active + [0] * (n - n_active))
        rng = np.random.default_rng(1)
        empirical = np.nanmean([metrics.bedroc(y, rng.random(n)) for _ in range(200)])
        assert empirical == pytest.approx(metrics.random_bedroc(ratio), abs=0.02)

    # Guard the specific claim that 0.5 is wrong.
    assert metrics.random_bedroc(0.1) < 0.2


def test_evaluate_handles_single_class():
    values = metrics.evaluate(np.array([1, 1, 1]), np.array([0.1, 0.2, 0.3]))
    assert all(np.isnan(v) for v in values.values())


# --- splits ----------------------------------------------------------------


def test_scaffold_split_has_no_scaffold_overlap():
    smiles = list(SMILES.values()) * 6
    train, test = splits.scaffold_split(smiles)

    train_scaffolds = {splits.scaffold_of(smiles[i]) for i in train}
    test_scaffolds = {splits.scaffold_of(smiles[i]) for i in test}
    assert not (train_scaffolds & test_scaffolds)


def test_scaffold_split_is_a_partition():
    smiles = list(SMILES.values()) * 6
    train, test = splits.scaffold_split(smiles)

    assert sorted(train + test) == list(range(len(smiles)))
    assert not set(train) & set(test)


def test_scaffold_split_is_deterministic():
    smiles = list(SMILES.values()) * 6
    assert splits.scaffold_split(smiles) == splits.scaffold_split(smiles)


def test_acyclic_molecules_share_one_bucket():
    """Ethanol has no ring system; it must not become its own scaffold group."""
    assert splits.scaffold_of("CCO") == "__acyclic__"
    assert splits.scaffold_of("CCCC") == "__acyclic__"


# --- datasets --------------------------------------------------------------


def test_thresholds_discard_the_ambiguous_band():
    """Compounds between 5 and 7 carry labels no better than noise."""
    assert datasets.INACTIVE_THRESHOLD == 5.0
    assert datasets.ACTIVE_THRESHOLD == 7.0

    records = [
        {"molecule_chembl_id": "A", "canonical_smiles": SMILES["caffeine"], "pchembl_value": 8.5},
        {"molecule_chembl_id": "B", "canonical_smiles": SMILES["aspirin"], "pchembl_value": 6.0},
        {"molecule_chembl_id": "C", "canonical_smiles": SMILES["diazepam"], "pchembl_value": 4.0},
    ]
    aggregated = datasets._aggregate_measured(records)
    labelled = {
        key: value
        for key, (_, value) in aggregated.items()
        if value >= 7.0 or value <= 5.0
    }
    assert set(labelled) == {"A", "C"}


def test_aggregate_uses_median_not_max():
    records = [
        {"molecule_chembl_id": "X", "canonical_smiles": SMILES["caffeine"], "pchembl_value": v}
        for v in (5.0, 6.0, 10.0)
    ]
    _, value = datasets._aggregate_measured(records)["X"]
    assert value == pytest.approx(6.0)


def test_invalid_smiles_are_dropped():
    records = [
        {"molecule_chembl_id": "BAD", "canonical_smiles": "not-a-smiles", "pchembl_value": 9.0}
    ]
    assert datasets._aggregate_measured(records) == {}


def test_decoys_are_property_matched_and_dissimilar():
    from backend.science.featurizers import ecfp4, tanimoto

    actives = [
        datasets.Compound(chembl_id="A1", smiles=SMILES["haloperidol"], label=1),
        datasets.Compound(chembl_id="A2", smiles=SMILES["diazepam"], label=1),
    ]
    pool = [(f"D{i}", s) for i, s in enumerate(SMILES.values())] * 40
    pool = [(f"{mid}_{i}", smi) for i, (mid, smi) in enumerate(pool)]

    built = datasets.build_decoy_dataset(actives, pool, active_fraction=0.05)
    decoys = [c for c in built.compounds if c.source == "decoy"]

    active_fps = [ecfp4(a.smiles) for a in actives]
    for decoy in decoys:
        fingerprint = ecfp4(decoy.smiles)
        assert max(tanimoto(fingerprint, fp) for fp in active_fps) < datasets.DECOY_MAX_TANIMOTO
        assert decoy.label == 0


# --- the leakage check -----------------------------------------------------


def test_shuffled_labels_score_near_random():
    """The sanity check that must fail.

    Train on labels that carry no information. Any method scoring materially
    above chance means information is leaking across the split — a class of bug
    every other test in this file would happily pass.
    """
    rng = np.random.default_rng(7)
    smiles = list(SMILES.values()) * 40
    labels = rng.integers(0, 2, len(smiles))

    train, test = splits.scaffold_split(smiles)
    y_train, y_test = labels[train], labels[test]
    if len(set(y_test.tolist())) < 2:
        pytest.skip("degenerate test split for this fixture")

    model = models.RandomForestModel(seed=7)
    model.fit([smiles[i] for i in train], y_train)
    scores = model.score([smiles[i] for i in test])

    roc = metrics.evaluate(y_test, scores)["roc_auc"]
    assert 0.30 < roc < 0.70, f"possible leakage: ROC-AUC {roc:.3f} on shuffled labels"
