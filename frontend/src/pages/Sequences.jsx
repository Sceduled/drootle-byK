import { useState, useEffect } from 'react';
import api from '../lib/api';
import { Lock, Power, ToggleRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const SEQUENCE_DESCRIPTIONS = {
  1: "Opening message sent within 60s of form fill",
  2: "Maya qualifies leads across 7 questions",
  3: "4 follow-ups over 5 days for silent leads",
  4: "Call reminders to lead and sales team",
  5: "7-day nurture sequence after a good call",
  6: "3-day urgency push for fence-sitters",
  7: "12-week slow-burn reactivation",
  8: "Onboarding, referral and review sequence",
  9: "Cross-sell sequence for existing clients"
};

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 15 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
};

export default function Sequences() {
  const [sequences, setSequences] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSequences();
  }, []);

  const fetchSequences = async () => {
    try {
      const res = await api.get('/dashboard/sequences');
      setSequences(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const toggleSequence = async (seqNumber, currentEnabled) => {
    if (seqNumber === 1 || seqNumber === 2) return;
    
    // Optimistic update
    setSequences(prev => prev.map(s => s.sequence_number === seqNumber ? { ...s, enabled: !currentEnabled } : s));
    
    try {
      await api.patch(`/dashboard/sequences/${seqNumber}`, { enabled: !currentEnabled });
    } catch (err) {
      alert("Failed to update sequence setting");
      await fetchSequences(); // Revert
    }
  };

  if (loading) return (
    <div className="flex h-full items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.5)]"></div>
    </div>
  );

  return (
    <motion.div 
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="p-8 max-w-4xl mx-auto"
    >
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-white/[0.03] border border-white/[0.05] rounded-xl flex items-center justify-center text-gray-200">
          <ToggleRight size={20} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Sequences</h1>
        </div>
      </div>
      
      <p className="text-gray-500 mb-10 max-w-2xl text-sm leading-relaxed">
        Manage the AI's autonomous sequences below. Toggling a sequence immediately updates the AI's behavior engine.
      </p>

      <div className="space-y-4">
        {sequences.map(seq => {
          const isLocked = seq.sequence_number === 1 || seq.sequence_number === 2;
          
          return (
            <motion.div 
              variants={itemVariants}
              key={seq.sequence_number} 
              className={`glass-card p-5 flex items-center justify-between transition-all duration-300 ${
                isLocked 
                  ? 'bg-white/[0.01] border-white/[0.02]' 
                  : seq.enabled 
                    ? 'border-white/[0.1]' 
                    : 'bg-white/[0.01] opacity-50 hover:opacity-100'
              }`}
            >
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <span className={`px-2 py-0.5 rounded text-[11px] font-semibold tracking-widest uppercase ${
                    seq.enabled && !isLocked ? 'bg-white/10 text-white' : 'bg-white/[0.02] text-gray-500'
                  }`}>
                    SEQ {seq.sequence_number}
                  </span>
                  <h3 className={`text-base font-semibold ${seq.enabled || isLocked ? 'text-white' : 'text-gray-400'}`}>
                    {seq.sequence_name}
                  </h3>
                  {isLocked && (
                    <div title="Required — cannot be disabled" className="flex items-center text-gray-600 ml-1">
                      <Lock size={14} />
                    </div>
                  )}
                </div>
                <p className="text-sm text-gray-500 mt-1">
                  {SEQUENCE_DESCRIPTIONS[seq.sequence_number] || "System sequence"}
                </p>
                {isLocked && (
                  <p className="text-[11px] text-gray-400 mt-2 font-semibold tracking-widest uppercase">REQUIRED SYSTEM LOOP</p>
                )}
              </div>
              
              <button
                onClick={() => toggleSequence(seq.sequence_number, seq.enabled)}
                disabled={isLocked}
                title={isLocked ? "Required — cannot be disabled" : ""}
                className={`relative flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-xs tracking-widest transition-all duration-300 ${
                  isLocked ? 'bg-transparent text-gray-600 cursor-not-allowed border border-white/[0.02]' :
                  seq.enabled 
                    ? 'bg-white text-black hover:bg-gray-200' 
                    : 'bg-transparent text-gray-400 border border-white/[0.1] hover:bg-white/[0.05]'
                }`}
              >
                <Power size={14} strokeWidth={seq.enabled && !isLocked ? 2.5 : 2} />
                {seq.enabled ? 'ACTIVE' : 'INACTIVE'}
              </button>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
