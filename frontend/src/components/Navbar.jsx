import React, { useState, useEffect } from 'react';
import { getHealth } from '../services/api';

export default function Navbar() {
  const [health, setHealth] = useState(null);
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await getHealth();
        setHealth(data);
      } catch {
        setHealth({ status: 'offline', model_loaded: false, device: 'unknown' });
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString('en-US', { hour12: false }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const isOnline = health?.status === 'online';

  return (
    <header className="qc-navbar">
      <div className="d-flex align-items-center gap-3">
        <div className="navbar-brand-title">
          <i className="bi bi-cpu text-primary fs-4"></i>
          <span>CRACKXNET</span>
          <span className="brand-sub d-none d-md-inline">
            Intelligent Real-Time PCB Quality Inspection
          </span>
        </div>
      </div>

      <div className="d-flex align-items-center gap-3">
        {/* Device & Model Specs */}
        <div className="d-none d-lg-flex align-items-center gap-2 text-muted small font-mono">
          <span className="badge bg-light text-dark border">
            <i className="bi bi-diagram-3 me-1 text-primary"></i>
            CrackXNet v1.0
          </span>
          <span className="badge bg-light text-dark border text-uppercase">
            <i className="bi bi-hdd-network me-1 text-secondary"></i>
            {health?.device || 'CPU'}
          </span>
        </div>

        {/* System Online / Offline Status */}
        <div className={`status-pill ${isOnline ? 'status-pill-online' : 'status-pill-offline'}`}>
          <span className={`led-indicator ${isOnline ? 'led-green' : 'led-red'}`}></span>
          <span>{isOnline ? 'STATION ONLINE' : 'BACKEND OFFLINE'}</span>
        </div>

        {/* Live Clock */}
        <div className="d-none d-sm-block text-secondary small font-mono border-start ps-3">
          <i className="bi bi-clock me-1"></i>
          <span>{timeStr}</span>
        </div>
      </div>
    </header>
  );
}
