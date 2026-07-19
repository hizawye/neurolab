# NeuroLab

NeuroLab is a source-available drug discovery workbench. The current MVP focuses on one runnable local workflow:

```text
target resolution -> measured binders (ChEMBL) -> RDKit descriptors -> affinity ranking
                  \-> PDB structures (RCSB)
```

The broader roadmap includes docking, ADMET integrations, workflow orchestration, and simulation, but those are not production features yet.

## Current Capabilities

- FastAPI backend with typed endpoints for health, target search, ligand search, and lite workflow execution.
- ChEMBL target resolution: free text (e.g. `dopamine D2 receptor`) resolves to a single
  ChEMBL target, preferring human single-protein entries, with its UniProt accession.
- ChEMBL bioactivity lookup: ligands are compounds with *measured* binding affinity against
  that resolved target, so the target genuinely selects the ligand set.
- Binding assays only (`Ki`, `Kd`, `IC50`); functional readouts like `EC50` are excluded so a
  single ranking never mixes occupancy with downstream response.
- Repeat measurements of the same compound collapse to their **median** pChEMBL, so ranking
  follows consensus rather than the most favourable outlier.
- RCSB Search API for PDB structures of the same target, as structural context.
- RDKit descriptor calculation for molecular weight, LogP, TPSA, hydrogen bond donors, and hydrogen bond acceptors.
- React/Vite frontend with a runnable workflow dashboard.

## How ranking works

Ligands are ordered by **measured affinity** (pChEMBL, i.e. -log10 molar potency — higher is
stronger). Descriptors are reported alongside as raw values, which they are; they are
deliberately **not** the ranking signal, because molecular weight, LogP and TPSA describe
drug-likeness and carry no information about whether a compound binds a given target.

Screening adds two *predictions*, each with its own independently measured track record and
each kept in its own field so that one method's validation never vouches for another's:
similarity to known actives (activity) and a trained model (BBB penetration). Measured values
are never merged into a predicted field.

## Validation harness

`backend/science/` measures whether a scoring method actually predicts binding, rather
than assuming it does. Nothing in it runs in a request path, and its dependencies
(scikit-learn, scipy, pandas) live in the `dev` group rather than the runtime set — the
API server never imports them. It needs `uv sync --group dev`.

```bash
cd backend
uv run python -m backend.science.cli --panel          # full CNS panel
uv run python -m backend.science.cli --target CHEMBL2039
NEUROLAB_OFFLINE=1 uv run python -m backend.science.cli --panel   # reproduce from cache
```

Reports land in `reports/` as markdown plus machine-readable JSON, stamped with the ChEMBL
release and the seed.

**The pre-registered criterion**, fixed before the first run: a method is validated only if
it beats *all three* baselines — random, the existing descriptor score, and nearest-neighbour
Tanimoto similarity — on BEDROC, with its bootstrap lower bound above the best baseline.

`max_tanimoto` is the bar that matters. Many published QSAR models never beat plain
similarity search, and reporting a win over random alone is the most common way this kind of
work misleads. If a model loses to similarity, that is the finding and it is reported as one.

Design decisions that make the numbers mean something:

- **Scaffold split** (Bemis-Murcko, DeepChem convention: large scaffold groups fill train,
  test gets rare and singleton scaffolds). ChEMBL actives arrive as congeneric series, so a
  random split puts near-identical analogs on both sides and inflates every metric. The
  random split is still reported beside it — the gap measures the analog bias.
- **Two dataset tracks, never pooled.** Track A inactives are *measured*. Track B pads with
  property-matched decoys that are *presumed* inactive, needed because enrichment metrics are
  meaningless at Track A's class ratio.
- **The 5-7 pChEMBL band is discarded.** Between-lab measurement error is comparable to that
  window's width, so those labels would be noise.
- **Median across repeat measurements**, not max, so ranking follows consensus rather than
  the most flattering outlier.
- **BEDROC's random reference is not 0.5.** It depends on the active ratio (~0.12 at 10%
  actives, ~0.05 at 0.5%). Each report states its own reference.

## BBB prediction

The developability score was benchmarked against B3DB (7,807 compounds with measured
brain-penetration outcomes) and **lost to TPSA alone** — ROC-AUC 0.799 against 0.823, with a
paired-bootstrap difference of [-0.037, -0.009], entirely below zero. Its molecular weight,
LogP and hydrogen-bond terms were actively harmful rather than merely redundant.

It was replaced by a random forest over ECFP4 (ROC-AUC 0.929, CI [0.916, 0.939]), trained by:

```bash
cd backend
uv run python -m backend.science.train_bbb
```

The artifact ships with a sidecar JSON recording its held-out numbers and the baselines it
beat; the API refuses to load a model without that record, so a prediction can always be
traced to the evaluation justifying it.

### Known limitations

- ChEMBL target search is fuzzy and can match on a stray word. The resolved target is shown
  in the UI so it can be verified, and low-relevance matches raise a warning — but the
  warning is a heuristic threshold, not a correctness guarantee. **Always check the resolved
  target before trusting a result set.**
- Ligands are drawn from the most-potent slice of ChEMBL for the target, so the set is biased
  toward the high-affinity tail rather than being a representative sample of known chemistry.

## Requirements

- Node.js 18+
- npm 9+
- uv
- Python 3.10+

Install uv if it is not already available:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Development

Install frontend dependencies:

```bash
npm install
```

Install backend dependencies and run tests:

```bash
cd backend
uv sync --group dev
uv run pytest
```

Run the backend:

```bash
cd backend
uv run uvicorn backend.main:app --reload --app-dir ..
```

Run the frontend in another shell:

```bash
npm run dev
```

Open:

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs

## API

### `GET /health`

Returns backend health.

### `GET /targets/search?query=MAO-B&limit=10`

Returns RCSB PDB structure candidates.

### `GET /ligands/search?query=dopamine D2 receptor&limit=8`

Resolves the query to a ChEMBL target and returns its known binders, most potent first,
with descriptors and measured affinity. Responds 404 if no target matches.

### `POST /screen`

Scores user-supplied compounds against a target's known binders. This is the endpoint that
makes a prediction — the workflow endpoint below only retrieves what is already known.

```json
{
  "target_query": "dopamine D2 receptor",
  "smiles": ["O=C1NC=NN1c1ccc(cc1)C1CCN(CCCC(=O)c2ccc(F)cc2)CC1"],
  "reference_limit": 100
}
```

Returns each compound's predicted similarity to the nearest known active, which reference it
matched, its descriptors, and — when the compound already has ChEMBL data — its *measured*
affinity, kept in a separate field so a measurement is never presented as a prediction. Every
response carries the scoring method's held-out benchmark numbers.

### `POST /workflows/run-lite`

Runs the MVP workflow.

```json
{
  "query": "dopamine D2 receptor",
  "limit": 8
}
```

Response includes the resolved ChEMBL target, RCSB structures, ligands ranked by measured
affinity with their pChEMBL evidence, descriptors, score notes, and non-fatal warnings.

## Verification

```bash
npm run build
npm run lint
npm test
```

## Docker

`docker/docker-compose.yml` currently provides local PostgreSQL and pgAdmin only. The MVP backend does not persist results yet. Full backend/frontend/worker Docker deployment is planned after storage and orchestration are added.

## Roadmap

Next phases:

1. Persist workflow runs and results in PostgreSQL.
2. Add Redis/Celery for background job execution and progress logs.
3. Add docking with Vina/Smina and artifact storage.
4. Add ADMET/toxicity integrations.
5. Add molecule visualization and editing once real result artifacts exist.

## License

Business Source License 1.1, non-converting. Commercial use requires a separate license from the licensor. See [LICENSE](LICENSE).
