# Velo Language Specification

This document formally specifies the lexical grammar, type system, operator precedence, statements, expressions, and memory semantics of the **Velo** programming language for **Stage 2 (Self-Hosted Native Compiler)**.

---

## 1. Lexical Structure

### 1.1 Source Encoding
Velo source files are UTF-8 encoded text files with the `.vl` extension. Files must not begin with a UTF-8 Byte Order Mark (BOM).

### 1.2 Comments
* Single-line comments start with `//` and extend to the end of the line.
```rust
// This is a single-line comment in Velo
```
* Block comments are enclosed in `/* ... */` (nested comments supported).
```rust
/* This is a /* nested */ block comment */
```
* Documentation comments start with `///` and attach to following declarations.

### 1.3 Identifiers
Identifiers name variables, functions, types, and fields.
* Must start with an ASCII letter (`a-z`, `A-Z`) or an underscore `_`.
* May be followed by letters, digits (`0-9`), or underscores.
* Case-sensitive (`foo` and `Foo` are distinct).

### 1.4 Keywords
The following keywords are reserved in Velo:
```
act       data      mut       let       if        else
loop      in        return    zone      extern    defer
use       true      false     null      sizeof    as
break     continue  on        and       or        not
kind      fail
```

Contextual keywords recognized in specific declaration or expression contexts include `aka`, `op`, and `unsafe`.

### 1.5 Punctuation & Semicolons
* Code blocks are delimited by curly braces `{` and `}`.
* **Semicolons are optional**: Newlines act as statement terminators. Semicolons `;` may be used to place multiple statements on the same line.

### 1.6 Operator Precedence & Associativity
Operators are evaluated in the following order (from highest precedence to lowest):

| Precedence | Operator | Description | Associativity |
| :---: | :--- | :--- | :---: |
| **1 (Highest)** | `.` `()` `[]` | Member access, function call, array index, tuple member (`t.0`) | Left-to-right |
| **2** | `@` (prefix) | Address-of operator | Right-to-left |
| **2** | `!` `not` `-` (unary) | Logical NOT, bitwise NOT, arithmetic negation | Right-to-left |
| **2** | `as` | Type casting (`x as f32`) | Left-to-right |
| **3** | `*` `/` `%` | Multiplication, division, modulo | Left-to-right |
| **4** | `+` `-` | Addition, subtraction, string concatenation (`+`) | Left-to-right |
| **5** | `..` `..=` | Range creation (`0..10`, `1..=5`) | Non-associative |
| **6** | `<` `<=` `>` `>=` | Relational comparisons | Left-to-right |
| **7** | `==` `!=` | Equality comparisons (scalar, enum, string, pointer) | Left-to-right |
| **8** | `and` `&&` | Logical AND (short-circuiting) | Left-to-right |
| **9** | `or` `\|\|` | Logical OR (short-circuiting) | Left-to-right |
| **10 (Lowest)**| `=` `+=` `-=` `*=` `/=` | Assignment operators, string append (`+=`) | Right-to-left |

> [!NOTE]
> **Precedence Rule for `@` vs `.`**:
> Because `.` (precedence 1) binds tighter than `@` (precedence 2):
> * `@player.pos.x` evaluates as `@((player.pos).x)` — it takes the memory address of the `x` field.
> * To take the address of `player` first, use parentheses: `(@player).pos`.

### 1.7 Expression Evaluation Order & Associativity
* Binary expressions, function call arguments, and struct literal fields evaluate in strict **left-to-right** order.
* Logical `and` (`&&`) and `or` (`||`) short-circuit: the right-hand operand is not evaluated if the left-hand operand determines the result.
* The `or return` outcome unwrapping operator evaluates its operand; if it represents an error outcome, execution immediately returns the error from the enclosing function.

---

## 2. Type System

### 2.1 Primitive Types
Velo requires explicit bit sizes to guarantee cross-platform predictability:

| Type | Description | Size | C Equivalent |
| :--- | :--- | :--- | :--- |
| `i8`, `i16`, `i32`, `i64` | Signed integers | 1, 2, 4, 8 bytes | `int8_t`, `int16_t`, `int32_t`, `int64_t` |
| `u8`, `u16`, `u32`, `u64` | Unsigned integers | 1, 2, 4, 8 bytes | `uint8_t`, `uint16_t`, `uint32_t`, `uint64_t` |
| `f32`, `f64` | IEEE 754 floating-point | 4, 8 bytes | `float`, `double` |
| `f32x4`, `i32x4` | 128-bit hardware SIMD vectors | 16 bytes | `__m128`, `__m128i` / vector extensions |
| `bool` | Boolean (`true` or `false`) | 1 byte | `bool` (`stdbool.h`) |
| `usize`, `isize` | Pointer-sized integers | 4 or 8 bytes | `size_t`, `ptrdiff_t` |
| `string` | UTF-8 string view/slice | Pointer + Length | `const char*` (in C99) |
| `void` | Absence of value | 0 bytes | `void` |

### 2.2 Pointer Types (`@T`)
A pointer to a type `T` is denoted as `@T`:
* `@i32`: Pointer to a 32-bit integer (emits `int32_t*` in C).
* `@Particle`: Pointer to a `Particle` struct (emits `Particle*` in C).
* `@@f32`: Pointer to a pointer to a 32-bit float (emits `float**` in C).

### 2.3 User-Defined Types (`data`)
Composite types are declared with the `data` keyword. They have guaranteed flat C-ABI memory layouts:

```rust
data Point {
    x: f32
    y: f32
}
```

### 2.4 First-Class Enums & Tagged Unions (`kind`)
Sum types and enumerations are declared using the 4-letter `kind` keyword. Velo supports pure scalar enums, explicit discriminants, and payload-bearing tagged unions:

```rust
// 1. Pure scalar enum (0 overhead, int32_t in C)
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
}

// 3. Tagged union with single and multi-field payloads
kind Event {
    Quit
    KeyDown: i32
    Click(button: i32, x: f32, y: f32)
}
```

#### Instantiation & Dot-Shorthand:
* Contextual dot-shorthand is supported whenever the target type is known:
  ```rust
  let d: Direction = .North
  let e: Event = .KeyDown(65)
  let click: Event = .Click(1, 100.0, 200.0)
  ```
* Fully-qualified syntax is always valid: `Direction.North`, `Event.Quit`.
* Pure enums lower directly to C99 `int32_t` scalar values.
* Tagged unions lower to a C99 `struct` containing `int32_t kind;` and a payload `union { ... } as;`.

### 2.5 Generics & Parametric Polymorphism
Velo provides zero-runtime-cost parametric polymorphism using square-bracket generic parameters (`[T]`, `[K, V]`). Generic templates for data structs, kinds (tagged unions), and functions are monomorphized into specialized C99 code at compile-time:

#### Generic Structs (`data`):
```rust
data Box[T] {
    value: T
}

data Pair[K, V] {
    key: K
    val: V
}
```

#### Generic Tagged Unions (`kind`):
```rust
kind Option[T] {
    None
    Some: T
}
```

#### Generic Functions (`act`):
```rust
act min[T](a: T, b: T) -> T {
    if a < b { return a }
    return b
}

act swap[T](a: @T, b: @T) {
    let tmp = a.@
    a.@ = b.@
    b.@ = tmp
}
```

#### Instantiation & Type Inference:
* **Struct & Kind Literals**: Instantiated using concrete type arguments:
  ```rust
  let b: Box[i32] = Box[i32]{ value: 42 }
  let opt: Option[string] = .Some("ready")
  ```
* **Call-Site Type Inference**: Generic functions can be called directly without explicit type arguments; Velo automatically infers `T` from argument types:
  ```rust
  let m = min(15, 25) // infers T = i32 -> calls min_i32
  ```
* **Explicit Type Arguments**: Can also be supplied explicitly:
  ```rust
  let mf = min[f32](3.14, 2.71) // calls min_f32
  ```
* **Zero Overhead**: Generics are monomorphized into specialized C99 functions and types (`Box_i32`, `Option_string`, `min_i32`, `Pair_string_i32`) with zero runtime indirection or virtual method table overhead.

### 2.6 Function Pointers & First-Class Callbacks (`act(...) -> Ret`)
Velo supports first-class function pointer types using the canonical `act(...) -> Ret` syntax, harmonizing directly with the function definition keyword `act`.

#### Function Type Signatures:
```rust
act(i32, i32) -> i32        // Takes two i32, returns i32
act(@Button) -> void         // Takes pointer to Button, returns void
act() -> void                // Takes no arguments, returns void
```

#### Storing & Passing Function Pointers:
Named functions can be referenced as expressions and stored in variables or passed as arguments to higher-order functions:
```rust
act add(a: i32, b: i32) -> i32 { return a + b }

let op: act(i32, i32) -> i32 = add
let res = op(10, 20) // Direct execution: 30

act apply_binary(a: i32, b: i32, op: act(i32, i32) -> i32) -> i32 {
    return op(a, b)
}
let sum = apply_binary(7, 8, add)
```

#### Struct Callback Fields & Vtables:
Structs can store function pointer fields for callbacks, event handlers, and manual vtables:
```rust
data Button {
    id: i32
    label: string
    on_click: act(@Button) -> void
}

mut btn = Button{ id: 101, label: "OK", on_click: handle_click }

// Null checking & direct invocation
if btn.on_click != null {
    btn.on_click(@btn)
}
```

#### Inline Anonymous Functions:
Anonymous functions can be defined inline with parameter types and optional return type (defaults to `void`):
```rust
btn.on_click = act(b: @Button) {
    io.println("Clicked button: {b.id}")
}

let calc = act(x: i32, y: i32) -> i32 { return x * 2 + y }
let val = calc(10, 5) // 25
```

### 2.7 Method Syntax / Uniform Function Call Syntax (UFCS)
Velo supports pure Uniform Function Call Syntax (UFCS) without requiring `class`, `impl`, or object-oriented keywords. Any top-level function whose first parameter matches the receiver type can be called using method syntax (`receiver.method(args...)`):

```rust
data Vector2 {
    x: f32
    y: f32
}

act length_sq(v: Vector2) -> f32 {
    return v.x * v.x + v.y * v.y
}

act scale(v: @Vector2, factor: f32) {
    v.x *= factor
    v.y *= factor
}

mut vec = Vector2{ x: 3.0, y: 4.0 }

// Direct UFCS calls:
let len = vec.length_sq()    // calls length_sq(vec) -> 25.0
vec.scale(2.0)              // auto-borrows address: scale(&vec, 2.0)
```

#### Auto-Referencing and Auto-Dereferencing:
* **Auto-Borrow (`&`)**: If the target function expects a pointer `@T` and the caller provides an lvalue of value type `T`, the compiler automatically passes the address of the receiver (`&receiver`).
* **Auto-Dereference (`*`)**: If the target function expects a value `T` and the caller provides a pointer `@T`, the compiler automatically dereferences the pointer (`*receiver`).
* **Direct Match**: If the receiver type already matches the first parameter type (e.g. pointer-to-pointer or value-to-value), it is passed directly without transformation.

#### Struct Field Priority:
Struct fields always take priority over free functions with the same name. If a struct has a function pointer field `on_click`, invoking `btn.on_click(...)` calls the struct's callback field, not a top-level `act on_click(...)`.

### 2.8 Operator Overloading (`act op <symbol>`)
Velo enables custom types (such as game math vectors, matrices, and colors) to overload standard binary and unary operators using the punchy 2-letter `op` prefix. Overloaded operators compile directly to specialized C99 function calls with zero overhead.

```rust
data Vector2 {
    x: f32
    y: f32
}

// 1. Binary addition: Vector2 + Vector2
act op +(a: Vector2, b: Vector2) -> Vector2 {
    return Vector2{ x: a.x + b.x, y: a.y + b.y }
}

// 2. Scalar multiplication: Vector2 * f32 and f32 * Vector2
act op *(v: Vector2, s: f32) -> Vector2 {
    return Vector2{ x: v.x * s, y: v.y * s }
}
act op *(s: f32, v: Vector2) -> Vector2 {
    return Vector2{ x: v.x * s, y: v.y * s }
}

// 3. Unary negation
act op -(v: Vector2) -> Vector2 {
    return Vector2{ x: -v.x, y: -v.y }
}

// 4. Equality comparisons
act op ==(a: Vector2, b: Vector2) -> bool {
    return a.x == b.x and a.y == b.y
}
```

Compound assignments (`pos += vel`) automatically desugar into `pos = pos + vel`, calling the overloaded `+` operator.

### 2.9 Advanced Struct Features (Type Aliases, Field Defaults, `#align`/`#packed`)

#### Type Aliases (`aka Name = T`):
A type alias gives a primitive type a domain-specific name:
```rust
aka EntityId = u64
aka HealthPoints = i32
aka TexBuf = @u8

let entity: EntityId = 42
let next = entity + 1   // alias resolves to u64 statically
```

#### Default Field Initializers:
Struct fields may declare constant default initializers:
```rust
data Vec4 {
    x: f32 = 0.0
    y: f32 = 0.0
    z: f32 = 0.0
    w: f32 = 1.0
}

let v = Vec4{ x: 2.5 }   // v.y == 0.0, v.z == 0.0, v.w == 1.0
```

#### Struct Layout Attributes (`#align(N)` / `#packed`):
```rust
data Vec4 #align(16) { ... }    // struct __attribute__((aligned(16))) Vec4 { ... };
data Blob #packed { ... }       // struct __attribute__((packed)) Blob { ... };
data Item #align(64) #packed { ... }
```

---

### 2.10 Fixed-Size Stack Arrays (`[N]T`)

Velo supports first-class fixed-size stack arrays (`[N]T`), providing deterministic $O(1)$ zero-overhead allocation on the native call stack without heap or arena overhead:

```rust
// 1. Stack buffer declaration (zero-initialized)
mut packet: [64]u8

// 2. Direct element assignment and indexing
packet[0] = 0xAA as u8
packet[1] = 0x55 as u8

// 3. Array properties: .len and .ptr
let count: usize = packet.len   // 64
let raw: @u8 = packet.ptr       // pointer to first element

// 4. Array literals
let primes: [4]i32 = [2, 3, 5, 7]

// 5. Value copy
mut backup: [64]u8
backup = packet                 // lowers to memcpy(backup, packet, sizeof(packet))
```

#### Semantic Rules:
* **Size Constraint**: The array length `N` must be an integer constant strictly greater than 0 (`N > 0`).
* **Compile-Time Bounds Checking**: Constant index expressions (`arr[idx]`) are validated at compile-time. Accessing an index where `idx >= N` or `idx < 0` produces a compile-time error: `[Velo Error] Array index out of bounds`.
* **Mutability Enforcement**: Elements of an array declared with `let` cannot be modified (`cannot assign to element of immutable variable`).
* **Pointer Decay & Compatibility**: A fixed-size array `[N]T` automatically decays to `@T` and `@void` when passed to functions expecting a raw pointer.
* **Function Parameters**: Arrays passed by value (`act handle(buf: [64]u8)`) emit standard C parameter declarations `uint8_t buf[64]`.
* **Struct Embedding**: Structs may contain embedded array fields (`data Header { magic: [4]u8 }`), maintaining flat C memory layout.

---

### 2.11 First-Class Tuples & Multiple Return Values (`-> (A, B)`)

Functions in Velo can return multiple values simultaneously using first-class tuples. Tuples require zero heap allocations and lower to anonymous C99 value structs:

```rust
// 1. Function returning multiple values
act div_rem(n: i32, d: i32) -> (i32, i32) {
    return (n / d, n % d)
}

// 2. Tuple destructuring declaration
let (quotient, remainder) = div_rem(10, 3)

// 3. Mutable destructuring
mut (x, y) = (100, 200)
x += 5

// 4. Wildcard discard (_)
let (result, _) = div_rem(50, 8)

// 5. Positional member access (.0, .1)
let pair = (42, "velo")
let first = pair.0              // 42
let second = pair.1             // "velo"
```

#### Semantic Rules:
* **Tuple Types**: Denoted as `(T0, T1, ...)`.
* **Tuple Literals**: Constructed with parenthesized expressions containing at least one comma: `(e0, e1, ...)`. Single-element grouping expressions `(expr)` remain grouping expressions.
* **Evaluation Guarantee**: During tuple destructuring (`let (a, b) = expr`), the right-hand side expression `expr` is evaluated strictly once into a scoped temporary before binding to variables.
* **Zero Overhead**: Tuples are lowered to lightweight mangled structs (`_Velo_Tuple_T0_T1`) passed and returned directly by value in CPU registers or the stack per the standard platform C-ABI.

---

### 2.12 Optional Types & Compile-Time Null Safety (`?T`)

Velo enforces compile-time null safety using optional types (`?T`). Variables that can hold `null` must be explicitly declared as optional:

```rust
// 1. Optional declarations
mut maybe_name: ?string = null
mut maybe_count: ?i32 = 42

// 2. Direct property checking
if maybe_count.has {
    let val = maybe_count.val   // explicit unwrapping
}
```

#### Flow-Sensitive Type Narrowing:
Velo features flow-sensitive type narrowing. Inside a null-check guard (`if x != null`), the compiler automatically narrows `x` from `?T` to `T`, allowing direct field, method, and operator access without manual unwrapping:

```rust
data Node {
    val: i32
    name: string
}

act process_node(opt: ?@Node) -> i32 {
    // Early exit guard clause narrows 'opt' for the remainder of the block
    if opt == null { return 0 }

    // 'opt' is statically narrowed to @Node here:
    return opt.val + opt.name.len()
}
```

#### Rules & Lowering:
* **Pointer Optionals (`?@T`, `?string`)**: Directly lower to C pointers (`T*`), where `null` maps to `NULL` with zero overhead.
* **Value Optionals (`?i32`, `?bool`, `?Struct`)**: Lower to an unboxed struct `_Velo_Opt_T` containing `bool has;` and `T val;`.
* **Conjunctions**: Conjunctions `if a != null and b != null` simultaneously narrow both `a` and `b`.

---

### 2.13 Algebraic Outcome Types & Error Handling (`T or E`)

Velo eliminates runtime exceptions and unhandled panics by providing first-class algebraic outcome types (`T or E`), representing either a successful value `T` or an error payload `E`:

```rust
// 1. Function returning an outcome type
act parse_port(s: string) -> i32 or string {
    if s.len() == 0 {
        fail "port string is empty"     // constructs error outcome and returns
    }
    let port = s.to_i32()
    if port < 1 or port > 65535 {
        fail "port out of range"
    }
    return port                         // constructs success outcome
}

// 2. Error propagation with 'or return'
act start_server(port_str: string) -> bool or string {
    // Unwraps port on success; immediately returns error on failure:
    let port = parse_port(port_str) or return

    io.println("Server listening on port {port}")
    return true
}

// 3. Explicit inspection via .ok, .val, .err
let outcome = parse_port("8080")
if outcome.ok {
    io.println("Valid port: {outcome.val}")
} else {
    io.println("Error: {outcome.err}")
}
```

#### Semantic Rules:
* **`fail <expr>` Statement**: Can only be used inside a function whose return type is an outcome `T or E`. Constructs an error variant with the given error payload and immediately exits the function.
* **`or return` Operator**: Evaluates an outcome expression. If `outcome.ok` is `true`, it evaluates to `outcome.val`. If `outcome.ok` is `false`, it propagates `fail outcome.err` out of the calling function.
* **Combined Destructuring**: Seamlessly integrates with tuples: `let (data, bytes) = read_socket() or return`.

---

## 3. Variables & Mutability

### 3.1 Immutable by Default
Variables declared without `mut` are immutable:
```rust
x: i32 = 10
let name = "Velo"
// x = 20  --> Compile Error: 'x' is immutable
```

### 3.2 Mutable Variables
Mutable variables must explicitly use the `mut` modifier:
```rust
mut counter: i32 = 0
counter += 1 // OK
```

### 3.3 Type Inference
Types can be inferred when an initial value is provided:
```rust
mut score = 100       // Inferred as i32
ratio = 0.5           // Inferred as f32
is_active = true      // Inferred as bool
```

---

## 4. Functions (`act`)

Functions represent executable routines:

```rust
act add(a: i32, b: i32) -> i32 {
    return a + b
}

// Void return type can omit '-> void'
act log_message(msg: string) {
    io.println(msg)
}
```

The main entry point of every Velo program is:
```rust
act main() {
    // Execution begins here
}
```

Command-line arguments can optionally be received via:
```rust
act main(argc: i32, argv: @string) -> i32 {
    return 0
}
```

---

## 5. Pointers & Memory Semantics

### 5.1 Address-Of (`@`)
The `@` operator placed before an expression takes its memory address:
```rust
mut x: i32 = 42
ptr: @i32 = @x  // ptr holds the memory address of x
```

### 5.2 Auto-Dereferencing Member Access (`.`)
When accessing fields of a struct through a pointer, developers write `.`:
```rust
data Player {
    health: i32
}

act heal(p: @Player, amount: i32) {
    p.health += amount  // Emits: p->health += amount;
}
```

### 5.3 Direct Pointer Value Dereferencing (`.@`)
To read or overwrite the raw value pointed to by a pointer:
```rust
mut val: i32 = 10
p: @i32 = @val
p.@ = 25  // Overwrite memory pointed to by p (emits *p = 25;)
```

### 5.4 The `zone` Memory Allocator
A `zone` block defines a hardware-level bump arena:
* **Mechanism**: 
  1. Entering a `zone` saves the current arena offset (the watermark).
  2. Allocations via `mem.alloc` simply advance the offset ($O(1)$ pointer bump).
  3. Exiting the `zone` restores the saved offset ($O(1)$ instant reset).
* **Guarantees**: Zero GC pauses, zero fragmentation, zero memory leaks.
* **Zone Escape Analysis**: The compiler statically ensures that pointers allocated in an inner `zone` or stack addresses cannot escape into outer variables or return values.

```rust
zone {
    // Allocated on the active thread-local arena
    particles: @Particle = mem.alloc(@Particle, 1000)
    
    // Work with particles...
} // All allocations wiped in 1 CPU instruction here!
```

---

## 6. String Subsystem & Operations

### 6.1 String Interpolation
Strings containing `{expression}` syntax are desugared at compile time into formatted output:

```rust
name = "Velo"
speed = 100
io.println("Running {name} at {speed}% speed!")
```

Arbitrary expressions, function calls, and UFCS methods are supported inside `{}`:
```rust
io.println("Next power of two: {calc_next(speed)}")
```

### 6.2 Native String Concatenation (`+` and `+=`)
Velo supports native string concatenation using binary `+` and in-place `+=`:

```rust
let first = "Hello, "
let full = first + "world!"     // allocates in active zone/heap

mut banner = "Velo"
banner += " v2.0"
```

Concatenation automatically computes the combined string length, allocates the required memory in the active arena, and copies bytes with guaranteed null-termination.

---

## 7. Control Flow

### 7.1 Conditionals (`if` / `else`)
Parentheses around conditions are optional. Braces `{}` are mandatory:
```rust
if health <= 0 {
    io.println("Game Over")
} else if health < 25 {
    io.println("Warning: Low Health")
} else {
    io.println("Healthy")
}
```

### 7.2 Loops (`loop`)
Velo standardizes on a single `loop` keyword covering all iteration patterns:

#### 1. Infinite Loop (`loop { ... }`)
```rust
loop {
    if it == 5 { break }
}
```

#### 2. Count / Repeat Loop (`loop <count> { ... }`)
```rust
loop 5 {
    io.println("Iteration {it}")
}
```

#### 3. Condition Loop (`loop <condition> { ... }`)
```rust
mut x = 10
loop x > 0 {
    io.println("tick #{it}, x is {x}")
    x -= 1
}
```

#### 4. Named Range Loop (`loop <var> in <start>..<end>[:<step>]`)
```rust
loop i in 0..10:2 {
    io.println("Step 2: {i}") // 0, 2, 4, 6, 8
}
```

#### 5. Smart Reverse Auto-Countdown (`loop <start>..<end>`)
```rust
loop 5..0 {
    io.println("Liftoff in {it}...") // 5, 4, 3, 2, 1
}
```

#### 6. Inclusive Range (`..=`)
```rust
loop i in 1..=5 {
    io.println("{i}") // 1, 2, 3, 4, 5
}
```

### 7.3 Pattern Matching (`on`)
The `on` statement performs pattern matching over scalar values, tagged unions, and strings:

#### 1. Tagged Union Matching:
```rust
on event {
    .Quit => { io.println("Quit") }
    .KeyDown(key) => { io.println("Key: {key}") }
    .Click(button, x, y) => { io.println("Click at {x}, {y}") }
}
```

#### 2. String Pattern Matching:
```rust
on method {
    "GET" => { handle_get() }
    "POST" => { handle_post() }
    "DELETE" => { handle_delete() }
    _ => { handle_unknown() }
}
```

### 7.4 First-Class Conditional Expressions (`if-else`)
`if-else` blocks can be used directly as expressions producing values:

```rust
let score = 88
let grade = if score >= 90 { "A" } else if score >= 80 { "B" } else { "C" }

let max_val = if a > b { a } else { b }
```

Both branches are type-checked and automatically widened (`widen_if_branch_types`) to ensure type compatibility. Both `if` and `else` branches are mandatory when used as an expression.

---

## 8. Foreign Function Interface (`extern`)

Directly bind to any existing C library function with zero runtime overhead:

```rust
extern act puts(s: @u8) -> i32
extern act sqrtf(val: f32) -> f32
```

---

## 9. Command-Line Interface

The Velo compiler (`velo.exe` / `velo`) exposes the unified CLI toolchain:

| Command | Description |
| :--- | :--- |
| `velo run <file> [args...]` | Compile and immediately execute the program |
| `velo build <file> [-o <out>]` | Compile to a standalone native executable (`--cc gcc\|cl`, `--debug\|--release`) |
| `velo emit-c <file> [-o <out>]` | Print or export the generated C99 translation unit |
| `velo check <file> [--json]` | Validate only: lex, parse, semantic analysis, monomorphization (no codegen) |
| `velo doc <file> [-o <out.md>]` | Extract Markdown API documentation from `///` doc comments |
| `velo test [path] [--filter <k>]` | Run native test suites with optional test name filter |
| `velo pkg <cmd>` | Package manager (`init`, `add`, `install`, `build`, `run`, `test`, `tree`) |
| `velo lsp` | Launch the Language Server Protocol (LSP 3.17) server over stdio |
| `velo version` / `velo help` | Print version banner or command-line help manual |
