import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Eye, EyeOff } from 'lucide-react';
import api from '../lib/api';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const res = await api.post('/auth/login', { username, password });
      localStorage.setItem('drootle_token', res.data.access_token);
      localStorage.setItem('drootle_role', res.data.role);
      localStorage.setItem('drootle_username', username);
      navigate('/leads');
    } catch (err) {
      setError('Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background py-12 px-4 sm:px-6 lg:px-8 font-sans">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="max-w-md w-full space-y-8 glass-card p-10 relative overflow-hidden"
      >
        <div className="mb-8 text-center relative z-10">
          <div className="w-12 h-12 rounded-xl bg-card-hover border border-border flex items-center justify-center mx-auto mb-6">
            <svg className="w-6 h-6 text-foreground-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h2 className="text-3xl font-bold text-foreground tracking-tight">Kalvron</h2>
          <p className="mt-3 text-sm text-muted">Sign in to your workspace</p>
        </div>
        
        <form className="mt-8 space-y-6 relative z-10" onSubmit={handleLogin}>
          {error && (
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-red-400 text-sm text-center bg-red-500/10 border border-red-500/20 py-3 rounded-lg font-medium"
            >
              {error}
            </motion.div>
          )}
          
          <div className="space-y-4">
            <div>
              <input
                type="text"
                required
                className="appearance-none rounded-xl relative block w-full px-4 py-3.5 bg-card-hover border border-border placeholder-gray-500 text-foreground focus:outline-none focus:ring-1 focus:ring-white/20 focus:border-white/20 sm:text-sm transition-all"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                required
                className="appearance-none rounded-xl relative block w-full px-4 py-3.5 bg-card-hover border border-border placeholder-gray-500 text-foreground focus:outline-none focus:ring-1 focus:ring-white/20 focus:border-white/20 sm:text-sm transition-all pr-12"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-muted hover:text-foreground-muted"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-3.5 px-4 text-sm font-semibold rounded-xl text-black bg-white hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-white transition-all disabled:opacity-50"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full animate-spin" />
                  Signing in...
                </span>
              ) : 'Sign in'}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
