"""Redocking validation.

The first question to ask of a docking setup is not "what scores well" but
"can it reproduce a pose we already know the answer to". Take a structure
solved with its ligand bound, throw away the ligand's coordinates, rebuild it
from SMILES, dock it back, and measure how far the top-ranked pose sits from
the crystallographic truth. Under 2 A is the accepted standard.

A setup that fails this cannot be trusted to rank unknowns, and any enrichment
it produced would be luck. Running it per target also catches target-specific
problems — a mis-detected binding site, a stripped cofactor, a ligand whose
bond orders were assigned wrongly.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import requests
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem

from . import docking, provenance

RDLogger.DisableLog("rdApp.*")

REPORT_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

# One solved complex per CNS panel target. Only the structure and the receptor
# chain are specified; the bound ligand and its bond orders are discovered from
# the structure and RCSB's chemical dictionary.
#
# Hand-writing those two fields was a mistake worth recording. It put a PIP2
# lipid in this panel as though it were a 5-HT1A drug, pointed at the G protein
# chain instead of the receptor, and gave safinamide an imine where it has an
# amine. All three are the kind of error that produces a confident number about
# the wrong molecule.
PANEL = {
    "CHEMBL2039": {"name": "MAO-B", "pdb": "2V5Z", "chain": "A"},
    # Chain R, not A: in a GPCR-G protein complex, A is the G alpha subunit.
    "CHEMBL217": {"name": "Dopamine D2 receptor", "pdb": "6CM4", "chain": "A"},
    "CHEMBL214": {"name": "5-HT1A receptor", "pdb": "7E2Z", "chain": "R"},
}


@dataclass
class RedockOutcome:
    target: str
    name: str
    pdb: str
    ligand_code: str
    ligand_name: str
    top_affinity: float | None
    top_rmsd: float | None
    best_rmsd: float | None
    crystal_affinity: float | None
    failure_mode: str | None
    n_poses: int
    succeeded: bool | None
    note: str = ""


def fetch_ligand_smiles(comp_id: str) -> str | None:
    """Authoritative SMILES for a PDB chemical component.

    Fetched rather than hand-written. Writing them by hand put a lipid in this
    panel as though it were a drug, and got safinamide's bond orders wrong.
    RCSB knows what is in its own structures.
    """
    key = provenance.cache_key("chemcomp", {"id": comp_id})
    cached = provenance.cache_read(key)
    if cached is None:
        if provenance.offline():
            raise RuntimeError(f"Offline mode: chemcomp {comp_id} not in cache.")
        response = requests.get(
            f"https://data.rcsb.org/rest/v1/core/chemcomp/{comp_id}", timeout=60
        )
        response.raise_for_status()
        cached = response.json()
        provenance.cache_write(key, cached)

    descriptors = cached.get("pdbx_chem_comp_descriptor", []) or []
    for program in ("OpenEye OEToolkits", "CACTVS"):
        for entry in descriptors:
            if entry.get("type") == "SMILES_CANONICAL" and entry.get("program") == program:
                return entry.get("descriptor")
    for entry in descriptors:
        if entry.get("type") in {"SMILES_CANONICAL", "SMILES"}:
            return entry.get("descriptor")
    return None


def fetch_pdb(pdb_id: str) -> str:
    key = provenance.cache_key("pdb", {"id": pdb_id})
    cached = provenance.cache_read(key)
    if cached is None:
        if provenance.offline():
            raise RuntimeError(f"Offline mode: {pdb_id} not in cache.")
        response = requests.get(f"https://files.rcsb.org/download/{pdb_id}.pdb", timeout=120)
        response.raise_for_status()
        cached = response.text
        provenance.cache_write(key, cached)
    return cached


def reference_from_structure(pdb_text: str, entry: dict):
    """Find the bound ligand and rebuild it with correct bond orders.

    Picks the largest remaining HET group after solvent, membrane components
    and cofactors are excluded, then takes its bond orders from RCSB rather
    than inferring them from geometry, which is unreliable for conjugated
    systems.
    """
    _, ligands = docking.split_structure(pdb_text, chain=entry["chain"])
    if not ligands:
        return None, None, []

    def heavy_atoms(text: str) -> int:
        return sum(
            1 for l in text.splitlines()
            if l.startswith(("ATOM", "HETATM")) and l[76:78].strip() != "H"
        )

    ranked = sorted(ligands.items(), key=lambda kv: heavy_atoms(kv[1]), reverse=True)
    available = [f"{k} ({heavy_atoms(v)} atoms)" for k, v in ranked]

    for key, text in ranked:
        comp_id = key.split(":")[1]
        smiles = fetch_ligand_smiles(comp_id)
        if not smiles:
            continue

        template = Chem.MolFromSmiles(smiles)
        crystal = Chem.MolFromPDBBlock(text, removeHs=True, sanitize=False)
        if template is None or crystal is None:
            continue
        try:
            reference = AllChem.AssignBondOrdersFromTemplate(template, crystal)
        except Exception:
            continue
        return reference, {"code": comp_id, "smiles": smiles}, available

    return None, None, available


def redock_target(target_id: str, entry: dict, seed: int) -> RedockOutcome:
    base = dict(
        target=target_id, name=entry["name"], pdb=entry["pdb"],
        ligand_code="?", ligand_name="?",
        top_affinity=None, top_rmsd=None, best_rmsd=None,
        crystal_affinity=None, failure_mode=None, n_poses=0, succeeded=None,
    )

    pdb_text = fetch_pdb(entry["pdb"])
    receptor, _ = docking.split_structure(pdb_text, chain=entry["chain"])
    reference, ligand, available_ligands = reference_from_structure(pdb_text, entry)

    if reference is None:
        return RedockOutcome(
            **base,
            note=f"no usable ligand in chain {entry['chain']}; candidates: {available_ligands}",
        )

    base["ligand_code"] = ligand["code"]
    base["ligand_name"] = ligand["code"]

    # Built from SMILES only, so the docking search starts with no knowledge of
    # the crystal geometry.
    probe = docking.conformer_from_smiles(ligand["smiles"], seed=seed)
    if probe is None:
        return RedockOutcome(**base, note="conformer generation failed")

    result = docking.dock(receptor, probe, reference_mol=reference, seed=seed)
    if not result.poses:
        return RedockOutcome(**base, note="docking returned no poses")

    rmsds = [p.rmsd_to_reference for p in result.poses if p.rmsd_to_reference is not None]

    # Scoring the crystal pose in place separates a search failure from a
    # scoring failure. Without it a FAIL is uninterpretable.
    crystal_affinity = docking.score_in_place(receptor, reference)
    failure_mode = None
    if result.redock_succeeded is False and crystal_affinity is not None and result.top_affinity is not None:
        if result.top_affinity < crystal_affinity:
            failure_mode = "scoring"   # found something it scored better than the truth
        else:
            failure_mode = "search"    # never reached a pose as good as the truth

    base.update(
        top_affinity=result.top_affinity,
        top_rmsd=result.top_rmsd,
        best_rmsd=min(rmsds) if rmsds else None,
        crystal_affinity=crystal_affinity,
        failure_mode=failure_mode,
        n_poses=len(result.poses),
        succeeded=result.redock_succeeded,
    )
    return RedockOutcome(**base)


def run(seed: int = provenance.DEFAULT_SEED) -> dict:
    outcomes = [redock_target(t, e, seed) for t, e in PANEL.items()]
    return {
        "metadata": provenance.run_metadata(seed=seed, rmsd_threshold=docking.RMSD_SUCCESS),
        "outcomes": [asdict(o) for o in outcomes],
    }


def render(report: dict) -> str:
    lines = [
        "# Redocking validation",
        "",
        f"Generated {report['metadata']['generated_at']} · seed "
        f"`{report['metadata']['seed']}` · success threshold "
        f"{docking.RMSD_SUCCESS} A",
        "",
        "Each ligand is rebuilt from SMILES with no crystal information, docked back into "
        "its own structure, and compared to the crystallographic pose. Cofactors are kept "
        "in the receptor; waters are removed.",
        "",
        "| target | PDB | ligand | top affinity | crystal-pose affinity | top RMSD | best RMSD | result |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for o in report["outcomes"]:
        if o["succeeded"] is None:
            verdict = f"could not run — {o['note']}"
            aff = xtal = top = best = "—"
        else:
            verdict = "**PASS**" if o["succeeded"] else "**FAIL**"
            if o["failure_mode"]:
                verdict += f" ({o['failure_mode']})"
            aff = f"{o['top_affinity']:.2f}"
            xtal = f"{o['crystal_affinity']:.2f}" if o["crystal_affinity"] is not None else "—"
            top = f"{o['top_rmsd']:.2f} A"
            best = f"{o['best_rmsd']:.2f} A"
        lines.append(
            f"| {o['name']} | {o['pdb']} | {o['ligand_code']} | "
            f"{aff} | {xtal} | {top} | {best} | {verdict} |"
        )

    lines += [
        "",
        "Top-pose RMSD is the number that matters: it asks whether the scoring function "
        "*ranked* the correct pose first. A good best-pose RMSD with a poor top-pose RMSD "
        "means the search found the right answer and the scoring failed to recognise it.",
        "",
        "The crystal-pose affinity column scores the experimental pose without moving it, "
        "which separates two failures that otherwise look identical:",
        "",
        "- **scoring failure** — docking found a pose it scores *better* than the "
        "crystallographic truth. The search worked; the scoring function is wrong. More "
        "sampling will not help.",
        "- **search failure** — nothing sampled scored as well as the crystal pose, so the "
        "search never reached it. More exhaustiveness or a larger box might.",
        "",
    ]
    return "\n".join(lines)


def save(report: dict) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = report["metadata"]["generated_at"][:10]
    md = REPORT_DIR / f"redocking-{stamp}.md"
    js = REPORT_DIR / f"redocking-{stamp}.json"
    md.write_text(render(report))
    js.write_text(json.dumps(report, indent=2, default=str))
    return md, js


def main() -> None:
    if not docking.available():
        raise SystemExit("smina not found. Run scripts/fetch_smina.sh first.")
    report = run()
    for o in report["outcomes"]:
        status = "PASS" if o["succeeded"] else ("FAIL" if o["succeeded"] is False else "SKIP")
        detail = (
            f"top {o['top_rmsd']:.2f} A, best {o['best_rmsd']:.2f} A, {o['top_affinity']:.2f} kcal/mol"
            if o["succeeded"] is not None
            else o["note"]
        )
        print(f"{status}  {o['name']:<24} {o['pdb']}  {detail}")
    md, js = save(report)
    print(f"\nReport: {md}\n        {js}")


if __name__ == "__main__":
    main()
