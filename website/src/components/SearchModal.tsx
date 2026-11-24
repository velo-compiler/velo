import React, { useState, useEffect, useRef } from 'react';
import { Search, X, BookOpen, Code, Terminal, Layers, ArrowRight, CornerDownLeft } from 'lucide-react';
import { searchDocumentation } from '../utils/searchIndex';
import { SearchResult } from '../types/docs';

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectResult: (slug: string) => void;
}

export const SearchModal: React.FC<SearchModalProps> = ({
  isOpen,
  onClose,
  onSelectResult,
}) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery('');
      setResults([]);
      setSelectedIndex(0);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    const found = searchDocumentation(query);
    setResults(found);
    setSelectedIndex(0);
  }, [query]);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev < results.length - 1 ? prev + 1 : prev));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev > 0 ? prev - 1 : 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (results[selectedIndex]) {
        onSelectResult(results[selectedIndex].slug);
        onClose();
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  if (!isOpen) return null;

  const getTypeIcon = (type: SearchResult['type']) => {
    switch (type) {
      case 'api':
        return <Terminal className="w-3.5 h-3.5 text-[#00d4f0]" />;
      case 'syntax':
        return <Code className="w-3.5 h-3.5 text-slate-300" />;
      case 'reference':
        return <Layers className="w-3.5 h-3.5 text-slate-300" />;
      default:
        return <BookOpen className="w-3.5 h-3.5 text-slate-300" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-150">
      <div 
        className="w-full max-w-2xl bg-[#0f121a] border border-white/[0.1] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]"
        onClick={e => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-white/[0.08] gap-3 bg-[#161b26]">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search guides, language syntax, keywords, standard library APIs..."
            className="w-full bg-transparent text-slate-100 placeholder-slate-500 focus:outline-none text-sm font-sans"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="p-1 text-slate-400 hover:text-slate-200 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] text-slate-400 bg-white/[0.05] rounded border border-white/[0.08] font-mono">
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div className="overflow-y-auto p-2 space-y-1">
          {query.trim() === '' ? (
            <div className="p-8 text-center text-slate-400 space-y-3">
              <p className="text-xs">Type a search term to find guides, syntax, keywords, or APIs.</p>
              <div className="flex flex-wrap justify-center gap-1.5">
                {['zone', 'pointer', 'shelf', 'UFCS', 'SIMD', 'kind', 'defer', 'std.mem'].map(tag => (
                  <button
                    key={tag}
                    onClick={() => setQuery(tag)}
                    className="px-2.5 py-1 text-xs bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 rounded border border-white/[0.08] transition-colors"
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>
          ) : results.length === 0 ? (
            <div className="p-8 text-center text-slate-400 space-y-1">
              <p className="text-xs">No entries found for &ldquo;<span className="text-slate-200">{query}</span>&rdquo;</p>
              <p className="text-[11px] text-slate-500">Try keywords like &ldquo;act&rdquo;, &ldquo;data&rdquo;, &ldquo;shelf&rdquo;, &ldquo;install&rdquo;, or &ldquo;mem&rdquo;.</p>
            </div>
          ) : (
            results.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={`${item.slug}-${idx}`}
                  onClick={() => {
                    onSelectResult(item.slug);
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                    isSelected ? 'bg-white/[0.06] border border-white/[0.1]' : 'hover:bg-white/[0.03] border border-transparent'
                  }`}
                >
                  <div className="mt-0.5 p-1.5 rounded bg-white/[0.04] border border-white/[0.08] shrink-0 text-slate-300">
                    {getTypeIcon(item.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-xs text-white truncate">
                        {item.pageTitle}
                      </span>
                      {item.sectionTitle && (
                        <span className="text-[11px] text-slate-400 flex items-center gap-1 truncate">
                          <ArrowRight className="w-3 h-3 text-slate-600" />
                          <span>{item.sectionTitle}</span>
                        </span>
                      )}
                      <span className="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.04] text-slate-400 border border-white/[0.06] shrink-0">
                        {item.category}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                      {item.snippet}
                    </p>
                  </div>
                  {isSelected && (
                    <CornerDownLeft className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-1.5 hidden sm:block" />
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Search Modal Footer */}
        <div className="px-4 py-2.5 bg-[#161b26] border-t border-white/[0.08] flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1 text-[11px]">
              <kbd className="px-1.5 py-0.5 bg-white/[0.05] rounded border border-white/[0.08] font-mono text-[10px]">↑</kbd>
              <kbd className="px-1.5 py-0.5 bg-white/[0.05] rounded border border-white/[0.08] font-mono text-[10px]">↓</kbd>
              navigate
            </span>
            <span className="flex items-center gap-1 text-[11px]">
              <kbd className="px-1.5 py-0.5 bg-white/[0.05] rounded border border-white/[0.08] font-mono text-[10px]">↵</kbd>
              select
            </span>
          </div>
          <span className="text-slate-500 text-[11px] font-mono">
            {results.length} {results.length === 1 ? 'result' : 'results'}
          </span>
        </div>
      </div>
    </div>
  );
};

