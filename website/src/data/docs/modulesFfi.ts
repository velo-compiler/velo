import { DocCategory } from '../../types/docs';

export const MODULES_FFI_CATEGORY: DocCategory = {
  id: 'modules-ffi',
  name: '10. Modules, Packages & C Interop',
  description: 'Multi-file compilation, package manifests (velo pkg), and zero-overhead C FFI interoperability.',
  iconName: 'Package',
  pages: [
    {
      id: 'modules-packages',
      slug: 'modules-packages',
      title: 'Packages & Dependency Management (velo pkg)',
      category: '10. Modules, Packages & C Interop',
      categoryOrder: 10,
      order: 1,
      description: 'Create, build, and manage multi-file libraries and applications using velo pkg and velo.toml.',
      readTimeMinutes: 5,
      whatYoullLearn: [
        'The velo pkg CLI tool',
        'Configuring velo.toml package manifests',
        'Managing local and Git dependencies',
        'Building library archives'
      ],
      sections: [
        {
          id: 'velo-toml',
          title: 'The velo.toml Package Manifest',
          content: `Velo projects can be configured with a \`velo.toml\` manifest:

\`\`\`toml
[package]
name = "my_game"
version = "1.0.0"
authors = ["Alice <alice@example.com>"]
entry = "src/main.vl"

[dependencies]
raylib = { git = "https://github.com/raysan5/raylib", branch = "master" }
sqlite = { path = "../libs/sqlite" }

[build]
backend = "gcc"
opt_level = 3
flags = ["-lraylib", "-lopengl32", "-lgdi32", "-lwinmm"]
\`\`\``
        },
        {
          id: 'pkg-commands',
          title: 'velo pkg Subcommands',
          content: `- \`velo pkg new <name>\`: Scaffolds a new Velo project with source tree and manifest.
- \`velo pkg build\`: Builds the project according to \`velo.toml\` settings.
- \`velo pkg test\`: Runs all tests within the package.`
        }
      ],
      prevPage: { title: '128-Bit SIMD Acceleration', slug: 'hardware-simd' },
      nextPage: { title: 'Foreign Function Interface (extern)', slug: 'c-interop-ffi' }
    },
    {
      id: 'c-interop-ffi',
      slug: 'c-interop-ffi',
      title: 'Foreign Function Interface (extern)',
      category: '10. Modules, Packages & C Interop',
      categoryOrder: 10,
      order: 2,
      description: 'Directly call any existing standard C library or OS API with zero glue code and zero overhead.',
      readTimeMinutes: 6,
      badge: 'C Interop',
      whatYoullLearn: [
        'The extern act declaration syntax',
        'Passing pointers and primitive values across the C boundary',
        'Calling Raylib, OpenGL, SQLite, and Win32 APIs',
        'Linking external C libraries (-l flags)'
      ],
      sections: [
        {
          id: 'extern-syntax',
          title: 'Declaring Foreign Functions',
          content: `Because Velo compiles to C99, **calling C functions incurs zero overhead and requires zero glue code**. You declare external C signatures using \`extern act\`:`,
          codeExamples: [
            {
              title: 'c_ffi.vl',
              language: 'velo',
              code: `use std.io

// 1. Declare standard C runtime functions:
extern act puts(s: string) -> i32
extern act sqrtf(val: f32) -> f32
extern act rand() -> i32

// 2. Declare Raylib window creation functions:
extern act InitWindow(width: i32, height: i32, title: string)
extern act WindowShouldClose() -> bool
extern act CloseWindow()

act main() {
    let r = rand()
    io.println("Random number from C: {r}")

    let root = sqrtf(144.0)
    io.println("Square root from C: {root}")
}`
            }
          ]
        },
        {
          id: 'linking',
          title: 'Compiling with External C Libraries',
          content: `Pass the linker flags directly to \`velo build\`:

\`\`\`bash
# Link Raylib and Windows graphics libraries:
velo build game.vl -o game.exe -lraylib -lopengl32 -lgdi32 -lwinmm
\`\`\``
        }
      ],
      prevPage: { title: 'Packages & Dependency Management', slug: 'modules-packages' },
      nextPage: { title: 'Standard Library Architecture', slug: 'stdlib-overview' }
    }
  ]
};

