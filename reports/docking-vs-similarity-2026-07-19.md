# Docking versus similarity search

ChEMBL ChEMBL_37 · seed `20260718` · generated 2026-07-19T06:17:44.535689+00:00

Both methods rank the identical compound set. Only targets whose setup reproduces a known crystallographic pose are eligible.

## MAO-B (2V5Z, redock 1.40 A)

1995 compounds, 145 active (7.3%) · 3 docking failures · 236.3 min

| method | BEDROC | 95% CI | EF@1% | EF@5% | ROC-AUC |
|---|---|---|---|---|---|
| similarity | 0.887 | [0.843, 0.924] | 13.8 | 12.9 | 0.953 |
| docking | 0.273 | [0.207, 0.340] | 3.4 | 2.6 | 0.773 |

### By similarity to training actives

The bin that matters is the first: compounds unlike anything known, where similarity search has no signal to work from.

| novelty bin | n | actives | similarity BEDROC | docking BEDROC |
|---|---|---|---|---|
| dissimilar (<0.5) | 1897 | 53 | 0.549 | 0.209 |
| close analog (>=0.5) | 98 | 92 | 0.997 | 0.963 |
