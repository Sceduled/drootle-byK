import { useState, useEffect, useRef } from 'react';
import { startSimulation, getSimulationHistory, sendSimulationMessage, exportSimulations } from '../lib/api';
import { Send, User, Bot, RefreshCw, Loader2, Download } from 'lucide-react';

export default function Simulator() {
  const [sessionId, setSessionId] = useState(localStorage.getItem('sim_session_id'));
  const [name, setName] = useState('');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [leadScore, setLeadScore] = useState('');
  const [aiSummary, setAiSummary] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (sessionId) {
      loadHistory();
    }
  }, [sessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadHistory = async () => {
    try {
      const res = await getSimulationHistory(sessionId);
      setMessages(res.data);
    } catch (err) {
      console.error("Failed to load history", err);
      // If session not found or invalid, clear it
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
    } catch (err) {
      console.error("Failed to start simulation", err);
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
    } catch (err) {
      console.error("Failed to send message", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRestart = () => {
    setSessionId(null);
    setMessages([]);
    setName('');
    setLeadScore('');
    setAiSummary('');
    localStorage.removeItem('sim_session_id');
  };

  const handleExport = async () => {
    try {
      const res = await exportSimulations();
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'simulation_chats.csv');
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      console.error("Failed to export simulations", err);
    }
  };

  if (!sessionId) {
    return (
      <div className="max-w-md mx-auto mt-20 p-6 bg-card rounded-xl border border-border shadow-2xl">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-foreground mb-2">AI Chat Simulator</h1>
          <p className="text-muted text-sm">Test your prompts without affecting real leads</p>
        </div>
        <form onSubmit={handleStart} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-muted mb-1">Your (Fake Lead) Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-input border border-border rounded-lg px-4 py-3 text-foreground focus:outline-none focus:border-emerald-500 transition-colors"
              placeholder="e.g. John Doe"
              required
            />
          </div>
          <button
            type="submit"
            disabled={starting}
            className="w-full bg-emerald-600 hover:bg-emerald-700 text-foreground font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {starting ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Start Simulation'}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-border">
          <button
            onClick={handleExport}
            className="w-full bg-card-hover hover:bg-border text-foreground-muted font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 text-sm"
          >
            <Download className="w-4 h-4" />
            Download All Chats (CSV)
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col max-w-4xl mx-auto py-6">
      <div className="flex items-center justify-between mb-4 px-4">
        <div>
          <h1 className="text-xl font-bold text-foreground">Simulation Session</h1>
          <p className="text-sm text-muted">Testing as: {name || 'Unknown'}</p>
        </div>
        <button
          onClick={handleRestart}
          className="flex items-center gap-2 px-4 py-2 bg-card-hover hover:bg-red-500/10 text-foreground-muted hover:text-red-500 rounded-lg transition-colors text-sm font-medium"
        >
          <RefreshCw className="w-4 h-4" />
          End Session
        </button>
      </div>

      <div className="flex-1 flex gap-6 overflow-hidden">
        {/* Chat window */}
        <div className="flex-[2] bg-card border border-border rounded-xl overflow-hidden flex flex-col shadow-2xl">
          <div className="flex-1 p-4 overflow-y-auto space-y-6">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`flex gap-3 max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-emerald-600/20 text-emerald-500' : 'bg-blue-600/20 text-blue-500'}`}>
                    {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>
                  <div className={`px-4 py-3 rounded-2xl ${msg.role === 'user' ? 'bg-emerald-600 text-white rounded-tr-sm' : 'bg-card-hover text-foreground rounded-tl-sm'}`}>
                    <p className="whitespace-pre-wrap leading-relaxed text-sm">{msg.content}</p>
                  </div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="flex gap-3 max-w-[80%] flex-row">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 bg-blue-600/20 text-blue-500">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="px-5 py-4 rounded-2xl bg-card-hover text-muted rounded-tl-sm flex items-center gap-2">
                    <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div className="p-4 bg-input border-t border-border">
            <form onSubmit={handleSend} className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message..."
                disabled={loading}
                className="flex-1 bg-background border border-border rounded-xl px-4 py-3 text-foreground focus:outline-none focus:border-emerald-500 disabled:opacity-50 transition-colors"
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-foreground p-3 rounded-xl transition-colors flex items-center justify-center shrink-0"
              >
                <Send className="w-5 h-5" />
              </button>
            </form>
          </div>
        </div>
        
        {/* Analytics Panel */}
        <div className="flex-1 bg-card border border-border rounded-xl p-5 shadow-2xl flex flex-col gap-6 overflow-y-auto">
          <div>
            <h3 className="text-sm font-semibold text-muted uppercase tracking-wider mb-3">Live Lead Score</h3>
            {leadScore ? (
              <div className={`px-4 py-3 rounded-xl border ${
                leadScore.toLowerCase() === 'hot' ? 'bg-orange-500/10 border-orange-500/20 text-orange-400' :
                leadScore.toLowerCase() === 'warm' ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400' :
                'bg-blue-500/10 border-blue-500/20 text-blue-400'
              }`}>
                <span className="font-bold uppercase tracking-wide">{leadScore}</span>
              </div>
            ) : (
              <div className="px-4 py-3 rounded-xl border border-border bg-input text-muted text-sm italic">
                Pending analysis...
              </div>
            )}
          </div>
          
          <div>
            <h3 className="text-sm font-semibold text-muted uppercase tracking-wider mb-3">Live AI Summary</h3>
            {aiSummary ? (
              <div className="px-4 py-4 rounded-xl border border-border bg-input text-foreground-muted text-sm leading-relaxed whitespace-pre-wrap">
                {aiSummary}
              </div>
            ) : (
              <div className="px-4 py-3 rounded-xl border border-border bg-input text-muted text-sm italic">
                Gathering context...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
