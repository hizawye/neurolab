import { useState, type FormEvent } from 'react';

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

  return (
    <div className="space-y-6">
      <section className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <div className="space-y-5">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-teal-700">
              Lite MVP
            </p>
            <h2 className="mt-2 text-3xl font-semibold text-slate-950">
              Target search, ligand lookup, RDKit descriptors, and ranking.
            </h2>
          </div>
          <form className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm" onSubmit={runWorkflow}>
            <label className="block text-sm font-medium text-slate-700" htmlFor="query">
              Discovery query
            </label>
            <div className="mt-2 flex flex-col gap-3 sm:flex-row">
              <input
                id="query"
                className="min-h-11 flex-1 rounded-md border border-slate-300 px-3 text-slate-950 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="dopamine D2 receptor"
                required
              />
              <button
                className="min-h-11 rounded-md bg-teal-700 px-4 font-semibold text-white transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                disabled={isLoading}
                type="submit"
              >
                {isLoading ? 'Running...' : 'Run workflow'}
              </button>
            </div>
            <p className="mt-3 text-sm text-slate-500">
              Backend: {apiBaseUrl}
            </p>
          </form>

          {error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
              {error}
            </div>
          ) : null}
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          {result?.resolved_target ? (
            <div className="mb-4 rounded-md border border-teal-200 bg-teal-50 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-teal-800">
                Resolved target
              </p>
              <a
                className="mt-1 block font-semibold text-slate-950 hover:text-teal-800"
                href={result.resolved_target.source_url}
                rel="noreferrer"
                target="_blank"
              >
                {result.resolved_target.pref_name}
              </a>
              <p className="mt-1 text-xs text-slate-600">
                {result.resolved_target.chembl_id}
                {result.resolved_target.organism ? ` · ${result.resolved_target.organism}` : ''}
                {result.resolved_target.uniprot_accession
                  ? ` · UniProt ${result.resolved_target.uniprot_accession}`
                  : ''}
              </p>
            </div>
          ) : null}
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-lg font-semibold text-slate-950">Structures</h3>
            <span className="rounded-md bg-slate-100 px-2 py-1 text-sm text-slate-600">
              {result?.targets.length ?? 0} hits
            </span>
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {result?.targets.length ? (
              result.targets.map((target) => (
                <a
                  className="rounded-md border border-slate-200 p-3 text-sm transition hover:border-teal-500 hover:bg-teal-50"
                  href={target.source_url}
                  key={target.rcsb_id}
                  rel="noreferrer"
                  target="_blank"
                >
                  <span className="font-semibold text-slate-950">{target.rcsb_id}</span>
                  <span className="mt-1 block text-slate-500">RCSB structure</span>
                </a>
              ))
            ) : (
              <p className="text-sm text-slate-500">Run the workflow to populate target candidates.</p>
            )}
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 p-4">
          <h3 className="text-lg font-semibold text-slate-950">Ranked ligands</h3>
          <p className="text-sm text-slate-500">
            {result?.resolved_target ? (
              <>
                Known binders of{' '}
                <a
                  className="font-medium text-teal-700 hover:text-teal-900"
                  href={result.resolved_target.source_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  {result.resolved_target.pref_name}
                </a>
                , ordered by measured affinity (pChEMBL). Descriptor score is a
                developability read-out, not the ranking signal.
              </>
            ) : (
              'Ordered by measured binding affinity from ChEMBL.'
            )}
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Ligand</th>
                <th className="px-4 py-3">Affinity</th>
                <th className="px-4 py-3">Score</th>
                <th className="px-4 py-3">MW</th>
                <th className="px-4 py-3">LogP</th>
                <th className="px-4 py-3">TPSA</th>
                <th className="px-4 py-3">HBD/HBA</th>
                <th className="px-4 py-3">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {result?.ligands.length ? (
                result.ligands.map((item) => (
                  <tr key={item.ligand.chembl_id}>
                    <td className="px-4 py-3">
                      <a
                        className="font-semibold text-teal-700 hover:text-teal-900"
                        href={item.ligand.source_url}
                        rel="noreferrer"
                        target="_blank"
                      >
                        {item.ligand.name ?? item.ligand.chembl_id}
                      </a>
                      <span className="block max-w-72 truncate text-xs text-slate-500">
                        {item.ligand.smiles}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {item.activity ? (
                        <>
                          <span className="font-semibold text-slate-950">
                            {item.activity.pchembl_value.toFixed(2)}
                          </span>
                          <span className="block text-xs text-slate-500">
                            {item.activity.standard_type} &middot; n={item.activity.measurement_count}
                          </span>
                        </>
                      ) : (
                        <span className="text-slate-400">&mdash;</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-700">{item.score}</td>
                    <td className="px-4 py-3">{item.descriptors.molecular_weight}</td>
                    <td className="px-4 py-3">{item.descriptors.logp}</td>
                    <td className="px-4 py-3">{item.descriptors.tpsa}</td>
                    <td className="px-4 py-3">
                      {item.descriptors.h_bond_donors}/{item.descriptors.h_bond_acceptors}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{item.notes.join('; ') || 'Within baseline range'}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="px-4 py-8 text-center text-slate-500" colSpan={8}>
                    No ranked ligands yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {result?.warnings.length ? (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          {result.warnings.map((warning) => (
            <p key={`${warning.stage}-${warning.message}`}>
              <span className="font-semibold">{warning.stage}:</span> {warning.message}
            </p>
          ))}
        </section>
      ) : null}
    </div>
  );
}
