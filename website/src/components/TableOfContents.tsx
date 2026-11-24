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
      <div className="space-y-1.5 pb-4 border-b border-white/[0.08]">
        <div className="flex items-center justify-between text-slate-400 font-medium">
          <span>Reading progress</span>
          <span className="text-slate-300 font-mono">{scrollProgress}%</span>
        </div>
        <div className="w-full h-1 bg-white/[0.06] rounded-full overflow-hidden">
          <div
            className="h-full bg-[#00d4f0] transition-all duration-150"
            style={{ width: `${scrollProgress}%` }}
          />
        </div>
      </div>

      {/* Headings List */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 font-medium text-slate-400 uppercase tracking-wider text-[11px]">
          <AlignLeft className="w-3.5 h-3.5 text-slate-400" />
          <span>On this page</span>
        </div>

        {headings.length === 0 ? (
          <p className="text-slate-500 italic">No sub-sections</p>
        ) : (
          <nav className="space-y-1 pl-2 border-l border-white/[0.08]">
            {headings.map(h => {
              const isActive = activeId === h.id;
              return (
                <button
                  key={h.id}
                  onClick={() => scrollToHeading(h.id)}
                  className={`block text-left py-1 text-[12.5px] transition-colors leading-snug w-full truncate ${
                    isActive
                      ? 'text-[#eef0f6] font-medium -ml-[9px] border-l-2 border-[#00d4f0] pl-2'
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
      <div className="pt-4 border-t border-white/[0.08] space-y-2">
        <button
          onClick={onToggleComplete}
          className={`w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
            isCompleted
              ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-800/40'
              : 'bg-[#161b26] hover:bg-white/[0.05] text-slate-300 border border-white/[0.08]'
          }`}
        >
          <CheckCircle2 className={`w-3.5 h-3.5 ${isCompleted ? 'text-emerald-400' : 'text-slate-400'}`} />
          <span>{isCompleted ? 'Completed' : 'Mark as read'}</span>
        </button>

        <button
          onClick={copyPageLink}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-medium bg-[#161b26] hover:bg-white/[0.05] text-slate-400 hover:text-slate-200 border border-white/[0.08] transition-colors"
        >
          {copiedLink ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span>Link copied</span>
            </>
          ) : (
            <>
              <LinkIcon className="w-3.5 h-3.5 text-slate-400" />
              <span>Copy article link</span>
            </>
          )}
        </button>

        <button
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="w-full flex items-center justify-center gap-2 px-3 py-1.5 text-slate-400 hover:text-slate-200 transition-colors text-xs"
        >
          <ArrowUp className="w-3.5 h-3.5" />
          <span>Back to top</span>
        </button>
      </div>
    </div>
  );
};

