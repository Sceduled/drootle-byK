import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Users, LogOut, ToggleRight } from 'lucide-react';
import { motion } from 'framer-motion';

export default function Layout({ children }) {
  const location = useLocation();

  const logout = () => {
    localStorage.removeItem('drootle_token');
    window.location.href = '/login';
  };

  const navItems = [
    { name: 'Leads', path: '/leads', icon: Users },
    { name: 'Metrics', path: '/metrics', icon: LayoutDashboard },
    { name: 'Sequences', path: '/sequences', icon: ToggleRight },
  ];

  return (
    <div className="flex h-screen w-full bg-[#09090b] text-gray-100 overflow-hidden font-sans">
      
      {/* Floating Sidebar */}
      <motion.aside 
        initial={{ x: -20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        className="w-64 glass-sidebar flex flex-col shrink-0 relative z-10"
      >
        <div className="p-8">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
              <svg className="w-4 h-4 text-gray-900" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h1 className="text-lg font-semibold tracking-wide text-white">LEAD<span className="text-gray-500 font-normal">AI</span></h1>
          </div>
        </div>
        
        <nav className="flex-1 px-4 space-y-2 mt-4">
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            const Icon = item.icon;
            return (
              <Link 
                key={item.path}
                to={item.path} 
                className="relative flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group"
              >
                {isActive && (
                  <motion.div 
                    layoutId="activeTab" 
                    className="absolute inset-0 bg-white/[0.05] border border-white/[0.05] rounded-xl"
                    initial={false}
                    transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                  />
                )}
                <Icon size={18} className={`relative z-10 transition-colors duration-300 ${isActive ? 'text-white' : 'text-gray-500 group-hover:text-gray-300'}`} />
                <span className={`relative z-10 font-medium transition-colors duration-300 text-sm ${isActive ? 'text-white' : 'text-gray-400 group-hover:text-gray-200'}`}>
                  {item.name}
                </span>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 mt-auto border-t border-white/[0.05]">
          <button 
            onClick={logout}
            className="flex items-center gap-3 px-4 py-3 w-full text-left rounded-xl text-gray-500 hover:bg-white/[0.03] hover:text-gray-200 transition-all duration-300"
          >
            <LogOut size={18} />
            <span className="font-medium text-sm">Logout</span>
          </button>
        </div>
      </motion.aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-hidden relative z-10 bg-[#09090b]">
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="h-full w-full overflow-auto"
        >
          {children}
        </motion.div>
      </main>
    </div>
  );
}
