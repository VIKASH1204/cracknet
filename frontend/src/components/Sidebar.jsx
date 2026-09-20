import React from 'react';
import { NavLink } from 'react-router-dom';

export default function Sidebar() {
  const navItems = [
    { to: '/', label: 'Factory Dashboard', icon: 'bi-grid-1x2' },
    { to: '/live', label: 'Live Camera Inspection', icon: 'bi-camera-video' },
    { to: '/upload', label: 'Upload PCB Image', icon: 'bi-cloud-arrow-up' },
    { to: '/history', label: 'Inspection History', icon: 'bi-clock-history' },
    { to: '/analytics', label: 'Quality Analytics', icon: 'bi-graph-up' },
    { to: '/model-info', label: 'Model Architecture', icon: 'bi-cpu' },
    { to: '/settings', label: 'System Settings', icon: 'bi-sliders' },
  ];

  return (
    <aside className="qc-sidebar">
      <div className="sidebar-header">
        <i className="bi bi-shield-check text-primary fs-5"></i>
        <div>
          <div className="fw-bold text-white small text-uppercase" style={{ letterSpacing: '0.05em' }}>
            Station QC-01
          </div>
          <div className="text-secondary" style={{ fontSize: '0.7rem' }}>
            Production Line A
          </div>
        </div>
      </div>

      <ul className="sidebar-menu">
        {navItems.map((item) => (
          <li key={item.to} className="sidebar-item">
            <NavLink
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            >
              <i className={`bi ${item.icon}`}></i>
              <span>{item.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>

      <div className="sidebar-footer">
        <div className="d-flex align-items-center justify-content-between mb-1">
          <span>CrackXNet Engine</span>
          <span className="badge bg-primary-subtle text-primary border border-primary-subtle font-mono">v1.0.0</span>
        </div>
        <div className="text-secondary" style={{ fontSize: '0.68rem' }}>
          Real-Time PCB Decision Support
        </div>
      </div>
    </aside>
  );
}
