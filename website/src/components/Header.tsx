import React from 'react';
import { 
  Zap, 
  Search, 
  Sun, 
  Moon, 
  Menu, 
  Terminal, 
  BookOpen, 
  Layers, 
  Archive,
  CheckCircle2
} from 'lucide-react';

interface HeaderProps {
  currentView: 'home' | 'docs' | 'playground' | 'stdlib' | 'architecture';
  onNavigate: (view: 'home' | 'docs' | 'playground' | 'stdlib' | 'architecture') => void;
  onOpenSearch: () => void;
  isDark: boolean;
  onToggleTheme: () => void;
  onToggleMobileMenu: () => void;
  completedCount: number;
  totalCount: number;
  onOpenProgressModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentView,
  onNavigate,
  onOpenSearch,
  isDark,
  onToggleTheme,
  onToggleMobileMenu,
  completedCount,
  totalCount,
  onOpenProgressModal,
}) => {
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  return (
    <header className="sticky top-0 z-40 w-full backdrop-blur-md bg-[#0B0F17]/90 border-b border-slate-800 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Brand Logo & Version */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate('home')}
            className="flex items-center gap-2.5 group focus:outline-none"
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 group-hover:scale-105 transition-transform">
              <Zap className="w-5 h-5 text-white fill-white" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold tracking-tight text-white font-sans">
                Velo
              </span>
              <span className="hidden sm:inline-block text-[11px] font-mono px-2 py-0.5 rounded-full bg-cyan-950/80 text-cyan-400 border border-cyan-500/30">
                v2.0 Native
              </span>
            </div>
          </button>
        </div>

        {/* Global Navigation Links (Desktop) */}
        <nav className="hidden md:flex items-center gap-1">
          <button
            onClick={() => onNavigate('home')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              currentView === 'home'
                ? 'bg-slate-800 text-cyan-300 font-semibold'
                : 'text-slate-300 hover:text-white hover:bg-slate-850'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => onNavigate('docs')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              currentView === 'docs'
                ? 'bg-slate-800 text-cyan-300 font-semibold'
                : 'text-slate-300 hover:text-white hover:bg-slate-850'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            Docs
          </button>
          <button
            onClick={() => onNavigate('playground')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              currentView === 'playground'
                ? 'bg-slate-800 text-cyan-300 font-semibold'
                : 'text-slate-300 hover:text-white hover:bg-slate-850'
            }`}
          >
            <Terminal className="w-3.5 h-3.5 text-emerald-400" />
            Playground
          </button>
          <button
            onClick={() => onNavigate('stdlib')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              currentView === 'stdlib'
                ? 'bg-slate-800 text-cyan-300 font-semibold'
                : 'text-slate-300 hover:text-white hover:bg-slate-850'
            }`}
          >
            <Archive className="w-3.5 h-3.5 text-purple-400" />
            Stdlib
          </button>
          <button
            onClick={() => onNavigate('architecture')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              currentView === 'architecture'
                ? 'bg-slate-800 text-cyan-300 font-semibold'
                : 'text-slate-300 hover:text-white hover:bg-slate-850'
            }`}
          >
            <Layers className="w-3.5 h-3.5 text-amber-400" />
            Architecture
          </button>
        </nav>

        {/* Search, Learning Progress & Controls */}
        <div className="flex items-center gap-2.5">
          {/* Search Trigger Button */}
          <button
            onClick={onOpenSearch}
            className="flex items-center gap-2 px-3 py-1.5 text-xs text-slate-400 bg-[#161B22] hover:bg-slate-800 border border-slate-800 hover:border-slate-700 rounded-lg transition-all"
            title="Search docs (Ctrl + K)"
          >
            <Search className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">Search docs...</span>
            <kbd className="hidden sm:inline-block px-1.5 py-0.2 text-[10px] text-slate-400 bg-slate-850 rounded border border-slate-700 font-mono">
              Ctrl K
            </kbd>
          </button>

          {/* Learning Progress Trigger */}
          <button
            onClick={onOpenProgressModal}
            className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-emerald-500/40 text-xs text-slate-300 transition-all group"
            title="View learning path progress"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span className="font-mono text-emerald-400 font-semibold">{progressPercent}%</span>
          </button>

          {/* Theme Switcher */}
          <button
            onClick={onToggleTheme}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDark ? <Sun className="w-4 h-4 text-amber-300" /> : <Moon className="w-4 h-4" />}
          </button>

          {/* Mobile Menu Button */}
          <button
            onClick={onToggleMobileMenu}
            className="md:hidden p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>
      </div>
    </header>
  );
};

