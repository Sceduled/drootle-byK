import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Users, User, LogOut, ToggleRight, Menu, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import logoUrl from '../assets/logo.jpeg';

export default function Layout({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem('drootle_token');
    localStorage.removeItem('drootle_role');
    localStorage.removeItem('drootle_username');
    navigate('/login');
  };

  const navItems = [
    { name: 'Leads', path: '/leads', icon: Users },
    { name: 'Metrics', path: '/metrics', icon: LayoutDashboard },
    { name: 'Sequences', path: '/sequences', icon: ToggleRight },
    { name: 'Profile', path: '/profile', icon: User },
  ];

  return (
    <div className="flex h-screen w-full bg-[#09090b] text-gray-100 overflow-hidden font-sans">
      
      {/* Mobile Header */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-16 bg-[#09090b]/80 backdrop-blur-md border-b border-white/[0.05] z-50 flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center overflow-hidden">
            <img src={logoUrl} alt="Kalvron Logo" className="w-full h-full object-cover" />
          </div>
          <h1 className="text-lg font-semibold tracking-wide text-white">Kalvron</h1>
        </div>
        <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="p-2 text-gray-400 hover:text-white">
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Sidebar */}
      <AnimatePresence>
        {(mobileMenuOpen || window.innerWidth >= 768) && (
          <motion.aside 
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            exit={{ x: -280 }}
            transition={{ type: "spring", bounce: 0, duration: 0.4 }}
            className={`w-64 glass-sidebar flex flex-col shrink-0 fixed md:relative z-40 h-full bg-[#09090b] md:bg-transparent ${mobileMenuOpen ? 'pt-16' : ''}`}
          >
            <div className="p-8 hidden md:block">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center overflow-hidden">
                  <img src={logoUrl} alt="Kalvron Logo" className="w-full h-full object-cover" />
                </div>
                <h1 className="text-lg font-semibold tracking-wide text-white">Kalvron</h1>
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
                onClick={() => setMobileMenuOpen(false)}
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
            onClick={handleLogout}
            className="flex items-center gap-3 px-4 py-3 w-full text-left rounded-xl text-gray-500 hover:bg-white/[0.03] hover:text-gray-200 transition-all duration-300"
          >
            <LogOut size={18} />
            <span className="font-medium text-sm">Logout</span>
          </button>
        </div>
      </motion.aside>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <main className="flex-1 overflow-hidden relative z-10 bg-[#09090b] pt-16 md:pt-0">
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
