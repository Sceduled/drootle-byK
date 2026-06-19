import { useState, useEffect, useCallback } from 'react';
import api from '../lib/api';
import { Lock, Power, ToggleRight, ChevronDown, ChevronUp, Save, Clock, CheckCircle2, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const SEQUENCE_DESCRIPTIONS = {
  1: "Opening message sent within 60s of form fill",
  2: "Qualification nudge 24h after opening if no reply",
  3: "4 follow-ups over 5 days for silent leads",
  4: "Call reminders to lead and sales team",
  5: "7-day nurture sequence after a good call",
  6: "3-day urgency push for fence-sitters",
  7: "12-week slow-burn reactivation",
  8: "Onboarding, referral and review sequence",
  9: "Cross-sell sequence for existing clients"
};

// Human-readable labels for each message_key
const MESSAGE_LABELS = {
  dnp_message_1: "Message 1 — Initial check-in",
  dnp_message_2: "Message 2 — Project highlight",
  dnp_message_3: "Message 3 — No pressure nudge",
  dnp_message_4: "Message 4 — Final follow-up",
  check_dnp_exhausted: "Gate — Mark cold after last message",
  post_call_message_2: "Message 2 — Social proof story",
  post_call_message_3: "Message 3 — Buyer testimonial",
  post_call_message_4: "Message 4 — Address concern",
  post_call_message_5: "Message 5 — Site visit push",
  check_post_call_complete: "Gate — Transition to FOMO",
  fomo_message_2: "Message 2 — Inventory movement",
  fomo_message_3: "Message 3 — Final FOMO close",
  check_fomo_complete: "Gate — Transition to cold",
  reactivation_from_cold: "Delay before first reactivation message",
  reactivation_2: "Message 2 — Metro connectivity",
  reactivation_3: "Message 3 — Still looking?",
  reactivation_4: "Message 4 — Virtual walkthrough",
  reactivation_5: "Message 5 — Closing enquiry",
  check_reactivation_complete: "Gate — Archive after 12 weeks",
  closed_message_1: "Message 1 — Welcome",
  closed_message_2: "Message 2 — Onboarding check-in",
  closed_message_3: "Message 3 — Referral ask",
  closed_message_4: "Message 4 — Review request",
  upsell_message_2: "Message 2 — Investment example",
  upsell_message_3: "Message 3 — Advisory call offer",
};

// Which sequences have configurable timing
const TIMING_SEQUENCES = [3, 5, 6, 7, 8, 9];

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } }
};

const itemVariants = {
  hidden: { opacity: 0, y: 15 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
};

export default function Sequences() {
  const [sequences, setSequences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedSeq, setExpandedSeq] = useState(null);
  const [timingData, setTimingData] = useState({});
  const [timingEdits, setTimingEdits] = useState({});
  const [saving, setSaving] = useState({});
  const [toast, setToast] = useState({ message: '', type: 'success', visible: false });

  const showToast = (message, type = 'success') => {
    setToast({ message, type, visible: true });
    setTimeout(() => {
      setToast(prev => ({ ...prev, visible: false }));
    }, 3000);
  };

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

  const fetchTiming = useCallback(async (seqNumber) => {
    if (timingData[seqNumber]) return;
    try {
      const res = await api.get(`/dashboard/sequences/${seqNumber}/timing`);
      const data = res.data;
      setTimingData(prev => ({ ...prev, [seqNumber]: data }));
      // Initialize edits with current values
      const edits = {};
      data.forEach(row => {
        edits[row.message_key] = { delay_value: row.delay_value, delay_unit: row.delay_unit };
      });
      setTimingEdits(prev => ({ ...prev, [seqNumber]: edits }));
    } catch (err) {
      console.error('Failed to load timing for seq', seqNumber, err);
    }
  }, [timingData]);

  const toggleSequence = async (seqNumber, currentEnabled) => {
    if (seqNumber === 1 || seqNumber === 2) return;
    setSequences(prev => prev.map(s => s.sequence_number === seqNumber ? { ...s, enabled: !currentEnabled } : s));
    try {
      await api.patch(`/dashboard/sequences/${seqNumber}`, { enabled: !currentEnabled });
    } catch (err) {
      showToast("Failed to update sequence setting", "error");
      await fetchSequences();
    }
  };

  const handleTimingChange = (seqNumber, key, field, value) => {
    setTimingEdits(prev => ({
      ...prev,
      [seqNumber]: {
        ...prev[seqNumber],
        [key]: { ...prev[seqNumber]?.[key], [field]: field === 'delay_value' ? parseInt(value) || 1 : value }
      }
    }));
  };

  const saveTiming = async (seqNumber) => {
    const edits = timingEdits[seqNumber];
    if (!edits) return;
    setSaving(prev => ({ ...prev, [seqNumber]: true }));
    try {
      const payload = Object.entries(edits).map(([key, val]) => ({
        message_key: key,
        delay_value: val.delay_value,
        delay_unit: val.delay_unit
      }));
      await api.patch(`/dashboard/sequences/${seqNumber}/timing`, payload);
      // Invalidate cached timing so next expand re-fetches
      setTimingData(prev => { const n = { ...prev }; delete n[seqNumber]; return n; });
      showToast(`Timing saved for Sequence ${seqNumber}.`, "success");
    } catch (err) {
      showToast("Failed to save timing.", "error");
    } finally {
      setSaving(prev => ({ ...prev, [seqNumber]: false }));
    }
  };

  const handleExpand = (seqNumber) => {
    if (expandedSeq === seqNumber) {
      setExpandedSeq(null);
    } else {
      setExpandedSeq(seqNumber);
      if (TIMING_SEQUENCES.includes(seqNumber)) {
        fetchTiming(seqNumber);
      }
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
      className="p-8 max-w-4xl mx-auto relative"
    >
      {/* Toast Notification */}
      <AnimatePresence>
        {toast.visible && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            className={`fixed bottom-8 right-8 flex items-center gap-3 px-4 py-3 rounded-lg shadow-2xl border z-50 ${
              toast.type === 'success' 
                ? 'bg-[#111] border-[#333] text-green-400' 
                : 'bg-[#111] border-[#333] text-red-400'
            }`}
          >
            {toast.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
            <span className="text-sm font-medium text-gray-100">{toast.message}</span>
          </motion.div>
        )}
      </AnimatePresence>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-card-hover border border-border rounded-xl flex items-center justify-center text-foreground-muted">
          <ToggleRight size={20} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Sequences</h1>
        </div>
      </div>

      <p className="text-muted mb-2 max-w-2xl text-sm leading-relaxed">
        Manage the AI's autonomous sequences below. Toggling a sequence immediately updates the AI's behavior engine.
      </p>
      <p className="text-muted mb-10 max-w-2xl text-xs leading-relaxed opacity-60">
        ⚠ Timing changes apply to new sequence triggers only — leads already mid-sequence are unaffected.
      </p>

      <div className="space-y-4">
        {sequences.map(seq => {
          const isLocked = seq.sequence_number === 1 || seq.sequence_number === 2;
          const hasTiming = TIMING_SEQUENCES.includes(seq.sequence_number);
          const isExpanded = expandedSeq === seq.sequence_number;
          const seqTiming = timingData[seq.sequence_number] || [];
          const edits = timingEdits[seq.sequence_number] || {};

          return (
            <motion.div
              variants={itemVariants}
              key={seq.sequence_number}
              className={`glass-card flex flex-col transition-all duration-300 ${
                isLocked
                  ? 'bg-white/[0.01] border-white/[0.02]'
                  : seq.enabled
                    ? 'border-border'
                    : 'bg-white/[0.01] opacity-50 hover:opacity-100'
              }`}
            >
              {/* Header row */}
              <div
                className={`p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 sm:gap-0 ${(seq.templates?.length > 0 || hasTiming) ? 'cursor-pointer hover:bg-card-hover transition-colors rounded-t-xl' : ''}`}
                onClick={() => handleExpand(seq.sequence_number)}
              >
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-semibold tracking-widest uppercase ${
                      seq.enabled && !isLocked ? 'bg-white/10 text-foreground' : 'bg-card-hover text-muted'
                    }`}>
                      SEQ {seq.sequence_number}
                    </span>
                    <h3 className={`text-base font-semibold ${seq.enabled || isLocked ? 'text-foreground' : 'text-muted'}`}>
                      {seq.sequence_name}
                    </h3>
                    {isLocked && (
                      <div title="Required — cannot be disabled" className="flex items-center text-gray-600 ml-1">
                        <Lock size={14} />
                      </div>
                    )}
                    {hasTiming && (
                      <div title="Timing configurable" className="flex items-center text-cyan-600 ml-1">
                        <Clock size={13} />
                      </div>
                    )}
                  </div>
                  <p className="text-sm text-muted mt-1">
                    {SEQUENCE_DESCRIPTIONS[seq.sequence_number] || "System sequence"}
                  </p>
                  {isLocked && (
                    <p className="text-[11px] text-muted mt-2 font-semibold tracking-widest uppercase">REQUIRED SYSTEM LOOP</p>
                  )}
                </div>

                <div className="flex items-center gap-4">
                  <button
                    onClick={(e) => { e.stopPropagation(); toggleSequence(seq.sequence_number, seq.enabled); }}
                    disabled={isLocked}
                    title={isLocked ? "Required — cannot be disabled" : ""}
                    className={`relative flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-xs tracking-widest transition-all duration-300 ${
                      isLocked ? 'bg-transparent text-gray-600 cursor-not-allowed border border-white/[0.02]' :
                      seq.enabled
                        ? 'bg-white text-black hover:bg-gray-200'
                        : 'bg-transparent text-muted border border-border hover:bg-white/[0.05]'
                    }`}
                  >
                    <Power size={14} strokeWidth={seq.enabled && !isLocked ? 2.5 : 2} />
                    {seq.enabled ? 'ACTIVE' : 'INACTIVE'}
                  </button>
                  {(seq.templates?.length > 0 || hasTiming) && (
                    <div className="text-muted">
                      {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                    </div>
                  )}
                </div>
              </div>

              {/* Expanded panel */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3 }}
                    className="overflow-hidden border-t border-border"
                  >
                    <div className="p-6 bg-white/[0.01] space-y-4">

                      {/* Message previews (non-timing sequences) */}
                      {!hasTiming && seq.templates?.map((tpl, i) => (
                        <div key={i} className="bg-background border border-border rounded-lg p-4">
                          <p className="text-xs text-muted font-mono mb-2 uppercase tracking-wider">{tpl.key}</p>
                          <p className="text-sm text-foreground-muted whitespace-pre-wrap leading-relaxed">{tpl.content}</p>
                        </div>
                      ))}

                      {/* Timing editor (timing sequences) */}
                      {hasTiming && (
                        <>
                          {seqTiming.length === 0 ? (
                            <div className="text-muted text-sm">Loading timing...</div>
                          ) : (
                            seqTiming.map((row) => {
                              const edit = edits[row.message_key] || { delay_value: row.delay_value, delay_unit: row.delay_unit };
                              const label = MESSAGE_LABELS[row.message_key] || row.message_key;
                              // Find matching message template preview
                              const templateKey = Object.keys(row).includes('template_key') ? row.template_key : null;
                              const preview = seq.templates?.find(t => t.key === row.message_key)?.content;

                              return (
                                <div key={row.message_key} className="bg-background border border-border rounded-lg p-4 space-y-3">
                                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                                    <p className="text-sm font-medium text-foreground">{label}</p>
                                    <div className="flex items-center gap-2">
                                      <input
                                        type="number"
                                        min="1"
                                        value={edit.delay_value}
                                        onChange={e => handleTimingChange(seq.sequence_number, row.message_key, 'delay_value', e.target.value)}
                                        className="w-20 bg-card-hover border border-border rounded-md px-3 py-1.5 text-sm text-foreground text-center focus:outline-none focus:border-cyan-500 transition-colors"
                                      />
                                      <select
                                        value={edit.delay_unit}
                                        onChange={e => handleTimingChange(seq.sequence_number, row.message_key, 'delay_unit', e.target.value)}
                                        className="bg-card-hover border border-border rounded-md px-3 py-1.5 text-sm text-foreground focus:outline-none focus:border-cyan-500 transition-colors"
                                      >
                                        <option value="hours">hours</option>
                                        <option value="days">days</option>
                                      </select>
                                    </div>
                                  </div>
                                  {preview && (
                                    <p className="text-xs text-muted leading-relaxed border-t border-border/50 pt-2 italic">
                                      "{preview.substring(0, 120)}{preview.length > 120 ? '...' : ''}"
                                    </p>
                                  )}
                                </div>
                              );
                            })
                          )}

                          {seqTiming.length > 0 && (
                            <div className="flex justify-end pt-2">
                              <button
                                onClick={() => saveTiming(seq.sequence_number)}
                                disabled={saving[seq.sequence_number]}
                                className="flex items-center gap-2 px-5 py-2 bg-white text-black rounded-lg text-sm font-semibold tracking-wide hover:bg-gray-100 transition-all duration-200 disabled:opacity-50"
                              >
                                <Save size={14} />
                                {saving[seq.sequence_number] ? 'Saving...' : 'Save Timing Changes'}
                              </button>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
