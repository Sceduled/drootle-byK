import { useState, useEffect } from 'react';
import api from '../lib/api';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Users, PhoneCall, Clock, CheckCircle, XCircle, Trophy, Activity, RotateCcw } from 'lucide-react';

const COLORS = {
  HOT: '#ef4444',
  WARM: '#eab308',
  COLD: '#3b82f6'
};

const STAGE_COLORS = ['#3b82f6', '#8b5cf6', '#f97316', '#06b6d4', '#14b8a6', '#eab308', '#64748b', '#22c55e', '#ef4444', '#1f2937'];

export default function Metrics() {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    api.get('/dashboard/metrics').then(res => setMetrics(res.data)).catch(console.error);
  }, []);

  if (!metrics) return <div className="p-8 text-gray-500">Loading metrics...</div>;

  const scoreData = [
    { name: 'HOT', value: metrics.hot_count },
    { name: 'WARM', value: metrics.warm_count },
    { name: 'COLD', value: metrics.cold_count }
  ].filter(d => d.value > 0);

  const funnelData = [
    { name: 'New', value: metrics.leads_by_stage?.new || 0 },
    { name: 'Qualifying', value: metrics.leads_by_stage?.qualifying || 0 },
    { name: 'Call', value: (metrics.leads_by_stage?.awaiting_call || 0) + (metrics.leads_by_stage?.post_call || 0) },
    { name: 'Closed', value: metrics.leads_by_stage?.closed || 0 }
  ];

  const stageData = Object.entries(metrics.leads_by_stage || {}).map(([name, value]) => ({
    name: name.replace('_', ' '),
    value
  })).filter(d => d.value > 0);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Lifecycle Metrics</h1>

      {/* Primary KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Total Leads</p>
              <h3 className="text-3xl font-bold text-gray-900 mt-1">{metrics.total_leads}</h3>
            </div>
            <div className="w-12 h-12 bg-blue-50 rounded-full flex items-center justify-center text-blue-600">
              <Users size={24} />
            </div>
          </div>
          <div className="mt-4 text-sm text-gray-600">
            <span className="font-medium text-blue-600">+{metrics.leads_today}</span> today
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Awaiting Call</p>
              <h3 className="text-3xl font-bold text-gray-900 mt-1">{metrics.leads_by_stage?.awaiting_call || 0}</h3>
            </div>
            <div className="w-12 h-12 bg-purple-50 rounded-full flex items-center justify-center text-purple-600">
              <PhoneCall size={24} />
            </div>
          </div>
          <div className="mt-4 text-sm text-gray-600">
            {metrics.conversion_qualifying_to_call}% conversion from qualified
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Deals Closed</p>
              <h3 className="text-3xl font-bold text-gray-900 mt-1">{metrics.leads_by_stage?.closed || 0}</h3>
            </div>
            <div className="w-12 h-12 bg-green-50 rounded-full flex items-center justify-center text-green-600">
              <Trophy size={24} />
            </div>
          </div>
          <div className="mt-4 text-sm text-gray-600">
            {metrics.conversion_call_to_closed}% close rate from calls
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Lost / Opt-Out</p>
              <h3 className="text-3xl font-bold text-gray-900 mt-1">{metrics.leads_by_stage?.lost || 0}</h3>
            </div>
            <div className="w-12 h-12 bg-red-50 rounded-full flex items-center justify-center text-red-600">
              <XCircle size={24} />
            </div>
          </div>
          <div className="mt-4 text-sm text-gray-600">
            {metrics.opt_out_rate}% opt-out rate
          </div>
        </div>
      </div>

      {/* Recovery & Time Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Recovery Rates */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <RotateCcw className="text-gray-400" size={20} />
            <h3 className="text-lg font-bold text-gray-900">AI Sequence Recovery Rates</h3>
          </div>
          <div className="space-y-6">
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm font-medium text-gray-700">Sequence 3: DNP Recovery</span>
                <span className="text-sm font-medium text-gray-900">{metrics.sequence_recovery_rate?.dnp}%</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div className="bg-orange-500 h-2 rounded-full" style={{ width: `${metrics.sequence_recovery_rate?.dnp}%` }}></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm font-medium text-gray-700">Sequence 6: FOMO Revival</span>
                <span className="text-sm font-medium text-gray-900">{metrics.sequence_recovery_rate?.fomo}%</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div className="bg-yellow-500 h-2 rounded-full" style={{ width: `${metrics.sequence_recovery_rate?.fomo}%` }}></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm font-medium text-gray-700">Sequence 7: Cold Reactivation</span>
                <span className="text-sm font-medium text-gray-900">{metrics.sequence_recovery_rate?.cold}%</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${metrics.sequence_recovery_rate?.cold}%` }}></div>
              </div>
            </div>
          </div>
        </div>

        {/* Funnel Chart */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <Activity className="text-gray-400" size={20} />
            <h3 className="text-lg font-bold text-gray-900">Sales Funnel</h3>
          </div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={funnelData} layout="vertical" margin={{ top: 0, right: 0, left: 20, bottom: 0 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} />
                <Tooltip cursor={{ fill: '#f9fafb' }} />
                <Bar dataKey="value" fill="#111827" radius={[0, 4, 4, 0]} barSize={24} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-4 border-t border-gray-100 pt-4">
            <div>
              <p className="text-xs text-gray-500">Avg Time to Qualify</p>
              <p className="font-semibold text-gray-900">{metrics.avg_time_to_qualify_minutes}m</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Avg Time Qual → Call</p>
              <p className="font-semibold text-gray-900">{metrics.avg_time_qualifying_to_call_minutes}m</p>
            </div>
          </div>
        </div>
      </div>

      {/* Stage Breakdown Donut */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h3 className="text-lg font-bold text-gray-900 mb-6">Stage Breakdown</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={stageData}
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {stageData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={STAGE_COLORS[index % STAGE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap justify-center gap-4 mt-4">
            {stageData.map((d, i) => (
              <div key={d.name} className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: STAGE_COLORS[i % STAGE_COLORS.length] }} />
                <span className="text-xs text-gray-600 capitalize">{d.name} ({d.value})</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h3 className="text-lg font-bold text-gray-900 mb-6">Score Distribution</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={scoreData}
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {scoreData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[entry.name]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-6 mt-4">
            {scoreData.map(d => (
              <div key={d.name} className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[d.name] }} />
                <span className="text-xs text-gray-600">{d.name} ({d.value})</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
