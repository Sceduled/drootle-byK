import { useState, useEffect, useRef } from 'react';
import { startSimulation, getSimulationHistory, sendSimulationMessage, exportSimulations } from '../lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send, User, Bot, RefreshCw, Loader2, Download,
  Phone, PhoneOff, Mic, MessageSquare, Waves,
  PhoneCall, PhoneIncoming, CheckCircle2, XCircle, Activity
} from 'lucide-react';

// ─── Animation variants (same as Metrics.jsx) ──────────────────────────────

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
};

// ─── Voice Simulator ─────────────────────────────────────────────────────────

function VoiceSimulator() {
  return (
    <div className="glass-card p-12 flex flex-col items-center justify-center gap-4 text-center min-h-[400px]">
      <div className="w-16 h-16 bg-card-hover border border-border rounded-2xl flex items-center justify-center text-muted mb-2">
        <PhoneCall size={28} strokeWidth={1.5} />
      </div>
      <h2 className="text-xl font-bold text-foreground tracking-tight">Voice Simulator Under Testing</h2>
      <p className="text-muted text-sm max-w-md">
        The web-based voice simulator is currently undergoing testing. Please use backend APIs (<code className="px-1.5 py-0.5 bg-card border border-border rounded text-emerald-400">POST /api/tasks/call</code>) to dispatch outbound test calls directly to the voice engine.
      </p>
    </div>
  );
}

// ─── Chat Simulator ───────────────────────────────────────────────────────────

function ChatSimulator() {
  const [sessionId, setSessionId] = useState(localStorage.getItem('sim_session_id'));
  const [name, setName] = useState('');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [leadScore, setLeadScore] = useState('');
  const [aiSummary, setAiSummary] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => { if (sessionId) loadHistory(); }, [sessionId]);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const loadHistory = async () => {
    try {
      const res = await getSimulationHistory(sessionId);
      setMessages(res.data);
    } catch {
      setSessionId(null);
      localStorage.removeItem('sim_session_id');
    }
  };

  const handleStart = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setStarting(true);
    try {
      const res = await startSimulation(name);
      setSessionId(res.data.session_id);
      localStorage.setItem('sim_session_id', res.data.session_id);
      setMessages([{ role: 'assistant', content: res.data.message }]);
      if (res.data.lead_score) setLeadScore(res.data.lead_score);
      if (res.data.ai_summary) setAiSummary(res.data.ai_summary);
    } finally {
      setStarting(false);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);
    try {
      const res = await sendSimulationMessage(sessionId, userMsg);
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.reply }]);
      if (res.data.lead_score) setLeadScore(res.data.lead_score);
      if (res.data.ai_summary) setAiSummary(res.data.ai_summary);
    } finally {
      setLoading(false);
    }
  };

  const handleRestart = () => {
    setSessionId(null); setMessages([]); setName('');
    setLeadScore(''); setAiSummary('');
    localStorage.removeItem('sim_session_id');
  };

  const handleExport = async () => {
    try {
      const res = await exportSimulations();
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url; a.setAttribute('download', 'simulation_chats.csv');
      document.body.appendChild(a); a.click(); a.remove();
    } catch (err) { console.error(err); }
  };

  const scoreStyle = {
    hot:  'bg-red-500/10 border-red-500/20 text-red-500',
    warm: 'bg-amber-500/10 border-amber-500/20 text-amber-500',
    cold: 'bg-blue-500/10 border-blue-500/20 text-blue-500',
  };

  return (
    <div className="glass-card p-8 flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-card-hover border border-border rounded-xl flex items-center justify-center text-muted">
            <MessageSquare size={22} strokeWidth={1.5} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-foreground tracking-tight">Chat Agent Simulator</h2>
            <p className="text-sm text-muted mt-0.5">Test WhatsApp flow without affecting real leads</p>
          </div>
        </div>
        {sessionId && (
          <button onClick={handleRestart}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-muted hover:text-red-500 bg-card-hover hover:bg-red-500/10 border border-border hover:border-red-500/20 rounded-xl transition-all">
            <RefreshCw size={14} /> End Session
          </button>
        )}
      </div>

      {/* Setup form */}
      {!sessionId ? (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
          <form onSubmit={handleStart} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-muted uppercase tracking-widest mb-2">Your (Fake Lead) Name</label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="e.g. John Doe"
                className="w-full bg-input border border-border rounded-xl px-4 py-3 text-foreground text-sm focus:outline-none focus:border-emerald-400 transition-colors"
                required
              />
            </div>
            <button type="submit" disabled={starting}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold text-foreground bg-foreground/5 hover:bg-foreground/10 border border-border hover:border-foreground/20 transition-all group">
              {starting ? <Loader2 size={16} className="animate-spin" /> : <><MessageSquare size={15} className="group-hover:scale-110 transition-transform" /> Start Chat Session</>}
            </button>
          </form>
          <div className="pt-4 border-t border-border">
            <button onClick={handleExport}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium text-muted hover:text-foreground bg-card-hover hover:bg-foreground/5 border border-border transition-all">
              <Download size={14} /> Download All Chats (CSV)
            </button>
          </div>
        </motion.div>
      ) : (
        <div className="flex flex-col gap-4 flex-1 min-h-0">
          <p className="text-sm text-muted">Testing as: <span className="font-semibold text-foreground-muted">{name || 'Unknown'}</span></p>

          <div className="flex gap-4 flex-1 min-h-0">
            {/* Chat window */}
            <div className="flex-[2] bg-card-hover border border-border rounded-xl flex flex-col overflow-hidden">
              <div className="flex-1 p-4 overflow-y-auto space-y-4 min-h-0 max-h-80">
                {messages.map((msg, idx) => (
                  <motion.div key={idx} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`flex gap-2.5 max-w-[82%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 border ${
                        msg.role === 'user' ? 'bg-foreground/5 border-border text-foreground-muted' : 'bg-blue-500/10 border-blue-500/20 text-blue-500'
                      }`}>
                        {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
                      </div>
                      <div className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed border ${
                        msg.role === 'user'
                          ? 'bg-foreground text-background rounded-tr-sm border-transparent'
                          : 'bg-card border-border text-foreground rounded-tl-sm'
                      }`}>
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                      </div>
                    </div>
                  </motion.div>
                ))}
                {loading && (
                  <div className="flex justify-start">
                    <div className="flex gap-2.5">
                      <div className="w-8 h-8 rounded-full flex items-center justify-center border bg-blue-500/10 border-blue-500/20 text-blue-500"><Bot size={14} /></div>
                      <div className="px-5 py-4 rounded-2xl bg-card border border-border rounded-tl-sm flex items-center gap-1.5">
                        {[0, 150, 300].map(d => <span key={d} className="w-1.5 h-1.5 bg-muted rounded-full animate-bounce" style={{ animationDelay: `${d}ms` }} />)}
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
              <div className="p-3 border-t border-border bg-card">
                <form onSubmit={handleSend} className="flex gap-2">
                  <input
                    type="text" value={input} onChange={e => setInput(e.target.value)}
                    placeholder="Type your message…" disabled={loading}
                    className="flex-1 bg-input border border-border rounded-xl px-4 py-2.5 text-foreground text-sm focus:outline-none focus:border-foreground/30 disabled:opacity-50 transition-colors"
                  />
                  <button type="submit" disabled={!input.trim() || loading}
                    className="bg-foreground hover:bg-foreground/90 disabled:opacity-30 disabled:cursor-not-allowed text-background p-2.5 rounded-xl transition-colors flex items-center justify-center">
                    <Send size={15} />
                  </button>
                </form>
              </div>
            </div>

            {/* Analytics panel */}
            <div className="flex-1 flex flex-col gap-4 overflow-y-auto">
              <div className="glass-card p-4">
                <p className="text-xs font-semibold text-muted uppercase tracking-widest mb-3">Live Lead Score</p>
                {leadScore ? (
                  <div className={`px-4 py-3 rounded-xl border ${scoreStyle[leadScore.toLowerCase()] || 'bg-card-hover border-border text-muted'}`}>
                    <span className="font-bold uppercase tracking-wide text-sm">{leadScore}</span>
                  </div>
                ) : (
                  <div className="px-4 py-3 rounded-xl border border-border bg-card-hover text-muted text-xs italic">Pending analysis…</div>
                )}
              </div>
              <div className="glass-card p-4 flex-1">
                <p className="text-xs font-semibold text-muted uppercase tracking-widest mb-3">AI Summary</p>
                {aiSummary ? (
                  <p className="text-foreground-muted text-sm leading-relaxed whitespace-pre-wrap">{aiSummary}</p>
                ) : (
                  <p className="text-muted text-xs italic">Gathering context…</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Stat cards (same pattern as Metrics.jsx) ─────────────────────────────────

const STAT_CARDS = [
  { label: 'Voice Tests Run', value: '—', sub: 'this session', Icon: PhoneCall },
  { label: 'Chat Sessions',   value: '—', sub: 'all time',     Icon: MessageSquare },
  { label: 'Avg Call Duration', value: '—', sub: 'simulated',  Icon: Activity },
  { label: 'Scenarios Tested', value: '3', sub: 'available',   Icon: CheckCircle2 },
];

// ─── Main Page ────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'voice', label: 'Voice Agent', Icon: Phone },
  { id: 'chat',  label: 'Chat Agent',  Icon: MessageSquare },
];

export default function Simulator() {
  const [activeTab, setActiveTab] = useState('voice');

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="p-8 max-w-7xl mx-auto space-y-8"
    >
      {/* Page header — same as Metrics */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground tracking-tight">Agent Simulator</h1>
          <p className="text-muted mt-1">Test voice and chat agents without touching real lead data</p>
        </div>

        {/* Tab switcher — matches pipeline tabs in Leads.jsx */}
        <div className="flex items-center gap-1 bg-card-hover border border-border rounded-xl p-1">
          {TABS.map(({ id, label, Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === id
                  ? 'bg-card border border-border text-foreground shadow-sm'
                  : 'text-muted hover:text-foreground-muted'
              }`}
            >
              <Icon size={14} strokeWidth={2} />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* KPI stat row — same layout as Metrics.jsx KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
        {STAT_CARDS.map(({ label, value, sub, Icon }, i) => (
          <motion.div key={i} variants={itemVariants} className="glass-card p-6 relative overflow-hidden group">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-muted uppercase tracking-widest">{label}</p>
                <h3 className="text-4xl font-bold text-foreground mt-2 tracking-tight">{value}</h3>
              </div>
              <div className="w-12 h-12 bg-card-hover border border-border rounded-xl flex items-center justify-center text-muted group-hover:text-foreground transition-colors">
                <Icon size={22} strokeWidth={1.5} />
              </div>
            </div>
            <p className="mt-4 text-sm text-muted">{sub}</p>
          </motion.div>
        ))}
      </div>

      {/* Info banner */}
      <motion.div variants={itemVariants}
        className="flex items-center gap-3 px-5 py-3 bg-card-hover border border-border rounded-xl text-sm text-muted">
        {activeTab === 'voice'
          ? <><PhoneIncoming size={14} className="text-foreground-muted shrink-0" /> Simulates outbound AI calls directly via the telephony backend integration</>
          : <><MessageSquare size={14} className="text-foreground-muted shrink-0" /> Simulates the WhatsApp qualification flow using the live Maya prompt and real backend</>
        }
      </motion.div>

      {/* Simulator panel */}
      <motion.div variants={itemVariants}>
        <AnimatePresence mode="wait">
          {activeTab === 'voice'
            ? <motion.div key="voice" initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 10 }}><VoiceSimulator /></motion.div>
            : <motion.div key="chat"  initial={{ opacity: 0, x: 10  }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }}><ChatSimulator /></motion.div>
          }
        </AnimatePresence>
      </motion.div>

      {/* Wave keyframe */}
      <style>{`
        @keyframes wave {
          0%, 100% { transform: scaleY(0.4); opacity: 0.4; }
          50%       { transform: scaleY(1.4); opacity: 1; }
        }
      `}</style>
    </motion.div>
  );
}
