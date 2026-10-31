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
        return <Terminal className="w-4 h-4 text-emerald-400" />;
      case 'syntax':
        return <Code className="w-4 h-4 text-cyan-400" />;
      case 'reference':
        return <Layers className="w-4 h-4 text-purple-400" />;
      default:
        return <BookOpen className="w-4 h-4 text-blue-400" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div 
        className="w-full max-w-2xl bg-[#0D1117] border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]"
        onClick={e => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-slate-800 gap-3 bg-[#161B22]">
          <Search className="w-5 h-5 text-cyan-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search documentation, syntax, keywords, standard library APIs..."
            className="w-full bg-transparent text-slate-100 placeholder-slate-400 focus:outline-none text-base"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="p-1 text-slate-400 hover:text-slate-200"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <kbd className="hidden sm:inline-block px-2 py-0.5 text-xs text-slate-400 bg-slate-800 rounded border border-slate-700 font-mono">
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div className="overflow-y-auto p-2 space-y-1 divide-y divide-slate-800/40">
          {query.trim() === '' ? (
            <div className="p-8 text-center text-slate-400">
              <p className="text-sm">Type a search term to find guides, syntax, keywords, or APIs.</p>
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                {['zone', 'pointer', 'shelf', 'UFCS', 'SIMD', 'kind', 'defer', 'std.mem'].map(tag => (
                  <button
                    key={tag}
                    onClick={() => setQuery(tag)}
                    className="px-2.5 py-1 text-xs bg-slate-800/70 hover:bg-slate-700 text-cyan-300 rounded-md border border-slate-700/50 transition-colors"
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>
          ) : results.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              <p className="text-sm">No documentation entries found for &ldquo;<span className="text-slate-200">{query}</span>&rdquo;</p>
              <p className="text-xs text-slate-500 mt-1">Try searching for keywords like &ldquo;act&rdquo;, &ldquo;data&rdquo;, &ldquo;shelf&rdquo;, or &ldquo;install&rdquo;.</p>
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
                  className={`flex items-start gap-3 p-3 rounded-xl cursor-pointer transition-all ${
                    isSelected ? 'bg-cyan-950/40 border border-cyan-500/30' : 'hover:bg-slate-800/40 border border-transparent'
                  }`}
                >
                  <div className="mt-0.5 p-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 shrink-0">
                    {getTypeIcon(item.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-slate-100 truncate">
                        {item.pageTitle}
                      </span>
                      {item.sectionTitle && (
                        <span className="text-xs text-cyan-400 flex items-center gap-1 truncate">
                          <ArrowRight className="w-3 h-3" />
                          {item.sectionTitle}
                        </span>
                      )}
                      <span className="ml-auto text-[11px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 shrink-0">
                        {item.category}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                      {item.snippet}
                    </p>
                  </div>
                  {isSelected && (
                    <CornerDownLeft className="w-4 h-4 text-cyan-400 shrink-0 mt-1.5 hidden sm:block" />
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Search Modal Footer */}
        <div className="px-4 py-2.5 bg-[#161B22] border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-slate-800 rounded border border-slate-700 font-mono">↑</kbd>
              <kbd className="px-1.5 py-0.5 bg-slate-800 rounded border border-slate-700 font-mono">↓</kbd>
              to navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-slate-800 rounded border border-slate-700 font-mono">↵</kbd>
              to select
            </span>
          </div>
          <span className="text-slate-500">
            {results.length} {results.length === 1 ? 'match' : 'matches'}
          </span>
        </div>
      </div>
    </div>
  );
};

