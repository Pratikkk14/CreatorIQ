import React, { useState, useEffect } from 'react';
import { LineChart, ArrowLeft, GitFork, UserCheck, Calendar } from 'lucide-react';
import { apiService } from '../services/api';

export default function ConceptDetail({ concept, onBack }) {
  const [signals, setSignals] = useState([]);
  const [selectedMetric, setSelectedMetric] = useState('median_view_velocity');
  const [selectedDate, setSelectedDate] = useState('');
  const [provenance, setProvenance] = useState(null);
  const [loadingProv, setLoadingProv] = useState(false);

  useEffect(() => {
    fetchSignals();
  }, [concept.id]);

  const fetchSignals = async () => {
    try {
      const data = await apiService.getSignals(concept.id);
      setSignals(data);
      if (data.length > 0) {
        // Default select latest date to show provenance
        const latestDate = data[data.length - 1].signal_date;
        handleSelectDate(latestDate);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSelectDate = async (dateStr) => {
    setSelectedDate(dateStr);
    setLoadingProv(true);
    try {
      const data = await apiService.getProvenance(concept.id, dateStr);
      setProvenance(data);
    } catch (err) {
      console.error("Failed to load provenance", err);
    } finally {
      setLoadingProv(false);
    }
  };

  // Safe helper to build responsive SVG path for the chart
  const renderSVGChart = () => {
    if (signals.length === 0) return <div style={{ color: 'var(--text-secondary)', padding: '40px 0', textAlign: 'center' }}>No historical signals generated yet. Run pipeline steps!</div>;

    const width = 800;
    const height = 240;
    const paddingLeft = 60;
    const paddingRight = 30;
    const paddingTop = 20;
    const paddingBottom = 40;

    const chartWidth = width - paddingLeft - paddingRight;
    const chartHeight = height - paddingTop - paddingBottom;

    // Get value bounds
    const values = signals.map(s => s[selectedMetric] || 0);
    const minVal = Math.min(...values, 0); // floor at 0
    const maxVal = Math.max(...values, 100) * 1.1; // 10% buffer
    const range = maxVal - minVal;

    // Generate points
    const points = signals.map((sig, idx) => {
      const x = paddingLeft + (idx / (signals.length - 1 || 1)) * chartWidth;
      const y = paddingTop + chartHeight - ((sig[selectedMetric] || 0) - minVal) / range * chartHeight;
      return { x, y, date: sig.signal_date, value: sig[selectedMetric] };
    });

    // Build SVG path
    let pathD = '';
    let areaD = '';

    if (points.length > 0) {
      pathD = `M ${points[0].x} ${points[0].y}`;
      areaD = `M ${points[0].x} ${paddingTop + chartHeight}`;
      
      for (let i = 0; i < points.length; i++) {
        pathD += ` L ${points[i].x} ${points[i].y}`;
        areaD += ` L ${points[i].x} ${points[i].y}`;
      }
      
      areaD += ` L ${points[points.length - 1].x} ${paddingTop + chartHeight} Z`;
    }

    return (
      <div className="chart-container">
        <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg">
          <defs>
            <linearGradient id="chart-gradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.4" />
              <stop offset="100%" stopColor="var(--primary)" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => {
            const y = paddingTop + chartHeight * ratio;
            const val = maxVal - (ratio * range);
            return (
              <g key={idx}>
                <line x1={paddingLeft} y1={y} x2={width - paddingRight} y2={y} className="chart-grid" />
                <text x={paddingLeft - 8} y={y + 4} textAnchor="end" fill="var(--text-muted)" fontSize="10">
                  {val.toFixed(selectedMetric.includes('growth') || selectedMetric.includes('density') ? 2 : 0)}
                </text>
              </g>
            );
          })}

          {/* Fill Area */}
          {areaD && <path d={areaD} className="chart-area" />}

          {/* Line Path */}
          {pathD && <path d={pathD} className="chart-line" />}

          {/* Interactive points */}
          {points.map((pt, idx) => (
            <circle
              key={idx}
              cx={pt.x}
              cy={pt.y}
              r={pt.date === selectedDate ? 7 : 4}
              className="chart-point"
              style={{ fill: pt.date === selectedDate ? 'var(--secondary)' : 'var(--primary)' }}
              onClick={() => handleSelectDate(pt.date)}
            >
              <title>{`${pt.date}: ${pt.value}`}</title>
            </circle>
          ))}

          {/* X Axis labels */}
          {points.map((pt, idx) => {
            // Show first, middle, last to avoid crowding
            if (idx === 0 || idx === Math.floor(points.length / 2) || idx === points.length - 1) {
              return (
                <text key={idx} x={pt.x} y={height - 15} textAnchor="middle" fill="var(--text-muted)" fontSize="10">
                  {pt.date}
                </text>
              );
            }
            return null;
          })}
        </svg>
      </div>
    );
  };

  const formatMetricName = (name) => {
    return name
      .replace('median_', '')
      .split('_')
      .map(w => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  };

  return (
    <div>
      <div className="page-header">
        <div className="header-title">
          <button 
            onClick={onBack}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', marginBottom: '12px', fontSize: '0.9rem' }}
          >
            <ArrowLeft size={16} /> Back to Dashboard
          </button>
          <h1>Concept: {concept.name}</h1>
          <p>{concept.description || 'Monitored topics and search parameters'}</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '32px', marginBottom: '32px' }}>
        {/* Chart Panel */}
        <div className="panel" style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '12px', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <LineChart size={20} style={{ color: 'var(--primary)' }} />
              <h3>Signal Metric Trajectory</h3>
            </div>
            
            {/* Metric Selector Dropdown */}
            <select 
              value={selectedMetric} 
              onChange={(e) => setSelectedMetric(e.target.value)}
              style={{ background: 'var(--bg-main)', border: '1px solid var(--border)', color: 'var(--text-primary)', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', outline: 'none' }}
            >
              <option value="median_view_velocity">Median View Velocity</option>
              <option value="median_view_growth">Median View Growth</option>
              <option value="median_view_acceleration">Median View Acceleration</option>
              <option value="median_normalized_velocity">Median Normalized Velocity</option>
              <option value="median_reach_ratio">Median Reach Ratio</option>
              <option value="median_interaction_density">Median Interaction Density</option>
            </select>
          </div>

          {renderSVGChart()}
          
          <div style={{ marginTop: '16px', fontSize: '0.85rem', color: 'var(--text-secondary)', textAlign: 'center' }}>
            💡 Click on any dot on the chart line to audit the <strong>Data Provenance</strong> for that date below.
          </div>
        </div>

        {/* Stratification Box */}
        <div className="panel">
          <div className="panel-title">
            <UserCheck size={20} style={{ color: 'var(--secondary)' }} />
            <h3>Latest Creator Ratios</h3>
          </div>
          {provenance?.signal ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '16px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
                  <span>Big Creators Signal</span>
                  <span className="badge big">{provenance.signal.big_creator_signal ?? 'N/A'} views/day</span>
                </div>
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
                  <span>Medium Creators Signal</span>
                  <span className="badge medium">{provenance.signal.medium_creator_signal ?? 'N/A'} views/day</span>
                </div>
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
                  <span>Small Creators Signal</span>
                  <span className="badge small">{provenance.signal.small_creator_signal ?? 'N/A'} views/day</span>
                </div>
              </div>
              <div style={{ borderTop: '1px solid var(--border)', paddingTop: '16px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Ratios are calculated using percentile cuts on subscriber counts from candidates returned in search.
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', padding: '24px 0', textAlign: 'center' }}>
              No data signals available yet.
            </div>
          )}
        </div>
      </div>

      {/* Provenance lineage panel */}
      <div className="panel">
        <div className="panel-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <GitFork size={20} style={{ color: 'var(--primary)' }} />
            <h3>Data Provenance Lineage: {selectedDate || 'Select a date'}</h3>
          </div>
          {provenance?.signal && (
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', gap: '16px' }}>
              <span>Population Size: <strong>{provenance.signal.population_size}</strong></span>
              <span>Obs Coverage: <strong>{(provenance.signal.observation_coverage * 100).toFixed(0)}%</strong></span>
            </div>
          )}
        </div>

        {loadingProv ? (
          <div style={{ color: 'var(--text-secondary)', padding: '32px 0', textAlign: 'center' }}>Loading lineage data...</div>
        ) : provenance?.contributions ? (
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Video Title</th>
                  <th>Creator Bucket</th>
                  <th>Selection Score</th>
                  <th>Total Views</th>
                  <th>Velocity</th>
                  <th>Growth</th>
                  <th>Reach Ratio</th>
                  <th>Int. Density</th>
                </tr>
              </thead>
              <tbody>
                {provenance.contributions.map((video, idx) => (
                  <tr key={video.video_id}>
                    <td>#{video.selection_rank || (idx + 1)}</td>
                    <td style={{ fontWeight: '500', maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      <span title={video.title}>{video.title}</span>
                    </td>
                    <td>
                      <span className={`badge ${video.creator_bucket}`}>
                        {video.creator_bucket.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-secondary)' }}>
                      {video.selection_score?.toFixed(3) ?? 'N/A'}
                    </td>
                    <td>{video.view_count?.toLocaleString() ?? 'N/A'}</td>
                    <td style={{ color: 'var(--primary)', fontWeight: '500' }}>
                      {video.view_velocity !== null ? `+${video.view_velocity.toLocaleString()}` : 'N/A'}
                    </td>
                    <td style={{ color: 'var(--secondary)' }}>
                      {video.view_growth !== null ? `${(video.view_growth * 100).toFixed(1)}%` : 'N/A'}
                    </td>
                    <td>{video.reach_ratio?.toFixed(3) ?? 'N/A'}</td>
                    <td>{video.interaction_density?.toFixed(3) ?? 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', padding: '32px 0', textAlign: 'center', fontSize: '0.9rem' }}>
            Please select a date point on the chart to trace signal origins.
          </div>
        )}
      </div>
    </div>
  );
}
