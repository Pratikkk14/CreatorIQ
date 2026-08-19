import React, { useState } from 'react';
import { Server, Activity, Terminal, ShieldAlert, RefreshCw, CheckCircle2 } from 'lucide-react';
import { apiService } from '../services/api';

export default function Diagnostics({ diagnostics, onRefreshDiag }) {
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState('');

  const handleRunHealthCheck = async () => {
    setLoading(true);
    try {
      await onRefreshDiag();
      setTestResult("Diagnostics refreshed successfully.");
      setTimeout(() => setTestResult(''), 3000);
    } catch (err) {
      setTestResult(`Health check failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div className="header-title">
          <h1>Pipeline Diagnostics</h1>
          <p>Debug console and sanity verification for database states and YouTube configuration settings</p>
        </div>
        <button 
          className="btn-submit" 
          disabled={loading} 
          onClick={handleRunHealthCheck}
          style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
          onMouseOver={(e) => e.target.style.background = 'var(--border)'}
          onMouseOut={(e) => e.target.style.background = 'rgba(255,255,255,0.03)'}
        >
          <RefreshCw size={16} className={loading ? 'spin-anim' : ''} />
          Refresh Diagnostics
        </button>
      </div>

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        .spin-anim {
          animation: spin 1s linear infinite;
        }
      `}</style>

      {testResult && (
        <div style={{ padding: '12px 16px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid var(--secondary)', borderRadius: '8px', marginBottom: '24px', fontSize: '0.9rem', color: 'var(--secondary)' }}>
          {testResult}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '32px' }}>
        {/* Connection Diagnostics */}
        <div>
          <div className="panel">
            <div className="panel-title">
              <Server size={20} style={{ color: 'var(--primary)' }} />
              <h3>Integrations Health Check</h3>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginTop: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
                <div>
                  <div style={{ fontWeight: '600' }}>PostgreSQL Connectivity</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Neon DB instances connection verify</div>
                </div>
                <span className={`badge ${diagnostics?.database === "OK" ? "medium" : "small"}`} style={{ padding: '6px 12px' }}>
                  {diagnostics?.database === "OK" ? "CONNECTED" : "DISCONNECTED"}
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
                <div>
                  <div style={{ fontWeight: '600' }}>YouTube Data API Key</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Google Console developer key authentication</div>
                </div>
                <span className={`badge ${diagnostics?.youtube_configuration === "OK" ? "medium" : "small"}`} style={{ padding: '6px 12px' }}>
                  {diagnostics?.youtube_configuration === "OK" ? "AUTHENTICATED" : "MISSING_KEY"}
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '12px' }}>
                <div>
                  <div style={{ fontWeight: '600' }}>API Request Errors</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Failures rate recorded in logger telemetry</div>
                </div>
                <span className={`badge ${(diagnostics?.api_failures ?? 0) === 0 ? "medium" : "small"}`} style={{ padding: '6px 12px' }}>
                  {diagnostics?.api_failures ?? 0} FAILURES
                </span>
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-title">
              <Terminal size={20} style={{ color: 'var(--secondary)' }} />
              <h3>Longitudinal Timeline Provenance</h3>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Latest Immutable Observation Run</span>
                <strong style={{ color: 'var(--text-primary)' }}>{diagnostics?.latest_observation ? new Date(diagnostics.latest_observation).toLocaleString() : 'Never'}</strong>
              </div>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Latest Derived Daily Concept Signal</span>
                <strong style={{ color: 'var(--text-primary)' }}>{diagnostics?.latest_signal ? new Date(diagnostics.latest_signal).toLocaleString() : 'Never'}</strong>
              </div>
            </div>
          </div>
        </div>

        {/* Database Tally checklist */}
        <div className="panel">
          <div className="panel-title">
            <CheckCircle2 size={20} style={{ color: 'var(--secondary)' }} />
            <h3>Database Row Tally</h3>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '24px' }}>
            Current table record logs tracked in PostgreSQL:
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '10px' }}>
              <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>concepts</span>
              <strong style={{ fontFamily: 'var(--font-heading)' }}>{diagnostics?.active_concepts ?? 0} rows</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '10px' }}>
              <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>videos</span>
              <strong style={{ fontFamily: 'var(--font-heading)' }}>{diagnostics?.videos ?? 0} rows</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '10px' }}>
              <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>video_candidates</span>
              <strong style={{ fontFamily: 'var(--font-heading)' }}>{diagnostics?.candidates ?? 0} rows</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '10px' }}>
              <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>population_members</span>
              <strong style={{ fontFamily: 'var(--font-heading)' }}>{diagnostics?.population_members ?? 0} rows</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '10px' }}>
              <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>video_observations</span>
              <strong style={{ fontFamily: 'var(--font-heading)' }}>{diagnostics?.observations ?? 0} rows</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '10px' }}>
              <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>concept_daily_signals</span>
              <strong style={{ fontFamily: 'var(--font-heading)' }}>{diagnostics?.signals ?? 0} rows</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
