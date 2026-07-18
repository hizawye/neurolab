"""Train/test splitting.

Scaffold splitting is the load-bearing defence against analog bias. ChEMBL
actives arrive as congeneric series from individual papers: a random split puts
near-identical analogs on both sides and inflates every metric toward ceiling.
Grouping by Bemis-Murcko scaffold and assigning whole groups forces the test set
to be structurally novel relative to training.

The random split is kept only as a diagnostic. The gap between the two
quantifies how much analog bias the dataset carried.
"""

from __future__ import annotations

import random

from rdkit import Chem, RDLogger
from rdkit.Chem.Scaffolds import MurckoScaffold

from . import provenance

RDLogger.DisableLog("rdApp.*")

TEST_FRACTION = 0.2


def scaffold_of(smiles: str) -> str:
    """Bemis-Murcko scaffold as canonical SMILES.

    Acyclic molecules reduce to an empty scaffold; they are bucketed together
    under a sentinel rather than each becoming its own singleton group.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return "__invalid__"
    try:
        scaffold = MurckoScaffold.GetScaffoldForMol(mol)
    except Exception:
        return "__invalid__"
    smiles_out = Chem.MolToSmiles(scaffold)
    return smiles_out or "__acyclic__"


def scaffold_split(
    smiles_list: list[str],
    test_fraction: float = TEST_FRACTION,
    seed: int = provenance.DEFAULT_SEED,
) -> tuple[list[int], list[int]]:
    """Split indices so no scaffold appears in both train and test.

    Groups are sorted largest-first and packed into *train* until it is full;
    the remainder becomes test. This is the DeepChem convention, and the
    direction matters: filling test largest-first instead would concentrate the
    big congeneric series in test, which both skews its class balance and makes
    it easier rather than harder. Packing train first leaves test as the rare
    and singleton scaffolds — genuinely novel chemistry relative to training.
    """
    groups: dict[str, list[int]] = {}
    for index, smiles in enumerate(smiles_list):
        groups.setdefault(scaffold_of(smiles), []).append(index)

    ordered = list(groups.values())

    # Deterministic shuffle before the size sort, so equal-sized groups break
    # ties reproducibly rather than by dict insertion order.
    rng = random.Random(seed)
    rng.shuffle(ordered)
    ordered.sort(key=len, reverse=True)

    train_target = len(smiles_list) - int(len(smiles_list) * test_fraction)
    train: list[int] = []
    test: list[int] = []
    for group in ordered:
        if len(train) + len(group) <= train_target:
            train.extend(group)
        else:
            test.extend(group)

    return sorted(train), sorted(test)


def random_split(
    smiles_list: list[str],
    test_fraction: float = TEST_FRACTION,
    seed: int = provenance.DEFAULT_SEED,
) -> tuple[list[int], list[int]]:
    """Diagnostic only. Reported beside the scaffold split to expose analog bias."""
    indices = list(range(len(smiles_list)))
    rng = random.Random(seed)
    rng.shuffle(indices)
    cut = int(len(indices) * test_fraction)
    return sorted(indices[cut:]), sorted(indices[:cut])
