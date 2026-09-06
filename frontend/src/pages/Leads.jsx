import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Download, Inbox, ChevronDown, ChevronRight, Search, ArrowRight, Phone } from 'lucide-react';
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
  new: 'bg-card-hover text-foreground-muted border border-border',
  call_attempted: 'bg-indigo-500/10 text-indigo-300 border border-indigo-500/20',
  qualifying: 'bg-purple-500/10 text-purple-300 border border-purple-500/20',
  stalled: 'bg-orange-500/10 text-orange-300 border border-orange-500/20',
  awaiting_call: 'bg-blue-500/10 text-blue-300 border border-blue-500/20',
  post_call: 'bg-teal-500/10 text-teal-300 border border-teal-500/20',
  fomo: 'bg-yellow-500/10 text-yellow-300 border border-yellow-500/20',
  cold: 'bg-slate-500/10 text-slate-300 border border-slate-500/20',
  closed: 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20',
  upsell: 'bg-yellow-400/10 text-yellow-200 border border-yellow-400/20',
  archived: 'bg-card-hover text-muted border border-border',
  lost: 'bg-red-500/10 text-red-300 border border-red-500/20'
};

const PIPELINE_STAGES = [
  { id: 'new', label: 'New Leads', statuses: ['new', 'in_progress', 'qualifying', 'call_attempted'], color: 'from-blue-500/20 to-cyan-500/20', border: 'border-blue-500/30', text: 'text-blue-400' },
  { id: 'qualified', label: 'Qualified', statuses: ['awaiting_call'], color: 'from-purple-500/20 to-pink-500/20', border: 'border-purple-500/30', text: 'text-purple-400' },
  { id: 'nurturing', label: 'Nurturing', statuses: ['stalled', 'post_call', 'fomo', 'cold'], color: 'from-amber-500/20 to-orange-500/20', border: 'border-amber-500/30', text: 'text-amber-400' },
  { id: 'won', label: 'Closed Won', statuses: ['closed', 'upsell'], color: 'from-emerald-500/20 to-teal-500/20', border: 'border-emerald-500/30', text: 'text-emerald-400' },
  { id: 'lost', label: 'No Response / Lost', statuses: ['archived', 'lost'], color: 'from-gray-500/20 to-slate-500/20', border: 'border-gray-500/30', text: 'text-muted' },
];

export default function Leads() {
  const [leads, setLeads] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [activeStageId, setActiveStageId] = useState('new');
  const [expandedRowId, setExpandedRowId] = useState(null);
  const [outcomeUpdating, setOutcomeUpdating] = useState(null);
  
  const currentUserRole = localStorage.getItem('drootle_role');
  const currentUserUsername = localStorage.getItem('drootle_username');

  const [modalConfig, setModalConfig] = useState({ isOpen: false });
  const [modalInput, setModalInput] = useState('');
  
  // Bulk Upload State
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [pollingInterval, setPollingInterval] = useState(null);
  
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

  useEffect(() => {
    return () => {
      if (pollingInterval) clearInterval(pollingInterval);
    };
  }, [pollingInterval]);

  const handleExport = () => {
    window.open(`${import.meta.env.VITE_API_URL || '/api'}/dashboard/leads/export`, '_blank');
  };

  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;
    
    setUploading(true);
    setUploadError(null);
    const formData = new FormData();
    formData.append('file', uploadFile);
    
    try {
      const res = await api.post('/dashboard/leads/bulk-upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      const batchId = res.data.batch_id;
      
      const interval = setInterval(async () => {
        try {
          const statusRes = await api.get(`/dashboard/leads/bulk-upload/status/${batchId}`);
          setUploadProgress(statusRes.data);
          
          if (statusRes.data.status === 'completed') {
            clearInterval(interval);
            setUploading(false);
            fetchLeads();
          }
        } catch (err) {
          console.error(err);
        }
      }, 2000);
      
      setPollingInterval(interval);
    } catch (err) {
      setUploadError(err.response?.data?.detail || err.message);
      setUploading(false);
    }
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
    
    const targetLead = leads.find(l => l.id === leadId);
    
    try {
      await api.post(`/dashboard/leads/${leadId}/call-outcome`, { 
        outcome, 
        notes,
        last_updated_at: targetLead?.updated_at || null
      });
      await fetchLeads();
      setExpandedRowId(null);
    } catch (err) {
      if (err.response?.status === 409) {
        setModalConfig({
          isOpen: true,
          type: 'alert',
          title: 'Conflict Detected',
          description: err.response.data.detail
        });
        await fetchLeads(); // Auto-refresh to show latest data
      } else {
        setModalConfig({
          isOpen: true,
          type: 'alert',
          title: 'Error',
          description: err.response?.data?.error || "Failed to update outcome."
        });
      }
    } finally {
      setOutcomeUpdating(null);
    }
  };

  const handleClaim = async (e, leadId) => {
    e.stopPropagation();
    try {
      await api.post(`/dashboard/leads/${leadId}/claim`);
      await fetchLeads();
    } catch (err) {
      setModalConfig({
        isOpen: true,
        type: 'alert',
        title: 'Error',
        description: err.response?.data?.detail || err.response?.data?.error || "Failed to claim lead."
      });
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
          <div className="w-10 h-10 bg-card-hover border border-border rounded-xl flex items-center justify-center text-foreground-muted shadow-sm">
            <Inbox size={20} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground tracking-tight">CRM Pipeline</h1>
          </div>
        </div>
        
        <div className="flex items-center gap-4 w-full sm:w-auto">
          <div className="relative flex-1 sm:flex-none">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" size={16} />
            <input 
              type="text" 
              placeholder="Search leads..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full sm:w-64 bg-card-hover border border-border rounded-lg pl-9 pr-4 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-white/20 placeholder-gray-600 transition-all"
            />
          </div>
          <button 
            onClick={() => {
              setShowUploadModal(true);
              setUploadFile(null);
              setUploadProgress(null);
              setUploadError(null);
            }}
            className="flex items-center justify-center gap-2 bg-blue-600/20 text-blue-400 border border-blue-500/30 px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-500/30 transition-all shrink-0"
          >
            <span className="hidden sm:inline">Upload Leads</span>
          </button>
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
                    : 'bg-background border-border hover:bg-card-hover text-muted hover:text-foreground'
                  }
                `}
              >
                <span className={`text-3xl font-bold mb-1 ${isActive ? stage.text : 'text-foreground-muted'}`}>{count}</span>
                <span className={`text-xs font-semibold uppercase tracking-widest ${isActive ? stage.text : 'text-muted'}`}>{stage.label}</span>
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
            <p className="text-foreground-muted font-medium text-lg mb-2">No leads found</p>
            <p className="text-muted text-sm">There are no leads currently in the "{PIPELINE_STAGES.find(s => s.id === activeStageId)?.label}" stage.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-background text-muted font-medium border-b border-border uppercase tracking-widest text-[10px]">
                <tr>
                  <th className="px-6 py-4">Score</th>
                  <th className="px-6 py-4">Name</th>
                  <th className="px-6 py-4">Company</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Assigned To</th>
                  <th className="px-6 py-4 text-right">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {activeLeads.map((lead) => {
                  
                  // Construct Summary Logic
                  let aiSummary = "";
                  if (lead.ai_summary) {
                    aiSummary = lead.ai_summary;
                  } else if (lead.pain_point || lead.urgency || lead.budget) {
                    const parts = [];
                    if (lead.pain_point) parts.push(`Struggling with ${lead.pain_point.toLowerCase()}.`);
                    if (lead.budget) parts.push(`Budget is around ${lead.budget}.`);
                    if (lead.urgency) parts.push(`Timeline: ${lead.urgency}.`);
                    aiSummary = parts.join(" ");
                  }
                  
                  let summaryText = "";
                  if (lead.call_notes && aiSummary) {
                     summaryText = `[ AI Chat Summary ]\n${aiSummary}\n\n[ Sales Call Notes ]\n${lead.call_notes}`;
                  } else if (lead.call_notes) {
                     summaryText = `[ Sales Call Notes ]\n${lead.call_notes}`;
                  } else if (aiSummary) {
                     summaryText = `[ AI Chat Summary ]\n${aiSummary}`;
                  } else {
                     summaryText = "Lead has not provided enough information yet. No summary available.";
                  }

                  return (
                    <React.Fragment key={lead.id}>
                      <tr 
                        onClick={(e) => toggleRow(e, lead.id)}
                        className={`hover:bg-card-hover cursor-pointer transition-colors group bg-background ${expandedRowId === lead.id ? 'bg-card-hover' : ''}`}
                      >
                        <td className="px-6 py-4">
                          {lead.lead_score ? (
                            <div className="flex items-center gap-2">
                              <div className={`w-2 h-2 rounded-full ${lead.lead_score === 'HOT' ? 'bg-red-400' : lead.lead_score === 'WARM' ? 'bg-amber-400' : 'bg-blue-400'}`} />
                              <span className="font-semibold text-foreground-muted text-xs">{lead.lead_score}</span>
                            </div>
                          ) : (
                            <div className="flex items-center gap-2">
                              <div className="w-2 h-2 rounded-full bg-gray-700" />
                              <span className="text-gray-600 font-medium text-xs">UNRATED</span>
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4 font-semibold text-foreground-muted group-hover:text-foreground transition-colors">
                          <div className="flex items-center gap-2">
                            {lead.name || '—'}
                            {lead.call_attempted && (
                              <Phone size={14} className="text-cyan-500" title="Call Attempted" />
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-muted">{lead.company_name || '—'}</td>
                        <td className="px-6 py-4">
                          <span className={`px-2.5 py-1.5 rounded text-[10px] font-semibold tracking-widest uppercase ${STATUS_COLORS[lead.conv_status] || 'bg-card-hover text-muted'}`}>
                            {lead.conv_status?.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          {lead.assigned_to ? (
                            <span className="text-foreground-muted text-xs font-medium px-2 py-1 bg-white/[0.05] rounded border border-border">{lead.assigned_to}</span>
                          ) : (
                            <span className="text-muted text-xs italic">Unassigned</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-muted text-right text-xs font-medium">{moment(lead.created_at).format('MMM D, YYYY')}</td>
                      </tr>
                      
                      <AnimatePresence>
                        {expandedRowId === lead.id && (
                          <tr className="bg-white/[0.01]">
                            <td colSpan="5" className="px-6 py-6 border-b border-border">
                              <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: "auto", opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                transition={{ duration: 0.2 }}
                                className="flex flex-col md:flex-row gap-8 items-start overflow-hidden"
                              >
                                  <div className="flex-1 bg-card-hover border border-border rounded-xl p-5">
                                    <h4 className="text-[10px] font-semibold text-muted uppercase tracking-widest mb-3 flex items-center gap-2">
                                      <div className="w-1.5 h-1.5 rounded-full bg-cyan-500"></div>
                                      Lead Summary
                                    </h4>
                                    <p className="text-foreground-muted text-sm leading-relaxed whitespace-pre-wrap">
                                      {summaryText}
                                    </p>
                                  </div>
                                  
                                  <div className="w-full md:w-72 shrink-0 bg-background p-5 rounded-xl border border-border">
                                    {!lead.assigned_to ? (
                                      <div className="mb-4">
                                        <button 
                                          onClick={(e) => handleClaim(e, lead.id)}
                                          className="w-full bg-cyan-500 hover:bg-cyan-400 text-black text-xs font-bold uppercase tracking-widest py-3 px-4 rounded-lg transition-colors shadow-[0_0_15px_rgba(6,182,212,0.3)]"
                                        >
                                          Claim Lead
                                        </button>
                                      </div>
                                    ) : (
                                      <>
                                        <label className="block text-[10px] font-semibold text-muted uppercase tracking-widest mb-3">Log Call Outcome</label>
                                        <select 
                                          className="w-full bg-card-hover border border-border text-foreground-muted text-sm rounded-lg focus:ring-1 focus:ring-white/20 block p-3 disabled:opacity-50 [&>option]:bg-card [&>option]:text-foreground mb-4 hover:bg-white/[0.05] transition-colors outline-none cursor-pointer"
                                          onChange={(e) => handleOutcomeSelect(e, lead.id)}
                                          value=""
                                          disabled={outcomeUpdating === lead.id || (currentUserRole !== 'admin' && lead.assigned_to !== currentUserUsername)}
                                          onClick={e => e.stopPropagation()}
                                        >
                                          <option value="" disabled>Select outcome...</option>
                                          {CALL_OUTCOMES.map(o => (
                                            <option key={o.value} value={o.value}>{o.label}</option>
                                          ))}
                                        </select>
                                      </>
                                    )}
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
        isOpen={showUploadModal} 
        onClose={() => {
          if (!uploading) setShowUploadModal(false);
        }}
      >
        <div className="p-6 max-w-md w-full bg-background border border-border rounded-2xl shadow-2xl">
          <h2 className="text-xl font-bold text-foreground mb-4">Bulk Upload Leads</h2>
          
          {!uploadProgress ? (
            <form onSubmit={handleFileUpload} className="space-y-4">
              <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                <p className="text-sm text-blue-300 mb-2 font-semibold">CSV Format Required</p>
                <p className="text-xs text-blue-200/70">Required column: <code className="bg-black/30 px-1 py-0.5 rounded">phone</code></p>
                <p className="text-xs text-blue-200/70">Optional: <code className="bg-black/30 px-1 py-0.5 rounded">name</code>, <code className="bg-black/30 px-1 py-0.5 rounded">email</code>, <code className="bg-black/30 px-1 py-0.5 rounded">source_ad</code></p>
              </div>
              
              <div>
                <input 
                  type="file" 
                  accept=".csv"
                  onChange={(e) => setUploadFile(e.target.files[0])}
                  className="block w-full text-sm text-muted
                    file:mr-4 file:py-2 file:px-4
                    file:rounded-full file:border-0
                    file:text-sm file:font-semibold
                    file:bg-blue-500/20 file:text-blue-300
                    hover:file:bg-blue-500/30
                    cursor-pointer"
                  disabled={uploading}
                />
              </div>
              
              {uploadError && <p className="text-red-400 text-sm mt-2">{uploadError}</p>}
              
              <div className="pt-4 flex justify-end gap-3">
                <button 
                  type="button" 
                  onClick={() => setShowUploadModal(false)}
                  disabled={uploading}
                  className="px-4 py-2 rounded-lg text-sm font-medium hover:bg-card-hover transition-colors"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={!uploadFile || uploading}
                  className="px-4 py-2 rounded-lg text-sm font-semibold bg-white text-black hover:bg-gray-200 transition-colors disabled:opacity-50"
                >
                  {uploading ? 'Starting...' : 'Upload & Start'}
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-muted">Status:</span>
                <span className={`text-sm font-bold uppercase tracking-wider ${uploadProgress.status === 'completed' ? 'text-emerald-400' : 'text-blue-400 animate-pulse'}`}>
                  {uploadProgress.status}
                </span>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-card-hover p-4 rounded-xl border border-border">
                  <p className="text-xs text-muted font-medium mb-1">Total Found</p>
                  <p className="text-2xl font-bold text-foreground">{uploadProgress.total}</p>
                </div>
                <div className="bg-emerald-500/10 p-4 rounded-xl border border-emerald-500/20">
                  <p className="text-xs text-emerald-300 font-medium mb-1">New Created</p>
                  <p className="text-2xl font-bold text-emerald-400">{uploadProgress.created}</p>
                </div>
                <div className="bg-blue-500/10 p-4 rounded-xl border border-blue-500/20">
                  <p className="text-xs text-blue-300 font-medium mb-1">Messages Sent</p>
                  <p className="text-2xl font-bold text-blue-400">{uploadProgress.sent}</p>
                </div>
                <div className="bg-orange-500/10 p-4 rounded-xl border border-orange-500/20">
                  <p className="text-xs text-orange-300 font-medium mb-1">Duplicates Skipped</p>
                  <p className="text-2xl font-bold text-orange-400">{uploadProgress.skipped}</p>
                </div>
              </div>
              
              {uploadProgress.errors?.length > 0 && (
                <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg max-h-32 overflow-y-auto">
                  <p className="text-xs text-red-300 font-semibold mb-1">Errors:</p>
                  <ul className="list-disc list-inside text-xs text-red-200">
                    {uploadProgress.errors.map((e, i) => <li key={i}>{e}</li>)}
                  </ul>
                </div>
              )}
              
              {uploadProgress.status === 'completed' && (
                <div className="pt-4 flex justify-end">
                  <button 
                    onClick={() => setShowUploadModal(false)}
                    className="px-4 py-2 rounded-lg text-sm font-semibold bg-white text-black hover:bg-gray-200 transition-colors"
                  >
                    Done
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </Modal>

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
