"""Molecular featurization.

ECFP4 (Morgan radius 2) is the workhorse for ligand-based virtual screening and
the primary representation here. RDKit physicochemical descriptors are kept as a
secondary feature set so the descriptor-only baseline is comparable.
"""

from __future__ import annotations

import numpy as np
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import rdFingerprintGenerator

from ..modules.descriptors import calculate_descriptors

RDLogger.DisableLog("rdApp.*")

FP_RADIUS = 2
FP_BITS = 2048

_generator = rdFingerprintGenerator.GetMorganGenerator(radius=FP_RADIUS, fpSize=FP_BITS)


def ecfp4(smiles: str):
    """ECFP4 bit vector, or None if the SMILES will not parse."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return _generator.GetFingerprint(mol)


def tanimoto(left, right) -> float:
    return DataStructs.TanimotoSimilarity(left, right)


def fingerprint_matrix(smiles_list: list[str]) -> tuple[np.ndarray, list[int]]:
    """Stack ECFP4 vectors into a dense matrix.

    Returns the matrix alongside the indices that survived parsing, so callers
    can drop the corresponding labels and keep rows aligned.
    """
    rows = []
    kept = []
    for index, smiles in enumerate(smiles_list):
        fingerprint = ecfp4(smiles)
        if fingerprint is None:
            continue
        array = np.zeros((FP_BITS,), dtype=np.uint8)
        DataStructs.ConvertToNumpyArray(fingerprint, array)
        rows.append(array)
        kept.append(index)

    if not rows:
        return np.zeros((0, FP_BITS), dtype=np.uint8), []
    return np.vstack(rows), kept


def descriptor_matrix(smiles_list: list[str]) -> tuple[np.ndarray, list[int]]:
    """The five RDKit descriptors the existing ranker uses."""
    rows = []
    kept = []
    for index, smiles in enumerate(smiles_list):
        descriptors = calculate_descriptors(smiles)
        if descriptors is None:
            continue
        rows.append(
            [
                descriptors.molecular_weight,
                descriptors.logp,
                descriptors.tpsa,
                descriptors.h_bond_donors,
                descriptors.h_bond_acceptors,
            ]
        )
        kept.append(index)

    if not rows:
        return np.zeros((0, 5), dtype=float), []
    return np.array(rows, dtype=float), kept
