import { DocCategory } from '../../types/docs';

export const TOOLING_CATEGORY: DocCategory = {
  id: 'tooling',
  name: '12. Tooling, IDE & Debugging',
  description: 'Native Language Server Protocol (velo lsp), VS Code setup, test runners, and source-level debugging.',
  iconName: 'Wrench',
  pages: [
    {
      id: 'tooling-lsp',
      slug: 'tooling-lsp',
      title: 'Built-in LSP Server (velo lsp)',
      category: '12. Tooling, IDE & Debugging',
      categoryOrder: 12,
      order: 1,
      description: 'The native JSON-RPC 2.0 language server embedded directly within the compiler binary.',
      readTimeMinutes: 5,
      badge: 'Tooling',
      whatYoullLearn: [
        'How the embedded velo lsp server works',
        'Features: as-you-type diagnostics, markdown hovers, go-to-definition, document symbols',
        'Configuring VS Code and the Antigravity IDE',
        'Zero-disk-I/O in-memory document parsing in under 5ms'
      ],
      sections: [
        {
          id: 'native-lsp',
          title: 'Embedded Language Server',
          content: `Unlike languages that require separate LSP daemon installations, **the Velo compiler binary includes a full Language Server Protocol (LSP 3.17) server natively**:

\`\`\`bash
# Launch the language server via stdio:
velo lsp
\`\`\`

The server maintains an in-memory document cache (\`doc_store.vl\`) and responds to queries in sub-5ms:
- **As-You-Type Diagnostics**: Red squiggles appear immediately as you edit.
- **Rich Markdown Hovers**: Hovering over functions, structs, or variables shows full signatures and origin links.
- **Go-To-Definition (\`F12\`)**: Jump directly to definitions across your project and standard library.
- **Document Symbols**: Breadcrumbs and outline navigation for structs, acts, and enums.`
        },
        {
          id: 'vscode-setup',
          title: 'VS Code Extension Setup',
          content: `Install the official Velo extension in \`editors/vscode/\`:
1. Open Visual Studio Code.
2. The extension automatically detects \`bin/velo.exe\` on your PATH and connects to \`velo lsp\`.
3. Enjoy full syntax highlighting, autocompletion, error diagnostics, and hover documentation.`
        }
      ],
      prevPage: { title: 'Standard Library A–Z Catalog', slug: 'stdlib-catalog-az' },
      nextPage: { title: 'Testing & Source Debugging', slug: 'tooling-testing-debugging' }
    },
    {
      id: 'tooling-testing-debugging',
      slug: 'tooling-testing-debugging',
      title: 'Testing & Source Debugging',
      category: '12. Tooling, IDE & Debugging',
      categoryOrder: 12,
      order: 2,
      description: 'Run native tests with velo test and step through .vl source code with GDB or Visual Studio using #line directives.',
      readTimeMinutes: 6,
      whatYoullLearn: [
        'Native assertions with assert(condition, message)',
        'Running test suites with velo test',
        'Source-level debugging with GDB and Visual Studio using #line directives',
        'Compiling in debug mode with --debug'
      ],
      sections: [
        {
          id: 'native-tests',
          title: 'The Integrated Test Runner',
          content: `Velo embeds testing into the toolchain. You write assertions using \`assert\`:`,
          codeExamples: [
            {
              title: 'tests.vl',
              language: 'velo',
              code: `use std.io

act add(a: i32, b: i32) -> i32 { return a + b }

act main() -> i32 {
    let result = add(20, 22)
    assert(result == 42, "add(20, 22) must equal 42")
    io.println("All tests passed!")
    return 0
}`
            }
          ]
        },
        {
          id: 'debugging-line',
          title: 'Source-Level Debugging with #line Directives',
          content: `When you build with the \`--debug\` flag:

\`\`\`bash
velo build main.vl --debug -o game.exe
\`\`\`

The Velo compiler emits C preprocessor **\`#line\` directives** mapping each C line back to its original \`.vl\` file and line number. 

When you open \`game.exe\` in **Visual Studio Debugger, CLion, or GDB**, you set breakpoints and step directly through your original \`.vl\` source code — not the generated C code!`
        },
        {
          id: 'canonical-formatter',
          title: 'Canonical Code Formatting (velo fmt)',
          content: `Velo ships with an integrated canonical code formatter to ensure zero debates over code style:

\`\`\`bash
# Format a specific source file in place:
velo fmt src/main.vl

# Format an entire project directory recursively:
velo fmt src/

# Verify formatting in CI without modifying files (exits 1 if unformatted):
velo fmt --check src/
\`\`\`

### Formatter Standards
- **Indentation**: 4 spaces per nesting level (tabs rejected).
- **Operators**: Consistent binary spacing around operators (\`a + b\`, \`x == y\`).
- **Control Structures**: Canonical brace placement and keyword spacing.
- **Purity**: Idempotent and deterministic across all platforms.`
        }
      ],
      prevPage: { title: 'Built-in LSP Server (velo lsp)', slug: 'tooling-lsp' },
      nextPage: { title: 'Case Study: VeloKV', slug: 'case-study-velokv' }
    }
  ]
};

