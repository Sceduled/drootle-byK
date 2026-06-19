import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Users, User, LogOut, ToggleRight, Menu, X, MessageSquareCode, Moon, Sun, Radio } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import logoUrl from '../assets/logo.jpeg';

export default function Layout({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  
  // Theme toggle logic
  const [isDark, setIsDark] = useState(() => {
    if (typeof window !== 'undefined') {
      const savedTheme = localStorage.getItem('drootle_theme');
      if (savedTheme) {
        return savedTheme === 'dark';
      }
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return true; // Default dark
  });

  useEffect(() => {
    const root = window.document.documentElement;
    if (isDark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('drootle_theme', isDark ? 'dark' : 'light');
  }, [isDark]);

  const toggleTheme = () => setIsDark(!isDark);

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
    { name: 'Simulator', path: '/simulator', icon: MessageSquareCode },
    { name: 'Live Updates', path: '/live-updates', icon: Radio },
    { name: 'Profile', path: '/profile', icon: User },
  ];

  return (
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden font-sans">
      
      {/* Mobile Header */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-16 bg-background backdrop-blur-md border-b border-border z-50 flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center overflow-hidden">
            <img src={logoUrl} alt="Kalvron Logo" className="w-full h-full object-cover" />
          </div>
          <h1 className="text-lg font-semibold tracking-wide text-foreground">Kalvron</h1>
        </div>
        <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="p-2 text-muted hover:text-foreground">
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
            className={`w-64 glass-sidebar flex flex-col shrink-0 fixed md:relative z-40 h-full bg-background md:bg-transparent ${mobileMenuOpen ? 'pt-16' : ''}`}
          >
            <div className="p-8 hidden md:block">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center overflow-hidden">
                  <img src={logoUrl} alt="Kalvron Logo" className="w-full h-full object-cover" />
                </div>
                <h1 className="text-lg font-semibold tracking-wide text-foreground">Kalvron</h1>
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
                    className="absolute inset-0 bg-white/[0.05] border border-border rounded-xl"
                    initial={false}
                    transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                  />
                )}
                <Icon size={18} className={`relative z-10 transition-colors duration-300 ${isActive ? 'text-foreground' : 'text-muted group-hover:text-foreground-muted'}`} />
                <span className={`relative z-10 font-medium transition-colors duration-300 text-sm ${isActive ? 'text-foreground' : 'text-muted group-hover:text-foreground-muted'}`}>
                  {item.name}
                </span>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 mt-auto border-t border-border flex flex-col gap-2">
          <button 
            onClick={toggleTheme}
            className="flex items-center gap-3 px-4 py-3 w-full text-left rounded-xl text-foreground-muted hover:bg-card-hover hover:text-foreground transition-all duration-300"
          >
            {isDark ? <Sun size={18} /> : <Moon size={18} />}
            <span className="font-medium text-sm">{isDark ? 'Light Mode' : 'Dark Mode'}</span>
          </button>
          <button 
            onClick={handleLogout}
            className="flex items-center gap-3 px-4 py-3 w-full text-left rounded-xl text-foreground-muted hover:bg-card-hover hover:text-foreground transition-all duration-300"
          >
            <LogOut size={18} />
            <span className="font-medium text-sm">Logout</span>
          </button>
        </div>
      </motion.aside>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <main className="flex-1 overflow-hidden relative z-10 bg-background pt-16 md:pt-0">
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
