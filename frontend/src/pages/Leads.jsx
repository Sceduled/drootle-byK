import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Download } from 'lucide-react';
import api from '../lib/api';
import moment from 'moment';

const scoreEmoji = {
  HOT: '🔴',
  WARM: '🟡',
  COLD: '🔵'
};

const STATUS_COLORS = {
  new: 'bg-gray-100 text-gray-700',
  qualifying: 'bg-purple-100 text-purple-700',
  stalled: 'bg-orange-100 text-orange-700',
  awaiting_call: 'bg-blue-100 text-blue-700',
  post_call: 'bg-teal-100 text-teal-700',
  fomo: 'bg-yellow-100 text-yellow-800',
  cold: 'bg-slate-200 text-slate-700',
  closed: 'bg-green-100 text-green-700',
  upsell: 'bg-yellow-200 text-yellow-900',
  archived: 'bg-gray-800 text-gray-200',
  lost: 'bg-red-100 text-red-700'
};

export default function Leads() {
  const [leads, setLeads] = useState([]);
  const [score, setScore] = useState('');
  const [status, setStatus] = useState('');
  const navigate = useNavigate();

  const fetchLeads = async () => {
    try {
      const res = await api.get('/dashboard/leads', {
        params: { score: score || undefined, status: status || undefined }
      });
      setLeads(res.data.leads);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchLeads();
    const interval = setInterval(fetchLeads, 30000);
    return () => clearInterval(interval);
  }, [score, status]);

  const handleExport = () => {
    window.open(`${import.meta.env.VITE_API_URL || '/api'}/dashboard/leads/export`, '_blank');
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Lead Inbox</h1>
        <button 
          onClick={handleExport}
          className="flex items-center gap-2 bg-white border border-gray-200 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors shadow-sm"
        >
          <Download size={16} />
          Export CSV
        </button>
      </div>

      <div className="flex gap-4 mb-6">
        <select 
          value={score} 
          onChange={e => setScore(e.target.value)}
          className="border border-gray-200 rounded-lg px-4 py-2 text-sm bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
        >
          <option value="">All Scores</option>
          <option value="HOT">HOT 🔴</option>
          <option value="WARM">WARM 🟡</option>
          <option value="COLD">COLD 🔵</option>
        </select>
        
        <select 
          value={status} 
          onChange={e => setStatus(e.target.value)}
          className="border border-gray-200 rounded-lg px-4 py-2 text-sm bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
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

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-gray-50 text-gray-500 font-medium border-b border-gray-200">
            <tr>
              <th className="px-6 py-4">Score</th>
              <th className="px-6 py-4">Name</th>
              <th className="px-6 py-4">Company</th>
              <th className="px-6 py-4">Industry</th>
              <th className="px-6 py-4">Budget</th>
              <th className="px-6 py-4">Call Time</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Time Ago</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {leads.map(lead => (
              <tr 
                key={lead.id} 
                onClick={() => navigate(`/leads/${lead.id}`)}
                className="hover:bg-gray-50 cursor-pointer transition-colors"
              >
                <td className="px-6 py-4">
                  {lead.lead_score ? `${scoreEmoji[lead.lead_score] || '⚪'} ${lead.lead_score}` : '⚪ UNKNOWN'}
                </td>
                <td className="px-6 py-4 font-medium text-gray-900">{lead.name || '—'}</td>
                <td className="px-6 py-4">{lead.company_name || '—'}</td>
                <td className="px-6 py-4 capitalize">{lead.industry?.replace('_', ' ') || '—'}</td>
                <td className="px-6 py-4">{lead.monthly_ad_budget?.replace('_', ' ') || '—'}</td>
                <td className="px-6 py-4">{lead.preferred_call_time || '—'}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded text-xs uppercase tracking-wider font-medium ${STATUS_COLORS[lead.conv_status] || 'bg-gray-100 text-gray-700'}`}>
                    {lead.conv_status?.replace('_', ' ')}
                  </span>
                </td>
                <td className="px-6 py-4 text-gray-500">{moment(lead.created_at).fromNow()}</td>
              </tr>
            ))}
            {leads.length === 0 && (
              <tr>
                <td colSpan="8" className="px-6 py-8 text-center text-gray-500">No leads found</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
