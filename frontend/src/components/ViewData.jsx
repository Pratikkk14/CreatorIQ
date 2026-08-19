import React, { useState, useEffect } from 'react';
import { Database, RefreshCw, Search, ArrowRightLeft, FileJson, AlertCircle } from 'lucide-react';
import { apiService } from '../services/api';

export default function ViewData() {
  const [tables, setTables] = useState({});
  const [activeTable, setActiveTable] = useState('');
  const [tableData, setTableData] = useState([]);
  const [limit, setLimit] = useState(100);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingCounts, setLoadingCounts] = useState(false);
  const [error, setError] = useState('');
  const [selectedJson, setSelectedJson] = useState(null);

  // Table display names and descriptions
  const tableDescriptions = {
    concepts: "Trend concepts monitored by the longitudinal prediction system.",
    channels: "YouTube channel registries including subscriber and video counts.",
    videos: "YouTube video registries showing initial discovery stats.",
    search_runs: "Discovery search runs executed for active queries.",
    video_candidates: "Discovered video candidates with semantic relevance scores and check outcomes.",
    population_runs: "Active population selection runs and target size settings.",
    population_members: "Video members selected to populate specific trend cohorts.",
    video_observations: "Longitudinal daily observation counts (views, likes, comments).",
    video_metrics: "Longitudinal calculated changes (velocities, growth, acceleration).",
    concept_daily_signals: "Rollup trend signal aggregates (median velocities, bucket percentiles).",
    api_request_logs: "Auditing request costs, HTTP statuses, and error trace logs."
  };

  useEffect(() => {
    fetchTableCounts();
  }, []);

  useEffect(() => {
    if (activeTable) {
      fetchTableData(activeTable, limit);
    }
  }, [activeTable, limit]);

  const fetchTableCounts = async () => {
    setLoadingCounts(true);
    try {
      const summary = await apiService.getRawDataSummary();
      setTables(summary);
      // Auto-select first table if none active
      if (!activeTable && Object.keys(summary).length > 0) {
        setActiveTable(Object.keys(summary)[0]);
      }
    } catch (err) {
      setError("Failed to fetch database table row counts.");
    } finally {
      setLoadingCounts(false);
    }
  };

  const fetchTableData = async (tableName, rowLimit) => {
    setLoading(true);
    setError('');
    try {
      const response = await apiService.getRawTableData(tableName, rowLimit);
      setTableData(response.data || []);
    } catch (err) {
      setError(`Failed to fetch records for table '${tableName}': ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    await fetchTableCounts();
    if (activeTable) {
      await fetchTableData(activeTable, limit);
    }
  };

  // Local client-side row filtering
  const filteredData = tableData.filter(row => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return Object.values(row).some(val => 
      val !== null && val !== undefined && String(val).toLowerCase().includes(query)
    );
  });

  // Dynamic headers extraction
  const columns = tableData.length > 0 ? Object.keys(tableData[0]) : [];

  // Helper to format values in the table cells
  const formatCell = (val) => {
    if (val === null || val === undefined) {
      return <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>NULL</span>;
    }
    if (typeof val === 'boolean') {
      return <span className={`badge ${val ? 'medium' : 'small'}`}>{val ? 'true' : 'false'}</span>;
    }
    if (typeof val === 'object') {
      return (
        <button 
          className="btn-json-inspect"
          onClick={() => setSelectedJson(val)}
          title="Inspect JSON object"
        >
          <FileJson size={14} />
          <span>Object</span>
        </button>
      );
    }
    // Handle timestamps
    if (typeof val === 'string' && val.match(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)) {
      return new Date(val).toLocaleString();
    }
    return String(val);
  };

  return (
    <div className="view-data-container">
      <div className="page-header">
        <div className="header-title">
          <h1>Database Table Viewer</h1>
          <p>Direct view of raw database records (<code>SELECT * FROM table_name</code>) inside your Neon / SQLite instances.</p>
        </div>
        <button 
          className="btn-submit" 
          onClick={handleRefresh}
          disabled={loading || loadingCounts}
          style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
        >
          <RefreshCw size={16} className={loading || loadingCounts ? 'spin-anim' : ''} />
          Refresh Database
        </button>
      </div>

      <style>{`
        .view-data-layout {
          display: grid;
          grid-template-columns: 280px 1fr;
          gap: 24px;
          margin-top: 8px;
        }
        .table-tab-list {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .table-tab-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 16px;
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid var(--border);
          border-radius: 8px;
          color: var(--text-secondary);
          cursor: pointer;
          transition: all 0.2s ease;
          text-align: left;
        }
        .table-tab-item:hover {
          background: rgba(255, 255, 255, 0.04);
          color: var(--text-primary);
          border-color: rgba(255, 255, 255, 0.2);
        }
        .table-tab-item.active {
          background: rgba(var(--primary-rgb, 99, 102, 241), 0.15);
          border-color: var(--primary);
          color: var(--text-primary);
          font-weight: 600;
        }
        .tab-name-wrapper {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .tab-row-count {
          font-size: 0.75rem;
          background: rgba(255, 255, 255, 0.08);
          padding: 2px 8px;
          border-radius: 20px;
          font-weight: normal;
        }
        .table-tab-item.active .tab-row-count {
          background: var(--primary);
          color: #ffffff;
        }
        .data-viewer-panel {
          min-height: 500px;
          display: flex;
          flex-direction: column;
        }
        .controls-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          margin-bottom: 16px;
          flex-wrap: wrap;
        }
        .search-input-wrapper {
          position: relative;
          flex: 1;
          min-width: 250px;
        }
        .search-input-wrapper input {
          width: 100%;
          padding: 10px 16px 10px 40px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid var(--border);
          border-radius: 8px;
          color: var(--text-primary);
          outline: none;
          transition: border-color 0.2s;
        }
        .search-input-wrapper input:focus {
          border-color: var(--primary);
        }
        .search-icon {
          position: absolute;
          left: 14px;
          top: 50%;
          transform: translateY(-50%);
          color: var(--text-secondary);
        }
        .limit-select-wrapper {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.9rem;
          color: var(--text-secondary);
        }
        .limit-select-wrapper select {
          padding: 8px 12px;
          background: rgba(255,255,255,0.03);
          border: 1px solid var(--border);
          border-radius: 8px;
          color: var(--text-primary);
          outline: none;
          cursor: pointer;
        }
        .scrollable-table-wrapper {
          overflow-x: auto;
          border: 1px solid var(--border);
          border-radius: 8px;
          background: rgba(0, 0, 0, 0.2);
          max-height: 600px;
          overflow-y: auto;
        }
        .raw-data-table {
          width: 100%;
          border-collapse: collapse;
          text-align: left;
          font-size: 0.85rem;
        }
        .raw-data-table th {
          background: rgba(255, 255, 255, 0.04);
          padding: 12px 16px;
          font-weight: 600;
          color: var(--text-primary);
          border-bottom: 1px solid var(--border);
          position: sticky;
          top: 0;
          z-index: 10;
        }
        .raw-data-table td {
          padding: 10px 16px;
          border-bottom: 1px solid var(--border);
          color: var(--text-secondary);
          white-space: nowrap;
          max-width: 300px;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .raw-data-table tr:hover td {
          background: rgba(255, 255, 255, 0.02);
          color: var(--text-primary);
        }
        .btn-json-inspect {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 4px 8px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid var(--border);
          border-radius: 4px;
          color: var(--primary);
          font-size: 0.75rem;
          cursor: pointer;
          transition: background 0.2s;
        }
        .btn-json-inspect:hover {
          background: rgba(255, 255, 255, 0.1);
        }
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0,0,0,0.8);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }
        .modal-content {
          background: #141517;
          border: 1px solid var(--border);
          border-radius: 12px;
          padding: 24px;
          width: 90%;
          max-width: 600px;
          max-height: 80%;
          overflow-y: auto;
          box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        }
        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          border-bottom: 1px solid var(--border);
          padding-bottom: 12px;
        }
        .modal-body pre {
          background: rgba(0,0,0,0.3);
          border: 1px solid var(--border);
          padding: 16px;
          border-radius: 8px;
          color: #2ed573;
          font-family: monospace;
          font-size: 0.85rem;
          overflow-x: auto;
          white-space: pre-wrap;
        }
      `}</style>

      {error && (
        <div style={{ padding: '16px', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', borderRadius: '8px', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '10px', color: '#f87171' }}>
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      <div className="view-data-layout">
        {/* Sidebar table selection tabs */}
        <aside className="table-tab-list">
          {Object.entries(tables).map(([name, count]) => (
            <button
              key={name}
              className={`table-tab-item ${activeTable === name ? 'active' : ''}`}
              onClick={() => {
                setActiveTable(name);
                setSearchQuery('');
              }}
            >
              <div className="tab-name-wrapper">
                <Database size={16} />
                <span>{name}</span>
              </div>
              <span className="tab-row-count">{count}</span>
            </button>
          ))}
        </aside>

        {/* Content Viewer Panel */}
        <section className="panel data-viewer-panel">
          <div className="panel-title" style={{ justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <ArrowRightLeft size={20} style={{ color: 'var(--primary)' }} />
              <div>
                <h3 style={{ textTransform: 'capitalize' }}>Table: {activeTable.replace('_', ' ')}</h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px', fontWeight: 'normal' }}>
                  {tableDescriptions[activeTable] || "Direct view of data inside PostgreSQL database schema."}
                </p>
              </div>
            </div>
            
            <div className="limit-select-wrapper">
              <span>Limit:</span>
              <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
                <option value={50}>50 rows</option>
                <option value={100}>100 rows</option>
                <option value={200}>200 rows</option>
                <option value={500}>500 rows</option>
              </select>
            </div>
          </div>

          <div className="controls-row" style={{ marginTop: '16px' }}>
            <div className="search-input-wrapper">
              <Search size={18} className="search-icon" />
              <input 
                type="text" 
                placeholder="Search raw values in columns..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          {/* Table container */}
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, padding: '48px', gap: '16px' }}>
              <RefreshCw size={24} className="spin-anim" style={{ color: 'var(--primary)' }} />
              <span style={{ color: 'var(--text-secondary)' }}>Querying database rows...</span>
            </div>
          ) : filteredData.length === 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, padding: '48px', border: '1px dashed var(--border)', borderRadius: '8px', color: 'var(--text-secondary)' }}>
              <span>No rows found matching filters or database table is empty.</span>
            </div>
          ) : (
            <div className="scrollable-table-wrapper">
              <table className="raw-data-table">
                <thead>
                  <tr>
                    {columns.map(col => (
                      <th key={col}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredData.map((row, idx) => (
                    <tr key={row.id || idx}>
                      {columns.map(col => (
                        <td key={col} title={row[col] !== null && typeof row[col] !== 'object' ? String(row[col]) : ''}>
                          {formatCell(row[col])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      {/* JSON Viewer Inspector Modal */}
      {selectedJson && (
        <div className="modal-overlay" onClick={() => setSelectedJson(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>JSON Object Details</h3>
              <button 
                onClick={() => setSelectedJson(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '1.2rem' }}
              >
                &times;
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
