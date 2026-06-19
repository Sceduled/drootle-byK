import { useState, useEffect } from 'react';
import api from '../lib/api';
import { Save, Radio, MessageSquare, AlertCircle, CheckCircle2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const CONTEXT_FIELDS = [
  { key: 'units_sold_this_week', label: 'Units Sold This Week', type: 'number', placeholder: 'e.g. 12', icon: <Radio size={18} /> },
  { key: 'current_offer', label: 'Current Offer', type: 'text', placeholder: 'e.g. Pre-launch pricing ends this month', icon: <MessageSquare size={18} /> },
  { key: 'market_update', label: 'Market Update', type: 'text', placeholder: 'e.g. Whitefield prices up 8% this quarter', icon: <MessageSquare size={18} /> }
];

export default function LiveContext() {
  const [contextData, setContextData] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState({ message: '', type: 'success', visible: false });

  const showToast = (message, type = 'success') => {
    setToast({ message, type, visible: true });
    setTimeout(() => {
      setToast(prev => ({ ...prev, visible: false }));
    }, 3000);
  };

  useEffect(() => {
    fetchContext();
  }, []);

  const fetchContext = async () => {
    try {
      setLoading(true);
      const { data } = await api.get('/dashboard/context');
      setContextData(data);
    } catch (err) {
      showToast("Failed to fetch live context", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      const updates = Object.entries(contextData).map(([key, value]) => ({ context_key: key, context_value: value.toString() }));
      await api.patch('/dashboard/context', { updates });
      showToast("Live context updated successfully", "success");
    } catch (err) {
      showToast("Failed to update context", "error");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="p-8 text-center text-foreground-muted">Loading live context...</div>;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-8 max-w-2xl mx-auto relative"
    >
      {/* Toast Notification */}
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

      <div className="flex items-center gap-3 mb-6">
        <div className="w-12 h-12 bg-cyan-500/10 border border-cyan-500/20 rounded-2xl flex items-center justify-center text-cyan-400">
          <Radio size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">Live Updates</h1>
          <p className="text-foreground-muted">Update live variables used by AI in sequence messages.</p>
        </div>
      </div>

      <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
        <form onSubmit={handleSave} className="space-y-6">
          {CONTEXT_FIELDS.map((field) => (
            <div key={field.key} className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-medium text-foreground">
                <span className="text-muted">{field.icon}</span>
                {field.label}
              </label>
              <input
                type={field.type}
                value={contextData[field.key] || ''}
                placeholder={field.placeholder}
                onChange={e => setContextData({ ...contextData, [field.key]: e.target.value })}
                className="w-full bg-background border border-border rounded-lg px-4 py-3 text-sm text-foreground focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50 transition-all placeholder:text-muted"
              />
              <p className="text-xs text-muted">Internal key: <code className="bg-background px-1 py-0.5 rounded border border-border">{`{${field.key}}`}</code></p>
            </div>
          ))}

          <div className="pt-4 border-t border-border/50">
            <button
              type="submit"
              disabled={saving}
              className="w-full sm:w-auto flex items-center justify-center gap-2 bg-cyan-600 hover:bg-cyan-500 text-white px-6 py-3 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              <Save size={18} />
              {saving ? 'Saving...' : 'Save Context Updates'}
            </button>
          </div>
        </form>
      </div>
    </motion.div>
  );
}
