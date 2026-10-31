import React, { useEffect, useState } from 'react';
import { AlignLeft, ArrowUp, Link as LinkIcon, Check, CheckCircle2 } from 'lucide-react';
import { DocHeading } from '../types/docs';

interface TableOfContentsProps {
  headings: DocHeading[];
  isCompleted: boolean;
  onToggleComplete: () => void;
}

export const TableOfContents: React.FC<TableOfContentsProps> = ({
  headings,
  isCompleted,
  onToggleComplete,
}) => {
  const [activeId, setActiveId] = useState<string>('');
  const [copiedLink, setCopiedLink] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      // Calculate scroll progress percentage
      const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = totalHeight > 0 ? (window.scrollY / totalHeight) * 100 : 0;
      setScrollProgress(Math.min(100, Math.max(0, Math.round(progress))));

      // Find active heading
      const scrollPosition = window.scrollY + 100;
      for (let i = headings.length - 1; i >= 0; i--) {
        const el = document.getElementById(headings[i].id);
        if (el && el.offsetTop <= scrollPosition) {
          setActiveId(headings[i].id);
          return;
        }
      }
      if (headings[0]) {
        setActiveId(headings[0].id);
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, [headings]);

  const scrollToHeading = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      const top = el.getBoundingClientRect().top + window.scrollY - 80;
      window.scrollTo({ top, behavior: 'smooth' });
    }
  };

  const copyPageLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  return (
    <div className="w-full text-xs space-y-6">
      {/* Reading Progress Indicator */}
      <div className="space-y-1.5 pb-4 border-b border-slate-800">
        <div className="flex items-center justify-between text-slate-400 font-medium">
          <span>Article Progress</span>
          <span className="text-cyan-400 font-mono">{scrollProgress}%</span>
        </div>
        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-150"
            style={{ width: `${scrollProgress}%` }}
          />
        </div>
      </div>

      {/* Headings List */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 font-semibold text-slate-300 uppercase tracking-wider text-[11px]">
          <AlignLeft className="w-3.5 h-3.5 text-cyan-400" />
          <span>On this page</span>
        </div>

        {headings.length === 0 ? (
          <p className="text-slate-500 italic">No sub-sections</p>
        ) : (
          <nav className="space-y-1 pl-2 border-l border-slate-800">
            {headings.map(h => {
              const isActive = activeId === h.id;
              return (
                <button
                  key={h.id}
                  onClick={() => scrollToHeading(h.id)}
                  className={`block text-left py-1 text-[12.5px] transition-colors leading-snug w-full truncate ${
                    isActive
                      ? 'text-cyan-400 font-medium -ml-[9px] border-l-2 border-cyan-400 pl-2'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                  style={{ paddingLeft: h.level > 2 ? '12px' : '0px' }}
                >
                  {h.text}
                </button>
              );
            })}
          </nav>
        )}
      </div>

      {/* Quick Actions */}
      <div className="pt-4 border-t border-slate-800 space-y-2">
        <button
          onClick={onToggleComplete}
          className={`w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
            isCompleted
              ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-500/30'
              : 'bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/50'
          }`}
        >
          <CheckCircle2 className={`w-3.5 h-3.5 ${isCompleted ? 'text-emerald-400' : 'text-slate-400'}`} />
          {isCompleted ? 'Completed ✓' : 'Mark as Read'}
        </button>

        <button
          onClick={copyPageLink}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-medium bg-slate-900/60 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-colors"
        >
          {copiedLink ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span>Link Copied!</span>
            </>
          ) : (
            <>
              <LinkIcon className="w-3.5 h-3.5 text-slate-400" />
              <span>Copy Article Link</span>
            </>
          )}
        </button>

        <button
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="w-full flex items-center justify-center gap-2 px-3 py-1.5 text-slate-400 hover:text-cyan-400 transition-colors text-xs"
        >
          <ArrowUp className="w-3.5 h-3.5" />
          <span>Back to top</span>
        </button>
      </div>
    </div>
  );
};

