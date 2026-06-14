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
  const messagesEndRef = useRef(null);

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
  }, [data?.conversations]);

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
    
    if (window.confirm("Are you sure you want to log this outcome?")) {
      setLoadingAction("outcome");
      try {
        await api.post(`/dashboard/leads/${id}/call-outcome`, { outcome });
        await fetchLead();
      } catch (err) {
        alert(err.response?.data?.error || 'Failed to log outcome');
      } finally {
        setLoadingAction(null);
      }
    }
    e.target.value = ""; // Reset dropdown
  };

  if (!data) return <div className="p-8 text-center text-gray-500">Loading...</div>;

  const { lead, conversations } = data;

  return (
    <div className="p-8 max-w-7xl mx-auto flex gap-6">
      
      {showOverrideModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-6">
            <h3 className="text-lg font-bold mb-4">Override Stage</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">New Stage</label>
                <select 
                  className="w-full border border-gray-300 rounded-lg p-2 text-sm"
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
                <label className="block text-sm font-medium text-gray-700 mb-1">Reason</label>
                <textarea 
                  className="w-full border border-gray-300 rounded-lg p-2 text-sm"
                  rows="3"
                  value={overrideReason}
                  onChange={e => setOverrideReason(e.target.value)}
                  placeholder="Why are you manually changing this stage?"
                />
              </div>
              <div className="flex gap-3 justify-end mt-6">
                <button 
                  onClick={() => setShowOverrideModal(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg"
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
                        reason: overrideReason
                      });
                      setShowOverrideModal(false);
                      setOverrideStatus("");
                      setOverrideReason("");
                      await fetchLead();
                    } catch (err) {
                      alert(err.response?.data?.error || "Failed");
                    }
                    setLoadingAction(null);
                  }}
                  disabled={loadingAction === "override"}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50"
                >
                  Confirm Override
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="w-96 border-r border-gray-200 bg-white flex flex-col shrink-0">
        <div className="p-6 border-b border-gray-100">
          <button 
            onClick={() => navigate('/leads')}
            className="flex items-center gap-2 text-gray-500 hover:text-gray-900 transition-colors mb-6 text-sm font-medium"
          >
            <ArrowLeft size={16} /> Back to Leads
          </button>
          
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">{lead.name || 'Unknown Name'}</h2>
              <p className="text-gray-500 flex items-center gap-2 mt-1">
                <Phone size={14} /> {lead.phone}
              </p>
            </div>
            {lead.lead_score && (
              <span className="bg-gray-100 px-3 py-1.5 rounded-full text-sm font-medium border border-gray-200">
                {scoreEmoji[lead.lead_score]} {lead.lead_score}
              </span>
            )}
          </div>
          
          <span className="inline-block bg-gray-100 text-gray-700 px-2 py-1 rounded text-xs uppercase tracking-wider font-medium mb-6">
            STATUS: {lead.conv_status}
          </span>

          <div className="space-y-3 mt-4 flex flex-col">
            {lead.conv_status === 'awaiting_call' && (
              <div className="mb-2">
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-2">Log Call Outcome</label>
                <select 
                  className="w-full bg-white border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block p-2.5 disabled:opacity-50"
                  onChange={handleOutcomeSelect}
                  disabled={loadingAction === "outcome"}
                  defaultValue=""
                >
                  <option value="" disabled>Select outcome...</option>
                  {CALL_OUTCOMES.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            )}
            <button 
              onClick={() => handleAction('mark_closed')}
              disabled={loadingAction || lead.conv_status === 'closed'}
              className="bg-gray-100 hover:bg-gray-200 text-gray-900 font-medium py-2 px-4 rounded-lg transition-colors text-sm disabled:opacity-50"
            >
              Mark Closed
            </button>
            {lead.conv_status === 'closed' && (
              <button 
                onClick={() => handleAction('start_upsell')}
                disabled={loadingAction}
                className="bg-purple-50 hover:bg-purple-100 text-purple-700 font-medium py-2 px-4 rounded-lg transition-colors text-sm disabled:opacity-50"
              >
                Mark Upsell Opportunity
              </button>
            )}
            <button 
              onClick={() => handleAction('mark_hot')}
              disabled={loadingAction || lead.lead_score === 'HOT'}
              className="bg-red-50 hover:bg-red-100 text-red-700 font-medium py-2 px-4 rounded-lg transition-colors text-sm disabled:opacity-50"
            >
              Mark HOT
            </button>
            <button 
              onClick={() => handleAction('renotify_sales')}
              disabled={loadingAction}
              className="bg-blue-50 hover:bg-blue-100 text-blue-700 font-medium py-2 px-4 rounded-lg transition-colors text-sm disabled:opacity-50"
            >
              Re-notify Sales
            </button>
            <div className="relative group mt-4">
              <button 
                onClick={() => handleAction('call_now')}
                disabled={loadingAction}
                className="w-full bg-gray-900 hover:bg-gray-800 text-white font-medium py-3 px-4 rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2 group-disabled:bg-gray-300 mb-2"
                title="Only works if Voice is enabled in environment"
              >
                <Phone size={18} /> Call Now
              </button>
              <button 
                onClick={() => setShowOverrideModal(true)}
                className="w-full bg-red-50 hover:bg-red-100 text-red-700 font-medium py-2 px-4 rounded-lg transition-colors text-sm"
              >
                Override Stage
              </button>
            </div>
          </div>
        </div>

        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          <div>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Company Details</h3>
            <div className="space-y-3">
              <div className="flex gap-3 text-sm"><Building2 size={16} className="text-gray-400 mt-0.5" /> <span className="text-gray-900">{lead.company_name || '—'}</span></div>
              <div className="flex gap-3 text-sm"><Target size={16} className="text-gray-400 mt-0.5" /> <span className="text-gray-900 capitalize">{lead.industry?.replace('_', ' ') || '—'}</span></div>
              <div className="flex gap-3 text-sm"><DollarSign size={16} className="text-gray-400 mt-0.5" /> <span className="text-gray-900">{lead.monthly_ad_budget?.replace('_', ' ') || '—'}</span></div>
            </div>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Qualification Info</h3>
            <div className="space-y-4 text-sm">
              <div>
                <p className="text-gray-500 mb-1">Pain Point</p>
                <p className="text-gray-900 bg-gray-50 p-2 rounded border border-gray-100">{lead.pain_point || '—'}</p>
              </div>
              <div>
                <p className="text-gray-500 mb-1">Target Markets</p>
                <p className="text-gray-900">{lead.target_markets?.join(', ') || '—'}</p>
              </div>
              <div>
                <p className="text-gray-500 mb-1">Urgency</p>
                <p className="text-gray-900">{lead.urgency || '—'}</p>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Logistics</h3>
            <div className="flex gap-3 text-sm">
              <Clock size={16} className="text-gray-400 mt-0.5" /> 
              <div>
                <p className="text-gray-500 mb-1">Preferred Call Time</p>
                <p className="text-gray-900">{lead.preferred_call_time || '—'}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 flex flex-col bg-gray-50">
        <div className="p-6 border-b border-gray-200 bg-white">
          <h2 className="text-lg font-bold text-gray-900">Conversation History</h2>
          <p className="text-sm text-gray-500">Live chat view</p>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {conversations.map((msg, idx) => {
            const isSystem = msg.role === 'system';
            const isAgent = msg.role === 'assistant';
            const isUser = msg.role === 'user';
            
            if (isSystem) {
              return (
                <div key={idx} className="flex justify-center">
                  <div className="bg-gray-200 text-gray-600 text-xs px-4 py-2 rounded-lg max-w-lg text-center font-mono whitespace-pre-wrap">
                    {msg.content}
                    <div className="mt-1 opacity-50">{moment(msg.created_at).format('MMM D, h:mm A')}</div>
                  </div>
                </div>
              );
            }

            return (
              <div key={idx} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-xl rounded-2xl px-5 py-3 ${isUser ? 'bg-gray-900 text-white rounded-br-none' : 'bg-white border border-gray-200 text-gray-900 rounded-bl-none shadow-sm'}`}>
                  <div className="whitespace-pre-wrap text-[15px] leading-relaxed">{msg.content}</div>
                  <div className={`text-[11px] mt-2 ${isUser ? 'text-gray-400' : 'text-gray-400'}`}>
                    {moment(msg.created_at).format('h:mm A')}
                  </div>
                </div>
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>

        {/* Stage History */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 mt-6 overflow-hidden">
          <div className="border-b border-gray-200 px-6 py-4 bg-gray-50 flex items-center gap-2">
            <h3 className="font-semibold text-gray-900">Stage History</h3>
          </div>
          <div className="p-6">
            <div className="space-y-6">
              {history.map((item, idx) => (
                <div key={idx} className="relative flex gap-4">
                  {idx !== history.length - 1 && (
                    <div className="absolute top-8 left-[11px] bottom-[-24px] w-px bg-gray-200" />
                  )}
                  <div className="mt-1 w-[22px] h-[22px] rounded-full bg-blue-100 border-4 border-white flex-shrink-0 z-10" />
                  
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-gray-900 capitalize">
                        {item.from_status ? item.from_status.replace('_', ' ') : 'None'} 
                        <span className="text-gray-400 mx-1">→</span>
                        {item.to_status.replace('_', ' ')}
                      </span>
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded uppercase tracking-wider">
                        {item.triggered_by}
                      </span>
                    </div>
                    {item.notes && <p className="text-sm text-gray-500 mb-1">{item.notes}</p>}
                    <p className="text-xs text-gray-400">{moment(item.created_at).format('MMM D, YYYY h:mm A')}</p>
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
