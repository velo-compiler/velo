import React from 'react';
import { Zap, Heart, Terminal, BookOpen, Layers, ShieldCheck } from 'lucide-react';

interface FooterProps {
  onNavigate: (view: 'home' | 'docs' | 'playground' | 'stdlib' | 'architecture') => void;
  onSelectDocPage?: (slug: string) => void;
}

export const Footer: React.FC<FooterProps> = ({ onNavigate, onSelectDocPage }) => {
  return (
    <footer className="border-t border-slate-800 bg-[#080B10] text-slate-400 text-xs font-sans mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-10">
          {/* Brand Info */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center">
                <Zap className="w-3.5 h-3.5 text-white fill-white" />
              </div>
              <span className="text-base font-bold text-white font-sans">Velo</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/40">
                v2.0
              </span>
            </div>
            <p className="text-slate-400 leading-relaxed text-xs">
              Code at high velocity. The raw speed and hardware control of C, with modern syntax as clean as TypeScript, and zero garbage collection pauses.
            </p>
            <div className="flex items-center gap-2 text-slate-500 text-[11px]">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Bit-for-bit 3-gen determinism verified</span>
            </div>
          </div>

          {/* Learn & Documentation */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
              Documentation
            </h4>
            <ul className="space-y-1.5">
              <li>
                <button
                  onClick={() => {
                    onNavigate('docs');
                    if (onSelectDocPage) onSelectDocPage('intro-welcome');
                  }}
                  className="hover:text-cyan-400 transition-colors"
                >
                  Introduction & Philosophy
                </button>
              </li>
              <li>
                <button
                  onClick={() => {
                    onNavigate('docs');
                    if (onSelectDocPage) onSelectDocPage('getting-started-install');
                  }}
                  className="hover:text-cyan-400 transition-colors"
                >
                  Installation & Setup
                </button>
              </li>
              <li>
                <button
                  onClick={() => {
                    onNavigate('docs');
                    if (onSelectDocPage) onSelectDocPage('memory-pointers');
                  }}
                  className="hover:text-cyan-400 transition-colors"
                >
                  The @ Pointer System
                </button>
              </li>
              <li>
                <button
                  onClick={() => {
                    onNavigate('docs');
                    if (onSelectDocPage) onSelectDocPage('memory-zone-arenas');
                  }}
                  className="hover:text-cyan-400 transition-colors"
                >
                  Zone Arena Memory (0ms GC)
                </button>
              </li>
              <li>
                <button
                  onClick={() => {
                    onNavigate('docs');
                    if (onSelectDocPage) onSelectDocPage('collections-shelf');
                  }}
                  className="hover:text-cyan-400 transition-colors"
                >
                  Dynamic Shelves (shelf[T])
                </button>
              </li>
            </ul>
          </div>

          {/* Interactive Tools */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
              Ecosystem & Tools
            </h4>
            <ul className="space-y-1.5">
              <li>
                <button onClick={() => onNavigate('playground')} className="hover:text-cyan-400 transition-colors flex items-center gap-1.5">
                  <Terminal className="w-3 h-3 text-emerald-400" />
                  Virtual Playground
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('stdlib')} className="hover:text-cyan-400 transition-colors flex items-center gap-1.5">
                  <BookOpen className="w-3 h-3 text-purple-400" />
                  Stdlib Catalog (127 Modules)
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('architecture')} className="hover:text-cyan-400 transition-colors flex items-center gap-1.5">
                  <Layers className="w-3 h-3 text-amber-400" />
                  Compiler Architecture & Determinism
                </button>
              </li>
              <li>
                <button
                  onClick={() => {
                    onNavigate('docs');
                    if (onSelectDocPage) onSelectDocPage('tooling-lsp');
                  }}
                  className="hover:text-cyan-400 transition-colors"
                >
                  Native LSP 3.17 (velo lsp)
                </button>
              </li>
              <li>
                <button
                  onClick={() => {
                    onNavigate('docs');
                    if (onSelectDocPage) onSelectDocPage('case-study-velokv');
                  }}
                  className="hover:text-cyan-400 transition-colors"
                >
                  Case Study: VeloKV In-Memory Store
                </button>
              </li>
            </ul>
          </div>

          {/* Specifications & Standards */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
              Standards & Codebase
            </h4>
            <ul className="space-y-1.5 text-slate-400">
              <li>100% Self-Hosted Compiler (\`src/\`)</li>
              <li>Single-File Bootstrap Snapshot (\`bootstrap.c\`)</li>
              <li>Max 400 lines per module rule</li>
              <li>Clean ISO C99 target (GCC / MSVC cl.exe)</li>
              <li>No garbage collector runtime</li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-slate-800/80 flex flex-col sm:flex-row items-center justify-between gap-4 text-slate-500">
          <p>© 2026 The Velo Systems Programming Language Project. Open Source.</p>
          <p className="flex items-center gap-1">
            Engineered with <Heart className="w-3 h-3 text-rose-500 fill-rose-500" /> for systems programmers, game developers, and high-velocity engineers.
          </p>
        </div>
      </div>
    </footer>
  );
};

