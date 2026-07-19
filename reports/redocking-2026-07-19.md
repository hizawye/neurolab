# Redocking validation

Generated 2026-07-19T02:04:26.476062+00:00 · seed `20260718` · success threshold 2.0 A

Each ligand is rebuilt from SMILES with no crystal information, docked back into its own structure, and compared to the crystallographic pose. Cofactors are kept in the receptor; waters are removed.

| target | PDB | ligand | top affinity | crystal-pose affinity | top RMSD | best RMSD | result |
|---|---|---|---|---|---|---|---|
| MAO-B | 2V5Z | SAG | -10.09 | -9.21 | 1.40 A | 0.64 A | **PASS** |
| Dopamine D2 receptor | 6CM4 | 8NU | -11.86 | -11.04 | 0.62 A | 0.62 A | **PASS** |
| 5-HT1A receptor | 7E2Z | 9SC | -8.64 | -7.56 | 6.54 A | 5.53 A | **FAIL** (scoring) |

Top-pose RMSD is the number that matters: it asks whether the scoring function *ranked* the correct pose first. A good best-pose RMSD with a poor top-pose RMSD means the search found the right answer and the scoring failed to recognise it.

The crystal-pose affinity column scores the experimental pose without moving it, which separates two failures that otherwise look identical:

- **scoring failure** — docking found a pose it scores *better* than the crystallographic truth. The search worked; the scoring function is wrong. More sampling will not help.
- **search failure** — nothing sampled scored as well as the crystal pose, so the search never reached it. More exhaustiveness or a larger box might.
