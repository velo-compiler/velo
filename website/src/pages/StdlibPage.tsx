import React, { useState } from 'react';
import { 
  Archive, 
  Search, 
  CheckCircle2, 
  Code2, 
  Copy, 
  Check, 
  ShieldCheck, 
  ExternalLink,
  Layers,
  Terminal,
  Zap
} from 'lucide-react';
import { STDLIB_MODULES } from '../data/stdlib';
import { StdlibModule } from '../types/docs';

export const StdlibPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTier, setSelectedTier] = useState<'all' | '1' | '2'>('all');
  const [selectedModule, setSelectedModule] = useState<StdlibModule>(STDLIB_MODULES[0]);
  const [copiedSig, setCopiedSig] = useState<string | null>(null);

  const filteredModules = STDLIB_MODULES.filter(m => {
    const matchesSearch = m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.functions.some(f => f.name.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesTier = selectedTier === 'all' || m.tier.toString() === selectedTier;

    return matchesSearch && matchesTier;
  });

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSig(text);
    setTimeout(() => setCopiedSig(null), 2000);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Page Header */}
      <div className="space-y-4 pb-6 border-b border-slate-800">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-extrabold text-white font-sans flex items-center gap-2.5">
                <Archive className="w-7 h-7 text-cyan-400" />
                <span>Velo Standard Library (std.*)</span>
              </h1>
              <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/50">
                100% Pure Velo
              </span>
            </div>
            <p className="text-slate-300 text-sm mt-1 max-w-3xl">
              127 pure-Velo modules written with zero libc dependencies. Memory, formatting, strings, I/O, and data structures from the ground up.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs font-mono px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400">
              ~19,400 LOC in std/
            </span>
          </div>
        </div>

        {/* Filter & Search Bar */}
        <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search standard library modules or functions (e.g. mem.alloc, fmt, simd)..."
              className="w-full bg-[#161B22] border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Tier Switcher */}
          <div className="flex rounded-lg bg-[#161b26] p-0.5 border border-white/[0.08] shrink-0 text-xs">
            <button
              onClick={() => setSelectedTier('all')}
              className={`px-3 py-1 rounded transition-colors ${
                selectedTier === 'all'
                  ? 'bg-[#0f121a] text-white font-medium border border-white/[0.08]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All Modules
            </button>
            <button
              onClick={() => setSelectedTier('1')}
              className={`px-3 py-1 rounded transition-colors ${
                selectedTier === '1'
                  ? 'bg-[#0f121a] text-white font-medium border border-white/[0.08]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Tier 1 (Foundation)
            </button>
            <button
              onClick={() => setSelectedTier('2')}
              className={`px-3 py-1 rounded transition-colors ${
                selectedTier === '2'
                  ? 'bg-[#0f121a] text-white font-medium border border-white/[0.08]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Tier 2 (Extended A–Z)
            </button>
          </div>
        </div>
      </div>

      {/* Two-Column Explorer Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Left: Module List */}
        <div className="rounded-2xl bg-[#0f121a] border border-white/[0.08] p-2 space-y-1 max-h-[750px] overflow-y-auto">
          {filteredModules.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No matching standard library modules found.
            </div>
          ) : (
            filteredModules.map(mod => {
              const isSelected = mod.name === selectedModule.name;
              return (
                <button
                  key={mod.name}
                  onClick={() => setSelectedModule(mod)}
                  className={`w-full text-left p-3 rounded-xl transition-all flex items-start justify-between gap-2 ${
                    isSelected
                      ? 'bg-[#161b26] border border-white/[0.12] text-white'
                      : 'hover:bg-white/[0.03] text-slate-300 border border-transparent'
                  }`}
                >
                  <div className="space-y-0.5 truncate">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-[#eef0f6]">
                        {mod.name}
                      </span>
                      {mod.tier === 1 && (
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-white/[0.05] text-slate-400 border border-white/[0.08]">
                          Tier 1
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400 truncate max-w-[200px]">
                      {mod.description}
                    </p>
                  </div>
                  <span className="text-[10px] text-slate-500 shrink-0 font-mono">
                    {mod.functions.length} APIs
                  </span>
                </button>
              );
            })
          )}
        </div>

        {/* Right: Selected Module Details */}
        <div className="lg:col-span-2 space-y-6 rounded-2xl bg-[#0f121a] border border-white/[0.08] p-6 shadow-xl">
          {/* Module Header */}
          <div className="space-y-3 pb-6 border-b border-white/[0.08]">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <h2 className="text-2xl font-bold font-mono text-[#eef0f6]">
                  {selectedModule.name}
                </h2>
                <span className="text-xs font-sans px-2.5 py-0.5 rounded-full bg-white/[0.05] text-slate-300 border border-white/[0.08]">
                  {selectedModule.category}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/40 flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Zero Libc</span>
                </span>
              </div>
            </div>

            <p className="text-sm text-slate-300 leading-relaxed font-sans">
              {selectedModule.description}
            </p>

            <div className="p-3 bg-[#161b26] border border-white/[0.08] rounded-xl font-mono text-xs text-slate-300 flex items-center justify-between">
              <span>use {selectedModule.name}</span>
              <button
                onClick={() => handleCopy(`use ${selectedModule.name}`)}
                className="text-slate-400 hover:text-slate-200"
                title="Copy import"
              >
                {copiedSig === `use ${selectedModule.name}` ? (
                  <Check className="w-4 h-4 text-emerald-400" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>

          {/* Functions & APIs */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-sans flex items-center gap-2">
              <Terminal className="w-4 h-4 text-[#00d4f0]" />
              <span>Public Module Functions</span>
            </h3>

            <div className="space-y-4">
              {selectedModule.functions.map(fn => (
                <div key={fn.name} className="p-4 rounded-xl bg-[#161b26] border border-white/[0.06] space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs font-bold text-emerald-400">
                      {fn.signature}
                    </span>
                    <button
                      onClick={() => handleCopy(fn.signature)}
                      className="p-1 text-slate-400 hover:text-slate-200 rounded"
                      title="Copy signature"
                    >
                      {copiedSig === fn.signature ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>

                  <p className="text-xs text-slate-300 font-sans">
                    {fn.description}
                  </p>

                  {fn.example && (
                    <div className="pt-2">
                      <div className="text-[11px] text-slate-500 font-sans mb-1">Example usage:</div>
                      <pre className="p-2.5 rounded-lg bg-[#090b10] border border-white/[0.08] text-xs font-mono text-cyan-300 overflow-x-auto">
                        {fn.example}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Module Types if any */}
          {selectedModule.types && selectedModule.types.length > 0 && (
            <div className="space-y-4 pt-4 border-t border-white/[0.08]">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-sans flex items-center gap-2">
                <Code2 className="w-4 h-4 text-slate-400" />
                <span>Exported Data Types</span>
              </h3>

              <div className="space-y-3">
                {selectedModule.types.map(t => (
                  <div key={t.name} className="p-3.5 rounded-xl bg-[#161b26] border border-white/[0.06] space-y-1.5">
                    <div className="font-mono text-xs font-bold text-slate-200">
                      {t.name}
                    </div>
                    <pre className="p-2 rounded bg-[#090b10] border border-white/[0.08] text-xs font-mono text-slate-300 overflow-x-auto">
                      {t.definition}
                    </pre>
                    <p className="text-xs text-slate-400 font-sans">
                      {t.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

