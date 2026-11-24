import React from 'react';
import { Terminal, BookOpen, Layers, ShieldCheck } from 'lucide-react';
import { VeloLogo } from './VeloLogo';

interface FooterProps {
  onNavigate: (view: 'home' | 'docs' | 'playground' | 'stdlib' | 'architecture') => void;
  onSelectDocPage?: (slug: string) => void;
}

export const Footer: React.FC<FooterProps> = ({ onNavigate, onSelectDocPage }) => {
  return (
    <footer className="border-t border-white/[0.08] bg-[#07090e] text-zinc-400 text-xs font-sans mt-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 mb-12">
          {/* Brand Info */}
          <div className="space-y-3.5">
            <div className="flex items-center gap-2.5">
              <VeloLogo variant="symbol" size={20} />
              <span className="text-sm font-semibold tracking-tight text-white font-sans">Velo</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded text-zinc-400 bg-white/[0.04] border border-white/[0.08]">
                2.0.0-pre
              </span>
            </div>
            <p className="text-zinc-400 leading-relaxed text-xs">
              A self-hosted, bare-metal systems programming language compiling to deterministic C99 with SIMD vector intrinsics and zero garbage collection pauses.
            </p>
            <div className="flex items-center gap-2 text-zinc-500 text-[11px] font-mono">
              <ShieldCheck className="w-3.5 h-3.5 text-zinc-400" />
              <span>Bit-for-bit 3-generation determinism</span>
            </div>
          </div>

          {/* Learn & Documentation */}
          <div className="space-y-2.5">
            <h4 className="text-xs font-medium text-zinc-200">
              Documentation
            </h4>
            <ul className="space-y-1.5 text-zinc-400">
              <li>
                <button
                  onClick={() => {
                    onNavigate('docs');
                    if (onSelectDocPage) onSelectDocPage('intro-welcome');
                  }}
                  className="hover:text-white transition-colors cursor-pointer"
                >
                  Introduction & philosophy
                </button>
              </li>
              <li>
                <button
                  onClick={() => {
                    onNavigate('docs');
                    if (onSelectDocPage) onSelectDocPage('getting-started-install');
                  }}
                  className="hover:text-white transition-colors cursor-pointer"
                >
                  Installation & toolchain setup
                </button>
              </li>
              <li>
                <button
                  onClick={() => {
                    onNavigate('docs');
                    if (onSelectDocPage) onSelectDocPage('memory-pointers');
                  }}
                  className="hover:text-white transition-colors cursor-pointer"
                >
                  The @ pointer model
                </button>
              </li>
              <li>
                <button
                  onClick={() => {
                    onNavigate('docs');
                    if (onSelectDocPage) onSelectDocPage('memory-zone-arenas');
                  }}
                  className="hover:text-white transition-colors cursor-pointer"
                >
                  Lexical zone arenas (zero-cycle reset)
                </button>
              </li>
              <li>
                <button
                  onClick={() => {
                    onNavigate('docs');
                    if (onSelectDocPage) onSelectDocPage('collections-shelf');
                  }}
                  className="hover:text-white transition-colors cursor-pointer"
                >
                  Dynamic shelves (shelf[T])
                </button>
              </li>
            </ul>
          </div>

          {/* Interactive Tools */}
          <div className="space-y-2.5">
            <h4 className="text-xs font-medium text-zinc-200">
              Ecosystem & tools
            </h4>
            <ul className="space-y-1.5 text-zinc-400">
              <li>
                <button onClick={() => onNavigate('playground')} className="hover:text-white transition-colors flex items-center gap-1.5 cursor-pointer">
                  <Terminal className="w-3.5 h-3.5 text-zinc-400" />
                  Virtual compiler playground
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('stdlib')} className="hover:text-white transition-colors flex items-center gap-1.5 cursor-pointer">
                  <BookOpen className="w-3.5 h-3.5 text-zinc-400" />
                  Standard library catalog (127 modules)
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('architecture')} className="hover:text-white transition-colors flex items-center gap-1.5 cursor-pointer">
                  <Layers className="w-3.5 h-3.5 text-zinc-400" />
                  Compiler architecture & bootstrap
                </button>
              </li>
              <li>
                <button
                  onClick={() => {
                    onNavigate('docs');
                    if (onSelectDocPage) onSelectDocPage('tooling-lsp');
                  }}
                  className="hover:text-white transition-colors cursor-pointer"
                >
                  Native LSP 3.17 server
                </button>
              </li>
              <li>
                <button
                  onClick={() => {
                    onNavigate('docs');
                    if (onSelectDocPage) onSelectDocPage('case-study-velokv');
                  }}
                  className="hover:text-white transition-colors cursor-pointer"
                >
                  Case study: VeloKV in-memory engine
                </button>
              </li>
            </ul>
          </div>

          {/* Specifications & Standards */}
          <div className="space-y-2.5">
            <h4 className="text-xs font-medium text-zinc-200">
              Architecture standards
            </h4>
            <ul className="space-y-1.5 text-zinc-400 font-mono text-[11px]">
              <li>• 100% self-hosted compiler (src/)</li>
              <li>• Standalone bootstrap snapshot (bootstrap.c)</li>
              <li>• Strict 400-line modularity rule</li>
              <li>• Standard ISO C99 target (GCC & MSVC)</li>
              <li>• Zero runtime garbage collector</li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-white/[0.08] flex flex-col sm:flex-row items-center justify-between gap-4 text-zinc-500 text-[11px]">
          <p>© 2026 The Velo Programming Language Project. Open Source under Apache 2.0.</p>
          <p className="font-mono">
            Deterministic • Bare-metal • Verified
          </p>
        </div>
      </div>
    </footer>
  );
};

