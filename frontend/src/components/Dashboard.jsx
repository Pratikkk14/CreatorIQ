import React, { useState, useEffect } from 'react';
import { Play, Database, Activity, AlertTriangle, Plus, Check } from 'lucide-react';
import { apiService } from '../services/api';

export default function Dashboard({ onSelectConcept, diagnostics, onRefreshDiag }) {
  const [concepts, setConcepts] = useState([]);
  const [name, setName] = useState('');
  const [queries, setQueries] = useState('');
  const [description, setDescription] = useState('');
  const [statusMsg, setStatusMsg] = useState('');
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    fetchConcepts();
  }, []);

  const fetchConcepts = async () => {
    try {
      const data = await apiService.getConcepts();
      setConcepts(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateConcept = async (e) => {
    e.preventDefault();
    if (!name || !queries) return;
    const queryList = queries.split(',').map(q => q.trim()).filter(q => q);
    
    try {
      await apiService.createConcept(name, queryList, description);
      setName('');
      setQueries('');
      setDescription('');
      fetchConcepts();
      onRefreshDiag();
      setStatusMsg("Concept created successfully!");
      setTimeout(() => setStatusMsg(''), 3000);
    } catch (err) {
      console.error(err);
    }
  };

  const handleTriggerPipeline = async (stage) => {
    setIsRunning(true);
    setStatusMsg(`Triggering stage: ${stage}...`);
    try {
      const res = await apiService.triggerPipeline(stage);
      setStatusMsg(`Success: Pipeline stage '${stage}' started in background.`);
      setTimeout(() => {
        setStatusMsg('');
        onRefreshDiag();
      }, 4000);
    } catch (err) {
      setStatusMsg(`Failed to trigger pipeline stage: ${err.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div className="header-title">
          <h1>Longitudinal Dashboard</h1>
          <p>Real-time analytics and controls for the YouTube Trend Prediction Ingestion System</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="pulse-dot green"></span>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>System Active</span>
        </div>
      </div>

      {/* Grid of stats */}
      <div className="stats-grid">
        <div className="stat-card primary">
          <div className="stat-card-header">
            <span>Database Status</span>
            <Database size={16} className="stat-card-icon" />
          </div>
          <div className="stat-card-value" style={{ color: diagnostics?.database === "OK" ? "var(--secondary)" : "var(--accent)" }}>
            {diagnostics?.database || "CONNECTING..."}
          </div>
        </div>

        <div className="stat-card primary">
          <div className="stat-card-header">
            <span>Monitored Videos</span>
            <Activity size={16} className="stat-card-icon" />
          </div>
          <div className="stat-card-value">
            {diagnostics?.population_members ?? 0}
          </div>
        </div>

        <div className="stat-card secondary">
          <div className="stat-card-header">
            <span>Active Concepts</span>
            <Plus size={16} className="stat-card-icon" />
          </div>
          <div className="stat-card-value">
            {diagnostics?.active_concepts ?? 0}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-header">
            <span>API Request Failures</span>
            <AlertTriangle size={16} className="stat-card-icon" />
          </div>
          <div className="stat-card-value" style={{ color: (diagnostics?.api_failures ?? 0) > 0 ? "var(--accent)" : "var(--text-primary)" }}>
            {diagnostics?.api_failures ?? 0}
          </div>
        </div>
      </div>

      {/* Trigger control panel */}
      <div className="panel">
        <div className="panel-title">
          <Play size={20} style={{ color: 'var(--primary)' }} />
          <h3>Manual Pipeline Controls</h3>
        </div>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '20px', fontSize: '0.9rem' }}>
          Instantly run individual phases or the whole ingestion sequence. Operations run asynchronously in the background.
        </p>
        <div className="trigger-buttons">
          <button className="btn-trigger" disabled={isRunning} onClick={() => handleTriggerPipeline("discover")}>
            <Check size={20} style={{ color: 'var(--primary)' }} />
            <span>1. Discover</span>
          </button>
          <button className="btn-trigger" disabled={isRunning} onClick={() => handleTriggerPipeline("observe")}>
            <Check size={20} style={{ color: 'var(--secondary)' }} />
            <span>2. Observe</span>
          </button>
          <button className="btn-trigger" disabled={isRunning} onClick={() => handleTriggerPipeline("metrics")}>
            <Check size={20} style={{ color: 'var(--primary)' }} />
            <span>3. Metrics</span>
          </button>
          <button className="btn-trigger" disabled={isRunning} onClick={() => handleTriggerPipeline("signals")}>
            <Check size={20} style={{ color: 'var(--secondary)' }} />
            <span>4. Signals</span>
          </button>
          <button className="btn-trigger" disabled={isRunning} onClick={() => handleTriggerPipeline("run")} style={{ background: 'var(--primary-glow)', borderColor: 'rgba(99,102,241,0.4)' }}>
            <Play size={20} style={{ color: 'var(--primary)' }} />
            <span style={{ fontWeight: '600' }}>Run Full Pipe</span>
          </button>
        </div>
        {statusMsg && (
          <div style={{ marginTop: '20px', padding: '12px 16px', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border)', borderRadius: '4px', fontSize: '0.9rem', color: 'var(--primary)' }}>
            {statusMsg}
          </div>
        )}
      </div>

      {/* Split grid for list and creation form */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.7fr 1fr', gap: '32px' }}>
        <div className="panel">
          <div className="panel-title">
            <h3>Monitored Concepts</h3>
          </div>
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Concept ID</th>
                  <th>Name</th>
                  <th>Queries</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {concepts.map(concept => (
                  <tr key={concept.id}>
                    <td>#{concept.id}</td>
                    <td style={{ fontWeight: '600' }}>{concept.name}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{concept.search_queries.join(', ')}</td>
                    <td>
                      <span className={`badge ${concept.active ? 'medium' : 'small'}`}>
                        {concept.active ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                    </td>
                    <td>
                      <button 
                        onClick={() => onSelectConcept(concept)}
                        style={{ background: 'transparent', border: '1px solid var(--primary)', color: 'var(--primary)', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', transition: 'var(--transition)' }}
                        onMouseOver={(e) => { e.target.style.background = 'var(--primary)'; e.target.style.color = '#fff'; }}
                        onMouseOut={(e) => { e.target.style.background = 'transparent'; e.target.style.color = 'var(--primary)'; }}
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel">
          <div className="panel-title">
            <h3>Add New Concept</h3>
          </div>
          <form onSubmit={handleCreateConcept}>
            <div className="form-group">
              <label className="form-label">Concept Name</label>
              <input 
                type="text" 
                className="form-input" 
                value={name} 
                onChange={(e) => setName(e.target.value)} 
                placeholder="e.g. AI Agents" 
                required 
              />
            </div>
            <div className="form-group">
              <label className="form-label">Search Queries (comma separated)</label>
              <input 
                type="text" 
                className="form-input" 
                value={queries} 
                onChange={(e) => setQueries(e.target.value)} 
                placeholder="AI agents, agentic AI" 
                required 
              />
            </div>
            <div className="form-group">
              <label className="form-label">Description</label>
              <textarea 
                className="form-input" 
                value={description} 
                onChange={(e) => setDescription(e.target.value)} 
                placeholder="Describe this concept..." 
                rows="3" 
              />
            </div>
            <button type="submit" className="btn-submit" style={{ width: '100%' }}>
              Create Concept
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
