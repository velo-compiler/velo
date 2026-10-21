# Velo Language Specification (Stage 1)

This document formally specifies the lexical grammar, type system, operator precedence, statements, expressions, and memory semantics of the **Velo** programming language for **Stage 1 (Bootstrap)**.

---

## 1. Lexical Structure

### 1.1 Source Encoding
Velo source files are UTF-8 encoded text files with the `.vl` extension.

### 1.2 Comments
* Single-line comments start with `//` and extend to the end of the line.
```rust
// This is a single-line comment in Velo
```
* Block comments are enclosed in `/* ... */` (nested comments supported).

### 1.3 Identifiers
Identifiers name variables, functions, types, and fields.
* Must start with an ASCII letter (`a-z`, `A-Z`) or an underscore `_`.
* May be followed by letters, digits (`0-9`), or underscores.
* Case-sensitive (`foo` and `Foo` are distinct).

### 1.4 Keywords
The following keywords are reserved in Stage 1:
```
act       data      mut       let       if        else
loop      in        return    zone      extern    defer
use       true      false     null      sizeof    as
break     continue  on        and       or        not
kind
```

### 1.5 Punctuation & Semicolons
* Code blocks are delimited by curly braces `{` and `}`.
* **Semicolons are optional**: Newlines act as statement terminators. Semicolons `;` may be used to place multiple statements on the same line.

### 1.6 Operator Precedence & Associativity
Operators are evaluated in the following order (from highest precedence to lowest):

| Precedence | Operator | Description | Associativity |
| :---: | :--- | :--- | :---: |
| **1 (Highest)** | `.` `()` `[]` | Member access, function call, array index | Left-to-right |
| **2** | `@` (prefix) | Address-of operator | Right-to-left |
| **2** | `!` `not` `-` (unary) | Logical NOT, bitwise NOT, arithmetic negation | Right-to-left |
| **2** | `as` | Type casting (`x as f32`) | Left-to-right |
| **3** | `*` `/` `%` | Multiplication, division, modulo | Left-to-right |
| **4** | `+` `-` | Addition, subtraction | Left-to-right |
| **5** | `..` | Range creation (`0..10`) | Non-associative |
| **6** | `<` `<=` `>` `>=` | Relational comparisons | Left-to-right |
| **7** | `==` `!=` | Equality comparisons | Left-to-right |
| **8** | `and` `&&` | Logical AND | Left-to-right |
| **9** | `or` `\|\|` | Logical OR | Left-to-right |
| **10 (Lowest)**| `=` `+=` `-=` `*=` `/=` | Assignment operators | Right-to-left |

> [!NOTE]
> **Precedence Rule for `@` vs `.`**:
> Because `.` (precedence 1) binds tighter than `@` (precedence 2):
> * `@player.pos.x` evaluates as `@((player.pos).x)` — it takes the memory address of the `x` field.
> * To take the address of `player` first, use parentheses: `(@player).pos`.

---

## 2. Type System

### 2.1 Primitive Types
Velo requires explicit bit sizes to guarantee cross-platform predictability:

| Type | Description | Size | C Equivalent |
| :--- | :--- | :--- | :--- |
| `i8`, `i16`, `i32`, `i64` | Signed integers | 1, 2, 4, 8 bytes | `int8_t`, `int16_t`, `int32_t`, `int64_t` |
| `u8`, `u16`, `u32`, `u64` | Unsigned integers | 1, 2, 4, 8 bytes | `uint8_t`, `uint16_t`, `uint32_t`, `uint64_t` |
| `f32`, `f64` | IEEE 754 floating-point | 4, 8 bytes | `float`, `double` |
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

#### C99 Lowering:
* Each unique `act(...) -> Ret` signature generates a C function pointer typedef (e.g. `typedef int32_t (*velo_act_i32_i32_to_i32)(int32_t, int32_t);`).
* Anonymous functions are lifted into static C functions with forward prototypes and definitions.

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

#### Method Chaining & Primitive Extension:
* Functions returning struct values or pointers can be chained fluently:
  ```rust
  let result = pt.translate(1.0, 2.0).scale(2.0)
  ```
* Functions on primitive types can also be invoked as methods:
  ```rust
  act square(n: i32) -> i32 { return n * n }
  let s = 7.square() // 49
  ```

#### Generic Method Specialization:
UFCS seamlessly integrates with generic functions and structs:
```rust
data Box[T] { value: T }
act unwrap[T](b: @Box[T]) -> T { return b.value }

mut b = Box[i32]{ value: 999 }
let val = b.unwrap() // specializes unwrap[i32] and auto-borrows &b
```

### 2.8 Operator Overloading (`act op <symbol>`)
Velo enables custom types (such as game math vectors, matrices, and colors) to overload standard binary and unary operators using the punchy 2-letter `op` prefix. Overloaded operators have zero runtime overhead and compile directly to specialized C99 function calls.

#### Declaration Syntax:
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

// 3. Unary negation (single parameter, optional space)
act op -(v: Vector2) -> Vector2 {
    return Vector2{ x: -v.x, y: -v.y }
}

// 4. Equality and Inequality comparisons
act op ==(a: Vector2, b: Vector2) -> bool {
    return a.x == b.x and a.y == b.y
}
act op !=(a: Vector2, b: Vector2) -> bool {
    return not (a == b)
}
```

#### Natural Mathematical Usage:
```rust
let pos = Vector2{ x: 10.0, y: 20.0 }
let vel = Vector2{ x: 2.0, y: -3.0 }
let dt: f32 = 0.5

// Operator precedence is preserved: vel * dt runs first, then pos + ...
let next_pos = pos + vel * dt
let opposite = -vel
```

#### Automatic Compound Assignment:
Statements like `pos += vel` or `pos *= 2.0` automatically desugar into `pos = pos + vel` and `pos = pos * 2.0`, calling the corresponding overloaded binary operator without requiring separate `+=` methods.

#### Auto-Referencing / Auto-Dereferencing:
Operators declared with pointer parameters (`act op +(a: @Vector2, b: @Vector2)`) automatically receive the address of value lvalues (`&a`, `&b`), and vice-versa, avoiding unnecessary struct copying.

---

### 2.9 Advanced Struct Features (Type Aliases, Field Defaults, `#align`/`#packed`)

#### Type Aliases (`type Name = T`):
A type alias gives a primitive type a domain-specific name. `type` is a contextual keyword recognized only at top level; the target must be a primitive type, optionally preceded by a single pointer marker:

```rust
type EntityId = u64
type HealthPoints = i32
type TexBuf = @u8

let entity: EntityId = 42
let next = entity + 1   // alias resolves to u64 statically
```

Semantics:
- The target must be a primitive (`i8`..`i64`, `u8`..`u64`, `f32`, `f64`, `bool`, `usize`, `isize`, `string`) or `@<primitive>`; aliasing a struct or kind is a compile error.
- No alias-of-alias: the target is validated at parse time.
- Extra pointer levels compose over aliases and are applied before the alias target (`let p: @EntityId` where `type EntityId = u64` has type `@u64`).
- Resolution is order-free: aliases are collected from the whole program (including across `use`d files) before any use site is canonicalized, so an alias may be declared after its uses.
- Both compilers canonicalize every type string (struct fields, kind payloads, parameters, return types, local declarations, casts) before code generation; the emitted C also carries a decorative `typedef <target> <Name>;`.

#### Default Field Initializers:
Struct fields may declare constant default initializers. Struct literal fields that are omitted are filled from their defaults, in declaration order, via C99 designated initializers:

```rust
data Vec4 {
    x: f32 = 0.0
    y: f32 = 0.0
    z: f32 = 0.0
    w: f32 = 1.0
}

let v = Vec4{ x: 2.5 }   // v.y == 0.0, v.z == 0.0, v.w == 1.0
```

Rules:
- Defaults must be constant literals (integer, float, string, bool) or a unary `-` applied to a numeric literal.
- An omitted field **without** a default is a compile error ("missing field ... no default initializer"); a literal must remain complete with respect to non-defaulted fields.
- Field defaults may also reference other declared types (e.g. `id: EntityId = 1`).
- Defaults in generic struct templates are carried into every specialization.
- Defaults apply to `data` struct fields only; `kind` variant payload fields do not support default initializers.

#### Struct Layout Attributes (`#align(N)` / `#packed`):
Data declarations accept layout attributes between the header and the struct body; both compile to GCC/Clang `__attribute__` markers on the struct definition:

```rust
data Vec4 #align(16) { ... }    // struct __attribute__((aligned(16))) Vec4 { ... };
data Blob #packed { ... }       // struct __attribute__((packed)) Blob { ... };
data Item #align(64) #packed { ... }   // __attribute__((aligned(64), packed))
```

- `#align(N)` takes a positive integer literal; the forward `typedef struct T T;` is emitted without attributes (which is valid C and does not affect layout).
- Attributes appear on every specialization of a generic struct declaration.

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

---

## 5. Pointers & Memory Semantics

### 5.1 Address-Of (`@`)
The `@` operator placed before an expression takes its memory address:
```rust
mut x: i32 = 42
ptr: @i32 = @x  // ptr holds the memory address of x
```

### 5.2 Auto-Dereferencing Member Access (`.`)
When accessing fields of a struct through a pointer, the compiler consults the Symbol Table:
* If the base target is a pointer (`@T`), it translates to `target->member` in C.
* If the base target is a struct value (`T`), it translates to `target.member` in C.

Developers always write `.`:
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
A `zone` block defines an ultra-fast hardware arena:
* **Default Size**: 16 MB pre-allocated contiguous buffer managed by `velo_runtime.h`.
* **Mechanism**: 
  1. Entering a `zone` saves the current arena offset (the watermark).
  2. Allocations via `mem.alloc` simply advance the offset ($O(1)$ pointer bump).
  3. Exiting the `zone` restores the saved offset ($O(1)$ instant reset).
* **Guarantees**: Zero GC pauses, zero fragmentations, zero memory leaks.

```rust
zone {
    // Allocated on the 16MB arena
    particles: @Particle = mem.alloc(@Particle, 1000)
    
    // Work with particles...
} // All 1000 particles wiped in 1 CPU instruction here!
```

---

## 6. String Interpolation

Strings containing `{expression}` syntax are desugared at compile time into formatted output:

```rust
name = "Velo"
speed = 100
io.println("Running {name} at {speed}% speed!")
```

### Lowering Rules:
The compiler parses expressions inside `{}` and checks their types in the Symbol Table:
* `i8`..`i64`, `isize` $\to$ `%lld` with `(long long)` cast.
* `u8`..`u64`, `usize` $\to$ `%llu` with `(unsigned long long)` cast.
* `f32`, `f64` $\to$ `%f` / `%.6f`.
* `bool` $\to$ `%s` evaluated as `(expr ? "true" : "false")`.
* `string` $\to$ `%s`.
* `@T` (pointers) $\to$ `%p` with `(void*)` cast.

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
Velo standardizes on a single, expressive `loop` keyword covering all iteration patterns:

#### 1. Infinite Loop (`loop { ... }`)
Runs indefinitely; the implicit `it` counter tracks iterations starting at 0:
```rust
loop {
    if it == 5 { break }
}
```

#### 2. Count / Repeat Loop (`loop <count> { ... }`)
Repeats `<count>` times with `it` taking values `0` through `<count> - 1`:
```rust
loop 5 {
    io.println("Iteration {it}")
}
```

#### 3. Condition Loop (`loop <condition> { ... }`)
Executes while the boolean expression is true (replacing `while`), with `it` counter:
```rust
mut x = 10
loop x > 0 {
    io.println("tick #{it}, x is {x}")
    x -= 1
}
```

#### 4. Named Range Loop (`loop <var> in <start>..<end>[:<step>]`)
Iterates over a range with an explicit variable name and optional `:step` slice:
```rust
loop i in 0..10:2 {
    io.println("Step 2: {i}") // 0, 2, 4, 6, 8
}
```

#### 5. Smart Reverse Auto-Countdown (`loop <start>..<end>`)
When `start > end`, the loop automatically counts down without needing `:-1`:
```rust
loop 5..0 {
    io.println("Liftoff in {it}...") // 5, 4, 3, 2, 1
}
```

#### 6. Inclusive Range (`..=`)
Use `..=` for inclusive ranges:
```rust
loop i in 1..=5 {
    io.println("{i}") // 1, 2, 3, 4, 5
}
```

### 7.3 Pattern Matching (`on`)
The `on` statement performs pattern matching over scalar values, pure enums, and tagged unions. Payload variables are automatically extracted and bound within arm scope:

```rust
on e {
    .Quit => {
        io.println("Quit received")
    }
    .KeyDown(key) => {
        io.println("Key code: {key}")
    }
    .Click(button, x, y) => {
        io.println("Button {button} at ({x}, {y})")
    }
}
```

---

## 8. Foreign Function Interface (`extern`)

Directly bind to any existing C library function with zero runtime overhead:

```rust
extern act puts(s: @u8) -> i32
extern act sqrtf(val: f32) -> f32
```
