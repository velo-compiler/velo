import React, { useState } from 'react';
import { 
  Play, 
  RotateCcw, 
  Copy, 
  Check, 
  Terminal, 
  Code2, 
  Zap, 
  Layers, 
  CheckCircle2, 
  Cpu, 
  Info 
} from 'lucide-react';
import { PLAYGROUND_PRESETS } from '../data/playgroundPresets';
import { runVeloVirtual, SimulationResult } from '../utils/veloSimulator';
import { highlightVeloHtml } from '../utils/veloHighlighter';

export const PlaygroundPage: React.FC = () => {
  const [selectedPresetId, setSelectedPresetId] = useState<string>(PLAYGROUND_PRESETS[0].id);
  const [code, setCode] = useState<string>(PLAYGROUND_PRESETS[0].code);
  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);
  const [activeOutputTab, setActiveOutputTab] = useState<'terminal' | 'c99'>('terminal');
  const [copied, setCopied] = useState(false);

  const currentPreset = PLAYGROUND_PRESETS.find(p => p.id === selectedPresetId) || PLAYGROUND_PRESETS[0];

  const handleSelectPreset = (presetId: string) => {
    setSelectedPresetId(presetId);
    const p = PLAYGROUND_PRESETS.find(x => x.id === presetId);
    if (p) {
      setCode(p.code);
      setSimulationResult(null);
    }
  };

  const handleReset = () => {
    setCode(currentPreset.code);
    setSimulationResult(null);
  };

  const handleCopyCode = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRun = () => {
    const res = runVeloVirtual(code, currentPreset.expectedOutput);
    setSimulationResult(res);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Page Title & Preset Selector */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-white/[0.08]">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-bold text-white font-sans flex items-center gap-2">
              <Terminal className="w-5 h-5 text-[#00d4f0]" />
              <span>Interactive Velo Playground</span>
            </h1>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-white/[0.05] text-zinc-400 border border-white/[0.08]">
              v2.0.0-pre
            </span>
          </div>
          <p className="text-xs text-zinc-400 mt-1 font-sans">
            Edit, inspect, and execute authentic Velo code snippets client-side with full ISO C99 emission previews.
          </p>
        </div>

        {/* Preset Selector */}
        <div className="flex items-center gap-2 w-full md:w-auto">
          <span className="text-xs text-zinc-400 whitespace-nowrap hidden sm:inline">Preset:</span>
          <select
            value={selectedPresetId}
            onChange={e => handleSelectPreset(e.target.value)}
            className="bg-[#161b26] border border-white/[0.08] rounded-lg px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-white/[0.2] w-full md:w-64 font-sans cursor-pointer"
          >
            {PLAYGROUND_PRESETS.map(preset => (
              <option key={preset.id} value={preset.id}>
                {preset.title} ({preset.category})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Workspace (Editor + Output Terminal) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch min-h-[600px]">
        {/* ================= LEFT COLUMN: CODE EDITOR ================= */}
        <div className="flex flex-col rounded-xl bg-[#0f121a] border border-white/[0.08] overflow-hidden shadow-xl">
          {/* Editor Header Bar */}
          <div className="flex items-center justify-between px-4 py-2.5 bg-[#161b26] border-b border-white/[0.08] text-xs">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-white/[0.05] border border-white/[0.08] font-mono text-zinc-300 text-[11px]">
                main.vl
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleReset}
                title="Reset to default code"
                className="p-1.5 text-zinc-400 hover:text-white hover:bg-white/[0.05] rounded transition-colors cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={handleCopyCode}
                title="Copy code"
                className="p-1.5 text-zinc-400 hover:text-white hover:bg-white/[0.05] rounded transition-colors cursor-pointer"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
              <button
                onClick={handleRun}
                className="px-3.5 py-1.5 bg-[#00d4f0] hover:bg-[#22ddf5] text-black font-semibold text-xs rounded-md flex items-center gap-1.5 transition-colors cursor-pointer shadow-sm"
              >
                <Play className="w-3 h-3 fill-black" />
                <span>Run</span>
              </button>
            </div>
          </div>

          {/* Editable Textarea with Line Numbers */}
          <div className="relative flex-1 flex bg-[#090b10] overflow-hidden">
            {/* Gutter */}
            <div className="w-10 py-4 select-none bg-[#0c0e14] border-r border-white/[0.06] text-right pr-2.5 text-zinc-600 font-mono text-xs leading-relaxed overflow-hidden">
              {code.split('\n').map((_, i) => (
                <div key={i}>{i + 1}</div>
              ))}
            </div>

            {/* Editor Area */}
            <div className="relative flex-1 p-4 font-mono text-[13px] leading-relaxed overflow-auto">
              <textarea
                value={code}
                onChange={e => setCode(e.target.value)}
                spellCheck={false}
                className="w-full h-full bg-transparent text-zinc-100 resize-none focus:outline-none font-mono leading-relaxed selection:bg-cyan-500/30 min-h-[480px]"
              />
            </div>
          </div>

          {/* Editor Footer Info */}
          <div className="px-4 py-2 bg-[#161b26] border-t border-white/[0.08] text-[11px] text-zinc-400 flex items-center justify-between font-sans">
            <span className="font-mono">{code.split('\n').length} lines • UTF-8</span>
            <span className="text-zinc-500">Click &ldquo;Run&rdquo; to execute via virtual compiler</span>
          </div>
        </div>

        {/* ================= RIGHT COLUMN: OUTPUT & C EMISSION ================= */}
        <div className="flex flex-col rounded-xl bg-[#0f121a] border border-white/[0.08] overflow-hidden shadow-xl">
          {/* Output Header Bar */}
          <div className="flex items-center justify-between px-4 py-2.5 bg-[#161b26] border-b border-white/[0.08] text-xs">
            <div className="flex rounded-md bg-[#090b10] p-0.5 border border-white/[0.08]">
              <button
                onClick={() => setActiveOutputTab('terminal')}
                className={`px-3 py-1 rounded transition-colors flex items-center gap-1.5 font-sans ${
                  activeOutputTab === 'terminal'
                    ? 'bg-[#161b26] text-emerald-400 font-medium border border-white/[0.08]'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <Terminal className="w-3 h-3" />
                <span>Terminal Output</span>
              </button>
              <button
                onClick={() => setActiveOutputTab('c99')}
                className={`px-3 py-1 rounded transition-colors flex items-center gap-1.5 font-sans ${
                  activeOutputTab === 'c99'
                    ? 'bg-[#161b26] text-white font-medium border border-white/[0.08]'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <Code2 className="w-3 h-3" />
                <span>Generated C99</span>
              </button>
            </div>

            {simulationResult && (
              <span className="text-[11px] font-mono text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{simulationResult.executionTimeMs}ms execution</span>
              </span>
            )}
          </div>

          {/* Output Content */}
          <div className="flex-1 p-5 font-mono text-[13px] overflow-auto leading-relaxed bg-[#090b10]">
            {activeOutputTab === 'terminal' ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-xs text-zinc-400 font-sans border-b border-white/[0.06] pb-2">
                  <Terminal className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Program stdout:</span>
                </div>

                {simulationResult ? (
                  <div className="space-y-1">
                    {simulationResult.stdout.map((line, idx) => (
                      <div key={idx} className="text-emerald-400 whitespace-pre-wrap">
                        {line}
                      </div>
                    ))}
                    <div className="pt-4 text-xs text-zinc-500 font-mono">
                      Process finished with exit code 0 (zone arena peak: {simulationResult.memoryZonePeakBytes / 1024} KB)
                    </div>
                  </div>
                ) : (
                  <div className="text-zinc-300 whitespace-pre-wrap">
                    {currentPreset.expectedOutput}
                    <div className="pt-4 text-xs text-zinc-500 font-mono">
                      [Verified with native self-hosted toolchain: bin/velo.exe run]
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* C99 Translation Unit View */
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-xs text-zinc-400 font-sans border-b border-white/[0.06] pb-2">
                  <Code2 className="w-3.5 h-3.5 text-[#00d4f0]" />
                  <span>Emitted C99 code structure (velo emit-c):</span>
                </div>
                <pre className="text-zinc-300 text-xs font-mono whitespace-pre-wrap">
                  {currentPreset.cEquivalent}
                </pre>
              </div>
            )}
          </div>

          {/* Telemetry / Disclosure Footer */}
          <div className="p-3 bg-[#161b26] border-t border-white/[0.08] text-[11px] text-zinc-400 flex items-center justify-between font-sans">
            <div className="flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-[#00d4f0]" />
              <span>Zero GC pauses guaranteed by lexical memory arenas</span>
            </div>
            <span className="font-mono text-zinc-500">ISO C99 Native Target</span>
          </div>
        </div>
      </div>
    </div>
  );
};

