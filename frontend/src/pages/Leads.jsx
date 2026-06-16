import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Download, Inbox, ChevronDown, ChevronRight, Search, ArrowRight } from 'lucide-react';
import api from '../lib/api';
import moment from 'moment';
import { motion, AnimatePresence } from 'framer-motion';

const CALL_OUTCOMES = [
  { value: "call_went_well",   label: "✅ Call went well" },
  { value: "reschedule",       label: "📅 Need to reschedule" },
  { value: "no_show",         label: "📵 No show" },
  { value: "not_interested",  label: "❌ Not interested" },
  { value: "deal_closed",     label: "🏆 Deal closed" },
];

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

const PIPELINE_STAGES = [
  { id: 'new', label: 'New Leads', statuses: ['new', 'in_progress', 'qualifying'], color: 'from-blue-500/20 to-cyan-500/20', border: 'border-blue-500/30', text: 'text-blue-400' },
  { id: 'qualified', label: 'Qualified', statuses: ['awaiting_call'], color: 'from-purple-500/20 to-pink-500/20', border: 'border-purple-500/30', text: 'text-purple-400' },
  { id: 'nurturing', label: 'Nurturing', statuses: ['stalled', 'post_call', 'fomo', 'cold'], color: 'from-amber-500/20 to-orange-500/20', border: 'border-amber-500/30', text: 'text-amber-400' },
  { id: 'won', label: 'Closed Won', statuses: ['closed', 'upsell'], color: 'from-emerald-500/20 to-teal-500/20', border: 'border-emerald-500/30', text: 'text-emerald-400' },
  { id: 'lost', label: 'No Response / Lost', statuses: ['archived', 'lost'], color: 'from-gray-500/20 to-slate-500/20', border: 'border-gray-500/30', text: 'text-gray-400' },
];

export default function Leads() {
  const [leads, setLeads] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [expandedStages, setExpandedStages] = useState({ new: true, qualified: true });
  const [expandedRowId, setExpandedRowId] = useState(null);
  const [outcomeUpdating, setOutcomeUpdating] = useState(null);
  const navigate = useNavigate();

  const fetchLeads = async () => {
    try {
      const res = await api.get('/dashboard/leads', { params: { limit: 1000 } });
      setLeads(res.data.leads || []);
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
  }, []);

  const handleExport = () => {
    window.open(`${import.meta.env.VITE_API_URL || '/api'}/dashboard/leads/export`, '_blank');
  };

  const toggleStage = (stageId) => {
    setExpandedStages(prev => ({ ...prev, [stageId]: !prev[stageId] }));
  };

  const toggleRow = (e, id) => {
    e.stopPropagation();
    setExpandedRowId(prev => prev === id ? null : id);
  };

  const handleOutcomeSelect = async (e, leadId) => {
    e.stopPropagation();
    const outcome = e.target.value;
    if (!outcome) return;
    
    let notes = null;
    if (outcome === "call_went_well") {
      const promptResult = window.prompt("Optional: Any quick notes from the call? (Maya will use this to write a highly personalized follow-up message)");
      if (promptResult === null) {
        e.target.value = "";
        return;
      }
      notes = promptResult;
    } else {
      if (!window.confirm("Are you sure you want to log this call outcome?")) {
        e.target.value = "";
        return;
      }
    }
    
    setOutcomeUpdating(leadId);
    try {
      await api.post(`/dashboard/leads/${leadId}/call-outcome`, { outcome, notes });
      await fetchLeads();
      setExpandedRowId(null);
    } catch (err) {
      alert(err.response?.data?.error || "Failed");
      e.target.value = "";
    } finally {
      setOutcomeUpdating(null);
    }
  };

  const filteredLeads = leads.filter(lead => 
    lead.name?.toLowerCase().includes(searchQuery.toLowerCase()) || 
    lead.company_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    lead.phone?.includes(searchQuery)
  );

  const getLeadsForStage = (stage) => {
    return filteredLeads.filter(lead => stage.statuses.includes(lead.conv_status));
  };

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="p-4 md:p-8 max-w-[1600px] mx-auto"
    >
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-white/[0.03] border border-white/[0.05] rounded-xl flex items-center justify-center text-gray-200 shadow-sm">
            <Inbox size={20} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">CRM Pipeline</h1>
          </div>
        </div>
        
        <div className="flex items-center gap-4 w-full sm:w-auto">
          <div className="relative flex-1 sm:flex-none">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
            <input 
              type="text" 
              placeholder="Search leads..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full sm:w-64 bg-white/[0.02] border border-white/[0.05] rounded-lg pl-9 pr-4 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-white/20 placeholder-gray-600 transition-all"
            />
          </div>
          <button 
            onClick={handleExport}
            className="flex items-center justify-center gap-2 bg-white text-black px-4 py-2 rounded-lg text-sm font-semibold hover:bg-gray-200 transition-all shrink-0"
          >
            <Download size={16} />
            <span className="hidden sm:inline">Export CSV</span>
          </button>
        </div>
      </div>

      {/* Top Pipeline Bar */}
      <div className="mb-8 overflow-x-auto pb-2 -mx-4 px-4 sm:mx-0 sm:px-0">
        <div className="flex items-center gap-2 min-w-max">
          {PIPELINE_STAGES.map((stage, idx) => {
            const count = getLeadsForStage(stage).length;
            return (
              <div key={stage.id} className="flex items-center">
                <div 
                  onClick={() => toggleStage(stage.id)}
                  className={`flex flex-col justify-center px-6 py-3 rounded-xl border bg-gradient-to-br cursor-pointer hover:scale-[1.02] transition-transform ${stage.color} ${stage.border} min-w-[160px] relative overflow-hidden group`}
                >
                  <div className="absolute inset-0 bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                  <span className={`text-2xl font-bold mb-1 ${stage.text}`}>{count}</span>
                  <span className={`text-xs font-semibold uppercase tracking-widest ${stage.text} opacity-80`}>{stage.label}</span>
                </div>
                {idx < PIPELINE_STAGES.length - 1 && (
                  <div className="w-8 flex justify-center text-gray-700">
                    <ChevronRight size={20} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Pipeline Accordions */}
      <div className="space-y-4">
        {loading ? (
          <div className="glass-card p-12 flex justify-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.5)]"></div>
          </div>
        ) : filteredLeads.length === 0 ? (
          <div className="glass-card p-12 text-center">
            <p className="text-gray-400 font-medium text-lg mb-2">No leads found in pipeline</p>
            <p className="text-gray-600 text-sm">Try adjusting your search criteria or wait for new leads to arrive.</p>
          </div>
        ) : (
          PIPELINE_STAGES.map((stage) => {
            const stageLeads = getLeadsForStage(stage);
            const isExpanded = expandedStages[stage.id];
            
            if (stageLeads.length === 0) return null;

            return (
              <div key={stage.id} className="glass-card overflow-hidden transition-all duration-300">
                {/* Accordion Header */}
                <button 
                  onClick={() => toggleStage(stage.id)}
                  className={`w-full flex items-center justify-between p-4 bg-gradient-to-r hover:bg-white/[0.02] transition-colors text-left border-l-4 ${
                    stage.id === 'new' ? 'border-l-blue-500 from-blue-500/5' :
                    stage.id === 'qualified' ? 'border-l-purple-500 from-purple-500/5' :
                    stage.id === 'nurturing' ? 'border-l-amber-500 from-amber-500/5' :
                    stage.id === 'won' ? 'border-l-emerald-500 from-emerald-500/5' :
                    'border-l-gray-500 from-gray-500/5'
                  } to-transparent`}
                >
                  <div className="flex items-center gap-3">
                    <div className="text-gray-500 transition-transform duration-300" style={{ transform: isExpanded ? 'rotate(0deg)' : 'rotate(-90deg)' }}>
                      <ChevronDown size={20} />
                    </div>
                    <span className={`font-semibold tracking-wide ${stage.text}`}>{stage.label}</span>
                    <span className="bg-white/10 px-2.5 py-0.5 rounded-full text-xs font-bold text-white">{stageLeads.length}</span>
                  </div>
                </button>

                {/* Accordion Content (Table) */}
                <AnimatePresence initial={false}>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3 }}
                      className="border-t border-white/[0.05]"
                    >
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm whitespace-nowrap">
                          <thead className="bg-[#09090b]/50 text-gray-500 font-medium border-b border-white/[0.05] uppercase tracking-widest text-[10px]">
                            <tr>
                              <th className="px-6 py-3">Score</th>
                              <th className="px-6 py-3">Name</th>
                              <th className="px-6 py-3">Company</th>
                              <th className="px-6 py-3">Industry</th>
                              <th className="px-6 py-3">Budget</th>
                              <th className="px-6 py-3">Call Time</th>
                              <th className="px-6 py-3">Status</th>
                              <th className="px-6 py-3 text-right">Time Ago</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-white/[0.02]">
                            {stageLeads.map((lead) => (
                              <React.Fragment key={lead.id}>
                                <tr 
                                  onClick={(e) => toggleRow(e, lead.id)}
                                  className={`hover:bg-white/[0.04] cursor-pointer transition-colors group bg-[#09090b]/20 ${expandedRowId === lead.id ? 'bg-white/[0.03]' : ''}`}
                                >
                                  <td className="px-6 py-3.5">
                                    {lead.lead_score ? (
                                      <div className="flex items-center gap-2">
                                        <div className={`w-2 h-2 rounded-full ${lead.lead_score === 'HOT' ? 'bg-red-400' : lead.lead_score === 'WARM' ? 'bg-amber-400' : 'bg-blue-400'}`} />
                                        <span className="font-semibold text-gray-300 text-xs">{lead.lead_score}</span>
                                      </div>
                                    ) : (
                                      <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-gray-700" />
                                        <span className="text-gray-600 font-medium text-xs">UNRATED</span>
                                      </div>
                                    )}
                                  </td>
                                  <td className="px-6 py-3.5 font-semibold text-gray-200 group-hover:text-white transition-colors">{lead.name || '—'}</td>
                                  <td className="px-6 py-3.5 text-gray-400">{lead.company_name || '—'}</td>
                                  <td className="px-6 py-3.5 text-gray-400 capitalize">{lead.industry?.replace('_', ' ') || '—'}</td>
                                  <td className="px-6 py-3.5 text-gray-400">{lead.monthly_ad_budget?.replace('_', ' ') || '—'}</td>
                                  <td className="px-6 py-3.5 text-gray-400">{lead.preferred_call_time || '—'}</td>
                                  <td className="px-6 py-3.5">
                                    <span className={`px-2 py-1 rounded text-[10px] font-semibold tracking-widest uppercase ${STATUS_COLORS[lead.conv_status] || 'bg-white/[0.02] text-gray-500'}`}>
                                      {lead.conv_status?.replace('_', ' ')}
                                    </span>
                                  </td>
                                  <td className="px-6 py-3.5 text-gray-500 text-right text-xs">{moment(lead.created_at).fromNow()}</td>
                                </tr>
                                
                                <AnimatePresence>
                                  {expandedRowId === lead.id && (
                                    <tr className="bg-white/[0.01]">
                                      <td colSpan="8" className="px-6 py-4 border-b border-white/[0.05]">
                                        <motion.div
                                          initial={{ height: 0, opacity: 0 }}
                                          animate={{ height: "auto", opacity: 1 }}
                                          exit={{ height: 0, opacity: 0 }}
                                          transition={{ duration: 0.2 }}
                                          className="flex flex-col md:flex-row gap-6 items-start overflow-hidden"
                                        >
                                           <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4 text-sm mt-2">
                                              <div>
                                                <span className="text-gray-500 text-[10px] uppercase tracking-widest font-semibold block mb-1">Pain Point</span>
                                                <span className="text-gray-300 whitespace-normal">{lead.pain_point || '—'}</span>
                                              </div>
                                              <div>
                                                <span className="text-gray-500 text-[10px] uppercase tracking-widest font-semibold block mb-1">Urgency</span>
                                                <span className="text-gray-300 whitespace-normal">{lead.urgency || '—'}</span>
                                              </div>
                                              <div>
                                                <span className="text-gray-500 text-[10px] uppercase tracking-widest font-semibold block mb-1">Target Markets</span>
                                                <span className="text-gray-300 whitespace-normal">{lead.target_markets?.join(', ') || '—'}</span>
                                              </div>
                                              <div>
                                                <span className="text-gray-500 text-[10px] uppercase tracking-widest font-semibold block mb-1">Phone Number</span>
                                                <span className="text-gray-300">{lead.phone || '—'}</span>
                                              </div>
                                           </div>
                                           <div className="w-full md:w-72 shrink-0 bg-[#09090b]/50 p-4 rounded-xl border border-white/[0.05]">
                                              <label className="block text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-2">Log Call Outcome</label>
                                              <select 
                                                className="w-full bg-white/[0.03] border border-white/[0.1] text-gray-200 text-sm rounded-lg focus:ring-1 focus:ring-white/20 block p-2.5 disabled:opacity-50 [&>option]:bg-[#0f0f13] [&>option]:text-white mb-3 hover:bg-white/[0.05] transition-colors outline-none"
                                                onChange={(e) => handleOutcomeSelect(e, lead.id)}
                                                value=""
                                                disabled={outcomeUpdating === lead.id}
                                                onClick={e => e.stopPropagation()}
                                              >
                                                <option value="" disabled>Select outcome...</option>
                                                {CALL_OUTCOMES.map(o => (
                                                  <option key={o.value} value={o.value}>{o.label}</option>
                                                ))}
                                              </select>
                                              <button 
                                                onClick={(e) => { e.stopPropagation(); navigate(`/leads/${lead.id}`); }}
                                                className="w-full text-center text-cyan-500 text-xs font-semibold uppercase tracking-widest hover:text-cyan-400 transition-colors py-2 flex items-center justify-center gap-2 hover:bg-white/[0.02] rounded-lg"
                                              >
                                                View Full Profile <ArrowRight size={14} />
                                              </button>
                                           </div>
                                        </motion.div>
                                      </td>
                                    </tr>
                                  )}
                                </AnimatePresence>
                              </React.Fragment>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })
        )}
      </div>
    </motion.div>
  );
}
