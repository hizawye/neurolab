import { useEffect, useState } from 'react';
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom';
import Home from './pages/Home';
import Screen from './pages/Screen';
import { EvidenceKey } from './components/evidence';
import './App.css';

// Only routes backed by working functionality. Docking, molecule editing and
// persisted results are on the roadmap and are listed in the README rather
// than shown here as tabs that render a "planned" card.
//
// Each route is labelled with the kind of claim it produces, because that is the
// difference that matters between them: one retrieves measurements, the other
// makes predictions.
const navItems = [
  { to: '/', label: 'Workflow', kind: 'retrieval' },
  { to: '/screen', label: 'Screen', kind: 'prediction' },
];

type Theme = 'light' | 'dark';

function ThemeToggle() {
  const [theme, setTheme] = useState<Theme | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem('neurolab-theme') as Theme | null;
    if (stored === 'light' || stored === 'dark') setTheme(stored);
  }, []);

  useEffect(() => {
    if (theme) {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('neurolab-theme', theme);
    }
  }, [theme]);

  // Until a choice is made the OS preference governs, so the button offers the
  // opposite of whatever is currently rendering.
  const resolved: Theme =
    theme ??
    (window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

  return (
    <button
      type="button"
      className="rounded-md border border-line px-2.5 py-1.5 text-xs font-medium text-ink-2 transition-colors hover:border-line-strong hover:text-ink"
      onClick={() => setTheme(resolved === 'dark' ? 'light' : 'dark')}
      aria-label={`Switch to ${resolved === 'dark' ? 'light' : 'dark'} theme`}
    >
      {resolved === 'dark' ? 'Light' : 'Dark'}
    </button>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen flex-col">
        <header className="border-b border-line bg-surface">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-5 py-3">
            <div className="flex items-baseline gap-3">
              <span className="text-sm font-semibold tracking-[0.16em] text-ink">
                NEUROLAB
              </span>
              <span className="hidden text-xs text-muted sm:inline">
                Evidence-graded discovery workbench
              </span>
            </div>

            <div className="flex items-center gap-3">
              <nav>
                <ul className="flex gap-1">
                  {navItems.map((item) => (
                    <li key={item.to}>
                      <NavLink
                        to={item.to}
                        end={item.to === '/'}
                        className={({ isActive }) =>
                          [
                            'flex flex-col rounded-md px-3 py-1.5 text-sm transition-colors',
                            isActive
                              ? 'bg-ink text-plane'
                              : 'text-ink-2 hover:bg-line hover:text-ink',
                          ].join(' ')
                        }
                      >
                        {({ isActive }) => (
                          <>
                            <span className="font-medium">{item.label}</span>
                            <span
                              className={`text-[10px] uppercase tracking-wider ${
                                isActive ? 'text-plane/70' : 'text-muted'
                              }`}
                            >
                              {item.kind}
                            </span>
                          </>
                        )}
                      </NavLink>
                    </li>
                  ))}
                </ul>
              </nav>
              <ThemeToggle />
            </div>
          </div>

          {/* The key sits in the chrome so the encoding is learned once and
              holds on every page, rather than being re-explained per table. */}
          <div className="border-t border-line bg-plane">
            <div className="mx-auto max-w-7xl px-5 py-2">
              <EvidenceKey />
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-7xl flex-1 px-5 py-6">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/screen" element={<Screen />} />
          </Routes>
        </main>

        <footer className="border-t border-line bg-surface">
          <div className="mx-auto max-w-7xl px-5 py-4 text-xs text-muted">
            <p>
              Sources: ChEMBL bioactivities (binding assays only, median across repeat
              measurements) and RCSB PDB structures. Benchmarks are retrospective and
              overestimate prospective performance.
            </p>
            <p className="mt-1">
              Output is a prioritisation signal, not a drug candidate. Nothing here is
              wet-lab evidence, and nothing addresses selectivity, toxicity, or
              synthesizability.
            </p>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;
