import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import DecisionBadge from '../components/DecisionBadge';
import InspectionImage from '../components/InspectionImage';
import DefectTable from '../components/DefectTable';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import { getInspection } from '../services/api';

export default function InspectionDetails() {
  const { id } = useParams();
  const [inspection, setInspection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedIndex, setSelectedIndex] = useState(null);

  useEffect(() => {
    const fetchInspection = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getInspection(id);
        setInspection(data);
      } catch (err) {
        console.error('Fetch inspection error:', err);
        setError(err.response?.data?.detail || 'Could not load inspection record.');
      } finally {
        setLoading(false);
      }
    };
    if (id) {
      fetchInspection();
    }
  }, [id]);

  if (loading) return <LoadingSpinner message="Fetching Historical Inspection..." />;
  if (error) return <ErrorMessage message={error} />;
  if (!inspection) return <div className="alert alert-warning">Inspection not found.</div>;

  const defects = inspection.defects || [];
  const procTime = inspection.processing_time_ms;

  return (
    <div>
      {/* Header */}
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-2">
        <div>
          <div className="text-secondary small font-mono mb-1">
            <Link to="/history" className="text-decoration-none">
              &larr; Back to Inspection History
            </Link>
          </div>
          <h4 className="fw-bold text-dark mb-0">
            INSPECTION RECORD: <span className="font-mono text-primary">{inspection.pcb_id || inspection.inspection_id}</span>
          </h4>
        </div>
        <div className="d-flex gap-2">
          <Link to="/upload" className="btn btn-outline-primary btn-industrial">
            <i className="bi bi-cloud-arrow-up me-1"></i>
            New Inspection
          </Link>
        </div>
      </div>

      {/* Main Inspection Result Layout: LEFT Image, RIGHT Summary */}
      <div className="row g-3 mb-4">
        {/* LEFT: Image Viewer */}
        <div className="col-12 col-xl-7">
          <InspectionImage
            imageUrl={inspection.image_url}
            resultImageUrl={inspection.result_image_url}
            explainabilityUrl={inspection.explainability_url}
            defects={defects}
            selectedIndex={selectedIndex}
            onSelectDefect={setSelectedIndex}
          />
        </div>

        {/* RIGHT: Inspection Summary */}
        <div className="col-12 col-xl-5">
          <div className="qc-card mb-3">
            <div className="qc-card-header">
              <span>Inspection Quality Summary</span>
              <DecisionBadge decision={inspection.decision} size="sm" />
            </div>
            <div className="qc-card-body p-3">
              <div className="d-flex justify-content-center my-3">
                <DecisionBadge decision={inspection.decision} size="lg" />
              </div>

              <ul className="list-group list-group-flush font-mono small">
                <li className="list-group-item d-flex justify-content-between px-0">
                  <span className="text-muted">PCB ID:</span>
                  <span className="fw-bold text-dark">{inspection.pcb_id || '—'}</span>
                </li>
                <li className="list-group-item d-flex justify-content-between px-0">
                  <span className="text-muted">Inspection Timestamp:</span>
                  <span className="text-dark">
                    {inspection.timestamp ? new Date(inspection.timestamp).toLocaleString() : '—'}
                  </span>
                </li>
                <li className="list-group-item d-flex justify-content-between px-0">
                  <span className="text-muted">Processing Time:</span>
                  <span className="text-primary fw-bold">
                    {procTime ? `${procTime.toFixed(1)} ms` : '—'}
                  </span>
                </li>
                <li className="list-group-item d-flex justify-content-between px-0">
                  <span className="text-muted">Total Defects:</span>
                  <span className="badge bg-danger-subtle text-danger border border-danger-subtle">
                    {inspection.defect_count ?? defects.length}
                  </span>
                </li>
                <li className="list-group-item d-flex justify-content-between px-0">
                  <span className="text-muted">Highest Defect Severity:</span>
                  <span className="fw-bold text-dark">{inspection.highest_severity || 'LOW'}</span>
                </li>
                <li className="list-group-item d-flex justify-content-between px-0">
                  <span className="text-muted">Decision Rule Engine:</span>
                  <span className="text-success">Automated Rework/Reject Pass Criteria</span>
                </li>
              </ul>
            </div>
          </div>

          <div className="qc-card mb-0">
            <div className="qc-card-header">
              <i className="bi bi-info-circle text-primary me-2"></i>
              <span>Expert-Defined Severity Index</span>
            </div>
            <div className="qc-card-body p-3 small text-muted">
              Defect classifications are evaluated against industrial geometric tolerance models. Spurious shorts and severe opens warrant immediate rejection to prevent assembly line shorts.
            </div>
          </div>
        </div>
      </div>

      {/* BOTTOM: Detected Defects Table */}
      <div className="qc-card">
        <div className="qc-card-header d-flex justify-content-between align-items-center">
          <div className="d-flex align-items-center gap-2">
            <i className="bi bi-list-columns text-primary"></i>
            <span>CLASSIFIED DEFECTS BREAKDOWN ({defects.length})</span>
          </div>
          <span className="badge bg-light text-secondary border font-mono small">
            CrackXNet Multi-Head Output
          </span>
        </div>
        <div className="qc-card-body p-0">
          <DefectTable
            defects={defects}
            selectedIndex={selectedIndex}
            onSelectDefect={setSelectedIndex}
          />
        </div>
      </div>
    </div>
  );
}
