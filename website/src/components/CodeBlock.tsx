import React, { useState } from 'react';
import { Copy, Check, Terminal, Code2 } from 'lucide-react';
import { highlightVeloHtml } from '../utils/veloHighlighter';

interface CodeBlockProps {
  code: string;
  language?: string;
  title?: string;
  output?: string;
  showLineNumbers?: boolean;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({
  code,
  language = 'velo',
  title,
  output,
  showLineNumbers = true,
}) => {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'code' | 'output'>('code');

  const handleCopy = () => {
    const textToCopy = activeTab === 'code' ? code : (output || '');
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lines = code.trim().split('\n');

  return (
    <div className="my-6 rounded-xl overflow-hidden border border-slate-800 bg-[#0D1117] shadow-xl text-sm font-mono transition-all">
      {/* Code Header Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-[#161B22] border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          {/* Mac-style window dots */}
          <div className="flex items-center gap-1.5 opacity-70">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80"></span>
          </div>

          {title && (
            <span className="text-xs font-medium text-slate-300 font-sans flex items-center gap-1.5 pl-2 border-l border-slate-700/60">
              <Code2 className="w-3.5 h-3.5 text-cyan-400" />
              {title}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {output && (
            <div className="flex rounded-md bg-slate-900/90 p-0.5 border border-slate-800">
              <button
                onClick={() => setActiveTab('code')}
                className={`px-2.5 py-1 text-xs rounded transition-all flex items-center gap-1.5 ${
                  activeTab === 'code'
                    ? 'bg-slate-800 text-cyan-300 shadow font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Code2 className="w-3 h-3" />
                Code
              </button>
              <button
                onClick={() => setActiveTab('output')}
                className={`px-2.5 py-1 text-xs rounded transition-all flex items-center gap-1.5 ${
                  activeTab === 'output'
                    ? 'bg-slate-800 text-emerald-300 shadow font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Terminal className="w-3 h-3" />
                Verified Output
              </button>
            </div>
          )}

          <span className="text-[11px] uppercase tracking-wider px-2 py-0.5 rounded bg-slate-800/80 text-cyan-400 border border-slate-700/50">
            {language}
          </span>

          <button
            onClick={handleCopy}
            title="Copy to clipboard"
            className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
          >
            {copied ? (
              <Check className="w-4 h-4 text-emerald-400" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Code Body */}
      {activeTab === 'code' ? (
        <div className="p-4 overflow-x-auto text-[13px] leading-relaxed">
          <table className="w-full border-collapse">
            <tbody>
              {lines.map((line, idx) => (
                <tr key={idx} className="hover:bg-slate-800/20 transition-colors">
                  {showLineNumbers && (
                    <td className="pr-4 py-0.5 text-right select-none text-slate-600 font-mono text-xs w-8 align-top">
                      {idx + 1}
                    </td>
                  )}
                  <td className="py-0.5 font-mono whitespace-pre text-slate-200">
                    <span
                      dangerouslySetInnerHTML={{
                        __html: language === 'velo' ? highlightVeloHtml(line) : line
                      }}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* Verified Output View */
        <div className="p-4 bg-[#080B10] text-[13px] text-emerald-300/90 overflow-x-auto font-mono leading-relaxed border-t border-slate-800/40">
          <div className="flex items-center gap-2 mb-2 text-xs text-slate-400 border-b border-slate-800/60 pb-1.5">
            <Terminal className="w-3.5 h-3.5 text-emerald-400" />
            <span>Terminal output verified with <code className="text-cyan-300">bin/velo.exe run</code> (Stage 2 Self-Hosted)</span>
          </div>
          <pre className="whitespace-pre-wrap">{output}</pre>
        </div>
      )}
    </div>
  );
};

