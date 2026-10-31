import { DocCategory } from '../../types/docs';

export const TYPES_MODELING_CATEGORY: DocCategory = {
  id: 'types-modeling',
  name: '06. Composite Types & Data Modeling',
  description: 'Structs, tagged unions, parametric generics, operator overloading, and memory layout attributes.',
  iconName: 'Layers',
  pages: [
    {
      id: 'types-structs',
      slug: 'types-structs',
      title: 'Structs (data)',
      category: '06. Composite Types & Data Modeling',
      categoryOrder: 6,
      order: 1,
      description: 'Declare unboxed composite structures with the data keyword and flat C-ABI compatibility.',
      readTimeMinutes: 5,
      whatYoullLearn: [
        'The data keyword for declaring unboxed composite types',
        'Flat C-ABI memory layout guarantee',
        'Struct instantiation syntax and field access',
        'Passing structs by value vs by pointer (@T)'
      ],
      sections: [
        {
          id: 'declaration',
          title: 'Declaring Structs',
          content: `In Velo, composite structures are declared using the \`data\` keyword. Velo structs have guaranteed flat C-ABI memory layouts, meaning they match standard C \`struct\` layouts with zero hidden header pointers, vtables, or padding bloat:`,
          codeExamples: [
            {
              title: 'structs.vl',
              language: 'velo',
              code: `use std.io

data Vector3 {
    x: f32
    y: f32
    z: f32
}

data Transform {
    position: Vector3
    rotation: f32
    scale: f32
}

act main() {
    // Instantiation:
    mut pos = Vector3{ x: 10.0, y: 20.0, z: 0.0 }
    io.println("Position: ({pos.x}, {pos.y}, {pos.z})")

    pos.x += 5.0
    io.println("Updated X: {pos.x}")
}`
            }
          ]
        },
        {
          id: 'memory-layout',
          title: 'Memory Layout & ABI Compatibility',
          content: `Because \`data\` types map 1:1 to C structs, you can pass pointers to Velo structs directly to C libraries like OpenGL, Vulkan, Raylib, or SQLite without marshalling:

\`\`\`rust
// Compatible with Raylib's Vector3 struct:
data RaylibVector3 {
    x: f32
    y: f32
    z: f32
}
\`\`\``
        }
      ],
      prevPage: { title: 'Uniform Function Call Syntax (UFCS)', slug: 'functions-ufcs' },
      nextPage: { title: 'Enums & Tagged Unions (kind)', slug: 'types-enums-unions' }
    },
    {
      id: 'types-enums-unions',
      slug: 'types-enums-unions',
      title: 'Enums & Tagged Unions (kind)',
      category: '06. Composite Types & Data Modeling',
      categoryOrder: 6,
      order: 2,
      description: 'First-class enumerations and payload-bearing tagged unions using the 4-letter kind keyword.',
      readTimeMinutes: 6,
      badge: 'Core Feature',
      whatYoullLearn: [
        'Pure scalar enums and explicit discriminant values (Ok = 200)',
        'Payload-bearing tagged unions with single and multi-field payloads',
        'Contextual dot-shorthand (.Variant)',
        'C99 union and discriminator lowering'
      ],
      sections: [
        {
          id: 'enums-and-unions',
          title: 'The kind Keyword',
          content: `Sum types, enumerations, and tagged unions are declared using the concise \`kind\` keyword:`,
          codeExamples: [
            {
              title: 'enums_and_unions.vl',
              language: 'velo',
              code: `use std.io

// 1. Pure scalar enum (zero overhead: int32_t in C)
kind Direction {
    North
    East
    South
    West
}

// 2. Enum with explicit discriminants
kind HttpStatus {
    Ok = 200
    NotFound = 404
    ServerError = 500
}

// 3. Tagged union with payloads
kind Message {
    Disconnect
    Text: string
    Move(x: f32, y: f32, speed: f32)
}

act main() {
    // Contextual dot-shorthand whenever type is known:
    let dir: Direction = .North
    let status: HttpStatus = .Ok
    let msg: Message = .Move(100.0, 200.0, 5.0)

    // Fully-qualified syntax is also valid:
    let dir2 = Direction.East
}`
            }
          ]
        },
        {
          id: 'lowering',
          title: 'C99 Lowering Architecture',
          content: `- **Pure Enums**: Lower directly to scalar \`int32_t\` constants in C99.
- **Tagged Unions**: Lower to a C99 struct containing an integer discriminator and a payload union:
\`\`\`c
typedef struct Message {
    int32_t kind; // 0=Disconnect, 1=Text, 2=Move
    union {
        const char* Text;
        struct { float x; float y; float speed; } Move;
    } as;
} Message;
\`\`\``
        }
      ],
      prevPage: { title: 'Structs (data)', slug: 'types-structs' },
      nextPage: { title: 'Parametric Generics', slug: 'types-generics' }
    },
    {
      id: 'types-generics',
      slug: 'types-generics',
      title: 'Parametric Generics',
      category: '06. Composite Types & Data Modeling',
      categoryOrder: 6,
      order: 3,
      description: 'Zero-runtime-cost parametric polymorphism with square-bracket generics ([T], [K, V]) and monomorphization.',
      readTimeMinutes: 6,
      badge: 'Advanced',
      whatYoullLearn: [
        'Generic structs (data Box[T]) and unions (kind Option[T])',
        'Generic functions (act min[T]) and call-site type inference',
        'Monomorphization: how Velo specializes generics into C99 at compile time',
        'Zero runtime overhead guarantees'
      ],
      sections: [
        {
          id: 'generics-syntax',
          title: 'Declaring Generics',
          content: `Velo provides parametric polymorphism using square brackets (\`[T]\`, \`[K, V]\`):`,
          codeExamples: [
            {
              title: 'generics.vl',
              language: 'velo',
              code: `use std.io

// Generic Struct
data Box[T] {
    value: T
}

data Pair[K, V] {
    key: K
    val: V
}

// Generic Tagged Union
kind Option[T] {
    None
    Some: T
}

// Generic Function
act min[T](a: T, b: T) -> T {
    if a < b { return a }
    return b
}

act main() {
    let int_box: Box[i32] = Box[i32]{ value: 42 }
    let str_box: Box[string] = Box[string]{ value: "Velocity" }

    // Call-site type inference: automatically specializes min for i32
    let m = min(100, 250) // infers T = i32
    let mf = min[f32](3.14, 2.71) // explicit type argument

    io.println("min: {m}, min_f32: {mf}")
}`
            }
          ]
        },
        {
          id: 'monomorphization',
          title: 'Compile-Time Monomorphization',
          content: `Generics in Velo have **zero runtime overhead**. During compilation, the Velo monomorphizer specializes every unique generic instance into a dedicated C99 type or function (e.g. \`Box_i32\`, \`min_i32\`, \`min_f32\`). There is no virtual method table overhead, no type erasure, and no boxing.`
        }
      ],
      prevPage: { title: 'Enums & Tagged Unions (kind)', slug: 'types-enums-unions' },
      nextPage: { title: 'Operator Overloading', slug: 'types-operator-overloading' }
    },
    {
      id: 'types-operator-overloading',
      slug: 'types-operator-overloading',
      title: 'Operator Overloading',
      category: '06. Composite Types & Data Modeling',
      categoryOrder: 6,
      order: 4,
      description: 'Overload +, -, *, /, and comparisons for custom game math vectors and matrices using act op.',
      readTimeMinutes: 6,
      badge: 'Game Dev',
      whatYoullLearn: [
        'The act op declaration syntax',
        'Binary operators (+, -, *, /)',
        'Unary operators (unary negation op -)',
        'Equality operators (==, !=)',
        'Automatic compound assignment desugaring (+=, *=)'
      ],
      sections: [
        {
          id: 'operator-syntax',
          title: 'Overloading Operators for Game Math',
          content: `Custom types like 2D/3D vectors and colors can overload standard arithmetic and comparison operators using the 2-letter \`op\` prefix:`,
          codeExamples: [
            {
              title: 'vector_math.vl',
              language: 'velo',
              code: `use std.io

data Vector2 {
    x: f32
    y: f32
}

// 1. Vector + Vector
act op +(a: Vector2, b: Vector2) -> Vector2 {
    return Vector2{ x: a.x + b.x, y: a.y + b.y }
}

// 2. Vector * Scalar
act op *(v: Vector2, s: f32) -> Vector2 {
    return Vector2{ x: v.x * s, y: v.y * s }
}

// 3. Unary negation (-v)
act op-(v: Vector2) -> Vector2 {
    return Vector2{ x: -v.x, y: -v.y }
}

// 4. Equality comparison (==)
act op ==(a: Vector2, b: Vector2) -> bool {
    return a.x == b.x and a.y == b.y
}

act main() {
    let pos = Vector2{ x: 10.0, y: 20.0 }
    let vel = Vector2{ x: 2.0, y: -3.0 }
    let dt: f32 = 0.5

    // Natural mathematical equations with standard precedence:
    let next_pos = pos + vel * dt
    io.println("Next position: ({next_pos.x}, {next_pos.y})")
}`
            }
          ]
        },
        {
          id: 'compound-assignment',
          title: 'Automatic Compound Assignment',
          content: `When you overload binary \`+\`, statements like \`pos += vel\` are automatically desugared by the compiler into \`pos = pos + vel\`. You do not need to implement redundant \`+=\` methods.`
        }
      ],
      prevPage: { title: 'Parametric Generics', slug: 'types-generics' },
      nextPage: { title: 'Advanced Struct Features', slug: 'types-advanced-structs' }
    },
    {
      id: 'types-advanced-structs',
      slug: 'types-advanced-structs',
      title: 'Advanced Struct Features',
      category: '06. Composite Types & Data Modeling',
      categoryOrder: 6,
      order: 5,
      description: 'Default field initializers, memory alignment (#align), and struct packing (#packed).',
      readTimeMinutes: 5,
      whatYoullLearn: [
        'Default field initializers for structs',
        'Hardware memory alignment with #align(N)',
        'Dense struct packing with #packed',
        'Hardware cache line optimization'
      ],
      sections: [
        {
          id: 'defaults',
          title: 'Default Field Initializers',
          content: `Struct fields can specify constant default values. When initializing a struct literal, omitted fields are automatically filled from their defaults:`,
          codeExamples: [
            {
              title: 'defaults.vl',
              language: 'velo',
              code: `data Vec4 {
    x: f32 = 0.0
    y: f32 = 0.0
    z: f32 = 0.0
    w: f32 = 1.0
}

act main() {
    // Only specify x and y; z and w are filled from defaults:
    let v = Vec4{ x: 5.0, y: 10.0 }
    // v.z is 0.0, v.w is 1.0
}`
            }
          ]
        },
        {
          id: 'alignment-and-packing',
          title: 'Layout Attributes: #align and #packed',
          content: `For low-level hardware drivers, SIMD buffers, and network protocols, Velo provides explicit struct layout attributes:

\`\`\`rust
// 1. Force 16-byte alignment for 128-bit SIMD:
data Vec4Simd #align(16) {
    x: f32
    y: f32
    z: f32
    w: f32
}

// 2. Disable padding bytes for network packets:
data NetworkHeader #packed {
    magic: u16
    packet_id: u8
    payload_len: u32
}
\`\`\`

Both attributes compile directly to GCC, Clang, and MSVC alignment markers (\`__attribute__((aligned(N)))\`, \`__attribute__((packed))\`, and \`__declspec(align(N))\`).`
        }
      ],
      prevPage: { title: 'Operator Overloading', slug: 'types-operator-overloading' },
      nextPage: { title: 'The @ Pointer System', slug: 'memory-pointers' }
    }
  ]
};

