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

export default function LeadDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loadingAction, setLoadingAction] = useState(null);
  const messagesEndRef = useRef(null);

  const fetchLead = async () => {
    try {
      const res = await api.get(`/dashboard/leads/${id}`);
      setData(res.data);
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

  if (!data) return <div className="p-8 text-center text-gray-500">Loading...</div>;

  const { lead, conversations } = data;

  return (
    <div className="flex h-full">
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
            <button 
              onClick={() => handleAction('mark_closed')}
              disabled={loadingAction || lead.conv_status === 'closed'}
              className="bg-gray-100 hover:bg-gray-200 text-gray-900 font-medium py-2 px-4 rounded-lg transition-colors text-sm disabled:opacity-50"
            >
              Mark Closed
            </button>
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
                className="w-full bg-gray-900 hover:bg-gray-800 text-white font-medium py-3 px-4 rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2 group-disabled:bg-gray-300"
                title="Only works if Voice is enabled in environment"
              >
                <Phone size={18} /> Call Now
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
            const isMaya = msg.role === 'assistant';
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
      </div>
    </div>
  );
}
