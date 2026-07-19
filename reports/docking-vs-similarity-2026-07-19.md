# Docking versus similarity search

ChEMBL ChEMBL_37 · seed `20260718` · generated 2026-07-19T02:20:55.003536+00:00

Both methods rank the identical compound set. Only targets whose setup reproduces a known crystallographic pose are eligible.

## MAO-B (2V5Z, redock 1.40 A)

20 compounds, 8 active (40.0%) · 0 docking failures · 2.4 min

| method | BEDROC | 95% CI | EF@1% | EF@5% | ROC-AUC |
|---|---|---|---|---|---|
| similarity | 1.000 | [0.989, 1.000] | 2.5 | 2.5 | 0.990 |
| docking | 0.767 | [0.132, 1.000] | 2.5 | 2.5 | 0.844 |

### By similarity to training actives

The bin that matters is the first: compounds unlike anything known, where similarity search has no signal to work from.

| novelty bin | n | actives | similarity BEDROC | docking BEDROC |
|---|---|---|---|---|
| dissimilar (<0.5) | 13 | 1 | — | underpowered: 1 actives, need 30 |
| close analog (>=0.5) | 7 | 7 | — | underpowered: 7 actives, need 30 |
