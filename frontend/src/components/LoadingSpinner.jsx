import React from 'react';

export default function LoadingSpinner({ message = 'Analyzing PCB with CrackXNet AI...' }) {
  return (
    <div className="qc-card text-center p-5">
      <div className="spinner-border text-primary mb-3" style={{ width: '3rem', height: '3rem' }} role="status">
        <span className="visually-hidden">Loading...</span>
      </div>
      <h5 className="fw-bold text-dark mb-2">{message}</h5>
      <p className="text-muted small mb-4">
        Extracting multi-scale features, computing attention maps, and performing defect bounding-box regression...
      </p>

      {/* Industrial Pipeline Step Indicators */}
      <div className="d-flex justify-content-center gap-3 flex-wrap">
        <span className="badge bg-light text-secondary border font-mono">
          <i className="bi bi-cpu text-primary me-1"></i>
          EfficientNet-B0
        </span>
        <span className="badge bg-light text-secondary border font-mono">
          <i className="bi bi-eye text-primary me-1"></i>
          CBAM Attention
        </span>
        <span className="badge bg-light text-secondary border font-mono">
          <i className="bi bi-layers text-primary me-1"></i>
          AFFM + FPN
        </span>
        <span className="badge bg-light text-secondary border font-mono">
          <i className="bi bi-shield-check text-primary me-1"></i>
          Quality Decision Engine
        </span>
      </div>
    </div>
  );
}
