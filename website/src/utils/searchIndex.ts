import { SearchResult } from '../types/docs';
import { ALL_DOC_PAGES } from '../data/documentation';
import { STDLIB_MODULES } from '../data/stdlib';

export function searchDocumentation(query: string): SearchResult[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];

  const results: SearchResult[] = [];
  const seenKeys = new Set<string>();

  // 1. Search documentation pages & sections
  for (const page of ALL_DOC_PAGES) {
    const pageTitleMatch = page.title.toLowerCase().includes(q);
    const pageDescMatch = page.description.toLowerCase().includes(q);
    const categoryMatch = page.category.toLowerCase().includes(q);

    if (pageTitleMatch || pageDescMatch || categoryMatch) {
      const key = `${page.slug}-title`;
      if (!seenKeys.has(key)) {
        seenKeys.add(key);
        results.push({
          pageId: page.id,
          slug: page.slug,
          pageTitle: page.title,
          category: page.category,
          snippet: page.description,
          type: page.category.includes('Reference') ? 'reference' : 'guide'
        });
      }
    }

    // Search inside sections
    for (const section of page.sections) {
      const sectionTitleMatch = section.title.toLowerCase().includes(q);
      const contentMatch = section.content.toLowerCase().includes(q);

      if (sectionTitleMatch || contentMatch) {
        const key = `${page.slug}-${section.id}`;
        if (!seenKeys.has(key)) {
          seenKeys.add(key);

          // Extract excerpt around match
          let snippet = section.content.slice(0, 140) + '...';
          const matchIdx = section.content.toLowerCase().indexOf(q);
          if (matchIdx !== -1) {
            const start = Math.max(0, matchIdx - 40);
            const end = Math.min(section.content.length, matchIdx + 80);
            snippet = (start > 0 ? '...' : '') + section.content.slice(start, end).replace(/[#*`_]/g, '') + '...';
          }

          results.push({
            pageId: page.id,
            slug: `${page.slug}#${section.id}`,
            pageTitle: page.title,
            category: page.category,
            sectionId: section.id,
            sectionTitle: section.title,
            snippet,
            type: section.title.toLowerCase().includes('syntax') ? 'syntax' : 'guide'
          });
        }
      }
    }
  }

  // 2. Search standard library APIs
  for (const mod of STDLIB_MODULES) {
    if (mod.name.toLowerCase().includes(q) || mod.description.toLowerCase().includes(q)) {
      const key = `stdlib-${mod.name}`;
      if (!seenKeys.has(key)) {
        seenKeys.add(key);
        results.push({
          pageId: 'stdlib-catalog-az',
          slug: `stdlib-catalog-az#${mod.name}`,
          pageTitle: `${mod.name} (Module)`,
          category: 'Standard Library',
          sectionTitle: mod.name,
          snippet: mod.description,
          type: 'api'
        });
      }
    }

    for (const fn of mod.functions) {
      if (fn.name.toLowerCase().includes(q) || fn.description.toLowerCase().includes(q) || fn.signature.toLowerCase().includes(q)) {
        const key = `stdlib-fn-${fn.name}`;
        if (!seenKeys.has(key)) {
          seenKeys.add(key);
          results.push({
            pageId: 'stdlib-catalog-az',
            slug: `stdlib-catalog-az#${mod.name}`,
            pageTitle: fn.name,
            category: `${mod.name} API`,
            sectionTitle: fn.signature,
            snippet: fn.description,
            type: 'api'
          });
        }
      }
    }
  }

  // Limit results to top 15 matches
  return results.slice(0, 15);
}

