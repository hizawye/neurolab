# NeuroLab virtual-screening benchmark

ChEMBL release **ChEMBL_37** · seed `20260718` · generated 2026-07-18T23:29:31.980398+00:00

## Pre-registered criterion

A method is validated only if it beats **all three** baselines (`random`, `descriptor_score`, `max_tanimoto`) on **bedroc**, with the lower bound of its 95% bootstrap interval above the best baseline.

`max_tanimoto` is the bar that matters: beating only random proves nothing.

## Datasets

| target | track | actives | inactives |
|---|---|---|---|
| CHEMBL217 | A_measured | 3446 | 500 |
| CHEMBL217 | B_decoys | 100 | 17659 |
| CHEMBL2039 | A_measured | 1017 | 1278 |
| CHEMBL2039 | B_decoys | 100 | 16383 |
| CHEMBL214 | A_measured | 3361 | 350 |
| CHEMBL214 | B_decoys | 100 | 18402 |

Track A inactives are **measured**. Track B inactives are property-matched decoys that are **presumed** inactive — they have no recorded activity, which is not the same as being tested and found inactive.

## Results

### CHEMBL217 · A_measured · scaffold split

3157 train / 789 test · test actives 81.7% · random BEDROC reference `0.813`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.440 | 0.798 | 1.07 | 0.97 | 0.793 | [0.694, 0.880] |
| `descriptor_score` | baseline | 0.542 | 0.831 | 0.92 | 1.07 | 0.845 | [0.730, 0.890] |
| `max_tanimoto` | baseline | 0.944 | 0.983 | 1.22 | 1.19 | 0.987 | [0.963, 1.000] |
| `random_forest` | **model** | 0.968 | 0.992 | 1.22 | 1.22 | 1.000 | [1.000, 1.000] |
| `svm_linear` | **model** | 0.942 | 0.985 | 1.22 | 1.22 | 0.999 | [0.995, 1.000] |

**PASS** — random_forest, svm_linear beat the strongest baseline (`max_tanimoto` at 0.987).

> **Low information — do not read the above as a meaningful result.** The test set is 82% actives, so a random ranking already scores 0.813 BEDROC and EF@1% cannot exceed 1.22. There is almost no dynamic range left for a method to demonstrate anything. This happens when ChEMBL holds few measured inactives for the target; the Track B result is the informative one.

### CHEMBL217 · A_measured · random split

3157 train / 789 test · test actives 87.6% · random BEDROC reference `0.864`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.442 | 0.865 | 1.00 | 1.00 | 0.875 | [0.801, 0.945] |
| `descriptor_score` | baseline | 0.600 | 0.901 | 1.14 | 1.08 | 0.928 | [0.824, 0.957] |
| `max_tanimoto` | baseline | 0.962 | 0.991 | 1.14 | 1.14 | 0.991 | [0.953, 1.000] |
| `random_forest` | **model** | 0.988 | 0.998 | 1.14 | 1.14 | 1.000 | [1.000, 1.000] |
| `svm_linear` | **model** | 0.948 | 0.990 | 1.14 | 1.14 | 0.998 | [0.993, 1.000] |

**PASS** — random_forest, svm_linear beat the strongest baseline (`max_tanimoto` at 0.991).

> **Low information — do not read the above as a meaningful result.** The test set is 88% actives, so a random ranking already scores 0.864 BEDROC and EF@1% cannot exceed 1.14. There is almost no dynamic range left for a method to demonstrate anything. This happens when ChEMBL holds few measured inactives for the target; the Track B result is the informative one.

### CHEMBL217 · B_decoys · scaffold split

14208 train / 3551 test · test actives 1.0% · random BEDROC reference `0.055`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.524 | 0.012 | 0.00 | 1.11 | 0.058 | [0.016, 0.117] |
| `descriptor_score` | baseline | 0.493 | 0.011 | 41.10 | 8.31 | 0.441 | [0.016, 0.142] |
| `max_tanimoto` | baseline | 0.937 | 0.675 | 63.02 | 14.41 | 0.740 | [0.587, 0.855] |
| `random_forest` | **model** | 0.951 | 0.750 | 65.76 | 18.29 | 0.861 | [0.748, 0.934] |
| `svm_linear` | **model** | 0.977 | 0.805 | 73.98 | 18.29 | 0.886 | [0.783, 0.959] |

**PASS** — random_forest, svm_linear beat the strongest baseline (`max_tanimoto` at 0.740).

> **Underpowered — a FAIL here means "cannot tell", not "worse".** Only 36 actives in the test set (minimum 50 for a resolvable comparison). Every enrichment metric is computed from those actives alone, so the confidence intervals are wider than any plausible difference between methods. The Track B active count is capped by the decoy pool size — raising the pool is what fixes this, not changing the model.

### CHEMBL217 · B_decoys · random split

14208 train / 3551 test · test actives 0.9% · random BEDROC reference `0.055`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.533 | 0.010 | 0.00 | 0.62 | 0.050 | [0.013, 0.109] |
| `descriptor_score` | baseline | 0.508 | 0.009 | 40.07 | 8.10 | 0.428 | [0.009, 0.122] |
| `max_tanimoto` | baseline | 0.952 | 0.572 | 49.32 | 14.96 | 0.721 | [0.609, 0.838] |
| `random_forest` | **model** | 0.992 | 0.797 | 73.98 | 18.08 | 0.907 | [0.823, 0.965] |
| `svm_linear` | **model** | 0.973 | 0.757 | 70.90 | 16.83 | 0.852 | [0.760, 0.947] |

**PASS** — random_forest, svm_linear beat the strongest baseline (`max_tanimoto` at 0.721).

> **Underpowered — a FAIL here means "cannot tell", not "worse".** Only 32 actives in the test set (minimum 50 for a resolvable comparison). Every enrichment metric is computed from those actives alone, so the confidence intervals are wider than any plausible difference between methods. The Track B active count is capped by the decoy pool size — raising the pool is what fixes this, not changing the model.

### CHEMBL2039 · A_measured · scaffold split

1836 train / 459 test · test actives 31.6% · random BEDROC reference `0.316`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.518 | 0.353 | 1.27 | 1.24 | 0.408 | [0.267, 0.565] |
| `descriptor_score` | baseline | 0.585 | 0.362 | 1.90 | 1.38 | 0.441 | [0.243, 0.502] |
| `max_tanimoto` | baseline | 0.794 | 0.695 | 3.17 | 3.03 | 0.878 | [0.791, 0.939] |
| `random_forest` | **model** | 0.919 | 0.851 | 3.17 | 3.03 | 0.948 | [0.898, 0.981] |
| `svm_linear` | **model** | 0.848 | 0.730 | 3.17 | 2.75 | 0.845 | [0.733, 0.917] |

**PASS** — random_forest beat the strongest baseline (`max_tanimoto` at 0.878).

### CHEMBL2039 · A_measured · random split

1836 train / 459 test · test actives 42.3% · random BEDROC reference `0.423`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.525 | 0.451 | 0.95 | 1.23 | 0.480 | [0.328, 0.617] |
| `descriptor_score` | baseline | 0.609 | 0.486 | 0.95 | 1.65 | 0.582 | [0.355, 0.635] |
| `max_tanimoto` | baseline | 0.923 | 0.897 | 2.37 | 2.16 | 0.947 | [0.872, 0.995] |
| `random_forest` | **model** | 0.974 | 0.969 | 2.37 | 2.37 | 0.998 | [0.995, 1.000] |
| `svm_linear` | **model** | 0.926 | 0.902 | 2.37 | 2.26 | 0.959 | [0.898, 0.993] |

**PASS** — random_forest beat the strongest baseline (`max_tanimoto` at 0.947).

### CHEMBL2039 · B_decoys · scaffold split

13187 train / 3296 test · test actives 0.4% · random BEDROC reference `0.052`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.435 | 0.003 | 0.00 | 0.00 | 0.019 | [0.000, 0.056] |
| `descriptor_score` | baseline | 0.685 | 0.006 | 74.91 | 14.98 | 0.757 | [0.008, 0.222] |
| `max_tanimoto` | baseline | 0.971 | 0.715 | 74.91 | 14.98 | 0.778 | [0.519, 0.993] |
| `random_forest` | **model** | 0.937 | 0.738 | 74.91 | 14.98 | 0.787 | [0.527, 1.000] |
| `svm_linear` | **model** | 0.894 | 0.738 | 74.91 | 14.98 | 0.759 | [0.467, 1.000] |

**FAIL** — no model beat `max_tanimoto` (0.778) outside its confidence interval.

> **Underpowered — a FAIL here means "cannot tell", not "worse".** Only 12 actives in the test set (minimum 50 for a resolvable comparison). Every enrichment metric is computed from those actives alone, so the confidence intervals are wider than any plausible difference between methods. The Track B active count is capped by the decoy pool size — raising the pool is what fixes this, not changing the model.

### CHEMBL2039 · B_decoys · random split

13187 train / 3296 test · test actives 0.8% · random BEDROC reference `0.054`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.537 | 0.010 | 0.00 | 0.71 | 0.056 | [0.006, 0.115] |
| `descriptor_score` | baseline | 0.640 | 0.013 | 64.21 | 12.84 | 0.662 | [0.026, 0.165] |
| `max_tanimoto` | baseline | 0.939 | 0.804 | 78.48 | 16.41 | 0.832 | [0.695, 0.955] |
| `random_forest` | **model** | 0.964 | 0.817 | 82.04 | 16.41 | 0.847 | [0.720, 0.959] |
| `svm_linear` | **model** | 0.932 | 0.781 | 78.48 | 17.12 | 0.842 | [0.728, 0.954] |

**FAIL** — no model beat `max_tanimoto` (0.832) outside its confidence interval.

> **Underpowered — a FAIL here means "cannot tell", not "worse".** Only 28 actives in the test set (minimum 50 for a resolvable comparison). Every enrichment metric is computed from those actives alone, so the confidence intervals are wider than any plausible difference between methods. The Track B active count is capped by the decoy pool size — raising the pool is what fixes this, not changing the model.

### CHEMBL214 · A_measured · scaffold split

2969 train / 742 test · test actives 82.2% · random BEDROC reference `0.817`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.536 | 0.839 | 0.87 | 1.05 | 0.844 | [0.745, 0.915] |
| `descriptor_score` | baseline | 0.652 | 0.879 | 1.22 | 1.15 | 0.964 | [0.811, 0.964] |
| `max_tanimoto` | baseline | 0.976 | 0.994 | 1.22 | 1.22 | 1.000 | [1.000, 1.000] |
| `random_forest` | **model** | 0.989 | 0.998 | 1.22 | 1.22 | 1.000 | [1.000, 1.000] |
| `svm_linear` | **model** | 0.972 | 0.993 | 1.22 | 1.22 | 1.000 | [1.000, 1.000] |

**PASS** — random_forest beat the strongest baseline (`max_tanimoto` at 1.000).

> **Low information — do not read the above as a meaningful result.** The test set is 82% actives, so a random ranking already scores 0.817 BEDROC and EF@1% cannot exceed 1.22. There is almost no dynamic range left for a method to demonstrate anything. This happens when ChEMBL holds few measured inactives for the target; the Track B result is the informative one.

### CHEMBL214 · A_measured · random split

2969 train / 742 test · test actives 91.1% · random BEDROC reference `0.893`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.520 | 0.916 | 0.94 | 1.01 | 0.897 | [0.818, 0.969] |
| `descriptor_score` | baseline | 0.667 | 0.941 | 1.10 | 1.10 | 0.958 | [0.867, 0.985] |
| `max_tanimoto` | baseline | 0.977 | 0.997 | 1.10 | 1.10 | 1.000 | [1.000, 1.000] |
| `random_forest` | **model** | 0.997 | 1.000 | 1.10 | 1.10 | 1.000 | [1.000, 1.000] |
| `svm_linear` | **model** | 0.992 | 0.999 | 1.10 | 1.10 | 1.000 | [1.000, 1.000] |

**PASS** — random_forest beat the strongest baseline (`max_tanimoto` at 1.000).

> **Low information — do not read the above as a meaningful result.** The test set is 91% actives, so a random ranking already scores 0.893 BEDROC and EF@1% cannot exceed 1.10. There is almost no dynamic range left for a method to demonstrate anything. This happens when ChEMBL holds few measured inactives for the target; the Track B result is the informative one.

### CHEMBL214 · B_decoys · scaffold split

14802 train / 3700 test · test actives 0.9% · random BEDROC reference `0.055`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.537 | 0.011 | 0.00 | 1.14 | 0.060 | [0.021, 0.112] |
| `descriptor_score` | baseline | 0.564 | 0.012 | 51.43 | 10.29 | 0.538 | [0.026, 0.141] |
| `max_tanimoto` | baseline | 0.945 | 0.768 | 74.29 | 16.57 | 0.829 | [0.701, 0.935] |
| `random_forest` | **model** | 0.985 | 0.719 | 68.57 | 18.29 | 0.892 | [0.816, 0.954] |
| `svm_linear` | **model** | 0.989 | 0.775 | 74.29 | 18.29 | 0.901 | [0.826, 0.973] |

**FAIL** — no model beat `max_tanimoto` (0.829) outside its confidence interval.

> **Underpowered — a FAIL here means "cannot tell", not "worse".** Only 35 actives in the test set (minimum 50 for a resolvable comparison). Every enrichment metric is computed from those actives alone, so the confidence intervals are wider than any plausible difference between methods. The Track B active count is capped by the decoy pool size — raising the pool is what fixes this, not changing the model.

### CHEMBL214 · B_decoys · random split

14802 train / 3700 test · test actives 0.7% · random BEDROC reference `0.054`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.524 | 0.008 | 0.00 | 0.77 | 0.056 | [0.011, 0.118] |
| `descriptor_score` | baseline | 0.614 | 0.010 | 57.69 | 11.54 | 0.594 | [0.018, 0.170] |
| `max_tanimoto` | baseline | 0.958 | 0.821 | 80.77 | 17.69 | 0.854 | [0.695, 0.966] |
| `random_forest` | **model** | 0.993 | 0.811 | 88.46 | 19.23 | 0.926 | [0.828, 0.986] |
| `svm_linear` | **model** | 0.990 | 0.865 | 84.62 | 19.23 | 0.928 | [0.816, 0.992] |

**FAIL** — no model beat `max_tanimoto` (0.854) outside its confidence interval.

> **Underpowered — a FAIL here means "cannot tell", not "worse".** Only 26 actives in the test set (minimum 50 for a resolvable comparison). Every enrichment metric is computed from those actives alone, so the confidence intervals are wider than any plausible difference between methods. The Track B active count is capped by the decoy pool size — raising the pool is what fixes this, not changing the model.

## Interpretation notes

- The **scaffold** split is the real test; the **random** split is a diagnostic. A large gap between them measures how much analog bias the dataset carried.
- BEDROC's random reference is **not 0.5** — it depends on the active ratio (~0.12 at 10% actives, ~0.05 at 0.5%). Each table states its own reference.
- EF@1% saturates at `1/active_ratio`. On Track A that ceiling is low enough that methods tie there; Track B exists to make enrichment meaningful.
