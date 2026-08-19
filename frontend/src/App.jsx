import React, { useState, useEffect } from 'react';
import { Home, Terminal, BarChart2, Activity, ShieldCheck, Database } from 'lucide-react';
import { apiService } from './services/api';
import Dashboard from './components/Dashboard';
import ConceptDetail from './components/ConceptDetail';
import Diagnostics from './components/Diagnostics';
import ViewData from './components/ViewData';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedConcept, setSelectedConcept] = useState(null);
  const [diagnostics, setDiagnostics] = useState(null);

  useEffect(() => {
    fetchDiagnostics();
  }, []);

  const fetchDiagnostics = async () => {
    try {
      const data = await apiService.getDiagnostics();
      setDiagnostics(data);
    } catch (err) {
      console.error("Failed to load diagnostics", err);
    }
  };

  const handleSelectConcept = (concept) => {
    setSelectedConcept(concept);
    setActiveTab('concept-detail');
  };

  const handleBackToDashboard = () => {
    setSelectedConcept(null);
    setActiveTab('dashboard');
    fetchDiagnostics();
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <Dashboard 
            onSelectConcept={handleSelectConcept} 
            diagnostics={diagnostics} 
            onRefreshDiag={fetchDiagnostics} 
          />
        );
      case 'concept-detail':
        return (
          <ConceptDetail 
            concept={selectedConcept} 
            onBack={handleBackToDashboard} 
          />
        );
      case 'diagnostics':
        return (
          <Diagnostics 
            diagnostics={diagnostics} 
            onRefreshDiag={fetchDiagnostics} 
          />
        );
      case 'view-data':
        return <ViewData />;
      default:
        return (
          <Dashboard 
            onSelectConcept={handleSelectConcept} 
            diagnostics={diagnostics} 
            onRefreshDiag={fetchDiagnostics} 
          />
        );
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar navigation */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-logo">Y</div>
          <span className="brand-text">YouTube Trends</span>
        </div>

        <nav className="sidebar-nav">
          <button 
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => { setActiveTab('dashboard'); setSelectedConcept(null); }}
          >
            <Home size={18} />
            <span>Dashboard</span>
          </button>
          
          {selectedConcept && (
            <button 
              className={`nav-item ${activeTab === 'concept-detail' ? 'active' : ''}`}
              onClick={() => setActiveTab('concept-detail')}
            >
              <BarChart2 size={18} />
              <span>Concept: {selectedConcept.name}</span>
            </button>
          )}

          <button 
            className={`nav-item ${activeTab === 'diagnostics' ? 'active' : ''}`}
            onClick={() => { setActiveTab('diagnostics'); setSelectedConcept(null); }}
          >
            <Terminal size={18} />
            <span>Diagnostics</span>
          </button>

          <button 
            className={`nav-item ${activeTab === 'view-data' ? 'active' : ''}`}
            onClick={() => { setActiveTab('view-data'); setSelectedConcept(null); }}
          >
            <Database size={18} />
            <span>View Data</span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', marginBottom: '4px' }}>
            <ShieldCheck size={14} style={{ color: 'var(--secondary)' }} />
            <span>Ingestion Pipe</span>
          </div>
          <span>Phase 0 → 4 Active</span>
        </div>
      </aside>

      {/* Main content body */}
      <main className="main-content">
        {renderContent()}
      </main>
    </div>
  );
}
