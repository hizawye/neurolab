"""Tests for the BBB penetration model.

The discrimination test below is the one that matters. The model replaced a
hand-tuned score that was shipped for months without anyone checking whether it
predicted BBB penetration at all — it did not; it lost to TPSA alone. These
assert the replacement actually separates drugs that reach the brain from those
that do not.
"""

import pytest

from backend.modules import bbb_model

# Well-established CNS-penetrant drugs.
CNS_PENETRANT = {
    "caffeine": "CN1C=NC2=C1C(=O)N(C)C(=O)N2C",
    "diazepam": "CN1C(=O)CN=C(c2ccccc2)c2cc(Cl)ccc21",
    "haloperidol": "OC1(CCN(CCCC(=O)c2ccc(F)cc2)CC1)c1ccc(Cl)cc1",
    "nicotine": "CN1CCC[C@H]1c1cccnc1",
}

# Peripherally restricted: large, polar, or actively excluded from the CNS.
NON_PENETRANT = {
    "sucrose": "OCC1OC(OC2(CO)OC(CO)C(O)C2O)C(O)C(O)C1O",
    "atenolol": "CC(C)NCC(O)COc1ccc(CC(N)=O)cc1",
    "penicillin_g": "CC1(C)SC2C(NC(=O)Cc3ccccc3)C(=O)N2C1C(=O)O",
    "loratadine": "CCOC(=O)N1CCC(=C2c3ccc(Cl)cc3CCc3cccnc32)CC1",
}

pytestmark = pytest.mark.skipif(
    not bbb_model.available(), reason="BBB model artifact not trained"
)


def test_separates_cns_drugs_from_peripherally_restricted():
    penetrant = bbb_model.predict_batch(list(CNS_PENETRANT.values()))
    restricted = bbb_model.predict_batch(list(NON_PENETRANT.values()))

    mean_penetrant = sum(penetrant) / len(penetrant)
    mean_restricted = sum(restricted) / len(restricted)

    assert mean_penetrant > mean_restricted, (
        f"CNS drugs mean {mean_penetrant:.3f} not above "
        f"peripherally restricted mean {mean_restricted:.3f}"
    )


def test_sucrose_is_not_predicted_to_cross():
    """A highly polar sugar has no business scoring as brain-penetrant."""
    (probability,) = bbb_model.predict_batch([NON_PENETRANT["sucrose"]])
    assert probability < 0.5


def test_caffeine_is_predicted_to_cross():
    """The compound the old descriptor score ranked below benzene and hexane."""
    (probability,) = bbb_model.predict_batch([CNS_PENETRANT["caffeine"]])
    assert probability > 0.5


def test_probabilities_are_bounded():
    values = bbb_model.predict_batch(list(CNS_PENETRANT.values()))
    assert all(0.0 <= v <= 1.0 for v in values)


def test_unparseable_smiles_yields_none_without_shifting_others():
    values = bbb_model.predict_batch(
        [CNS_PENETRANT["caffeine"], "not-a-smiles", NON_PENETRANT["sucrose"]]
    )
    assert values[1] is None
    assert values[0] is not None and values[2] is not None
    # Position must be preserved, or scores get attached to the wrong compound.
    assert values[0] > values[2]


def test_validation_record_reports_what_it_beat():
    """A prediction must be traceable to the evaluation justifying it."""
    record = bbb_model.validation_record()

    assert record["roc_auc"] > 0.85
    assert "tpsa_only" in record["beats"]
    assert "hand_tuned_descriptor_score" in record["beats"]
    # The model must actually beat what it replaced.
    assert record["roc_auc"] > record["beats"]["hand_tuned_descriptor_score"]
    assert record["roc_auc"] > record["beats"]["tpsa_only"]
