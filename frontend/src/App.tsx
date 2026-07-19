import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom';
import Home from './pages/Home';
import Screen from './pages/Screen';
import './App.css';

// Only routes backed by working functionality. Docking, molecule editing and
// persisted results are on the roadmap and are listed in the README rather
// than shown here as tabs that render a "planned" card.
const navItems = [
  { to: '/', label: 'Workflow' },
  { to: '/screen', label: 'Screen' },
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
        </Routes>
      </main>
    </BrowserRouter>
  );
}

export default App;
