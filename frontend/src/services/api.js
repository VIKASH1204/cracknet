import axios from 'axios';

const api = axios.create({
  baseURL: '', // Handled via Vite proxy to http://localhost:8000
  timeout: 120000,
});

export const getHealth = async () => {
  const response = await api.get('/api/health');
  return response.data;
};

export const uploadInspection = async (formData) => {
  const response = await api.post('/api/inspection/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const cameraInspection = async (formData) => {
  const response = await api.post('/api/inspection/camera', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const getInspection = async (id) => {
  const response = await api.get(`/api/inspection/${id}`);
  return response.data;
};

export const getHistory = async (params = {}) => {
  const response = await api.get('/api/history', { params });
  return response.data;
};

export const getHistoryExportUrl = (params = {}) => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') query.append(k, v);
  });
  const qs = query.toString();
  return `/api/history/export${qs ? `?${qs}` : ''}`;
};

export const getDashboardSummary = async () => {
  const response = await api.get('/api/dashboard/summary');
  return response.data;
};

export const getDefectDistribution = async () => {
  const response = await api.get('/api/dashboard/defect-distribution');
  return response.data;
};

export const getSeverityDistribution = async () => {
  const response = await api.get('/api/dashboard/severity-distribution');
  return response.data;
};

export const getInspectionTrends = async (days = 30) => {
  const response = await api.get('/api/dashboard/trends', { params: { days } });
  return response.data;
};

export const getSettings = async () => {
  const response = await api.get('/api/settings');
  return response.data;
};

export const updateSettings = async (data) => {
  const response = await api.post('/api/settings', data);
  return response.data;
};

export default api;
