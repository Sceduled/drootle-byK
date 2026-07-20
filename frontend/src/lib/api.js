import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api'
});

// Simulator
export const getProjects = async () => {
  return await api.get('/simulator/projects');
};

export const startSimulation = async (name, projectKey) => {
  return await api.post('/simulator/start', { name, project_key: projectKey });
};

export const getSimulationHistory = async (sessionId) => {
  return await api.get(`/simulator/history/${sessionId}`);
};

export const exportSimulations = async () => {
  return await api.get('/simulator/export', { responseType: 'blob' });
};

export const sendSimulationMessage = async (sessionId, message) => {
  return await api.post(`/simulator/chat/${sessionId}`, { message });
};

api.interceptors.request.use(config => {
  const token = localStorage.getItem('drootle_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('drootle_token');
      localStorage.removeItem('drootle_role');
      localStorage.removeItem('drootle_username');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
