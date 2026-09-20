import React, { useState, useEffect } from 'react';
import { getHealth } from '../services/api';

export default function ModelInfo() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => {});
  }, []);

  const defectClasses = [
    { name: 'Open', desc: 'Broken circuit track causing open circuit condition.', severity: 'CRITICAL', color: '#dc2626' },
    { name: 'Short', desc: 'Unintended electrical bridge between adjacent copper tracks.', severity: 'CRITICAL', color: '#dc2626' },
    { name: 'Mousebite', desc: 'Edge nibble or irregular bite out of copper trace or substrate boundary.', severity: 'MEDIUM', color: '#eab308' },
    { name: 'Spur', desc: 'Unwanted copper projection protruding from conductor track.', severity: 'HIGH', color: '#f97316' },
    { name: 'Spurious Copper', desc: 'Residual isolated copper island left after chemical etching.', severity: 'LOW', color: '#0284c7' },
    { name: 'Pin Hole', desc: 'Micro-perforation or void in copper trace risking high resistance.', severity: 'MEDIUM', color: '#eab308' },
  ];

  return (
    <div>
      {/* Page Title */}
      <div className="mb-4">
        <h4 className="fw-bold text-dark mb-1">CRACKXNET ARCHITECTURE & RESEARCH METRICS</h4>
        <div className="text-secondary small">
          Intelligent Real-Time PCB Surface Defect Inspection and Quality Decision Support System.
        </div>
      </div>

      {/* Model Spec Overview */}
      <div className="row g-3 mb-4">
        <div className="col-12 col-lg-8">
          <div className="qc-card h-100 mb-0">
            <div className="qc-card-header d-flex justify-content-between align-items-center">
              <span>Deep Neural Network Architecture</span>
              <span className="badge bg-primary font-mono">PyTorch Implementation</span>
            </div>
            <div className="qc-card-body p-4">
              <h5 className="fw-bold text-primary mb-3">CrackXNet Modular Pipeline</h5>

              <div className="d-flex flex-column gap-3">
                <div className="p-3 bg-light rounded border">
                  <div className="fw-bold text-dark mb-1">
                    <span className="badge bg-secondary me-2 font-mono">1</span>
                    Backbone: EfficientNet-B0
                  </div>
                  <div className="small text-muted">
                    Extracts multi-scale deep hierarchical feature representations across stages C2, C3, C4, and C5 with inverted bottleneck convolutions.
                  </div>
                </div>

                <div className="p-3 bg-light rounded border">
                  <div className="fw-bold text-dark mb-1">
                    <span className="badge bg-secondary me-2 font-mono">2</span>
                    Convolutional Block Attention Module (CBAM)
                  </div>
                  <div className="small text-muted">
                    Sequentially applies Channel Attention and Spatial Attention to suppress optical PCB reflection noise and highlight fine conductor track anomalies.
                  </div>
                </div>

                <div className="p-3 bg-light rounded border">
                  <div className="fw-bold text-dark mb-1">
                    <span className="badge bg-secondary me-2 font-mono">3</span>
                    Lightweight Transformer Encoder
                  </div>
                  <div className="small text-muted">
                    Two-layer multi-head self-attention module capturing long-range contextual dependencies across complex PCB bus routing networks.
                  </div>
                </div>

                <div className="p-3 bg-light rounded border">
                  <div className="fw-bold text-dark mb-1">
                    <span className="badge bg-secondary me-2 font-mono">4</span>
                    Adaptive Feature Fusion Module (AFFM) & Feature Pyramid Network (FPN)
                  </div>
                  <div className="small text-muted">
                    Dynamically blends cross-scale features via learnable weighting gates into a unified multi-scale pyramid (P2, P3, P4, P5) for detection of micro pin-holes through large track bridges.
                  </div>
                </div>

                <div className="p-3 bg-light rounded border">
                  <div className="fw-bold text-dark mb-1">
                    <span className="badge bg-secondary me-2 font-mono">5</span>
                    Multi-Head Decision & Explainability System
                  </div>
                  <div className="small text-muted">
                    Parallel output heads: Multi-scale classification (6 defect classes), Bounding-box regression with NMS, Expert-defined Severity Head, and Saliency Attention Maps.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Benchmark Card */}
        <div className="col-12 col-lg-4">
          <div className="qc-card mb-3">
            <div className="qc-card-header">
              <span>DeepPCB Benchmark Performance</span>
            </div>
            <div className="qc-card-body p-4 text-center">
              <div className="alert alert-info py-2 small mb-3">
                <i className="bi bi-info-circle me-1"></i>
                Official Research Test-Set Evaluation
              </div>

              <div className="mb-4">
                <div className="display-5 fw-bold font-mono text-primary">95.40%</div>
                <div className="fw-bold text-dark small">mAP@0.5 (Mean Average Precision)</div>
                <div className="text-muted small">DeepPCB Test Benchmark</div>
              </div>

              <div className="pt-3 border-top">
                <div className="display-6 fw-bold font-mono text-secondary">63.40%</div>
                <div className="fw-bold text-dark small">mAP@0.5:0.95</div>
                <div className="text-muted small">Strict IoU Multi-Threshold Metric</div>
              </div>
            </div>
          </div>

          <div className="qc-card mb-0">
            <div className="qc-card-header">
              <span>Runtime Engine Status</span>
            </div>
            <div className="qc-card-body p-3 font-mono small">
              <div className="d-flex justify-content-between mb-2">
                <span className="text-muted">Target Resolution:</span>
                <span className="fw-bold">416 &times; 416 px</span>
              </div>
              <div className="d-flex justify-content-between mb-2">
                <span className="text-muted">Compute Device:</span>
                <span className="badge bg-dark">{health?.device || 'CPU'}</span>
              </div>
              <div className="d-flex justify-content-between mb-2">
                <span className="text-muted">Inference Mode:</span>
                <span className="text-success">torch.inference_mode</span>
              </div>
              <div className="d-flex justify-content-between">
                <span className="text-muted">Weights Loaded:</span>
                <span className={health?.weights_loaded ? 'text-success' : 'text-warning'}>
                  {health?.weights_loaded ? 'Trained Checkpoint' : 'Random Init / Eval Mode'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Defect Classes Grid */}
      <div className="qc-card">
        <div className="qc-card-header">
          <span>Target Surface Defect Taxonomies</span>
        </div>
        <div className="qc-card-body p-4">
          <div className="row g-3">
            {defectClasses.map((item, idx) => (
              <div key={idx} className="col-12 col-md-6 col-lg-4">
                <div className="p-3 border rounded h-100 bg-light">
                  <div className="d-flex justify-content-between align-items-center mb-2">
                    <span className="fw-bold text-dark h6 mb-0">{item.name}</span>
                    <span
                      className="badge font-mono small"
                      style={{ backgroundColor: `${item.color}22`, color: item.color, border: `1px solid ${item.color}55` }}
                    >
                      {item.severity}
                    </span>
                  </div>
                  <div className="small text-secondary">{item.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
