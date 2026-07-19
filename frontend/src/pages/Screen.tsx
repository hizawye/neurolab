import { useState, type FormEvent } from 'react';

type PredictedActivity = {
  similarity: number;
  nearest_active_smiles: string;
  n_references: number;
};

type ScreenedCompound = {
  query_smiles: string;
  descriptors: {
    molecular_weight: number;
    logp: number;
    tpsa: number;
    h_bond_donors: number;
    h_bond_acceptors: number;
  } | null;
  predicted: PredictedActivity | null;
  measured: { pchembl_value: number; standard_type: string; measurement_count: number } | null;
  bbb_probability: number | null;
  notes: string[];
};

type ScreenResponse = {
  resolved_target: { chembl_id: string; pref_name: string; source_url: string } | null;
  method: {
    method: string;
    benchmark: string;
    bedroc_range: number[];
    ef_1pct_range: number[];
    roc_auc_range: number[];
    n_reference_actives: number;
    caveat: string;
    best_for: string;
    weak_for: string;
    measured_coverage: string;
    bbb: {
      method: string;
      dataset: string;
      roc_auc: number;
      roc_auc_ci: number[];
      beats: Record<string, number>;
      caveat: string;
    } | null;
  };
  results: ScreenedCompound[];
  warnings: { stage: string; message: string }[];
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const EXAMPLE_SMILES = [
  'O=C1NC=NN1c1ccc(cc1)C1CCN(CCCC(=O)c2ccc(F)cc2)CC1',
  'CN1C(=O)CN=C(c2ccccc2)c2cc(Cl)ccc21',
  'CC(=O)Oc1ccccc1C(=O)O',
  'CN1C=NC2=C1C(=O)N(C)C(=O)N2C',
].join('\n');

/** Similarity is a prioritisation signal, not a probability — band it accordingly. */
function band(similarity: number): { label: string; className: string } {
  if (similarity >= 0.7) return { label: 'close analog', className: 'bg-teal-100 text-teal-900' };
  if (similarity >= 0.4) return { label: 'related scaffold', className: 'bg-sky-100 text-sky-900' };
  if (similarity >= 0.2) return { label: 'weak resemblance', className: 'bg-amber-100 text-amber-900' };
  return { label: 'unlike known actives', className: 'bg-slate-100 text-slate-600' };
}

export default function Screen() {
  const [targetQuery, setTargetQuery] = useState('dopamine D2 receptor');
  const [smilesText, setSmilesText] = useState(EXAMPLE_SMILES);
  const [result, setResult] = useState<ScreenResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function runScreen(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    const smiles = smilesText
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);

    try {
      const response = await fetch(`${apiBaseUrl}/screen`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_query: targetQuery, smiles }),
      });

      if (!response.ok) {
        const detail = await response.json().catch(() => null);
        throw new Error(detail?.detail ?? `API returned ${response.status}`);
      }

      setResult((await response.json()) as ScreenResponse);
    } catch (caught) {
      setResult(null);
      setError(caught instanceof Error ? caught.message : 'Screen request failed');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-teal-700">
          Virtual screening
        </p>
        <h2 className="mt-2 text-3xl font-semibold text-slate-950">
          Score compounds against a target's known binders.
        </h2>
        <p className="mt-2 max-w-3xl text-sm text-slate-600">
          Unlike the workflow view, which retrieves what is already known to bind, this makes a
          prediction that can be wrong. The scoring method was chosen by benchmark, not by
          preference — its measured track record is shown with every result.
        </p>
      </div>

      <form className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm" onSubmit={runScreen}>
        <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
          <div>
            <label className="block text-sm font-medium text-slate-700" htmlFor="target">
              Target
            </label>
            <input
              id="target"
              className="mt-2 min-h-11 w-full rounded-md border border-slate-300 px-3 text-slate-950 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
              value={targetQuery}
              onChange={(event) => setTargetQuery(event.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700" htmlFor="smiles">
              Compounds (one SMILES per line)
            </label>
            <textarea
              id="smiles"
              className="mt-2 min-h-32 w-full rounded-md border border-slate-300 p-3 font-mono text-xs text-slate-950 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
              value={smilesText}
              onChange={(event) => setSmilesText(event.target.value)}
              required
            />
          </div>
        </div>
        <button
          className="mt-4 min-h-11 rounded-md bg-teal-700 px-4 font-semibold text-white transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          disabled={isLoading}
          type="submit"
        >
          {isLoading ? 'Screening...' : 'Run screen'}
        </button>
      </form>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>
      ) : null}

      {result ? (
        <>
          <section className="rounded-lg border border-teal-200 bg-teal-50 p-4">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-teal-900">
              Method and its track record
            </h3>
            <p className="mt-2 text-sm text-slate-800">
              {result.method.method}, scored against{' '}
              <span className="font-semibold">{result.method.n_reference_actives}</span> known actives of{' '}
              <a
                className="font-semibold text-teal-800 underline"
                href={result.resolved_target?.source_url}
                rel="noreferrer"
                target="_blank"
              >
                {result.resolved_target?.pref_name}
              </a>
              .
            </p>
            <p className="mt-2 text-sm text-slate-700">
              Held-out benchmark ({result.method.benchmark}): BEDROC{' '}
              <span className="font-mono">
                {result.method.bedroc_range[0].toFixed(3)}–{result.method.bedroc_range[1].toFixed(3)}
              </span>
              , EF@1%{' '}
              <span className="font-mono">
                {result.method.ef_1pct_range[0].toFixed(0)}–{result.method.ef_1pct_range[1].toFixed(0)}×
              </span>
              , ROC-AUC{' '}
              <span className="font-mono">
                {result.method.roc_auc_range[0].toFixed(3)}–{result.method.roc_auc_range[1].toFixed(3)}
              </span>
              .
            </p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <p className="rounded-md bg-white/70 p-2 text-xs text-slate-700">
                <span className="font-semibold text-teal-900">Good for: </span>
                {result.method.best_for}
              </p>
              <p className="rounded-md bg-white/70 p-2 text-xs text-slate-700">
                <span className="font-semibold text-amber-800">Weak for: </span>
                {result.method.weak_for}
              </p>
            </div>
            <p className="mt-2 text-xs text-slate-600">{result.method.caveat}</p>
            <p className="mt-1 text-xs text-slate-600">{result.method.measured_coverage}</p>
            {result.method.bbb ? (
              <div className="mt-3 border-t border-teal-200 pt-3">
                <p className="text-sm text-slate-800">
                  <span className="font-semibold">BBB column: </span>
                  {result.method.bbb.method}. Held-out ROC-AUC{' '}
                  <span className="font-mono">{result.method.bbb.roc_auc.toFixed(3)}</span>{' '}
                  <span className="font-mono text-xs">
                    [{result.method.bbb.roc_auc_ci[0].toFixed(3)}, {result.method.bbb.roc_auc_ci[1].toFixed(3)}]
                  </span>{' '}
                  on {result.method.bbb.dataset}, beating TPSA alone (
                  {result.method.bbb.beats.tpsa_only?.toFixed(3)}) and the previous hand-tuned
                  score ({result.method.bbb.beats.hand_tuned_descriptor_score?.toFixed(3)}).
                </p>
                <p className="mt-1 text-xs text-slate-600">{result.method.bbb.caveat}</p>
              </div>
            ) : null}
          </section>

          <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Compound</th>
                    <th className="px-4 py-3">Predicted</th>
                    <th className="px-4 py-3">Measured</th>
                    <th className="px-4 py-3">BBB</th>
                    <th className="px-4 py-3">Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {result.results.map((row, index) => {
                    const tier = row.predicted ? band(row.predicted.similarity) : null;
                    return (
                      <tr key={`${row.query_smiles}-${index}`}>
                        <td className="px-4 py-3">
                          <span className="block max-w-80 truncate font-mono text-xs text-slate-700">
                            {row.query_smiles}
                          </span>
                          {row.descriptors ? (
                            <span className="mt-1 block text-xs text-slate-500">
                              MW {row.descriptors.molecular_weight} · LogP {row.descriptors.logp} · TPSA{' '}
                              {row.descriptors.tpsa}
                            </span>
                          ) : (
                            <span className="mt-1 block text-xs text-red-600">unparseable</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {row.predicted && tier ? (
                            <>
                              <span className="font-semibold text-slate-950">
                                {row.predicted.similarity.toFixed(3)}
                              </span>
                              <span
                                className={`ml-2 rounded px-2 py-0.5 text-xs font-medium ${tier.className}`}
                              >
                                {tier.label}
                              </span>
                            </>
                          ) : (
                            <span className="text-slate-400">&mdash;</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {row.measured ? (
                            <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-900">
                              pChEMBL {row.measured.pchembl_value} ({row.measured.standard_type})
                            </span>
                          ) : (
                            <span className="text-xs text-slate-400">no measurement</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-slate-700">
                          {row.bbb_probability !== null ? (
                            <>
                              <span className="font-semibold text-slate-950">
                                {row.bbb_probability.toFixed(2)}
                              </span>
                              <span className="ml-2 text-xs text-slate-500">
                                {row.bbb_probability >= 0.5 ? 'likely crosses' : 'likely excluded'}
                              </span>
                            </>
                          ) : (
                            <span className="text-slate-400">&mdash;</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-600">
                          {row.notes.join('; ') || '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          {result.warnings.length ? (
            <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              {result.warnings.map((warning) => (
                <p key={`${warning.stage}-${warning.message}`}>
                  <span className="font-semibold">{warning.stage}:</span> {warning.message}
                </p>
              ))}
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
