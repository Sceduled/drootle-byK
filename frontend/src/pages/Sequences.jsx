import { useState, useEffect } from 'react';
import api from '../lib/api';
import { Lock, Power, ToggleRight } from 'lucide-react';

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

  if (loading) return <div className="p-8 text-gray-500">Loading settings...</div>;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <ToggleRight size={28} className="text-gray-900" />
        <h1 className="text-2xl font-bold text-gray-900">Sequences</h1>
      </div>
      
      <p className="text-gray-600 mb-8 max-w-2xl text-sm leading-relaxed">
        Manage the AI's autonomous sequences below. Toggling a sequence immediately updates the AI's behavior engine.
      </p>

      <div className="space-y-4">
        {sequences.map(seq => {
          const isLocked = seq.sequence_number === 1 || seq.sequence_number === 2;
          
          return (
            <div 
              key={seq.sequence_number} 
              className={`bg-white rounded-xl border p-6 flex items-center justify-between transition-shadow shadow-sm hover:shadow-md ${isLocked ? 'border-gray-200' : seq.enabled ? 'border-blue-200 bg-blue-50/10' : 'border-gray-200 opacity-75'}`}
            >
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded text-xs font-bold font-mono">
                    SEQ {seq.sequence_number}
                  </span>
                  <h3 className="text-lg font-bold text-gray-900">{seq.sequence_name}</h3>
                  {isLocked && (
                    <div title="Required — cannot be disabled" className="flex items-center text-gray-400 ml-1">
                      <Lock size={14} />
                    </div>
                  )}
                </div>
                <p className="text-sm text-gray-500 mt-1">
                  {SEQUENCE_DESCRIPTIONS[seq.sequence_number] || "System sequence"}
                </p>
                {isLocked && (
                  <p className="text-xs text-blue-500 mt-1 font-medium">Required — cannot be disabled</p>
                )}
              </div>
              
              <button
                onClick={() => toggleSequence(seq.sequence_number, seq.enabled)}
                disabled={isLocked}
                title={isLocked ? "Required — cannot be disabled" : ""}
                className={`flex items-center gap-2 px-4 py-2 rounded-full font-medium text-sm transition-colors ${
                  isLocked ? 'bg-gray-100 text-gray-400 cursor-not-allowed' :
                  seq.enabled ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                <Power size={16} />
                {seq.enabled ? 'ON' : 'OFF'}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
