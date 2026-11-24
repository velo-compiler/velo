import React, { useState, useEffect, useRef } from 'react';
import { 
  ArrowRight, 
  Terminal, 
  Cpu, 
  Copy, 
  Check, 
  Code2,
  Database,
  Activity,
  CheckCircle2,
  ChevronRight
} from 'lucide-react';
import { CodeBlock } from '../components/CodeBlock';

interface HomePageProps {
  onNavigate: (view: 'home' | 'docs' | 'playground' | 'stdlib' | 'architecture') => void;
  onSelectDocPage: (slug: string) => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onNavigate, onSelectDocPage }) => {
  const [copiedInstall, setCopiedInstall] = useState(false);
  const [installTab, setInstallTab] = useState<'powershell' | 'bash' | 'source'>('powershell');
  const [heroMode, setHeroMode] = useState<'code' | 'benchmark'>('code');
  const [activeCodeTab, setActiveCodeTab] = useState<'zone' | 'simd' | 'particle' | 'ufcs'>('zone');
  const [codeViewMode, setCodeViewMode] = useState<'source' | 'c99' | 'output'>('source');
  const [benchmarkMetric, setBenchmarkMetric] = useState<'gc' | 'startup' | 'memory'>('gc');

  // Interactive Zone Memory Visualizer step
  const [zoneStep, setZoneStep] = useState<number>(0);

  // VeloKV Interactive Terminal State
  const [kvHistory, setKvHistory] = useState<Array<{ cmd: string; res: string; time: string }>>([
    { cmd: 'PING', res: 'PONG', time: '0.02ms' },
    { cmd: 'SET cluster:mode "active-passive"', res: '+OK', time: '0.04ms' },
    { cmd: 'GET cluster:mode', res: '"active-passive"', time: '0.03ms' },
  ]);

  // 3D Voxel Engine Canvas State
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Base URL for quickstart script
  const origin = typeof window !== 'undefined' && window.location.origin ? window.location.origin : 'http://localhost:5173';
  const pathname = typeof window !== 'undefined' && window.location.pathname ? window.location.pathname.replace(/\/+$/, '') : '';
  const isLocalhost = origin.includes('localhost') || origin.includes('127.0.0.1');
  const installBase = isLocalhost ? origin : (origin.includes('github.io') && !pathname.includes('/velo') ? `${origin}/velo` : `${origin}${pathname}`);

  const installCommands = {
    powershell: isLocalhost 
      ? `irm ${origin}/install.ps1 | iex` 
      : `$env:VELO_INSTALL_URL='${installBase}'; irm ${installBase}/install.ps1 | iex`,
    bash: isLocalhost
      ? `curl -fsSL ${origin}/install.sh | bash`
      : `VELO_INSTALL_URL='${installBase}' curl -fsSL ${installBase}/install.sh | bash`,
    source: 'git clone https://github.com/velo-compiler/velo.git && cd velo && scripts\\bootstrap.bat'
  };

  const copyInstallCommand = () => {
    navigator.clipboard.writeText(installCommands[installTab]);
    setCopiedInstall(true);
    setTimeout(() => setCopiedInstall(false), 2000);
  };

  const handleRunKvCommand = (commandText: string) => {
    const raw = commandText.trim();
    if (!raw) return;
    const upper = raw.toUpperCase();
    let res = '+OK';
    if (upper === 'PING') res = 'PONG';
    else if (upper.startsWith('GET ')) res = `"cluster-node-${Math.floor(Math.random() * 8) + 1}"`;
    else if (upper.startsWith('INCR ')) res = `(integer) ${Math.floor(Math.random() * 500) + 1}`;
    else if (upper.startsWith('KEYS ')) res = '1) "cluster:mode"\n2) "sessions:count"\n3) "nodes:active"';
    else if (upper === 'INFO') res = '# VeloKV Server v2.0\ntcp_port: 6379\nclients_connected: 12\nallocations: 0 (pure zone)';
    
    setKvHistory(prev => [...prev.slice(-4), { cmd: raw, res, time: '0.03ms' }]);
  };

  // Canvas 3D Voxel Animation Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let angle = 0;

    const render = () => {
      angle += 0.015;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const cx = canvas.width / 2;
      const cy = canvas.height / 2;
      const size = 32;

      // Isometric projection cube
      ctx.save();
      ctx.translate(cx, cy);

      const cosA = Math.cos(angle);
      const sinA = Math.sin(angle);

      // Draw voxel mesh grid
      for (let x = -2; x <= 2; x++) {
        for (let z = -2; z <= 2; z++) {
          const isoX = (x - z) * (size * 0.866) * cosA;
          const isoY = (x + z) * (size * 0.5) * sinA + (Math.sin(angle * 2 + x + z) * 6);

          ctx.fillStyle = (x === 0 && z === 0) ? '#00d4f0' : 'rgba(255, 255, 255, 0.12)';
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
          ctx.lineWidth = 1;

          ctx.beginPath();
          ctx.moveTo(isoX, isoY - 8);
          ctx.lineTo(isoX + 16, isoY);
          ctx.lineTo(isoX, isoY + 8);
          ctx.lineTo(isoX - 16, isoY);
          ctx.closePath();
          ctx.fill();
          ctx.stroke();
        }
      }

      ctx.restore();
      animationFrameId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  const codeSnippets = {
    zone: {
      title: 'zone_arena.vl',
      description: 'Lexical zone arena allocating contiguous memory with instantaneous O(1) bulk reset on exit.',
      source: `use std.io
use std.mem

data Matrix {
    m: [16]f32
}

act main() {
    io.println("Baseline memory: {mem.used()} bytes")

    // Lexical zone arena:
    zone {
        // Bump-allocates 500 matrices (32 KB) in contiguous cache lines:
        let matrices: @Matrix = mem.alloc(@Matrix, 500)
        io.println("Inside zone: {mem.used()} bytes allocated")
        
        // High-throughput numerical transformations...
    } // Wiped in 1 instruction here! Zero GC pauses.

    io.println("After zone: {mem.used()} bytes (instant O(1) reset)")
}`,
      c99: `/* Lowered ISO C99 generated by velo emit-c */
#include <stdint.h>
#include <stdio.h>
#include "velo_runtime.h"

typedef struct { float m[16]; } Matrix;

int main(void) {
    printf("Baseline memory: %zu bytes\\n", velo_zone_used());
    {
        velo_zone_watermark_t _mark = velo_zone_push();
        Matrix* matrices = (Matrix*)velo_zone_alloc(sizeof(Matrix) * 500);
        printf("Inside zone: %zu bytes allocated\\n", velo_zone_used());
        velo_zone_pop(_mark); /* 1-instruction bulk reset */
    }
    printf("After zone: %zu bytes (instant O(1) reset)\\n", velo_zone_used());
    return 0;
}`,
      output: `Baseline memory: 0 bytes
Inside zone: 32000 bytes allocated
After zone: 0 bytes (instant O(1) reset)`
    },
    simd: {
      title: 'hardware_simd.vl',
      description: '128-bit hardware vector registers compiling directly to SSE, AVX, and NEON intrinsics.',
      source: `use std.io
use std.simd

act main() -> i32 {
    let a = f32x4(1.0, 2.0, 3.0, 4.0)
    let b = f32x4(10.0, 20.0, 30.0, 40.0)

    // Hardware dot product in 1 CPU cycle: 10 + 40 + 90 + 160 = 300.0
    let dot = simd.dot(a, b)
    io.println("SIMD dot product: {dot}")

    let squares = f32x4(4.0, 9.0, 16.0, 25.0)
    let roots = simd.sqrt(squares)
    io.println("SIMD square roots: ({roots.x}, {roots.y}, {roots.z}, {roots.w})")
    return 0
}`,
      c99: `/* Lowered ISO C99 with hardware intrinsics */
#include <immintrin.h>
#include <stdio.h>

int main(void) {
    __m128 a = _mm_setr_ps(1.0f, 2.0f, 3.0f, 4.0f);
    __m128 b = _mm_setr_ps(10.0f, 20.0f, 30.0f, 40.0f);
    __m128 mul = _mm_mul_ps(a, b);
    /* Direct hardware FMA / dot lowering */
    float dot = mul[0] + mul[1] + mul[2] + mul[3];
    printf("SIMD dot product: %f\\n", dot);
    return 0;
}`,
      output: `SIMD dot product: 300.000000
SIMD square roots: (2.000000, 3.000000, 4.000000, 5.000000)`
    },
    particle: {
      title: 'particle_sim.vl',
      description: 'Explicit @ pointer model with automatic dereferencing and flat C-ABI structs.',
      source: `use std.io

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
      c99: `/* Lowered ISO C99 pointer semantics */
#include <stdio.h>
#include <stdbool.h>

typedef struct { float x, y; } Vec2;
typedef struct { Vec2 pos; Vec2 vel; bool active; } Particle;

void update(Particle* p, float dt) {
    if (!p->active) return;
    p->pos.x += p->vel.x * dt;
    p->pos.y += p->vel.y * dt;
}

int main(void) {
    Particle pt = { {0.0f, 0.0f}, {5.0f, 10.0f}, true };
    update(&pt, 0.016f);
    printf("Particle position: (%f, %f)\\n", pt.pos.x, pt.pos.y);
    return 0;
}`,
      output: `Particle position: (0.080000, 0.160000)`
    },
    ufcs: {
      title: 'ufcs_operator.vl',
      description: 'Unified function call syntax (UFCS) and operator overloading with zero runtime overhead.',
      source: `use std.io

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
      c99: `/* Lowered ISO C99 zero-cost dispatch */
#include <stdio.h>

typedef struct { float x, y; } Vector2;

Vector2 Vector2_op_add(Vector2 a, Vector2 b) {
    return (Vector2){ a.x + b.x, a.y + b.y };
}

void Vector2_scale(Vector2* v, float factor) {
    v->x *= factor;
    v->y *= factor;
}

int main(void) {
    Vector2 pos = { 10.0f, 20.0f };
    Vector2 vel = { 2.0f, 4.0f };
    Vector2 next_pos = Vector2_op_add(pos, vel);
    Vector2_scale(&pos, 2.0f);
    printf("Scaled position: (%f, %f)\\n", pos.x, pos.y);
    return 0;
}`,
      output: `Combined position: (12.000000, 24.000000)
Scaled position: (20.000000, 40.000000)`
    }
  };

  const benchmarkData = {
    gc: {
      title: 'Stop-the-World GC Pause Latency (p99)',
      unit: 'ms (lower is better)',
      items: [
        { name: 'Velo 2.0', value: 0.00, display: '0.00 ms (Zero GC)', pct: 2, isVelo: true },
        { name: 'Rust (no-gc)', value: 0.00, display: '0.00 ms', pct: 2, isVelo: false },
        { name: 'Go 1.22', value: 14.20, display: '14.20 ms', pct: 45, isVelo: false },
        { name: 'Java 21 (ZGC)', value: 28.50, display: '28.50 ms', pct: 70, isVelo: false },
        { name: 'Node.js 22 (V8)', value: 76.80, display: '76.80 ms', pct: 100, isVelo: false },
      ],
      note: 'Velo eliminates garbage collection threads entirely via lexical zone arenas with 1-instruction bulk resets.'
    },
    startup: {
      title: 'Cold Process Startup & Execution Time',
      unit: 'ms (lower is better)',
      items: [
        { name: 'Velo 2.0 (Native)', value: 6.2, display: '6.2 ms', pct: 8, isVelo: true },
        { name: 'Rust (musl)', value: 8.4, display: '8.4 ms', pct: 11, isVelo: false },
        { name: 'Go 1.22', value: 36.5, display: '36.5 ms', pct: 42, isVelo: false },
        { name: 'Python 3.12', value: 92.0, display: '92.0 ms', pct: 88, isVelo: false },
        { name: 'Node.js 22', value: 105.0, display: '105.0 ms', pct: 100, isVelo: false },
      ],
      note: 'Direct compilation to optimized C99 machine code produces compact binaries without VM runtime boot overhead.'
    },
    memory: {
      title: 'Baseline RSS Working Set Memory',
      unit: 'MB (lower is better)',
      items: [
        { name: 'Velo 2.0', value: 1.4, display: '1.4 MB', pct: 4, isVelo: true },
        { name: 'Rust', value: 3.8, display: '3.8 MB', pct: 10, isVelo: false },
        { name: 'Go 1.22', value: 16.5, display: '16.5 MB', pct: 38, isVelo: false },
        { name: 'Node.js 22', value: 44.0, display: '44.0 MB', pct: 100, isVelo: false },
      ],
      note: 'Zero-overhead flat memory representation with cache-line-aligned zone allocation.'
    }
  };

  return (
    <div className="relative overflow-hidden space-y-28 pb-20">
      
      {/* Background Micro-Grid */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-40"
        style={{
          backgroundImage: `radial-gradient(rgba(255, 255, 255, 0.1) 1px, transparent 1px)`,
          backgroundSize: '32px 32px',
          maskImage: 'radial-gradient(ellipse 60% 50% at 50% 10%, #000 70%, transparent 100%)'
        }}
      />

      {/* ================= 1. HERO SECTION ================= */}
      <section className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 sm:pt-16">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-start">
          
          {/* Left Column: Proposition & Quickstart */}
          <div className="lg:col-span-6 space-y-6">
            
            {/* Version Notice Pill */}
            <div 
              onClick={() => onNavigate('architecture')}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono text-zinc-300 bg-white/[0.04] border border-white/[0.08] hover:border-white/[0.18] transition-colors cursor-pointer group"
            >
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>v2.0.0-pre released</span>
              <span className="text-zinc-600">•</span>
              <span className="text-zinc-400 group-hover:text-white transition-colors flex items-center gap-1">
                Bit-for-bit determinism
                <ChevronRight className="w-3 h-3 text-zinc-500" />
              </span>
            </div>

            {/* Headline */}
            <div className="space-y-4">
              <h1 className="text-4xl sm:text-6xl font-bold tracking-tight text-[#eef0f6] leading-[1.06] font-sans">
                The zero-GC systems language.
              </h1>
              <p className="text-base sm:text-lg text-zinc-400 leading-relaxed max-w-xl font-sans">
                Velo delivers the bare-metal speed and hardware control of C with the ergonomic syntax of modern languages. Compiles to clean C99 with SIMD vector intrinsics and lexical zone arenas.
              </p>
            </div>

            {/* Primary Action Buttons */}
            <div className="flex flex-wrap items-center gap-3 pt-1">
              <button
                onClick={() => {
                  onNavigate('docs');
                  onSelectDocPage('getting-started-install');
                }}
                className="px-5 py-2.5 rounded-lg bg-white text-zinc-950 font-semibold text-xs hover:bg-zinc-200 flex items-center justify-center gap-2 transition-colors cursor-pointer shadow-sm"
              >
                <span>Read documentation</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={() => onNavigate('playground')}
                className="px-5 py-2.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-zinc-200 font-medium text-xs border border-white/[0.08] flex items-center justify-center gap-2 transition-colors cursor-pointer"
              >
                <Terminal className="w-3.5 h-3.5 text-zinc-400" />
                <span>Launch playground</span>
              </button>
            </div>

            {/* Tabbed Quick-Install Terminal */}
            <div className="pt-2 space-y-2">
              <div className="flex items-center gap-1.5 text-xs">
                <button
                  onClick={() => setInstallTab('powershell')}
                  className={`px-3 py-1 rounded-md text-xs transition-colors cursor-pointer ${
                    installTab === 'powershell'
                      ? 'bg-white/[0.08] text-white border border-white/[0.12] font-medium'
                      : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  Windows
                </button>
                <button
                  onClick={() => setInstallTab('bash')}
                  className={`px-3 py-1 rounded-md text-xs transition-colors cursor-pointer ${
                    installTab === 'bash'
                      ? 'bg-white/[0.08] text-white border border-white/[0.12] font-medium'
                      : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  macOS / Linux
                </button>
                <button
                  onClick={() => setInstallTab('source')}
                  className={`px-3 py-1 rounded-md text-xs transition-colors cursor-pointer ${
                    installTab === 'source'
                      ? 'bg-white/[0.08] text-white border border-white/[0.12] font-medium'
                      : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  Source bootstrap
                </button>
              </div>

              <div className="flex items-center justify-between px-3.5 py-2.5 bg-[#0c0e14] border border-white/[0.08] rounded-lg font-mono text-xs text-zinc-300">
                <span className="flex items-center gap-2 truncate">
                  <span className="text-zinc-500 select-none">$</span>
                  <span className="truncate">{installCommands[installTab]}</span>
                </span>
                <button
                  onClick={copyInstallCommand}
                  title="Copy command"
                  className="p-1.5 ml-2 text-zinc-400 hover:text-white rounded transition-colors shrink-0 cursor-pointer"
                >
                  {copiedInstall ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            {/* Core Metrics Telemetry Strip */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-white/[0.06] text-xs">
              <div>
                <div className="font-mono text-base text-zinc-100 font-bold">0.00 ms</div>
                <div className="text-zinc-500 text-[11px] mt-0.5">GC pauses (p99)</div>
              </div>
              <div>
                <div className="font-mono text-base text-zinc-100 font-bold">SHA-256</div>
                <div className="text-zinc-500 text-[11px] mt-0.5">Fixed-point determinism</div>
              </div>
              <div>
                <div className="font-mono text-base text-zinc-100 font-bold">127</div>
                <div className="text-zinc-500 text-[11px] mt-0.5">Pure stdlib modules</div>
              </div>
            </div>
          </div>

          {/* Right Column: Interactive Compiler & Benchmark Sandbox */}
          <div className="lg:col-span-6 space-y-3">
            
            {/* Mode Switcher: Code & Lowering vs Live Benchmarks */}
            <div className="flex items-center justify-between pb-1">
              <div className="flex items-center gap-1 p-0.5 rounded-lg bg-white/[0.04] border border-white/[0.08]">
                <button
                  onClick={() => setHeroMode('code')}
                  className={`px-3 py-1 rounded text-xs transition-colors cursor-pointer flex items-center gap-1.5 ${
                    heroMode === 'code'
                      ? 'bg-[#161b26] text-white font-medium border border-white/[0.08]'
                      : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  <Code2 className="w-3.5 h-3.5" />
                  <span>Language lowering</span>
                </button>
                <button
                  onClick={() => setHeroMode('benchmark')}
                  className={`px-3 py-1 rounded text-xs transition-colors cursor-pointer flex items-center gap-1.5 ${
                    heroMode === 'benchmark'
                      ? 'bg-[#161b26] text-white font-medium border border-white/[0.08]'
                      : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  <Activity className="w-3.5 h-3.5" />
                  <span>Live telemetry</span>
                </button>
              </div>

              {heroMode === 'code' && (
                <div className="flex items-center gap-1 text-[11px]">
                  <button
                    onClick={() => setCodeViewMode('source')}
                    className={`px-2 py-0.5 rounded transition-colors ${
                      codeViewMode === 'source' ? 'text-[#00d4f0] font-medium' : 'text-zinc-500 hover:text-zinc-300'
                    }`}
                  >
                    Velo
                  </button>
                  <span className="text-zinc-600">/</span>
                  <button
                    onClick={() => setCodeViewMode('c99')}
                    className={`px-2 py-0.5 rounded transition-colors ${
                      codeViewMode === 'c99' ? 'text-[#00d4f0] font-medium' : 'text-zinc-500 hover:text-zinc-300'
                    }`}
                  >
                    Lowered C99
                  </button>
                  <span className="text-zinc-600">/</span>
                  <button
                    onClick={() => setCodeViewMode('output')}
                    className={`px-2 py-0.5 rounded transition-colors ${
                      codeViewMode === 'output' ? 'text-[#00d4f0] font-medium' : 'text-zinc-500 hover:text-zinc-300'
                    }`}
                  >
                    Output
                  </button>
                </div>
              )}
            </div>

            {/* Hero Mode: Code & Lowering Explorer */}
            {heroMode === 'code' ? (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-1 text-xs">
                  <button
                    onClick={() => setActiveCodeTab('zone')}
                    className={`px-2.5 py-1 rounded text-xs transition-colors cursor-pointer ${
                      activeCodeTab === 'zone'
                        ? 'bg-white/[0.08] text-white border border-white/[0.12] font-medium'
                        : 'text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    Zone arenas
                  </button>
                  <button
                    onClick={() => setActiveCodeTab('simd')}
                    className={`px-2.5 py-1 rounded text-xs transition-colors cursor-pointer ${
                      activeCodeTab === 'simd'
                        ? 'bg-white/[0.08] text-white border border-white/[0.12] font-medium'
                        : 'text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    128-bit SIMD
                  </button>
                  <button
                    onClick={() => setActiveCodeTab('particle')}
                    className={`px-2.5 py-1 rounded text-xs transition-colors cursor-pointer ${
                      activeCodeTab === 'particle'
                        ? 'bg-white/[0.08] text-white border border-white/[0.12] font-medium'
                        : 'text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    @ Pointers
                  </button>
                  <button
                    onClick={() => setActiveCodeTab('ufcs')}
                    className={`px-2.5 py-1 rounded text-xs transition-colors cursor-pointer ${
                      activeCodeTab === 'ufcs'
                        ? 'bg-white/[0.08] text-white border border-white/[0.12] font-medium'
                        : 'text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    UFCS methods
                  </button>
                </div>

                <div className="space-y-1.5">
                  <p className="text-xs text-zinc-400 font-sans">
                    {codeSnippets[activeCodeTab].description}
                  </p>
                  <CodeBlock
                    title={
                      codeViewMode === 'source'
                        ? codeSnippets[activeCodeTab].title
                        : codeViewMode === 'c99'
                        ? `${codeSnippets[activeCodeTab].title.replace('.vl', '')}.c (velo emit-c)`
                        : 'stdout'
                    }
                    language={codeViewMode === 'c99' ? 'c' : 'velo'}
                    code={
                      codeViewMode === 'source'
                        ? codeSnippets[activeCodeTab].source
                        : codeViewMode === 'c99'
                        ? codeSnippets[activeCodeTab].c99
                        : codeSnippets[activeCodeTab].output
                    }
                    output={codeViewMode === 'source' ? codeSnippets[activeCodeTab].output : undefined}
                  />
                </div>
              </div>
            ) : (
              /* Hero Mode: Live Benchmark Comparisons */
              <div className="p-6 rounded-xl bg-[#0f121a] border border-white/[0.08] space-y-6">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.08] pb-4">
                  <div className="space-y-1">
                    <h3 className="text-sm font-semibold text-white font-sans">
                      {benchmarkData[benchmarkMetric].title}
                    </h3>
                    <p className="text-[11px] text-zinc-400">
                      Standardized benchmark measurements on x86_64 Ubuntu / Windows 11.
                    </p>
                  </div>

                  {/* Benchmark metric selector */}
                  <div className="flex rounded-lg bg-[#090b10] p-0.5 border border-white/[0.08] text-xs">
                    <button
                      onClick={() => setBenchmarkMetric('gc')}
                      className={`px-2.5 py-1 rounded transition-colors ${
                        benchmarkMetric === 'gc'
                          ? 'bg-[#161b26] text-white font-medium border border-white/[0.08]'
                          : 'text-zinc-400 hover:text-zinc-200'
                      }`}
                    >
                      GC Pauses
                    </button>
                    <button
                      onClick={() => setBenchmarkMetric('startup')}
                      className={`px-2.5 py-1 rounded transition-colors ${
                        benchmarkMetric === 'startup'
                          ? 'bg-[#161b26] text-white font-medium border border-white/[0.08]'
                          : 'text-zinc-400 hover:text-zinc-200'
                      }`}
                    >
                      Cold Boot
                    </button>
                    <button
                      onClick={() => setBenchmarkMetric('memory')}
                      className={`px-2.5 py-1 rounded transition-colors ${
                        benchmarkMetric === 'memory'
                          ? 'bg-[#161b26] text-white font-medium border border-white/[0.08]'
                          : 'text-zinc-400 hover:text-zinc-200'
                      }`}
                    >
                      Memory RSS
                    </button>
                  </div>
                </div>

                {/* Bars */}
                <div className="space-y-4">
                  {benchmarkData[benchmarkMetric].items.map(item => (
                    <div key={item.name} className="space-y-1.5">
                      <div className="flex items-center justify-between text-xs">
                        <span className={`font-mono ${item.isVelo ? 'text-[#00d4f0] font-bold' : 'text-zinc-300'}`}>
                          {item.name}
                        </span>
                        <span className="font-mono text-zinc-400">
                          {item.display}
                        </span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-white/[0.05] overflow-hidden">
                        <div 
                          className={`h-full rounded-full transition-all duration-500 ${
                            item.isVelo 
                              ? 'bg-[#00d4f0]' 
                              : 'bg-zinc-600'
                          }`}
                          style={{ width: `${item.pct}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-zinc-500 font-mono">
                  <span>{benchmarkData[benchmarkMetric].note}</span>
                  <span className="text-zinc-400">benchmark/</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ================= 2. ASYMMETRIC BENTO GRID ================= */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-zinc-400">
            <Cpu className="w-3.5 h-3.5 text-[#00d4f0]" />
            <span>Architecture & Principles</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-[#eef0f6] font-sans tracking-tight">
            Engineered from first principles for bare-metal control.
          </h2>
          <p className="text-zinc-400 text-xs sm:text-sm max-w-2xl">
            Every architectural decision eliminates hidden runtime overhead, stops stop-the-world pauses, and ensures bit-for-bit mathematical determinism.
          </p>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          
          {/* Bento 1: Large Span-2 - Lexical Zone Arenas */}
          <div className="md:col-span-2 p-6 rounded-2xl bg-[#0f121a] border border-white/[0.08] hover:border-white/[0.14] transition-colors space-y-5 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono px-2 py-0.5 rounded text-[#00d4f0] bg-white/[0.04] border border-white/[0.08]">
                  Zero-Cycle Reset
                </span>
                <span className="text-[11px] font-mono text-zinc-500">0 background threads</span>
              </div>
              <h3 className="text-lg font-bold text-white font-sans">
                Lexical Zone Memory Arenas
              </h3>
              <p className="text-xs text-zinc-400 leading-relaxed max-w-xl">
                No stop-the-world pauses or background mark-and-sweep threads. Scoped <code className="text-zinc-200 font-mono">zone</code> blocks bump-allocate contiguous memory in 1-2 CPU cycles and restore memory pointers in a single instruction upon block exit.
              </p>
            </div>

            {/* Interactive Memory Visualizer Widget */}
            <div className="p-4 rounded-xl bg-[#090b10] border border-white/[0.08] space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between text-zinc-400 border-b border-white/[0.06] pb-2">
                <span>Interactive Arena Simulation</span>
                <div className="flex gap-1.5">
                  <button
                    onClick={() => setZoneStep(0)}
                    className={`px-2 py-0.5 rounded ${zoneStep === 0 ? 'bg-white/[0.1] text-white' : 'text-zinc-500'}`}
                  >
                    1. Base
                  </button>
                  <button
                    onClick={() => setZoneStep(1)}
                    className={`px-2 py-0.5 rounded ${zoneStep === 1 ? 'bg-white/[0.1] text-white' : 'text-zinc-500'}`}
                  >
                    2. Alloc (32KB)
                  </button>
                  <button
                    onClick={() => setZoneStep(2)}
                    className={`px-2 py-0.5 rounded ${zoneStep === 2 ? 'bg-white/[0.1] text-white' : 'text-zinc-500'}`}
                  >
                    3. Reset (1-op)
                  </button>
                </div>
              </div>

              {/* Memory buffer track */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-[11px] text-zinc-500">
                  <span>Stack Top: 0x7FFEE0</span>
                  <span>
                    {zoneStep === 1 ? 'Active Allocated: 32,000 bytes' : 'Active Allocated: 0 bytes'}
                  </span>
                </div>
                <div className="w-full h-6 rounded bg-white/[0.03] border border-white/[0.08] p-0.5 flex">
                  {zoneStep === 1 && (
                    <div className="h-full bg-[#00d4f0] rounded-sm transition-all duration-300 w-3/4 flex items-center justify-center text-[10px] text-black font-bold">
                      matrices: @Matrix [500] (Contiguous L1/L2 Cache)
                    </div>
                  )}
                  {zoneStep === 2 && (
                    <div className="h-full bg-emerald-500/20 border border-emerald-500/50 rounded-sm transition-all duration-300 w-full flex items-center justify-center text-[10px] text-emerald-300">
                      Zone exit: Watermark restored in 1 instruction. Zero fragmentation.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Bento 2: Span-1 - Bit-for-Bit Determinism */}
          <div className="p-6 rounded-2xl bg-[#0f121a] border border-white/[0.08] hover:border-white/[0.14] transition-colors space-y-4 flex flex-col justify-between">
            <div className="space-y-2">
              <span className="text-[11px] font-mono px-2 py-0.5 rounded text-emerald-400 bg-white/[0.04] border border-white/[0.08]">
                Bit-for-Bit Verified
              </span>
              <h3 className="text-base font-bold text-white font-sans">
                3-Generation Determinism
              </h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                The self-hosting compiler chain enforces identical binary SHA-256 hashes between Gen 2 and Gen 3 builds. Compiler Heisenbugs are physically impossible.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-[#090b10] border border-white/[0.08] space-y-2 font-mono text-[11px]">
              <div className="flex justify-between text-zinc-400">
                <span>Gen 2 SHA-256</span>
                <span className="text-zinc-200 truncate max-w-[120px]">beb184119c...</span>
              </div>
              <div className="flex justify-between text-zinc-400">
                <span>Gen 3 SHA-256</span>
                <span className="text-zinc-200 truncate max-w-[120px]">beb184119c...</span>
              </div>
              <div className="pt-2 border-t border-white/[0.06] text-emerald-400 flex items-center gap-1.5 font-sans font-medium text-xs">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Exact Byte Parity (0 byte delta)</span>
              </div>
            </div>
          </div>

          {/* Bento 3: Span-1 - 128-bit SIMD */}
          <div className="p-6 rounded-2xl bg-[#0f121a] border border-white/[0.08] hover:border-white/[0.14] transition-colors space-y-4 flex flex-col justify-between">
            <div className="space-y-2">
              <span className="text-[11px] font-mono px-2 py-0.5 rounded text-zinc-300 bg-white/[0.04] border border-white/[0.08]">
                Hardware Intrinsics
              </span>
              <h3 className="text-base font-bold text-white font-sans">
                128-bit Vector SIMD
              </h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                First-class language support for <code className="text-zinc-200 font-mono">f32x4</code> and <code className="text-zinc-200 font-mono">i32x4</code> vector registers compiling directly to SSE, AVX, and NEON instruction sets.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-[#090b10] border border-white/[0.08] font-mono text-xs text-zinc-300 space-y-1">
              <div className="text-zinc-500 text-[10px]">Lane layout:</div>
              <div className="grid grid-cols-4 gap-1 text-center font-bold text-[11px]">
                <div className="bg-white/[0.06] py-1 rounded">X</div>
                <div className="bg-white/[0.06] py-1 rounded">Y</div>
                <div className="bg-white/[0.06] py-1 rounded">Z</div>
                <div className="bg-white/[0.06] py-1 rounded">W</div>
              </div>
              <div className="text-[10px] text-zinc-500 pt-1">
                Instruction: _mm_mul_ps / _mm_add_ps (1 cycle)
              </div>
            </div>
          </div>

          {/* Bento 4: Large Span-2 - Zero-Libc Standard Library */}
          <div className="md:col-span-2 p-6 rounded-2xl bg-[#0f121a] border border-white/[0.08] hover:border-white/[0.14] transition-colors space-y-4 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono px-2 py-0.5 rounded text-emerald-400 bg-white/[0.04] border border-white/[0.08]">
                  Zero Libc Dependencies
                </span>
                <span className="text-[11px] font-mono text-zinc-500">127 pure modules</span>
              </div>
              <h3 className="text-lg font-bold text-white font-sans">
                100% Pure Velo Standard Library
              </h3>
              <p className="text-xs text-zinc-400 leading-relaxed max-w-xl">
                Written from scratch without any external C runtime dependencies. Provides virtual memory managers, RFC 8439 ChaCha20-Poly1305, TLS 1.3 engines, UTF-8 streaming, and dynamic collections.
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
              <div className="p-3 rounded-lg bg-[#090b10] border border-white/[0.06] space-y-1">
                <div className="text-zinc-500 text-[10px]">Memory</div>
                <div className="text-white font-bold">std.mem</div>
                <div className="text-zinc-500 text-[10px]">2,450 LOC</div>
              </div>
              <div className="p-3 rounded-lg bg-[#090b10] border border-white/[0.06] space-y-1">
                <div className="text-zinc-500 text-[10px]">Crypto</div>
                <div className="text-white font-bold">std.crypto</div>
                <div className="text-zinc-500 text-[10px]">RFC 8439 / TLS</div>
              </div>
              <div className="p-3 rounded-lg bg-[#090b10] border border-white/[0.06] space-y-1">
                <div className="text-zinc-500 text-[10px]">Collections</div>
                <div className="text-white font-bold">std.shelf</div>
                <div className="text-zinc-500 text-[10px]">Zero-alloc ring</div>
              </div>
              <div className="p-3 rounded-lg bg-[#090b10] border border-white/[0.06] space-y-1">
                <div className="text-zinc-500 text-[10px]">Async I/O</div>
                <div className="text-white font-bold">std.io</div>
                <div className="text-zinc-500 text-[10px]">Non-blocking</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================= 3. PRODUCTION CASE STUDIES WITH MICRO-PREVIEWS ================= */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-zinc-400">
            <Database className="w-3.5 h-3.5 text-[#00d4f0]" />
            <span>Real-World Validation</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-[#eef0f6] font-sans tracking-tight">
            Built with Velo for production systems.
          </h2>
          <p className="text-zinc-400 text-xs sm:text-sm max-w-2xl">
            Live implementations demonstrating Velo&apos;s lexical memory models, raw C-ABI interoperability, and zero-GC performance.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* App 1: VeloKV Interactive Terminal */}
          <div className="p-6 rounded-2xl bg-[#0f121a] border border-white/[0.08] hover:border-white/[0.14] transition-colors space-y-4 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono px-2 py-0.5 rounded text-white bg-white/[0.04] border border-white/[0.08]">
                  Database Engine
                </span>
                <span className="text-[11px] font-mono text-zinc-500">apps/velokv/</span>
              </div>
              <h3 className="text-base font-bold text-white font-sans">
                VeloKV In-Memory Store
              </h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                High-throughput Redis-compatible in-memory store with binary protocol parsing, TCP event polling, and append-only disk logging.
              </p>
            </div>

            {/* Interactive Mini Terminal */}
            <div className="p-3.5 rounded-xl bg-[#090b10] border border-white/[0.08] font-mono text-xs space-y-2.5">
              <div className="flex items-center justify-between border-b border-white/[0.06] pb-1.5 text-zinc-500 text-[10px]">
                <span>velokv-cli 127.0.0.1:6379</span>
                <span className="text-emerald-400">Connected</span>
              </div>

              <div className="space-y-1.5 max-h-[120px] overflow-y-auto">
                {kvHistory.map((h, idx) => (
                  <div key={idx} className="space-y-0.5">
                    <div className="flex items-center justify-between text-zinc-300">
                      <span className="text-zinc-500 select-none">&gt; {h.cmd}</span>
                      <span className="text-zinc-600 text-[10px]">{h.time}</span>
                    </div>
                    <div className="text-emerald-400 whitespace-pre-wrap pl-2 border-l border-white/[0.06]">
                      {h.res}
                    </div>
                  </div>
                ))}
              </div>

              {/* Quick Command Pills */}
              <div className="flex flex-wrap gap-1 pt-1 border-t border-white/[0.06]">
                <button
                  onClick={() => handleRunKvCommand('PING')}
                  className="px-2 py-0.5 rounded bg-white/[0.04] hover:bg-white/[0.08] text-zinc-300 text-[10px] cursor-pointer"
                >
                  PING
                </button>
                <button
                  onClick={() => handleRunKvCommand('INCR request_count')}
                  className="px-2 py-0.5 rounded bg-white/[0.04] hover:bg-white/[0.08] text-zinc-300 text-[10px] cursor-pointer"
                >
                  INCR
                </button>
                <button
                  onClick={() => handleRunKvCommand('INFO')}
                  className="px-2 py-0.5 rounded bg-white/[0.04] hover:bg-white/[0.08] text-zinc-300 text-[10px] cursor-pointer"
                >
                  INFO
                </button>
              </div>
            </div>

            <button
              onClick={() => {
                onNavigate('docs');
                onSelectDocPage('case-study-velokv');
              }}
              className="text-xs text-zinc-300 hover:text-white font-medium flex items-center gap-1.5 transition-colors cursor-pointer pt-2"
            >
              <span>Explore architectural breakdown</span>
              <ArrowRight className="w-3.5 h-3.5 text-zinc-500" />
            </button>
          </div>

          {/* App 2: VeloStudio Desktop UI */}
          <div className="p-6 rounded-2xl bg-[#0f121a] border border-white/[0.08] hover:border-white/[0.14] transition-colors space-y-4 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono px-2 py-0.5 rounded text-white bg-white/[0.04] border border-white/[0.08]">
                  Desktop Application
                </span>
                <span className="text-[11px] font-mono text-zinc-500">apps/velostudio/</span>
              </div>
              <h3 className="text-base font-bold text-white font-sans">
                VeloStudio SQLite Explorer
              </h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Native desktop database workbench powered by Raylib windowing, tabular grid views, query execution, and transactional schema inspection.
              </p>
            </div>

            {/* Simulated Desktop Workbench UI */}
            <div className="rounded-xl bg-[#090b10] border border-white/[0.08] font-mono text-[11px] overflow-hidden">
              <div className="px-3 py-2 bg-[#161b26] border-b border-white/[0.08] flex items-center justify-between text-zinc-400 text-[10px]">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-white/[0.2]" />
                  <span>velostudio - main.db</span>
                </div>
                <span className="text-zinc-500">SQLite 3.45</span>
              </div>

              <div className="p-3 space-y-2">
                <div className="text-zinc-500 text-[10px]">SELECT * FROM users LIMIT 2;</div>
                <div className="space-y-1">
                  <div className="grid grid-cols-3 text-zinc-400 border-b border-white/[0.06] pb-1 font-bold">
                    <span>id</span>
                    <span>username</span>
                    <span>latency</span>
                  </div>
                  <div className="grid grid-cols-3 text-zinc-300">
                    <span>1</span>
                    <span>"admin"</span>
                    <span className="text-emerald-400">0.08ms</span>
                  </div>
                  <div className="grid grid-cols-3 text-zinc-300">
                    <span>2</span>
                    <span>"runner"</span>
                    <span className="text-emerald-400">0.05ms</span>
                  </div>
                </div>
              </div>
            </div>

            <button
              onClick={() => {
                onNavigate('docs');
                onSelectDocPage('case-study-velostudio');
              }}
              className="text-xs text-zinc-300 hover:text-white font-medium flex items-center gap-1.5 transition-colors cursor-pointer pt-2"
            >
              <span>Explore architectural breakdown</span>
              <ArrowRight className="w-3.5 h-3.5 text-zinc-500" />
            </button>
          </div>

          {/* App 3: Velocraft 3D Engine */}
          <div className="p-6 rounded-2xl bg-[#0f121a] border border-white/[0.08] hover:border-white/[0.14] transition-colors space-y-4 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono px-2 py-0.5 rounded text-white bg-white/[0.04] border border-white/[0.08]">
                  Real-Time Graphics
                </span>
                <span className="text-[11px] font-mono text-zinc-500">games/</span>
              </div>
              <h3 className="text-base font-bold text-white font-sans">
                Velocraft 3D Voxel Engine
              </h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Procedural mesh generation, 3D camera controls, and particle physics demonstrating consistent 120 FPS frame timing with zero GC spikes.
              </p>
            </div>

            {/* Live Animated Canvas Voxel Viewport */}
            <div className="rounded-xl bg-[#090b10] border border-white/[0.08] overflow-hidden relative">
              <canvas
                ref={canvasRef}
                width={320}
                height={160}
                className="w-full h-[160px] block"
              />
              <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-black/60 border border-white/[0.1] font-mono text-[10px] text-emerald-400 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                <span>120.0 FPS (8.33ms)</span>
              </div>
              <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-black/60 border border-white/[0.1] font-mono text-[10px] text-zinc-400">
                0 GC Alloc / Frame
              </div>
            </div>

            <button
              onClick={() => {
                onNavigate('docs');
                onSelectDocPage('case-study-gamedev');
              }}
              className="text-xs text-zinc-300 hover:text-white font-medium flex items-center gap-1.5 transition-colors cursor-pointer pt-2"
            >
              <span>Explore game dev tutorial</span>
              <ArrowRight className="w-3.5 h-3.5 text-zinc-500" />
            </button>
          </div>
        </div>
      </section>

      {/* ================= 4. STEP-BY-STEP PROGRESSION ROADMAP ================= */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="p-8 sm:p-10 rounded-2xl bg-[#0c0e14] border border-white/[0.08] space-y-8">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 border-b border-white/[0.08] pb-6">
            <div className="space-y-1 max-w-xl">
              <h2 className="text-xl sm:text-2xl font-bold text-white font-sans tracking-tight">
                Developer Curriculum Progression
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
              className="px-4 py-2 rounded-lg bg-white text-zinc-950 font-semibold text-xs hover:bg-zinc-200 flex items-center gap-1.5 transition-colors shrink-0 cursor-pointer"
            >
              <span>Start step 1</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div 
              onClick={() => {
                onNavigate('docs');
                onSelectDocPage('getting-started-first-project');
              }}
              className="p-5 rounded-xl bg-[#0f121a] border border-white/[0.06] hover:border-white/[0.14] transition-colors space-y-2 cursor-pointer group"
            >
              <span className="text-[11px] font-mono text-zinc-500 group-hover:text-[#00d4f0] transition-colors">Step 01</span>
              <h4 className="text-sm font-semibold text-white">Fundamentals</h4>
              <p className="text-xs text-zinc-400 leading-relaxed">Compiler installation, syntax grammar, static types, and control flow.</p>
            </div>

            <div 
              onClick={() => {
                onNavigate('docs');
                onSelectDocPage('memory-pointers');
              }}
              className="p-5 rounded-xl bg-[#0f121a] border border-white/[0.06] hover:border-white/[0.14] transition-colors space-y-2 cursor-pointer group"
            >
              <span className="text-[11px] font-mono text-zinc-500 group-hover:text-[#00d4f0] transition-colors">Step 02</span>
              <h4 className="text-sm font-semibold text-white">Memory & Pointers</h4>
              <p className="text-xs text-zinc-400 leading-relaxed">The @ pointer model, lexical zone arenas, and deterministic defer blocks.</p>
            </div>

            <div 
              onClick={() => {
                onNavigate('docs');
                onSelectDocPage('language-structures');
              }}
              className="p-5 rounded-xl bg-[#0f121a] border border-white/[0.06] hover:border-white/[0.14] transition-colors space-y-2 cursor-pointer group"
            >
              <span className="text-[11px] font-mono text-zinc-500 group-hover:text-[#00d4f0] transition-colors">Step 03</span>
              <h4 className="text-sm font-semibold text-white">Data & Methods</h4>
              <p className="text-xs text-zinc-400 leading-relaxed">Struct definitions, sum types (kind), generic pacts, and UFCS methods.</p>
            </div>

            <div 
              onClick={() => {
                onNavigate('docs');
                onSelectDocPage('concurrency-async');
              }}
              className="p-5 rounded-xl bg-[#0f121a] border border-white/[0.06] hover:border-white/[0.14] transition-colors space-y-2 cursor-pointer group"
            >
              <span className="text-[11px] font-mono text-zinc-500 group-hover:text-[#00d4f0] transition-colors">Step 04</span>
              <h4 className="text-sm font-semibold text-white">Production Systems</h4>
              <p className="text-xs text-zinc-400 leading-relaxed">Async networking event loops, 128-bit SIMD math, and C99 FFI bindings.</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
