import React from 'react';
import { 
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
import { VeloLogo } from './VeloLogo';

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
    <header className="sticky top-0 z-40 w-full backdrop-blur-md bg-[#090b10]/90 border-b border-white/[0.08] transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between gap-4">
        {/* Brand Logo & Version */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate('home')}
            className="flex items-center gap-2.5 focus:outline-none cursor-pointer"
          >
            <div className="flex items-center justify-center">
              <VeloLogo variant="symbol" size={22} />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-base font-semibold tracking-tight text-white font-sans">
                Velo
              </span>
              <span className="hidden sm:inline-block text-[11px] font-mono px-2 py-0.5 rounded text-zinc-400 bg-white/[0.04] border border-white/[0.08]">
                2.0.0-pre
              </span>
            </div>
          </button>
        </div>

        {/* Global Navigation Links (Desktop) */}
        <nav className="hidden md:flex items-center gap-1">
          <button
            onClick={() => onNavigate('home')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer ${
              currentView === 'home'
                ? 'bg-white/[0.08] text-white border border-white/[0.12]'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => onNavigate('docs')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer ${
              currentView === 'docs'
                ? 'bg-white/[0.08] text-white border border-white/[0.12]'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            Documentation
          </button>
          <button
            onClick={() => onNavigate('playground')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer ${
              currentView === 'playground'
                ? 'bg-white/[0.08] text-white border border-white/[0.12]'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]'
            }`}
          >
            <Terminal className="w-3.5 h-3.5" />
            Playground
          </button>
          <button
            onClick={() => onNavigate('stdlib')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer ${
              currentView === 'stdlib'
                ? 'bg-white/[0.08] text-white border border-white/[0.12]'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]'
            }`}
          >
            <Archive className="w-3.5 h-3.5" />
            Standard Library
          </button>
          <button
            onClick={() => onNavigate('architecture')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer ${
              currentView === 'architecture'
                ? 'bg-white/[0.08] text-white border border-white/[0.12]'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Architecture
          </button>
        </nav>

        {/* Search, Learning Progress & Controls */}
        <div className="flex items-center gap-2">
          {/* Search Trigger Button */}
          <button
            onClick={onOpenSearch}
            className="flex items-center gap-2 px-2.5 py-1.5 text-xs text-zinc-400 bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.08] rounded-md transition-colors cursor-pointer"
            title="Search documentation (Ctrl + K)"
          >
            <Search className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Search docs</span>
            <kbd className="hidden sm:inline-block px-1.5 py-0.2 text-[10px] text-zinc-400 bg-white/[0.06] rounded border border-white/[0.08] font-mono">
              Ctrl K
            </kbd>
          </button>

          {/* Learning Progress Trigger */}
          <button
            onClick={onOpenProgressModal}
            className="hidden sm:flex items-center gap-1.5 px-2 py-1.5 rounded-md bg-white/[0.03] border border-white/[0.08] hover:bg-white/[0.06] text-xs text-zinc-300 transition-colors cursor-pointer"
            title="Learning checklist"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span className="font-mono text-xs text-zinc-300">{progressPercent}%</span>
          </button>

          {/* Theme Switcher */}
          <button
            onClick={onToggleTheme}
            className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-white/[0.06] transition-colors cursor-pointer"
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDark ? <Sun className="w-4 h-4 text-zinc-300" /> : <Moon className="w-4 h-4 text-zinc-600" />}
          </button>

          {/* Mobile Menu Button */}
          <button
            onClick={onToggleMobileMenu}
            className="md:hidden p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-white/[0.06] transition-colors cursor-pointer"
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>
      </div>
    </header>
  );
};

