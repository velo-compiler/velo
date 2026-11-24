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
    <div className="my-6 rounded-xl overflow-hidden border border-white/[0.08] bg-[#0f121a] text-sm font-mono transition-all">
      {/* Code Header Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-[#161b26] border-b border-white/[0.08]">
        <div className="flex items-center gap-2">
          {title ? (
            <span className="text-xs font-mono text-slate-200 flex items-center gap-1.5">
              <Code2 className="w-3.5 h-3.5 text-slate-400" />
              <span>{title}</span>
            </span>
          ) : (
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
              {language}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {output && (
            <div className="flex rounded-md bg-[#090b10] p-0.5 border border-white/[0.08]">
              <button
                onClick={() => setActiveTab('code')}
                className={`px-2.5 py-1 text-xs rounded transition-colors flex items-center gap-1.5 ${
                  activeTab === 'code'
                    ? 'bg-[#161b26] text-slate-200 font-medium border border-white/[0.08]'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Code2 className="w-3 h-3" />
                <span>Code</span>
              </button>
              <button
                onClick={() => setActiveTab('output')}
                className={`px-2.5 py-1 text-xs rounded transition-colors flex items-center gap-1.5 ${
                  activeTab === 'output'
                    ? 'bg-[#161b26] text-emerald-400 font-medium border border-white/[0.08]'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Terminal className="w-3 h-3" />
                <span>Output</span>
              </button>
            </div>
          )}

          {title && (
            <span className="text-[11px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-white/[0.04] text-slate-400 border border-white/[0.06]">
              {language}
            </span>
          )}

          <button
            onClick={handleCopy}
            title="Copy to clipboard"
            className="p-1.5 rounded-md hover:bg-white/[0.05] text-slate-400 hover:text-slate-200 transition-colors"
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
                <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
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
        <div className="p-4 bg-[#090b10] text-[13px] text-slate-300 overflow-x-auto font-mono leading-relaxed border-t border-white/[0.08]">
          <div className="flex items-center gap-2 mb-2 text-xs text-slate-400 border-b border-white/[0.06] pb-1.5">
            <Terminal className="w-3.5 h-3.5 text-emerald-400" />
            <span>Output verified with <code className="text-slate-200">bin/velo.exe run</code></span>
          </div>
          <pre className="whitespace-pre-wrap">{output}</pre>
        </div>
      )}
    </div>
  );
};

