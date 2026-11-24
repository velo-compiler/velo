import React from 'react';
import { 
  ChevronRight, 
  Clock, 
  CheckCircle2, 
  ArrowLeft, 
  ArrowRight
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
        <div className="hidden md:flex flex-col w-64 lg:w-72 shrink-0 sticky top-20 h-[calc(100vh-6rem)] rounded-2xl overflow-hidden border border-white/[0.08] bg-[#0f121a]">
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
            <div className="relative w-80 max-w-[85vw] h-full bg-[#0f121a] shadow-2xl z-10 flex flex-col overflow-hidden">
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
          <nav className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
            <span className="hover:text-slate-300 cursor-pointer">Docs</span>
            <ChevronRight className="w-3 h-3 text-slate-600" />
            <span className="text-slate-400 truncate">{currentPage.category}</span>
            <ChevronRight className="w-3 h-3 text-slate-600" />
            <span className="text-slate-200 font-medium truncate">{currentPage.title}</span>
          </nav>

          {/* Article Header */}
          <div className="space-y-4 border-b border-white/[0.08] pb-8">
            <div className="flex flex-wrap items-center gap-2.5">
              {currentPage.badge && (
                <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-white/[0.05] text-slate-400 border border-white/[0.08]">
                  {currentPage.badge}
                </span>
              )}
              <div className="flex items-center gap-1.5 text-xs text-slate-500">
                <Clock className="w-3.5 h-3.5" />
                <span>{currentPage.readTimeMinutes} min read</span>
              </div>
            </div>

            <h1 className="text-3xl sm:text-4xl font-bold text-[#eef0f6] tracking-tight font-sans">
              {currentPage.title}
            </h1>

            <p className="text-base text-slate-400 leading-relaxed font-normal">
              {currentPage.description}
            </p>

            {/* Mark as Completed Toggle Button */}
            <div className="pt-2">
              <button
                onClick={() => onToggleComplete(currentPage.slug)}
                className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  isCompleted
                    ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-800/40'
                    : 'bg-[#161b26] hover:bg-white/[0.05] text-slate-300 border border-white/[0.08]'
                }`}
              >
                <CheckCircle2 className={`w-4 h-4 ${isCompleted ? 'text-emerald-400' : 'text-slate-400'}`} />
                <span>{isCompleted ? 'Completed' : 'Mark as complete'}</span>
              </button>
            </div>
          </div>

          {/* "What You'll Learn" Box */}
          {currentPage.whatYoullLearn && currentPage.whatYoullLearn.length > 0 && (
            <div className="p-5 rounded-xl bg-[#0f121a] border border-white/[0.08] space-y-3">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400 font-sans">
                <CheckCircle2 className="w-3.5 h-3.5 text-slate-400" />
                <span>Objectives</span>
              </div>
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-300 font-sans">
                {currentPage.whatYoullLearn.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-slate-500 font-mono text-xs shrink-0 mt-0.5">→</span>
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
                <h2 className="text-xl sm:text-2xl font-bold text-[#eef0f6] tracking-tight font-sans border-b border-white/[0.08] pb-2">
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
                                .replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-white/[0.06] text-slate-200 font-mono text-xs border border-white/[0.08]">$1</code>')
                            }} />
                          ))}
                        </ul>
                      );
                    }

                    if (para.startsWith('```')) {
                      const codeContent = para.replace(/```[a-z]*\n?/g, '').trim();
                      return (
                        <pre key={pIdx} className="p-4 rounded-xl bg-[#090b10] border border-white/[0.08] text-xs font-mono text-slate-300 overflow-x-auto">
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
                            .replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-white/[0.06] text-slate-200 font-mono text-xs border border-white/[0.08]">$1</code>')
                        }}
                      />
                    );
                  })}
                </div>

                {/* Table if present */}
                {section.table && (
                  <div className="overflow-x-auto my-6 rounded-xl border border-white/[0.08] bg-[#0f121a]">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-white/[0.08] bg-[#161b26] text-slate-200">
                          {section.table.headers.map((h, hIdx) => (
                            <th key={hIdx} className="p-3 font-semibold font-sans">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.05] text-slate-300 font-sans">
                        {section.table.rows.map((row, rIdx) => (
                          <tr key={rIdx} className="hover:bg-white/[0.02] transition-colors">
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
          <div className="pt-8 border-t border-white/[0.08] grid grid-cols-1 sm:grid-cols-2 gap-4">
            {currentPage.prevPage ? (
              <button
                onClick={() => onSelectPage(currentPage.prevPage!.slug)}
                className="p-4 rounded-xl bg-[#0f121a] hover:bg-[#161b26] border border-white/[0.08] hover:border-white/[0.16] text-left transition-colors group"
              >
                <div className="flex items-center gap-1.5 text-xs text-slate-500 group-hover:text-slate-400 font-medium">
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Previous</span>
                </div>
                <div className="text-sm font-semibold text-white mt-1 group-hover:text-[#00d4f0] transition-colors">
                  {currentPage.prevPage.title}
                </div>
              </button>
            ) : <div />}

            {currentPage.nextPage ? (
              <button
                onClick={() => onSelectPage(currentPage.nextPage!.slug)}
                className="p-4 rounded-xl bg-[#0f121a] hover:bg-[#161b26] border border-white/[0.08] hover:border-white/[0.16] text-right transition-colors group"
              >
                <div className="flex items-center justify-end gap-1.5 text-xs text-slate-500 group-hover:text-slate-400 font-medium">
                  <span>Next</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
                <div className="text-sm font-semibold text-white mt-1 group-hover:text-[#00d4f0] transition-colors">
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

