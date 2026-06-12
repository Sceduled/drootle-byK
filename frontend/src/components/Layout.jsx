import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Users, LogOut } from 'lucide-react';

export default function Layout({ children }) {
  const location = useLocation();

  const logout = () => {
    localStorage.removeItem('drootle_token');
    window.location.href = '/login';
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <div className="w-64 bg-gray-900 text-white flex flex-col shrink-0">
        <div className="p-6">
          <h1 className="text-xl font-bold tracking-wider">DROOTLE<span className="text-gray-400 font-normal"> AI</span></h1>
        </div>
        
        <nav className="flex-1 px-4 space-y-2 mt-4">
          <Link 
            to="/leads" 
            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${location.pathname.startsWith('/leads') ? 'bg-gray-800 text-white' : 'text-gray-400 hover:bg-gray-800/50 hover:text-white'}`}
          >
            <Users size={20} />
            Leads
          </Link>
          <Link 
            to="/metrics" 
            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${location.pathname === '/metrics' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:bg-gray-800/50 hover:text-white'}`}
          >
            <LayoutDashboard size={20} />
            Metrics
          </Link>
        </nav>

        <div className="p-4 border-t border-gray-800">
          <button 
            onClick={logout}
            className="flex items-center gap-3 px-4 py-3 w-full text-left rounded-lg text-gray-400 hover:bg-gray-800/50 hover:text-white transition-colors"
          >
            <LogOut size={20} />
            Logout
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto bg-gray-50">
        {children}
      </div>
    </div>
  );
}
