import React, { useState, useEffect } from 'react';
import { Server, Activity, Terminal, ShieldAlert, RefreshCw, CheckCircle2, FileText, CheckCircle, XCircle, AlertTriangle, FileJson } from 'lucide-react';
import { apiService } from '../services/api';

export default function Diagnostics({ diagnostics, onRefreshDiag }) {
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState('');
  const [logs, setLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [selectedJson, setSelectedJson] = useState(null);

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    setLogsLoading(true);
    try {
      const res = await apiService.getRawTableData('api_request_logs', 50);
      setLogs(res.data || []);
    } catch (err) {
      console.warn("Failed to fetch logs:", err);
    } finally {
      setLogsLoading(false);
    }
  };

  const handleRunHealthCheck = async () => {
    setLoading(true);
    try {
      await onRefreshDiag();
      await fetchLogs();
      setTestResult("Diagnostics and live logs refreshed successfully.");
      setTimeout(() => setTestResult(''), 3500);
    } catch (err) {
      setTestResult(`Health check failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ width: '100%' }}>
      <div className="page-header">
        <div className="header-title">
          <h1>Pipeline Diagnostics & Telemetry Logs</h1>
          <p>Live debug console, system request telemetry, and database sanity verification</p>
        </div>
        <button 
          className="btn-submit" 
          disabled={loading || logsLoading} 
          onClick={handleRunHealthCheck}
          style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
          onMouseOver={(e) => e.target.style.background = 'var(--border)'}
          onMouseOut={(e) => e.target.style.background = 'rgba(255,255,255,0.03)'}
        >
          <RefreshCw size={16} className={loading || logsLoading ? 'spin-anim' : ''} />
          Refresh Diagnostics & Logs
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
        .scrollable-log-wrapper {
          width: 100%;
          overflow-x: auto;
          overflow-y: auto;
          border: 1px solid var(--border);
          border-radius: 8px;
          background: rgba(0, 0, 0, 0.2);
          max-height: 450px;
          box-sizing: border-box;
          margin-top: 16px;
        }
        .scrollable-log-wrapper::-webkit-scrollbar {
          height: 10px;
          width: 8px;
        }
        .scrollable-log-wrapper::-webkit-scrollbar-track {
          background: rgba(0, 0, 0, 0.4);
          border-radius: 4px;
        }
        .scrollable-log-wrapper::-webkit-scrollbar-thumb {
          background: rgba(99, 102, 241, 0.5);
          border-radius: 4px;
        }
        .scrollable-log-wrapper::-webkit-scrollbar-thumb:hover {
          background: var(--primary);
        }
        .log-table {
          width: max-content;
          min-width: 100%;
          border-collapse: collapse;
          text-align: left;
          font-size: 0.85rem;
        }
        .log-table th {
          background: rgba(20, 21, 24, 0.95);
          padding: 12px 16px;
          font-weight: 600;
          color: var(--text-primary);
          border-bottom: 1px solid var(--border);
          position: sticky;
          top: 0;
          z-index: 10;
          white-space: nowrap;
        }
        .log-table td {
          padding: 10px 16px;
          border-bottom: 1px solid var(--border);
          color: var(--text-secondary);
          white-space: nowrap;
        }
      `}</style>

      {testResult && (
        <div style={{ padding: '12px 16px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid var(--secondary)', borderRadius: '8px', marginBottom: '24px', fontSize: '0.9rem', color: 'var(--secondary)' }}>
          {testResult}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '32px', marginBottom: '32px' }}>
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

          <div className="panel" style={{ marginTop: '24px' }}>
            <div className="panel-title">
              <Terminal size={20} style={{ color: 'var(--secondary)' }} />
              <h3>Longitudinal Timeline Provenance</h3>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Latest Ingestion Run</span>
                <strong style={{ color: 'var(--text-primary)' }}>{diagnostics?.latest_signal ? new Date(diagnostics.latest_signal).toLocaleString() : 'Never'}</strong>
              </div>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Target Publication Lag Window</span>
                <strong style={{ color: 'var(--secondary)' }}>LAG_DAYS = 1 (24h Buffer)</strong>
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
            Current table record logs tracked in database:
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '10px' }}>
              <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>concepts</span>
              <strong style={{ fontFamily: 'var(--font-heading)' }}>{diagnostics?.active_concepts ?? 0} rows</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '10px' }}>
              <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>concept_daily_signals</span>
              <strong style={{ fontFamily: 'var(--font-heading)' }}>{diagnostics?.signals ?? 0} rows</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '10px' }}>
              <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>api_request_logs</span>
              <strong style={{ fontFamily: 'var(--font-heading)' }}>{diagnostics?.api_failures ?? 0} failure logs</strong>
            </div>
          </div>
        </div>
      </div>

      {/* Live System API & Pipeline Telemetry Logs Section */}
      <div className="panel" style={{ width: '100%', boxSizing: 'border-box' }}>
        <div className="panel-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FileText size={20} style={{ color: 'var(--primary)' }} />
            <h3>System Telemetry & Real-Time API Execution Logs</h3>
          </div>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Showing last 50 telemetry log entries</span>
        </div>

        <div className="scrollable-log-wrapper">
          <table className="log-table">
            <thead>
              <tr>
                <th>Requested At</th>
                <th>API Provider</th>
                <th>Endpoint</th>
                <th>Operation</th>
                <th>Status</th>
                <th>Latency (ms)</th>
                <th>Attempt</th>
                <th>Details / Error Trace</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '32px', color: 'var(--text-secondary)' }}>
                    No system API logs recorded yet. Run a pipeline execution to populate telemetry logs.
                  </td>
                </tr>
              ) : (
                logs.map((log, idx) => (
                  <tr key={log.id || idx}>
                    <td style={{ fontSize: '0.8rem' }}>
                      {log.requested_at ? new Date(log.requested_at).toLocaleString() : 'N/A'}
                    </td>
                    <td>
                      <span className="badge medium" style={{ textTransform: 'uppercase', fontSize: '0.75rem' }}>
                        {log.api_name || 'youtube'}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'monospace', color: 'var(--text-primary)' }}>
                      {log.endpoint || '/search'}
                    </td>
                    <td>{log.operation || 'list'}</td>
                    <td>
                      {log.success ? (
                        <span className="badge medium" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <CheckCircle size={12} /> {log.http_status || 200} OK
                        </span>
                      ) : (
                        <span className="badge small" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: 'rgba(239, 68, 68, 0.2)', color: '#f87171' }}>
                          <XCircle size={12} /> {log.http_status || 'ERR'}
                        </span>
                      )}
                    </td>
                    <td>{log.duration_ms ? `${log.duration_ms} ms` : '-'}</td>
                    <td>{log.attempt || 1}</td>
                    <td>
                      {log.error_message ? (
                        <span style={{ color: '#f87171', fontSize: '0.8rem' }}>{log.error_message}</span>
                      ) : log.request_metadata ? (
                        <button 
                          className="btn-json-inspect"
                          onClick={() => setSelectedJson(log.request_metadata)}
                          style={{ padding: '3px 8px', fontSize: '0.75rem' }}
                        >
                          <FileJson size={12} /> Metadata
                        </button>
                      ) : (
                        <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>Clean run</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* JSON Viewer Modal */}
      {selectedJson && (
        <div className="modal-overlay" onClick={() => setSelectedJson(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Telemetry Metadata Inspector</h3>
              <button 
                onClick={() => setSelectedJson(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '1.2rem' }}
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              <pre>{JSON.stringify(selectedJson, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
