import { useState, type FormEvent } from 'react';
import {
  Callout,
  MeasuredValue,
  NoValue,
  Panel,
  SourceLink,
  WarningList,
} from '../components/evidence';

type TargetResult = {
  rcsb_id: string;
  title?: string | null;
  source_url: string;
};

type ResolvedTarget = {
  chembl_id: string;
  pref_name: string;
  organism?: string | null;
  target_type?: string | null;
  uniprot_accession?: string | null;
  match_score?: number | null;
  source_url: string;
};

type RankedLigand = {
  ligand: {
    chembl_id: string;
    name?: string | null;
    smiles: string;
    source_url: string;
  };
  descriptors: {
    molecular_weight: number;
    logp: number;
    tpsa: number;
    h_bond_donors: number;
    h_bond_acceptors: number;
  };
  activity: {
    pchembl_value: number;
    standard_type: string;
    measurement_count: number;
  } | null;
  score: number;
  notes: string[];
};

type WorkflowResponse = {
  query: string;
  ligand_query: string;
  resolved_target: ResolvedTarget | null;
  targets: TargetResult[];
  ligands: RankedLigand[];
  warnings: { stage: string; message: string }[];
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const EXAMPLE_QUERIES = ['dopamine D2 receptor', 'MAO-B', 'serotonin 1a receptor'];

export default function Home() {
  const [query, setQuery] = useState('dopamine D2 receptor');
  const [result, setResult] = useState<WorkflowResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function runWorkflow(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/workflows/run-lite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, limit: 8 }),
      });

      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }

      setResult((await response.json()) as WorkflowResponse);
    } catch (caught) {
      setResult(null);
      setError(caught instanceof Error ? caught.message : 'Workflow request failed');
    } finally {
      setIsLoading(false);
    }
  }

  const target = result?.resolved_target;

  return (
    <div className="space-y-5">
      <div className="max-w-3xl">
        <h1 className="text-2xl font-semibold text-ink">
          Known binders of a target, ordered by measured affinity
        </h1>
        <p className="mt-2 text-sm text-ink-2">
          This page retrieves what has already been measured — it makes no prediction.
          A query resolves to one ChEMBL target, and its binders are returned with the
          pChEMBL values that rank them.
        </p>
      </div>

      <Panel>
        <form onSubmit={runWorkflow}>
          <label className="block text-sm font-medium text-ink" htmlFor="query">
            Target query
          </label>
          <div className="mt-2 flex flex-col gap-2 sm:flex-row">
            <input
              id="query"
              className="min-h-10 flex-1 rounded-md border border-line-strong bg-plane px-3 text-sm text-ink outline-none focus:border-measured"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="dopamine D2 receptor"
              required
            />
            <button
              className="min-h-10 rounded-md bg-ink px-4 text-sm font-semibold text-plane transition-opacity hover:opacity-85 disabled:opacity-50"
              disabled={isLoading}
              type="submit"
            >
              {isLoading ? 'Running…' : 'Run workflow'}
            </button>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted">
            <span>Try:</span>
            {EXAMPLE_QUERIES.map((example) => (
              <button
                key={example}
                type="button"
                className="rounded border border-line px-2 py-0.5 text-ink-2 transition-colors hover:border-line-strong hover:text-ink"
                onClick={() => setQuery(example)}
              >
                {example}
              </button>
            ))}
            <span className="ml-auto font-mono">{apiBaseUrl}</span>
          </div>
        </form>
      </Panel>

      {error ? (
        <Callout tone="critical" title="Workflow request failed">
          {error}
        </Callout>
      ) : null}

      {result?.warnings.length ? <WarningList warnings={result.warnings} /> : null}

      {result ? (
        <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          {/* ChEMBL's search is fuzzy and can match on a stray word, so the
              resolved target is a checkpoint the reader is asked to clear
              before trusting anything downstream — not a caption. */}
          <Panel
            title="Resolved target"
            hint="Free-text search is fuzzy. Confirm this is the target you meant before reading the results below."
          >
            {target ? (
              <div>
                <SourceLink href={target.source_url}>
                  <span className="text-lg font-semibold text-measured-ink">
                    {target.pref_name}
                  </span>
                </SourceLink>
                <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm">
                  <dt className="text-muted">ChEMBL</dt>
                  <dd className="font-mono text-ink">{target.chembl_id}</dd>
                  {target.organism ? (
                    <>
                      <dt className="text-muted">Organism</dt>
                      <dd className="text-ink">{target.organism}</dd>
                    </>
                  ) : null}
                  {target.target_type ? (
                    <>
                      <dt className="text-muted">Type</dt>
                      <dd className="text-ink">{target.target_type}</dd>
                    </>
                  ) : null}
                  {target.uniprot_accession ? (
                    <>
                      <dt className="text-muted">UniProt</dt>
                      <dd className="font-mono text-ink">{target.uniprot_accession}</dd>
                    </>
                  ) : null}
                  {target.match_score != null ? (
                    <>
                      <dt className="text-muted">Match score</dt>
                      <dd className="tnum text-ink">{target.match_score.toFixed(1)}</dd>
                    </>
                  ) : null}
                </dl>
              </div>
            ) : (
              <p className="text-sm text-muted">
                No target resolved. The ligand set below cannot be attributed to a target.
              </p>
            )}
          </Panel>

          <Panel
            title="Structures"
            hint="RCSB PDB entries for the same target, as structural context."
            actions={
              <span className="tnum rounded border border-line px-2 py-0.5 text-xs text-ink-2">
                {result.targets.length}
              </span>
            }
          >
            {result.targets.length ? (
              <ul className="grid gap-1.5 sm:grid-cols-2">
                {result.targets.map((structure) => (
                  <li key={structure.rcsb_id}>
                    <a
                      className="block rounded-md border border-line px-3 py-2 transition-colors hover:border-measured"
                      href={structure.source_url}
                      rel="noreferrer"
                      target="_blank"
                    >
                      <span className="font-mono text-sm font-semibold text-ink">
                        {structure.rcsb_id}
                      </span>
                      {structure.title ? (
                        <span className="mt-0.5 block truncate text-xs text-muted">
                          {structure.title}
                        </span>
                      ) : null}
                    </a>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted">No structures returned.</p>
            )}
          </Panel>
        </div>
      ) : null}

      <Panel
        flush
        title="Ranked ligands"
        hint={
          target
            ? 'Ordered by measured affinity (pChEMBL, higher is stronger). Descriptors are reported alongside as raw values and are deliberately not the ranking signal — they describe drug-likeness and carry no information about binding this target.'
            : 'Run the workflow to retrieve known binders.'
        }
      >
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs text-muted">
                <th className="px-4 py-2 font-medium">#</th>
                <th className="px-4 py-2 font-medium">Ligand</th>
                <th className="px-4 py-2 font-medium">
                  Affinity
                  <span className="ml-1 font-normal text-muted">pChEMBL</span>
                </th>
                <th
                  className="border-l border-line px-4 py-2 font-medium"
                  colSpan={4}
                >
                  Descriptors
                  <span className="ml-1 font-normal normal-case">— not the ranking signal</span>
                </th>
                <th className="px-4 py-2 font-medium">Notes</th>
              </tr>
              <tr className="border-b border-line text-left text-[11px] text-muted">
                <th className="px-4 pb-2" />
                <th className="px-4 pb-2" />
                <th className="px-4 pb-2" />
                <th className="border-l border-line px-4 pb-2 font-normal">MW</th>
                <th className="px-4 pb-2 font-normal">LogP</th>
                <th className="px-4 pb-2 font-normal">TPSA</th>
                <th className="px-4 pb-2 font-normal">HBD / HBA</th>
                <th className="px-4 pb-2" />
              </tr>
            </thead>
            <tbody>
              {result?.ligands.length ? (
                result.ligands.map((item, index) => (
                  <tr
                    key={item.ligand.chembl_id}
                    className="border-b border-line last:border-0 hover:bg-plane"
                  >
                    <td className="tnum px-4 py-3 align-top text-muted">{index + 1}</td>
                    <td className="px-4 py-3 align-top">
                      <SourceLink href={item.ligand.source_url}>
                        <span className="font-medium text-ink">
                          {item.ligand.name ?? item.ligand.chembl_id}
                        </span>
                      </SourceLink>
                      <span className="mt-0.5 block max-w-[22rem] truncate font-mono text-xs text-muted">
                        {item.ligand.smiles}
                      </span>
                    </td>
                    <td className="px-4 py-3 align-top">
                      {item.activity ? (
                        <MeasuredValue
                          value={item.activity.pchembl_value.toFixed(2)}
                          detail={`${item.activity.standard_type} · n=${item.activity.measurement_count}`}
                        />
                      ) : (
                        <NoValue label="no measurement" />
                      )}
                    </td>
                    <td className="tnum border-l border-line px-4 py-3 align-top text-ink-2">
                      {item.descriptors.molecular_weight}
                    </td>
                    <td className="tnum px-4 py-3 align-top text-ink-2">
                      {item.descriptors.logp}
                    </td>
                    <td className="tnum px-4 py-3 align-top text-ink-2">
                      {item.descriptors.tpsa}
                    </td>
                    <td className="tnum px-4 py-3 align-top text-ink-2">
                      {item.descriptors.h_bond_donors} / {item.descriptors.h_bond_acceptors}
                    </td>
                    <td className="px-4 py-3 align-top text-xs text-muted">
                      {item.notes.join('; ') || '—'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="px-4 py-10 text-center text-sm text-muted" colSpan={8}>
                    No ranked ligands yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>

      {result?.ligands.length ? (
        <p className="text-xs text-muted">
          Ligands are drawn from the most-potent slice of ChEMBL for this target, so this
          set is biased toward the high-affinity tail rather than being a representative
          sample of known chemistry.
        </p>
      ) : null}
    </div>
  );
}
