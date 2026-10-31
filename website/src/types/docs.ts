export interface DocHeading {
  id: string;
  text: string;
  level: number;
}

export interface CodeExample {
  title?: string;
  code: string;
  output?: string;
  cCode?: string;
  language?: string;
}

export interface DocSection {
  id: string;
  title: string;
  content: string; // Markdown / HTML text
  codeExamples?: CodeExample[];
  callout?: {
    type: 'note' | 'tip' | 'important' | 'warning' | 'caution';
    title?: string;
    text: string;
  };
  table?: {
    headers: string[];
    rows: string[][];
  };
}

export interface DocPage {
  id: string;
  slug: string;
  title: string;
  category: string;
  categoryOrder: number;
  order: number;
  description: string;
  readTimeMinutes: number;
  badge?: string;
  whatYoullLearn: string[];
  sections: DocSection[];
  prevPage?: { title: string; slug: string };
  nextPage?: { title: string; slug: string };
  relatedPages?: { title: string; slug: string }[];
}

export interface DocCategory {
  id: string;
  name: string;
  description: string;
  iconName: string;
  pages: DocPage[];
}

export interface SearchResult {
  pageId: string;
  slug: string;
  pageTitle: string;
  category: string;
  sectionId?: string;
  sectionTitle?: string;
  snippet: string;
  type: 'guide' | 'syntax' | 'api' | 'tutorial' | 'reference';
}

export interface StdlibModule {
  name: string;
  category: string;
  tier: 1 | 2;
  description: string;
  pureVelo: boolean;
  loc?: number;
  functions: {
    name: string;
    signature: string;
    description: string;
    example?: string;
  }[];
  types?: {
    name: string;
    definition: string;
    description: string;
  }[];
}

export interface PlaygroundPreset {
  id: string;
  title: string;
  category: string;
  description: string;
  code: string;
  expectedOutput: string;
  cEquivalent: string;
}

