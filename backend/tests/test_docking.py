"""Tests for the docking module.

The structure-splitting tests matter most. Every docking result depends on
having built the right receptor, and the failure is silent: strip a cofactor
and you open a cavity that does not exist, keep a lipid and you may dock into
detergent. Both produce confident numbers about the wrong system.
"""

import pytest

from backend.science import docking

# Minimal PDB: two protein atoms, an FAD cofactor atom, a water, a cholesterol
# atom, and a drug-like HET group.
PDB = "\n".join(
    [
        "ATOM      1  N   ALA A   1      10.000  10.000  10.000  1.00 20.00           N",
        "ATOM      2  CA  ALA A   1      11.000  10.000  10.000  1.00 20.00           C",
        "HETATM    3  N1  FAD A 501      12.000  10.000  10.000  1.00 20.00           N",
        "HETATM    4  O   HOH A 601      50.000  50.000  50.000  1.00 20.00           O",
        "HETATM    5  C1  CLR A 701      30.000  30.000  30.000  1.00 20.00           C",
        "ATOM      6  CB  ALA B   1      99.000  99.000  99.000  1.00 20.00           C",
    ]
    + [
        f"HETATM {7 + i:4d}  C{i:<2d} LIG A 801      "
        f"{20.0 + i:7.3f} 20.000  20.000  1.00 20.00           C"
        for i in range(12)
    ]
)


def test_cofactors_stay_in_the_receptor():
    """FAD sits against MAO-B's binding site; removing it invents a cavity."""
    receptor, _ = docking.split_structure(PDB, chain="A")
    assert "FAD" in receptor


def test_waters_are_removed():
    receptor, ligands = docking.split_structure(PDB, chain="A")
    assert "HOH" not in receptor
    assert not any("HOH" in text for text in ligands.values())


def test_membrane_components_are_not_mistaken_for_ligands():
    """A GPCR's biggest HET group is often a lipid, not the drug."""
    receptor, ligands = docking.split_structure(PDB, chain="A")
    assert "CLR" not in receptor
    assert not any(key.split(":")[1] == "CLR" for key in ligands)


def test_only_the_requested_chain_is_kept():
    """In a GPCR-G protein complex, picking the wrong chain docks into the G protein."""
    receptor, _ = docking.split_structure(PDB, chain="A")
    assert " B " not in receptor
    assert "99.000" not in receptor


def test_drug_like_het_is_offered_as_a_ligand():
    _, ligands = docking.split_structure(PDB, chain="A")
    assert any(key.split(":")[1] == "LIG" for key in ligands)


def test_fragments_below_the_size_floor_are_rejected():
    tiny = "\n".join(
        [
            "ATOM      1  N   ALA A   1      10.000  10.000  10.000  1.00 20.00           N",
            "HETATM    2  C1  XYZ A 801      20.000  20.000  20.000  1.00 20.00           C",
        ]
    )
    _, ligands = docking.split_structure(tiny, chain="A")
    assert ligands == {}


def test_conformer_is_generated_without_crystal_information():
    mol = docking.conformer_from_smiles("CCO")
    assert mol is not None and mol.GetNumConformers() == 1


def test_conformer_rejects_bad_smiles():
    assert docking.conformer_from_smiles("not-a-smiles") is None


@pytest.mark.skipif(not docking.available(), reason="smina binary not fetched")
def test_smina_binary_runs():
    import subprocess

    out = subprocess.run(
        [str(docking.smina_path()), "--version"], capture_output=True, text=True, timeout=60
    )
    assert out.returncode == 0
    assert "smina" in out.stdout.lower()
