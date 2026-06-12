import { useState, useEffect } from 'react';
import api from '../lib/api';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Users, PhoneCall, Clock, CheckCircle } from 'lucide-react';

const COLORS = {
  HOT: '#ef4444',
  WARM: '#eab308',
  COLD: '#3b82f6'
};

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

  const industryData = Object.entries(metrics.by_industry).map(([name, value]) => ({
    name: name.replace('_', ' '),
    value
  }));

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Performance Metrics</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Total Leads</p>
              <h3 className="text-3xl font-bold text-gray-900 mt-1">{metrics.total_leads}</h3>
            </div>
            <div className="w-12 h-12 bg-gray-50 rounded-full flex items-center justify-center text-gray-900">
              <Users size={24} />
            </div>
          </div>
          <div className="mt-4 text-sm text-gray-600">
            <span className="font-medium text-green-600">+{metrics.leads_this_week}</span> this week
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Qualified Leads</p>
              <h3 className="text-3xl font-bold text-gray-900 mt-1">{metrics.qualified_count}</h3>
            </div>
            <div className="w-12 h-12 bg-green-50 rounded-full flex items-center justify-center text-green-600">
              <CheckCircle size={24} />
            </div>
          </div>
          <div className="mt-4 text-sm text-gray-600">
            {metrics.total_leads ? Math.round((metrics.qualified_count / metrics.total_leads) * 100) : 0}% qualification rate
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Call Booked Rate</p>
              <h3 className="text-3xl font-bold text-gray-900 mt-1">{metrics.call_booked_rate}%</h3>
            </div>
            <div className="w-12 h-12 bg-blue-50 rounded-full flex items-center justify-center text-blue-600">
              <PhoneCall size={24} />
            </div>
          </div>
          <div className="mt-4 text-sm text-gray-600">
            Users who scheduled a call
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Avg Qual Time</p>
              <h3 className="text-3xl font-bold text-gray-900 mt-1">{metrics.avg_qualification_minutes}m</h3>
            </div>
            <div className="w-12 h-12 bg-purple-50 rounded-full flex items-center justify-center text-purple-600">
              <Clock size={24} />
            </div>
          </div>
          <div className="mt-4 text-sm text-gray-600">
            Time to hit qualified status
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h3 className="text-lg font-bold text-gray-900 mb-6">Score Distribution</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={scoreData}
                  innerRadius={80}
                  outerRadius={110}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {scoreData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[entry.name]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-6 mt-4">
            {scoreData.map(d => (
              <div key={d.name} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[d.name] }} />
                <span className="text-sm text-gray-600">{d.name} ({d.value})</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h3 className="text-lg font-bold text-gray-900 mb-6">Leads by Industry</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={industryData} layout="vertical" margin={{ top: 0, right: 0, left: 40, bottom: 0 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} select={{ fill: '#4b5563' }} />
                <Tooltip cursor={{ fill: '#f9fafb' }} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                <Bar dataKey="value" fill="#111827" radius={[0, 4, 4, 0]} barSize={32} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
