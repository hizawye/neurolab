"""Structure-based docking via smina.

Docking is added only now, after ligand-based methods were benchmarked, so it
has something to be measured against. A docking score that cannot be compared
to nearest-neighbour similarity tells you nothing about whether the extra
machinery earns its cost.

Two things here are easy to get wrong and are handled explicitly:

Cofactors stay in the receptor. MAO-B's FAD sits against the safinamide binding
site; removing it to satisfy a preparation step would open a cavity that does
not exist, and every pose docked into that cavity would be an artefact. Waters
are removed, cofactors are not.

Redocking is genuine. The probe conformer is generated from SMILES alone, so it
carries no memory of the crystal geometry. Scoring the crystal pose in place
would validate nothing.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem, rdMolAlign

RDLogger.DisableLog("rdApp.*")

BIN_DIR = Path(__file__).resolve().parent.parent / "bin"

# Kept in the receptor. These are structural or catalytic components of the
# protein, not the thing being docked.
COFACTORS = {
    "FAD", "FMN", "NAD", "NAP", "NDP", "HEM", "HEC", "SAM", "SAH",
    "ATP", "ADP", "AMP", "GTP", "GDP", "PLP", "COA", "TPP", "BTN",
    "ZN", "MG", "MN", "FE", "FE2", "CA", "NA", "K", "CU", "CL",
}

# Discarded outright: solvent and crystallisation additives.
SOLVENTS = {
    "HOH", "WAT", "DOD", "GOL", "EDO", "PEG", "PGE", "SO4", "PO4",
    "ACT", "DMS", "MPD", "TRS", "IMD", "FMT", "NO3", "IOD", "BR",
}

# Membrane and detergent components. These matter for GPCR structures, where
# lipids are often larger than the drug and would otherwise be picked as the
# "ligand" — 7E2X's biggest HET group is a PIP2 molecule, not a therapeutic.
MEMBRANE = {
    "CLR", "CHS", "PLM", "OLA", "OLC", "OLB", "PEE", "PCW", "POV", "PGW",
    "LMT", "LMN", "DDQ", "D10", "D12", "HEX", "MYS", "STE", "PX4", "PGT",
    "Y01", "9PE", "PSC", "3PH", "SQL", "MC3", "LDA", "BOG", "C8E", "F09",
    "J40",
}

# A co-crystal ligand small enough to be a fragment or large enough to be a
# peptide is not a useful redocking reference.
MIN_LIGAND_ATOMS = 8
MAX_LIGAND_ATOMS = 100

# The accepted threshold for calling a redocked pose correct.
RMSD_SUCCESS = 2.0


class DockingUnavailable(RuntimeError):
    """smina binary not found."""


def smina_path() -> Path:
    """Locate smina: explicit env var, then the repo's bin/, then PATH."""
    override = os.getenv("SMINA_BIN")
    if override and Path(override).exists():
        return Path(override)

    local = BIN_DIR / "smina"
    if local.exists():
        return local

    found = shutil.which("smina")
    if found:
        return Path(found)

    raise DockingUnavailable(
        "smina not found. Run scripts/fetch_smina.sh, or set SMINA_BIN."
    )


def available() -> bool:
    try:
        smina_path()
        return True
    except DockingUnavailable:
        return False


@dataclass
class Pose:
    rank: int
    affinity: float          # kcal/mol, more negative is better
    rmsd_to_reference: float | None = None


@dataclass
class DockingResult:
    poses: list[Pose]
    top_affinity: float | None
    top_rmsd: float | None

    @property
    def redock_succeeded(self) -> bool | None:
        if self.top_rmsd is None:
            return None
        return self.top_rmsd < RMSD_SUCCESS


def split_structure(pdb_text: str, chain: str | None = None) -> tuple[str, dict[str, str]]:
    """Separate a PDB into receptor and its candidate co-crystal ligands.

    Returns the receptor PDB text (protein plus cofactors, waters removed) and
    a mapping of residue key -> PDB text for each plausible ligand.
    """
    receptor: list[str] = []
    ligands: dict[str, list[str]] = {}

    for line in pdb_text.splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue

        line_chain = line[21]
        if chain and line_chain != chain:
            continue

        resname = line[17:20].strip()
        if resname in SOLVENTS or resname in MEMBRANE:
            continue

        if line.startswith("ATOM") or resname in COFACTORS:
            receptor.append(line)
        else:
            key = f"{line_chain}:{resname}:{line[22:26].strip()}"
            ligands.setdefault(key, []).append(line)

    usable = {}
    for key, lines in ligands.items():
        heavy = [l for l in lines if l[76:78].strip() != "H"]
        if MIN_LIGAND_ATOMS <= len(heavy) <= MAX_LIGAND_ATOMS:
            usable[key] = "\n".join(lines) + "\nEND\n"

    return "\n".join(receptor) + "\nEND\n", usable


def conformer_from_smiles(smiles: str, seed: int = 20260718):
    """3D conformer built from the SMILES alone.

    Deliberately carries no crystal information, which is what makes a redock a
    test rather than a restatement.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    mol = Chem.AddHs(mol)
    if AllChem.EmbedMolecule(mol, randomSeed=seed) != 0:
        return None
    try:
        AllChem.MMFFOptimizeMolecule(mol)
    except Exception:
        pass
    return mol


def score_in_place(receptor_pdb: str, ligand_mol) -> float | None:
    """Score a pose without moving it.

    Used to separate two failure modes that look identical from the outside. If
    the crystal pose scores *worse* than what docking found, the search worked
    and the scoring function preferred the wrong answer. If it scores better,
    the search failed to reach it. The fixes differ entirely.
    """
    binary = smina_path()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        receptor_file = tmp / "receptor.pdb"
        receptor_file.write_text(receptor_pdb)
        ligand_file = tmp / "ligand.sdf"
        Chem.MolToMolFile(ligand_mol, str(ligand_file))

        completed = subprocess.run(
            [str(binary), "-r", str(receptor_file), "-l", str(ligand_file), "--score_only"],
            capture_output=True, text=True, timeout=300,
        )

    for line in completed.stdout.splitlines():
        if line.startswith("Affinity:"):
            try:
                return float(line.split()[1])
            except (IndexError, ValueError):
                return None
    return None


def dock(
    receptor_pdb: str,
    ligand_mol,
    reference_mol=None,
    box_center: tuple[float, float, float] | None = None,
    box_size: float = 22.0,
    exhaustiveness: int = 16,
    num_modes: int = 9,
    seed: int = 20260718,
) -> DockingResult:
    """Dock one ligand. Box comes from the reference ligand when given."""
    binary = smina_path()

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        receptor_file = tmp / "receptor.pdb"
        receptor_file.write_text(receptor_pdb)

        ligand_file = tmp / "ligand.sdf"
        Chem.MolToMolFile(ligand_mol, str(ligand_file))

        out_file = tmp / "out.sdf"
        cmd = [
            str(binary),
            "-r", str(receptor_file),
            "-l", str(ligand_file),
            "-o", str(out_file),
            "--seed", str(seed),
            "--exhaustiveness", str(exhaustiveness),
            "--num_modes", str(num_modes),
            "--cpu", str(min(8, os.cpu_count() or 1)),
        ]

        if reference_mol is not None:
            reference_file = tmp / "reference.sdf"
            Chem.MolToMolFile(reference_mol, str(reference_file))
            cmd += ["--autobox_ligand", str(reference_file), "--autobox_add", "4"]
        elif box_center is not None:
            cmd += [
                "--center_x", str(box_center[0]),
                "--center_y", str(box_center[1]),
                "--center_z", str(box_center[2]),
                "--size_x", str(box_size),
                "--size_y", str(box_size),
                "--size_z", str(box_size),
            ]
        else:
            raise ValueError("dock() needs either reference_mol or box_center")

        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if completed.returncode != 0 or not out_file.exists():
            return DockingResult(poses=[], top_affinity=None, top_rmsd=None)

        docked = [m for m in Chem.SDMolSupplier(str(out_file), removeHs=True) if m]

    reference = Chem.RemoveHs(reference_mol) if reference_mol is not None else None
    poses: list[Pose] = []
    for index, pose in enumerate(docked, start=1):
        pose = Chem.RemoveHs(pose)
        affinity = (
            float(pose.GetProp("minimizedAffinity"))
            if pose.HasProp("minimizedAffinity")
            else float("nan")
        )
        rmsd = None
        if reference is not None:
            try:
                # Symmetry-aware, and no realignment: both are already in the
                # receptor frame, so aligning them would hide the error.
                rmsd = float(rdMolAlign.CalcRMS(pose, reference))
            except Exception:
                rmsd = None
        poses.append(Pose(rank=index, affinity=affinity, rmsd_to_reference=rmsd))

    return DockingResult(
        poses=poses,
        top_affinity=poses[0].affinity if poses else None,
        top_rmsd=poses[0].rmsd_to_reference if poses else None,
    )
