from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import DescriptorSet, LigandResult, TargetResult

client = TestClient(app)


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


def test_ligand_search(monkeypatch):
    from backend.api import ligands

    monkeypatch.setattr(
        ligands.ligand_finder,
        "find_ligands",
        lambda query, limit=8: [
            LigandResult(
                cid=26757,
                name="selegiline",
                smiles="C#CCN(C)C(C)Cc1ccccc1",
                source_url="https://pubchem.ncbi.nlm.nih.gov/compound/26757",
            )
        ],
    )

    response = client.get("/ligands/search", params={"query": "selegiline"})

    assert response.status_code == 200
    assert response.json()[0]["cid"] == 26757


def test_lite_workflow(monkeypatch):
    from backend.api import workflows

    def fake_run(request):
        return {
            "query": request.query,
            "ligand_query": request.ligand_query or request.query,
            "targets": [
                {"rcsb_id": "2V5Z", "source_url": "https://www.rcsb.org/structure/2V5Z"}
            ],
            "ligands": [
                {
                    "ligand": {
                        "cid": 26757,
                        "name": "selegiline",
                        "smiles": "C#CCN(C)C(C)Cc1ccccc1",
                        "source_url": "https://pubchem.ncbi.nlm.nih.gov/compound/26757",
                    },
                    "descriptors": DescriptorSet(
                        molecular_weight=187.29,
                        logp=2.9,
                        tpsa=3.24,
                        h_bond_donors=0,
                        h_bond_acceptors=1,
                    ),
                    "score": 108,
                    "notes": ["TPSA is favorable for BBB-oriented screening"],
                }
            ],
            "warnings": [],
        }

    monkeypatch.setattr(workflows.workflow_runner, "run", fake_run)

    response = client.post("/workflows/run-lite", json={"query": "MAO-B inhibitor", "limit": 3})

    assert response.status_code == 200
    assert response.json()["targets"][0]["rcsb_id"] == "2V5Z"
    assert response.json()["ligands"][0]["ligand"]["name"] == "selegiline"
