import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Download, Inbox } from 'lucide-react';
import api from '../lib/api';
import moment from 'moment';
import { motion } from 'framer-motion';

const SCORE_STYLES = {
  HOT: 'text-red-400',
  WARM: 'text-amber-400',
  COLD: 'text-blue-400'
};

const STATUS_COLORS = {
  new: 'bg-white/[0.03] text-gray-300 border border-white/[0.05]',
  qualifying: 'bg-purple-500/10 text-purple-300 border border-purple-500/20',
  stalled: 'bg-orange-500/10 text-orange-300 border border-orange-500/20',
  awaiting_call: 'bg-blue-500/10 text-blue-300 border border-blue-500/20',
  post_call: 'bg-teal-500/10 text-teal-300 border border-teal-500/20',
  fomo: 'bg-yellow-500/10 text-yellow-300 border border-yellow-500/20',
  cold: 'bg-slate-500/10 text-slate-300 border border-slate-500/20',
  closed: 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20',
  upsell: 'bg-yellow-400/10 text-yellow-200 border border-yellow-400/20',
  archived: 'bg-gray-800/30 text-gray-400 border border-gray-700/50',
  lost: 'bg-red-500/10 text-red-300 border border-red-500/20'
};

export default function Leads() {
  const [leads, setLeads] = useState([]);
  const [score, setScore] = useState('');
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchLeads = async () => {
    try {
      const res = await api.get('/dashboard/leads', {
        params: { score: score || undefined, status: status || undefined }
      });
      setLeads(res.data.leads);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    fetchLeads();
    const interval = setInterval(fetchLeads, 30000);
    return () => clearInterval(interval);
  }, [score, status]);

  const handleExport = () => {
    window.open(`${import.meta.env.VITE_API_URL || '/api'}/dashboard/leads/export`, '_blank');
  };

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="p-8 max-w-7xl mx-auto"
    >
      <div className="flex justify-between items-center mb-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-white/[0.03] border border-white/[0.05] rounded-xl flex items-center justify-center text-gray-200">
            <Inbox size={20} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Lead Inbox</h1>
          </div>
        </div>
        <button 
          onClick={handleExport}
          className="flex items-center gap-2 bg-white text-black px-4 py-2 rounded-lg text-sm font-semibold hover:bg-gray-200 transition-all"
        >
          <Download size={16} />
          Export CSV
        </button>
      </div>

      <div className="flex gap-3 mb-6">
        <select 
          value={score} 
          onChange={e => setScore(e.target.value)}
          className="bg-white/[0.02] border border-white/[0.05] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:ring-1 focus:ring-white/20 appearance-none [&>option]:bg-[#0f0f13] [&>option]:text-white cursor-pointer min-w-[140px]"
        >
          <option value="">All Scores</option>
          <option value="HOT">HOT</option>
          <option value="WARM">WARM</option>
          <option value="COLD">COLD</option>
        </select>
        
        <select 
          value={status} 
          onChange={e => setStatus(e.target.value)}
          className="bg-white/[0.02] border border-white/[0.05] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:ring-1 focus:ring-white/20 appearance-none [&>option]:bg-[#0f0f13] [&>option]:text-white cursor-pointer min-w-[140px]"
        >
          <option value="">All Stages</option>
          <option value="new">New</option>
          <option value="qualifying">Qualifying</option>
          <option value="stalled">Stalled</option>
          <option value="awaiting_call">Awaiting Call</option>
          <option value="post_call">Post Call</option>
          <option value="fomo">FOMO</option>
          <option value="cold">Cold</option>
          <option value="closed">Closed</option>
          <option value="upsell">Upsell</option>
          <option value="archived">Archived</option>
          <option value="lost">Lost</option>
        </select>
      </div>

      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-white/[0.02] text-gray-500 font-medium border-b border-white/[0.05] uppercase tracking-widest text-[11px]">
              <tr>
                <th className="px-6 py-4">Score</th>
                <th className="px-6 py-4">Name</th>
                <th className="px-6 py-4">Company</th>
                <th className="px-6 py-4">Industry</th>
                <th className="px-6 py-4">Budget</th>
                <th className="px-6 py-4">Call Time</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Time Ago</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.02]">
              {loading ? (
                <tr>
                  <td colSpan="8" className="px-6 py-12 text-center">
                    <div className="inline-block animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-white"></div>
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan="8" className="px-6 py-12 text-center text-gray-500 font-medium">No leads found matching criteria</td>
                </tr>
              ) : (
                leads.map((lead, idx) => (
                  <motion.tr 
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.02 }}
                    key={lead.id} 
                    onClick={() => navigate(`/leads/${lead.id}`)}
                    className="hover:bg-white/[0.02] cursor-pointer transition-colors group"
                  >
                    <td className="px-6 py-4">
                      {lead.lead_score ? (
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${lead.lead_score === 'HOT' ? 'bg-red-400' : lead.lead_score === 'WARM' ? 'bg-amber-400' : 'bg-blue-400'}`} />
                          <span className="font-semibold text-gray-300">{lead.lead_score}</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full bg-gray-600" />
                          <span className="text-gray-500 font-medium">UNKNOWN</span>
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 font-semibold text-gray-200 group-hover:text-white transition-colors">{lead.name || '—'}</td>
                    <td className="px-6 py-4 text-gray-400">{lead.company_name || '—'}</td>
                    <td className="px-6 py-4 text-gray-400 capitalize">{lead.industry?.replace('_', ' ') || '—'}</td>
                    <td className="px-6 py-4 text-gray-400">{lead.monthly_ad_budget?.replace('_', ' ') || '—'}</td>
                    <td className="px-6 py-4 text-gray-400">{lead.preferred_call_time || '—'}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded text-[11px] font-semibold tracking-widest uppercase ${STATUS_COLORS[lead.conv_status] || 'bg-white/[0.02] text-gray-500'}`}>
                        {lead.conv_status?.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-500 text-right">{moment(lead.created_at).fromNow()}</td>
                  </motion.tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </motion.div>
  );
}
