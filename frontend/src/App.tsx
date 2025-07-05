import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import Home from './pages/Home';
import WorkflowBuilder from './pages/WorkflowBuilder';
import DockingVisualizer from './pages/DockingVisualizer';
import MoleculeEditor from './pages/MoleculeEditor';
import ResultsDashboard from './pages/ResultsDashboard';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <nav className="bg-gray-800 p-4">
        <ul className="flex space-x-4">
          <li><Link to="/" className="text-white hover:text-gray-300">Home</Link></li>
          <li><Link to="/workflow" className="text-white hover:text-gray-300">Workflow Builder</Link></li>
          <li><Link to="/docking" className="text-white hover:text-gray-300">Docking Visualizer</Link></li>
          <li><Link to="/editor" className="text-white hover:text-gray-300">Molecule Editor</Link></li>
          <li><Link to="/results" className="text-white hover:text-gray-300">Results</Link></li>
        </ul>
      </nav>
      <div className="p-4">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/workflow" element={<WorkflowBuilder />} />
          <Route path="/docking" element={<DockingVisualizer />} />
          <Route path="/editor" element={<MoleculeEditor />} />
          <Route path="/results" element={<ResultsDashboard />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;