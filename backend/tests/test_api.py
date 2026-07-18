from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import (
    ActivityEvidence,
    DescriptorSet,
    LigandResult,
    ResolvedTarget,
    TargetResult,
)

client = TestClient(app)


def _resolved_target():
    return ResolvedTarget(
        chembl_id="CHEMBL217",
        pref_name="D(2) dopamine receptor",
        organism="Homo sapiens",
        target_type="SINGLE PROTEIN",
        uniprot_accession="P14416",
        source_url="https://www.ebi.ac.uk/chembl/target_report_card/CHEMBL217/",
    )


def _ligand_pair(chembl_id="CHEMBL1201", pchembl=9.5):
    return (
        LigandResult(
            chembl_id=chembl_id,
            name="HALOPERIDOL",
            smiles="OC1(CCN(CCCC(=O)c2ccc(F)cc2)CC1)c1ccc(Cl)cc1",
            source_url=f"https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}/",
        ),
        ActivityEvidence(pchembl_value=pchembl, standard_type="Ki", measurement_count=4),
    )


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_target_search(monkeypatch):
    from backend.api import targets

    monkeypatch.setattr(
        targets.target_selector,
        "find_targets",
        lambda query, limit=10: [
            TargetResult(rcsb_id="2V5Z", source_url="https://www.rcsb.org/structure/2V5Z")
        ],
    )

    response = client.get("/targets/search", params={"query": "MAO-B", "limit": 1})

    assert response.status_code == 200
    assert response.json()[0]["rcsb_id"] == "2V5Z"


def test_ligand_search_returns_measured_binders(monkeypatch):
    from backend.api import ligands

    monkeypatch.setattr(ligands.target_resolver, "resolve_by_name", lambda query: _resolved_target())
    monkeypatch.setattr(
        ligands.ligand_finder,
        "find_for_target",
        lambda target, limit=8: [_ligand_pair()],
    )

    response = client.get("/ligands/search", params={"query": "dopamine D2 receptor"})

    assert response.status_code == 200
    row = response.json()[0]
    assert row["ligand"]["chembl_id"] == "CHEMBL1201"
    assert row["activity"]["pchembl_value"] == 9.5
    assert row["descriptors"]["molecular_weight"] > 0


def test_ligand_search_404s_on_unresolvable_target(monkeypatch):
    from backend.api import ligands

    monkeypatch.setattr(ligands.target_resolver, "resolve_by_name", lambda query: None)

    response = client.get("/ligands/search", params={"query": "not a protein"})

    assert response.status_code == 404


def test_lite_workflow_ranks_by_measured_affinity(monkeypatch):
    from backend.modules import workflow as workflow_module
    from backend.api import workflows

    runner = workflows.workflow_runner

    monkeypatch.setattr(
        runner.target_selector,
        "find_targets",
        lambda query, limit=10: [
            TargetResult(rcsb_id="7CMU", source_url="https://www.rcsb.org/structure/7CMU")
        ],
    )
    monkeypatch.setattr(workflow_module.target_resolver, "resolve_by_name", lambda query: _resolved_target())
    # Returned weakest-first so the sort has something to do.
    monkeypatch.setattr(
        runner.ligand_finder,
        "find_for_target",
        lambda target, limit=8: [
            _ligand_pair("CHEMBL_WEAK", 6.1),
            _ligand_pair("CHEMBL_STRONG", 10.2),
        ],
    )

    response = client.post("/workflows/run-lite", json={"query": "dopamine D2 receptor", "limit": 3})

    assert response.status_code == 200
    body = response.json()
    assert body["resolved_target"]["chembl_id"] == "CHEMBL217"
    assert body["targets"][0]["rcsb_id"] == "7CMU"
    assert [item["ligand"]["chembl_id"] for item in body["ligands"]] == [
        "CHEMBL_STRONG",
        "CHEMBL_WEAK",
    ]


def test_lite_workflow_warns_when_target_unresolvable(monkeypatch):
    from backend.modules import workflow as workflow_module
    from backend.api import workflows

    runner = workflows.workflow_runner

    monkeypatch.setattr(runner.target_selector, "find_targets", lambda query, limit=10: [])
    monkeypatch.setattr(workflow_module.target_resolver, "resolve_by_name", lambda query: None)

    response = client.post("/workflows/run-lite", json={"query": "serotonin receptor", "limit": 3})

    assert response.status_code == 200
    body = response.json()
    assert body["ligands"] == []
    # The silent-empty-result case must surface a reason.
    assert any(w["stage"] == "target_resolution" for w in body["warnings"])
