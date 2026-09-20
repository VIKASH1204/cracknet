import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import DecisionBadge from '../components/DecisionBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import { getHistory, getHistoryExportUrl } from '../services/api';

const DEFECT_CLASSES = ['open', 'short', 'mousebite', 'spur', 'spurious_copper', 'pin_hole'];
const SEVERITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
const DECISIONS = ['PASS', 'REWORK', 'REJECT'];

export default function InspectionHistory() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(15);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [searchPcbId, setSearchPcbId] = useState('');
  const [selectedDecision, setSelectedDecision] = useState('');
  const [selectedDefect, setSelectedDefect] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        page,
        limit,
        pcb_id: searchPcbId || undefined,
        decision: selectedDecision || undefined,
        defect: selectedDefect || undefined,
        severity: selectedSeverity || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      };
      const data = await getHistory(params);
      setItems(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error('History fetch error:', err);
      setError(err.response?.data?.detail || 'Failed to fetch inspection history.');
    } finally {
      setLoading(false);
    }
  }, [page, limit, searchPcbId, selectedDecision, selectedDefect, selectedSeverity, dateFrom, dateTo]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchHistory();
  };

  const handleResetFilters = () => {
    setSearchPcbId('');
    setSelectedDecision('');
    setSelectedDefect('');
    setSelectedSeverity('');
    setDateFrom('');
    setDateTo('');
    setPage(1);
  };

  const exportUrl = getHistoryExportUrl({
    pcb_id: searchPcbId || undefined,
    decision: selectedDecision || undefined,
    defect: selectedDefect || undefined,
    severity: selectedSeverity || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  });

  const totalPages = Math.ceil(total / limit) || 1;

  return (
    <div>
      {/* Title */}
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-2">
        <div>
          <h4 className="fw-bold text-dark mb-1">INSPECTION AUDIT LOG & HISTORY</h4>
          <div className="text-secondary small">
            Filter, search, and export all past automated PCB defect inspection decisions.
          </div>
        </div>
        <div className="d-flex gap-2">
          <a
            href={exportUrl}
            download="crackxnet_inspection_report.csv"
            className="btn btn-outline-success btn-industrial"
          >
            <i className="bi bi-file-earmark-spreadsheet me-1"></i>
            Export CSV Report
          </a>
          <button
            type="button"
            className="btn btn-outline-secondary btn-industrial"
            onClick={fetchHistory}
          >
            <i className="bi bi-arrow-clockwise me-1"></i>
            Refresh Records
          </button>
        </div>
      </div>

      <ErrorMessage message={error} onRetry={fetchHistory} />

      {/* Filter Control Bar */}
      <div className="qc-card mb-4">
        <div className="qc-card-header">
          <i className="bi bi-funnel text-primary me-2"></i>
          <span>Search & Filter Parameters</span>
        </div>
        <div className="qc-card-body p-3">
          <form onSubmit={handleSearchSubmit} className="row g-2 align-items-end">
            <div className="col-12 col-md-3">
              <label className="form-label small fw-bold text-muted mb-1">Search PCB ID</label>
              <div className="input-group input-group-sm">
                <span className="input-group-text bg-white">
                  <i className="bi bi-search text-muted"></i>
                </span>
                <input
                  type="text"
                  className="form-control font-mono"
                  placeholder="e.g. PCB-63C"
                  value={searchPcbId}
                  onChange={(e) => setSearchPcbId(e.target.value)}
                />
              </div>
            </div>

            <div className="col-6 col-md-2">
              <label className="form-label small fw-bold text-muted mb-1">Decision</label>
              <select
                className="form-select form-select-sm"
                value={selectedDecision}
                onChange={(e) => {
                  setSelectedDecision(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">All Decisions</option>
                {DECISIONS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            <div className="col-6 col-md-2">
              <label className="form-label small fw-bold text-muted mb-1">Defect Type</label>
              <select
                className="form-select form-select-sm"
                value={selectedDefect}
                onChange={(e) => {
                  setSelectedDefect(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">All Defect Types</option>
                {DEFECT_CLASSES.map((c) => (
                  <option key={c} value={c}>
                    {c.replace(/_/g, ' ').toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            <div className="col-6 col-md-2">
              <label className="form-label small fw-bold text-muted mb-1">Severity</label>
              <select
                className="form-select form-select-sm"
                value={selectedSeverity}
                onChange={(e) => {
                  setSelectedSeverity(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">All Severities</option>
                {SEVERITIES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div className="col-6 col-md-3 d-flex gap-2">
              <button type="submit" className="btn btn-primary btn-sm flex-grow-1">
                Filter
              </button>
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm"
                onClick={handleResetFilters}
              >
                Reset
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* History Table */}
      <div className="qc-card">
        <div className="qc-card-header d-flex justify-content-between align-items-center">
          <span>Inspection Records</span>
          <span className="badge bg-light text-secondary border font-mono small">
            Total Records: {total}
          </span>
        </div>

        {loading ? (
          <div className="p-5 text-center">
            <div className="spinner-border spinner-border-sm text-primary me-2"></div>
            <span className="text-muted">Loading historical inspections...</span>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="qc-table mb-0">
              <thead>
                <tr>
                  <th>PCB ID</th>
                  <th>Date / Time</th>
                  <th>Defect Count</th>
                  <th>Highest Severity</th>
                  <th>Quality Decision</th>
                  <th>Latency</th>
                  <th className="text-end">Inspection Details</th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="text-center text-muted py-4">
                      No inspection records match the selected filters.
                    </td>
                  </tr>
                ) : (
                  items.map((r) => (
                    <tr key={r.inspection_id || r._id}>
                      <td>
                        <span className="font-mono fw-bold text-dark">
                          {r.pcb_id || 'PCB-UNKNOWN'}
                        </span>
                      </td>
                      <td className="font-mono text-secondary small">
                        {r.timestamp ? new Date(r.timestamp).toLocaleString() : '—'}
                      </td>
                      <td>
                        <span className="badge bg-light text-dark border font-mono">
                          {r.defect_count ?? r.defects?.length ?? 0}
                        </span>
                      </td>
                      <td>
                        <span className="badge bg-secondary-subtle text-secondary small">
                          {r.highest_severity || 'LOW'}
                        </span>
                      </td>
                      <td>
                        <DecisionBadge decision={r.decision} size="sm" />
                      </td>
                      <td className="font-mono text-secondary small">
                        {r.processing_time_ms ? `${r.processing_time_ms.toFixed(1)} ms` : '—'}
                      </td>
                      <td className="text-end">
                        <Link
                          to={`/inspection/${r.inspection_id || r._id}`}
                          className="btn btn-outline-primary btn-sm py-0 px-2"
                        >
                          View &rarr;
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        {totalPages > 1 && (
          <div className="p-3 border-top d-flex justify-content-between align-items-center">
            <span className="small text-muted font-mono">
              Page {page} of {totalPages} ({total} items)
            </span>
            <div className="btn-group btn-group-sm">
              <button
                type="button"
                className="btn btn-outline-secondary"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                &larr; Prev
              </button>
              <button
                type="button"
                className="btn btn-outline-secondary"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next &rarr;
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
