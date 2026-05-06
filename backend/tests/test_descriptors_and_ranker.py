from backend.modules.descriptors import calculate_descriptors
from backend.modules.ranker import score_descriptors


def test_calculates_descriptors_for_valid_smiles():
    descriptors = calculate_descriptors("CN1CCC[C@H]1c2cccnc2")

    assert descriptors is not None
    assert descriptors.molecular_weight > 100
    assert descriptors.tpsa >= 0


def test_rejects_invalid_smiles():
    assert calculate_descriptors("not-a-smiles") is None


def test_ranker_rewards_bbb_friendly_tpsa():
    descriptors = calculate_descriptors("CN1CCC[C@H]1c2cccnc2")
    assert descriptors is not None

    score, notes = score_descriptors(descriptors)

    assert score > 90
    assert any("TPSA" in note for note in notes)
