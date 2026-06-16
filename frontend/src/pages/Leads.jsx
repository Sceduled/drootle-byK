import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Download, Inbox, ChevronDown, ChevronRight, Search, ArrowRight } from 'lucide-react';
import api from '../lib/api';
import moment from 'moment';
import { motion, AnimatePresence } from 'framer-motion';
import Modal from '../components/Modal';

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
  const [activeStageId, setActiveStageId] = useState('new');
  const [expandedRowId, setExpandedRowId] = useState(null);
  const [outcomeUpdating, setOutcomeUpdating] = useState(null);
  const [modalConfig, setModalConfig] = useState({ isOpen: false });
  const [modalInput, setModalInput] = useState('');
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

  const toggleRow = (e, id) => {
    e.stopPropagation();
    setExpandedRowId(prev => prev === id ? null : id);
  };

  const handleOutcomeSelect = async (e, leadId) => {
    e.stopPropagation();
    const outcome = e.target.value;
    if (!outcome) return;
    
    if (outcome === "call_went_well") {
      setModalConfig({
        isOpen: true,
        type: 'prompt',
        title: 'Call Notes',
        description: 'Optional: Any quick notes from the call? (Maya will use this to write a highly personalized follow-up message)',
        leadId,
        outcome
      });
      setModalInput('');
    } else {
      setModalConfig({
        isOpen: true,
        type: 'confirm',
        title: 'Confirm Outcome',
        description: 'Are you sure you want to log this call outcome?',
        leadId,
        outcome
      });
    }
  };

  const executeOutcomeUpdate = async (notes = null) => {
    const { leadId, outcome } = modalConfig;
    setModalConfig({ isOpen: false });
    setOutcomeUpdating(leadId);
    try {
      await api.post(`/dashboard/leads/${leadId}/call-outcome`, { outcome, notes });
      await fetchLeads();
      setExpandedRowId(null);
    } catch (err) {
      setModalConfig({
        isOpen: true,
        type: 'alert',
        title: 'Error',
        description: err.response?.data?.error || "Failed to update outcome."
      });
    } finally {
      setOutcomeUpdating(null);
    }
  };

  const filteredLeads = leads.filter(lead => 
    lead.name?.toLowerCase().includes(searchQuery.toLowerCase()) || 
    lead.company_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    lead.phone?.includes(searchQuery)
  );

  const getLeadsForStage = (stageId) => {
    const stage = PIPELINE_STAGES.find(s => s.id === stageId);
    if (!stage) return [];
    return filteredLeads.filter(lead => stage.statuses.includes(lead.conv_status));
  };

  const activeLeads = getLeadsForStage(activeStageId);

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

      {/* Top Pipeline Bar as Tabs */}
      <div className="mb-8 overflow-x-auto pb-4 -mx-4 px-4 sm:mx-0 sm:px-0">
        <div className="flex items-center gap-3 min-w-max">
          {PIPELINE_STAGES.map((stage) => {
            const count = filteredLeads.filter(l => stage.statuses.includes(l.conv_status)).length;
            const isActive = activeStageId === stage.id;
            
            return (
              <div 
                key={stage.id} 
                onClick={() => {
                  setActiveStageId(stage.id);
                  setExpandedRowId(null);
                }}
                className={`flex flex-col justify-center px-6 py-4 rounded-xl border transition-all cursor-pointer min-w-[180px]
                  ${isActive 
                    ? `bg-gradient-to-br ${stage.color} ${stage.border} scale-105 shadow-lg` 
                    : 'bg-[#09090b]/50 border-white/[0.05] hover:bg-white/[0.02] opacity-60 hover:opacity-100'
                  }
                `}
              >
                <span className={`text-3xl font-bold mb-1 ${isActive ? stage.text : 'text-gray-300'}`}>{count}</span>
                <span className={`text-xs font-semibold uppercase tracking-widest ${isActive ? stage.text : 'text-gray-500'}`}>{stage.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Single Table for Active Stage */}
      <div className="glass-card overflow-hidden">
        {loading ? (
          <div className="p-12 flex justify-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.5)]"></div>
          </div>
        ) : activeLeads.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-gray-400 font-medium text-lg mb-2">No leads found</p>
            <p className="text-gray-600 text-sm">There are no leads currently in the "{PIPELINE_STAGES.find(s => s.id === activeStageId)?.label}" stage.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-[#09090b]/50 text-gray-500 font-medium border-b border-white/[0.05] uppercase tracking-widest text-[10px]">
                <tr>
                  <th className="px-6 py-4">Score</th>
                  <th className="px-6 py-4">Name</th>
                  <th className="px-6 py-4">Company</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4 text-right">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.02]">
                {activeLeads.map((lead) => {
                  
                  // Construct Summary Logic
                  let summaryText = "";
                  if (lead.call_notes) {
                    summaryText = lead.call_notes;
                  } else if (lead.pain_point || lead.urgency || lead.budget) {
                    const parts = [];
                    if (lead.pain_point) parts.push(`Struggling with ${lead.pain_point.toLowerCase()}.`);
                    if (lead.budget) parts.push(`Budget is around ${lead.budget}.`);
                    if (lead.urgency) parts.push(`Timeline: ${lead.urgency}.`);
                    summaryText = parts.join(" ");
                  } else {
                    summaryText = "Lead has not provided enough information yet. No summary available.";
                  }

                  return (
                    <React.Fragment key={lead.id}>
                      <tr 
                        onClick={(e) => toggleRow(e, lead.id)}
                        className={`hover:bg-white/[0.04] cursor-pointer transition-colors group bg-[#09090b]/20 ${expandedRowId === lead.id ? 'bg-white/[0.03]' : ''}`}
                      >
                        <td className="px-6 py-4">
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
                        <td className="px-6 py-4 font-semibold text-gray-200 group-hover:text-white transition-colors">{lead.name || '—'}</td>
                        <td className="px-6 py-4 text-gray-400">{lead.company_name || '—'}</td>
                        <td className="px-6 py-4">
                          <span className={`px-2.5 py-1.5 rounded text-[10px] font-semibold tracking-widest uppercase ${STATUS_COLORS[lead.conv_status] || 'bg-white/[0.02] text-gray-500'}`}>
                            {lead.conv_status?.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-gray-500 text-right text-xs font-medium">{moment(lead.created_at).format('MMM D, YYYY')}</td>
                      </tr>
                      
                      <AnimatePresence>
                        {expandedRowId === lead.id && (
                          <tr className="bg-white/[0.01]">
                            <td colSpan="5" className="px-6 py-6 border-b border-white/[0.05]">
                              <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: "auto", opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                transition={{ duration: 0.2 }}
                                className="flex flex-col md:flex-row gap-8 items-start overflow-hidden"
                              >
                                  <div className="flex-1 bg-white/[0.02] border border-white/[0.05] rounded-xl p-5">
                                    <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                                      <div className="w-1.5 h-1.5 rounded-full bg-cyan-500"></div>
                                      {lead.call_notes ? "Call Notes" : "AI Summary"}
                                    </h4>
                                    <p className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
                                      {summaryText}
                                    </p>
                                  </div>
                                  
                                  <div className="w-full md:w-72 shrink-0 bg-[#09090b]/50 p-5 rounded-xl border border-white/[0.05]">
                                    <label className="block text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-3">Log Call Outcome</label>
                                    <select 
                                      className="w-full bg-white/[0.03] border border-white/[0.1] text-gray-200 text-sm rounded-lg focus:ring-1 focus:ring-white/20 block p-3 disabled:opacity-50 [&>option]:bg-[#0f0f13] [&>option]:text-white mb-4 hover:bg-white/[0.05] transition-colors outline-none cursor-pointer"
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
                                      className="w-full text-center bg-cyan-500/10 text-cyan-400 text-xs font-semibold uppercase tracking-widest hover:bg-cyan-500/20 hover:text-cyan-300 transition-colors py-3 flex items-center justify-center gap-2 rounded-lg border border-cyan-500/20"
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
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Modal 
        isOpen={modalConfig.isOpen}
        onClose={() => setModalConfig({ isOpen: false })}
        title={modalConfig.title}
        description={modalConfig.description}
        type={modalConfig.type}
        inputValue={modalInput}
        setInputValue={setModalInput}
        onConfirm={() => {
          if (modalConfig.type === 'alert') {
            setModalConfig({ isOpen: false });
          } else {
            executeOutcomeUpdate(modalConfig.type === 'prompt' ? modalInput : null);
          }
        }}
        confirmText={modalConfig.type === 'alert' ? 'OK' : 'Submit'}
      />
    </motion.div>
  );
}
