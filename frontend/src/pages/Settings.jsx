import React, { useState, useEffect } from 'react';
import { getHealth, getSettings, updateSettings } from '../services/api';

export default function Settings() {
  const [health, setHealth] = useState(null);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.50);
  const [iouThreshold, setIouThreshold] = useState(0.45);
  const [stationId, setStationId] = useState('QC-01');
  const [lineId, setLineId] = useState('Line A');
  const [alertSound, setAlertSound] = useState(true);
  const [conveyorInterval, setConveyorInterval] = useState(3);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => {});
    getSettings()
      .then((cfg) => {
        if (cfg.confidence_threshold !== undefined) setConfidenceThreshold(cfg.confidence_threshold);
        if (cfg.iou_threshold !== undefined) setIouThreshold(cfg.iou_threshold);
        if (cfg.station_id) setStationId(cfg.station_id);
        if (cfg.line_id) setLineId(cfg.line_id);
        if (cfg.alert_sound !== undefined) setAlertSound(cfg.alert_sound);
        if (cfg.conveyor_interval_sec !== undefined) setConveyorInterval(cfg.conveyor_interval_sec);
      })
      .catch((err) => console.warn('Could not fetch backend settings:', err));
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await updateSettings({
        confidence_threshold: confidenceThreshold,
        iou_threshold: iouThreshold,
        station_id: stationId,
        line_id: lineId,
        alert_sound: alertSound,
        conveyor_interval_sec: conveyorInterval,
      });
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3500);
    } catch (err) {
      console.error('Settings save failed:', err);
    } finally {
      setSaving(false);
    }
  };

  const isOnline = health?.status === 'online';

  return (
    <div>
      {/* Title */}
      <div className="mb-4">
        <h4 className="fw-bold text-dark mb-1">SYSTEM & INSPECTION SETTINGS</h4>
        <div className="text-secondary small">
          Configure detection tolerances, view hardware acceleration status, and system diagnostics.
        </div>
      </div>

      {savedSuccess && (
        <div className="alert alert-success d-flex align-items-center gap-2 small py-2 mb-3">
          <i className="bi bi-check-circle-fill"></i>
          <span>Settings successfully synchronized to database and workstation profile.</span>
        </div>
      )}

      <div className="row g-3">
        {/* Detection Thresholds Form */}
        <div className="col-12 col-lg-7">
          <div className="qc-card mb-4">
            <div className="qc-card-header">
              <span>Detection Sensitivity Thresholds</span>
            </div>
            <div className="qc-card-body p-4">
              <form onSubmit={handleSave}>
                <div className="mb-4">
                  <div className="d-flex justify-content-between mb-1">
                    <label className="form-label fw-bold text-dark mb-0">
                      Confidence Score Threshold: <span className="font-mono text-primary">{(confidenceThreshold * 100).toFixed(0)}%</span>
                    </label>
                    <span className="text-muted small">Default: 50%</span>
                  </div>
                  <input
                    type="range"
                    className="form-range"
                    min="0.10"
                    max="0.95"
                    step="0.05"
                    value={confidenceThreshold}
                    onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                  />
                  <div className="form-text small">
                    Minimum prediction probability required to consider a defect candidate valid. Lower values increase sensitivity for faint defects.
                  </div>
                </div>

                <div className="mb-4">
                  <div className="d-flex justify-content-between mb-1">
                    <label className="form-label fw-bold text-dark mb-0">
                      NMS IoU Overlap Threshold: <span className="font-mono text-primary">{iouThreshold.toFixed(2)}</span>
                    </label>
                    <span className="text-muted small">Default: 0.45</span>
                  </div>
                  <input
                    type="range"
                    className="form-range"
                    min="0.10"
                    max="0.80"
                    step="0.05"
                    value={iouThreshold}
                    onChange={(e) => setIouThreshold(parseFloat(e.target.value))}
                  />
                  <div className="form-text small">
                    Intersection over Union (IoU) limit for Non-Maximum Suppression duplicate box elimination.
                  </div>
                </div>

                <div className="row g-2 mb-4">
                  <div className="col-6">
                    <label className="form-label small fw-bold text-dark mb-1">Station ID</label>
                    <input
                      type="text"
                      className="form-control form-control-sm font-mono"
                      value={stationId}
                      onChange={(e) => setStationId(e.target.value)}
                    />
                  </div>
                  <div className="col-6">
                    <label className="form-label small fw-bold text-dark mb-1">Production Line</label>
                    <input
                      type="text"
                      className="form-control form-control-sm font-mono"
                      value={lineId}
                      onChange={(e) => setLineId(e.target.value)}
                    />
                  </div>
                </div>

                <div className="d-flex justify-content-end">
                  <button type="submit" className="btn btn-primary btn-industrial" disabled={saving}>
                    <i className="bi bi-save me-1"></i>
                    {saving ? 'Saving...' : 'Save & Persist Settings'}
                  </button>
                </div>
              </form>
            </div>
          </div>

          <div className="qc-card mb-0">
            <div className="qc-card-header">
              <i className="bi bi-shield-lock text-primary me-2"></i>
              <span>Architecture Integrity Lock</span>
            </div>
            <div className="qc-card-body p-3 small text-muted">
              Model layers, feature dimensions, and weights are locked against accidental modification to preserve validated DeepPCB compliance.
            </div>
          </div>
        </div>

        {/* System Diagnostics */}
        <div className="col-12 col-lg-5">
          <div className="qc-card">
            <div className="qc-card-header">
              <span>Station Hardware & Diagnostics</span>
            </div>
            <div className="qc-card-body p-0">
              <ul className="list-group list-group-flush font-mono small">
                <li className="list-group-item d-flex justify-content-between align-items-center px-3 py-2">
                  <span className="text-muted">Model Name:</span>
                  <span className="fw-bold text-dark">CrackXNet PyTorch</span>
                </li>
                <li className="list-group-item d-flex justify-content-between align-items-center px-3 py-2">
                  <span className="text-muted">Model Version:</span>
                  <span className="badge bg-light text-dark border">v1.0.0</span>
                </li>
                <li className="list-group-item d-flex justify-content-between align-items-center px-3 py-2">
                  <span className="text-muted">Device Accelerator:</span>
                  <span className="badge bg-dark">{health?.device || 'CPU'}</span>
                </li>
                <li className="list-group-item d-flex justify-content-between align-items-center px-3 py-2">
                  <span className="text-muted">Inference Resolution:</span>
                  <span className="text-dark">416 &times; 416 px</span>
                </li>
                <li className="list-group-item d-flex justify-content-between align-items-center px-3 py-2">
                  <span className="text-muted">Backend API Server:</span>
                  <span className={isOnline ? 'text-success fw-bold' : 'text-danger fw-bold'}>
                    {isOnline ? 'Connected (Port 8000)' : 'Disconnected'}
                  </span>
                </li>
                <li className="list-group-item d-flex justify-content-between align-items-center px-3 py-2">
                  <span className="text-muted">Database Engine:</span>
                  <span className={health?.mongodb_connected ? 'text-success' : 'text-primary'}>
                    {health?.mongodb_connected ? 'MongoDB Active' : 'Local File Persistence Active'}
                  </span>
                </li>
                <li className="list-group-item d-flex justify-content-between align-items-center px-3 py-2">
                  <span className="text-muted">Model Weights:</span>
                  <span className={health?.weights_loaded ? 'text-success' : 'text-warning'}>
                    {health?.weights_loaded ? 'Trained Checkpoint' : 'Eval Architecture (Random Init)'}
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
