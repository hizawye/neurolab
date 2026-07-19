"""Contract tests for module surfaces.

Every other test in this suite monkeypatches the ChEMBL client, so all of them
pass even when the functions being patched do not exist. That is exactly how a
truncating edit removed `search_targets`, `targets_by_uniprot`, and
`activities_for_target` from the client and still shipped green: the mocks
replaced attributes on a module that no longer had them, and only a real
request revealed it.

These tests touch no network. They assert the callables the request path
depends on are actually present and wired to each other.
"""

import inspect

from backend.modules import chembl_client, ligand_finder, predictor, target_resolver


def test_chembl_client_exposes_request_path_functions():
    for name in ("search_targets", "targets_by_uniprot", "activities_for_target"):
        assert callable(getattr(chembl_client, name, None)), f"chembl_client.{name} is missing"


def test_target_resolver_calls_only_functions_the_client_defines():
    """Catches a resolver referencing a client function that was removed."""
    source = inspect.getsource(target_resolver)
    for name in ("search_targets", "targets_by_uniprot"):
        if f"chembl_client.{name}" in source:
            assert hasattr(chembl_client, name), f"resolver calls missing chembl_client.{name}"


def test_ligand_finder_calls_only_functions_the_client_defines():
    source = inspect.getsource(ligand_finder)
    if "chembl_client.activities_for_target" in source:
        assert hasattr(chembl_client, "activities_for_target")


def test_predictor_featurisation_matches_the_benchmark():
    """A prediction is only covered by the benchmark if the features match.

    If these drift apart, the validation numbers surfaced to users describe a
    different method than the one actually scoring their compounds.
    """
    from backend.science import featurizers

    assert predictor.FP_RADIUS == featurizers.FP_RADIUS
    assert predictor.FP_BITS == featurizers.FP_BITS


def test_predictor_and_benchmark_agree_on_a_concrete_similarity():
    """Same pair of molecules, same number, through both code paths."""
    from rdkit import DataStructs

    from backend.science.featurizers import ecfp4

    a = "OC1(CCN(CCCC(=O)c2ccc(F)cc2)CC1)c1ccc(Cl)cc1"
    b = "CN1C(=O)CN=C(c2ccccc2)c2cc(Cl)ccc21"

    via_science = DataStructs.TanimotoSimilarity(ecfp4(a), ecfp4(b))
    via_predictor = predictor.predict(a, [b])["similarity"]

    assert round(via_science, 4) == via_predictor
