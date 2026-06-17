import { useState, useEffect } from 'react';
import { User, Building2 } from 'lucide-react';
import api from '../lib/api';
import { motion } from 'framer-motion';
import mayaAvatarUrl from '../assets/maya.png';

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState([]);
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [creatingUser, setCreatingUser] = useState(false);
  const [userError, setUserError] = useState('');

  const currentUserRole = localStorage.getItem('drootle_role');

  useEffect(() => {
    fetchProfile();
    if (currentUserRole === 'admin') {
      fetchUsers();
    }
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

  const fetchUsers = async () => {
    try {
      const res = await api.get('/dashboard/users');
      setUsers(res.data);
    } catch (err) {
      console.error("Failed to load users", err);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setUserError('');
    setCreatingUser(true);
    try {
      await api.post('/dashboard/users', { username: newUsername, password: newPassword });
      setNewUsername('');
      setNewPassword('');
      await fetchUsers();
    } catch (err) {
      setUserError(err.response?.data?.detail || err.response?.data?.error || "Failed to create user");
    } finally {
      setCreatingUser(false);
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
            <div className="w-12 h-12 rounded-xl border border-blue-500/20 flex items-center justify-center overflow-hidden shrink-0 shadow-[0_0_15px_rgba(59,130,246,0.2)]">
              <img src={mayaAvatarUrl} alt="Maya Avatar" className="w-full h-full object-cover" />
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

      {currentUserRole === 'admin' && (
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.3 }}
          className="glass-card p-6 mt-8"
        >
          <h2 className="text-lg font-semibold text-white mb-6 uppercase tracking-widest">Sales Team</h2>
          
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-widest mb-4">Add Sales Rep</h3>
              <form onSubmit={handleCreateUser} className="space-y-4">
                <div>
                  <input
                    type="text"
                    required
                    placeholder="Username"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    className="w-full bg-white/[0.02] border border-white/[0.05] rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:ring-1 focus:ring-white/20"
                  />
                </div>
                <div>
                  <input
                    type="password"
                    required
                    placeholder="Password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full bg-white/[0.02] border border-white/[0.05] rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:ring-1 focus:ring-white/20"
                  />
                </div>
                {userError && <p className="text-red-400 text-xs font-semibold">{userError}</p>}
                <button
                  type="submit"
                  disabled={creatingUser}
                  className="w-full bg-white text-black font-semibold py-3 px-4 rounded-xl hover:bg-gray-200 transition-colors disabled:opacity-50 text-sm"
                >
                  {creatingUser ? "Creating..." : "Create Account"}
                </button>
              </form>
            </div>
            
            <div>
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-widest mb-4">Current Team</h3>
              <div className="space-y-3">
                {users.map(u => (
                  <div key={u.id} className="bg-white/[0.02] border border-white/[0.05] rounded-xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
                        <User size={14} className="text-gray-400" />
                      </div>
                      <span className="font-medium text-white text-sm">{u.username}</span>
                    </div>
                    <span className="text-xs uppercase tracking-widest text-gray-500 font-semibold">{u.role.replace('_', ' ')}</span>
                  </div>
                ))}
                {users.length === 0 && <p className="text-gray-500 text-sm">No users found.</p>}
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
