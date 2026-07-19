import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom';
import Home from './pages/Home';
import Screen from './pages/Screen';
import WorkflowBuilder from './pages/WorkflowBuilder';
import DockingVisualizer from './pages/DockingVisualizer';
import MoleculeEditor from './pages/MoleculeEditor';
import ResultsDashboard from './pages/ResultsDashboard';
import './App.css';

const navItems = [
  { to: '/', label: 'Workflow' },
  { to: '/screen', label: 'Screen' },
  { to: '/workflow', label: 'Builder' },
  { to: '/docking', label: 'Docking' },
  { to: '/editor', label: 'Molecules' },
  { to: '/results', label: 'Results' },
];

function App() {
  return (
    <BrowserRouter>
      <nav className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-teal-700">NeuroLab</p>
            <h1 className="text-xl font-semibold text-slate-950">Runnable discovery workflow</h1>
          </div>
          <ul className="flex flex-wrap gap-2">
            {navItems.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    [
                      'inline-flex rounded-md px-3 py-2 text-sm font-medium transition',
                      isActive
                        ? 'bg-slate-950 text-white'
                        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950',
                    ].join(' ')
                  }
                  end={item.to === '/'}
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      </nav>
      <main className="mx-auto max-w-7xl px-5 py-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/screen" element={<Screen />} />
        <Route path="/workflow" element={<WorkflowBuilder />} />
          <Route path="/docking" element={<DockingVisualizer />} />
          <Route path="/editor" element={<MoleculeEditor />} />
          <Route path="/results" element={<ResultsDashboard />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

export default App;
