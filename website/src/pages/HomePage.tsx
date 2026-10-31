import React, { useState } from 'react';
import { 
  Zap, 
  ArrowRight, 
  Terminal, 
  BookOpen, 
  ShieldCheck, 
  Layers, 
  Cpu, 
  CheckCircle2, 
  Copy, 
  Check, 
  Activity,
  Box,
  Compass,
  Code2
} from 'lucide-react';
import { CodeBlock } from '../components/CodeBlock';

interface HomePageProps {
  onNavigate: (view: 'home' | 'docs' | 'playground' | 'stdlib' | 'architecture') => void;
  onSelectDocPage: (slug: string) => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onNavigate, onSelectDocPage }) => {
  const [copiedInstall, setCopiedInstall] = useState(false);
  const [activeCodeTab, setActiveCodeTab] = useState<'zone' | 'particle' | 'simd' | 'ufcs'>('zone');

  const copyInstallCommand = () => {
    navigator.clipboard.writeText('git clone https://github.com/velo-lang/velo.git && cd velo && scripts\\bootstrap.bat');
    setCopiedInstall(true);
    setTimeout(() => setCopiedInstall(false), 2000);
  };

  const codeSnippets = {
    zone: {
      title: 'zone_arena.vl',
      description: 'Allocate thousands of structs on a contiguous 16MB arena with 1-CPU-cycle reset upon exit.',
      code: `use std.io
use std.mem

data Matrix {
    m: [16]f32
}

act main() {
    io.println("Arena used before: {mem.used()} bytes")

    // Hardware zone arena:
    zone {
        // Bump allocates 500 matrices (32 KB) in O(1) time:
        matrices: @Matrix = mem.alloc(@Matrix, 500)

        io.println("Arena used inside: {mem.used()} bytes")
        // High-velocity matrix transformations...
    } // Wiped in 1 instruction here!

    io.println("Arena used after: {mem.used()} bytes (100% reset!)")
}`,
      output: `Arena used before: 0 bytes
Arena used inside: 32000 bytes
Arena used after: 0 bytes (100% reset!)`
    },
    particle: {
      title: 'particle_sim.vl',
      description: 'Game physics with the @ pointer system and flat C-ABI structs.',
      code: `use std.io

data Vec2 { x: f32, y: f32 }

data Particle {
    pos: Vec2
    vel: Vec2
    active: bool
}

act update(p: @Particle, dt: f32) {
    if !p.active { return }
    p.pos.x += p.vel.x * dt // Auto-dereference member access
    p.pos.y += p.vel.y * dt
}

act main() {
    mut pt = Particle{ pos: Vec2{ x: 0.0, y: 0.0 }, vel: Vec2{ x: 5.0, y: 10.0 }, active: true }
    update(@pt, 0.016)
    io.println("Particle pos: ({pt.pos.x}, {pt.pos.y})")
}`,
      output: `Particle pos: (0.080000, 0.160000)`
    },
    simd: {
      title: 'hardware_simd.vl',
      description: '128-bit SIMD hardware vector arithmetic (f32x4) compiling to SSE/AVX.',
      code: `use std.io
use std.simd

act main() -> i32 {
    let a = f32x4(1.0, 2.0, 3.0, 4.0)
    let b = f32x4(10.0, 20.0, 30.0, 40.0)

    // Hardware dot product in 1 instruction: 10 + 40 + 90 + 160 = 300.0
    let dot = simd.dot(a, b)
    io.println("SIMD Dot Product: {dot}")

    let squares = f32x4(4.0, 9.0, 16.0, 25.0)
    let roots = simd.sqrt(squares)
    io.println("SIMD Sqrt: ({roots.x}, {roots.y}, {roots.z}, {roots.w})")
    return 0
}`,
      output: `SIMD Dot Product: 300.000000
SIMD Sqrt: (2.000000, 3.000000, 4.000000, 5.000000)`
    },
    ufcs: {
      title: 'ufcs_operator.vl',
      description: 'Method syntax (UFCS) and operator overloading for game math.',
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

    // Overloaded + operator:
    let next_pos = pos + vel
    io.println("Next position: ({next_pos.x}, {next_pos.y})")

    // UFCS method call with auto-borrow:
    pos.scale(2.0)
    io.println("Scaled pos: ({pos.x}, {pos.y})")
}`,
      output: `Next position: (12.000000, 24.000000)
Scaled pos: (20.000000, 40.000000)`
    }
  };

  return (
    <div className="space-y-24 py-12">
      {/* 1. HERO SECTION */}
      <section className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-8">
        {/* Glow ambient background */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none -z-10" />

        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 text-xs font-mono">
          <Zap className="w-3.5 h-3.5 text-cyan-400 fill-cyan-400" />
          <span>Velo v2.0 Released: 100% Self-Hosted Gen3 Native Toolchain</span>
          <ArrowRight className="w-3 h-3 text-cyan-400" />
        </div>

        {/* Hero Title */}
        <div className="space-y-4 max-w-4xl mx-auto">
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white font-sans leading-[1.1]">
            Code at <span className="bg-gradient-to-r from-cyan-400 via-sky-300 to-blue-500 bg-clip-text text-transparent">high velocity.</span>
          </h1>
          <p className="text-lg sm:text-2xl text-slate-300 max-w-3xl mx-auto font-normal leading-relaxed">
            The raw speed and hardware control of <span className="text-cyan-300 font-semibold">C</span>, with modern syntax as clean as <span className="text-cyan-300 font-semibold">TypeScript</span>, and <span className="text-cyan-300 font-semibold">zero garbage collection pauses</span>.
          </p>
        </div>

        {/* CTAs & Terminal Copy */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
          <button
            onClick={() => {
              onNavigate('docs');
              onSelectDocPage('getting-started-install');
            }}
            className="w-full sm:w-auto px-7 py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-sm shadow-lg shadow-cyan-500/25 flex items-center justify-center gap-2 transition-all hover:scale-[1.02]"
          >
            <BookOpen className="w-4 h-4" />
            <span>Start Learning Velo</span>
            <ArrowRight className="w-4 h-4" />
          </button>

          <button
            onClick={() => onNavigate('playground')}
            className="w-full sm:w-auto px-7 py-3.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-slate-200 font-semibold text-sm border border-slate-700/80 flex items-center justify-center gap-2 transition-all hover:scale-[1.02]"
          >
            <Terminal className="w-4 h-4 text-emerald-400" />
            <span>Interactive Playground</span>
          </button>
        </div>

        {/* Quick Install Banner */}
        <div className="max-w-xl mx-auto pt-4">
          <div className="flex items-center justify-between px-4 py-3 bg-[#111620] border border-slate-800 rounded-xl font-mono text-xs text-slate-300 shadow-inner">
            <span className="flex items-center gap-2 truncate">
              <span className="text-cyan-400 select-none">$</span>
              <span className="truncate">git clone https://github.com/velo-lang/velo && scripts\bootstrap.bat</span>
            </span>
            <button
              onClick={copyInstallCommand}
              title="Copy install command"
              className="p-1.5 ml-2 hover:bg-slate-800 rounded text-slate-400 hover:text-slate-200 shrink-0 transition-colors"
            >
              {copiedInstall ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </section>

      {/* 2. INTERACTIVE CODE SHOWCASE */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center space-y-3 mb-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-white font-sans">
            Authentic Systems Semantics in Action
          </h2>
          <p className="text-slate-400 text-sm max-w-2xl mx-auto">
            Explore how Velo solves real systems problems: zero-GC arena blocks, clean pointers, hardware SIMD registers, and operator overloading.
          </p>

          {/* Code Tab Switcher */}
          <div className="flex flex-wrap items-center justify-center gap-2 pt-4">
            <button
              onClick={() => setActiveCodeTab('zone')}
              className={`px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                activeCodeTab === 'zone'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                  : 'bg-slate-800/60 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              1-Cycle Zone Arenas
            </button>
            <button
              onClick={() => setActiveCodeTab('particle')}
              className={`px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                activeCodeTab === 'particle'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                  : 'bg-slate-800/60 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              The @ Pointer System
            </button>
            <button
              onClick={() => setActiveCodeTab('simd')}
              className={`px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                activeCodeTab === 'simd'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                  : 'bg-slate-800/60 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              128-Bit SIMD Math
            </button>
            <button
              onClick={() => setActiveCodeTab('ufcs')}
              className={`px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                activeCodeTab === 'ufcs'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                  : 'bg-slate-800/60 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              UFCS & Operator Overloading
            </button>
          </div>
        </div>

        {/* Selected Code Example */}
        <div className="space-y-2">
          <p className="text-xs text-slate-400 font-sans text-center">
            {codeSnippets[activeCodeTab].description}
          </p>
          <CodeBlock
            title={codeSnippets[activeCodeTab].title}
            code={codeSnippets[activeCodeTab].code}
            output={codeSnippets[activeCodeTab].output}
          />
        </div>
      </section>

      {/* 3. SIX PILLARS OF VELO */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="text-center space-y-3">
          <h2 className="text-2xl sm:text-3xl font-bold text-white font-sans">
            Engineered for Bare-Metal Performance
          </h2>
          <p className="text-slate-400 text-sm max-w-2xl mx-auto">
            Every architectural decision in Velo guarantees speed, predictability, and safety without runtime bloat.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Card 1 */}
          <div className="p-6 rounded-2xl bg-[#0D1117] border border-slate-800/80 hover:border-cyan-500/30 transition-all space-y-3 group">
            <div className="w-10 h-10 rounded-xl bg-cyan-950/80 border border-cyan-500/30 flex items-center justify-center text-cyan-400 group-hover:scale-105 transition-transform">
              <Zap className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-white font-sans">
              Zero GC Stutter (120+ FPS)
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              No background garbage collection threads or stop-the-world pauses. Lexical <code className="text-cyan-300">zone</code> arenas allocate in 1-2 CPU cycles and wipe memory in a single instruction.
            </p>
          </div>

          {/* Card 2 */}
          <div className="p-6 rounded-2xl bg-[#0D1117] border border-slate-800/80 hover:border-cyan-500/30 transition-all space-y-3 group">
            <div className="w-10 h-10 rounded-xl bg-blue-950/80 border border-blue-500/30 flex items-center justify-center text-blue-400 group-hover:scale-105 transition-transform">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-white font-sans">
              Bit-for-Bit Determinism
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              The 3-generation self-hosting bootstrap pipeline guarantees that Gen 2 and Gen 3 produce identical SHA-256 hashes, eliminating compiler Heisenbugs mathematically.
            </p>
          </div>

          {/* Card 3 */}
          <div className="p-6 rounded-2xl bg-[#0D1117] border border-slate-800/80 hover:border-cyan-500/30 transition-all space-y-3 group">
            <div className="w-10 h-10 rounded-xl bg-emerald-950/80 border border-emerald-500/30 flex items-center justify-center text-emerald-400 group-hover:scale-105 transition-transform">
              <Cpu className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-white font-sans">
              128-Bit SIMD Acceleration
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Direct language support for <code className="text-emerald-300">f32x4</code> and <code className="text-emerald-300">i32x4</code> vector registers. Compiles to hardware SSE, AVX, and NEON instructions for 4x math throughput.
            </p>
          </div>

          {/* Card 4 */}
          <div className="p-6 rounded-2xl bg-[#0D1117] border border-slate-800/80 hover:border-cyan-500/30 transition-all space-y-3 group">
            <div className="w-10 h-10 rounded-xl bg-purple-950/80 border border-purple-500/30 flex items-center justify-center text-purple-400 group-hover:scale-105 transition-transform">
              <Box className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-white font-sans">
              Pure Velo Stdlib (Zero Libc)
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              127 pure-Velo modules with zero dependency on libc. Memory, formatting, strings, I/O, and JSON are written in pure Velo, reducing OS reliance to minimal syscall boundaries.
            </p>
          </div>

          {/* Card 5 */}
          <div className="p-6 rounded-2xl bg-[#0D1117] border border-slate-800/80 hover:border-cyan-500/30 transition-all space-y-3 group">
            <div className="w-10 h-10 rounded-xl bg-amber-950/80 border border-amber-500/30 flex items-center justify-center text-amber-400 group-hover:scale-105 transition-transform">
              <Activity className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-white font-sans">
              Native Embedded LSP 3.17
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              The native compiler binary embeds a full JSON-RPC 2.0 language server (<code className="text-amber-300">velo lsp</code>). Enjoy instant hover tooltips, go-to-definition, and diagnostics in under 5ms.
            </p>
          </div>

          {/* Card 6 */}
          <div className="p-6 rounded-2xl bg-[#0D1117] border border-slate-800/80 hover:border-cyan-500/30 transition-all space-y-3 group">
            <div className="w-10 h-10 rounded-xl bg-rose-950/80 border border-rose-500/30 flex items-center justify-center text-rose-400 group-hover:scale-105 transition-transform">
              <Code2 className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-white font-sans">
              400-Line Code Standards
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Every compiler source file is capped at 400 lines of code. This strict modularity rule enforces clean separation of concerns and eliminates monolithic code rot.
            </p>
          </div>
        </div>
      </section>

      {/* 4. REAL-WORLD PRODUCTION SHOWCASE */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="text-center space-y-3">
          <h2 className="text-2xl sm:text-3xl font-bold text-white font-sans">
            Battle-Tested in Real Projects
          </h2>
          <p className="text-slate-400 text-sm max-w-2xl mx-auto">
            Velo is already powering production database engines, desktop GUI applications, and real-time games.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* App 1: VeloKV */}
          <div className="p-6 rounded-2xl bg-[#0D1117] border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/50">
                Database Engine
              </span>
              <span className="text-xs text-slate-500">apps/velokv/</span>
            </div>
            <h3 className="text-lg font-bold text-white font-sans">
              VeloKV
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              A high-performance in-memory Redis-compatible database server with RESP protocol parsing, multi-client network TCP loop, and Append-Only File (AOF) disk persistence.
            </p>
            <button
              onClick={() => {
                onNavigate('docs');
                onSelectDocPage('case-study-velokv');
              }}
              className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1 transition-colors"
            >
              <span>Read Architecture Case Study</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* App 2: VeloStudio */}
          <div className="p-6 rounded-2xl bg-[#0D1117] border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-purple-950 text-purple-400 border border-purple-800/50">
                Desktop GUI
              </span>
              <span className="text-xs text-slate-500">apps/velostudio/</span>
            </div>
            <h3 className="text-lg font-bold text-white font-sans">
              VeloStudio
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              A cross-platform desktop SQLite database explorer built with Velo and Raylib bindings. Features tabular data visualization, SQL queries, modal dialogs, and a theme engine.
            </p>
            <button
              onClick={() => {
                onNavigate('docs');
                onSelectDocPage('case-study-velostudio');
              }}
              className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1 transition-colors"
            >
              <span>Read Architecture Case Study</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* App 3: Velocraft & Games */}
          <div className="p-6 rounded-2xl bg-[#0D1117] border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800/50">
                120 FPS Games
              </span>
              <span className="text-xs text-slate-500">games/</span>
            </div>
            <h3 className="text-lg font-bold text-white font-sans">
              Velocraft & Raylib Games
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              A collection of real-time 2D and 3D games (Velocraft voxel engine, Survivors, Flappy Bird) verifying 120+ FPS frame stability with zero GC stutter.
            </p>
            <button
              onClick={() => {
                onNavigate('docs');
                onSelectDocPage('case-study-gamedev');
              }}
              className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1 transition-colors"
            >
              <span>Explore Game Dev Tutorial</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </section>

      {/* 5. LEARNING CURRICULUM PREVIEW */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 bg-[#0D1117] border border-slate-800 rounded-3xl p-8 sm:p-12 space-y-8">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-xl">
            <h2 className="text-2xl sm:text-3xl font-bold text-white font-sans">
              Master Velo in Four Clear Steps
            </h2>
            <p className="text-slate-400 text-sm">
              From your first program to building a 120 FPS game engine or network microservice.
            </p>
          </div>
          <button
            onClick={() => {
              onNavigate('docs');
              onSelectDocPage('getting-started-install');
            }}
            className="px-6 py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs uppercase tracking-wider flex items-center gap-2 transition-all shrink-0"
          >
            <span>Begin Step 1</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4.5 rounded-xl bg-[#161B22] border border-slate-800 space-y-2">
            <span className="text-xs font-mono text-cyan-400 font-bold">Step 01</span>
            <h4 className="text-sm font-bold text-white">Fundamentals</h4>
            <p className="text-xs text-slate-400">Install Velo, write Hello World, and master variables, types, and loops.</p>
          </div>
          <div className="p-4.5 rounded-xl bg-[#161B22] border border-slate-800 space-y-2">
            <span className="text-xs font-mono text-cyan-400 font-bold">Step 02</span>
            <h4 className="text-sm font-bold text-white">Memory & Pointers</h4>
            <p className="text-xs text-slate-400">Master the @ pointer system, lexical zone arenas, and defer cleanup.</p>
          </div>
          <div className="p-4.5 rounded-xl bg-[#161B22] border border-slate-800 space-y-2">
            <span className="text-xs font-mono text-cyan-400 font-bold">Step 03</span>
            <h4 className="text-sm font-bold text-white">Data & Methods</h4>
            <p className="text-xs text-slate-400">Model types with data and kind, parametric generics, and UFCS methods.</p>
          </div>
          <div className="p-4.5 rounded-xl bg-[#161B22] border border-slate-800 space-y-2">
            <span className="text-xs font-mono text-cyan-400 font-bold">Step 04</span>
            <h4 className="text-sm font-bold text-white">Real-World Projects</h4>
            <p className="text-xs text-slate-400">Build high-throughput network stores, Raylib GUI tools, and SIMD math.</p>
          </div>
        </div>
      </section>
    </div>
  );
};

