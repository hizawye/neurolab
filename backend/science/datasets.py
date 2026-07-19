"""Benchmark dataset construction from ChEMBL measurements.

Two tracks, reported separately and never pooled:

Track A uses compounds ChEMBL records as *measured* inactive. Most defensible,
but the class ratio is unrealistic because publications are biased toward
compounds that bind, so it measures discrimination rather than screening
performance.

Track B pads with property-matched decoys to reach a realistic screening
imbalance, which is what the enrichment metrics need to mean anything.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field
from statistics import median

from rdkit import Chem, RDLogger
from rdkit.Chem import Crippen, Descriptors, Lipinski, rdMolDescriptors

from . import chembl_bulk
from . import provenance

# RDKit is noisy on the malformed SMILES that inevitably appear in bulk data.
RDLogger.DisableLog("rdApp.*")

BINDING_ASSAY_TYPES = "Ki,Kd,IC50"

# Fixed before any run, so the boundary can't be tuned to flatter a result.
# The 5-7 band is discarded: measurement error between labs is comparable to
# the width of that window, so those labels would be noise.
ACTIVE_THRESHOLD = 7.0
INACTIVE_THRESHOLD = 5.0

# Realistic virtual-screening hit rate for Track B.
DECOY_ACTIVE_FRACTION = 0.005

# A decoy must be physicochemically similar but topologically distinct, or the
# model learns to separate on bulk properties instead of on binding.
DECOY_MAX_TANIMOTO = 0.35


@dataclass
class Compound:
    chembl_id: str
    smiles: str
    label: int  # 1 active, 0 inactive
    pchembl: float | None = None
    source: str = "measured"  # or "decoy"


@dataclass
class Dataset:
    target_chembl_id: str
    track: str
    compounds: list[Compound]
    metadata: dict = field(default_factory=dict)

    @property
    def n_active(self) -> int:
        return sum(c.label for c in self.compounds)

    @property
    def n_inactive(self) -> int:
        return len(self.compounds) - self.n_active


def _valid_smiles(smiles: str) -> str | None:
    """Canonicalise, rejecting anything RDKit cannot parse."""
    if not smiles:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol)


def _aggregate_measured(records: list[dict]) -> dict[str, tuple[str, float]]:
    """Collapse repeat measurements per molecule to a median pChEMBL.

    Same reasoning as the request-path aggregation in
    `backend/modules/ligand_finder.py`: a compound assayed many times across
    labs should be represented by its consensus, not its most flattering value.
    """
    grouped: dict[str, list[tuple[str, float]]] = {}
    for record in records:
        molecule_id = record.get("molecule_chembl_id")
        smiles = record.get("canonical_smiles")
        pchembl = record.get("pchembl_value")
        if not molecule_id or not smiles or pchembl is None:
            continue
        grouped.setdefault(molecule_id, []).append((smiles, float(pchembl)))

    aggregated = {}
    for molecule_id, entries in grouped.items():
        canonical = _valid_smiles(entries[0][0])
        if canonical is None:
            continue
        aggregated[molecule_id] = (canonical, median([value for _, value in entries]))
    return aggregated


def _explicit_inactives(target_chembl_id: str, max_records: int) -> dict[str, str]:
    """Compounds ChEMBL flags 'Not Active' — these carry no pChEMBL value."""
    records = chembl_bulk.fetch_all(
        "activity",
        {
            "target_chembl_id": target_chembl_id,
            "activity_comment__iexact": "Not Active",
        },
        max_records=max_records,
    )
    found = {}
    for record in records:
        molecule_id = record.get("molecule_chembl_id")
        canonical = _valid_smiles(record.get("canonical_smiles") or "")
        if molecule_id and canonical:
            found[molecule_id] = canonical
    return found


def build_measured_dataset(target_chembl_id: str, max_records: int = 20000) -> Dataset:
    """Track A: actives and inactives both from real measurements."""
    records = chembl_bulk.fetch_all(
        "activity",
        {
            "target_chembl_id": target_chembl_id,
            "standard_type__in": BINDING_ASSAY_TYPES,
            "pchembl_value__isnull": "false",
        },
        max_records=max_records,
    )
    aggregated = _aggregate_measured(records)

    compounds: list[Compound] = []
    discarded_ambiguous = 0
    for molecule_id, (smiles, pchembl) in aggregated.items():
        if pchembl >= ACTIVE_THRESHOLD:
            label = 1
        elif pchembl <= INACTIVE_THRESHOLD:
            label = 0
        else:
            discarded_ambiguous += 1
            continue
        compounds.append(
            Compound(chembl_id=molecule_id, smiles=smiles, label=label, pchembl=pchembl)
        )

    measured_ids = {c.chembl_id for c in compounds}
    for molecule_id, smiles in _explicit_inactives(target_chembl_id, max_records).items():
        if molecule_id not in measured_ids:
            compounds.append(
                Compound(chembl_id=molecule_id, smiles=smiles, label=0, pchembl=None)
            )

    dataset = Dataset(
        target_chembl_id=target_chembl_id,
        track="A_measured",
        compounds=compounds,
        metadata=provenance.run_metadata(
            target=target_chembl_id,
            track="A_measured",
            active_threshold=ACTIVE_THRESHOLD,
            inactive_threshold=INACTIVE_THRESHOLD,
            discarded_ambiguous=discarded_ambiguous,
            raw_records=len(records),
        ),
    )
    return dataset


def fetch_decoy_pool(
    n_molecules: int = 24000,
    seed: int = provenance.DEFAULT_SEED,
) -> list[tuple[str, str]]:
    """Drug-like ChEMBL molecules to draw property-matched decoys from.

    These are *presumed* inactive, not measured inactive: they simply have no
    recorded activity against the target. That is standard decoy practice and
    is labelled as such in reports, because a presumed inactive that turns out
    to bind is a false negative we cannot detect.

    Sampled across scattered offsets rather than sequentially, since ChEMBL IDs
    are assigned per-publication and a contiguous block would be one series of
    near-identical analogs.
    """
    rng = random.Random(seed)
    # Offsets fixed by seed so the pool is reproducible.
    chunk = 2000
    offsets = sorted(rng.sample(range(0, 1_200_000, chunk), n_molecules // chunk))

    pool: list[tuple[str, str]] = []
    for offset in offsets:
        records = chembl_bulk.fetch_all(
            "molecule",
            {
                "molecule_properties__mw_freebase__gte": 250,
                "molecule_properties__mw_freebase__lte": 500,
                "molecule_type": "Small molecule",
            },
            max_records=chunk,
            start_offset=offset,
        )
        for record in records:
            structures = record.get("molecule_structures") or {}
            canonical = _valid_smiles(structures.get("canonical_smiles") or "")
            molecule_id = record.get("molecule_chembl_id")
            if molecule_id and canonical:
                pool.append((molecule_id, canonical))

    return pool


def _generator_fp(mol):
    """ECFP4 from an already-parsed molecule, avoiding a second SMILES parse."""
    from .featurizers import _generator

    return _generator.GetFingerprint(mol)


def _properties(smiles: str) -> tuple | None:
    """Physicochemical profile a decoy must match."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return (
        Descriptors.MolWt(mol),
        Crippen.MolLogP(mol),
        Lipinski.NumHDonors(mol),
        Lipinski.NumHAcceptors(mol),
        rdMolDescriptors.CalcNumRotatableBonds(mol),
        Chem.GetFormalCharge(mol),
    )


def _property_distance(left: tuple, right: tuple) -> float:
    """Scaled distance in property space; charge mismatch is disqualifying."""
    if left[5] != right[5]:
        return float("inf")
    scales = (50.0, 1.0, 1.0, 2.0, 2.0)
    return sum(abs(a - b) / s for a, b, s in zip(left[:5], right[:5], scales))


def build_decoy_dataset(
    actives: list[Compound],
    decoy_pool: list[tuple[str, str]],
    seed: int = provenance.DEFAULT_SEED,
    active_fraction: float = DECOY_ACTIVE_FRACTION,
) -> Dataset:
    """Track B: actives padded with property-matched, topologically distinct decoys.

    Each decoy is matched to an active on bulk properties so the model cannot
    win by learning "actives are heavier", and required to be dissimilar by
    ECFP4 Tanimoto so a matched decoy is not just an unlabelled active.
    """
    import numpy as np
    from rdkit import DataStructs

    from .featurizers import ecfp4

    rng = random.Random(seed)
    active_props = [(c, _properties(c.smiles)) for c in actives]
    active_props = [(c, p) for c, p in active_props if p is not None]

    # The decoy pool bounds how many actives the target ratio can support:
    # 1000 actives at 0.5% would need ~200k decoys. Subsample actives to fit
    # rather than silently settling for an unrealistic ratio, which is what
    # would quietly destroy the meaning of the enrichment metrics.
    max_actives = max(1, int(len(decoy_pool) * active_fraction / (1 - active_fraction)))
    if len(active_props) > max_actives:
        active_props = rng.sample(active_props, max_actives)

    active_fps = [fp for fp in (ecfp4(c.smiles) for c, _ in active_props) if fp is not None]

    # Matching is O(candidates x actives), which at pool sizes large enough to
    # give a well-powered test set is millions of comparisons. Both inner loops
    # are pushed into compiled code: property distance via numpy broadcasting,
    # similarity via RDKit's bulk C++ kernel. Same filter, same results.
    active_matrix = np.array([p[:5] for _, p in active_props], dtype=float)
    active_charges = np.array([p[5] for _, p in active_props], dtype=int)
    scales = np.array([50.0, 1.0, 1.0, 2.0, 2.0], dtype=float)

    needed = int(len(active_props) / active_fraction) - len(active_props)
    candidates = list(decoy_pool)
    rng.shuffle(candidates)

    chosen: list[Compound] = []
    seen: set[str] = {c.chembl_id for c in actives}
    for molecule_id, smiles in candidates:
        if len(chosen) >= needed:
            break
        if molecule_id in seen:
            continue

        # Parse once; _properties and ecfp4 would each re-parse the SMILES.
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            continue
        props = (
            Descriptors.MolWt(mol),
            Crippen.MolLogP(mol),
            Lipinski.NumHDonors(mol),
            Lipinski.NumHAcceptors(mol),
            rdMolDescriptors.CalcNumRotatableBonds(mol),
        )
        charge = Chem.GetFormalCharge(mol)

        # Charge must match exactly; distance is scaled L1 over the rest.
        eligible = active_charges == charge
        if not eligible.any():
            continue
        distances = np.abs(active_matrix[eligible] - np.array(props)) / scales
        if distances.sum(axis=1).min() > 4.0:
            continue

        fingerprint = _generator_fp(mol)
        if max(DataStructs.BulkTanimotoSimilarity(fingerprint, active_fps)) >= DECOY_MAX_TANIMOTO:
            continue

        seen.add(molecule_id)
        chosen.append(
            Compound(chembl_id=molecule_id, smiles=smiles, label=0, source="decoy")
        )

    compounds = [c for c, _ in active_props] + chosen
    return Dataset(
        target_chembl_id=actives[0].chembl_id if actives else "unknown",
        track="B_decoys",
        compounds=compounds,
        metadata=provenance.run_metadata(
            seed=seed,
            track="B_decoys",
            requested_decoys=needed,
            matched_decoys=len(chosen),
            max_tanimoto=DECOY_MAX_TANIMOTO,
            active_fraction=active_fraction,
        ),
    )


def summarize(dataset: Dataset) -> str:
    sources = Counter(c.source for c in dataset.compounds)
    return (
        f"{dataset.target_chembl_id} [{dataset.track}] "
        f"{dataset.n_active} active / {dataset.n_inactive} inactive "
        f"({dict(sources)})"
    )
