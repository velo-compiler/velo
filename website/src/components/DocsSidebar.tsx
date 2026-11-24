import React, { useState } from 'react';
import { 
  ChevronDown, 
  ChevronRight, 
  CheckCircle2, 
  Circle, 
  Search,
  Sparkles,
  PlayCircle,
  BookOpen,
  GitBranch,
  Cpu,
  Layers,
  Shield,
  Database,
  Zap,
  Package,
  Archive,
  Wrench,
  Compass,
  Terminal,
  X
} from 'lucide-react';
import { DocCategory, DocPage } from '../types/docs';

interface DocsSidebarProps {
  categories: DocCategory[];
  currentPageSlug: string;
  onSelectPage: (slug: string) => void;
  completedSlugs: Set<string>;
  onToggleComplete: (slug: string) => void;
  onCloseMobile?: () => void;
}

export const DocsSidebar: React.FC<DocsSidebarProps> = ({
  categories,
  currentPageSlug,
  onSelectPage,
  completedSlugs,
  onToggleComplete,
  onCloseMobile,
}) => {
  const [filterText, setFilterText] = useState('');
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set());

  const toggleCategory = (catId: string) => {
    setCollapsedCategories(prev => {
      const next = new Set(prev);
      if (next.has(catId)) next.delete(catId);
      else next.add(catId);
      return next;
    });
  };

  const getCategoryIcon = (iconName: string) => {
    const props = { className: "w-4 h-4 text-cyan-400 shrink-0" };
    switch (iconName) {
      case 'Sparkles': return <Sparkles {...props} />;
      case 'PlayCircle': return <PlayCircle {...props} />;
      case 'BookOpen': return <BookOpen {...props} />;
      case 'GitBranch': return <GitBranch {...props} />;
      case 'Cpu': return <Cpu {...props} />;
      case 'Layers': return <Layers {...props} />;
      case 'Shield': return <Shield {...props} />;
      case 'Database': return <Database {...props} />;
      case 'Zap': return <Zap {...props} />;
      case 'Package': return <Package {...props} />;
      case 'Archive': return <Archive {...props} />;
      case 'Wrench': return <Wrench {...props} />;
      case 'Compass': return <Compass {...props} />;
      default: return <Terminal {...props} />;
    }
  };

  const filteredCategories = categories.map(cat => {
    if (!filterText.trim()) return cat;
    const matchingPages = cat.pages.filter(p =>
      p.title.toLowerCase().includes(filterText.toLowerCase()) ||
      p.description.toLowerCase().includes(filterText.toLowerCase())
    );
    return { ...cat, pages: matchingPages };
  }).filter(cat => cat.pages.length > 0);

  return (
    <aside className="w-full h-full flex flex-col bg-[#0f121a] border-r border-white/[0.08] text-sm">
      {/* Top Filter and Mobile Close */}
      <div className="p-3.5 border-b border-white/[0.08] flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            value={filterText}
            onChange={e => setFilterText(e.target.value)}
            placeholder="Filter documentation topics..."
            className="w-full bg-[#161b26] border border-white/[0.08] rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
          />
        </div>
        {onCloseMobile && (
          <button
            onClick={onCloseMobile}
            className="md:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Categories & Pages Tree */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-4">
        {filteredCategories.map(cat => {
          const isCollapsed = collapsedCategories.has(cat.id);
          return (
            <div key={cat.id} className="space-y-1">
              {/* Category Header */}
              <button
                onClick={() => toggleCategory(cat.id)}
                className="w-full flex items-center justify-between px-2.5 py-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400 hover:text-slate-200 rounded-lg hover:bg-white/[0.03] transition-colors group"
              >
                <div className="flex items-center gap-2">
                  {getCategoryIcon(cat.iconName)}
                  <span>{cat.name}</span>
                </div>
                {isCollapsed ? (
                  <ChevronRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-300" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-300" />
                )}
              </button>

              {/* Pages inside category */}
              {!isCollapsed && (
                <div className="pl-3 space-y-0.5 border-l border-white/[0.08] ml-3 mt-1">
                  {cat.pages.map(page => {
                    const isActive = page.slug === currentPageSlug;
                    const isCompleted = completedSlugs.has(page.slug);

                    return (
                      <div
                        key={page.slug}
                        className={`group flex items-center justify-between rounded-lg px-2.5 py-1.5 transition-all text-xs ${
                          isActive
                            ? 'bg-white/[0.06] text-[#00d4f0] font-medium border-l-2 border-[#00d4f0] pl-2'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]'
                        }`}
                      >
                        <button
                          onClick={() => {
                            onSelectPage(page.slug);
                            if (onCloseMobile) onCloseMobile();
                          }}
                          className="flex-1 text-left truncate py-0.5"
                        >
                          {page.title}
                        </button>

                        <div className="flex items-center gap-1.5 shrink-0 pl-1">
                          {page.badge && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700/50">
                              {page.badge}
                            </span>
                          )}
                          <button
                            onClick={e => {
                              e.stopPropagation();
                              onToggleComplete(page.slug);
                            }}
                            title={isCompleted ? 'Mark as incomplete' : 'Mark as completed'}
                            className="text-slate-500 hover:text-cyan-400 transition-colors"
                          >
                            {isCompleted ? (
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <Circle className="w-3.5 h-3.5 opacity-40 group-hover:opacity-80" />
                            )}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
};

