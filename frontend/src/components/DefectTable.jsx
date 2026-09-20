import React from 'react';

export default function DefectTable({ defects = [], onSelectDefect, selectedIndex }) {
  if (!defects || defects.length === 0) {
    return (
      <div className="p-4 text-center text-muted bg-light rounded border">
        <i className="bi bi-shield-check text-success fs-3 d-block mb-2"></i>
        <div className="fw-semibold">No Surface Defects Detected</div>
        <div className="small">The inspected PCB meets baseline quality specifications.</div>
      </div>
    );
  }

  const getSeverityBadgeClass = (sev) => {
    const s = (sev || '').toUpperCase();
    if (s === 'CRITICAL') return 'sev-critical';
    if (s === 'HIGH') return 'sev-high';
    if (s === 'MEDIUM') return 'sev-medium';
    return 'sev-low';
  };

  return (
    <div className="table-responsive">
      <table className="qc-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Defect Class</th>
            <th>Confidence</th>
            <th>Severity Score</th>
            <th>Severity Level</th>
            <th>Coordinates [x1, y1, x2, y2]</th>
          </tr>
        </thead>
        <tbody>
          {defects.map((d, idx) => {
            const isSelected = selectedIndex === idx;
            const bbox = d.bbox || {};
            const coordStr = `[${bbox.x1 ?? 0}, ${bbox.y1 ?? 0}, ${bbox.x2 ?? 0}, ${bbox.y2 ?? 0}]`;
            const confPct = ((d.confidence || 0) * 100).toFixed(1) + '%';
            const sevScore = typeof d.severity_score === 'number' ? d.severity_score.toFixed(3) : '—';
            const sevLevel = d.severity || 'LOW';

            return (
              <tr
                key={idx}
                onClick={() => onSelectDefect && onSelectDefect(idx)}
                style={{
                  cursor: onSelectDefect ? 'pointer' : 'default',
                  backgroundColor: isSelected ? '#eff6ff' : undefined,
                }}
              >
                <td className="font-mono text-muted">{idx + 1}</td>
                <td>
                  <span className="fw-bold text-dark text-capitalize">
                    {d.class_name?.replace(/_/g, ' ') || 'Unknown'}
                  </span>
                </td>
                <td>
                  <span className="font-mono fw-semibold text-primary">{confPct}</span>
                </td>
                <td className="font-mono">{sevScore}</td>
                <td>
                  <span className={`sev-badge ${getSeverityBadgeClass(sevLevel)}`}>
                    {sevLevel}
                  </span>
                </td>
                <td className="font-mono text-secondary small">{coordStr}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
