import React from 'react';
import { useLocation, Navigate } from 'react-router-dom';
import InspectionDetails from './InspectionDetails';

export default function InspectionResult() {
  const location = useLocation();
  const inspection = location.state?.inspection;

  if (inspection?.inspection_id) {
    return <Navigate to={`/inspection/${inspection.inspection_id}`} replace />;
  }

  return <InspectionDetails />;
}
