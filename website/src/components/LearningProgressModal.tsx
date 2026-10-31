import React from 'react';
import { X, CheckCircle2, Circle, RotateCcw, ArrowRight, Award, BookOpen } from 'lucide-react';
import { DocCategory } from '../types/docs';

interface LearningProgressModalProps {
  isOpen: boolean;
  onClose: () => void;
  categories: DocCategory[];
  completedSlugs: Set<string>;
  onToggleComplete: (slug: string) => void;
  onResetProgress: () => void;
  onSelectPage: (slug: string) => void;
}

export const LearningProgressModal: React.FC<LearningProgressModalProps> = ({
  isOpen,
  onClose,
  categories,
  completedSlugs,
  onToggleComplete,
  onResetProgress,
  onSelectPage,
}) => {
  if (!isOpen) return null;

  const allPages = categories.flatMap(c => c.pages);
  const totalCount = allPages.length;
  const completedCount = completedSlugs.size;
  const percent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  // Find next uncompleted lesson
  const nextLesson = allPages.find(p => !completedSlugs.has(p.slug));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
      <div 
        className="w-full max-w-2xl bg-[#0D1117] border border-slate-700 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
        onClick={e => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="px-6 py-4.5 bg-[#161B22] border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Award className="w-5 h-5 text-emerald-400" />
            <h3 className="text-base font-bold text-white font-sans">
              Learning Path Progress
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Progress Overview Bar */}
        <div className="px-6 py-5 bg-[#0A0D13] border-b border-slate-800/80 space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-300 font-medium">Curriculum Completion</span>
            <span className="text-emerald-400 font-bold font-mono text-base">
              {completedCount} / {totalCount} lessons ({percent}%)
            </span>
          </div>

          <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 transition-all duration-300"
              style={{ width: `${percent}%` }}
            />
          </div>

          {nextLesson && (
            <div className="pt-2 flex items-center justify-between">
              <span className="text-xs text-slate-400">Next suggested lesson:</span>
              <button
                onClick={() => {
                  onSelectPage(nextLesson.slug);
                  onClose();
                }}
                className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1.5 transition-colors"
              >
                <span>{nextLesson.title}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>

        {/* Lessons List categorized */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4 divide-y divide-slate-800/50">
          {categories.map(cat => {
            const catCompleted = cat.pages.filter(p => completedSlugs.has(p.slug)).length;
            return (
              <div key={cat.id} className="pt-3 first:pt-0 space-y-2">
                <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-400">
                  <span>{cat.name}</span>
                  <span className="font-mono text-slate-500">
                    {catCompleted}/{cat.pages.length}
                  </span>
                </div>

                <div className="space-y-1">
                  {cat.pages.map(page => {
                    const isDone = completedSlugs.has(page.slug);
                    return (
                      <div
                        key={page.slug}
                        className="flex items-center justify-between py-1.5 px-2.5 rounded-lg hover:bg-slate-850 transition-colors text-xs"
                      >
                        <button
                          onClick={() => {
                            onSelectPage(page.slug);
                            onClose();
                          }}
                          className="flex items-center gap-2 text-left truncate flex-1 text-slate-300 hover:text-white"
                        >
                          <BookOpen className="w-3.5 h-3.5 text-slate-500" />
                          <span className={isDone ? 'line-through text-slate-500' : ''}>
                            {page.title}
                          </span>
                        </button>

                        <button
                          onClick={() => onToggleComplete(page.slug)}
                          className="p-1 text-slate-500 hover:text-emerald-400 transition-colors shrink-0"
                          title={isDone ? 'Mark incomplete' : 'Mark completed'}
                        >
                          {isDone ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                          ) : (
                            <Circle className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Modal Footer with Reset */}
        <div className="px-6 py-3.5 bg-[#161B22] border-t border-slate-800 flex items-center justify-between text-xs">
          <button
            onClick={() => {
              if (window.confirm('Reset all saved learning progress?')) {
                onResetProgress();
              }
            }}
            className="flex items-center gap-1.5 text-slate-400 hover:text-rose-400 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Progress</span>
          </button>

          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition-colors font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

