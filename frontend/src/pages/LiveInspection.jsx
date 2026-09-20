import React, { useState, useRef } from 'react';
import CameraView from '../components/CameraView';
import DecisionBadge from '../components/DecisionBadge';
import InspectionImage from '../components/InspectionImage';
import DefectTable from '../components/DefectTable';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import { cameraInspection } from '../services/api';

// Web Audio API tone synthesizer for factory alert
const playAlertChime = (decision) => {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.connect(gain);
    gain.connect(ctx.destination);

    if (decision === 'REJECT') {
      // Two-tone warning beep
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(440, ctx.currentTime);
      osc.frequency.setValueAtTime(330, ctx.currentTime + 0.15);
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.4);
    } else if (decision === 'REWORK') {
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(587.33, ctx.currentTime);
      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.25);
    } else {
      // Pleasant pass chime
      osc.type = 'sine';
      osc.frequency.setValueAtTime(523.25, ctx.currentTime);
      osc.frequency.setValueAtTime(659.25, ctx.currentTime + 0.1);
      gain.gain.setValueAtTime(0.1, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.3);
    }
  } catch (err) {
    console.debug('Audio alert skipped:', err);
  }
};

export default function LiveInspection() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [inspectionResult, setInspectionResult] = useState(null);
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [sessionCount, setSessionCount] = useState(0);
  const [soundEnabled, setSoundEnabled] = useState(true);

  const handleCaptureFrame = async (blob, meta = {}) => {
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', blob, 'camera_capture.png');
      formData.append('pcb_id', `CAM-${Date.now().toString().slice(-6)}`);
      formData.append('operator_id', 'OP-01');

      const data = await cameraInspection(formData);
      setInspectionResult(data);
      setSessionCount((c) => c + 1);

      if (soundEnabled) {
        playAlertChime(data.decision);
      }
    } catch (err) {
      console.error('Inference error:', err);
      setError(err.response?.data?.detail || err.message || 'Inspection inference failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setInspectionResult(null);
    setSelectedIndex(null);
    setError(null);
  };

  const procTime = inspectionResult?.processing_time_ms;
  const fps = procTime ? (1000 / procTime).toFixed(1) : null;
  const isReject = inspectionResult?.decision === 'REJECT';

  return (
    <div>
      {/* Page Header */}
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-2">
        <div>
          <h4 className="fw-bold text-dark mb-1">LIVE OPTICAL PCB INSPECTION STATION</h4>
          <div className="text-secondary small">
            Continuous optical alignment and real-time CrackXNet defect decision support.
          </div>
        </div>

        <div className="d-flex align-items-center gap-2">
          <div className="form-check form-switch form-check-inline m-0 small border px-2 py-1 rounded bg-white">
            <input
              className="form-check-input ms-0 me-2"
              type="checkbox"
              id="toggleSound"
              checked={soundEnabled}
              onChange={(e) => setSoundEnabled(e.target.checked)}
            />
            <label className="form-check-label text-muted small" htmlFor="toggleSound">
              <i className={`bi ${soundEnabled ? 'bi-volume-up-fill text-primary' : 'bi-volume-mute-fill'} me-1`}></i>
              Audio Alerts
            </label>
          </div>

          <span className="badge bg-light text-secondary border font-mono small">
            Session Inspected: {sessionCount}
          </span>

          {inspectionResult && (
            <button
              type="button"
              className="btn btn-outline-secondary btn-sm"
              onClick={handleReset}
            >
              <i className="bi bi-arrow-repeat me-1"></i>
              Clear
            </button>
          )}
        </div>
      </div>

      <ErrorMessage message={error} onRetry={() => setError(null)} />

      {/* Live Video Camera Station */}
      <CameraView onCapture={handleCaptureFrame} disabled={loading} />

      {/* Loading State during inference */}
      {loading && (
        <LoadingSpinner message="Evaluating Optical PCB Frame with CrackXNet AI..." />
      )}

      {/* Inspection Results Section */}
      {inspectionResult && !loading && (
        <div className="mt-4">
          {/* Top Banner Decision Card */}
          <div className={`qc-card mb-4 ${isReject ? 'border-danger shadow-sm' : ''}`}>
            <div className="qc-card-body p-4">
              <div className="row align-items-center g-3">
                <div className="col-12 col-md-5">
                  <div className="text-secondary small font-mono mb-1">
                    PCB ID: {inspectionResult.pcb_id}
                  </div>
                  <div className="d-flex align-items-center gap-3">
                    <DecisionBadge decision={inspectionResult.decision} size="lg" />
                    <div>
                      <div className="small text-muted">Defects Found:</div>
                      <div className="h4 fw-bold font-mono text-dark mb-0">
                        {inspectionResult.defect_count}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="col-6 col-md-3 border-start">
                  <div className="text-secondary small">Inference Latency</div>
                  <div className="h5 fw-bold font-mono text-primary mb-0">
                    {procTime ? `${procTime.toFixed(1)} ms` : '—'}
                  </div>
                  <div className="small text-muted font-mono">
                    {fps ? `Estimated: ${fps} FPS` : ''}
                  </div>
                </div>

                <div className="col-6 col-md-4 border-start">
                  <div className="text-secondary small">Highest Severity</div>
                  <div className="h5 fw-bold text-dark mb-0">
                    {inspectionResult.highest_severity || 'LOW'}
                  </div>
                  <div className="small text-muted">
                    Database Persisted: {inspectionResult.persisted ? 'Yes' : 'Local Backup'}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Dual Panel: Visual Viewer & Defect Breakdown */}
          <div className="row g-3">
            <div className="col-12 col-xl-7">
              <InspectionImage
                imageUrl={inspectionResult.image_url}
                resultImageUrl={inspectionResult.result_image_url}
                explainabilityUrl={inspectionResult.explainability_url}
                defects={inspectionResult.defects}
                selectedIndex={selectedIndex}
                onSelectDefect={setSelectedIndex}
              />
            </div>

            <div className="col-12 col-xl-5">
              <div className="qc-card h-100 mb-0">
                <div className="qc-card-header">
                  <div className="d-flex align-items-center gap-2">
                    <i className="bi bi-list-check text-primary"></i>
                    <span>DETECTED DEFECTS ({inspectionResult.defect_count})</span>
                  </div>
                </div>
                <div className="qc-card-body p-0">
                  <DefectTable
                    defects={inspectionResult.defects}
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
