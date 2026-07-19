# NeuroLab virtual-screening benchmark

ChEMBL release **ChEMBL_37** · seed `20260718` · generated 2026-07-19T01:30:57.125879+00:00

## Pre-registered criterion

A method is validated only if it beats **all three** baselines (`random`, `descriptor_score`, `max_tanimoto`) on **bedroc**, with the lower bound of its 95% bootstrap interval above the best baseline.

`max_tanimoto` is the bar that matters: beating only random proves nothing.

## Datasets

| target | track | actives | inactives |
|---|---|---|---|
| CHEMBL217 | A_measured | 3446 | 500 |
| CHEMBL217 | B_decoys | 502 | 90175 |
| CHEMBL2039 | A_measured | 1017 | 1278 |
| CHEMBL2039 | B_decoys | 502 | 85084 |
| CHEMBL214 | A_measured | 3361 | 350 |
| CHEMBL214 | B_decoys | 502 | 91453 |

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

72542 train / 18135 test · test actives 1.0% · random BEDROC reference `0.055`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.479 | 0.012 | 1.12 | 0.78 | 0.049 | [0.027, 0.072] |
| `descriptor_score` | baseline | 0.505 | 0.011 | 40.30 | 8.04 | 0.426 | [0.043, 0.096] |
| `max_tanimoto` | baseline | 0.988 | 0.907 | 89.00 | 18.43 | 0.927 | [0.894, 0.956] |
| `random_forest` | **model** | 0.989 | 0.901 | 80.60 | 19.44 | 0.959 | [0.939, 0.976] |
| `svm_linear` | **model** | 0.991 | 0.873 | 79.48 | 18.77 | 0.936 | [0.910, 0.957] |

**PASS** — random_forest beat the strongest baseline (`max_tanimoto` at 0.927).

### CHEMBL217 · B_decoys · random split

72542 train / 18135 test · test actives 0.5% · random BEDROC reference `0.053`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.502 | 0.005 | 0.00 | 0.61 | 0.037 | [0.017, 0.061] |
| `descriptor_score` | baseline | 0.530 | 0.006 | 45.54 | 9.09 | 0.468 | [0.038, 0.104] |
| `max_tanimoto` | baseline | 0.987 | 0.937 | 93.11 | 18.98 | 0.954 | [0.917, 0.988] |
| `random_forest` | **model** | 0.990 | 0.904 | 91.08 | 19.39 | 0.956 | [0.921, 0.981] |
| `svm_linear` | **model** | 0.977 | 0.887 | 90.07 | 18.38 | 0.920 | [0.868, 0.966] |

**FAIL** — no model beat `max_tanimoto` (0.954) outside its confidence interval.

### CHEMBL2039 · A_measured · scaffold split

1836 train / 459 test · test actives 31.6% · random BEDROC reference `0.316`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.518 | 0.353 | 1.27 | 1.24 | 0.408 | [0.267, 0.565] |
| `descriptor_score` | baseline | 0.585 | 0.362 | 1.90 | 1.38 | 0.441 | [0.243, 0.502] |
| `max_tanimoto` | baseline | 0.794 | 0.695 | 3.17 | 3.03 | 0.878 | [0.791, 0.939] |
| `random_forest` | **model** | 0.919 | 0.851 | 3.17 | 3.03 | 0.948 | [0.898, 0.981] |
| `svm_linear` | **model** | 0.848 | 0.730 | 3.17 | 2.75 | 0.845 | [0.734, 0.917] |

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

68469 train / 17117 test · test actives 0.4% · random BEDROC reference `0.052`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.518 | 0.004 | 0.00 | 0.58 | 0.043 | [0.019, 0.073] |
| `descriptor_score` | baseline | 0.672 | 0.007 | 65.28 | 13.04 | 0.661 | [0.059, 0.151] |
| `max_tanimoto` | baseline | 0.962 | 0.831 | 84.14 | 17.39 | 0.874 | [0.797, 0.940] |
| `random_forest` | **model** | 0.974 | 0.788 | 82.69 | 18.26 | 0.899 | [0.837, 0.955] |
| `svm_linear` | **model** | 0.947 | 0.579 | 73.99 | 16.81 | 0.810 | [0.728, 0.881] |

**FAIL** — no model beat `max_tanimoto` (0.874) outside its confidence interval.

### CHEMBL2039 · B_decoys · random split

68469 train / 17117 test · test actives 0.6% · random BEDROC reference `0.053`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.502 | 0.006 | 0.00 | 0.61 | 0.037 | [0.017, 0.061] |
| `descriptor_score` | baseline | 0.751 | 0.012 | 82.91 | 16.56 | 0.836 | [0.079, 0.160] |
| `max_tanimoto` | baseline | 0.977 | 0.932 | 93.02 | 18.78 | 0.941 | [0.895, 0.981] |
| `random_forest` | **model** | 0.995 | 0.917 | 93.02 | 19.39 | 0.960 | [0.920, 0.986] |
| `svm_linear` | **model** | 0.977 | 0.855 | 86.96 | 18.18 | 0.915 | [0.866, 0.956] |

**FAIL** — no model beat `max_tanimoto` (0.941) outside its confidence interval.

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

73564 train / 18391 test · test actives 1.0% · random BEDROC reference `0.055`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.478 | 0.012 | 1.14 | 0.69 | 0.047 | [0.027, 0.072] |
| `descriptor_score` | baseline | 0.547 | 0.012 | 46.83 | 9.37 | 0.492 | [0.052, 0.107] |
| `max_tanimoto` | baseline | 0.992 | 0.944 | 92.53 | 19.19 | 0.962 | [0.934, 0.982] |
| `random_forest` | **model** | 0.998 | 0.937 | 87.96 | 19.88 | 0.977 | [0.964, 0.987] |
| `svm_linear` | **model** | 0.996 | 0.888 | 81.10 | 19.42 | 0.954 | [0.936, 0.974] |

**PASS** — random_forest beat the strongest baseline (`max_tanimoto` at 0.962).

### CHEMBL214 · B_decoys · random split

73564 train / 18391 test · test actives 0.5% · random BEDROC reference `0.053`

| method | | ROC-AUC | PR-AUC | EF@1% | EF@5% | BEDROC | BEDROC 95% CI |
|---|---|---|---|---|---|---|---|
| `random` | baseline | 0.501 | 0.005 | 0.00 | 0.63 | 0.038 | [0.019, 0.061] |
| `descriptor_score` | baseline | 0.559 | 0.006 | 47.35 | 9.47 | 0.487 | [0.038, 0.108] |
| `max_tanimoto` | baseline | 0.991 | 0.951 | 94.69 | 19.15 | 0.959 | [0.921, 0.993] |
| `random_forest` | **model** | 0.996 | 0.941 | 93.64 | 19.78 | 0.977 | [0.949, 0.995] |
| `svm_linear` | **model** | 0.995 | 0.921 | 93.64 | 19.57 | 0.964 | [0.932, 0.989] |

**FAIL** — no model beat `max_tanimoto` (0.959) outside its confidence interval.

## Interpretation notes

- The **scaffold** split is the real test; the **random** split is a diagnostic. A large gap between them measures how much analog bias the dataset carried.
- BEDROC's random reference is **not 0.5** — it depends on the active ratio (~0.12 at 10% actives, ~0.05 at 0.5%). Each table states its own reference.
- EF@1% saturates at `1/active_ratio`. On Track A that ceiling is low enough that methods tie there; Track B exists to make enrichment meaningful.
