import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import DecisionBadge from '../components/DecisionBadge';
import InspectionImage from '../components/InspectionImage';
import DefectTable from '../components/DefectTable';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import { uploadInspection } from '../services/api';

export default function UploadInspection() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [pcbId, setPcbId] = useState('');
  const [operatorId, setOperatorId] = useState('OP-01');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileSelect = (selectedFile) => {
    if (!selectedFile) return;
    const ext = selectedFile.name.split('.').pop().toLowerCase();
    if (!['jpg', 'jpeg', 'png'].includes(ext)) {
      setError('Invalid file type. Only JPG, JPEG, and PNG images are supported.');
      return;
    }
    setFile(selectedFile);
    setError(null);
    setResult(null);
    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);
    if (!pcbId) {
      setPcbId(`PCB-${Date.now().toString().slice(-6)}`);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleLoadSample = () => {
    // Generate a high-contrast synthetic PCB image for testing
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 480;
    const ctx = canvas.getContext('2d');

    // PCB substrate
    ctx.fillStyle = '#0f4c28';
    ctx.fillRect(0, 0, 640, 480);

    // Traces
    ctx.strokeStyle = '#c99716';
    ctx.lineWidth = 3;
    for (let x = 40; x < 640; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, 480);
      ctx.stroke();
    }
    for (let y = 40; y < 480; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(640, y);
      ctx.stroke();
    }

    // Pads
    ctx.fillStyle = '#f59e0b';
    for (let i = 0; i < 24; i++) {
      const px = 60 + ((i * 45) % 520);
      const py = 50 + ((i * 35) % 380);
      ctx.beginPath();
      ctx.arc(px, py, 8, 0, 2 * Math.PI);
      ctx.fill();
    }

    // Defect anomalies: spur and bridge
    ctx.fillStyle = '#dc2626';
    ctx.fillRect(200, 160, 20, 8);
    ctx.fillRect(360, 240, 12, 12);

    canvas.toBlob((blob) => {
      if (blob) {
        const sampleFile = new File([blob], 'sample_pcb_board.png', { type: 'image/png' });
        handleFileSelect(sampleFile);
      }
    }, 'image/png');
  };

  const handleRunInspection = async (e) => {
    if (e) e.preventDefault();
    if (!file) {
      setError('Please select or drop a PCB image first.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('pcb_id', pcbId || `PCB-${Date.now().toString().slice(-6)}`);
      formData.append('operator_id', operatorId || 'OP-01');

      const data = await uploadInspection(formData);
      setResult(data);
    } catch (err) {
      console.error('Upload inspection error:', err);
      setError(err.response?.data?.detail || err.message || 'Inspection failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setPreviewUrl(null);
    setResult(null);
    setPcbId('');
    setError(null);
  };

  return (
    <div>
      {/* Page Title */}
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-2">
        <div>
          <h4 className="fw-bold text-dark mb-1">OPTICAL PCB IMAGE UPLOAD</h4>
          <div className="text-secondary small">
            Submit high-resolution optical PCB images (JPG / PNG) for automated surface defect detection.
          </div>
        </div>
        {result && (
          <button
            type="button"
            className="btn btn-outline-secondary btn-industrial"
            onClick={handleReset}
          >
            <i className="bi bi-arrow-repeat me-1"></i>
            Upload Another PCB
          </button>
        )}
      </div>

      <ErrorMessage message={error} onRetry={() => setError(null)} />

      {!result && (
        <div className="row g-3">
          <div className="col-12 col-lg-8">
            <div className="qc-card">
              <div className="qc-card-header d-flex justify-content-between align-items-center">
                <span>Upload PCB Image</span>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-primary"
                  onClick={handleLoadSample}
                >
                  <i className="bi bi-magic me-1"></i>
                  Load Sample PCB Image
                </button>
              </div>
              <div className="qc-card-body p-4">
                {/* Drag and Drop Box */}
                <div
                  className={`upload-dropzone ${isDragging ? 'active' : ''}`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".jpg,.jpeg,.png"
                    style={{ display: 'none' }}
                    onChange={(e) => handleFileSelect(e.target.files[0])}
                  />

                  {previewUrl ? (
                    <div>
                      <img
                        src={previewUrl}
                        alt="Selected PCB"
                        style={{ maxHeight: '220px', maxWidth: '100%', objectFit: 'contain' }}
                        className="rounded border mb-3"
                      />
                      <div className="fw-bold text-dark">{file?.name}</div>
                      <div className="text-muted small">
                        {file ? `${(file.size / 1024).toFixed(1)} KB` : ''} &bull; Click or drop another image to replace
                      </div>
                    </div>
                  ) : (
                    <div>
                      <i className="bi bi-cloud-arrow-up text-primary" style={{ fontSize: '3rem' }}></i>
                      <h5 className="fw-bold text-dark mt-2 mb-1">Drag and Drop PCB Image Here</h5>
                      <p className="text-secondary small mb-3">
                        Supported formats: <span className="font-mono">JPG, JPEG, PNG</span> (Up to 20 MB)
                      </p>
                      <button type="button" className="btn btn-primary btn-industrial">
                        Browse Local Files
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Metadata & Submit Controls */}
          <div className="col-12 col-lg-4">
            <div className="qc-card">
              <div className="qc-card-header">
                <span>Inspection Parameters</span>
              </div>
              <div className="qc-card-body p-3">
                <form onSubmit={handleRunInspection}>
                  <div className="mb-3">
                    <label className="form-label small fw-bold text-muted">PCB Identifier</label>
                    <input
                      type="text"
                      className="form-control font-mono"
                      placeholder="e.g. PCB-2026-A1"
                      value={pcbId}
                      onChange={(e) => setPcbId(e.target.value)}
                    />
                    <div className="form-text small">Auto-generated if left blank.</div>
                  </div>

                  <div className="mb-3">
                    <label className="form-label small fw-bold text-muted">Operator Station ID</label>
                    <input
                      type="text"
                      className="form-control font-mono"
                      value={operatorId}
                      onChange={(e) => setOperatorId(e.target.value)}
                    />
                  </div>

                  <div className="d-grid mt-4">
                    <button
                      type="submit"
                      className="btn btn-success btn-industrial btn-lg"
                      disabled={!file || loading}
                    >
                      <i className="bi bi-play-circle-fill me-1"></i>
                      Inspect PCB
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      )}

      {loading && (
        <LoadingSpinner message="Executing CrackXNet Multi-Scale Inference..." />
      )}

      {/* Result Display */}
      {result && !loading && (
        <div className="mt-2">
          {/* Summary Card */}
          <div className="qc-card mb-4">
            <div className="qc-card-body p-4">
              <div className="row align-items-center g-3">
                <div className="col-12 col-md-5">
                  <div className="text-secondary small font-mono mb-1">
                    PCB ID: {result.pcb_id}
                  </div>
                  <div className="d-flex align-items-center gap-3">
                    <DecisionBadge decision={result.decision} size="lg" />
                    <div>
                      <div className="small text-muted">Defects Detected:</div>
                      <div className="h4 fw-bold font-mono text-dark mb-0">
                        {result.defect_count}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="col-6 col-md-3 border-start">
                  <div className="text-secondary small">Processing Latency</div>
                  <div className="h5 fw-bold font-mono text-primary mb-0">
                    {result.processing_time_ms ? `${result.processing_time_ms.toFixed(1)} ms` : '—'}
                  </div>
                  <div className="small text-muted font-mono">
                    {result.processing_time_ms ? `~${(1000 / result.processing_time_ms).toFixed(1)} FPS` : ''}
                  </div>
                </div>

                <div className="col-6 col-md-4 border-start">
                  <div className="text-secondary small">Highest Severity</div>
                  <div className="h5 fw-bold text-dark mb-0">
                    {result.highest_severity || 'LOW'}
                  </div>
                  <div className="small text-muted">
                    Database Persisted: {result.persisted ? 'Yes' : 'Local Backup'}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Visuals & Defect Table */}
          <div className="row g-3">
            <div className="col-12 col-xl-7">
              <InspectionImage
                imageUrl={result.image_url}
                resultImageUrl={result.result_image_url}
                explainabilityUrl={result.explainability_url}
                defects={result.defects}
                selectedIndex={selectedIndex}
                onSelectDefect={setSelectedIndex}
              />
            </div>

            <div className="col-12 col-xl-5">
              <div className="qc-card h-100 mb-0">
                <div className="qc-card-header">
                  <div className="d-flex align-items-center gap-2">
                    <i className="bi bi-list-check text-primary"></i>
                    <span>DETECTED DEFECTS ({result.defect_count})</span>
                  </div>
                </div>
                <div className="qc-card-body p-0">
                  <DefectTable
                    defects={result.defects}
                    selectedIndex={selectedIndex}
                    onSelectDefect={setSelectedIndex}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
