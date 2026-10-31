import { DocCategory } from '../../types/docs';

export const GETTING_STARTED_CATEGORY: DocCategory = {
  id: 'getting-started',
  name: '02. Getting Started',
  description: 'Install Velo, compile your first program, master the CLI, and structure projects.',
  iconName: 'PlayCircle',
  pages: [
    {
      id: 'getting-started-install',
      slug: 'getting-started-install',
      title: 'Installation & Toolchain Setup',
      category: '02. Getting Started',
      categoryOrder: 2,
      order: 1,
      description: 'Set up your development environment on Windows, Linux, or macOS with GCC or MSVC.',
      readTimeMinutes: 5,
      whatYoullLearn: [
        'Prerequisites for compiling Velo',
        'Configuring GCC (MSYS2 UCRT64) or MSVC (cl.exe)',
        'Bootstrapping the compiler from the C snapshot',
        'Verifying your installation'
      ],
      sections: [
        {
          id: 'prerequisites',
          title: 'Prerequisites',
          content: `Because Velo compiles directly to standard C99, all you need is a C compiler:

- **Windows**:
  - **GCC (Recommended)**: MSYS2 with UCRT64 toolchain (\`C:\\msys64\\ucrt64\\bin\` in \`PATH\`).
  - **MSVC**: Visual Studio 2019/2022 or Build Tools with \`cl.exe\`.
- **Linux**: GCC or Clang (\`sudo apt install build-essential\` or \`pacman -S gcc\`).
- **macOS**: Apple Clang via Xcode Command Line Tools (\`xcode-select --install\`).`
        },
        {
          id: 'bootstrap-chain',
          title: 'Bootstrapping Velo',
          content: `Velo ships with a canonical single-file C snapshot: \`bootstrap.c\`. You do not need Python or any external compiler to build Velo from scratch.

To build the native standalone compiler binary (\`bin/velo.exe\`):

\`\`\`bash
# On Windows (PowerShell or CMD):
scripts\\bootstrap.bat

# Or compile bootstrap.c manually with GCC:
gcc -std=c99 -O2 bootstrap.c -o bin/velo.exe

# Or compile with MSVC cl.exe:
cl /nologo /O2 /TC bootstrap.c /Fe:bin/velo.exe
\`\`\`

The bootstrap batch script verifies compiler self-hosting by compiling \`src/main.vl\` through Gen 2 and Gen 3 and validating bit-for-bit SHA-256 determinism.`,
          callout: {
            type: 'tip',
            title: 'Single-Binary Portability',
            text: 'Once built, bin/velo.exe is completely standalone. It requires no runtime libraries, no Python interpreter, and no registry keys.'
          }
        },
        {
          id: 'verify-install',
          title: 'Verify Your Installation',
          content: `Run the version command in your terminal to verify that Velo is active:

\`\`\`bash
bin\\velo.exe version
\`\`\`

Expected output:
\`\`\`
Velo Systems Language v2.0 (Self-Hosted Gen3 Native Toolchain)
Target: x86_64-pc-windows-gcc | C99 Native Backend
\`\`\``
        }
      ],
      prevPage: { title: 'Language Comparison', slug: 'intro-comparison' },
      nextPage: { title: 'Your First Program', slug: 'getting-started-first-program' }
    },
    {
      id: 'getting-started-first-program',
      slug: 'getting-started-first-program',
      title: 'Your First Program',
      category: '02. Getting Started',
      categoryOrder: 2,
      order: 2,
      description: 'Write, compile, run, and inspect the generated C99 code for a classic Hello World application.',
      readTimeMinutes: 4,
      whatYoullLearn: [
        'Anatomy of a Velo source file (.vl)',
        'Importing standard library modules (use std.io)',
        'Defining the main execution entry point (act main)',
        'Running and compiling with the Velo CLI'
      ],
      sections: [
        {
          id: 'writing-code',
          title: '1. Writing the Code',
          content: `Create a new file named \`hello.vl\` in your project directory:`,
          codeExamples: [
            {
              title: 'hello.vl',
              language: 'velo',
              code: `use std.io

act main() {
    io.println("Hello, world from Velo 2.0!")
    io.println("Code at high velocity.")
}`
            }
          ]
        },
        {
          id: 'anatomy',
          title: '2. Code Breakdown',
          content: `- \`use std.io\`: Imports the pure Velo standard I/O module from the standard library.
- \`act main() { ... }\`: Declares the executable entry point. In Velo, routines and functions are declared with the \`act\` keyword.
- \`io.println(...)\`: Prints the string literal followed by a newline directly to the standard output stream.
- Semicolons are **optional**: each newline cleanly terminates a statement.`
        },
        {
          id: 'running-building',
          title: '3. Running & Compiling',
          content: `You can execute the file immediately in one step (transpile + compile + run):

\`\`\`bash
velo run hello.vl
\`\`\`

Or compile it into a permanent standalone executable:

\`\`\`bash
velo build hello.vl -o hello.exe
\`\`\`

Run the generated binary directly:
\`\`\`bash
./hello.exe
\`\`\`

Output:
\`\`\`
Hello, world from Velo 2.0!
Code at high velocity.
\`\`\``
        },
        {
          id: 'inspecting-c',
          title: '4. Inspecting the Generated C99 Code',
          content: `Velo generates clean, human-readable C99 code. You can inspect the emitted translation unit at any time with \`emit-c\`:

\`\`\`bash
velo emit-c hello.vl
\`\`\`

Notice how clean the emitted code is: standard C functions, no obfuscation, and zero runtime overhead.`,
          codeExamples: [
            {
              title: 'Emitted C99 Output',
              language: 'c',
              code: `// Emitted by Velo Self-Hosted Compiler v2.0
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

int main(int argc, char** argv) {
    puts("Hello, world from Velo 2.0!");
    puts("Code at high velocity.");
    return 0;
}`
            }
          ]
        }
      ],
      prevPage: { title: 'Installation & Setup', slug: 'getting-started-install' },
      nextPage: { title: 'CLI Command Reference', slug: 'getting-started-cli' }
    },
    {
      id: 'getting-started-cli',
      slug: 'getting-started-cli',
      title: 'CLI Command Reference',
      category: '02. Getting Started',
      categoryOrder: 2,
      order: 3,
      description: 'Master every command and compiler flag provided by the unified velo CLI driver.',
      readTimeMinutes: 6,
      badge: 'CLI',
      whatYoullLearn: [
        'All primary CLI subcommands (run, build, emit-c, check, test, lsp, pkg)',
        'Switching backends with --cc gcc or --cc cl (MSVC)',
        'Optimizations flags (-O0, -O1, -O2, -O3, --release, --debug)',
        'Machine-readable diagnostics with velo check --json'
      ],
      sections: [
        {
          id: 'commands',
          title: 'Core CLI Commands',
          content: `Both the Stage 1 reference driver and the Stage 2 self-hosted \`velo\` binary expose a consistent command-line interface:`,
          table: {
            headers: ['Command', 'Usage', 'Description'],
            rows: [
              ['velo run', 'velo run <file.vl> [args...]', 'Compiles and immediately executes the program in memory.'],
              ['velo build', 'velo build <file.vl> [-o <out.exe>]', 'Compiles the source to a standalone native executable.'],
              ['velo emit-c', 'velo emit-c <file.vl>', 'Emits the optimized C99 translation unit to stdout.'],
              ['velo check', 'velo check <file.vl> [--json]', 'Validates lexing, parsing, and semantics without code generation.'],
              ['velo test', 'velo test <file.vl>', 'Runs all declared test blocks and assertions.'],
              ['velo lsp', 'velo lsp', 'Launches the embedded JSON-RPC 2.0 Language Server Protocol server.'],
              ['velo pkg', 'velo pkg <new|build|add>', 'Manages packages and project dependencies.'],
              ['velo version', 'velo version', 'Displays version banner, toolchain backend, and build information.']
            ]
          }
        },
        {
          id: 'compiler-flags',
          title: 'Compiler Options & Flags',
          content: `Configure backend compilation and optimization behavior:

- \`--cc <gcc|cl>\`: Selects the C compiler backend. Defaults to \`gcc\`. Use \`--cc cl\` to compile with Microsoft Visual C++ (\`cl.exe\`).
- \`--release\`: Enables full optimization (\`-O3\`), strip symbols, and maximum inlining.
- \`--debug\`: Emits \`#line\` preprocessor directives and debug symbols (\`-g\` / \`/Zi\`) for source-level debugging in Visual Studio and GDB.
- \`-O0\`, \`-O1\`, \`-O2\`, \`-O3\`: Explicit optimization levels passed to the native backend.
- \`-l<lib>\`: Link against native external libraries (e.g. \`-lraylib\`, \`-lopengl32\`, \`-lsqlite3\`).
- \`-L<dir>\`: Add library search path.`
        },
        {
          id: 'check-json',
          title: 'Static Analysis with velo check --json',
          content: `CI systems, linters, and IDE plugins can invoke \`velo check --json\` to receive structured, machine-readable validation reports in JSON format:

\`\`\`json
{
  "file": "app.vl",
  "ok": false,
  "diagnostics": [
    {
      "file": "app.vl",
      "line": 14,
      "col": 5,
      "severity": "error",
      "message": "cannot assign to immutable variable 'score'. Declare with 'mut score' to allow mutation."
    }
  ]
}
\`\`\``
        }
      ],
      prevPage: { title: 'Your First Program', slug: 'getting-started-first-program' },
      nextPage: { title: 'Project Structure & Modules', slug: 'getting-started-project-structure' }
    },
    {
      id: 'getting-started-project-structure',
      slug: 'getting-started-project-structure',
      title: 'Project Structure & Modules',
      category: '02. Getting Started',
      categoryOrder: 2,
      order: 4,
      description: 'Organize multi-file applications with relative imports, include guards, and the standard library.',
      readTimeMinutes: 5,
      whatYoullLearn: [
        'How the multi-file module system works (use "file.vl")',
        'Automatic deduplication and include guards',
        'Grouped import syntax (use std.{mem, fmt, io})',
        'Recommended directory layout for real-world projects'
      ],
      sections: [
        {
          id: 'multi-file-system',
          title: 'Multi-File Imports with use',
          content: `Real-world systems projects are split across multiple modular files. In Velo, files import other files using the \`use\` keyword:

\`\`\`rust
// Relative local file imports:
use "tokens.vl"
use "compiler/lexer.vl"
use "compiler/parser.vl"

// Standard library imports:
use std.io
use std.mem
\`\`\`

### Resolution Rules:
1. **Relative Paths**: Quoted paths (e.g. \`use "math/vec2.vl"\`) are resolved relative to the directory of the file containing the \`use\` statement.
2. **Automatic Deduplication**: The compiler maintains an internal module cache. If \`A.vl\` imports \`common.vl\` and \`B.vl\` also imports \`common.vl\`, the file is parsed and included **only once**.
3. **Global Project Scope**: All top-level structs (\`data\`), tagged unions (\`kind\`), and routines (\`act\`) are placed in the project namespace. No header files or manual forward declarations are ever required.`
        },
        {
          id: 'grouped-imports',
          title: 'Grouped Imports',
          content: `To eliminate vertical import clutter at the top of your files, Velo supports grouped module imports:

\`\`\`rust
use std.{mem, fmt, io, str}
use std.{json, net, time}
\`\`\``
        },
        {
          id: 'recommended-layout',
          title: 'Recommended Project Layout',
          content: `A typical production Velo project follows this clean structure:

\`\`\`
my_project/
├── velo.toml             # Package manifest (name, version, dependencies)
├── src/
│   ├── main.vl           # Primary application entry point (act main)
│   ├── config.vl         # Configuration settings & data structs
│   ├── engine/
│   │   ├── renderer.vl   # Graphics rendering routines
│   │   └── physics.vl    # Physics simulation and math
│   └── util/
│       └── logger.vl     # Logging utilities
└── tests/
    └── test_physics.vl   # Native test suites
\`\`\``
        }
      ],
      prevPage: { title: 'CLI Command Reference', slug: 'getting-started-cli' },
      nextPage: { title: 'Lexical Grammar & Keywords', slug: 'lang-lexical-grammar' }
    }
  ]
};

