import React, { useState } from 'react';
import { 
  ArrowRight, 
  Terminal, 
  BookOpen, 
  ShieldCheck, 
  Cpu, 
  Copy, 
  Check, 
  Layers, 
  Box, 
  Code2,
  Database,
  Monitor,
  Gamepad2
} from 'lucide-react';
import { CodeBlock } from '../components/CodeBlock';

interface HomePageProps {
  onNavigate: (view: 'home' | 'docs' | 'playground' | 'stdlib' | 'architecture') => void;
  onSelectDocPage: (slug: string) => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onNavigate, onSelectDocPage }) => {
  const [copiedInstall, setCopiedInstall] = useState(false);
  const [installTab, setInstallTab] = useState<'powershell' | 'bash' | 'source'>('powershell');
  const [activeCodeTab, setActiveCodeTab] = useState<'zone' | 'particle' | 'simd' | 'ufcs'>('zone');

  const origin = typeof window !== 'undefined' && window.location.origin ? window.location.origin : 'http://localhost:5173';
  const isLocalhost = origin.includes('localhost') || origin.includes('127.0.0.1');

  const installCommands = {
    powershell: isLocalhost 
      ? `irm ${origin}/install.ps1 | iex` 
      : `$env:VELO_INSTALL_URL='${origin}'; irm ${origin}/install.ps1 | iex`,
    bash: isLocalhost
      ? `curl -fsSL ${origin}/install.sh | bash`
      : `VELO_INSTALL_URL='${origin}' curl -fsSL ${origin}/install.sh | bash`,
    source: 'git clone https://github.com/velo-compiler/velo.git && cd velo && scripts\\bootstrap.bat'
  };

  const copyInstallCommand = () => {
    navigator.clipboard.writeText(installCommands[installTab]);
    setCopiedInstall(true);
    setTimeout(() => setCopiedInstall(false), 2000);
  };

  const codeSnippets = {
    zone: {
      title: 'zone_arena.vl',
      description: 'Lexical zone arena allocating contiguous memory with instantaneous O(1) bulk reset on exit.',
      code: `use std.io
use std.mem

data Matrix {
    m: [16]f32
}

act main() {
    io.println("Arena baseline: {mem.used()} bytes")

    // Lexical zone arena:
    zone {
        // Bump-allocates 500 matrices (32 KB) in contiguous cache lines:
        let matrices: @Matrix = mem.alloc(@Matrix, 500)
        io.println("Inside zone: {mem.used()} bytes allocated")
        
        // High-throughput numerical transformations...
    } // Wiped in 1 instruction here! Zero GC pauses.

    io.println("After zone: {mem.used()} bytes (instant O(1) reset)")
}`,
      output: `Arena baseline: 0 bytes
Inside zone: 32000 bytes allocated
After zone: 0 bytes (instant O(1) reset)`
    },
    particle: {
      title: 'particle_sim.vl',
      description: 'Explicit @ pointer model with automatic dereferencing and flat C-ABI structs.',
      code: `use std.io

data Vec2 { x: f32, y: f32 }

data Particle {
    pos: Vec2
    vel: Vec2
    active: bool
}

act update(p: @Particle, dt: f32) {
    if !p.active { return }
    p.pos.x += p.vel.x * dt // Safe auto-dereference member access
    p.pos.y += p.vel.y * dt
}

act main() {
    mut pt = Particle{ pos: Vec2{ x: 0.0, y: 0.0 }, vel: Vec2{ x: 5.0, y: 10.0 }, active: true }
    update(@pt, 0.016)
    io.println("Particle position: ({pt.pos.x}, {pt.pos.y})")
}`,
      output: `Particle position: (0.080000, 0.160000)`
    },
    simd: {
      title: 'hardware_simd.vl',
      description: '128-bit hardware vector registers compiling directly to SSE, AVX, and NEON intrinsics.',
      code: `use std.io
use std.simd

act main() -> i32 {
    let a = f32x4(1.0, 2.0, 3.0, 4.0)
    let b = f32x4(10.0, 20.0, 30.0, 40.0)

    // Hardware dot product in 1 instruction: 10 + 40 + 90 + 160 = 300.0
    let dot = simd.dot(a, b)
    io.println("SIMD dot product: {dot}")

    let squares = f32x4(4.0, 9.0, 16.0, 25.0)
    let roots = simd.sqrt(squares)
    io.println("SIMD square roots: ({roots.x}, {roots.y}, {roots.z}, {roots.w})")
    return 0
}`,
      output: `SIMD dot product: 300.000000
SIMD square roots: (2.000000, 3.000000, 4.000000, 5.000000)`
    },
    ufcs: {
      title: 'ufcs_operator.vl',
      description: 'Unified function call syntax (UFCS) and operator overloading with zero runtime overhead.',
      code: `use std.io

data Vector2 { x: f32, y: f32 }

act op +(a: Vector2, b: Vector2) -> Vector2 {
    return Vector2{ x: a.x + b.x, y: a.y + b.y }
}

act scale(v: @Vector2, factor: f32) {
    v.x *= factor
    v.y *= factor
}

act main() {
    mut pos = Vector2{ x: 10.0, y: 20.0 }
    let vel = Vector2{ x: 2.0, y: 4.0 }

    let next_pos = pos + vel
    io.println("Combined position: ({next_pos.x}, {next_pos.y})")

    // UFCS method syntax with automatic address-of:
    pos.scale(2.0)
    io.println("Scaled position: ({pos.x}, {pos.y})")
}`,
      output: `Combined position: (12.000000, 24.000000)
Scaled position: (20.000000, 40.000000)`
    }
  };

  return (
    <div className="space-y-24 py-12 sm:py-16">
      {/* 1. ASYMMETRIC HERO SECTION */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-start">
          
          {/* Left Column: Proposition, CTAs & Install */}
          <div className="lg:col-span-6 space-y-6">
            
            {/* Version Notice */}
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded text-xs font-mono text-zinc-400 bg-white/[0.04] border border-white/[0.08]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span>Version 2.0.0-pre</span>
              <span className="text-zinc-600">•</span>
              <span>100% self-hosted native compiler</span>
            </div>

            {/* Headline */}
            <div className="space-y-3">
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-medium tracking-tight text-[#eef0f6] leading-[1.08]">
                Deterministic systems programming.
                <span className="block text-zinc-400 mt-1">Zero garbage collection.</span>
              </h1>
              <p className="text-base sm:text-lg text-zinc-400 leading-relaxed max-w-xl">
                Velo combines the hardware control and raw execution speed of C with expressive modern syntax. It compiles to clean C99 with SIMD vector intrinsics and lexical zone arenas.
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center gap-3 pt-1">
              <button
                onClick={() => {
                  onNavigate('docs');
                  onSelectDocPage('getting-started-install');
                }}
                className="px-5 py-2.5 rounded-md bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 flex items-center justify-center gap-2 transition-colors cursor-pointer"
              >
                <span>Read documentation</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={() => onNavigate('playground')}
                className="px-5 py-2.5 rounded-md bg-white/[0.04] hover:bg-white/[0.08] text-zinc-200 font-medium text-xs border border-white/[0.08] flex items-center justify-center gap-2 transition-colors cursor-pointer"
              >
                <Terminal className="w-3.5 h-3.5 text-zinc-400" />
                <span>Interactive playground</span>
              </button>
            </div>

            {/* Quick Install Terminal Box */}
            <div className="pt-2 space-y-2">
              <div className="flex items-center gap-1.5 text-xs">
                <button
                  onClick={() => setInstallTab('powershell')}
                  className={`px-2.5 py-1 rounded text-xs transition-colors cursor-pointer ${
                    installTab === 'powershell'
                      ? 'bg-white/[0.08] text-white border border-white/[0.12] font-medium'
                      : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  Windows
                </button>
                <button
                  onClick={() => setInstallTab('bash')}
                  className={`px-2.5 py-1 rounded text-xs transition-colors cursor-pointer ${
                    installTab === 'bash'
                      ? 'bg-white/[0.08] text-white border border-white/[0.12] font-medium'
                      : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  macOS / Linux
                </button>
                <button
                  onClick={() => setInstallTab('source')}
                  className={`px-2.5 py-1 rounded text-xs transition-colors cursor-pointer ${
                    installTab === 'source'
                      ? 'bg-white/[0.08] text-white border border-white/[0.12] font-medium'
                      : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  Source bootstrap
                </button>
              </div>

              <div className="flex items-center justify-between px-3.5 py-2.5 bg-[#0c0e14] border border-white/[0.08] rounded-md font-mono text-xs text-zinc-300">
                <span className="flex items-center gap-2 truncate">
                  <span className="text-zinc-500 select-none">$</span>
                  <span className="truncate">{installCommands[installTab]}</span>
                </span>
                <button
                  onClick={copyInstallCommand}
                  title="Copy command"
                  className="p-1 ml-2 text-zinc-400 hover:text-zinc-200 rounded transition-colors shrink-0 cursor-pointer"
                >
                  {copiedInstall ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            {/* Core Metrics Strip */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-white/[0.06] text-xs">
              <div>
                <div className="font-mono text-sm text-zinc-100 font-medium">0 ms</div>
                <div className="text-zinc-500 text-[11px] mt-0.5">GC pauses</div>
              </div>
              <div>
                <div className="font-mono text-sm text-zinc-100 font-medium">SHA-256</div>
                <div className="text-zinc-500 text-[11px] mt-0.5">Bit-identical builds</div>
              </div>
              <div>
                <div className="font-mono text-sm text-zinc-100 font-medium">127</div>
                <div className="text-zinc-500 text-[11px] mt-0.5">Stdlib modules</div>
              </div>
            </div>
          </div>

          {/* Right Column: Code Showcase */}
          <div className="lg:col-span-6 space-y-3">
            {/* Code Tab Switcher */}
            <div className="flex flex-wrap items-center gap-1 text-xs">
              <button
                onClick={() => setActiveCodeTab('zone')}
                className={`px-3 py-1.5 rounded-md text-xs transition-colors cursor-pointer ${
                  activeCodeTab === 'zone'
                    ? 'bg-white/[0.08] text-white border border-white/[0.12] font-medium'
                    : 'text-zinc-400 hover:text-zinc-200 bg-white/[0.02] border border-transparent'
                }`}
              >
                Zone arenas
              </button>
              <button
                onClick={() => setActiveCodeTab('particle')}
                className={`px-3 py-1.5 rounded-md text-xs transition-colors cursor-pointer ${
                  activeCodeTab === 'particle'
                    ? 'bg-white/[0.08] text-white border border-white/[0.12] font-medium'
                    : 'text-zinc-400 hover:text-zinc-200 bg-white/[0.02] border border-transparent'
                }`}
              >
                @ pointers
              </button>
              <button
                onClick={() => setActiveCodeTab('simd')}
                className={`px-3 py-1.5 rounded-md text-xs transition-colors cursor-pointer ${
                  activeCodeTab === 'simd'
                    ? 'bg-white/[0.08] text-white border border-white/[0.12] font-medium'
                    : 'text-zinc-400 hover:text-zinc-200 bg-white/[0.02] border border-transparent'
                }`}
              >
                128-bit SIMD
              </button>
              <button
                onClick={() => setActiveCodeTab('ufcs')}
                className={`px-3 py-1.5 rounded-md text-xs transition-colors cursor-pointer ${
                  activeCodeTab === 'ufcs'
                    ? 'bg-white/[0.08] text-white border border-white/[0.12] font-medium'
                    : 'text-zinc-400 hover:text-zinc-200 bg-white/[0.02] border border-transparent'
                }`}
              >
                UFCS & operators
              </button>
            </div>

            <div className="space-y-1.5">
              <p className="text-xs text-zinc-400">
                {codeSnippets[activeCodeTab].description}
              </p>
              <CodeBlock
                title={codeSnippets[activeCodeTab].title}
                code={codeSnippets[activeCodeTab].code}
                output={codeSnippets[activeCodeTab].output}
              />
            </div>
          </div>
        </div>
      </section>

      {/* 2. ARCHITECTURAL PILLARS */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="space-y-1">
          <h2 className="text-xl sm:text-2xl font-medium text-zinc-100 font-sans tracking-tight">
            Engineered for predictable bare-metal execution
          </h2>
          <p className="text-zinc-400 text-xs sm:text-sm max-w-2xl">
            Every architectural decision eliminates hidden runtime overhead, stops stop-the-world pauses, and ensures deterministic outputs.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {/* Pillar 1 */}
          <div className="p-5 rounded-xl bg-[#0f121a] border border-white/[0.08] hover:border-white/[0.16] transition-colors space-y-3">
            <div className="w-8 h-8 rounded-md bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-zinc-300">
              <Box className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-medium text-zinc-100 font-sans">
              Lexical zone memory (zero-cycle reset)
            </h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              No garbage collection threads or runtime background sweepers. Scoped <code className="text-zinc-300 font-mono text-[11px]">zone</code> blocks bump-allocate in 1-2 CPU cycles and restore memory pointers in a single instruction.
            </p>
          </div>

          {/* Pillar 2 */}
          <div className="p-5 rounded-xl bg-[#0f121a] border border-white/[0.08] hover:border-white/[0.16] transition-colors space-y-3">
            <div className="w-8 h-8 rounded-md bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-zinc-300">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-medium text-zinc-100 font-sans">
              Bit-for-bit compiler determinism
            </h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              The 3-generation self-hosting pipeline enforces identical SHA-256 binary outputs between Gen 2 and Gen 3 compilers, eliminating build nondeterminism at compilation time.
            </p>
          </div>

          {/* Pillar 3 */}
          <div className="p-5 rounded-xl bg-[#0f121a] border border-white/[0.08] hover:border-white/[0.16] transition-colors space-y-3">
            <div className="w-8 h-8 rounded-md bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-zinc-300">
              <Cpu className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-medium text-zinc-100 font-sans">
              128-bit hardware SIMD vectors
            </h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Direct language support for <code className="text-zinc-300 font-mono text-[11px]">f32x4</code> and <code className="text-zinc-300 font-mono text-[11px]">i32x4</code> vector types compiling to SSE, AVX, and NEON instructions for parallel numerical math.
            </p>
          </div>

          {/* Pillar 4 */}
          <div className="p-5 rounded-xl bg-[#0f121a] border border-white/[0.08] hover:border-white/[0.16] transition-colors space-y-3">
            <div className="w-8 h-8 rounded-md bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-zinc-300">
              <Layers className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-medium text-zinc-100 font-sans">
              Pure Velo standard library
            </h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              127 pure-Velo modules with zero libc dependency. Collections, serialization, cryptographic hashing, and networking interface directly with clean platform primitives.
            </p>
          </div>

          {/* Pillar 5 */}
          <div className="p-5 rounded-xl bg-[#0f121a] border border-white/[0.08] hover:border-white/[0.16] transition-colors space-y-3">
            <div className="w-8 h-8 rounded-md bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-zinc-300">
              <Code2 className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-medium text-zinc-100 font-sans">
              Embedded language server protocol
            </h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              The self-hosted compiler embeds a full LSP 3.17 server (<code className="text-zinc-300 font-mono text-[11px]">velo lsp</code>). Get instant hover inspections, go-to-definition, and sub-millisecond diagnostics.
            </p>
          </div>

          {/* Pillar 6 */}
          <div className="p-5 rounded-xl bg-[#0f121a] border border-white/[0.08] hover:border-white/[0.16] transition-colors space-y-3">
            <div className="w-8 h-8 rounded-md bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-zinc-300">
              <Terminal className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-medium text-zinc-100 font-sans">
              Strict 400-line code ceiling
            </h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Every compiler source file is capped at 400 lines of code. This strict modularity rule enforces clean separation of concerns and eliminates monolithic code rot.
            </p>
          </div>
        </div>
      </section>

      {/* 3. PRODUCTION CASE STUDIES */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="space-y-1">
          <h2 className="text-xl sm:text-2xl font-medium text-zinc-100 font-sans tracking-tight">
            Production application case studies
          </h2>
          <p className="text-zinc-400 text-xs sm:text-sm max-w-2xl">
            Real implementations proving Velo's memory model and speed across database engines, desktop GUI applications, and real-time graphics.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* App 1: VeloKV */}
          <div className="p-5 rounded-xl bg-[#0f121a] border border-white/[0.08] hover:border-white/[0.16] transition-colors space-y-3.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono px-2 py-0.5 rounded text-zinc-300 bg-white/[0.04] border border-white/[0.08]">
                Database engine
              </span>
              <span className="text-[11px] font-mono text-zinc-500">apps/velokv/</span>
            </div>
            <h3 className="text-sm font-medium text-zinc-100 font-sans">
              VeloKV in-memory database
            </h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              A high-throughput Redis-compatible in-memory store with binary protocol parsing, TCP multi-client event polling, and append-only file persistence.
            </p>
            <button
              onClick={() => {
                onNavigate('docs');
                onSelectDocPage('case-study-velokv');
              }}
              className="text-xs text-zinc-200 hover:text-white font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <span>Read architectural breakdown</span>
              <ArrowRight className="w-3.5 h-3.5 text-zinc-400" />
            </button>
          </div>

          {/* App 2: VeloStudio */}
          <div className="p-5 rounded-xl bg-[#0f121a] border border-white/[0.08] hover:border-white/[0.16] transition-colors space-y-3.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono px-2 py-0.5 rounded text-zinc-300 bg-white/[0.04] border border-white/[0.08]">
                Desktop application
              </span>
              <span className="text-[11px] font-mono text-zinc-500">apps/velostudio/</span>
            </div>
            <h3 className="text-sm font-medium text-zinc-100 font-sans">
              VeloStudio SQLite explorer
            </h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              A cross-platform database workbench with native Raylib windowing, tabular grid rendering, query execution, and transactional schema inspection.
            </p>
            <button
              onClick={() => {
                onNavigate('docs');
                onSelectDocPage('case-study-velostudio');
              }}
              className="text-xs text-zinc-200 hover:text-white font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <span>Read architectural breakdown</span>
              <ArrowRight className="w-3.5 h-3.5 text-zinc-400" />
            </button>
          </div>

          {/* App 3: Velocraft & Games */}
          <div className="p-5 rounded-xl bg-[#0f121a] border border-white/[0.08] hover:border-white/[0.16] transition-colors space-y-3.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono px-2 py-0.5 rounded text-zinc-300 bg-white/[0.04] border border-white/[0.08]">
                Real-time graphics
              </span>
              <span className="text-[11px] font-mono text-zinc-500">games/</span>
            </div>
            <h3 className="text-sm font-medium text-zinc-100 font-sans">
              Velocraft 3D voxel engine
            </h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Real-time procedural mesh generation, 3D camera controls, and particle physics demonstrating consistent 120 FPS frame timing with zero GC spikes.
            </p>
            <button
              onClick={() => {
                onNavigate('docs');
                onSelectDocPage('case-study-gamedev');
              }}
              className="text-xs text-zinc-200 hover:text-white font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <span>Explore game dev tutorial</span>
              <ArrowRight className="w-3.5 h-3.5 text-zinc-400" />
            </button>
          </div>
        </div>
      </section>

      {/* 4. LEARNING PATH */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="p-6 sm:p-10 rounded-xl bg-[#0c0e14] border border-white/[0.08] space-y-8">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="space-y-1 max-w-xl">
              <h2 className="text-xl sm:text-2xl font-medium text-zinc-100 font-sans tracking-tight">
                Step-by-step developer guide
              </h2>
              <p className="text-zinc-400 text-xs sm:text-sm">
                Follow the four-stage progression from your first binary to building high-concurrency systems and Raylib graphics.
              </p>
            </div>
            <button
              onClick={() => {
                onNavigate('docs');
                onSelectDocPage('getting-started-install');
              }}
              className="px-4 py-2 rounded-md bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 flex items-center gap-1.5 transition-colors shrink-0 cursor-pointer"
            >
              <span>Start step 1</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg bg-[#0f121a] border border-white/[0.06] space-y-1.5">
              <span className="text-[11px] font-mono text-zinc-500">Step 01</span>
              <h4 className="text-xs font-medium text-zinc-200">Fundamentals</h4>
              <p className="text-xs text-zinc-400 leading-relaxed">Compiler installation, basic grammar, static typing, and control flow.</p>
            </div>
            <div className="p-4 rounded-lg bg-[#0f121a] border border-white/[0.06] space-y-1.5">
              <span className="text-[11px] font-mono text-zinc-500">Step 02</span>
              <h4 className="text-xs font-medium text-zinc-200">Memory & pointers</h4>
              <p className="text-xs text-zinc-400 leading-relaxed">The @ pointer system, lexical zone arenas, and deterministic defer blocks.</p>
            </div>
            <div className="p-4 rounded-lg bg-[#0f121a] border border-white/[0.06] space-y-1.5">
              <span className="text-[11px] font-mono text-zinc-500">Step 03</span>
              <h4 className="text-xs font-medium text-zinc-200">Data & methods</h4>
              <p className="text-xs text-zinc-400 leading-relaxed">Struct definitions, sum types (kind), generic pacts, and UFCS syntax.</p>
            </div>
            <div className="p-4 rounded-lg bg-[#0f121a] border border-white/[0.06] space-y-1.5">
              <span className="text-[11px] font-mono text-zinc-500">Step 04</span>
              <h4 className="text-xs font-medium text-zinc-200">Production systems</h4>
              <p className="text-xs text-zinc-400 leading-relaxed">Async networking loops, hardware SIMD math, and C99 FFI bindings.</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
