import { DocCategory } from '../../types/docs';

export const COLLECTIONS_CATEGORY: DocCategory = {
  id: 'collections',
  name: '08. Dynamic Collections',
  description: 'First-class built-in collections: dynamic shelves, open-addressing maps, circular rings, and dense bitsets.',
  iconName: 'Database',
  pages: [
    {
      id: 'collections-overview',
      slug: 'collections-overview',
      title: 'Collections Overview',
      category: '08. Dynamic Collections',
      categoryOrder: 8,
      order: 1,
      description: 'Why Velo bakes four essential memory-conscious collections directly into the language syntax.',
      readTimeMinutes: 4,
      whatYoullLearn: [
        'The four built-in dynamic collection types',
        'Cache-conscious contiguous memory layout',
        'Zero-allocation snapshot iteration',
        'Lifecycle and memory management'
      ],
      sections: [
        {
          id: 'four-collections',
          title: 'The Four Native Collections',
          content: `Rather than forcing developers to reinvent dynamic arrays or pull in heavy third-party dependencies, Velo bakes four highly optimized collections directly into the compiler:

1. **\`shelf[T]\`**: Cache-friendly dynamic resizable array (vector).
2. **\`map[K, V]\`**: High-performance open-addressing hash table with Robin Hood hashing.
3. **\`ring[T]\`**: Circular ring buffer for zero-reallocation queues and FIFO streams.
4. **\`bitset[N]\`**: Dense bitfield with hardware population count and set operations.`
        }
      ],
      prevPage: { title: 'Custom Allocators', slug: 'memory-allocators' },
      nextPage: { title: 'Dynamic Shelves (shelf[T])', slug: 'collections-shelf' }
    },
    {
      id: 'collections-shelf',
      slug: 'collections-shelf',
      title: 'Dynamic Shelves (shelf[T])',
      category: '08. Dynamic Collections',
      categoryOrder: 8,
      order: 2,
      description: 'Growable dynamic arrays with bounds checking, put/take LIFO operations, and snapshot loop-of iteration.',
      readTimeMinutes: 6,
      badge: 'Core Feature',
      whatYoullLearn: [
        'Typed shelf literals: shelf[10, 20, 30]',
        'Appending with .put() and popping with .take()',
        'Zero-overhead snapshot iteration: loop v of xs',
        'Passing shelves by value into acts'
      ],
      sections: [
        {
          id: 'shelf-usage',
          title: 'Working with Shelves',
          content: `In Velo, dynamic arrays are called **shelves**:`,
          codeExamples: [
            {
              title: 'shelves.vl',
              language: 'velo',
              code: `use std.io

act main() {
    // 1. Typed literal:
    let nums: shelf[i32] = shelf[4, 8, 15, 16]
    io.println("Length: {nums.len}")
    io.println("Element [2]: {nums[2]}")

    // 2. Mutable shelf with put/take:
    mut items = shelf[10, 20]
    items.put(30) // Appends to the end
    let top = items.take() // Pops from the end (LIFO)
    io.println("Popped top: {top}, remaining len: {items.len}")

    // 3. Snapshot iteration (loop ... of ...):
    mut sum = 0
    loop val of nums {
        sum += val
    }
    io.println("Sum of elements: {sum}")
}`
            }
          ]
        },
        {
          id: 'snapshot-iteration',
          title: 'Snapshot Iteration Safety',
          content: `When iterating over a shelf using \`loop v of xs\`, the loop operates over a **fixed snapshot** of the shelf length at loop start. Adding items inside the loop body with \`xs.put(...)\` does not cause infinite iteration loops.`
        }
      ],
      prevPage: { title: 'Collections Overview', slug: 'collections-overview' },
      nextPage: { title: 'Hash Maps (map[K, V])', slug: 'collections-map' }
    },
    {
      id: 'collections-map',
      slug: 'collections-map',
      title: 'Hash Maps (map[K, V])',
      category: '08. Dynamic Collections',
      categoryOrder: 8,
      order: 3,
      description: 'Open-addressing hash tables with Robin Hood collision resolution and tombstone deletion.',
      readTimeMinutes: 5,
      whatYoullLearn: [
        'Creating and querying maps (map[string, i32])',
        'Inserting and updating entries with .set(k, v)',
        'Lookup and pointer returns with .get(k)',
        'Robin Hood hashing performance characteristics'
      ],
      sections: [
        {
          id: 'map-usage',
          title: 'Using Maps in Velo',
          content: `Velo maps provide $O(1)$ expected lookup and insertion times using Robin Hood open-addressing:`,
          codeExamples: [
            {
              title: 'maps.vl',
              language: 'velo',
              code: `use std.io

act main() {
    mut inventory = map[string, i32]{}

    inventory.set("health_potion", 5)
    inventory.set("mana_potion", 3)

    let p_count = inventory.get("health_potion")
    if p_count != null {
        io.println("Health potions: {p_count.@}")
    }
}`
            }
          ]
        }
      ],
      prevPage: { title: 'Dynamic Shelves (shelf[T])', slug: 'collections-shelf' },
      nextPage: { title: 'Ring Buffers & Bitsets', slug: 'collections-ring-bitset' }
    },
    {
      id: 'collections-ring-bitset',
      slug: 'collections-ring-bitset',
      title: 'Ring Buffers & Bitsets',
      category: '08. Dynamic Collections',
      categoryOrder: 8,
      order: 4,
      description: 'Circular ring buffers for high-speed queues and fixed-capacity bitfields with hardware popcount.',
      readTimeMinutes: 5,
      whatYoullLearn: [
        'Circular ring[T] buffers for queues and audio pipelines',
        'Dense bitfields with bitset[N]',
        'Bitwise union, intersection, and hardware popcount'
      ],
      sections: [
        {
          id: 'ring-buffers',
          title: 'Ring Buffers (ring[T])',
          content: `Ring buffers provide contiguous, zero-reallocation FIFO queues for audio DSP, network packets, and event queues:

\`\`\`rust
mut audio_queue = ring[f32](1024)
audio_queue.push(0.75)
let sample = audio_queue.pop()
\`\`\``
        },
        {
          id: 'bitsets',
          title: 'Dense Bitfields (bitset[N])',
          content: `\`bitset[N]\` stores compact bit arrays with hardware popcount instructions for entity component flags:

\`\`\`rust
mut flags: bitset[64] = bitset[64]()
flags.set(3) // Set bit 3
if flags.test(3) {
    io.println("Bit 3 is enabled!")
}
\`\`\``
        }
      ],
      prevPage: { title: 'Hash Maps (map[K, V])', slug: 'collections-map' },
      nextPage: { title: '128-Bit SIMD Acceleration', slug: 'hardware-simd' }
    }
  ]
};

