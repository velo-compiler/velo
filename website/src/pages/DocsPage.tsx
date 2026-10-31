import React from 'react';
import { 
  ChevronRight, 
  Clock, 
  CheckCircle2, 
  ArrowLeft, 
  ArrowRight, 
  BookOpen,
  Sparkles,
  Share2,
  Terminal
} from 'lucide-react';
import { DocCategory, DocPage, DocHeading } from '../types/docs';
import { DocsSidebar } from '../components/DocsSidebar';
import { TableOfContents } from '../components/TableOfContents';
import { CodeBlock } from '../components/CodeBlock';
import { Callout } from '../components/Callout';

interface DocsPageProps {
  categories: DocCategory[];
  currentPage: DocPage;
  onSelectPage: (slug: string) => void;
  completedSlugs: Set<string>;
  onToggleComplete: (slug: string) => void;
  isMobileSidebarOpen: boolean;
  onCloseMobileSidebar: () => void;
}

export const DocsPage: React.FC<DocsPageProps> = ({
  categories,
  currentPage,
  onSelectPage,
  completedSlugs,
  onToggleComplete,
  isMobileSidebarOpen,
  onCloseMobileSidebar,
}) => {
  const isCompleted = completedSlugs.has(currentPage.slug);

  // Extract headings from sections for TableOfContents
  const headings: DocHeading[] = currentPage.sections.map(s => ({
    id: s.id,
    text: s.title,
    level: 2,
  }));

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div className="flex gap-8 items-start relative">
        {/* ================= 1. LEFT SIDEBAR (DESKTOP) ================= */}
        <div className="hidden md:block w-64 lg:w-72 shrink-0 sticky top-20 max-h-[calc(100vh-6rem)] rounded-2xl overflow-hidden border border-slate-800 shadow-lg">
          <DocsSidebar
            categories={categories}
            currentPageSlug={currentPage.slug}
            onSelectPage={onSelectPage}
            completedSlugs={completedSlugs}
            onToggleComplete={onToggleComplete}
          />
        </div>

        {/* ================= MOBILE SIDEBAR DRAWER ================= */}
        {isMobileSidebarOpen && (
          <div className="fixed inset-0 z-50 md:hidden flex">
            <div
              className="fixed inset-0 bg-black/75 backdrop-blur-sm"
              onClick={onCloseMobileSidebar}
            />
            <div className="relative w-80 max-w-[85vw] h-full bg-[#0B0F17] shadow-2xl z-10">
              <DocsSidebar
                categories={categories}
                currentPageSlug={currentPage.slug}
                onSelectPage={onSelectPage}
                completedSlugs={completedSlugs}
                onToggleComplete={onToggleComplete}
                onCloseMobile={onCloseMobileSidebar}
              />
            </div>
          </div>
        )}

        {/* ================= 2. MAIN CONTENT ARTICLE ================= */}
        <main className="flex-1 min-w-0 max-w-3xl py-2 space-y-10">
          {/* Breadcrumbs */}
          <nav className="flex items-center gap-1.5 text-xs text-slate-400 font-medium">
            <span className="hover:text-slate-200 cursor-pointer">Docs</span>
            <ChevronRight className="w-3 h-3 text-slate-600" />
            <span className="text-slate-400 truncate">{currentPage.category}</span>
            <ChevronRight className="w-3 h-3 text-slate-600" />
            <span className="text-cyan-400 font-semibold truncate">{currentPage.title}</span>
          </nav>

          {/* Article Header */}
          <div className="space-y-4 border-b border-slate-800 pb-8">
            <div className="flex flex-wrap items-center gap-2.5">
              {currentPage.badge && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-cyan-950 text-cyan-400 border border-cyan-800/40">
                  {currentPage.badge}
                </span>
              )}
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <Clock className="w-3.5 h-3.5" />
                <span>{currentPage.readTimeMinutes} min read</span>
              </div>
            </div>

            <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight font-sans">
              {currentPage.title}
            </h1>

            <p className="text-base sm:text-lg text-slate-300 leading-relaxed font-normal">
              {currentPage.description}
            </p>

            {/* Mark as Completed Toggle Button */}
            <div className="pt-2">
              <button
                onClick={() => onToggleComplete(currentPage.slug)}
                className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all ${
                  isCompleted
                    ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/40 shadow-sm'
                    : 'bg-slate-850 hover:bg-slate-800 text-slate-300 border border-slate-700/60'
                }`}
              >
                <CheckCircle2 className={`w-4 h-4 ${isCompleted ? 'text-emerald-400' : 'text-slate-400'}`} />
                <span>{isCompleted ? 'Lesson Completed' : 'Mark as Completed'}</span>
              </button>
            </div>
          </div>

          {/* "What You'll Learn" Box */}
          {currentPage.whatYoullLearn && currentPage.whatYoullLearn.length > 0 && (
            <div className="p-5 rounded-2xl bg-[#0E131F] border border-cyan-500/20 space-y-2.5">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-cyan-400 font-sans">
                <Sparkles className="w-4 h-4" />
                <span>What you&apos;ll learn in this guide</span>
              </div>
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-300 font-sans">
                {currentPage.whatYoullLearn.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-cyan-400 font-bold shrink-0 mt-0.5">✓</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Article Sections */}
          <div className="space-y-12">
            {currentPage.sections.map((section) => (
              <section key={section.id} id={section.id} className="space-y-4 scroll-mt-24">
                <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight font-sans border-b border-slate-800/60 pb-2">
                  {section.title}
                </h2>

                {/* Markdown text formatted as readable paragraphs */}
                <div className="text-slate-300 text-sm sm:text-[14.5px] leading-relaxed space-y-3.5 font-sans">
                  {section.content.split('\n\n').map((para, pIdx) => {
                    // Check if blockquote or bullet
                    if (para.startsWith('- ') || para.startsWith('* ')) {
                      const items = para.split('\n').map(line => line.replace(/^[-*]\s+/, ''));
                      return (
                        <ul key={pIdx} className="list-disc list-inside space-y-1.5 pl-2 text-slate-300">
                          {items.map((it, iIdx) => (
                            <li key={iIdx} dangerouslySetInnerHTML={{
                              __html: it
                                .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>')
                                .replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono text-xs border border-slate-700/50">$1</code>')
                            }} />
                          ))}
                        </ul>
                      );
                    }

                    if (para.startsWith('```')) {
                      const codeContent = para.replace(/```[a-z]*\n?/g, '').trim();
                      return (
                        <pre key={pIdx} className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono text-cyan-300 overflow-x-auto">
                          {codeContent}
                        </pre>
                      );
                    }

                    return (
                      <p
                        key={pIdx}
                        dangerouslySetInnerHTML={{
                          __html: para
                            .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>')
                            .replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono text-xs border border-slate-700/50">$1</code>')
                        }}
                      />
                    );
                  })}
                </div>

                {/* Table if present */}
                {section.table && (
                  <div className="overflow-x-auto my-6 rounded-xl border border-slate-800 bg-[#0E121A] shadow-md">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-slate-800 bg-[#161B24] text-slate-200">
                          {section.table.headers.map((h, hIdx) => (
                            <th key={hIdx} className="p-3 font-semibold font-sans">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 text-slate-300 font-sans">
                        {section.table.rows.map((row, rIdx) => (
                          <tr key={rIdx} className="hover:bg-slate-800/30 transition-colors">
                            {row.map((cell, cIdx) => (
                              <td key={cIdx} className="p-3 font-mono text-[12.5px]">
                                {cell}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Callout if present */}
                {section.callout && (
                  <Callout
                    type={section.callout.type}
                    title={section.callout.title}
                    text={section.callout.text}
                  />
                )}

                {/* Code Examples */}
                {section.codeExamples && section.codeExamples.map((ex, exIdx) => (
                  <CodeBlock
                    key={exIdx}
                    title={ex.title}
                    code={ex.code}
                    output={ex.output}
                    language={ex.language || 'velo'}
                  />
                ))}
              </section>
            ))}
          </div>

          {/* Previous / Next Article Navigation Cards */}
          <div className="pt-8 border-t border-slate-800 grid grid-cols-1 sm:grid-cols-2 gap-4">
            {currentPage.prevPage ? (
              <button
                onClick={() => onSelectPage(currentPage.prevPage!.slug)}
                className="p-4 rounded-xl bg-[#0D1117] hover:bg-slate-850 border border-slate-800 hover:border-cyan-500/30 text-left transition-all group"
              >
                <div className="flex items-center gap-1.5 text-xs text-slate-500 group-hover:text-cyan-400 font-medium">
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Previous</span>
                </div>
                <div className="text-sm font-bold text-white mt-1 group-hover:text-cyan-300 transition-colors">
                  {currentPage.prevPage.title}
                </div>
              </button>
            ) : <div />}

            {currentPage.nextPage ? (
              <button
                onClick={() => onSelectPage(currentPage.nextPage!.slug)}
                className="p-4 rounded-xl bg-[#0D1117] hover:bg-slate-850 border border-slate-800 hover:border-cyan-500/30 text-right transition-all group"
              >
                <div className="flex items-center justify-end gap-1.5 text-xs text-slate-500 group-hover:text-cyan-400 font-medium">
                  <span>Next</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
                <div className="text-sm font-bold text-white mt-1 group-hover:text-cyan-300 transition-colors">
                  {currentPage.nextPage.title}
                </div>
              </button>
            ) : <div />}
          </div>
        </main>

        {/* ================= 3. RIGHT SIDEBAR ("ON THIS PAGE") ================= */}
        <div className="hidden xl:block w-60 shrink-0 sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto pl-2">
          <TableOfContents
            headings={headings}
            isCompleted={isCompleted}
            onToggleComplete={() => onToggleComplete(currentPage.slug)}
          />
        </div>
      </div>
    </div>
  );
};

