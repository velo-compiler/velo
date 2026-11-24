/**
 * High-performance, accurate syntax highlighter for the Velo programming language (.vl)
 */

export interface Token {
  type: 'keyword' | 'type' | 'function' | 'string' | 'number' | 'comment' | 'operator' | 'pointer' | 'macro' | 'interp' | 'text' | 'punct';
  value: string;
}

const KEYWORDS = new Set([
  'act', 'data', 'kind', 'aka', 'mut', 'let', 'if', 'else', 'loop', 'in',
  'return', 'zone', 'extern', 'defer', 'use', 'true', 'false', 'null',
  'sizeof', 'as', 'break', 'continue', 'on', 'and', 'or', 'not', 'op',
  'test', 'assert'
]);

const BUILTIN_TYPES = new Set([
  'i8', 'i16', 'i32', 'i64',
  'u8', 'u16', 'u32', 'u64',
  'f32', 'f64', 'bool',
  'usize', 'isize', 'string', 'void',
  'shelf', 'map', 'ring', 'bitset',
  'f32x4', 'i32x4'
]);

export function tokenizeVelo(code: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;
  const len = code.length;

  while (i < len) {
    const char = code[i];

    // 1. Single line comment
    if (char === '/' && code[i + 1] === '/') {
      let start = i;
      while (i < len && code[i] !== '\n') {
        i++;
      }
      tokens.push({ type: 'comment', value: code.slice(start, i) });
      continue;
    }

    // 2. Block comment
    if (char === '/' && code[i + 1] === '*') {
      let start = i;
      i += 2;
      while (i < len && !(code[i] === '*' && code[i + 1] === '/')) {
        i++;
      }
      if (i < len) i += 2;
      tokens.push({ type: 'comment', value: code.slice(start, i) });
      continue;
    }

    // 3. String literal with interpolation handling
    if (char === '"') {
      i++; // skip opening quote
      tokens.push({ type: 'string', value: '"' });
      
      let strStart = i;
      while (i < len && code[i] !== '"' && code[i] !== '\n') {
        if (code[i] === '\\' && i + 1 < len) {
          i += 2;
          continue;
        }
        if (code[i] === '{') {
          // Push preceding string part
          if (i > strStart) {
            tokens.push({ type: 'string', value: code.slice(strStart, i) });
          }
          // Highlight interpolation expression
          let braceDepth = 1;
          i++; // skip '{'
          tokens.push({ type: 'operator', value: '{' });
          
          let exprStart = i;
          while (i < len && braceDepth > 0) {
            if (code[i] === '{') braceDepth++;
            else if (code[i] === '}') {
              braceDepth--;
              if (braceDepth === 0) break;
            }
            i++;
          }
          
          const exprCode = code.slice(exprStart, i);
          const subTokens = tokenizeVelo(exprCode);
          tokens.push(...subTokens);
          
          if (i < len && code[i] === '}') {
            tokens.push({ type: 'operator', value: '}' });
            i++;
          }
          strStart = i;
          continue;
        }
        i++;
      }

      if (i > strStart) {
        tokens.push({ type: 'string', value: code.slice(strStart, i) });
      }

      if (i < len && code[i] === '"') {
        tokens.push({ type: 'string', value: '"' });
        i++;
      }
      continue;
    }

    // 4. Raw string literal (`)
    if (char === '`') {
      let start = i;
      i++;
      while (i < len && code[i] !== '`') {
        i++;
      }
      if (i < len) i++;
      tokens.push({ type: 'string', value: code.slice(start, i) });
      continue;
    }

    // 5. Attributes (#align, #packed)
    if (char === '#') {
      let start = i;
      i++;
      while (i < len && /[a-zA-Z0-9_]/.test(code[i])) {
        i++;
      }
      tokens.push({ type: 'macro', value: code.slice(start, i) });
      continue;
    }

    // 6. Pointer symbol (@)
    if (char === '@') {
      tokens.push({ type: 'pointer', value: '@' });
      i++;
      continue;
    }

    // 7. Numbers (hex, binary, float, int with _)
    if (/[0-9]/.test(char) || (char === '.' && /[0-9]/.test(code[i + 1] || ''))) {
      let start = i;
      if (char === '0' && (code[i + 1] === 'x' || code[i + 1] === 'X')) {
        i += 2;
        while (i < len && /[0-9a-fA-F_]/.test(code[i])) i++;
      } else if (char === '0' && (code[i + 1] === 'b' || code[i + 1] === 'B')) {
        i += 2;
        while (i < len && /[01_]/.test(code[i])) i++;
      } else if (char === '0' && (code[i + 1] === 'o' || code[i + 1] === 'O')) {
        i += 2;
        while (i < len && /[0-7_]/.test(code[i])) i++;
      } else {
        while (i < len && /[0-9_]/.test(code[i])) i++;
        if (code[i] === '.' && code[i + 1] !== '.' && /[0-9]/.test(code[i + 1] || '')) {
          i++; // decimal point
          while (i < len && /[0-9_]/.test(code[i])) i++;
        }
      }
      tokens.push({ type: 'number', value: code.slice(start, i) });
      continue;
    }

    // 8. Identifiers and Keywords
    if (/[a-zA-Z_]/.test(char)) {
      let start = i;
      while (i < len && /[a-zA-Z0-9_]/.test(code[i])) {
        i++;
      }
      const word = code.slice(start, i);

      // Check if function call (followed by '(')
      let nextIdx = i;
      while (nextIdx < len && (code[nextIdx] === ' ' || code[nextIdx] === '\t')) nextIdx++;
      const isCall = code[nextIdx] === '(';

      if (KEYWORDS.has(word)) {
        tokens.push({ type: 'keyword', value: word });
      } else if (BUILTIN_TYPES.has(word)) {
        tokens.push({ type: 'type', value: word });
      } else if (isCall) {
        tokens.push({ type: 'function', value: word });
      } else if (word[0] === word[0].toUpperCase() && /[a-z]/.test(word)) {
        // Likely a user-defined struct/kind type
        tokens.push({ type: 'type', value: word });
      } else {
        tokens.push({ type: 'text', value: word });
      }
      continue;
    }

    // 9. Multi-character Operators
    const twoChars = code.slice(i, i + 2);
    const threeChars = code.slice(i, i + 3);

    if (threeChars === '..=') {
      tokens.push({ type: 'operator', value: '..=' });
      i += 3;
      continue;
    }

    if (['->', '=>', '..', '==', '!=', '<=', '>=', '+=', '-=', '*=', '/=', '&&', '||', '<<', '>>'].includes(twoChars)) {
      tokens.push({ type: 'operator', value: twoChars });
      i += 2;
      continue;
    }

    // 10. Single character operators and punctuation
    if (['+', '-', '*', '/', '%', '=', '<', '>', '!', '&', '|', '^', '~', ':'].includes(char)) {
      tokens.push({ type: 'operator', value: char });
      i++;
      continue;
    }

    if (['{', '}', '(', ')', '[', ']', '.', ',', ';'].includes(char)) {
      tokens.push({ type: 'punct', value: char });
      i++;
      continue;
    }

    // Whitespace and other characters
    tokens.push({ type: 'text', value: char });
    i++;
  }

  return tokens;
}

export function highlightVeloHtml(code: string): string {
  const tokens = tokenizeVelo(code);
  return tokens.map(tok => {
    const escaped = tok.value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    switch (tok.type) {
      case 'keyword':
        return `<span class="tok-kw">${escaped}</span>`;
      case 'type':
        return `<span class="tok-type">${escaped}</span>`;
      case 'function':
        return `<span class="tok-fn">${escaped}</span>`;
      case 'string':
        return `<span class="tok-str">${escaped}</span>`;
      case 'number':
        return `<span class="tok-num">${escaped}</span>`;
      case 'comment':
        return `<span class="tok-comment">${escaped}</span>`;
      case 'operator':
        return `<span class="tok-op">${escaped}</span>`;
      case 'pointer':
        return `<span class="tok-ptr">${escaped}</span>`;
      case 'macro':
        return `<span class="tok-macro">${escaped}</span>`;
      case 'punct':
        return `<span class="text-slate-400">${escaped}</span>`;
      default:
        return escaped;
    }
  }).join('');
}

