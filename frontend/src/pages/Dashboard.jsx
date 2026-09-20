import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Bar, Line } from 'react-chartjs-2';
import StatusCard from '../components/StatusCard';
import DecisionBadge from '../components/DecisionBadge';
import { getDashboardSummary, getDefectDistribution, getInspectionTrends, getHistory } from '../services/api';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [defects, setDefects] = useState([]);
  const [trends, setTrends] = useState([]);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadAll = async () => {
      try {
        setLoading(true);
        const [sumRes, defRes, trendRes, histRes] = await Promise.allSettled([
          getDashboardSummary(),
          getDefectDistribution(),
          getInspectionTrends(14),
          getHistory({ page: 1, limit: 10 }),
        ]);

        if (sumRes.status === 'fulfilled') setSummary(sumRes.value);
        if (defRes.status === 'fulfilled') setDefects(defRes.value);
        if (trendRes.status === 'fulfilled') setTrends(trendRes.value);
        if (histRes.status === 'fulfilled') setRecent(histRes.value.items || []);
      } finally {
        setLoading(false);
      }
    };
    loadAll();
  }, []);

  // Defect Distribution Bar Chart Data
  const defectLabels = defects.map((d) => d.class_name?.replace(/_/g, ' ').toUpperCase() || 'UNKNOWN');
  const defectCounts = defects.map((d) => d.count || 0);

  const barData = {
    labels: defectLabels.length ? defectLabels : ['OPEN', 'SHORT', 'MOUSEBITE', 'SPUR', 'SPURIOUS COPPER', 'PIN HOLE'],
    datasets: [
      {
        label: 'Defect Frequency',
        data: defectCounts.length ? defectCounts : [0, 0, 0, 0, 0, 0],
        backgroundColor: [
          '#ef4444',
          '#f97316',
          '#eab308',
          '#3b82f6',
          '#8b5cf6',
          '#14b8a6',
        ],
        borderRadius: 4,
      },
    ],
  };

  const barOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#0f172a',
        padding: 10,
        titleFont: { family: 'monospace' },
        bodyFont: { family: 'monospace' },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: '#e2e8f0' },
        ticks: { precision: 0, font: { family: 'monospace' } },
      },
      x: {
        grid: { display: false },
        ticks: { font: { size: 11, weight: 'bold' } },
      },
    },
  };

  // Trends Line Chart Data
  const trendLabels = trends.map((t) => t.date?.slice(5) || '');
  const trendTotals = trends.map((t) => t.total || 0);
  const trendRejects = trends.map((t) => t.reject_count || 0);

  const lineData = {
    labels: trendLabels.length ? trendLabels : ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5'],
    datasets: [
      {
        label: 'Total Inspections',
        data: trendTotals.length ? trendTotals : [0, 0, 0, 0, 0],
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37, 99, 235, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 3,
      },
      {
        label: 'Rejects',
        data: trendRejects.length ? trendRejects : [0, 0, 0, 0, 0],
        borderColor: '#dc2626',
        backgroundColor: 'transparent',
        borderDash: [4, 4],
        tension: 0.3,
        pointRadius: 3,
      },
    ],
  };

  const lineOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } },
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: '#e2e8f0' },
        ticks: { precision: 0, font: { family: 'monospace' } },
      },
      x: {
        grid: { display: false },
        ticks: { font: { size: 11, family: 'monospace' } },
      },
    },
  };

  const totalInspections = summary?.total_inspections ?? 0;
  const passCount = summary?.pass_count ?? 0;
  const reworkCount = summary?.rework_count ?? 0;
  const rejectCount = summary?.reject_count ?? 0;
  const totalDefects = summary?.defect_count ?? 0;
  const avgTime = summary?.average_processing_time_ms ?? 0;
  const passRate = totalInspections > 0 ? ((passCount / totalInspections) * 100).toFixed(1) + '%' : '100%';

  return (
    <div>
      {/* Top Header Section */}
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-3">
        <div>
          <h4 className="fw-bold text-dark mb-1">FACTORY QUALITY OVERVIEW</h4>
          <div className="text-secondary small">
            Live PCB surface defect inspection and quality decision metrics across all active lines.
          </div>
        </div>
        <div className="d-flex gap-2">
          <Link to="/live" className="btn btn-primary btn-industrial">
            <i className="bi bi-camera-video me-1"></i>
            Live Camera Inspection
          </Link>
          <Link to="/upload" className="btn btn-outline-secondary btn-industrial">
            <i className="bi bi-cloud-arrow-up me-1"></i>
            Upload PCB
          </Link>
        </div>
      </div>

      {/* KPI Display Cards */}
      <div className="row g-3 mb-4">
        <div className="col-6 col-md-4 col-xl-2">
          <StatusCard
            title="Total PCB"
            value={totalInspections}
            subtext="Lifetime inspections"
            icon="bi-layers"
            accentColor="#2563eb"
          />
        </div>
        <div className="col-6 col-md-4 col-xl-2">
          <StatusCard
            title="PASS"
            value={passCount}
            subtext={`Yield: ${passRate}`}
            icon="bi-check-circle"
            accentColor="#059669"
          />
        </div>
        <div className="col-6 col-md-4 col-xl-2">
          <StatusCard
            title="REWORK"
            value={reworkCount}
            subtext="Secondary repair"
            icon="bi-exclamation-triangle"
            accentColor="#d97706"
          />
        </div>
        <div className="col-6 col-md-4 col-xl-2">
          <StatusCard
            title="REJECT"
            value={rejectCount}
            subtext="Scrap threshold"
            icon="bi-x-circle"
            accentColor="#dc2626"
          />
        </div>
        <div className="col-6 col-md-4 col-xl-2">
          <StatusCard
            title="Total Defects"
            value={totalDefects}
            subtext="Classified anomalies"
            icon="bi-bug"
            accentColor="#7c3aed"
          />
        </div>
        <div className="col-6 col-md-4 col-xl-2">
          <StatusCard
            title="Avg Time"
            value={avgTime ? `${avgTime} ms` : '—'}
            subtext={avgTime ? `~${Math.round(1000 / avgTime)} FPS` : 'Latency'}
            icon="bi-stopwatch"
            accentColor="#0891b2"
          />
        </div>
      </div>

      {/* Charts Section */}
      <div className="row g-3 mb-4">
        <div className="col-12 col-lg-6">
          <div className="qc-card h-100 mb-0">
            <div className="qc-card-header">
              <div className="d-flex align-items-center gap-2">
                <i className="bi bi-bar-chart-fill text-primary"></i>
                <span>DEFECT DISTRIBUTION (DeepPCB Classes)</span>
              </div>
              <span className="badge bg-light text-secondary border small">Total: {totalDefects}</span>
            </div>
            <div className="qc-card-body" style={{ height: '280px' }}>
              <Bar data={barData} options={barOptions} />
            </div>
          </div>
        </div>

        <div className="col-12 col-lg-6">
          <div className="qc-card h-100 mb-0">
            <div className="qc-card-header">
              <div className="d-flex align-items-center gap-2">
                <i className="bi bi-graph-up-arrow text-primary"></i>
                <span>INSPECTION TRENDS (Past 14 Days)</span>
              </div>
              <span className="badge bg-light text-secondary border small">Daily Throughput</span>
            </div>
            <div className="qc-card-body" style={{ height: '280px' }}>
              <Line data={lineData} options={lineOptions} />
            </div>
          </div>
        </div>
      </div>

      {/* Recent Inspections Table */}
      <div className="qc-card">
        <div className="qc-card-header">
          <div className="d-flex align-items-center gap-2">
            <i className="bi bi-clock-history text-primary"></i>
            <span>RECENT FACTORY INSPECTIONS</span>
          </div>
          <Link to="/history" className="small text-decoration-none fw-semibold">
            View All History &rarr;
          </Link>
        </div>
        <div className="table-responsive">
          <table className="qc-table mb-0">
            <thead>
              <tr>
                <th>PCB ID</th>
                <th>Date / Time</th>
                <th>Defects</th>
                <th>Severity</th>
                <th>Quality Decision</th>
                <th>Inference Time</th>
                <th className="text-end">Action</th>
              </tr>
            </thead>
            <tbody>
              {recent.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center text-muted py-4">
                    {loading ? 'Loading recent inspections...' : 'No inspections recorded yet. Start by uploading or capturing a PCB.'}
                  </td>
                </tr>
              ) : (
                recent.map((item) => (
                  <tr key={item.inspection_id || item._id}>
                    <td>
                      <span className="font-mono fw-bold text-dark">
                        {item.pcb_id || 'PCB-UNKNOWN'}
                      </span>
                    </td>
                    <td className="font-mono text-secondary small">
                      {item.timestamp ? new Date(item.timestamp).toLocaleString() : '—'}
                    </td>
                    <td>
                      <span className="badge bg-light text-dark border font-mono">
                        {item.defect_count ?? item.defects?.length ?? 0}
                      </span>
                    </td>
                    <td>
                      <span className="badge bg-secondary-subtle text-secondary small">
                        {item.highest_severity || 'LOW'}
                      </span>
                    </td>
                    <td>
                      <DecisionBadge decision={item.decision} size="sm" />
                    </td>
                    <td className="font-mono text-secondary small">
                      {item.processing_time_ms ? `${item.processing_time_ms.toFixed(1)} ms` : '—'}
                    </td>
                    <td className="text-end">
                      <Link
                        to={`/inspection/${item.inspection_id || item._id}`}
                        className="btn btn-outline-primary btn-sm py-0 px-2"
                      >
                        Inspect &rarr;
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
