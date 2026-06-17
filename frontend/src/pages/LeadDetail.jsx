import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Phone, Building2, Target, DollarSign, Clock } from 'lucide-react';
import api from '../lib/api';
import moment from 'moment';

const scoreEmoji = {
  HOT: '🔴',
  WARM: '🟡',
  COLD: '🔵'
};

const CALL_OUTCOMES = [
  { value: "call_went_well",   label: "✅ Call went well" },
  { value: "reschedule",       label: "📅 Need to reschedule" },
  { value: "no_show",         label: "📵 No show" },
  { value: "not_interested",  label: "❌ Not interested" },
  { value: "deal_closed",     label: "🏆 Deal closed" },
];

export default function LeadDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [history, setHistory] = useState([]);
  const [loadingAction, setLoadingAction] = useState(null);
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const [overrideStatus, setOverrideStatus] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [outcomeSelection, setOutcomeSelection] = useState("");
  const messagesEndRef = useRef(null);

  const currentUserRole = localStorage.getItem('drootle_role');
  const currentUserUsername = localStorage.getItem('drootle_username');

  const fetchLead = async () => {
    try {
      const res = await api.get(`/dashboard/leads/${id}`);
      setData(res.data);
      try {
        const histRes = await api.get(`/dashboard/leads/${id}/history`);
        setHistory(histRes.data);
      } catch (e) {
        console.error("Failed to load history", e);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchLead();
    const interval = setInterval(fetchLead, 10000);
    return () => clearInterval(interval);
  }, [id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [data?.conversations?.length]);

  const handleAction = async (action) => {
    setLoadingAction(action);
    try {
      await api.post(`/dashboard/leads/${id}/action`, { action });
      await fetchLead();
      if (action === 'call_now') {
        alert('Call dispatched!');
      }
    } catch (err) {
      alert(err.response?.data?.error || 'Action failed');
    } finally {
      setLoadingAction(null);
    }
  };

  const handleOutcomeSelect = async (e) => {
    const outcome = e.target.value;
    if (!outcome) return;
    
    let notes = null;
    if (outcome === "call_went_well") {
      const promptResult = window.prompt("Optional: Any quick notes from the call? (Maya will use this to write a highly personalized follow-up message)");
      if (promptResult === null) {
        setOutcomeSelection("");
        return;
      }
      notes = promptResult;
    } else {
      if (!window.confirm("Are you sure you want to log this outcome?")) {
        setOutcomeSelection("");
        return;
      }
    }
    
    setLoadingAction("outcome");
    try {
      await api.post(`/dashboard/leads/${id}/call-outcome`, { 
        outcome, 
        notes,
        last_updated_at: data?.lead?.updated_at || null
      });
      await fetchLead();
    } catch (err) {
      if (err.response?.status === 409) {
        alert(err.response.data.detail);
        await fetchLead(); // Auto-refresh to show latest data
      } else {
        alert(err.response?.data?.error || 'Failed to log outcome');
      }
    } finally {
      setLoadingAction(null);
    }
    
    setOutcomeSelection(""); // Reset dropdown
  };

  const handleClaim = async () => {
    try {
      await api.post(`/dashboard/leads/${id}/claim`);
      await fetchLead();
    } catch (err) {
      alert(err.response?.data?.detail || err.response?.data?.error || "Failed to claim lead.");
    }
  };

  if (!data) return <div className="p-8 text-center text-gray-500">Loading...</div>;

  const { lead, conversations } = data;

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto flex flex-col md:flex-row gap-6">
      
      {showOverrideModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
          <div className="glass-card max-w-md w-full p-6 border border-white/[0.1]">
            <h3 className="text-lg font-semibold text-white mb-4">Override Stage</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">New Stage</label>
                <select 
                  className="w-full bg-white/[0.02] border border-white/[0.05] rounded-lg p-2.5 text-sm text-gray-300 focus:outline-none focus:ring-1 focus:ring-white/20 [&>option]:bg-[#0f0f13] [&>option]:text-white"
                  value={overrideStatus}
                  onChange={e => setOverrideStatus(e.target.value)}
                >
                  <option value="">Select...</option>
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
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">Reason</label>
                <textarea 
                  className="w-full bg-white/[0.02] border border-white/[0.05] rounded-lg p-2.5 text-sm text-gray-300 focus:outline-none focus:ring-1 focus:ring-white/20 placeholder-gray-600"
                  rows="3"
                  value={overrideReason}
                  onChange={e => setOverrideReason(e.target.value)}
                  placeholder="Why are you manually changing this stage?"
                />
              </div>
              <div className="flex gap-3 justify-end mt-6">
                <button 
                  onClick={() => setShowOverrideModal(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-400 bg-white/[0.03] hover:bg-white/[0.05] border border-white/[0.05] rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button 
                  onClick={async () => {
                    if (!overrideStatus || !overrideReason) {
                      alert("Status and reason are required");
                      return;
                    }
                    setLoadingAction("override");
                    try {
                      await api.post(`/dashboard/leads/${id}/force-stage`, {
                        status: overrideStatus,
                        reason: overrideReason,
                        last_updated_at: lead?.updated_at || null
                      });
                      setShowOverrideModal(false);
                      setOverrideStatus("");
                      setOverrideReason("");
                      await fetchLead();
                    } catch (err) {
                      if (err.response?.status === 409) {
                        alert("⚠️ " + err.response.data.detail);
                        await fetchLead(); // Auto-refresh to show latest data
                      } else {
                        alert(err.response?.data?.error || "Failed");
                      }
                    }
                    setLoadingAction(null);
                  }}
                  disabled={loadingAction === "override"}
                  className="px-4 py-2 text-sm font-medium text-black bg-white hover:bg-gray-200 rounded-lg disabled:opacity-50 transition-colors"
                >
                  Confirm Override
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="w-full md:w-96 border-b md:border-b-0 md:border-r border-white/[0.05] glass-sidebar flex flex-col shrink-0">
        <div className="p-6 border-b border-white/[0.05]">
          <button 
            onClick={() => navigate('/leads')}
            className="flex items-center gap-2 text-gray-500 hover:text-white transition-colors mb-6 text-sm font-medium"
          >
            <ArrowLeft size={16} /> Back to Leads
          </button>
          
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-xl font-bold text-white">{lead.name || 'Unknown Name'}</h2>
              <p className="text-gray-400 flex items-center gap-2 mt-1 text-sm">
                <Phone size={14} /> {lead.phone}
              </p>
            </div>
            {lead.lead_score && (
              <span className="bg-white/[0.03] px-3 py-1.5 rounded text-[11px] font-semibold tracking-widest uppercase border border-white/[0.05] text-white">
                {scoreEmoji[lead.lead_score]} {lead.lead_score}
              </span>
            )}
          </div>
          
          <div className="flex gap-2 mb-6">
            <span className="inline-block bg-white/[0.03] text-gray-300 px-2.5 py-1 rounded text-[11px] uppercase tracking-widest font-semibold border border-white/[0.05]">
              STATUS: {lead.conv_status}
            </span>
            {lead.assigned_to ? (
              <span className="inline-block bg-white/[0.03] text-gray-300 px-2.5 py-1 rounded text-[11px] uppercase tracking-widest font-semibold border border-white/[0.05]">
                {lead.assigned_to}
              </span>
            ) : (
              <span className="inline-block bg-white/[0.02] text-gray-500 px-2.5 py-1 rounded text-[11px] uppercase tracking-widest font-semibold border border-white/[0.05] italic">
                Unassigned
              </span>
            )}
          </div>

          <div className="space-y-3 mt-4 flex flex-col">
            {!lead.assigned_to && (
              <button 
                onClick={handleClaim}
                className="w-full bg-cyan-500 hover:bg-cyan-400 text-black text-xs font-bold uppercase tracking-widest py-3 px-4 rounded-lg transition-colors shadow-[0_0_15px_rgba(6,182,212,0.3)] mb-4"
              >
                Claim Lead
              </button>
            )}
            {lead.conv_status === 'awaiting_call' && (
              <div className="mb-2">
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-widest mb-2">Log Call Outcome</label>
                <select 
                  className="w-full bg-white/[0.02] border border-white/[0.05] text-white text-sm rounded-lg focus:ring-1 focus:ring-white/20 block p-2.5 disabled:opacity-50 [&>option]:bg-[#0f0f13] [&>option]:text-white"
                  onChange={handleOutcomeSelect}
                  value={outcomeSelection}
                  disabled={loadingAction === "outcome" || (currentUserRole !== 'admin' && lead.assigned_to !== currentUserUsername)}
                >
                  <option value="" disabled>Select outcome...</option>
                  {CALL_OUTCOMES.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            )}
            {lead.conv_status === 'closed' && (
              <button 
                onClick={() => handleAction('start_upsell')}
                disabled={loadingAction}
                className="bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 font-medium py-2.5 px-4 rounded-lg transition-colors text-sm disabled:opacity-50 border border-purple-500/20"
              >
                Mark Upsell Opportunity
              </button>
            )}
            <button 
              onClick={() => handleAction('mark_hot')}
              disabled={loadingAction || lead.lead_score === 'HOT'}
              className="bg-red-500/10 hover:bg-red-500/20 text-red-400 font-medium py-2.5 px-4 rounded-lg transition-colors text-sm disabled:opacity-50 border border-red-500/20"
            >
              Mark HOT
            </button>
            <button 
              onClick={() => handleAction('renotify_sales')}
              disabled={loadingAction}
              className="bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 font-medium py-2.5 px-4 rounded-lg transition-colors text-sm disabled:opacity-50 border border-blue-500/20"
            >
              Re-notify Sales
            </button>
            <div className="relative group mt-4">
              <button 
                onClick={() => handleAction('call_now')}
                disabled={loadingAction}
                className="w-full bg-white hover:bg-gray-200 text-black font-semibold py-3 px-4 rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2 group-disabled:bg-gray-300 mb-2"
                title="Only works if Voice is enabled in environment"
              >
                <Phone size={18} /> Call Now
              </button>
              <button 
                onClick={() => setShowOverrideModal(true)}
                disabled={currentUserRole !== 'admin' && lead.assigned_to !== currentUserUsername}
                className="w-full bg-white/[0.03] hover:bg-white/[0.05] text-gray-300 font-medium py-2 px-4 rounded-lg transition-colors text-sm border border-white/[0.05] disabled:opacity-50"
              >
                Override Stage
              </button>
            </div>
          </div>
        </div>

        <div className="p-6 overflow-y-auto space-y-8 flex-1">
          <div>
            <h3 className="text-[11px] font-semibold text-gray-500 uppercase tracking-widest mb-4">Company Details</h3>
            <div className="space-y-4">
              <div className="flex gap-3 text-sm items-center"><Building2 size={16} className="text-gray-500" /> <span className="text-gray-300">{lead.company_name || '—'}</span></div>
              <div className="flex gap-3 text-sm items-center"><Target size={16} className="text-gray-500" /> <span className="text-gray-300 capitalize">{lead.industry?.replace('_', ' ') || '—'}</span></div>
              <div className="flex gap-3 text-sm items-center"><DollarSign size={16} className="text-gray-500" /> <span className="text-gray-300">{lead.monthly_ad_budget?.replace('_', ' ') || '—'}</span></div>
            </div>
          </div>

          <div>
            <h3 className="text-[11px] font-semibold text-gray-500 uppercase tracking-widest mb-4">Qualification Info</h3>
            <div className="space-y-4 text-sm">
              <div>
                <p className="text-gray-500 mb-1 text-xs">Pain Point</p>
                <p className="text-gray-300 bg-white/[0.02] p-3 rounded-lg border border-white/[0.05]">{lead.pain_point || '—'}</p>
              </div>
              <div>
                <p className="text-gray-500 mb-1 text-xs">Target Markets</p>
                <p className="text-gray-300">{lead.target_markets?.join(', ') || '—'}</p>
              </div>
              <div>
                <p className="text-gray-500 mb-1 text-xs">Urgency</p>
                <p className="text-gray-300">{lead.urgency || '—'}</p>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-[11px] font-semibold text-gray-500 uppercase tracking-widest mb-4">Logistics</h3>
            <div className="flex gap-3 text-sm items-start">
              <Clock size={16} className="text-gray-500 mt-0.5" /> 
              <div>
                <p className="text-gray-500 mb-1 text-xs">Preferred Call Time</p>
                <p className="text-gray-300">{lead.preferred_call_time || '—'}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 flex flex-col bg-[#09090b] relative">
        <div className="p-6 border-b border-white/[0.05] bg-transparent relative z-10 backdrop-blur-sm">
          <h2 className="text-lg font-semibold text-white tracking-wide">Conversation History</h2>
          <p className="text-sm text-gray-500">Live chat view</p>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6 space-y-6 relative z-10">
          {conversations.map((msg, idx) => {
            const isSystem = msg.role === 'system';
            const isAgent = msg.role === 'assistant';
            const isUser = msg.role === 'user';
            
            if (isSystem) {
              return (
                <div key={idx} className="flex justify-center">
                  <div className="bg-white/[0.02] border border-white/[0.05] text-gray-400 text-[11px] px-4 py-2 rounded-lg max-w-lg text-center font-mono whitespace-pre-wrap">
                    {msg.content}
                    <div className="mt-1 opacity-50">{moment(msg.created_at).format('MMM D, h:mm A')}</div>
                  </div>
                </div>
              );
            }

            return (
              <div key={idx} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-xl rounded-2xl px-5 py-3 ${isUser ? 'bg-blue-600 text-white rounded-br-none' : 'bg-[#18181b] border border-white/[0.05] text-gray-200 rounded-bl-none shadow-sm'}`}>
                  <div className="whitespace-pre-wrap text-[14px] leading-relaxed">{msg.content}</div>
                  <div className={`text-[10px] mt-2 font-medium tracking-wide ${isUser ? 'text-blue-200' : 'text-gray-500'}`}>
                    {moment(msg.created_at).format('h:mm A')}
                  </div>
                </div>
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>

        {/* Stage History */}
        <div className="glass-card m-6 overflow-hidden relative z-10">
          <div className="border-b border-white/[0.05] px-6 py-4 bg-white/[0.01] flex items-center gap-2">
            <h3 className="font-semibold text-white tracking-wide">Stage History</h3>
          </div>
          <div className="p-6">
            <div className="space-y-6">
              {history.map((item, idx) => (
                <div key={idx} className="relative flex gap-4">
                  {idx !== history.length - 1 && (
                    <div className="absolute top-8 left-[11px] bottom-[-24px] w-px bg-white/[0.1]" />
                  )}
                  <div className="mt-1 w-[22px] h-[22px] rounded-full bg-blue-500/20 border-4 border-[#0f0f13] flex-shrink-0 z-10" />
                  
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-semibold text-gray-200 capitalize">
                        {item.from_status ? item.from_status.replace('_', ' ') : 'None'} 
                        <span className="text-gray-500 mx-1">→</span>
                        <span className="text-white">{item.to_status.replace('_', ' ')}</span>
                      </span>
                      <span className="text-[10px] bg-white/[0.05] border border-white/[0.05] text-gray-400 px-2 py-0.5 rounded uppercase tracking-widest font-semibold">
                        {item.triggered_by}
                      </span>
                    </div>
                    {item.notes && <p className="text-sm text-gray-400 mb-1">{item.notes}</p>}
                    <p className="text-xs text-gray-500">{moment(item.created_at).format('MMM D, YYYY h:mm A')}</p>
                  </div>
                </div>
              ))}
              {history.length === 0 && (
                <p className="text-sm text-gray-500">No stage history recorded yet.</p>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
