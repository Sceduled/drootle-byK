import { useState, useEffect } from 'react';
import { Save, AlertCircle, RefreshCw } from 'lucide-react';
import api from '../lib/api';

export default function LiveUpdates() {
  const [projects, setProjects] = useState([]);
  const [activeProject, setActiveProject] = useState(null);
  
  const [contextData, setContextData] = useState({
    units_sold_this_week: '',
    current_offer: '',
    market_update: ''
  });
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchProjects();
  }, []);

  useEffect(() => {
    if (activeProject) {
      fetchContext(activeProject.project_key);
    }
  }, [activeProject]);

  const fetchProjects = async () => {
    try {
      const res = await api.get('/dashboard/projects');
      setProjects(res.data);
      if (res.data.length > 0) {
        setActiveProject(res.data[0]);
      } else {
        setLoading(false);
      }
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  const fetchContext = async (project_key) => {
    setLoading(true);
    try {
      const res = await api.get(`/dashboard/campaign-context/${project_key}`);
      setContextData({
        units_sold_this_week: res.data.units_sold_this_week || '',
        current_offer: res.data.current_offer || '',
        market_update: res.data.market_update || ''
      });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (key, value) => {
    setContextData(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage('');
    try {
      await api.post(`/dashboard/campaign-context/${activeProject.project_key}`, {
        contexts: contextData
      });
      setMessage('Updates saved successfully!');
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      console.error(err);
      setMessage('Error saving updates');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-4 md:p-8 max-w-4xl mx-auto flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground mb-1">Live Updates</h1>
        <p className="text-muted text-sm">
          Update the real-time context injected into sequence messages for each project.
        </p>
      </div>

      <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
        <label className="block text-sm font-semibold text-foreground-muted uppercase tracking-wider mb-3">
          Select Project
        </label>
        {projects.length > 0 ? (
          <select
            value={activeProject?.project_key || ''}
            onChange={(e) => setActiveProject(projects.find(p => p.project_key === e.target.value))}
            className="w-full bg-background border border-border text-foreground rounded-lg p-3 outline-none focus:border-blue-500/50"
          >
            {projects.map((p) => (
              <option key={p.project_key} value={p.project_key}>
                {p.project_name} — {p.area}
              </option>
            ))}
          </select>
        ) : (
          <p className="text-muted text-sm flex items-center gap-2">
            <AlertCircle size={14} /> No active projects found. Add projects first.
          </p>
        )}
      </div>

      {activeProject && (
        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          {loading ? (
            <div className="py-12 flex justify-center text-muted">
              <RefreshCw size={24} className="animate-spin" />
            </div>
          ) : (
            <div className="flex flex-col gap-5">
              
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-foreground-muted">Units sold this week</label>
                <input
                  type="text"
                  value={contextData.units_sold_this_week}
                  onChange={(e) => handleChange('units_sold_this_week', e.target.value)}
                  placeholder="e.g. 12"
                  className="bg-background border border-border text-foreground rounded-lg px-4 py-2 outline-none focus:border-blue-500/50"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-foreground-muted">Current offer</label>
                <input
                  type="text"
                  value={contextData.current_offer}
                  onChange={(e) => handleChange('current_offer', e.target.value)}
                  placeholder="e.g. Pre-launch pricing ends this month"
                  className="bg-background border border-border text-foreground rounded-lg px-4 py-2 outline-none focus:border-blue-500/50"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-foreground-muted">Market update</label>
                <input
                  type="text"
                  value={contextData.market_update}
                  onChange={(e) => handleChange('market_update', e.target.value)}
                  placeholder="e.g. Whitefield prices up 8% this quarter"
                  className="bg-background border border-border text-foreground rounded-lg px-4 py-2 outline-none focus:border-blue-500/50"
                />
              </div>

              <div className="mt-4 flex items-center justify-between border-t border-border pt-4">
                <span className={`text-sm ${message.includes('Error') ? 'text-red-400' : 'text-green-400'}`}>
                  {message}
                </span>
                
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
                >
                  <Save size={18} />
                  {saving ? 'Saving...' : 'Save Updates'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
