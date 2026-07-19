"""Tests for the screening endpoint and the validated predictor."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.modules import predictor
from backend.schemas import ActivityEvidence, LigandResult, ResolvedTarget

client = TestClient(app)

HALOPERIDOL = "OC1(CCN(CCCC(=O)c2ccc(F)cc2)CC1)c1ccc(Cl)cc1"
# Same butyrophenone class as haloperidol - a true D2 analog.
DROPERIDOL = "O=C1NC=NN1c1ccc(cc1)C1CCN(CCCC(=O)c2ccc(F)cc2)CC1"
ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"
ETHANOL = "CCO"


def _target():
    return ResolvedTarget(
        chembl_id="CHEMBL217",
        pref_name="D(2) dopamine receptor",
        organism="Homo sapiens",
        source_url="https://www.ebi.ac.uk/chembl/target_report_card/CHEMBL217/",
    )


def _pairs():
    return [
        (
            LigandResult(
                chembl_id="CHEMBL54",
                name="HALOPERIDOL",
                smiles=HALOPERIDOL,
                source_url="https://www.ebi.ac.uk/chembl/compound_report_card/CHEMBL54/",
            ),
            ActivityEvidence(pchembl_value=9.2, standard_type="Ki", measurement_count=6),
        )
    ]


# --- predictor ------------------------------------------------------------


def test_analog_scores_far_above_unrelated_compound():
    """The core claim the endpoint makes. If this inverts, nothing else matters."""
    analog = predictor.predict(DROPERIDOL, [HALOPERIDOL])
    unrelated = predictor.predict(ASPIRIN, [HALOPERIDOL])

    assert analog["similarity"] > unrelated["similarity"]
    assert analog["similarity"] > 0.4
    assert unrelated["similarity"] < 0.2


def test_identical_compound_scores_one():
    result = predictor.predict(HALOPERIDOL, [HALOPERIDOL])
    assert result["similarity"] == pytest.approx(1.0)


def test_prediction_reports_which_reference_matched():
    result = predictor.predict(DROPERIDOL, [ETHANOL, HALOPERIDOL])
    assert result["nearest_active_smiles"] == HALOPERIDOL
    assert result["n_references"] == 2


def test_unparseable_query_returns_none():
    assert predictor.predict("not-a-smiles", [HALOPERIDOL]) is None


def test_no_usable_references_returns_none():
    assert predictor.predict(HALOPERIDOL, ["not-a-smiles"]) is None


# --- endpoint -------------------------------------------------------------


def test_screen_ranks_by_predicted_similarity(monkeypatch):
    from backend.api import screen

    monkeypatch.setattr(screen.target_resolver, "resolve_by_name", lambda q: _target())
    monkeypatch.setattr(screen.ligand_finder, "find_for_target", lambda t, limit=100: _pairs())

    response = client.post(
        "/screen",
        json={"target_query": "dopamine D2 receptor", "smiles": [ASPIRIN, DROPERIDOL]},
    )

    assert response.status_code == 200
    body = response.json()
    # The analog must outrank the unrelated compound.
    assert body["results"][0]["query_smiles"] == DROPERIDOL
    assert body["results"][0]["predicted"]["similarity"] > body["results"][1]["predicted"]["similarity"]


def test_screen_surfaces_validation_record(monkeypatch):
    """A score must never be returned without its track record."""
    from backend.api import screen

    monkeypatch.setattr(screen.target_resolver, "resolve_by_name", lambda q: _target())
    monkeypatch.setattr(screen.ligand_finder, "find_for_target", lambda t, limit=100: _pairs())

    body = client.post(
        "/screen", json={"target_query": "dopamine D2 receptor", "smiles": [DROPERIDOL]}
    ).json()

    assert "bedroc_range" in body["method"]
    assert "caveat" in body["method"]
    assert body["method"]["n_reference_actives"] == 1


def test_measured_data_is_not_presented_as_prediction(monkeypatch):
    """A compound already in the reference set has real data; say so."""
    from backend.api import screen

    monkeypatch.setattr(screen.target_resolver, "resolve_by_name", lambda q: _target())
    monkeypatch.setattr(screen.ligand_finder, "find_for_target", lambda t, limit=100: _pairs())

    body = client.post(
        "/screen", json={"target_query": "dopamine D2 receptor", "smiles": [HALOPERIDOL]}
    ).json()

    row = body["results"][0]
    assert row["measured"] is not None
    assert row["measured"]["pchembl_value"] == 9.2


def test_measured_data_found_via_non_canonical_smiles(monkeypatch):
    """The same molecule has many valid SMILES spellings.

    A user typing a non-canonical form of a compound ChEMBL has measured must
    still get its measurement, not a prediction standing in for one.
    """
    from backend.api import screen

    monkeypatch.setattr(screen.target_resolver, "resolve_by_name", lambda q: _target())
    monkeypatch.setattr(screen.ligand_finder, "find_for_target", lambda t, limit=100: _pairs())

    # Same molecule as HALOPERIDOL, written differently.
    rewritten = "C1CN(CCC1(c1ccc(Cl)cc1)O)CCCC(=O)c1ccc(F)cc1"
    assert rewritten != HALOPERIDOL

    body = client.post(
        "/screen", json={"target_query": "dopamine D2 receptor", "smiles": [rewritten]}
    ).json()

    assert body["results"][0]["measured"] is not None
    assert body["results"][0]["measured"]["pchembl_value"] == 9.2


def test_screen_404s_on_unresolvable_target(monkeypatch):
    from backend.api import screen

    monkeypatch.setattr(screen.target_resolver, "resolve_by_name", lambda q: None)

    response = client.post("/screen", json={"target_query": "nonsense", "smiles": [ASPIRIN]})
    assert response.status_code == 404


def test_screen_422s_when_target_has_no_reference_actives(monkeypatch):
    from backend.api import screen

    monkeypatch.setattr(screen.target_resolver, "resolve_by_name", lambda q: _target())
    monkeypatch.setattr(screen.ligand_finder, "find_for_target", lambda t, limit=100: [])

    response = client.post("/screen", json={"target_query": "obscure", "smiles": [ASPIRIN]})
    assert response.status_code == 422


def test_unparseable_smiles_warns_but_does_not_fail_the_batch(monkeypatch):
    from backend.api import screen

    monkeypatch.setattr(screen.target_resolver, "resolve_by_name", lambda q: _target())
    monkeypatch.setattr(screen.ligand_finder, "find_for_target", lambda t, limit=100: _pairs())

    body = client.post(
        "/screen",
        json={"target_query": "dopamine D2 receptor", "smiles": ["not-a-smiles", DROPERIDOL]},
    ).json()

    assert any(w["stage"] == "parse" for w in body["warnings"])
    assert len(body["results"]) == 2
