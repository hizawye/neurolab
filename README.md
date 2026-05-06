# NeuroLab

NeuroLab is a source-available drug discovery workbench. The current MVP focuses on one runnable local workflow:

```text
target search -> ligand lookup -> RDKit descriptors -> transparent ranking
```

The broader roadmap includes docking, ADMET integrations, workflow orchestration, and simulation, but those are not production features yet.

## Current Capabilities

- FastAPI backend with typed endpoints for health, target search, ligand search, and lite workflow execution.
- RCSB Search API integration for target candidates.
- PubChem lookup for ligand candidates, with a small query expansion for common neuroscience targets.
- RDKit descriptor calculation for molecular weight, LogP, TPSA, hydrogen bond donors, and hydrogen bond acceptors.
- Deterministic ranking score for early BBB-oriented screening.
- React/Vite frontend with a runnable workflow dashboard.

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

Returns RCSB target candidates.

### `GET /ligands/search?query=selegiline&limit=8`

Returns PubChem ligand candidates.

### `POST /workflows/run-lite`

Runs the MVP workflow.

```json
{
  "query": "MAO-B inhibitor",
  "limit": 8
}
```

Response includes targets, ranked ligands, descriptors, score notes, and non-fatal warnings.

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
3. Add ChEMBL ligand search as a second source.
4. Add docking with Vina/Smina and artifact storage.
5. Add ADMET/toxicity integrations.
6. Add molecule visualization and editing once real result artifacts exist.

## License

Business Source License 1.1, non-converting. Commercial use requires a separate license from the licensor. See [LICENSE](LICENSE).
