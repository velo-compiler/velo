// Verification script for Velo documentation website
import { DOC_CATEGORIES, ALL_DOC_PAGES, findDocPageBySlug } from '../src/data/documentation.ts';
import { STDLIB_MODULES } from '../src/data/stdlib.ts';
import { PLAYGROUND_PRESETS } from '../src/data/playgroundPresets.ts';
import { searchDocumentation } from '../src/utils/searchIndex.ts';

console.log("=== Verifying Velo Documentation Website Integrity ===");

let errors = 0;

// 1. Verify Page Count & Slugs
console.log(`Checking ${ALL_DOC_PAGES.length} documentation pages across ${DOC_CATEGORIES.length} categories...`);
const slugSet = new Set();
for (const page of ALL_DOC_PAGES) {
  if (slugSet.has(page.slug)) {
    console.error(`ERROR: Duplicate slug detected: "${page.slug}"`);
    errors++;
  }
  slugSet.add(page.slug);

  // Check prevPage
  if (page.prevPage) {
    const prev = findDocPageBySlug(page.prevPage.slug);
    if (!prev) {
      console.error(`ERROR: Broken prevPage slug "${page.prevPage.slug}" in page "${page.title}"`);
      errors++;
    }
  }

  // Check nextPage
  if (page.nextPage) {
    const next = findDocPageBySlug(page.nextPage.slug);
    if (!next) {
      console.error(`ERROR: Broken nextPage slug "${page.nextPage.slug}" in page "${page.title}"`);
      errors++;
    }
  }

  // Check sections
  if (!page.sections || page.sections.length === 0) {
    console.error(`ERROR: Page "${page.title}" has no sections!`);
    errors++;
  }
}

// 2. Verify Stdlib Modules
console.log(`Checking ${STDLIB_MODULES.length} standard library modules...`);
const modSet = new Set();
for (const mod of STDLIB_MODULES) {
  if (modSet.has(mod.name)) {
    console.error(`ERROR: Duplicate stdlib module "${mod.name}"`);
    errors++;
  }
  modSet.add(mod.name);
  if (!mod.functions || mod.functions.length === 0) {
    console.error(`ERROR: Stdlib module "${mod.name}" has no functions!`);
    errors++;
  }
}

// 3. Verify Playground Presets
console.log(`Checking ${PLAYGROUND_PRESETS.length} playground presets...`);
for (const p of PLAYGROUND_PRESETS) {
  if (!p.code || !p.expectedOutput) {
    console.error(`ERROR: Preset "${p.title}" missing code or expected output`);
    errors++;
  }
}

// 4. Test Search Engine
console.log("Testing search engine...");
const testQueries = ['zone', 'pointer', 'shelf', 'simd', 'kind', 'fmt.int_to_str', 'install', 'redis'];
for (const q of testQueries) {
  const results = searchDocumentation(q);
  if (results.length === 0) {
    console.error(`ERROR: Search query "${q}" returned 0 results!`);
    errors++;
  } else {
    console.log(`  ✓ Search "${q}" -> ${results.length} results`);
  }
}

if (errors === 0) {
  console.log("\n✅ ALL VERIFICATION CHECKS PASSED: 0 errors detected!");
  process.exit(0);
} else {
  console.error(`\n❌ FAILED with ${errors} errors.`);
  process.exit(1);
}

