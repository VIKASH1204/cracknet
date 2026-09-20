import React, { useState, useEffect } from 'react';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Filler,
  RadialLinearScale,
} from 'chart.js';
import { Doughnut, Bar, Line } from 'react-chartjs-2';
import StatusCard from '../components/StatusCard';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import {
  getDashboardSummary,
  getDefectDistribution,
  getSeverityDistribution,
  getInspectionTrends,
} from '../services/api';

ChartJS.register(
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Filler,
  RadialLinearScale
);

export default function Analytics() {
  const [summary, setSummary] = useState(null);
  const [defects, setDefects] = useState([]);
  const [severities, setSeverities] = useState([]);
  const [trends, setTrends] = useState([]);
  const [timeRangeDays, setTimeRangeDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [sumRes, defRes, sevRes, trendRes] = await Promise.all([
          getDashboardSummary(),
          getDefectDistribution(),
          getSeverityDistribution(),
          getInspectionTrends(timeRangeDays),
        ]);
        setSummary(sumRes);
        setDefects(defRes);
        setSeverities(sevRes);
        setTrends(trendRes);
      } catch (err) {
        console.error('Analytics fetch error:', err);
        setError('Failed to load quality analytics data.');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [timeRangeDays]);

  if (loading) return <LoadingSpinner message="Calculating Statistical Quality Analytics..." />;

  // 1. Decision Breakdown Doughnut Data
  const passCount = summary?.pass_count || 0;
  const reworkCount = summary?.rework_count || 0;
  const rejectCount = summary?.reject_count || 0;
  const total = summary?.total_inspections || 0;

  const doughnutData = {
    labels: ['PASS', 'REWORK', 'REJECT'],
    datasets: [
      {
        data: total > 0 ? [passCount, reworkCount, rejectCount] : [1, 0, 0],
        backgroundColor: ['#059669', '#d97706', '#dc2626'],
        borderWidth: 2,
        borderColor: '#ffffff',
      },
    ],
  };

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { boxWidth: 12, font: { weight: 'bold' } } },
    },
    cutout: '70%',
  };

  // 2. Defect Category Frequency Bar Data
  const barData = {
    labels: defects.map((d) => d.class_name?.replace(/_/g, ' ').toUpperCase() || ''),
    datasets: [
      {
        label: 'Occurrence Count',
        data: defects.map((d) => d.count || 0),
        backgroundColor: '#2563eb',
        borderRadius: 4,
      },
    ],
  };

  const barOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, ticks: { precision: 0, font: { family: 'monospace' } } },
      x: { ticks: { font: { size: 10, weight: 'bold' } } },
    },
  };

  // 3. Severity Breakdown Bar Data
  const severityLabels = severities.map((s) => s.severity || '');
  const severityCounts = severities.map((s) => s.count || 0);

  const severityBarData = {
    labels: severityLabels.length ? severityLabels : ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'],
    datasets: [
      {
        label: 'Defect Severity Count',
        data: severityCounts.length ? severityCounts : [0, 0, 0, 0],
        backgroundColor: ['#0284c7', '#eab308', '#f97316', '#ef4444'],
        borderRadius: 4,
      },
    ],
  };

  const severityBarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, ticks: { precision: 0, font: { family: 'monospace' } } },
      x: { ticks: { font: { size: 11, weight: 'bold' } } },
    },
  };

  // 4. Daily Inspection Trends Line Data
  const lineData = {
    labels: trends.map((t) => t.date?.slice(5) || ''),
    datasets: [
      {
        label: 'Total Inspected',
        data: trends.map((t) => t.total || 0),
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37, 99, 235, 0.08)',
        fill: true,
        tension: 0.2,
      },
      {
        label: 'Passed',
        data: trends.map((t) => t.pass_count || 0),
        borderColor: '#059669',
        borderDash: [3, 3],
        tension: 0.2,
      },
      {
        label: 'Rejected',
        data: trends.map((t) => t.reject_count || 0),
        borderColor: '#dc2626',
        tension: 0.2,
      },
    ],
  };

  const lineOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top', labels: { boxWidth: 12 } },
    },
    scales: {
      y: { beginAtZero: true, ticks: { precision: 0, font: { family: 'monospace' } } },
      x: { ticks: { font: { size: 10, family: 'monospace' } } },
    },
  };

  const yieldRate = total > 0 ? ((passCount / total) * 100).toFixed(2) + '%' : '100.00%';
  const scrapRate = total > 0 ? ((rejectCount / total) * 100).toFixed(2) + '%' : '0.00%';
  const avgLatency = summary?.average_processing_time_ms || 0;

  return (
    <div>
      {/* Title */}
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-2">
        <div>
          <h4 className="fw-bold text-dark mb-1">FACTORY QUALITY ANALYTICS</h4>
          <div className="text-secondary small">
            Long-term defect prevalence, yield distributions, and inspection throughput.
          </div>
        </div>

        {/* Reporting Period Filter */}
        <div className="d-flex align-items-center gap-2">
          <span className="small text-muted fw-bold">Time Window:</span>
          <div className="btn-group btn-group-sm">
            {[7, 14, 30].map((d) => (
              <button
                key={d}
                type="button"
                className={`btn ${timeRangeDays === d ? 'btn-primary' : 'btn-outline-secondary'}`}
                onClick={() => setTimeRangeDays(d)}
              >
                {d} Days
              </button>
            ))}
          </div>
        </div>
      </div>

      <ErrorMessage message={error} />

      {/* KPI Row */}
      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <StatusCard
            title="First Pass Yield (FPY)"
            value={yieldRate}
            subtext="Production target: >95.0%"
            icon="bi-pie-chart"
            accentColor="#059669"
          />
        </div>
        <div className="col-6 col-md-3">
          <StatusCard
            title="Scrap Rate"
            value={scrapRate}
            subtext="Production target: <2.0%"
            icon="bi-trash"
            accentColor="#dc2626"
          />
        </div>
        <div className="col-6 col-md-3">
          <StatusCard
            title="Total Anomalies"
            value={summary?.defect_count ?? 0}
            subtext="Detected surface flaws"
            icon="bi-exclamation-diamond"
            accentColor="#d97706"
          />
        </div>
        <div className="col-6 col-md-3">
          <StatusCard
            title="Average Latency"
            value={avgLatency ? `${avgLatency} ms` : '—'}
            subtext={avgLatency ? `Throughput: ~${Math.round(1000 / avgLatency)} FPS` : ''}
            icon="bi-speedometer2"
            accentColor="#2563eb"
          />
        </div>
      </div>

      {/* Charts Row 1: Decision Donut & Defect Distribution */}
      <div className="row g-3 mb-4">
        <div className="col-12 col-md-4">
          <div className="qc-card h-100 mb-0">
            <div className="qc-card-header">
              <span>Quality Decision Ratio</span>
            </div>
            <div className="qc-card-body d-flex flex-column align-items-center justify-content-center" style={{ height: '280px' }}>
              <div style={{ width: '200px', height: '200px' }}>
                <Doughnut data={doughnutData} options={doughnutOptions} />
              </div>
            </div>
          </div>
        </div>

        <div className="col-12 col-md-8">
          <div className="qc-card h-100 mb-0">
            <div className="qc-card-header">
              <span>Defect Class Prevalence (DeepPCB Classes)</span>
            </div>
            <div className="qc-card-body" style={{ height: '280px' }}>
              <Bar data={barData} options={barOptions} />
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row 2: Severity Distribution & Daily Inspection Volume */}
      <div className="row g-3 mb-4">
        <div className="col-12 col-md-5">
          <div className="qc-card h-100 mb-0">
            <div className="qc-card-header">
              <span>Defect Severity Grading</span>
            </div>
            <div className="qc-card-body" style={{ height: '280px' }}>
              <Bar data={severityBarData} options={severityBarOptions} />
            </div>
          </div>
        </div>

        <div className="col-12 col-md-7">
          <div className="qc-card h-100 mb-0">
            <div className="qc-card-header">
              <span>Daily Throughput & Yield Trends ({timeRangeDays} Days)</span>
            </div>
            <div className="qc-card-body" style={{ height: '280px' }}>
              <Line data={lineData} options={lineOptions} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
