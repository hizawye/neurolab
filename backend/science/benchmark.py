"""Benchmark orchestration and reporting.

Runs every scoring method over every track and split for a set of targets, and
judges the result against the criteria fixed before the first run:

  A method is validated only if it beats random, the descriptor score, AND
  nearest-neighbour Tanimoto similarity, on early-enrichment metrics, by a
  margin outside the bootstrap confidence interval.

The similarity baseline is the real bar. If a model loses to it, that is the
finding and it gets reported as one.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from . import datasets, metrics, models, provenance, splits

REPORT_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

# Fixed before the first run. Changing these after seeing results would turn
# the benchmark back into a demo.
PRIMARY_METRIC = "bedroc"
BASELINE_NAMES = ("random", "descriptor_score", "max_tanimoto")


@dataclass
class MethodResult:
    method: str
    is_baseline: bool
    metrics: dict
    ci: dict = field(default_factory=dict)


@dataclass
class SplitResult:
    target: str
    track: str
    split: str
    n_train: int
    n_test: int
    test_active_ratio: float
    random_bedroc_reference: float
    results: list[MethodResult]


def run_split(
    target: str,
    track: str,
    split_name: str,
    smiles: list[str],
    labels: np.ndarray,
    train_idx: list[int],
    test_idx: list[int],
    seed: int,
    n_boot: int,
) -> SplitResult:
    train_smiles = [smiles[i] for i in train_idx]
    test_smiles = [smiles[i] for i in test_idx]
    y_train, y_test = labels[train_idx], labels[test_idx]

    method_results = []
    for method in models.all_methods(seed):
        method.fit(train_smiles, y_train)
        scores = method.score(test_smiles)
        values = metrics.evaluate(y_test, scores)

        ci = {}
        if n_boot:
            for name, fn in (
                ("bedroc", lambda t, s: metrics.bedroc(t, s)),
                ("ef_1pct", lambda t, s: metrics.enrichment_factor(t, s, 0.01)),
            ):
                ci[name] = metrics.bootstrap_ci(y_test, scores, fn, n_boot=n_boot, seed=seed)

        method_results.append(
            MethodResult(method.name, method.is_baseline, values, ci)
        )

    return SplitResult(
        target=target,
        track=track,
        split=split_name,
        n_train=len(train_idx),
        n_test=len(test_idx),
        test_active_ratio=float(y_test.mean()),
        random_bedroc_reference=metrics.random_bedroc(float(y_test.mean())),
        results=method_results,
    )


def run_track(
    target: str,
    dataset: datasets.Dataset,
    seed: int,
    n_boot: int,
) -> list[SplitResult]:
    smiles = [c.smiles for c in dataset.compounds]
    labels = np.array([c.label for c in dataset.compounds])

    out = []
    for split_name, splitter in (
        ("scaffold", splits.scaffold_split),
        ("random", splits.random_split),
    ):
        train_idx, test_idx = splitter(smiles, seed=seed)
        if not train_idx or not test_idx:
            continue
        out.append(
            run_split(
                target, dataset.track, split_name, smiles, labels,
                train_idx, test_idx, seed, n_boot,
            )
        )
    return out


def run_target(
    target: str,
    decoy_pool: list[tuple[str, str]] | None = None,
    seed: int = provenance.DEFAULT_SEED,
    n_boot: int = 500,
) -> tuple[list[SplitResult], list[dict]]:
    measured = datasets.build_measured_dataset(target)
    dataset_summaries = [
        {"track": measured.track, "n_active": measured.n_active,
         "n_inactive": measured.n_inactive, **measured.metadata}
    ]
    results = run_track(target, measured, seed, n_boot)

    if decoy_pool:
        actives = [c for c in measured.compounds if c.label == 1]
        decoy_set = datasets.build_decoy_dataset(actives, decoy_pool, seed=seed)
        decoy_set.target_chembl_id = target
        dataset_summaries.append(
            {"track": decoy_set.track, "n_active": decoy_set.n_active,
             "n_inactive": decoy_set.n_inactive, **decoy_set.metadata}
        )
        results.extend(run_track(target, decoy_set, seed, n_boot))

    return results, dataset_summaries


# Above this active ratio the metrics lose their dynamic range: at 87% actives
# a random ranking already scores 0.86 BEDROC and EF@1% cannot exceed 1.15, so
# "beating random" means almost nothing. Splits past this are reported but
# marked low-information rather than being allowed to read as a clean pass.
LOW_INFORMATION_ACTIVE_RATIO = 0.60

# Every early-enrichment metric is computed from the actives in the test set,
# so that count — not the total compound count — sets the precision. Below
# this, confidence intervals are wider than any plausible difference between
# methods, and a FAIL means "cannot tell", not "worse".
MIN_TEST_ACTIVES = 50


def is_low_information(split: SplitResult) -> bool:
    return split.test_active_ratio > LOW_INFORMATION_ACTIVE_RATIO


def n_test_actives(split: SplitResult) -> int:
    return int(round(split.n_test * split.test_active_ratio))


def is_underpowered(split: SplitResult) -> bool:
    return n_test_actives(split) < MIN_TEST_ACTIVES


def verdict(split: SplitResult) -> dict:
    """Does any non-baseline method clear all three baselines on the primary metric?

    A margin that sits inside the bootstrap interval is not a win. Reported per
    split so a model that only wins on the easy random split is visible as such.
    """
    by_name = {r.method: r for r in split.results}
    baseline_values = [
        by_name[n].metrics.get(PRIMARY_METRIC, float("nan"))
        for n in BASELINE_NAMES
        if n in by_name
    ]
    best_baseline = max([v for v in baseline_values if not np.isnan(v)], default=float("nan"))

    winners = []
    for result in split.results:
        if result.is_baseline:
            continue
        value = result.metrics.get(PRIMARY_METRIC, float("nan"))
        low = result.ci.get(PRIMARY_METRIC, (float("nan"), float("nan")))[0]
        # Beat the strongest baseline, and do it outside the noise band.
        if not np.isnan(value) and value > best_baseline and low > best_baseline:
            winners.append(result.method)

    return {
        "best_baseline": best_baseline,
        "best_baseline_name": max(
            (n for n in BASELINE_NAMES if n in by_name),
            key=lambda n: by_name[n].metrics.get(PRIMARY_METRIC, float("-inf")),
            default=None,
        ),
        "winners": winners,
        "passed": bool(winners),
        "low_information": is_low_information(split),
        "underpowered": is_underpowered(split),
        "n_test_actives": n_test_actives(split),
    }


def _fmt(value: float, places: int = 3) -> str:
    return "n/a" if value is None or np.isnan(value) else f"{value:.{places}f}"


def render_report(all_results: list[SplitResult], summaries: list[dict], meta: dict) -> str:
    lines = [
        "# NeuroLab virtual-screening benchmark",
        "",
        f"ChEMBL release **{meta['chembl_release']}** · seed `{meta['seed']}` · "
        f"generated {meta['generated_at']}",
        "",
        "## Pre-registered criterion",
        "",
        f"A method is validated only if it beats **all three** baselines "
        f"(`random`, `descriptor_score`, `max_tanimoto`) on **{PRIMARY_METRIC}**, "
        "with the lower bound of its 95% bootstrap interval above the best baseline.",
        "",
        "`max_tanimoto` is the bar that matters: beating only random proves nothing.",
        "",
        "## Datasets",
        "",
        "| target | track | actives | inactives |",
        "|---|---|---|---|",
    ]
    for summary in summaries:
        lines.append(
            f"| {summary.get('target', '—')} | {summary['track']} | "
            f"{summary['n_active']} | {summary['n_inactive']} |"
        )

    lines += [
        "",
        "Track A inactives are **measured**. Track B inactives are property-matched "
        "decoys that are **presumed** inactive — they have no recorded activity, which "
        "is not the same as being tested and found inactive.",
        "",
        "## Results",
        "",
    ]

    for split in all_results:
        outcome = verdict(split)
        lines += [
            f"### {split.target} · {split.track} · {split.split} split",
            "",
            f"{split.n_train} train / {split.n_test} test · "
            f"test actives {split.test_active_ratio:.1%} · "
            f"random BEDROC reference `{_fmt(split.random_bedroc_reference)}`",
            "",
            "| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for result in split.results:
            tag = "baseline" if result.is_baseline else "**model**"
            ci = result.ci.get("bedroc", (float("nan"), float("nan")))
            lines.append(
                f"| `{result.method}` | {tag} | {_fmt(result.metrics['roc_auc'])} | "
                f"{_fmt(result.metrics['pr_auc'])} | {_fmt(result.metrics['ef_1pct'], 2)} | "
                f"{_fmt(result.metrics['ef_5pct'], 2)} | {_fmt(result.metrics['bedroc'])} | "
                f"[{_fmt(ci[0])}, {_fmt(ci[1])}] |"
            )

        if outcome["passed"]:
            note = (
                f"**PASS** — {', '.join(outcome['winners'])} beat the strongest baseline "
                f"(`{outcome['best_baseline_name']}` at {_fmt(outcome['best_baseline'])})."
            )
        else:
            note = (
                f"**FAIL** — no model beat `{outcome['best_baseline_name']}` "
                f"({_fmt(outcome['best_baseline'])}) outside its confidence interval."
            )
        lines += ["", note, ""]

        if outcome["underpowered"]:
            lines += [
                f"> **Underpowered — a FAIL here means \"cannot tell\", not \"worse\".** "
                f"Only {outcome['n_test_actives']} actives in the test set (minimum "
                f"{MIN_TEST_ACTIVES} for a resolvable comparison). Every enrichment metric "
                f"is computed from those actives alone, so the confidence intervals are "
                f"wider than any plausible difference between methods. The Track B active "
                f"count is capped by the decoy pool size — raising the pool is what fixes "
                f"this, not changing the model.",
                "",
            ]

        if outcome["low_information"]:
            lines += [
                f"> **Low information — do not read the above as a meaningful result.** "
                f"The test set is {split.test_active_ratio:.0%} actives, so a random ranking "
                f"already scores {_fmt(split.random_bedroc_reference)} BEDROC and EF@1% cannot "
                f"exceed {1 / split.test_active_ratio:.2f}. There is almost no dynamic range "
                f"left for a method to demonstrate anything. This happens when ChEMBL holds "
                f"few measured inactives for the target; the Track B result is the informative "
                f"one.",
                "",
            ]

    lines += [
        "## Interpretation notes",
        "",
        "- The **scaffold** split is the real test; the **random** split is a diagnostic. "
        "A large gap between them measures how much analog bias the dataset carried.",
        "- BEDROC's random reference is **not 0.5** — it depends on the active ratio "
        "(~0.12 at 10% actives, ~0.05 at 0.5%). Each table states its own reference.",
        "- EF@1% saturates at `1/active_ratio`. On Track A that ceiling is low enough "
        "that methods tie there; Track B exists to make enrichment meaningful.",
        "",
    ]
    return "\n".join(lines)


def save_report(all_results, summaries, meta) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = meta["generated_at"][:10]

    md_path = REPORT_DIR / f"benchmark-{stamp}.md"
    md_path.write_text(render_report(all_results, summaries, meta))

    json_path = REPORT_DIR / f"benchmark-{stamp}.json"
    json_path.write_text(
        json.dumps(
            {
                "metadata": meta,
                "datasets": summaries,
                "splits": [
                    {**asdict(s), "verdict": verdict(s)} for s in all_results
                ],
            },
            indent=2,
            default=str,
        )
    )
    return md_path, json_path
