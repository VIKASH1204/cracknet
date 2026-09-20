import React from 'react';

export default function DecisionBadge({ decision, size = 'md', className = '' }) {
  const norm = (decision || 'UNKNOWN').toUpperCase();

  let badgeClass = 'decision-pass';
  let icon = 'bi-check-circle-fill';

  if (norm === 'REWORK') {
    badgeClass = 'decision-rework';
    icon = 'bi-exclamation-triangle-fill';
  } else if (norm === 'REJECT') {
    badgeClass = 'decision-reject';
    icon = 'bi-x-circle-fill';
  }

  const isLarge = size === 'lg';

  return (
    <span
      className={`decision-badge ${badgeClass} ${isLarge ? 'decision-badge-lg' : ''} ${className}`}
      title={`Quality Decision: ${norm}`}
    >
      <span className="pulse-dot"></span>
      <i className={`bi ${icon} me-1`}></i>
      <span>{norm}</span>
    </span>
  );
}
