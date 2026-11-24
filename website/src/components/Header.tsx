import React from 'react';
import { 
  Search, 
  Sun, 
  Moon, 
  Menu, 
  Terminal, 
  BookOpen, 
  Layers, 
  Archive
} from 'lucide-react';
import { VeloLogo } from './VeloLogo';

interface HeaderProps {
  currentView: 'home' | 'docs' | 'playground' | 'stdlib' | 'architecture';
  onNavigate: (view: 'home' | 'docs' | 'playground' | 'stdlib' | 'architecture') => void;
  onOpenSearch: () => void;
  isDark: boolean;
  onToggleTheme: () => void;
  onToggleMobileMenu: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentView,
  onNavigate,
  onOpenSearch,
  isDark,
  onToggleTheme,
  onToggleMobileMenu,
}) => {

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

          {/* GitHub Repository Link */}
          <a
            href="https://github.com/velo-compiler/velo"
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-white/[0.06] transition-colors cursor-pointer flex items-center justify-center"
            title="GitHub Repository (velo-compiler/velo)"
            aria-label="GitHub Repository"
          >
            <svg
              className="w-4 h-4 fill-current"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
              />
            </svg>
          </a>

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

