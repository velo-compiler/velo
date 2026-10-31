import { DocCategory } from '../../types/docs';

export const FUNCTIONS_CATEGORY: DocCategory = {
  id: 'functions',
  name: '05. Functions & Methods',
  description: 'Function declarations, first-class function pointers, callbacks, and Uniform Function Call Syntax (UFCS).',
  iconName: 'Cpu',
  pages: [
    {
      id: 'functions-declarations',
      slug: 'functions-declarations',
      title: 'Function Declarations (act)',
      category: '05. Functions & Methods',
      categoryOrder: 5,
      order: 1,
      description: 'Declaring routines with act, parameter definitions, return types, and the main entry point.',
      readTimeMinutes: 5,
      whatYoullLearn: [
        'The act keyword for declaring routines',
        'Typed parameter lists and return signatures (-> Type)',
        'Omitting return types for void functions',
        'The act main() program entry point'
      ],
      sections: [
        {
          id: 'syntax',
          title: 'Function Syntax',
          content: `In Velo, executable routines and functions are declared with the 3-letter keyword \`act\`:`,
          codeExamples: [
            {
              title: 'functions.vl',
              language: 'velo',
              code: `use std.io

// Function taking two integers and returning an integer:
act add(a: i32, b: i32) -> i32 {
    return a + b
}

// Void function: '-> void' can be omitted
act log_info(msg: string) {
    io.println("[INFO] {msg}")
}

act main() {
    let result = add(15, 27)
    log_info("Calculation result: {result}")
}`
            }
          ]
        },
        {
          id: 'main-entry',
          title: 'The act main Entry Point',
          content: `Every executable Velo application defines an \`act main()\` function. It can return \`void\` (implicit exit code 0) or return an \`i32\` status code:

\`\`\`rust
act main() -> i32 {
    io.println("Running...")
    return 0 // Success
}
\`\`\``
        }
      ],
      prevPage: { title: 'Pattern Matching (on)', slug: 'control-flow-pattern-matching' },
      nextPage: { title: 'Function Pointers & Callbacks', slug: 'functions-pointers-callbacks' }
    },
    {
      id: 'functions-pointers-callbacks',
      slug: 'functions-pointers-callbacks',
      title: 'Function Pointers & Callbacks',
      category: '05. Functions & Methods',
      categoryOrder: 5,
      order: 2,
      description: 'First-class function types act(...) -> Ret, passing routines as arguments, struct vtables, and anonymous closures.',
      readTimeMinutes: 6,
      badge: 'Advanced',
      whatYoullLearn: [
        'Function pointer signatures (act(i32, i32) -> i32)',
        'Passing named functions as callbacks to higher-order functions',
        'Storing function pointers in struct fields (manual vtables and UI callbacks)',
        'Inline anonymous functions'
      ],
      sections: [
        {
          id: 'function-types',
          title: 'First-Class Function Types',
          content: `Velo treats functions as first-class citizens using canonical \`act(...) -> Ret\` type signatures:`,
          codeExamples: [
            {
              title: 'function_pointers.vl',
              language: 'velo',
              code: `use std.io

act multiply(a: i32, b: i32) -> i32 { return a * b }
act add(a: i32, b: i32) -> i32 { return a + b }

// Higher-order function: accepts a function pointer
act apply_binary(x: i32, y: i32, op: act(i32, i32) -> i32) -> i32 {
    return op(x, y)
}

act main() {
    // Storing function pointer in a variable:
    let callback: act(i32, i32) -> i32 = multiply
    let res1 = apply_binary(6, 7, callback) // 42
    let res2 = apply_binary(10, 20, add)    // 30
    io.println("res1: {res1}, res2: {res2}")
}`
            }
          ]
        },
        {
          id: 'struct-callbacks',
          title: 'Struct Callbacks & Vtables',
          content: `Structs can store function pointers for event handlers, game hooks, and virtual dispatch:`,
          codeExamples: [
            {
              title: 'button_callback.vl',
              language: 'velo',
              code: `data Button {
    id: i32
    label: string
    on_click: act(@Button)
}

act handle_click(b: @Button) {
    io.println("Button {b.id} ({b.label}) was clicked!")
}

act main() {
    mut btn = Button{ id: 101, label: "Submit", on_click: handle_click }
    if btn.on_click != null {
        btn.on_click(@btn)
    }
}`
            }
          ]
        },
        {
          id: 'anonymous-functions',
          title: 'Anonymous Inline Functions',
          content: `You can declare anonymous functions directly inline:

\`\`\`rust
let calc = act(x: i32, y: i32) -> i32 { return x * 2 + y }
let val = calc(10, 5) // 25
\`\`\`

The compiler lifts anonymous functions into static C99 functions with generated forward prototypes.`
        }
      ],
      prevPage: { title: 'Function Declarations (act)', slug: 'functions-declarations' },
      nextPage: { title: 'Uniform Function Call Syntax (UFCS)', slug: 'functions-ufcs' }
    },
    {
      id: 'functions-ufcs',
      slug: 'functions-ufcs',
      title: 'Uniform Function Call Syntax (UFCS)',
      category: '05. Functions & Methods',
      categoryOrder: 5,
      order: 3,
      description: 'Call any top-level function as a method on its first argument, with automatic borrowing and dereferencing.',
      readTimeMinutes: 6,
      badge: 'Core Feature',
      whatYoullLearn: [
        'How UFCS eliminates the need for class and impl boilerplate',
        'Automatic address borrowing (&) when methods require pointers',
        'Automatic dereferencing (*) when methods expect values',
        'Method chaining and primitive type extension'
      ],
      sections: [
        {
          id: 'ufcs-concept',
          title: 'What is UFCS?',
          content: `In traditional object-oriented languages, methods are trapped inside \`class\` definitions. In Velo, **any free function whose first parameter matches a type can be called using method syntax (\`receiver.method(args)\`)**:`,
          codeExamples: [
            {
              title: 'ufcs_example.vl',
              language: 'velo',
              code: `use std.io

data Vector2 {
    x: f32
    y: f32
}

// 1. Value method: takes Vector2 by value
act length_sq(v: Vector2) -> f32 {
    return v.x * v.x + v.y * v.y
}

// 2. Pointer method: takes @Vector2 to mutate in place
act scale(v: @Vector2, factor: f32) {
    v.x *= factor
    v.y *= factor
}

act main() {
    mut vec = Vector2{ x: 3.0, y: 4.0 }

    // Direct method calls:
    let len = vec.length_sq() // calls length_sq(vec) -> 25.0
    vec.scale(2.0)            // auto-borrows address: scale(&vec, 2.0)

    io.println("Length squared: {len}")
    io.println("Scaled vector: ({vec.x}, {vec.y})")
}`
            }
          ]
        },
        {
          id: 'auto-borrow',
          title: 'Auto-Borrowing & Auto-Dereferencing',
          content: `Notice what happened when calling \`vec.scale(2.0)\`:
- The function \`scale\` expects a pointer parameter: \`v: @Vector2\`.
- The caller provided a value variable: \`vec: Vector2\`.
- **The Velo compiler automatically passed the memory address \`&vec\`!**

Similarly, if a function takes a value \`T\` and you call it on a pointer \`@T\`, the compiler automatically dereferences the pointer (\`*ptr\`). You never have to manually juggle \`&\` and \`*\` at call sites.`
        },
        {
          id: 'primitive-extension',
          title: 'Extending Primitive Types',
          content: `UFCS works equally well on primitive types:

\`\`\`rust
act square(n: i32) -> i32 { return n * n }

let val = 7.square() // 49
\`\`\``
        }
      ],
      prevPage: { title: 'Function Pointers & Callbacks', slug: 'functions-pointers-callbacks' },
      nextPage: { title: 'Structs (data)', slug: 'types-structs' }
    }
  ]
};

