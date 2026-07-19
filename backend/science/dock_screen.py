"""Docking versus similarity search, on identical compounds.

The overall comparison is the less interesting half. Similarity search already
posts EF@1% of 84-92x on this benchmark, and the literature is consistent that
docking rarely beats a well-resourced ligand-based method when good actives
exist. Confirming that again would cost hours and change nothing.

The question worth the compute is narrower. Similarity search has a specific,
measured weakness: it cannot see past resemblance, so it degrades on compounds
unlike anything in the reference set (ROC-AUC 0.962 against random library
compounds, 0.794 against measured inactives that are close analogs). Docking
scores a pose against a protein and is indifferent to whether the ligand looks
like anything known. If it earns its cost anywhere, it is there.

So compounds are binned by their similarity to the training actives, and the
two methods are compared *within* each bin. Both rank the identical compound
set, which makes the comparison fair even though the active ratio is higher
than a real screening library.

Only targets that pass redocking are eligible. A docking score from a setup
that cannot reproduce a known pose is not evidence of anything.
"""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from rdkit import Chem, RDLogger

from . import datasets, docking, metrics, provenance, redock, splits
from .featurizers import ecfp4
from .models import SimilarityBaseline

RDLogger.DisableLog("rdApp.*")

REPORT_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

# Bins of max ECFP4 Tanimoto to the training actives. The low bin is where
# similarity search has little to work with and docking should have its edge.
#
# Split at 0.5 rather than in thirds because of how the actives actually
# distribute. A <0.3 bin holds 1496 MAO-B compounds but only 14 actives, and
# for D2 just 3 — far too few to resolve a difference between methods. Even
# after a scaffold split, ChEMBL's actives for well-studied targets are
# overwhelmingly close analogs of one another.
NOVELTY_BINS = [
    ("dissimilar (<0.5)", 0.0, 0.5),
    ("close analog (>=0.5)", 0.5, 1.01),
]

# A bin needs this many actives before its comparison means anything, matching
# the threshold used elsewhere in the harness.
MIN_BIN_ACTIVES = 30

# Lower than the redocking runs. Pose geometry needs care; ranking a library
# tolerates a coarser search, and this buys back most of the wall clock.
SCREEN_EXHAUSTIVENESS = 8


@dataclass
class DockedCompound:
    smiles: str
    label: int
    affinity: float | None
    similarity: float


def _dock_one(args) -> tuple[str, float | None]:
    """Worker: dock a single compound. Must be top-level for pickling."""
    smiles, receptor_pdb, reference_block, seed, cpus = args
    try:
        probe = docking.conformer_from_smiles(smiles, seed=seed)
        if probe is None:
            return smiles, None
        reference = Chem.MolFromMolBlock(reference_block)
        result = docking.dock(
            receptor_pdb,
            probe,
            reference_mol=reference,
            exhaustiveness=SCREEN_EXHAUSTIVENESS,
            num_modes=3,
            seed=seed,
        )
        return smiles, result.top_affinity
    except Exception:
        return smiles, None


def build_compound_set(
    target_id: str,
    n_actives: int,
    n_decoys: int,
    seed: int,
) -> tuple[list[str], np.ndarray, list[str]]:
    """Held-out actives and decoys, plus the training actives for similarity.

    Uses the same scaffold split as the activity benchmark, so the test
    compounds are structurally novel relative to what similarity search is
    given as reference.
    """
    import random

    measured = datasets.build_measured_dataset(target_id)
    smiles = [c.smiles for c in measured.compounds]
    labels = np.array([c.label for c in measured.compounds])
    train_idx, test_idx = splits.scaffold_split(smiles, seed=seed)

    train_actives = [smiles[i] for i in train_idx if labels[i] == 1]
    test_actives = [smiles[i] for i in test_idx if labels[i] == 1]

    rng = random.Random(seed)
    if len(test_actives) > n_actives:
        test_actives = rng.sample(test_actives, n_actives)

    pool = datasets.fetch_decoy_pool(n_molecules=40000, seed=seed)
    active_compounds = [
        datasets.Compound(chembl_id=f"A{i}", smiles=s, label=1)
        for i, s in enumerate(test_actives)
    ]
    decoy_set = datasets.build_decoy_dataset(
        active_compounds,
        pool,
        seed=seed,
        active_fraction=len(test_actives) / (len(test_actives) + n_decoys),
    )
    decoys = [c.smiles for c in decoy_set.compounds if c.source == "decoy"][:n_decoys]

    compounds = test_actives + decoys
    y = np.array([1] * len(test_actives) + [0] * len(decoys))
    return compounds, y, train_actives


def run_target(
    target_id: str,
    n_actives: int = 100,
    n_decoys: int = 1900,
    seed: int = provenance.DEFAULT_SEED,
    workers: int = 6,
) -> dict:
    entry = redock.PANEL[target_id]

    # Eligibility: the setup must reproduce a known pose for this target.
    outcome = redock.redock_target(target_id, entry, seed)
    if not outcome.succeeded:
        return {
            "target": target_id,
            "name": entry["name"],
            "eligible": False,
            "reason": (
                f"redocking failed ({outcome.top_rmsd:.2f} A"
                f"{', ' + outcome.failure_mode + ' failure' if outcome.failure_mode else ''}); "
                "a docking score from a setup that cannot reproduce a known pose "
                "is not evidence"
            ),
        }

    pdb_text = redock.fetch_pdb(entry["pdb"])
    receptor, _ = docking.split_structure(pdb_text, chain=entry["chain"])
    reference, ligand, _ = redock.reference_from_structure(pdb_text, entry)
    reference_block = Chem.MolToMolBlock(reference)

    compounds, y, train_actives = build_compound_set(target_id, n_actives, n_decoys, seed)

    # Similarity: the incumbent, scored on the identical set.
    similarity_model = SimilarityBaseline()
    similarity_model.fit(train_actives, np.ones(len(train_actives), dtype=int))
    similarity = similarity_model.score(compounds)

    cpus = max(1, (os.cpu_count() or 4) // workers)
    payload = [(s, receptor, reference_block, seed, cpus) for s in compounds]

    started = time.time()
    affinities: dict[str, float | None] = {}
    with ProcessPoolExecutor(max_workers=workers) as pool_exec:
        for index, (smiles, affinity) in enumerate(pool_exec.map(_dock_one, payload), 1):
            affinities[smiles] = affinity
            if index % 100 == 0:
                rate = (time.time() - started) / index
                remaining = (len(payload) - index) * rate / 60
                print(
                    f"  docked {index}/{len(payload)}  "
                    f"{rate:.1f}s/compound  ~{remaining:.0f} min left",
                    flush=True,
                )

    # More negative affinity is better, so negate to make "higher is better".
    docking_scores = np.array(
        [-affinities.get(s) if affinities.get(s) is not None else np.nan for s in compounds]
    )

    usable = ~np.isnan(docking_scores)
    n_failed = int((~usable).sum())
    # Failed dockings rank last rather than being dropped, which is how they
    # would behave in a real campaign.
    docking_scores = np.where(usable, docking_scores, np.nanmin(docking_scores) - 1.0)

    overall = {
        "docking": metrics.evaluate(y, docking_scores),
        "similarity": metrics.evaluate(y, similarity),
    }
    for name, scores in (("docking", docking_scores), ("similarity", similarity)):
        overall[name]["bedroc_ci"] = metrics.bootstrap_ci(
            y, scores, lambda t, s: metrics.bedroc(t, s), n_boot=500, seed=seed
        )

    # The question the run exists to answer.
    by_bin = []
    for label, low, high in NOVELTY_BINS:
        mask = (similarity >= low) & (similarity < high)
        n_active = int(y[mask].sum())
        if n_active < MIN_BIN_ACTIVES or len(set(y[mask].tolist())) < 2:
            by_bin.append({
                "bin": label,
                "n": int(mask.sum()),
                "n_active": n_active,
                "note": f"underpowered: {n_active} actives, need {MIN_BIN_ACTIVES}",
            })
            continue
        by_bin.append({
            "bin": label,
            "n": int(mask.sum()),
            "n_active": int(y[mask].sum()),
            "docking": metrics.evaluate(y[mask], docking_scores[mask]),
            "similarity": metrics.evaluate(y[mask], similarity[mask]),
        })

    return {
        "target": target_id,
        "name": entry["name"],
        "eligible": True,
        "pdb": entry["pdb"],
        "ligand": ligand["code"],
        "redock_rmsd": outcome.top_rmsd,
        "n_compounds": len(compounds),
        "n_active": int(y.sum()),
        "active_ratio": float(y.mean()),
        "n_train_actives": len(train_actives),
        "n_docking_failures": n_failed,
        "elapsed_minutes": round((time.time() - started) / 60, 1),
        "overall": overall,
        "by_novelty": by_bin,
    }


def save(report: dict) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = report["metadata"]["generated_at"][:10]
    js = REPORT_DIR / f"docking-vs-similarity-{stamp}.json"
    js.write_text(json.dumps(report, indent=2, default=str))
    md = REPORT_DIR / f"docking-vs-similarity-{stamp}.md"
    md.write_text(render(report))
    return md, js


def render(report: dict) -> str:
    lines = [
        "# Docking versus similarity search",
        "",
        f"ChEMBL {report['metadata']['chembl_release']} · seed "
        f"`{report['metadata']['seed']}` · generated {report['metadata']['generated_at']}",
        "",
        "Both methods rank the identical compound set. Only targets whose setup reproduces a "
        "known crystallographic pose are eligible.",
        "",
    ]
    for result in report["targets"]:
        if not result.get("eligible"):
            lines += [f"## {result['name']} — not eligible", "", result["reason"], ""]
            continue

        lines += [
            f"## {result['name']} ({result['pdb']}, redock {result['redock_rmsd']:.2f} A)",
            "",
            f"{result['n_compounds']} compounds, {result['n_active']} active "
            f"({result['active_ratio']:.1%}) · {result['n_docking_failures']} docking failures "
            f"· {result['elapsed_minutes']} min",
            "",
            "| method | BEDROC | 95% CI | EF@1% | EF@5% | ROC-AUC |",
            "|---|---|---|---|---|---|",
        ]
        for name in ("similarity", "docking"):
            m = result["overall"][name]
            ci = m.get("bedroc_ci", (float("nan"), float("nan")))
            lines.append(
                f"| {name} | {m['bedroc']:.3f} | [{ci[0]:.3f}, {ci[1]:.3f}] | "
                f"{m['ef_1pct']:.1f} | {m['ef_5pct']:.1f} | {m['roc_auc']:.3f} |"
            )

        lines += [
            "",
            "### By similarity to training actives",
            "",
            "The bin that matters is the first: compounds unlike anything known, where "
            "similarity search has no signal to work from.",
            "",
            "| novelty bin | n | actives | similarity BEDROC | docking BEDROC |",
            "|---|---|---|---|---|",
        ]
        for b in result["by_novelty"]:
            if "note" in b:
                lines.append(f"| {b['bin']} | {b['n']} | {b.get('n_active','—')} | — | {b['note']} |")
                continue
            lines.append(
                f"| {b['bin']} | {b['n']} | {b['n_active']} | "
                f"{b['similarity']['bedroc']:.3f} | {b['docking']['bedroc']:.3f} |"
            )
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Entry point.

    Guarded because run_target uses a process pool and Python does not default
    to fork everywhere: an unguarded caller re-imports the module in each child
    and re-spawns itself.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Docking versus similarity search.")
    parser.add_argument("--target", action="append", help="ChEMBL target id (repeatable)")
    parser.add_argument("--actives", type=int, default=150)
    parser.add_argument("--decoys", type=int, default=1850)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--seed", type=int, default=provenance.DEFAULT_SEED)
    args = parser.parse_args()

    if not docking.available():
        raise SystemExit("smina not found. Run scripts/fetch_smina.sh first.")

    targets = args.target or ["CHEMBL2039"]
    results = []
    for target_id in targets:
        print(f"=== {target_id} ===", flush=True)
        result = run_target(
            target_id,
            n_actives=args.actives,
            n_decoys=args.decoys,
            seed=args.seed,
            workers=args.workers,
        )
        results.append(result)
        if not result.get("eligible"):
            print(f"  not eligible: {result['reason']}", flush=True)
        else:
            for name in ("similarity", "docking"):
                m = result["overall"][name]
                print(
                    f"  {name:<11} BEDROC {m['bedroc']:.3f}  "
                    f"EF@1% {m['ef_1pct']:.1f}  ROC {m['roc_auc']:.3f}",
                    flush=True,
                )

    report = {"metadata": provenance.run_metadata(seed=args.seed), "targets": results}
    md, js = save(report)
    print(f"\nReport: {md}\n        {js}", flush=True)


if __name__ == "__main__":
    main()
