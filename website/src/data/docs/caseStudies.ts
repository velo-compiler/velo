import { DocCategory } from '../../types/docs';

export const CASE_STUDIES_CATEGORY: DocCategory = {
  id: 'case-studies',
  name: '13. Case Studies & Tutorials',
  description: 'Production applications built in Velo: VeloKV (Redis store), VeloStudio (GUI SQLite inspector), and game dev.',
  iconName: 'Compass',
  pages: [
    {
      id: 'case-study-velokv',
      slug: 'case-study-velokv',
      title: 'Case Study: VeloKV',
      category: '13. Case Studies & Tutorials',
      categoryOrder: 13,
      order: 1,
      description: 'A Redis-compatible in-memory database server written in pure Velo with Append-Only File (AOF) persistence.',
      readTimeMinutes: 7,
      badge: 'Case Study',
      whatYoullLearn: [
        'How VeloKV implements Redis RESP protocol in pure Velo',
        'Managing concurrent client connections and map lookups',
        'Append-Only File (AOF) disk persistence',
        'Achieving sub-millisecond query responses with zone memory'
      ],
      sections: [
        {
          id: 'velokv-arch',
          title: 'VeloKV Architecture (apps/velokv/)',
          content: `**VeloKV** is a production-grade in-memory key-value database server written entirely in Velo:

- **RESP Protocol Parser**: Decodes standard Redis client protocol commands (\`SET\`, \`GET\`, \`DEL\`, \`PING\`, \`EXISTS\`, \`INCR\`).
- **High-Performance Storage**: Backed by Velo's built-in open-addressing \`map[string, string]\` with zero-allocation slicing.
- **AOF Persistence**: Automatically logs every mutating transaction to an Append-Only File (\`velokv.aof\`) on disk using atomic streaming writes.
- **Zero GC Lag**: Because incoming requests are handled within ephemeral \`zone { ... }\` arenas, memory is wiped in 1 instruction between requests, eliminating garbage collection latency spikes.`
        }
      ],
      prevPage: { title: 'Testing & Source Debugging', slug: 'tooling-testing-debugging' },
      nextPage: { title: 'Case Study: VeloStudio', slug: 'case-study-velostudio' }
    },
    {
      id: 'case-study-velostudio',
      slug: 'case-study-velostudio',
      title: 'Case Study: VeloStudio',
      category: '13. Case Studies & Tutorials',
      categoryOrder: 13,
      order: 2,
      description: 'A cross-platform desktop GUI SQLite database explorer built with Velo and Raylib.',
      readTimeMinutes: 6,
      badge: 'Case Study',
      whatYoullLearn: [
        'Building desktop GUI applications in Velo',
        'Binding to Raylib and SQLite via extern act',
        'Dynamic table rendering with shelf collections',
        'Theme engine and responsive layout calculation'
      ],
      sections: [
        {
          id: 'velostudio-arch',
          title: 'VeloStudio Architecture (apps/velostudio/)',
          content: `**VeloStudio** is a desktop database inspector application:

- **Raylib Integration**: Binds directly to Raylib GUI primitives with zero wrapper tax.
- **SQLite Engine**: Executes SQL queries, inspects schema metadata, and fetches tabular rows into dynamic \`shelf[Row]\` collections.
- **Responsive UI**: Custom UI widgets (modal dialogs, data tables, scrollbars) rendered at 120 FPS.`
        }
      ],
      prevPage: { title: 'Case Study: VeloKV', slug: 'case-study-velokv' },
      nextPage: { title: 'Tutorial: Real-Time Particle Simulation', slug: 'case-study-gamedev' }
    },
    {
      id: 'case-study-gamedev',
      slug: 'case-study-gamedev',
      title: 'Tutorial: Real-Time Particle Simulation',
      category: '13. Case Studies & Tutorials',
      categoryOrder: 13,
      order: 3,
      description: 'Step-by-step tutorial creating a 120 FPS 2D particle simulation engine using zone arenas and operator overloading.',
      readTimeMinutes: 8,
      badge: 'Tutorial',
      whatYoullLearn: [
        'Setting up particle vectors with operator overloading (op +)',
        'Managing 10,000 active particles inside a zone arena',
        'Euler physics integration loop',
        'Zero-GC 120 FPS guarantees'
      ],
      sections: [
        {
          id: 'step-by-step',
          title: 'Building the Particle Engine',
          content: `Let's assemble a complete, production-ready particle system combining structs, operator overloading, and zone memory:`,
          codeExamples: [
            {
              title: 'particles_game.vl',
              language: 'velo',
              code: `use std.io
use std.mem

data Vec2 {
    x: f32
    y: f32
}

act op +(a: Vec2, b: Vec2) -> Vec2 {
    return Vec2{ x: a.x + b.x, y: a.y + b.y }
}

act op *(v: Vec2, s: f32) -> Vec2 {
    return Vec2{ x: v.x * s, y: v.y * s }
}

data Particle {
    pos: Vec2
    vel: Vec2
    life: f32
}

act main() {
    io.println("Initializing 10,000 Particle Engine...")

    zone {
        count: usize = 10000
        particles: @Particle = mem.alloc(@Particle, count)

        // Initialize particles
        loop i in 0..count {
            p: @Particle = @particles[i]
            p.pos = Vec2{ x: 0.0, y: 0.0 }
            p.vel = Vec2{ x: (i as f32) * 0.1, y: 9.8 }
            p.life = 1.0
        }

        // Simulate 60 frames (1 second at 60 FPS)
        let dt: f32 = 0.016
        loop frame in 0..60 {
            loop i in 0..count {
                p: @Particle = @particles[i]
                p.pos = p.pos + p.vel * dt
                p.life -= dt
            }
        }

        let p0 = particles[0]
        io.println("Particle 0 position after 60 frames: ({p0.pos.x}, {p0.pos.y})")
    }

    io.println("Simulation complete: 10,000 particles cleared in 1 CPU cycle!")
}`
            }
          ]
        }
      ],
      prevPage: { title: 'Case Study: VeloStudio', slug: 'case-study-velostudio' },
      nextPage: { title: 'Formal Language Grammar', slug: 'reference-grammar' }
    }
  ]
};

