import { useState, useEffect } from 'react';
import api from '../lib/api';
import { Plus, Edit2, AlertCircle, Building2, CheckCircle2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState({ message: '', type: 'success', visible: false });
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [saving, setSaving] = useState(false);

  // Form State
  const [projectKey, setProjectKey] = useState('');
  const [projectName, setProjectName] = useState('');
  const [area, setArea] = useState('');
  const [propertyType, setPropertyType] = useState('flat');
  const [bhkOrSize, setBhkOrSize] = useState('');
  const [priceRange, setPriceRange] = useState('');
  const [keyFeatures, setKeyFeatures] = useState('');
  const [isActive, setIsActive] = useState(true);

  const showToast = (message, type = 'success') => {
    setToast({ message, type, visible: true });
    setTimeout(() => {
      setToast(prev => ({ ...prev, visible: false }));
    }, 3000);
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const { data } = await api.get('/dashboard/projects');
      setProjects(data);
    } catch (err) {
      showToast("Failed to fetch projects", "error");
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setEditingProject(null);
    setProjectKey('');
    setProjectName('');
    setArea('');
    setPropertyType('flat');
    setBhkOrSize('');
    setPriceRange('');
    setKeyFeatures('');
    setIsActive(true);
  };

  const handleOpenEdit = (proj) => {
    setEditingProject(proj);
    setProjectKey(proj.project_key);
    setProjectName(proj.project_name);
    setArea(proj.area);
    setPropertyType(proj.property_type);
    setBhkOrSize(proj.bhk_or_size);
    setPriceRange(proj.price_range);
    setKeyFeatures(proj.key_features || '');
    setIsActive(proj.active);
    setIsModalOpen(true);
  };

  const handleOpenAdd = () => {
    resetForm();
    setIsModalOpen(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      const payload = {
        project_name: projectName,
        area,
        property_type: propertyType,
        bhk_or_size: bhkOrSize,
        price_range: priceRange,
        key_features: keyFeatures,
        active: isActive
      };

      if (editingProject) {
        await api.patch(`/dashboard/projects/${editingProject.project_key}`, payload);
        showToast("Project updated successfully", "success");
      } else {
        await api.post('/dashboard/projects', { ...payload, project_key: projectKey });
        showToast("Project created successfully", "success");
      }
      setIsModalOpen(false);
      fetchProjects();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to save project", "error");
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (proj) => {
    try {
      await api.patch(`/dashboard/projects/${proj.project_key}`, { active: !proj.active });
      fetchProjects();
      showToast(`Project ${!proj.active ? 'enabled' : 'disabled'}`, "success");
    } catch (err) {
      showToast("Failed to toggle project status", "error");
    }
  };

  if (loading) return <div className="p-8 text-center text-foreground-muted">Loading projects...</div>;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-8 max-w-5xl mx-auto relative"
    >
      <AnimatePresence>
        {toast.visible && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            className={`fixed bottom-8 right-8 flex items-center gap-3 px-4 py-3 rounded-lg shadow-2xl border z-50 ${
              toast.type === 'success' 
                ? 'bg-[#111] border-[#333] text-green-400' 
                : 'bg-[#111] border-[#333] text-red-400'
            }`}
          >
            {toast.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
            <span className="text-sm font-medium text-gray-100">{toast.message}</span>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-cyan-500/10 border border-cyan-500/20 rounded-2xl flex items-center justify-center text-cyan-400">
            <Building2 size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-foreground tracking-tight">Projects</h1>
            <p className="text-foreground-muted">Manage real estate projects to match with ad sources.</p>
          </div>
        </div>
        <button
          onClick={handleOpenAdd}
          className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-500 text-white px-5 py-2.5 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={18} />
          Add Project
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map((proj) => (
          <div key={proj.project_key} className={`bg-card border border-border rounded-xl p-6 shadow-sm flex flex-col ${!proj.active && 'opacity-60 grayscale'}`}>
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-semibold text-foreground truncate" title={proj.project_name}>{proj.project_name}</h3>
                <p className="text-xs text-muted font-mono bg-background px-1.5 py-0.5 rounded border border-border inline-block mt-1">{proj.project_key}</p>
              </div>
              {proj.active ? (
                <span className="flex items-center gap-1 text-xs font-medium text-green-400 bg-green-400/10 px-2 py-1 rounded-full border border-green-400/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400"></span> Active
                </span>
              ) : (
                <span className="text-xs font-medium text-red-400 bg-red-400/10 px-2 py-1 rounded-full border border-red-400/20">
                  Disabled
                </span>
              )}
            </div>
            <div className="space-y-1 mb-6 flex-1">
              <p className="text-sm text-foreground-muted">{proj.area} &middot; <span className="capitalize">{proj.property_type}</span></p>
              <p className="text-sm text-foreground-muted">{proj.bhk_or_size} &middot; {proj.price_range}</p>
            </div>
            <div className="flex items-center gap-3 mt-auto pt-4 border-t border-border/50">
              <button onClick={() => handleOpenEdit(proj)} className="text-sm text-cyan-400 hover:text-cyan-300 font-medium flex items-center gap-1">
                <Edit2 size={14} /> Edit
              </button>
              <button onClick={() => toggleActive(proj)} className={`text-sm font-medium ${proj.active ? 'text-red-400 hover:text-red-300' : 'text-green-400 hover:text-green-300'}`}>
                {proj.active ? 'Disable' : 'Enable'}
              </button>
            </div>
          </div>
        ))}
      </div>

      <AnimatePresence>
        {isModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              onClick={() => setIsModalOpen(false)}
            />
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-lg relative z-10 max-h-[90vh] overflow-y-auto"
            >
              <form onSubmit={handleSave} className="p-6 space-y-5">
                <h2 className="text-xl font-semibold text-foreground">{editingProject ? 'Edit Project' : 'Add New Project'}</h2>
                
                {!editingProject && (
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">Project Key*</label>
                    <input
                      type="text"
                      required
                      value={projectKey}
                      onChange={e => setProjectKey(e.target.value)}
                      placeholder="e.g. whitefield_flat"
                      className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-cyan-500"
                    />
                    <p className="text-xs text-muted mt-1">Used to match with ad campaigns (lowercase, no spaces).</p>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Project Name*</label>
                  <input
                    type="text"
                    required
                    value={projectName}
                    onChange={e => setProjectName(e.target.value)}
                    placeholder="e.g. Prestige Raintree Park"
                    className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">Area*</label>
                    <input
                      type="text"
                      required
                      value={area}
                      onChange={e => setArea(e.target.value)}
                      placeholder="e.g. Whitefield"
                      className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">Property Type*</label>
                    <select
                      value={propertyType}
                      onChange={e => setPropertyType(e.target.value)}
                      className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-cyan-500"
                    >
                      <option value="flat">Flat</option>
                      <option value="villa">Villa</option>
                      <option value="plot">Plot</option>
                      <option value="commercial">Commercial</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">BHK / Size*</label>
                    <input
                      type="text"
                      required
                      value={bhkOrSize}
                      onChange={e => setBhkOrSize(e.target.value)}
                      placeholder="e.g. 3, 4 BHK"
                      className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">Price Range*</label>
                    <input
                      type="text"
                      required
                      value={priceRange}
                      onChange={e => setPriceRange(e.target.value)}
                      placeholder="e.g. 2Cr - 5Cr"
                      className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Key Features</label>
                  <textarea
                    value={keyFeatures}
                    onChange={e => setKeyFeatures(e.target.value)}
                    placeholder="e.g. RERA approved, lake facing..."
                    rows={3}
                    className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-cyan-500 resize-none"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="active"
                    checked={isActive}
                    onChange={e => setIsActive(e.target.checked)}
                    className="w-4 h-4 bg-background border border-border rounded focus:ring-cyan-500 text-cyan-600"
                  />
                  <label htmlFor="active" className="text-sm font-medium text-foreground">Active</label>
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t border-border/50">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 text-sm font-medium text-foreground-muted hover:text-foreground transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="bg-cyan-600 hover:bg-cyan-500 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                  >
                    {saving ? 'Saving...' : 'Save Project'}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
