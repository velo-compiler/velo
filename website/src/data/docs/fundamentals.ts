import { DocCategory } from '../../types/docs';

export const FUNDAMENTALS_CATEGORY: DocCategory = {
  id: 'fundamentals',
  name: '03. Language Fundamentals',
  description: 'Master Velo syntax: variables, types, operators, precedence, strings, and aliases.',
  iconName: 'BookOpen',
  pages: [
    {
      id: 'lang-lexical-grammar',
      slug: 'lang-lexical-grammar',
      title: 'Lexical Grammar & Keywords',
      category: '03. Language Fundamentals',
      categoryOrder: 3,
      order: 1,
      description: 'Source encoding, identifiers, comments, punctuation, and the 28 reserved keywords in Velo.',
      readTimeMinutes: 5,
      whatYoullLearn: [
        'UTF-8 source encoding requirements',
        'Single-line and nested block comments',
        'The 28 official keywords reserved in Velo',
        'Contextual keywords (data, kind, op) and how they prevent name collisions'
      ],
      sections: [
        {
          id: 'source-encoding',
          title: 'Source Encoding & Files',
          content: `Velo source files are plain text files encoded in standard UTF-8 with the \`.vl\` extension.

> [!WARNING]
> **No UTF-8 BOM**: The Velo lexer rejects the Byte Order Mark character (\`\\ufeff\`). Always save \`.vl\` files as clean UTF-8 without BOM.`
        },
        {
          id: 'comments',
          title: 'Comments',
          content: `Velo supports single-line and nested block comments:

\`\`\`rust
// This is a single-line comment

/* This is a block comment.
   /* Block comments can be nested safely! */
   Useful for commenting out large blocks of code. */
\`\`\``
        },
        {
          id: 'keywords',
          title: 'The 28 Reserved Keywords',
          content: `The following keywords are reserved in Velo:`,
          table: {
            headers: ['Keyword', 'Purpose / Description'],
            rows: [
              ['act', 'Declares functions, routines, procedures, and method callbacks'],
              ['data', 'Declares unboxed composite struct types with flat C-ABI layouts'],
              ['kind', 'Declares first-class enums and tagged unions with payloads'],
              ['aka', 'Declares domain-specific type aliases (aka EntityId = u64)'],
              ['mut', 'Declares a mutable variable binding'],
              ['let', 'Declares an immutable variable binding (optional, default)'],
              ['if / else', 'Conditional execution branching'],
              ['loop', 'Universal iteration construct (replaces while, for, repeat)'],
              ['in', 'Specifies iteration range or collection membership'],
              ['return', 'Returns an optional value from a function'],
              ['zone', 'Defines a hardware arena memory block with 1-cycle reset'],
              ['extern', 'Declares foreign C function interfaces without glue code'],
              ['defer', 'Registers a statement to execute in LIFO order upon block exit'],
              ['use', 'Imports files or standard library modules'],
              ['on', 'Pattern matching over scalars, enums, and tagged unions'],
              ['as', 'Explicit type casting operator (e.g. x as f32)'],
              ['sizeof', 'Returns the memory size of a type in bytes'],
              ['break / continue', 'Loop control jump statements'],
              ['and / or / not', 'Logical boolean operators (aliases for &&, ||, !)'],
              ['true / false / null', 'Standard boolean literals and null pointer sentinel'],
              ['op', 'Declares custom operator overloading (act op +)'],
              ['test / assert', 'Native integrated test assertion and test blocks']
            ]
          }
        },
        {
          id: 'contextual-keywords',
          title: 'Contextual Identifiers',
          content: `To keep syntax natural, words like \`data\`, \`kind\`, \`op\`, \`in\`, and \`of\` are **context-sensitive**. You can freely use \`data\` or \`kind\` as variable names or struct fields without compiler syntax errors:

\`\`\`rust
let data = "payload"     // Valid: 'data' is a variable here
let kind = 1             // Valid: 'kind' is an identifier here
\`\`\``
        }
      ],
      prevPage: { title: 'Project Structure & Modules', slug: 'getting-started-project-structure' },
      nextPage: { title: 'Variables & Immutability', slug: 'lang-variables-immutability' }
    },
    {
      id: 'lang-variables-immutability',
      slug: 'lang-variables-immutability',
      title: 'Variables & Immutability',
      category: '03. Language Fundamentals',
      categoryOrder: 3,
      order: 2,
      description: 'Understanding let vs mut: why variables are immutable by default and how Velo verifies mutability.',
      readTimeMinutes: 5,
      whatYoullLearn: [
        'Immutable by default philosophy',
        'Declaring mutable variables with mut',
        'Automatic type inference',
        'How the compiler catches invalid mutation attempts'
      ],
      sections: [
        {
          id: 'immutable-default',
          title: 'Immutable by Default',
          content: `In Velo, safety and clarity start with immutability. Variables declared without \`mut\` (or with \`let\`) are **strictly immutable**. Reassigning or mutating an immutable variable halts compilation immediately:`,
          codeExamples: [
            {
              title: 'immutability.vl',
              language: 'velo',
              code: `max_players: i32 = 64
let server_name = "Velo US-East"

// ❌ COMPILE ERROR:
// max_players = 128
// [Velo Error] cannot assign to immutable variable 'max_players'.
// Declare with 'mut max_players' to allow mutation.`
            }
          ]
        },
        {
          id: 'mutable-variables',
          title: 'Declaring Mutable Variables (mut)',
          content: `When you need a variable to change over time, explicitly declare it with \`mut\`:`,
          codeExamples: [
            {
              title: 'mut_variables.vl',
              language: 'velo',
              code: `mut active_connections: i32 = 0
active_connections += 1 // OK: mutation permitted

mut player_score = 100
player_score *= 2       // OK: 200`
            }
          ]
        },
        {
          id: 'type-inference',
          title: 'Type Inference',
          content: `When initializing a variable, you can omit the explicit type annotation. Velo automatically infers the precise type:

\`\`\`rust
speed = 100           // Inferred as i32
ratio = 0.5           // Inferred as f32
is_connected = true   // Inferred as bool
message = "Ready"     // Inferred as string
\`\`\``
        }
      ],
      prevPage: { title: 'Lexical Grammar & Keywords', slug: 'lang-lexical-grammar' },
      nextPage: { title: 'Primitive Data Types', slug: 'lang-primitive-types' }
    },
    {
      id: 'lang-primitive-types',
      slug: 'lang-primitive-types',
      title: 'Primitive Data Types',
      category: '03. Language Fundamentals',
      categoryOrder: 3,
      order: 3,
      description: 'Explore explicit bit-width integers, IEEE-754 floats, booleans, pointer sizes, and strings.',
      readTimeMinutes: 5,
      whatYoullLearn: [
        'All primitive types and exact byte sizes',
        'Signed and unsigned integers (i8-i64, u8-u64)',
        'Pointer-sized integers (usize, isize)',
        'C99 ABI equivalents'
      ],
      sections: [
        {
          id: 'type-table',
          title: 'The Primitive Types Table',
          content: `Velo mandates explicit bit sizes across all primitive types to guarantee cross-platform predictability between Windows, Linux, and embedded architectures:`,
          table: {
            headers: ['Type', 'Description', 'Size', 'Value Range', 'C99 ABI Equivalent'],
            rows: [
              ['i8', 'Signed 8-bit integer', '1 byte', '-128 to 127', 'int8_t'],
              ['i16', 'Signed 16-bit integer', '2 bytes', '-32,768 to 32,767', 'int16_t'],
              ['i32', 'Signed 32-bit integer', '4 bytes', '-2,147,483,648 to 2,147,483,647', 'int32_t'],
              ['i64', 'Signed 64-bit integer', '8 bytes', '-9.22e18 to 9.22e18', 'int64_t'],
              ['u8', 'Unsigned 8-bit byte', '1 byte', '0 to 255', 'uint8_t'],
              ['u16', 'Unsigned 16-bit integer', '2 bytes', '0 to 65,535', 'uint16_t'],
              ['u32', 'Unsigned 32-bit integer', '4 bytes', '0 to 4,294,967,295', 'uint32_t'],
              ['u64', 'Unsigned 64-bit integer', '8 bytes', '0 to 1.84e19', 'uint64_t'],
              ['f32', 'Single-precision float', '4 bytes', 'IEEE 754 32-bit float', 'float'],
              ['f64', 'Double-precision float', '8 bytes', 'IEEE 754 64-bit float', 'double'],
              ['bool', 'Boolean flag', '1 byte', 'true or false', 'bool (stdbool.h)'],
              ['usize', 'Pointer-sized unsigned int', '4 or 8 bytes', '0 to memory limit', 'size_t'],
              ['isize', 'Pointer-sized signed int', '4 or 8 bytes', 'pointer difference', 'ptrdiff_t'],
              ['string', 'UTF-8 string slice/view', 'Pointer + Len', 'Immutable UTF-8 text', 'const char*'],
              ['void', 'Absence of value', '0 bytes', 'Unit type', 'void']
            ]
          }
        },
        {
          id: 'numeric-literals',
          title: 'Numeric Literals & Formatting',
          content: `Velo supports standard base notations and visual readability underscores:

\`\`\`rust
let decimal = 1_000_000       // Underscores for readability
let hex_mask = 0xFF00AA       // Hexadecimal (0x)
let bin_flags = 0b1011_0010   // Binary (0b)
let octal_val = 0o755         // Octal (0o)
let pi = 3.14159265           // Floating-point
\`\`\``
        }
      ],
      prevPage: { title: 'Variables & Immutability', slug: 'lang-variables-immutability' },
      nextPage: { title: 'Operators & Precedence', slug: 'lang-operators-precedence' }
    },
    {
      id: 'lang-operators-precedence',
      slug: 'lang-operators-precedence',
      title: 'Operators & Precedence',
      category: '03. Language Fundamentals',
      categoryOrder: 3,
      order: 4,
      description: 'The complete 10-level operator precedence table, associativity rules, and the vital @ vs . binding precedence.',
      readTimeMinutes: 6,
      badge: 'Reference',
      whatYoullLearn: [
        'All 10 operator precedence tiers from highest to lowest',
        'Prefix @ address-of operator precedence',
        'Member access . vs @ precedence resolution',
        'Range operators (.. and ..=)'
      ],
      sections: [
        {
          id: 'precedence-table',
          title: 'Operator Precedence Table',
          content: `Operators in Velo are evaluated in the following strict order (Level 1 is highest precedence; Level 10 is lowest):`,
          table: {
            headers: ['Level', 'Operators', 'Description', 'Associativity'],
            rows: [
              ['1 (Highest)', '. () []', 'Member access, function call, array index', 'Left-to-right'],
              ['2', '@', 'Address-of prefix operator (@val)', 'Right-to-left'],
              ['2', '! not - ~', 'Logical NOT, unary negation, bitwise NOT', 'Right-to-left'],
              ['2', 'as', 'Explicit type cast (x as f32)', 'Left-to-right'],
              ['3', '* / %', 'Multiplication, division, modulo', 'Left-to-right'],
              ['4', '+ -', 'Addition, subtraction', 'Left-to-right'],
              ['5', '<< >>', 'Bitwise shift left, shift right', 'Left-to-right'],
              ['5', '.. ..=', 'Range creation (0..10, 1..=5)', 'Non-associative'],
              ['6', '< <= > >=', 'Relational comparisons', 'Left-to-right'],
              ['7', '== !=', 'Equality, inequality', 'Left-to-right'],
              ['8', '& | ^', 'Bitwise AND, OR, XOR', 'Left-to-right'],
              ['9', 'and && or ||', 'Logical boolean AND, OR', 'Left-to-right'],
              ['10 (Lowest)', '= += -= *= /=', 'Assignment and compound assignments', 'Right-to-left']
            ]
          }
        },
        {
          id: 'at-vs-dot',
          title: 'Critical Rule: @ vs . Precedence',
          content: `Because member access \`.\` (Level 1) binds tighter than the address operator \`@\` (Level 2):

- \`@player.pos.x\` evaluates as \`@((player.pos).x)\` — it takes the memory address of the nested \`x\` field.
- To take the address of \`player\` itself before accessing fields, use explicit parentheses: \`(@player).pos\`.`,
          callout: {
            type: 'important',
            title: 'Design Consistency',
            text: 'This precedence rule ensures that taking the address of struct fields (@entity.health) works naturally without requiring cumbersome parentheses.'
          }
        }
      ],
      prevPage: { title: 'Primitive Data Types', slug: 'lang-primitive-types' },
      nextPage: { title: 'Strings & Interpolation', slug: 'lang-strings-interpolation' }
    },
    {
      id: 'lang-strings-interpolation',
      slug: 'lang-strings-interpolation',
      title: 'Strings & Interpolation',
      category: '03. Language Fundamentals',
      categoryOrder: 3,
      order: 5,
      description: 'UTF-8 strings, raw string literals, escape sequences, and compile-time string interpolation.',
      readTimeMinutes: 5,
      whatYoullLearn: [
        'String literals and raw backtick strings',
        'String interpolation syntax: {expr}',
        'Arbitrary expressions, function calls, and UFCS inside interpolation',
        'How Velo desugars interpolation at compile time'
      ],
      sections: [
        {
          id: 'string-literals',
          title: 'String Literals & Raw Strings',
          content: "Velo provides two string literal formats:\n\n1. **Standard Double-Quoted Strings**: Supports escape sequences (\\n, \\t, \\\", \\\\, \\uXXXX) and string interpolation:\n```rust\nlet msg = \"Hello\\nWorld!\"\n```\n\n2. **Raw String Literals**: Enclosed in backticks (`...`). Disables all escape processing, preserving verbatim text and multiline content:\n```rust\nlet raw_path = `C:\\new_folder\\test\\bin`\n```"
        },
        {
          id: 'interpolation',
          title: 'Compile-Time String Interpolation',
          content: `Strings containing \`{expression}\` syntax are desugared at compile time into formatted output without runtime parsing overhead:`,
          codeExamples: [
            {
              title: 'interpolation.vl',
              language: 'velo',
              code: `use std.io

act square(n: i32) -> i32 { return n * n }

act main() {
    let name = "Velo"
    let fps = 120
    let temp = 36.6

    // Variables, expressions, and function calls inside {}:
    io.println("Engine {name} running at {fps} FPS (temp: {temp}C)")
    io.println("Math: 2 + 2 = {2 + 2}")
    io.println("Square of 9: {square(9)}")
}`
            }
          ]
        },
        {
          id: 'lowering-rules',
          title: 'Compiler Lowering Rules for {}',
          content: `The compiler inspects expression types in the Symbol Table and generates optimal C format specifiers:
- \`i8\`..\`i64\`, \`isize\` $\\to$ \`%lld\` with \`(long long)\` cast.
- \`u8\`..\`u64\`, \`usize\` $\\to$ \`%llu\` with \`(unsigned long long)\` cast.
- \`f32\`, \`f64\` $\\to$ \`%f\` / \`%.6f\`.
- \`bool\` $\\to$ evaluated as \`(expr ? "true" : "false")\`.
- \`string\` $\\to$ \`%s\`.
- \`@T\` (pointers) $\\to$ \`%p\` with \`(void*)\` cast.`
        }
      ],
      prevPage: { title: 'Operators & Precedence', slug: 'lang-operators-precedence' },
      nextPage: { title: 'Type Aliases & Casting', slug: 'lang-type-aliases' }
    },
    {
      id: 'lang-type-aliases',
      slug: 'lang-type-aliases',
      title: 'Type Aliases & Casting',
      category: '03. Language Fundamentals',
      categoryOrder: 3,
      order: 6,
      description: 'Domain-specific type definitions with aka and safe bit-level type conversions with as.',
      readTimeMinutes: 4,
      whatYoullLearn: [
        'Declaring type aliases with the aka keyword',
        'Order-free alias resolution rules',
        'Type casting with the as operator'
      ],
      sections: [
        {
          id: 'type-aliases',
          title: 'Type Aliases (aka)',
          content: `A type alias assigns a domain-specific name to an existing primitive type. In Velo, type aliases are declared with the 3-letter keyword \`aka\`:`,
          codeExamples: [
            {
              title: 'aliases.vl',
              language: 'velo',
              code: `aka EntityId = u64
aka HealthPoints = i32
aka FrameTime = f32
aka Pixels = @u8

act damage(id: EntityId, hp: @HealthPoints, amount: HealthPoints) {
    hp.@ -= amount
}`
            }
          ]
        },
        {
          id: 'alias-rules',
          title: 'Alias Semantics & Order-Free Resolution',
          content: `- **Primitives & Pointers**: The target of \`aka\` must be a primitive type or a pointer to primitive (e.g. \`aka TexPtr = @u8\`).
- **Order-Free**: Aliases are collected from the entire program (including across imported modules) before type checking, so an alias can be declared after its use site.
- **Zero Overhead**: In emitted C, aliases generate standard \`typedef\` declarations with zero runtime indirection.`
        },
        {
          id: 'type-casting',
          title: 'Type Casting (as)',
          content: `Explicit conversion between numeric and pointer types uses the \`as\` keyword:

\`\`\`rust
let total_count: i64 = 100
let progress_ratio = (current_step as f32) / (total_count as f32)
let byte_ptr = raw_buffer as @u8
\`\`\``
        }
      ],
      prevPage: { title: 'Strings & Interpolation', slug: 'lang-strings-interpolation' },
      nextPage: { title: 'Conditionals (if/else)', slug: 'control-flow-conditionals' }
    }
  ]
};
