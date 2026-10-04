import React, { useState, useEffect } from 'react';
import { Play, Database, Activity, AlertTriangle, Plus, Check, TrendingUp, Flame, Clock } from 'lucide-react';
import { apiService } from '../services/api';

export default function Dashboard({ onSelectConcept, diagnostics, onRefreshDiag }) {
  const [concepts, setConcepts] = useState([]);
  const [latestEntries, setLatestEntries] = useState([]);
  const [name, setName] = useState('');
  const [queries, setQueries] = useState('');
  const [description, setDescription] = useState('');
  const [statusMsg, setStatusMsg] = useState('');
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    fetchConcepts();
    fetchLatestEntries();
  }, []);

  const fetchConcepts = async () => {
    try {
      const data = await apiService.getConcepts();
      setConcepts(data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchLatestEntries = async () => {
    try {
      const data = await apiService.getLatestEntries(15);
      setLatestEntries(data);
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
    setStatusMsg(`Triggering real-time ingestion run...`);
    try {
      const res = await apiService.triggerPipeline(stage);
      setStatusMsg(`Success: Pipeline execution started in background.`);
      setTimeout(() => {
        setStatusMsg('');
        onRefreshDiag();
        fetchLatestEntries();
      }, 5000);
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
          <h1>Real-Time Trend Prediction Dashboard</h1>
          <p>Real-time analytics, concept signal tracking, and trend opportunity scoring (3x Daily Execution)</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(16,185,129,0.1)', padding: '6px 12px', borderRadius: '20px', border: '1px solid rgba(16,185,129,0.2)' }}>
            <span className="pulse-dot green"></span>
            <span style={{ fontSize: '0.82rem', fontWeight: '600', color: '#10B981' }}>Real-Time 3x/Day Schedule</span>
          </div>
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
            <span>Populated Videos</span>
            <Activity size={16} className="stat-card-icon" />
          </div>
          <div className="stat-card-value">
            {diagnostics?.videos ?? diagnostics?.population_members ?? 0}
          </div>
        </div>

        <div className="stat-card secondary">
          <div className="stat-card-header">
            <span>Tracked Concepts</span>
            <Plus size={16} className="stat-card-icon" />
          </div>
          <div className="stat-card-value">
            {concepts.length || diagnostics?.active_concepts || 10}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-header">
            <span>Generated Signals</span>
            <TrendingUp size={16} className="stat-card-icon" />
          </div>
          <div className="stat-card-value">
            {diagnostics?.signals ?? 0}
          </div>
        </div>
      </div>

      {/* Trigger control panel */}
      <div className="panel">
        <div className="panel-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Play size={20} style={{ color: 'var(--primary)' }} />
            <h3>Real-Time Pipeline Execution Controls</h3>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
            <Clock size={14} />
            <span>Runs automatically at 00:00, 08:00, 16:00 UTC</span>
          </div>
        </div>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '0.9rem' }}>
          Instantly execute real-time candidate search, semantic identity filtering, channel bucketing, and composite trend scoring.
        </p>
        <div className="trigger-buttons">
          <button className="btn-trigger" disabled={isRunning} onClick={() => handleTriggerPipeline("run")} style={{ background: 'var(--primary-glow)', borderColor: 'rgba(99,102,241,0.4)', padding: '12px 24px' }}>
            <Play size={20} style={{ color: 'var(--primary)' }} />
            <span style={{ fontWeight: '600' }}>Execute Real-Time Ingestion Pipe</span>
          </button>
        </div>
        {statusMsg && (
          <div style={{ marginTop: '16px', padding: '12px 16px', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border)', borderRadius: '4px', fontSize: '0.9rem', color: 'var(--primary)' }}>
            {statusMsg}
          </div>
        )}
      </div>

      {/* Top Populated Entries Leaderboard (Recent Pipeline Run) */}
      <div className="panel" style={{ marginBottom: '32px' }}>
        <div className="panel-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Flame size={22} style={{ color: '#F59E0B' }} />
            <h3>Top Populated Entries (Recent Pipeline Run)</h3>
          </div>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>Ranked by Composite Trend Score</span>
        </div>
        {latestEntries.length === 0 ? (
          <p style={{ color: 'var(--text-secondary)', fontStyle: 'italic', padding: '16px 0' }}>
            No populated video entries found yet. Execute a pipeline run above to populate real-time trend data.
          </p>
        ) : (
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Video Title</th>
                  <th>Concept</th>
                  <th>Views</th>
                  <th>Reach Ratio</th>
                  <th>Tier</th>
                  <th>Trend Score</th>
                </tr>
              </thead>
              <tbody>
                {latestEntries.map((entry, idx) => (
                  <tr key={`${entry.video_id}-${idx}`}>
                    <td style={{ fontWeight: '700', color: idx < 3 ? '#F59E0B' : 'var(--text-secondary)' }}>#{idx + 1}</td>
                    <td style={{ fontWeight: '600', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <a 
                        href={`https://www.youtube.com/watch?v=${entry.video_id}`} 
                        target="_blank" 
                        rel="noreferrer" 
                        style={{ color: 'var(--text-primary)', textDecoration: 'none' }}
                        onMouseOver={(e) => e.target.style.color = 'var(--primary)'}
                        onMouseOut={(e) => e.target.style.color = 'var(--text-primary)'}
                      >
                        {entry.title}
                      </a>
                    </td>
                    <td>
                      <span className="badge" style={{ background: 'rgba(99,102,241,0.15)', color: '#818CF8', border: '1px solid rgba(99,102,241,0.3)' }}>
                        {entry.concept_name}
                      </span>
                    </td>
                    <td>{entry.view_count ? entry.view_count.toLocaleString() : 'N/A'}</td>
                    <td>{entry.reach_ratio ? entry.reach_ratio.toFixed(3) : '0.000'}</td>
                    <td>
                      <span className={`badge ${entry.channel_tier === 'big' ? 'big' : entry.channel_tier === 'medium' ? 'medium' : 'small'}`}>
                        {(entry.channel_tier || 'medium').toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '60px', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{ width: `${Math.min(100, entry.trend_score || 0)}%`, height: '100%', background: 'linear-gradient(90deg, #6366F1, #10B981)' }}></div>
                        </div>
                        <span style={{ fontWeight: '700', color: '#10B981', fontSize: '0.9rem' }}>{entry.trend_score ? entry.trend_score.toFixed(1) : '0.0'}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Split grid for list and creation form */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.7fr 1fr', gap: '32px' }}>
        <div className="panel">
          <div className="panel-title">
            <h3>Tracked Fitness Concepts</h3>
          </div>
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Concept Name</th>
                  <th>Include Terms</th>
                  <th>Category</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {concepts.map(concept => (
                  <tr key={concept.id}>
                    <td style={{ fontWeight: '600' }}>{concept.name}</td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                      {(concept.include_terms || concept.search_queries || []).slice(0, 2).join(', ')}
                    </td>
                    <td>
                      <span className="badge" style={{ background: 'rgba(16,185,129,0.1)', color: '#10B981', border: '1px solid rgba(16,185,129,0.2)' }}>
                        {concept.category || 'Fitness'}
                      </span>
                    </td>
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
                        Details
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
                placeholder="e.g. Muscle Growth" 
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
                placeholder="muscle growth, hypertrophy" 
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
