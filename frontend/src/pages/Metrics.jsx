import { useState, useEffect } from 'react';
import api from '../lib/api';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { Users, PhoneCall, CheckCircle, XCircle, Trophy, Activity, RotateCcw, MessageSquare } from 'lucide-react';
import { motion } from 'framer-motion';

const COLORS = {
  HOT: '#ef4444',   // Neon red
  WARM: '#eab308',  // Neon yellow
  COLD: '#3b82f6'   // Neon blue
};

const STAGE_COLORS = ['#3b82f6', '#8b5cf6', '#f97316', '#06b6d4', '#14b8a6', '#eab308', '#64748b', '#22c55e', '#ef4444', '#f87171'];

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
};

export default function Metrics() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get('/dashboard/metrics')
      .then(res => {
        setMetrics(res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Metrics API Error:", err);
        setError(err.message || 'Failed to load metrics');
        setLoading(false);
      });
  }, []);

  if (loading) return (
    <div className="flex h-full items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.5)]"></div>
    </div>
  );
  if (error) return <div className="p-8 text-red-400 flex items-center gap-2"><XCircle /> {error}</div>;
  if (!metrics) return <div className="p-8 text-muted">No metrics data available.</div>;

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

  const sequencePerf = metrics.sequence_performance || {};
  const dnpData = [
    { name: 'Day 1', rate: sequencePerf['dnp_day_1']?.rate || 0, sent: sequencePerf['dnp_day_1']?.sent || 0, replied: sequencePerf['dnp_day_1']?.replied || 0 },
    { name: 'Day 2', rate: sequencePerf['dnp_day_2']?.rate || 0, sent: sequencePerf['dnp_day_2']?.sent || 0, replied: sequencePerf['dnp_day_2']?.replied || 0 },
    { name: 'Day 3', rate: sequencePerf['dnp_day_3']?.rate || 0, sent: sequencePerf['dnp_day_3']?.sent || 0, replied: sequencePerf['dnp_day_3']?.replied || 0 },
  ];
  
  const fomoData = [
    { name: 'Day 1', rate: sequencePerf['fomo_day_1']?.rate || 0, sent: sequencePerf['fomo_day_1']?.sent || 0, replied: sequencePerf['fomo_day_1']?.replied || 0 },
    { name: 'Day 2', rate: sequencePerf['fomo_day_2']?.rate || 0, sent: sequencePerf['fomo_day_2']?.sent || 0, replied: sequencePerf['fomo_day_2']?.replied || 0 },
    { name: 'Day 3', rate: sequencePerf['fomo_day_3']?.rate || 0, sent: sequencePerf['fomo_day_3']?.sent || 0, replied: sequencePerf['fomo_day_3']?.replied || 0 },
  ];

  const CustomSequenceTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-card border border-border p-3 rounded-lg shadow-xl">
          <p className="text-foreground font-medium mb-2">{label}</p>
          <p className="text-emerald-400 text-sm">Response Rate: {data.rate}%</p>
          <p className="text-muted text-xs mt-1">{data.replied} replies out of {data.sent} sent</p>
        </div>
      );
    }
    return null;
  };

  return (
    <motion.div 
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="p-8 max-w-7xl mx-auto space-y-8"
    >
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-foreground tracking-tight">Lifecycle Metrics</h1>
          <p className="text-muted mt-1">Real-time performance of your AI agents and sales funnel</p>
        </div>
      </div>

      {/* Primary KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <motion.div variants={itemVariants} className="glass-card p-6 relative overflow-hidden group">
          <div className="flex items-center justify-between relative z-10">
            <div>
              <p className="text-xs font-semibold text-muted uppercase tracking-widest">Total Leads</p>
              <h3 className="text-4xl font-bold text-foreground mt-2 tracking-tight">{metrics.total_leads}</h3>
            </div>
            <div className="w-12 h-12 bg-card-hover border border-border rounded-xl flex items-center justify-center text-muted group-hover:text-foreground transition-colors">
              <Users size={24} strokeWidth={1.5} />
            </div>
          </div>
          <div className="mt-6 text-sm text-muted relative z-10 flex items-center gap-2">
            <span className="font-medium text-emerald-400">+{metrics.leads_today}</span> today
          </div>
        </motion.div>

        <motion.div variants={itemVariants} className="glass-card p-6 relative overflow-hidden group">
          <div className="flex items-center justify-between relative z-10">
            <div>
              <p className="text-xs font-semibold text-muted uppercase tracking-widest">Awaiting Call</p>
              <h3 className="text-4xl font-bold text-foreground mt-2 tracking-tight">{metrics.leads_by_stage?.awaiting_call || 0}</h3>
            </div>
            <div className="w-12 h-12 bg-card-hover border border-border rounded-xl flex items-center justify-center text-muted group-hover:text-foreground transition-colors">
              <PhoneCall size={24} strokeWidth={1.5} />
            </div>
          </div>
          <div className="mt-6 text-sm text-muted relative z-10">
            <span className="text-foreground-muted font-medium">{metrics.conversion_qualifying_to_call}%</span> conv. from qualified
          </div>
        </motion.div>

        <motion.div variants={itemVariants} className="glass-card p-6 relative overflow-hidden group">
          <div className="flex items-center justify-between relative z-10">
            <div>
              <p className="text-xs font-semibold text-muted uppercase tracking-widest">Deals Closed</p>
              <h3 className="text-4xl font-bold text-foreground mt-2 tracking-tight">{metrics.leads_by_stage?.closed || 0}</h3>
            </div>
            <div className="w-12 h-12 bg-card-hover border border-border rounded-xl flex items-center justify-center text-muted group-hover:text-foreground transition-colors">
              <Trophy size={24} strokeWidth={1.5} />
            </div>
          </div>
          <div className="mt-6 text-sm text-muted relative z-10">
            <span className="text-emerald-400 font-medium">{metrics.conversion_call_to_closed}%</span> close rate from calls
          </div>
        </motion.div>

        <motion.div variants={itemVariants} className="glass-card p-6 relative overflow-hidden group">
          <div className="flex items-center justify-between relative z-10">
            <div>
              <p className="text-xs font-semibold text-muted uppercase tracking-widest">Lost / Opt-Out</p>
              <h3 className="text-4xl font-bold text-foreground mt-2 tracking-tight">{metrics.leads_by_stage?.lost || 0}</h3>
            </div>
            <div className="w-12 h-12 bg-card-hover border border-border rounded-xl flex items-center justify-center text-muted group-hover:text-foreground transition-colors">
              <XCircle size={24} strokeWidth={1.5} />
            </div>
          </div>
          <div className="mt-6 text-sm text-muted relative z-10">
            <span className="text-red-400 font-medium">{metrics.opt_out_rate}%</span> opt-out rate
          </div>
        </motion.div>
      </div>

      {/* Recovery & Time Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Recovery Rates */}
        <motion.div variants={itemVariants} className="glass-card p-8">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 bg-card-hover rounded-xl border border-border flex items-center justify-center">
              <RotateCcw className="text-foreground-muted" size={18} />
            </div>
            <h3 className="text-lg font-semibold text-foreground tracking-wide">AI Sequence Recovery Rates</h3>
          </div>
          <div className="space-y-8">
            <div>
              <div className="flex justify-between mb-3">
                <span className="text-sm font-medium text-muted">Sequence 3: DNP Recovery</span>
                <span className="text-sm font-semibold text-foreground-muted">{metrics.sequence_recovery_rate?.dnp}%</span>
              </div>
              <div className="w-full bg-white/[0.05] rounded-full h-1.5 overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${metrics.sequence_recovery_rate?.dnp}%` }}
                  transition={{ duration: 1, ease: "easeOut" }}
                  className="bg-white h-full rounded-full"
                />
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-3">
                <span className="text-sm font-medium text-muted">Sequence 6: FOMO Revival</span>
                <span className="text-sm font-semibold text-foreground-muted">{metrics.sequence_recovery_rate?.fomo}%</span>
              </div>
              <div className="w-full bg-white/[0.05] rounded-full h-1.5 overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${metrics.sequence_recovery_rate?.fomo}%` }}
                  transition={{ duration: 1, delay: 0.2, ease: "easeOut" }}
                  className="bg-white h-full rounded-full"
                />
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-3">
                <span className="text-sm font-medium text-muted">Sequence 7: Cold Reactivation</span>
                <span className="text-sm font-semibold text-foreground-muted">{metrics.sequence_recovery_rate?.cold}%</span>
              </div>
              <div className="w-full bg-white/[0.05] rounded-full h-1.5 overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${metrics.sequence_recovery_rate?.cold}%` }}
                  transition={{ duration: 1, delay: 0.4, ease: "easeOut" }}
                  className="bg-white h-full rounded-full"
                />
              </div>
            </div>
          </div>
        </motion.div>

        {/* Funnel Chart */}
        <motion.div variants={itemVariants} className="glass-card p-8 flex flex-col">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 bg-card-hover rounded-xl border border-border flex items-center justify-center">
              <Activity className="text-foreground-muted" size={18} />
            </div>
            <h3 className="text-lg font-semibold text-foreground tracking-wide">Sales Funnel</h3>
          </div>
          <div className="h-56 w-full relative">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={funnelData} layout="vertical" margin={{ top: 0, right: 30, left: 30, bottom: 0 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fill: '#71717a', fontSize: 13 }} />
                <Tooltip 
                  cursor={{ fill: 'rgba(255,255,255,0.02)' }} 
                  contentStyle={{ backgroundColor: '#0f0f13', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }} 
                />
                <Bar dataKey="value" fill="#ffffff" radius={[0, 4, 4, 0]} barSize={20} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-auto grid grid-cols-2 gap-4 border-t border-border pt-6">
            <div className="bg-card-hover p-4 rounded-xl border border-border">
              <p className="text-xs text-muted uppercase tracking-widest mb-1">Avg Time to Qualify</p>
              <p className="text-2xl font-bold text-foreground tracking-tight">{metrics.avg_time_to_qualify_minutes}m</p>
            </div>
            <div className="bg-card-hover p-4 rounded-xl border border-border">
              <p className="text-xs text-muted uppercase tracking-widest mb-1">Avg Time Qual → Call</p>
              <p className="text-2xl font-bold text-foreground tracking-tight">{metrics.avg_time_qualifying_to_call_minutes}m</p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Sequence Performance Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <motion.div variants={itemVariants} className="glass-card p-8">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 bg-blue-500/10 rounded-xl border border-blue-500/20 flex items-center justify-center">
              <MessageSquare className="text-blue-400" size={18} />
            </div>
            <h3 className="text-lg font-semibold text-foreground tracking-wide">DNP Sequence Response Rates</h3>
          </div>
          <div className="h-64 w-full relative">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dnpData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#71717a', fontSize: 12 }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#71717a', fontSize: 12 }} tickFormatter={(val) => `${val}%`} />
                <Tooltip content={<CustomSequenceTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                <Bar dataKey="rate" fill="#3b82f6" radius={[4, 4, 0, 0]} maxBarSize={60} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div variants={itemVariants} className="glass-card p-8">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 bg-amber-500/10 rounded-xl border border-amber-500/20 flex items-center justify-center">
              <MessageSquare className="text-amber-400" size={18} />
            </div>
            <h3 className="text-lg font-semibold text-foreground tracking-wide">FOMO Sequence Response Rates</h3>
          </div>
          <div className="h-64 w-full relative">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={fomoData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#71717a', fontSize: 12 }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#71717a', fontSize: 12 }} tickFormatter={(val) => `${val}%`} />
                <Tooltip content={<CustomSequenceTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                <Bar dataKey="rate" fill="#f59e0b" radius={[4, 4, 0, 0]} maxBarSize={60} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>

      {/* Stage Breakdown Donut */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <motion.div variants={itemVariants} className="glass-card p-8">
          <h3 className="text-lg font-semibold text-foreground tracking-wide mb-8 text-center">Stage Breakdown</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={stageData}
                  innerRadius={80}
                  outerRadius={110}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="none"
                >
                  {stageData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={STAGE_COLORS[index % STAGE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#0f0f13', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '8px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap justify-center gap-3 mt-6">
            {stageData.map((d, i) => (
              <div key={d.name} className="flex items-center gap-2 bg-card-hover px-3 py-1.5 rounded border border-border">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: STAGE_COLORS[i % STAGE_COLORS.length] }} />
                <span className="text-xs text-muted capitalize">{d.name} <span className="font-semibold text-foreground-muted ml-1">{d.value}</span></span>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div variants={itemVariants} className="glass-card p-8">
          <h3 className="text-lg font-semibold text-foreground tracking-wide mb-8 text-center">Score Distribution</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={scoreData}
                  innerRadius={80}
                  outerRadius={110}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="none"
                >
                  {scoreData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[entry.name]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#0f0f13', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '8px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-4 mt-6">
            {scoreData.map(d => (
              <div key={d.name} className="flex items-center gap-2 bg-card-hover px-3 py-1.5 rounded border border-border">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[d.name] }} />
                <span className="text-xs text-muted">{d.name} <span className="font-semibold text-foreground-muted ml-1">{d.value}</span></span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}
