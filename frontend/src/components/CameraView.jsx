import React, { useRef, useState, useEffect, useCallback } from 'react';

export default function CameraView({ onCapture, disabled = false }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [streamActive, setStreamActive] = useState(false);
  const [capturedBlob, setCapturedBlob] = useState(null);
  const [capturedPreview, setCapturedPreview] = useState(null);
  const [cameraError, setCameraError] = useState(null);

  // Conveyor Mode state
  const [conveyorActive, setConveyorActive] = useState(false);
  const [conveyorInterval, setConveyorInterval] = useState(3);
  const [countdown, setCountdown] = useState(3);

  const startCamera = async () => {
    setCameraError(null);
    try {
      const constraints = {
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'environment',
        },
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
        setStreamActive(true);
      }
    } catch (err) {
      console.warn('Camera access denied or unavailable:', err);
      setCameraError(
        'Physical camera stream unavailable or permission denied. You can use the "Simulate Camera Capture" button below to test live inspection.'
      );
    }
  };

  const stopCamera = useCallback(() => {
    setConveyorActive(false);
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach((track) => track.stop());
      videoRef.current.srcObject = null;
    }
    setStreamActive(false);
  }, []);

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  const captureFrame = useCallback(() => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;

    if (videoRef.current && streamActive) {
      const video = videoRef.current;
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    } else {
      // Fallback synthetic generator for simulation
      canvas.width = 640;
      canvas.height = 480;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#115e33';
      ctx.fillRect(0, 0, 640, 480);
      ctx.strokeStyle = '#d4af37';
      ctx.lineWidth = 3;
      for (let x = 30; x < 640; x += 40) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, 480);
        ctx.stroke();
      }
      for (let y = 30; y < 480; y += 40) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(640, y);
        ctx.stroke();
      }
      ctx.fillStyle = '#f59e0b';
      for (let i = 0; i < 20; i++) {
        const px = 50 + ((i * 47) % 540);
        const py = 40 + ((i * 37) % 400);
        ctx.beginPath();
        ctx.arc(px, py, 9, 0, 2 * Math.PI);
        ctx.fill();
      }
      // defect
      ctx.fillStyle = '#ef4444';
      ctx.fillRect(240, 160, 18, 6);
    }

    canvas.toBlob(
      (blob) => {
        if (blob) {
          setCapturedBlob(blob);
          const previewUrl = URL.createObjectURL(blob);
          setCapturedPreview(previewUrl);
          if (conveyorActive && onCapture) {
            onCapture(blob, { auto: true });
          }
        }
      },
      'image/png',
      0.95
    );
  }, [streamActive, conveyorActive, onCapture]);

  // Conveyor Mode Interval Runner
  useEffect(() => {
    let timer = null;
    let countdownTimer = null;

    if (conveyorActive && !disabled) {
      setCountdown(conveyorInterval);

      countdownTimer = setInterval(() => {
        setCountdown((prev) => (prev <= 1 ? conveyorInterval : prev - 1));
      }, 1000);

      timer = setInterval(() => {
        captureFrame();
      }, conveyorInterval * 1000);
    }

    return () => {
      if (timer) clearInterval(timer);
      if (countdownTimer) clearInterval(countdownTimer);
    };
  }, [conveyorActive, conveyorInterval, disabled, captureFrame]);

  const simulateCapture = () => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    canvas.width = 640;
    canvas.height = 480;
    const ctx = canvas.getContext('2d');

    // Green PCB substrate
    ctx.fillStyle = '#115e33';
    ctx.fillRect(0, 0, 640, 480);

    // Copper traces
    ctx.strokeStyle = '#d4af37';
    ctx.lineWidth = 3;
    for (let x = 30; x < 640; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, 480);
      ctx.stroke();
    }
    for (let y = 30; y < 480; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(640, y);
      ctx.stroke();
    }

    // Pads and via holes
    ctx.fillStyle = '#f59e0b';
    for (let i = 0; i < 20; i++) {
      const px = 50 + ((i * 47) % 540);
      const py = 40 + ((i * 37) % 400);
      ctx.beginPath();
      ctx.arc(px, py, 9, 0, 2 * Math.PI);
      ctx.fill();
    }

    // Defect artifact (spur / bridge)
    ctx.fillStyle = '#ef4444';
    ctx.fillRect(230, 150, 15, 6);

    canvas.toBlob(
      (blob) => {
        if (blob) {
          setCapturedBlob(blob);
          const previewUrl = URL.createObjectURL(blob);
          setCapturedPreview(previewUrl);
        }
      },
      'image/png',
      0.95
    );
  };

  const handleRunInspection = () => {
    if (capturedBlob && onCapture) {
      onCapture(capturedBlob, { auto: false });
    }
  };

  const handleResetCapture = () => {
    if (capturedPreview) {
      URL.revokeObjectURL(capturedPreview);
    }
    setCapturedBlob(null);
    setCapturedPreview(null);
  };

  return (
    <div className="qc-card mb-3">
      <div className="qc-card-header d-flex flex-wrap align-items-center justify-content-between gap-2">
        <div className="d-flex align-items-center gap-2">
          <span className={`led-indicator ${streamActive ? 'led-green' : 'led-red'}`}></span>
          <span>{streamActive ? 'LIVE OPTICAL CAMERA STREAM' : 'CAMERA STANDBY'}</span>
          {conveyorActive && (
            <span className="badge bg-warning text-dark border ms-2 font-mono">
              <i className="bi bi-arrow-repeat me-1"></i>
              CONVEYOR AUTO-INSPECT: Next in {countdown}s
            </span>
          )}
        </div>

        <div className="d-flex align-items-center gap-2">
          <span className="badge bg-light text-secondary border font-mono small">
            720p 30 FPS Stream
          </span>
        </div>
      </div>

      <div className="qc-card-body p-3">
        {cameraError && (
          <div className="alert alert-warning small py-2 mb-3">
            <i className="bi bi-exclamation-triangle-fill me-2"></i>
            {cameraError}
          </div>
        )}

        {/* Viewport Area */}
        <div className="row g-3">
          <div className="col-12 col-lg-7">
            <div className="camera-container">
              {capturedPreview && !conveyorActive ? (
                <img
                  src={capturedPreview}
                  alt="Captured Frame"
                  className="camera-video"
                />
              ) : (
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="camera-video"
                  style={{ display: streamActive ? 'block' : 'none' }}
                />
              )}

              {!streamActive && (!capturedPreview || conveyorActive) && (
                <div className="text-center text-secondary p-4">
                  <i className="bi bi-camera-video-off fs-1 d-block mb-2"></i>
                  <div className="fw-semibold text-white">Camera Standby</div>
                  <div className="small text-muted">Click "Start Camera" or "Simulate Frame" to inspect.</div>
                </div>
              )}

              {streamActive && <div className="camera-crosshairs"></div>}
            </div>

            {/* Hidden canvas for snapshot rasterization */}
            <canvas ref={canvasRef} style={{ display: 'none' }} />
          </div>

          {/* Controls Panel */}
          <div className="col-12 col-lg-5 d-flex flex-column justify-content-between">
            <div className="bg-light p-3 rounded border mb-3">
              <h6 className="fw-bold text-dark mb-2">Conveyor & Manual Inspection Controls</h6>
              <p className="small text-muted mb-3">
                Operate the optical inspection camera manually per-unit or engage conveyor belt automatic inspection.
              </p>

              <div className="d-grid gap-2">
                {!streamActive ? (
                  <button
                    type="button"
                    className="btn btn-primary btn-industrial"
                    onClick={startCamera}
                    disabled={disabled}
                  >
                    <i className="bi bi-camera-video me-1"></i>
                    Start Camera Stream
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn-outline-danger btn-industrial"
                    onClick={stopCamera}
                  >
                    <i className="bi bi-stop-circle me-1"></i>
                    Stop Camera Stream
                  </button>
                )}

                <button
                  type="button"
                  className="btn btn-outline-secondary btn-industrial"
                  onClick={simulateCapture}
                  disabled={disabled}
                >
                  <i className="bi bi-lightning-charge me-1"></i>
                  Simulate Camera Capture
                </button>

                {streamActive && !capturedPreview && (
                  <button
                    type="button"
                    className="btn btn-success btn-industrial btn-lg"
                    onClick={captureFrame}
                    disabled={disabled}
                  >
                    <i className="bi bi-camera me-1"></i>
                    Capture PCB Frame
                  </button>
                )}
              </div>

              {/* Conveyor Belt Continuous Mode */}
              <div className="border-top mt-3 pt-3">
                <div className="d-flex align-items-center justify-content-between mb-2">
                  <span className="small fw-bold text-dark">Conveyor Auto-Inspect:</span>
                  <div className="btn-group btn-group-sm">
                    {[2, 3, 5].map((sec) => (
                      <button
                        key={sec}
                        type="button"
                        className={`btn ${conveyorInterval === sec ? 'btn-primary' : 'btn-outline-secondary'}`}
                        onClick={() => setConveyorInterval(sec)}
                        disabled={conveyorActive}
                      >
                        {sec}s
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  type="button"
                  className={`btn w-100 ${conveyorActive ? 'btn-warning fw-bold' : 'btn-outline-primary'}`}
                  onClick={() => setConveyorActive((v) => !v)}
                  disabled={disabled}
                >
                  <i className={`bi ${conveyorActive ? 'bi-pause-circle' : 'bi-arrow-repeat'} me-1`}></i>
                  {conveyorActive ? 'Pause Conveyor Auto-Inspect' : 'Start Conveyor Auto-Inspect'}
                </button>
              </div>
            </div>

            {/* Run Inspection Action when snapshot ready */}
            {capturedPreview && !conveyorActive && (
              <div className="p-3 bg-primary-subtle border border-primary-subtle rounded text-center">
                <div className="fw-bold text-primary mb-1">Frame Ready for Analysis</div>
                <div className="small text-muted mb-3">Snap captured at 640x480 resolution.</div>
                <div className="d-flex gap-2">
                  <button
                    type="button"
                    className="btn btn-outline-secondary flex-grow-1"
                    onClick={handleResetCapture}
                    disabled={disabled}
                  >
                    Retake
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary flex-grow-2 fw-bold"
                    onClick={handleRunInspection}
                    disabled={disabled}
                  >
                    <i className="bi bi-play-fill me-1"></i>
                    RUN INSPECTION
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
