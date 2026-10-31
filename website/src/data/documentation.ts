import { DocCategory, DocPage } from '../types/docs';
import { INTRO_CATEGORY } from './docs/intro';
import { GETTING_STARTED_CATEGORY } from './docs/gettingStarted';
import { FUNDAMENTALS_CATEGORY } from './docs/fundamentals';
import { CONTROL_FLOW_CATEGORY } from './docs/controlFlow';
import { FUNCTIONS_CATEGORY } from './docs/functions';
import { TYPES_MODELING_CATEGORY } from './docs/typesModeling';
import { MEMORY_CATEGORY } from './docs/memory';
import { COLLECTIONS_CATEGORY } from './docs/collections';
import { SIMD_CATEGORY } from './docs/simd';
import { MODULES_FFI_CATEGORY } from './docs/modulesFfi';
import { STDLIB_DOCS_CATEGORY } from './docs/stdlibDocs';
import { TOOLING_CATEGORY } from './docs/tooling';
import { CASE_STUDIES_CATEGORY } from './docs/caseStudies';
import { REFERENCE_CATEGORY } from './docs/reference';

export const DOC_CATEGORIES: DocCategory[] = [
  INTRO_CATEGORY,
  GETTING_STARTED_CATEGORY,
  FUNDAMENTALS_CATEGORY,
  CONTROL_FLOW_CATEGORY,
  FUNCTIONS_CATEGORY,
  TYPES_MODELING_CATEGORY,
  MEMORY_CATEGORY,
  COLLECTIONS_CATEGORY,
  SIMD_CATEGORY,
  MODULES_FFI_CATEGORY,
  STDLIB_DOCS_CATEGORY,
  TOOLING_CATEGORY,
  CASE_STUDIES_CATEGORY,
  REFERENCE_CATEGORY,
];

export const ALL_DOC_PAGES: DocPage[] = DOC_CATEGORIES.flatMap(cat => cat.pages);

export function findDocPageBySlug(slug: string): DocPage | undefined {
  return ALL_DOC_PAGES.find(p => p.slug === slug || p.id === slug);
}

export function getInitialDocPage(): DocPage {
  return ALL_DOC_PAGES[0];
}

