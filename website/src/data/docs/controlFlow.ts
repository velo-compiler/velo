import { DocCategory } from '../../types/docs';

export const CONTROL_FLOW_CATEGORY: DocCategory = {
  id: 'control-flow',
  name: '04. Control Flow',
  description: 'Conditionals, the universal loop keyword with 6 iteration modes, break/continue, and pattern matching.',
  iconName: 'GitBranch',
  pages: [
    {
      id: 'control-flow-conditionals',
      slug: 'control-flow-conditionals',
      title: 'Conditionals (if / else)',
      category: '04. Control Flow',
      categoryOrder: 4,
      order: 1,
      description: 'Branching logic in Velo: optional parentheses, mandatory curly braces, and logical operators.',
      readTimeMinutes: 4,
      whatYoullLearn: [
        'Syntax of if, else if, and else in Velo',
        'Optional parentheses around condition expressions',
        'Mandatory curly braces {}',
        'Boolean logical operators (and, or, not, &&, ||, !)'
      ],
      sections: [
        {
          id: 'syntax',
          title: 'Syntax & Branching',
          content: `Velo adopts modern, clean conditional syntax: parentheses around conditions are completely optional, but curly braces \`{}\` are strictly mandatory to eliminate dangling-else ambiguities:`,
          codeExamples: [
            {
              title: 'conditionals.vl',
              language: 'velo',
              code: `use std.io

act evaluate_health(health: i32) {
    if health <= 0 {
        io.println("Player Defeated")
    } else if health < 25 {
        io.println("Warning: Critical Low Health!")
    } else if health < 75 {
        io.println("Player Injured")
    } else {
        io.println("Player at Full Health")
    }
}`
            }
          ]
        },
        {
          id: 'logical-operators',
          title: 'Logical Operators',
          content: `Velo allows both word-based and symbol-based logical operators:

- \`and\` or \`&&\`: Logical AND (short-circuiting)
- \`or\` or \`||\`: Logical OR (short-circuiting)
- \`not\` or \`!\`: Logical negation

\`\`\`rust
if is_alive and (stamina > 10 or has_shield) {
    perform_action()
}
\`\`\``
        }
      ],
      prevPage: { title: 'Type Aliases & Casting', slug: 'lang-type-aliases' },
      nextPage: { title: 'The Universal Loop Keyword', slug: 'control-flow-loops' }
    },
    {
      id: 'control-flow-loops',
      slug: 'control-flow-loops',
      title: 'The Universal Loop Keyword',
      category: '04. Control Flow',
      categoryOrder: 4,
      order: 2,
      description: 'Velo standardizes all iteration on one single, expressive keyword: loop. Explore all 6 iteration modes.',
      readTimeMinutes: 6,
      badge: 'Core Feature',
      whatYoullLearn: [
        'Why Velo unifies for, while, and repeat into a single loop keyword',
        'The implicit it counter variable',
        'The 6 iteration patterns (infinite, repeat N, conditional, range, reverse countdown, inclusive)',
        'Range slices with custom step increments (:step)'
      ],
      sections: [
        {
          id: 'universal-loop',
          title: 'One Keyword for All Iteration',
          content: `Instead of cluttering the language with separate \`for\`, \`while\`, \`do-while\`, and \`repeat\` keywords, Velo standardizes on a **single versatile keyword: \`loop\`**. The compiler inspects the loop header and emits optimized C99 loops.`,
          codeExamples: [
            {
              title: 'all_loops.vl',
              language: 'velo',
              code: `use std.io

act main() {
    // 1. Repeat Count Loop: repeats N times, 'it' counter starts at 0
    io.println("--- 1. Repeat Loop ---")
    loop 3 {
        io.println("Repeat iteration: {it}")
    }

    // 2. Condition Loop: executes while boolean is true (replaces while)
    io.println("--- 2. Condition Loop ---")
    mut energy = 3
    loop energy > 0 {
        io.println("Energy remaining: {energy} (tick #{it})")
        energy -= 1
    }

    // 3. Named Range Loop with custom step: loop i in start..end:step
    io.println("--- 3. Range with Step ---")
    loop i in 0..10:2 {
        io.println("Step 2: {i}") // 0, 2, 4, 6, 8
    }

    // 4. Smart Auto-Countdown: counts down automatically when start > end
    io.println("--- 4. Countdown ---")
    loop 3..0 {
        io.println("Liftoff in: {it}") // 3, 2, 1
    }

    // 5. Inclusive Range: using ..=
    io.println("--- 5. Inclusive Range ---")
    loop i in 1..=3 {
        io.println("Inclusive: {i}") // 1, 2, 3
    }

    // 6. Infinite Loop: with break
    io.println("--- 6. Infinite Loop ---")
    loop {
        if it == 2 {
            io.println("Breaking infinite loop at it = {it}")
            break
        }
    }
}`
            }
          ]
        },
        {
          id: 'the-it-variable',
          title: 'The Implicit it Variable',
          content: `In loops where you don't provide an explicit named variable (such as \`loop 5\` or \`loop condition\`), Velo automatically provides an implicit iteration counter named **\`it\`**. It starts at \`0\` and increments with each iteration.`,
          callout: {
            type: 'tip',
            title: 'Clean Syntax',
            text: 'The implicit it counter removes boilerplate index variables when performing simple repeated actions or polling loops.'
          }
        }
      ],
      prevPage: { title: 'Conditionals (if/else)', slug: 'control-flow-conditionals' },
      nextPage: { title: 'Break and Continue', slug: 'control-flow-break-continue' }
    },
    {
      id: 'control-flow-break-continue',
      slug: 'control-flow-break-continue',
      title: 'Break and Continue',
      category: '04. Control Flow',
      categoryOrder: 4,
      order: 3,
      description: 'Control loop execution flow: terminating early with break and advancing with continue.',
      readTimeMinutes: 4,
      whatYoullLearn: [
        'How break exits the nearest enclosing loop',
        'How continue skips the remaining block statements',
        'Nested loop control behavior'
      ],
      sections: [
        {
          id: 'break-continue',
          title: 'Using break and continue',
          content: `Within any \`loop\` block:
- \`break\`: Exits immediately from the loop, jumping to the statement following the loop's closing brace.
- \`continue\`: Skips the remainder of the current iteration and advances directly to the next loop cycle:`,
          codeExamples: [
            {
              title: 'break_continue.vl',
              language: 'velo',
              code: `use std.io

act find_target() {
    loop i in 0..100 {
        if i % 2 == 0 {
            continue // Skip even numbers
        }
        if i > 7 {
            break // Halt iteration
        }
        io.println("Odd number: {i}") // Prints 1, 3, 5, 7
    }
}`
            }
          ]
        }
      ],
      prevPage: { title: 'The Universal Loop Keyword', slug: 'control-flow-loops' },
      nextPage: { title: 'Pattern Matching (on)', slug: 'control-flow-pattern-matching' }
    },
    {
      id: 'control-flow-pattern-matching',
      slug: 'control-flow-pattern-matching',
      title: 'Pattern Matching (on)',
      category: '04. Control Flow',
      categoryOrder: 4,
      order: 4,
      description: 'Exhaustive and structured pattern matching over scalar values, enums, and tagged union payloads.',
      readTimeMinutes: 6,
      badge: 'Core Feature',
      whatYoullLearn: [
        'Syntax of the on statement',
        'Pattern matching against scalar values and enums',
        'Deconstructing tagged union variants with payload variables',
        'Contextual dot-shorthand (.Variant)'
      ],
      sections: [
        {
          id: 'on-statement',
          title: 'The on Statement',
          content: `Velo replaces bulky \`switch\` statements with the concise \`on\` keyword. It supports scalar values, pure enums, and payload-bearing tagged unions:`,
          codeExamples: [
            {
              title: 'pattern_matching.vl',
              language: 'velo',
              code: `use std.io

kind Event {
    Quit
    KeyDown: i32
    Click(button: i32, x: f32, y: f32)
}

act dispatch(e: Event) {
    on e {
        .Quit => {
            io.println("Application Quitting")
        }
        .KeyDown(code) => {
            io.println("Key pressed: {code}")
        }
        .Click(btn, x, y) => {
            io.println("Mouse button {btn} clicked at ({x}, {y})")
        }
    }
}`
            }
          ]
        },
        {
          id: 'payload-extraction',
          title: 'Automatic Payload Binding',
          content: `Notice how parameters in \`.KeyDown(code)\` and \`.Click(btn, x, y)\` are automatically extracted and scoped to that specific arm. In emitted C99 code, this translates to type-safe \`union\` member accesses with zero dynamic casting overhead.`
        }
      ],
      prevPage: { title: 'Break and Continue', slug: 'control-flow-break-continue' },
      nextPage: { title: 'Function Declarations (act)', slug: 'functions-declarations' }
    }
  ]
};

