import { useState, type FormEvent } from 'react';
import {
  Callout,
  EvidenceMark,
  IntervalBar,
  MeasuredValue,
  NoValue,
  Panel,
  PredictedValue,
  SourceLink,
  WarningList,
} from '../components/evidence';

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
    targets_tested: number;
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
function band(similarity: number): string {
  if (similarity >= 0.7) return 'close analog';
  if (similarity >= 0.4) return 'related scaffold';
  if (similarity >= 0.2) return 'weak resemblance';
  return 'unlike known actives';
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

  const compoundCount = smilesText.split('\n').filter((line) => line.trim()).length;
  const method = result?.method;
  const spread = `across ${method?.targets_tested ?? 3} targets`;

  return (
    <div className="space-y-5">
      <div className="max-w-3xl">
        <h1 className="text-2xl font-semibold text-ink">
          Score compounds against a target's known binders
        </h1>
        <p className="mt-2 text-sm text-ink-2">
          Unlike the workflow view, which retrieves what is already known, this page makes
          a prediction that can be wrong. The scoring method was chosen by benchmark
          rather than preference, and its measured track record is shown with every result.
        </p>
      </div>

      <Panel>
        <form onSubmit={runScreen}>
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
            <div>
              <label className="block text-sm font-medium text-ink" htmlFor="target">
                Target
              </label>
              <input
                id="target"
                className="mt-2 min-h-10 w-full rounded-md border border-line-strong bg-plane px-3 text-sm text-ink outline-none focus:border-measured"
                value={targetQuery}
                onChange={(event) => setTargetQuery(event.target.value)}
                required
              />
              <p className="mt-2 text-xs text-muted">
                Predictions exist only for targets with known ChEMBL actives to compare
                against.
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-ink" htmlFor="smiles">
                Compounds
                <span className="ml-2 font-normal text-muted">one SMILES per line</span>
              </label>
              <textarea
                id="smiles"
                className="mt-2 min-h-28 w-full rounded-md border border-line-strong bg-plane p-3 font-mono text-xs text-ink outline-none focus:border-measured"
                value={smilesText}
                onChange={(event) => setSmilesText(event.target.value)}
                required
              />
              <p className="tnum mt-2 text-xs text-muted">{compoundCount} compounds</p>
            </div>
          </div>
          <button
            className="mt-4 min-h-10 rounded-md bg-ink px-4 text-sm font-semibold text-plane transition-opacity hover:opacity-85 disabled:opacity-50"
            disabled={isLoading}
            type="submit"
          >
            {isLoading ? 'Screening…' : 'Run screen'}
          </button>
        </form>
      </Panel>

      {error ? (
        <Callout tone="critical" title="Screen request failed">
          {error}
        </Callout>
      ) : null}

      {result?.warnings.length ? <WarningList warnings={result.warnings} /> : null}

      {result && method ? (
        <>
          <Panel
            title="The method, and how well it is known to work"
            hint="No score is shown without the benchmark that justifies it."
          >
            <p className="text-sm text-ink-2">
              <span className="font-medium text-ink">{method.method}</span>, scored against{' '}
              <span className="tnum font-medium text-ink">{method.n_reference_actives}</span>{' '}
              known actives of{' '}
              <SourceLink href={result.resolved_target?.source_url}>
                <span className="font-medium text-measured-ink">
                  {result.resolved_target?.pref_name}
                </span>
              </SourceLink>
              .
            </p>

            {/* These three spans are the spread across the three benchmarked
                targets, not confidence intervals — the distinction is stated on
                each bar so the reader is not left to guess which it is. */}
            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              <IntervalBar
                label="BEDROC (α=20)"
                kind={spread}
                lo={method.bedroc_range[0]}
                hi={method.bedroc_range[1]}
              />
              <IntervalBar
                label="Enrichment @ 1%"
                kind={spread}
                lo={method.ef_1pct_range[0]}
                hi={method.ef_1pct_range[1]}
                domainMin={0}
                domainMax={100}
                format={(n) => `${n.toFixed(1)}×`}
              />
              <IntervalBar
                label="ROC-AUC"
                kind={`${spread} · 0.5 = random`}
                lo={method.roc_auc_range[0]}
                hi={method.roc_auc_range[1]}
                domainMin={0.5}
                domainMax={1}
              />
            </div>
            <p className="mt-2 text-xs text-muted">
              Held-out {method.benchmark}. BEDROC's random reference is not 0.5 — it
              depends on the active ratio.
            </p>

            <div className="mt-4 grid gap-3 border-t border-line pt-4 sm:grid-cols-2">
              <div>
                <p className="text-xs font-semibold text-good-ink">Reliable for</p>
                <p className="mt-1 text-sm text-ink-2">{method.best_for}</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-warn-ink">Unreliable for</p>
                <p className="mt-1 text-sm text-ink-2">{method.weak_for}</p>
              </div>
            </div>

            <div className="mt-4 space-y-1 border-t border-line pt-4 text-xs text-muted">
              <p>{method.caveat}</p>
              <p>{method.measured_coverage}</p>
            </div>
          </Panel>

          {method.bbb ? (
            <Panel
              title="BBB column"
              hint="A separate model with its own evaluation. One method's validation never vouches for another's."
            >
              <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
                <IntervalBar
                  label="ROC-AUC"
                  kind="95% CI · 0.5 = random"
                  lo={method.bbb.roc_auc_ci[0]}
                  hi={method.bbb.roc_auc_ci[1]}
                  point={method.bbb.roc_auc}
                  domainMin={0.5}
                  domainMax={1}
                />
                <div className="text-sm text-ink-2">
                  <p>
                    <span className="font-medium text-ink">{method.bbb.method}</span>, on{' '}
                    {method.bbb.dataset}.
                  </p>
                  <p className="mt-1">
                    Beats TPSA alone (
                    <span className="tnum">{method.bbb.beats.tpsa_only?.toFixed(3)}</span>)
                    and the previous hand-tuned score (
                    <span className="tnum">
                      {method.bbb.beats.hand_tuned_descriptor_score?.toFixed(3)}
                    </span>
                    ), which the benchmark retired.
                  </p>
                </div>
              </div>
              <p className="mt-3 border-t border-line pt-3 text-xs text-muted">
                {method.bbb.caveat}
              </p>
            </Panel>
          ) : null}

          <Panel flush title="Results">
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-xs text-muted">
                    <th className="px-4 py-2 font-medium">Compound</th>
                    <th className="px-4 py-2 font-medium">
                      <span className="inline-flex items-center gap-1.5">
                        <EvidenceMark tone="predicted" />
                        Predicted activity
                      </span>
                    </th>
                    <th className="px-4 py-2 font-medium">
                      <span className="inline-flex items-center gap-1.5">
                        <EvidenceMark tone="predicted" />
                        Predicted BBB
                      </span>
                    </th>
                    <th className="border-l border-line px-4 py-2 font-medium">
                      <span className="inline-flex items-center gap-1.5">
                        <EvidenceMark tone="measured" />
                        Measured affinity
                      </span>
                    </th>
                    <th className="px-4 py-2 font-medium">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {result.results.map((row, index) => (
                    <tr
                      key={`${row.query_smiles}-${index}`}
                      className="border-b border-line last:border-0 hover:bg-plane"
                    >
                      <td className="px-4 py-3 align-top">
                        <span className="block max-w-[20rem] truncate font-mono text-xs text-ink">
                          {row.query_smiles}
                        </span>
                        {row.descriptors ? (
                          <span className="tnum mt-1 block text-xs text-muted">
                            MW {row.descriptors.molecular_weight} · LogP{' '}
                            {row.descriptors.logp} · TPSA {row.descriptors.tpsa}
                          </span>
                        ) : (
                          <span className="mt-1 block text-xs font-medium text-critical-ink">
                            unparseable SMILES
                          </span>
                        )}
                      </td>

                      <td className="px-4 py-3 align-top">
                        {row.predicted ? (
                          <PredictedValue
                            value={row.predicted.similarity.toFixed(3)}
                            band={band(row.predicted.similarity)}
                            detail={
                              <span className="block max-w-[16rem] truncate font-mono">
                                nearest: {row.predicted.nearest_active_smiles}
                              </span>
                            }
                          />
                        ) : (
                          <NoValue label="not scored" />
                        )}
                      </td>

                      <td className="px-4 py-3 align-top">
                        {row.bbb_probability !== null ? (
                          <PredictedValue
                            value={row.bbb_probability.toFixed(2)}
                            band={
                              row.bbb_probability >= 0.5 ? 'likely crosses' : 'likely excluded'
                            }
                          />
                        ) : (
                          <NoValue label="not scored" />
                        )}
                      </td>

                      <td className="border-l border-line px-4 py-3 align-top">
                        {row.measured ? (
                          <MeasuredValue
                            value={`pChEMBL ${row.measured.pchembl_value}`}
                            detail={`${row.measured.standard_type} · n=${row.measured.measurement_count}`}
                          />
                        ) : (
                          <NoValue label="no measurement" />
                        )}
                      </td>

                      <td className="px-4 py-3 align-top text-xs text-muted">
                        {row.notes.join('; ') || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <p className="text-xs text-muted">
            A measured affinity, where one exists, is the stronger evidence — it is kept in
            its own column and never merged into the predicted score.
          </p>
        </>
      ) : null}
    </div>
  );
}
