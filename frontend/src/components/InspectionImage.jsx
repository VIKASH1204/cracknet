import React, { useState, useRef, useEffect } from 'react';

export default function InspectionImage({
  imageUrl,
  resultImageUrl,
  explainabilityUrl,
  defects = [],
  selectedIndex = null,
  onSelectDefect,
}) {
  const [viewMode, setViewMode] = useState('annotated'); // 'annotated' | 'explainability' | 'original' | 'split'
  const [showBoxes, setShowBoxes] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const imgRef = useRef(null);
  const [naturalSize, setNaturalSize] = useState({ width: 640, height: 480 });

  const onImageLoad = (e) => {
    setNaturalSize({
      width: e.target.naturalWidth || 640,
      height: e.target.naturalHeight || 480,
    });
  };

  const getSeverityColor = (sev) => {
    const s = (sev || '').toUpperCase();
    if (s === 'CRITICAL') return '#ef4444';
    if (s === 'HIGH') return '#f97316';
    if (s === 'MEDIUM') return '#eab308';
    return '#0284c7';
  };

  // Determine which image URL to display
  let activeImgSrc = resultImageUrl || imageUrl;
  if (viewMode === 'original') activeImgSrc = imageUrl;
  if (viewMode === 'explainability') activeImgSrc = explainabilityUrl || resultImageUrl || imageUrl;

  return (
    <div className="qc-card mb-0">
      {/* Viewer Controls Toolbar */}
      <div className="qc-card-header d-flex flex-wrap align-items-center justify-content-between gap-2">
        <div className="d-flex align-items-center gap-1">
          <div className="btn-group btn-group-sm" role="group">
            <button
              type="button"
              className={`btn ${viewMode === 'annotated' ? 'btn-primary' : 'btn-outline-secondary'}`}
              onClick={() => setViewMode('annotated')}
              title="Detection Result Overlay"
            >
              <i className="bi bi-bounding-box-circles me-1"></i>
              Detection Overlay
            </button>
            <button
              type="button"
              className={`btn ${viewMode === 'explainability' ? 'btn-primary' : 'btn-outline-secondary'}`}
              onClick={() => setViewMode('explainability')}
              disabled={!explainabilityUrl}
              title="Saliency / Attention Heatmap"
            >
              <i className="bi bi-eye me-1"></i>
              Explainability Map
            </button>
            <button
              type="button"
              className={`btn ${viewMode === 'original' ? 'btn-primary' : 'btn-outline-secondary'}`}
              onClick={() => setViewMode('original')}
              title="Raw PCB Image"
            >
              <i className="bi bi-image me-1"></i>
              Original PCB
            </button>
            <button
              type="button"
              className={`btn ${viewMode === 'split' ? 'btn-primary' : 'btn-outline-secondary'}`}
              onClick={() => setViewMode('split')}
              title="Side-by-Side Comparison"
            >
              <i className="bi bi-layout-split me-1"></i>
              Split View
            </button>
          </div>
        </div>

        {viewMode !== 'split' && (
          <div className="d-flex align-items-center gap-2">
            <div className="form-check form-switch form-check-inline m-0 small">
              <input
                className="form-check-input"
                type="checkbox"
                id="toggleBBoxes"
                checked={showBoxes}
                onChange={(e) => setShowBoxes(e.target.checked)}
              />
              <label className="form-check-label text-muted small" htmlFor="toggleBBoxes">
                Boxes
              </label>
            </div>
            <div className="form-check form-switch form-check-inline m-0 small">
              <input
                className="form-check-input"
                type="checkbox"
                id="toggleLabels"
                checked={showLabels}
                onChange={(e) => setShowLabels(e.target.checked)}
              />
              <label className="form-check-label text-muted small" htmlFor="toggleLabels">
                Labels
              </label>
            </div>
          </div>
        )}
      </div>

      {/* Main Image Display */}
      <div className="qc-card-body p-2 bg-dark">
        {viewMode === 'split' ? (
          <div className="row g-2">
            <div className="col-12 col-md-6">
              <div className="text-white small mb-1 text-center font-mono">Original PCB</div>
              <div className="inspection-viewer" style={{ minHeight: '320px' }}>
                <img
                  src={imageUrl}
                  alt="Original PCB"
                  className="inspection-img"
                  style={{ maxHeight: '420px' }}
                />
              </div>
            </div>
            <div className="col-12 col-md-6">
              <div className="text-white small mb-1 text-center font-mono">Detection Result</div>
              <div className="inspection-viewer" style={{ minHeight: '320px' }}>
                <img
                  src={resultImageUrl || imageUrl}
                  alt="Annotated PCB"
                  className="inspection-img"
                  style={{ maxHeight: '420px' }}
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="inspection-viewer">
            <div className="inspection-canvas-wrapper position-relative">
              <img
                ref={imgRef}
                src={activeImgSrc}
                alt="PCB Inspection"
                className="inspection-img"
                onLoad={onImageLoad}
              />

              {/* Dynamic SVG Bounding Box Overlay for precise interactive inspection */}
              {showBoxes && viewMode !== 'explainability' && defects.length > 0 && (
                <svg
                  className="bbox-overlay position-absolute top-0 start-0 w-100 h-100"
                  viewBox={`0 0 ${naturalSize.width} ${naturalSize.height}`}
                  preserveAspectRatio="none"
                >
                  {defects.map((defect, idx) => {
                    const bbox = defect.bbox || {};
                    const x = bbox.x1 ?? 0;
                    const y = bbox.y1 ?? 0;
                    const w = Math.max(1, (bbox.x2 ?? 0) - x);
                    const h = Math.max(1, (bbox.y2 ?? 0) - y);
                    const isSelected = selectedIndex === idx;
                    const color = getSeverityColor(defect.severity);
                    const label = `${(defect.class_name || 'DEFECT').toUpperCase()} ${((defect.confidence || 0) * 100).toFixed(1)}%`;

                    return (
                      <g
                        key={idx}
                        style={{ cursor: 'pointer', pointerEvents: 'auto' }}
                        onClick={() => onSelectDefect && onSelectDefect(idx)}
                      >
                        {/* Bounding Box Rectangle */}
                        <rect
                          x={x}
                          y={y}
                          width={w}
                          height={h}
                          fill={isSelected ? `${color}44` : 'none'}
                          stroke={color}
                          strokeWidth={isSelected ? 3 : 2}
                          strokeDasharray={defect.severity === 'CRITICAL' ? '4 2' : 'none'}
                        />

                        {/* Label Badge */}
                        {showLabels && (
                          <g>
                            <rect
                              x={x}
                              y={Math.max(0, y - 18)}
                              width={Math.min(180, label.length * 8.5)}
                              height={18}
                              fill={color}
                              rx={2}
                            />
                            <text
                              x={x + 4}
                              y={Math.max(12, y - 5)}
                              fill="#ffffff"
                              fontSize="11"
                              fontFamily="monospace"
                              fontWeight="bold"
                            >
                              {label}
                            </text>
                          </g>
                        )}
                      </g>
                    );
                  })}
                </svg>
              )}
            </div>
          </div>
        )}

        {/* Explainability Explanation Note */}
        {viewMode === 'explainability' && (
          <div className="alert alert-secondary text-dark small m-2 py-2 mb-0">
            <i className="bi bi-info-circle-fill me-2 text-primary"></i>
            <strong>Explainability Heatmap:</strong> Highlighted warm regions indicate feature areas contributing most strongly to the CrackXNet prediction.
          </div>
        )}
      </div>
    </div>
  );
}
