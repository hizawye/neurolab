"""Benchmark entry point.

    uv run python -m backend.science.cli --target CHEMBL2039
    uv run python -m backend.science.cli --panel

Re-running with NEUROLAB_OFFLINE=1 must reproduce identical numbers from cache.
"""

from __future__ import annotations

import argparse

from . import benchmark, datasets, provenance

# The CNS panel. Validating on a single target cannot distinguish a working
# method from one overfit to that target's quirks.
CNS_PANEL = {
    "CHEMBL217": "Dopamine D2 receptor",
    "CHEMBL2039": "MAO-B",
    "CHEMBL214": "5-HT1A receptor",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the virtual-screening benchmark.")
    parser.add_argument("--target", action="append", help="ChEMBL target id (repeatable)")
    parser.add_argument("--panel", action="store_true", help="Run the full CNS panel")
    parser.add_argument("--seed", type=int, default=provenance.DEFAULT_SEED)
    parser.add_argument("--bootstrap", type=int, default=500, help="0 disables CIs")
    parser.add_argument("--decoy-pool", type=int, default=20000)
    parser.add_argument("--no-decoys", action="store_true", help="Track A only")
    args = parser.parse_args()

    targets = list(args.target or [])
    if args.panel or not targets:
        targets = list(CNS_PANEL)

    pool = None
    if not args.no_decoys:
        print(f"Fetching decoy pool ({args.decoy_pool} molecules)...")
        pool = datasets.fetch_decoy_pool(n_molecules=args.decoy_pool, seed=args.seed)
        print(f"  pool: {len(pool)} molecules")

    all_results = []
    all_summaries = []
    for target in targets:
        label = CNS_PANEL.get(target, target)
        print(f"\n=== {target} ({label}) ===")
        results, summaries = benchmark.run_target(
            target, decoy_pool=pool, seed=args.seed, n_boot=args.bootstrap
        )
        for summary in summaries:
            summary["target"] = target
            print(f"  {summary['track']}: {summary['n_active']} active / {summary['n_inactive']} inactive")
        for split in results:
            outcome = benchmark.verdict(split)
            status = "PASS" if outcome["passed"] else "FAIL"
            print(
                f"  {split.track:<12} {split.split:<9} {status}"
                f"  (best baseline {outcome['best_baseline_name']}"
                f" = {outcome['best_baseline']:.3f})"
            )
        all_results.extend(results)
        all_summaries.extend(summaries)

    meta = provenance.run_metadata(seed=args.seed, targets=targets)
    md_path, json_path = benchmark.save_report(all_results, all_summaries, meta)
    print(f"\nReport: {md_path}\n        {json_path}")


if __name__ == "__main__":
    main()
