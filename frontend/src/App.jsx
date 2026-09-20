import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import LiveInspection from './pages/LiveInspection';
import UploadInspection from './pages/UploadInspection';
import InspectionResult from './pages/InspectionResult';
import InspectionDetails from './pages/InspectionDetails';
import InspectionHistory from './pages/InspectionHistory';
import Analytics from './pages/Analytics';
import ModelInfo from './pages/ModelInfo';
import Settings from './pages/Settings';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <Sidebar />
        <div className="main-wrapper">
          <Navbar />
          <main className="content-area">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/live" element={<LiveInspection />} />
              <Route path="/upload" element={<UploadInspection />} />
              <Route path="/inspection" element={<InspectionResult />} />
              <Route path="/inspection/:id" element={<InspectionDetails />} />
              <Route path="/history" element={<InspectionHistory />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/model-info" element={<ModelInfo />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}
