import React from 'react';

export default function StatusCard({
  title,
  value,
  subtext,
  icon,
  accentColor = '#2563eb',
  trend,
  className = '',
}) {
  return (
    <div
      className={`kpi-card ${className}`}
      style={{ '--card-accent': accentColor }}
    >
      <div className="d-flex justify-content-between align-items-start">
        <div className="kpi-title">{title}</div>
        {icon && (
          <i
            className={`bi ${icon} fs-5`}
            style={{ color: accentColor, opacity: 0.85 }}
          ></i>
        )}
      </div>

      <div className="kpi-value font-mono my-1">{value ?? '—'}</div>

      <div className="d-flex justify-content-between align-items-center">
        {subtext && <div className="kpi-subtext">{subtext}</div>}
        {trend && (
          <span className="badge bg-light text-secondary border font-mono small">
            {trend}
          </span>
        )}
      </div>
    </div>
  );
}
