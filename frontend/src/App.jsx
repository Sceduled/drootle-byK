import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Leads from './pages/Leads';
import LeadDetail from './pages/LeadDetail';
import Metrics from './pages/Metrics';
import Sequences from './pages/Sequences';
import Profile from './pages/Profile';
import Simulator from './pages/Simulator';
import Layout from './components/Layout';

function PrivateRoute({ children }) {
  const token = localStorage.getItem('drootle_token');
  return token ? <Layout>{children}</Layout> : <Navigate to="/login" />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/leads" element={<PrivateRoute><Leads /></PrivateRoute>} />
        <Route path="/leads/:id" element={<PrivateRoute><LeadDetail /></PrivateRoute>} />
        <Route path="/metrics" element={<PrivateRoute><Metrics /></PrivateRoute>} />
        <Route path="/sequences" element={<PrivateRoute><Sequences /></PrivateRoute>} />
        <Route path="/simulator" element={<PrivateRoute><Simulator /></PrivateRoute>} />
        <Route path="/profile" element={<PrivateRoute><Profile /></PrivateRoute>} />
        <Route path="*" element={<Navigate to="/leads" />} />
      </Routes>
    </BrowserRouter>
  );
}
