import React from 'react';

export default function ErrorMessage({ title = 'Inspection Error', message, onRetry }) {
  if (!message) return null;

  return (
    <div className="alert alert-danger d-flex align-items-center justify-content-between p-3 rounded border border-danger-subtle shadow-sm my-3" role="alert">
      <div className="d-flex align-items-center gap-3">
        <i className="bi bi-exclamation-octagon-fill fs-3 text-danger"></i>
        <div>
          <h6 className="alert-heading fw-bold mb-1">{title}</h6>
          <div className="small text-secondary">{message}</div>
        </div>
      </div>
      {onRetry && (
        <button
          type="button"
          className="btn btn-outline-danger btn-sm fw-semibold"
          onClick={onRetry}
        >
          <i className="bi bi-arrow-clockwise me-1"></i>
          Retry
        </button>
      )}
    </div>
  );
}
