import React from 'react';
import {
  LayoutDashboard,
  MapPin,
  Cpu,
  Send,
  ShieldAlert,
  Award,
  UploadCloud,
  FileCode2,
  Settings,
  BookOpen,
  ExternalLink,
  Layers,
} from 'lucide-react';

export type PageId =
  | 'overview'
  | 'destinations'
  | 'connectors'
  | 'publish'
  | 'rules'
  | 'certification'
  | 'import'
  | 'jobs'
  | 'settings';

interface SidebarProps {
  currentPage: PageId;
  onSelectPage: (page: PageId) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentPage, onSelectPage }) => {
  const navItems: Array<{ id: PageId; label: string; icon: React.ReactNode; badge?: string }> = [
    { id: 'overview', label: 'Overview', icon: <LayoutDashboard className="w-5 h-5" /> },
    { id: 'destinations', label: 'Destinations', icon: <MapPin className="w-5 h-5" />, badge: 'Catalogue' },
    { id: 'connectors', label: 'Connectors', icon: <Cpu className="w-5 h-5" />, badge: 'Registry' },
    { id: 'publish', label: 'Publish', icon: <Send className="w-5 h-5" />, badge: 'Dispatch' },
    { id: 'rules', label: 'Rules Engine', icon: <ShieldAlert className="w-5 h-5" />, badge: 'Pre-flight' },
    { id: 'certification', label: 'Certification Center', icon: <Award className="w-5 h-5" />, badge: '8-Step' },
    { id: 'import', label: 'Catalogue Import', icon: <UploadCloud className="w-5 h-5" /> },
    { id: 'jobs', label: 'Jobs & Logs', icon: <FileCode2 className="w-5 h-5" />, badge: 'Durable' },
    { id: 'settings', label: 'Settings', icon: <Settings className="w-5 h-5" /> },
  ];

  return (
    <aside id="sidebar-navigation" className="w-64 bg-[#0d121f] border-r border-gray-800 flex flex-col justify-between shrink-0 select-none">
      <div>
        {/* Brand Header */}
        <div className="h-16 flex items-center px-6 border-b border-gray-800 space-x-3 bg-[#0a0e1a]">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20 text-white font-black text-lg">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-white tracking-wide flex items-center gap-1.5">
              <span>IncuBrix</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-400 border border-sky-400/30">v1.0</span>
            </div>
            <div className="text-[11px] text-gray-400">Distribution Engine</div>
          </div>
        </div>

        {/* Navigation List */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const active = currentPage === item.id;
            return (
              <button
                key={item.id}
                id={`nav-link-${item.id}`}
                onClick={() => onSelectPage(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all group ${
                  active
                    ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30 shadow-sm'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60 border border-transparent'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <span className={`${active ? 'text-sky-400' : 'text-gray-400 group-hover:text-gray-300'}`}>
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                      active ? 'bg-sky-500/30 text-sky-300' : 'bg-gray-800 text-gray-400'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer / Docs Link */}
      <div className="p-4 border-t border-gray-800 bg-[#0a0e1a]/60 space-y-2">
        <a
          href="/docs"
          target="_blank"
          rel="noopener noreferrer"
          id="nav-link-docs"
          className="flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium text-gray-300 hover:text-white bg-gray-800/60 hover:bg-gray-800 border border-gray-700/60 transition group"
        >
          <div className="flex items-center space-x-2">
            <BookOpen className="w-4 h-4 text-sky-400" />
            <span>Interactive API Docs</span>
          </div>
          <ExternalLink className="w-3.5 h-3.5 text-gray-400 group-hover:text-white" />
        </a>

        <div className="text-[11px] text-gray-400 px-2 flex justify-between items-center">
          <span>Engine Status</span>
          <span className="flex items-center gap-1 text-emerald-400 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
            Operational
          </span>
        </div>
      </div>
    </aside>
  );
};
