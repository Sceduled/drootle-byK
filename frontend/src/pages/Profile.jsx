import { useState, useEffect } from 'react';
import { User, Building2, Bot } from 'lucide-react';
import api from '../lib/api';
import { motion } from 'framer-motion';

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await api.get('/dashboard/profile');
      setProfile(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-8 text-center text-gray-500">Loading...</div>;
  if (!profile) return <div className="p-8 text-center text-red-500">Failed to load profile.</div>;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-wide">Company Profile</h1>
          <p className="text-gray-400 mt-1">Your brand and AI agent details</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="glass-card p-6"
        >
          <div className="flex items-center gap-4 mb-6">
            <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center">
              <Building2 size={24} className="text-gray-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-widest">Brand Name</h3>
              <p className="text-lg font-medium text-white">{profile.client_brand}</p>
            </div>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="glass-card p-6"
        >
          <div className="flex items-center gap-4 mb-6">
            <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center">
              <User size={24} className="text-gray-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-widest">Owner</h3>
              <p className="text-lg font-medium text-white">{profile.owner_name}</p>
            </div>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="glass-card p-6 md:col-span-2"
        >
          <div className="flex items-center gap-4 mb-6">
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
              <Bot size={24} className="text-blue-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-widest">AI Agent Persona</h3>
              <p className="text-lg font-medium text-white">{profile.agent_name}</p>
            </div>
          </div>
          <p className="text-sm text-gray-400 leading-relaxed max-w-2xl">
            {profile.agent_name} is your AI sales assistant deployed to qualify leads. She operates based on the qualification criteria and sequence settings defined in your configuration.
          </p>
        </motion.div>
      </div>
    </div>
  );
}
