import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { SearchModal } from './components/SearchModal';
import { HomePage } from './pages/HomePage';
import { DocsPage } from './pages/DocsPage';
import { PlaygroundPage } from './pages/PlaygroundPage';
import { StdlibPage } from './pages/StdlibPage';
import { ArchitecturePage } from './pages/ArchitecturePage';
import { DOC_CATEGORIES, ALL_DOC_PAGES, findDocPageBySlug } from './data/documentation';
import { DocPage } from './types/docs';

export function App() {
  const [currentView, setCurrentView] = useState<'home' | 'docs' | 'playground' | 'stdlib' | 'architecture'>('home');
  const [currentDocPage, setCurrentDocPage] = useState<DocPage>(ALL_DOC_PAGES[0]);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isDark, setIsDark] = useState(true);

  // Learning Progress state (saved in localStorage)
  const [completedSlugs, setCompletedSlugs] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem('velo_docs_completed');
      return saved ? new Set(JSON.parse(saved)) : new Set<string>();
    } catch {
      return new Set<string>();
    }
  });

  // Load theme preference
  useEffect(() => {
    try {
      const savedTheme = localStorage.getItem('velo_theme');
      if (savedTheme === 'light') {
        setIsDark(false);
        document.documentElement.classList.remove('dark');
        document.documentElement.classList.add('light');
      } else {
        setIsDark(true);
        document.documentElement.classList.add('dark');
        document.documentElement.classList.remove('light');
      }
    } catch {
      // Default dark
    }
  }, []);

  const toggleTheme = () => {
    setIsDark(prev => {
      const next = !prev;
      if (next) {
        document.documentElement.classList.add('dark');
        document.documentElement.classList.remove('light');
        localStorage.setItem('velo_theme', 'dark');
      } else {
        document.documentElement.classList.remove('dark');
        document.documentElement.classList.add('light');
        localStorage.setItem('velo_theme', 'light');
      }
      return next;
    });
  };

  // Listen for global Ctrl+K / Cmd+K for search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsSearchOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Sync Hash changes with views/pages
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '');
      if (!hash) return;

      if (hash === 'home' || hash === 'playground' || hash === 'stdlib' || hash === 'architecture') {
        setCurrentView(hash as any);
        return;
      }

      if (hash.startsWith('docs/')) {
        const slug = hash.replace('docs/', '');
        const page = findDocPageBySlug(slug);
        if (page) {
          setCurrentDocPage(page);
          setCurrentView('docs');
        }
      } else {
        const page = findDocPageBySlug(hash);
        if (page) {
          setCurrentDocPage(page);
          setCurrentView('docs');
        }
      }
    };

    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleSelectDocPage = (slug: string) => {
    const cleanSlug = slug.includes('#') ? slug.split('#')[0] : slug;
    const targetAnchor = slug.includes('#') ? slug.split('#')[1] : null;

    if (cleanSlug.startsWith('stdlib') || cleanSlug === 'stdlib-catalog-az') {
      setCurrentView('stdlib');
      window.location.hash = targetAnchor ? `stdlib#${targetAnchor}` : 'stdlib';
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    const page = findDocPageBySlug(cleanSlug);
    if (page) {
      setCurrentDocPage(page);
      setCurrentView('docs');
      window.location.hash = `docs/${cleanSlug}`;

      if (targetAnchor) {
        setTimeout(() => {
          const el = document.getElementById(targetAnchor);
          if (el) {
            el.scrollIntoView({ behavior: 'smooth' });
          }
        }, 100);
      } else {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    }
  };

  const handleToggleComplete = (slug: string) => {
    setCompletedSlugs(prev => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      try {
        localStorage.setItem('velo_docs_completed', JSON.stringify(Array.from(next)));
      } catch {
        // ignore
      }
      return next;
    });
  };

  const handleNavigate = (view: 'home' | 'docs' | 'playground' | 'stdlib' | 'architecture') => {
    setCurrentView(view);
    window.location.hash = view;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#090b10] text-slate-100 font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Header */}
      <Header
        currentView={currentView}
        onNavigate={handleNavigate}
        onOpenSearch={() => setIsSearchOpen(true)}
        isDark={isDark}
        onToggleTheme={toggleTheme}
        onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
      />

      {/* Main Page Content */}
      <div className="flex-1">
        {currentView === 'home' && (
          <HomePage
            onNavigate={handleNavigate}
            onSelectDocPage={handleSelectDocPage}
          />
        )}

        {currentView === 'docs' && (
          <DocsPage
            categories={DOC_CATEGORIES}
            currentPage={currentDocPage}
            onSelectPage={handleSelectDocPage}
            completedSlugs={completedSlugs}
            onToggleComplete={handleToggleComplete}
            isMobileSidebarOpen={isMobileMenuOpen}
            onCloseMobileSidebar={() => setIsMobileMenuOpen(false)}
          />
        )}

        {currentView === 'playground' && <PlaygroundPage />}

        {currentView === 'stdlib' && <StdlibPage />}

        {currentView === 'architecture' && <ArchitecturePage />}
      </div>

      {/* Search Modal */}
      <SearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onSelectResult={handleSelectDocPage}
      />

      {/* Footer */}
      <Footer
        onNavigate={handleNavigate}
        onSelectDocPage={handleSelectDocPage}
      />
    </div>
  );
}

export default App;
