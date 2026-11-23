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
<!-- not-compiled -->
```
act       data      mut       let       if        else
loop      in        return    zone      extern    defer
use       true      false     null      sizeof    as
break     continue  on        and       or        not
kind      fail      pact      view
```

Contextual keywords recognized in specific declaration or expression contexts include `aka`, `op`, and `unsafe`. Additionally, certain keywords (such as `act`, `data`, `defer`, `loop`, `return`, `break`, `continue`, `on`, `extern`, `zone`, `use`) are recognized contextually as identifiers in struct field definitions, member accesses, parameters, and variable declarations where syntactic ambiguity does not arise. Non-contextual keywords (`mut`, `let`, `if`, `else`, `true`, `false`, `null`, `sizeof`, `view`, `pact`, `as`) are strictly reserved across all identifier positions.

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

#### Integer Overflow Policy
Velo specifies **two's-complement wraparound arithmetic by default** for all signed integer types (`i8`, `i16`, `i32`, `i64`, `isize`) and unsigned integer types (`u8`, `u16`, `u32`, `u64`, `usize`) across standard arithmetic operators (`+`, `-`, `*`).

* **Predictable Semantics:** Signed integer overflow in Velo is well-defined modular arithmetic and never invokes C undefined behaviour (UB). For example, `2147483647_i32 + 1 == -2147483648_i32`, and `9223372036854775807_i64 + 1 == -9223372036854775808_i64`.
* **Toolchain Enforcement:** When compiling via GCC or Clang, the compiler backend automatically emits the `-fwrapv` flag, ensuring the C backend compiler does not optimize away overflow checks or assume that signed overflow cannot occur. On MSVC, two's-complement wrapping is the guaranteed native representation.
* **Checked and Saturating Arithmetic:** Applications requiring explicit overflow detection or clamp-on-overflow semantics should use the `std.math.int` standard library module:
  * Saturating arithmetic: `add_sat_*`, `sub_sat_*`, `mul_sat_*`.
  * Checked arithmetic: `checked_add_*`, `checked_sub_*`, `checked_mul_*`, `checked_div_*`, `checked_rem_*` (returns `bool` indicating whether the calculation completed without overflow, storing the wrapped value into an out-pointer `@T`).

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
  <!-- not-compiled -->
  ```rust
  let m = min(15, 25) // infers T = i32 -> calls min_i32
  ```
* **Explicit Type Arguments**: Can also be supplied explicitly:
  <!-- not-compiled -->
  ```rust
  let mf = min[f32](3.14, 2.71) // calls min_f32
  ```
* **Zero Overhead**: Generics are monomorphized into specialized C99 functions and types (`Box_i32`, `Option_string`, `min_i32`, `Pair_string_i32`) with zero runtime indirection or virtual method table overhead.

### 2.6 Function Pointers & First-Class Callbacks (`act(...) -> Ret`)
Velo supports first-class function pointer types using the canonical `act(...) -> Ret` syntax, harmonizing directly with the function definition keyword `act`.

#### Function Type Signatures:
<!-- not-compiled -->
```rust
act(i32, i32) -> i32        // Takes two i32, returns i32
act(@Button) -> void         // Takes pointer to Button, returns void
act() -> void                // Takes no arguments, returns void
```

#### Storing & Passing Function Pointers:
Named functions can be referenced as expressions and stored in variables or passed as arguments to higher-order functions:
<!-- not-compiled -->
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
<!-- not-compiled -->
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

#### Inline Anonymous Functions & Fat-Arrow Syntax:
Velo supports first-class anonymous functions (`act`) using both single-expression fat-arrow syntax (`=>`) and multi-statement block syntax:

* **Single-Expression Fat-Arrow Form (`act(params...) => expr`):**
  Omitting the return type infers it automatically from the return expression:
  ```velo
  let doubler = act(x: i32) => x * 2
  let sum = act(a: i32, b: i32) => a + b
  ```

* **Fat-Arrow Form with Explicit Return Type (`act(params...) -> Ret => expr`):**
  ```velo
  let add_ten = act(x: i32) -> i32 => x + 10
  ```

* **Full Block Anonymous Function Form (`act(params...) [-> Ret] { body }`):**
  If `-> Ret` is omitted, the return type defaults to `void`:
  <!-- not-compiled -->
  ```velo
  btn.on_click = act(b: @Button) {
      io.println("Clicked button: {b.id}")
  }

  let calc = act(x: i32, y: i32) -> i32 {
      return x * 2 + y
  }
  ```

* **Named Fat-Arrow Functions (`act name(params...) [-> Ret] => expr`):**
  Named function declarations also support single-expression fat-arrow syntax:
  ```velo
  act square(x: i32) => x * x
  act cube(x: i32) -> i32 => x * x * x
  ```

* **Passing Anonymous Acts to Higher-Order Functions:**
  Anonymous acts can be passed directly as arguments to any function expecting a matching `act(...) -> Ret` function pointer:
  <!-- not-compiled -->
  ```velo
  act apply_int(val: i32, f: act(i32) -> i32) -> i32 {
      return f(val)
  }

  let result = apply_int(7, act(n: i32) => n * 3) // 21
  ```

### 2.7 Method Syntax / Uniform Function Call Syntax (UFCS)
Velo supports pure Uniform Function Call Syntax (UFCS) without requiring `class`, `impl`, or object-oriented keywords. Any top-level function whose first parameter matches the receiver type can be called using method syntax (`receiver.method(args...)`):

<!-- not-compiled -->
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
<!-- not-compiled -->
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

<!-- not-compiled -->
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

<!-- not-compiled -->
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

<!-- not-compiled -->
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

### 2.14 Integer Literals & Unsuffixed Literal Type Ladder

#### 2.14.1 Literal Bases & Syntax
Velo supports integer literals in four numerical bases, with optional digit separators (`_`) for enhanced readability:
* **Decimal**: digits `0-9` (e.g. `42`, `1_000_000`).
* **Hexadecimal**: prefix `0x` or `0X` followed by hex digits `0-9`, `a-f`, `A-F` (e.g. `0xFF`, `0xDead_Beef`).
* **Binary**: prefix `0b` or `0B` followed by binary digits `0` or `1` (e.g. `0b1010`, `0b11111111_00000000`).
* **Octal**: prefix `0o` or `0O` followed by octal digits `0-7` (e.g. `0o755`, `0o17777777777`).

All integer literals are verified at compile time to fit within the 64-bit unsigned magnitude range `[0, 18446744073709551615]`. Values exceeding $2^{64}-1$ trigger a loud compile-time error. Empty literals (`0x`, `0b`, `0o`) and literals containing invalid digits (e.g. `0b102`, `0o78`) are strictly rejected.

#### 2.14.2 Explicit Suffixes (Strict Typing)
Integer literals may carry an explicit type suffix designating their exact static type:
* Signed: `i8`, `i16`, `i32`, `i64`, `isize` (e.g. `100i8`, `-42i64`, `0isize`).
* Unsigned: `u8`, `u16`, `u32`, `u64`, `usize` (e.g. `255u8`, `1000u32`, `0xFFu64`, `64usize`).

When an explicit suffix is supplied, the literal's static type is strictly pinned to that type. No implicit widening, narrowing, or cross-family conversions are permitted:
```rust
let a = 100u64         // Type is strictly u64
let b: u32 = 100u64    // Compile Error: Cannot implicitly convert 'u64' to narrower type 'u32'
```

#### 2.14.3 Unsuffixed Literal Type Ladder
When an integer literal has no explicit type suffix, its inferred static type is determined by the unsuffixed literal type ladder:
1. **Fits `i32`**: Values in `[-2147483648, 2147483647]` are inferred as `i32`.
2. **Else fits `i64`**: Values in `[-9223372036854775808, 9223372036854775807]` are inferred as `i64`.
3. **Else fits `u64`**: Positive values in `[9223372036854775808, 18446744073709551615]` are inferred as `u64`.
4. **Out of Range**: Values outside `[-9223372036854775808, 18446744073709551615]` trigger a compile-time overflow error.

```rust
let a = 42                   // Inferred as i32 (fits i32)
let b = 2147483648           // Inferred as i64 (exceeds INT32_MAX, fits i64)
let c = 0x80000000           // Inferred as i64 (2147483648 fits i64)
let d = 9223372036854775808  // Inferred as u64 (exceeds INT64_MAX, fits u64)
let e = -2147483648          // Inferred as i32 (INT32_MIN fits i32)
let f = -9223372036854775808 // Inferred as i64 (INT64_MIN fits i64)
```

#### 2.14.4 Contextual Literal Adaptation
To maintain clean ergonomics without compromising type safety, unsuffixed integer literals adapt to the target integer type of their enclosing context (variable annotations, struct fields, assignments, returns, and function arguments) if and only if the constant value fits within the target type's representable range:
```rust
let x: u8 = 255              // OK: 255 fits in u8
let y: u8 = 256              // Compile Error: Integer literal '256' out of range for type 'u8'
let z: i64 = -9223372036854775808 // OK: fits in i64
let w: usize = 2305843009213693952 // OK: fits in usize
```

---

### 2.15 Static Contracts & Generic Constraints (`pact`)

Velo supports compile-time static contracts and interface constraints using the unique, punchy 4-character keyword `pact`. A `pact` defines a set of required method signatures that a concrete type must satisfy:

```velo
// 1. Defining a static contract (pact)
pact Printable {
    act print(self: @Self) -> void
}

pact Measurable {
    act area(self: @Self) -> i32
    act perimeter(self: @Self) -> i32
}
```

#### Generic Constraints (`[T: PactName]`):
Generic functions and data structures can constrain their type parameters using `: PactName`:

```velo
// 2. Generic function bounded by Printable
act display[T: Printable](item: @T) {
    item.print()
}

// 3. Multi-parameter generic function with pact bound
act pair_inspect[T: Printable, U](item: @T, tag: U) {
    item.print()
    io.println("Tag: {tag}")
}
```

#### Implementing a Pact:
In accordance with Velo's philosophy of structural elegance and zero boilerplate, types do not need explicit `implements` or `conforms` keywords. Any type that provides matching methods (via free functions using Uniform Function Call Syntax) automatically satisfies the pact:

<!-- not-compiled -->
```velo
data User {
    name: string
}

// Satisfies pact Printable for User
act print(u: @User) {
    io.println(u.name)
}

act main() {
    mut u = User{ name: "Alice" }
    display(@u) // Monomorphized static call, zero runtime overhead
}
```

#### Semantic Rules & Guarantees:
* **Zero Runtime Overhead**: Pacts are verified strictly at compile time during semantic analysis and monomorphization. No dynamic dispatch tables (vtables), pointer indirections, or runtime boxing overhead are introduced.
* **UFCS Receiver Flexibility**: Pact methods can be satisfied by functions accepting either pointer receivers (`@T`) or value receivers (`T`), taking full advantage of Velo's automatic referencing and dereferencing.
* **Deterministic Compiler Diagnostics**: When a concrete type fails to satisfy a pact constraint during generic instantiation, the compiler reports a clear, actionable error:
  <!-- not-compiled -->
  ```
  [Velo Error] semantic:<line>:<col> - Type '<ConcreteType>' does not satisfy pact '<PactName>': missing method '<method>'
  ```

---

### 2.16 Module Privacy & Export Control (`view`)

Velo enforces strict file-level modular encapsulation by default. To make a top-level declaration accessible to other modules that import the defining file via `use`, the declaration must be explicitly prefixed with the 4-character keyword `view` (short for *viewable* / *public view*):

```velo
// math.vl
view act add(a: i32, b: i32) -> i32 {
    return a + b
}

// Unmarked declarations are strictly private to this file
act internal_helper() -> i32 {
    return 42
}

view data Point {
    x: i32
    y: i32
}

view kind Status {
    Ok
    Err
}

view pact Serializable {
    act serialize(self: @Self) -> string
}

view let MAX_LIMIT: i32 = 1000
```

#### Module Privacy Rules:
* **Private by Default:** Any top-level `act`, `data`, `kind`, `pact`, or `let` without the `view` modifier is private to the file in which it is declared.
* **Prohibited on Non-Exportable Constructs:** Applying `view` to `use` or `test` declarations is a compile-time syntax error (`'view' cannot be applied to 'use'` / `'view' cannot be applied to 'test'`).
* **Cross-Module Access Enforcement:** Attempting to call a private function, instantiate/reference a private struct, access a private enum kind, reference a private pact, or read a private global variable from an importing file triggers a compile-time semantic error:
  <!-- not-compiled -->
  ```
  [Velo Error] semantic:<line>:<col> - '<Name>' is private to '<defining_file>' and cannot be accessed from '<importing_file>'
  ```
* **Intra-File Freedom:** Private declarations can be freely referenced anywhere within the file where they are defined.
* **Standard Library:** All public functions, structs, kinds, and constants across `std/` are exported with `view`.

---

### 2.17 Import Aliasing & Selective Imports (`:>`)

Velo uses the distinct, easy `:>` operator for import aliasing and selective symbol imports:

#### 1. Module Aliasing
Modules can be imported under a local namespace alias using `:> <alias>`:
<!-- not-compiled -->
```velo
use "std/math.vl" :> m

act main() {
    let r = m.add(10, 20)
    let pi = m.PI
}
```
* **Enforced Encapsulation:** When a module is imported under an alias, its declarations cannot be accessed bare from that importing file. Attempting bare access produces an informative compiler diagnostic:
  <!-- not-compiled -->
  ```
  [Velo Error] semantic:<line>:<col> - '<Sym>' is not imported into '<importer>' (module '<file>' is imported under alias '<alias>'; use '<alias>.<Sym>')
  ```

#### 2. Selective Imports
Specific declarations can be selectively imported using `:> { ... }`:
<!-- not-compiled -->
```velo
use "std/math.vl" :> { add, sub }

act main() {
    let a = add(10, 5) // OK
    let b = sub(10, 5) // OK
    // mul(10, 5)      // Compile Error: 'mul' is not imported from 'std/math.vl' into 'main.vl'
}
```
* **Strict Whitelist:** Only the explicitly listed symbols are brought into bare scope. Accessing unlisted symbols from the target file triggers:
  <!-- not-compiled -->
  ```
  [Velo Error] semantic:<line>:<col> - '<Sym>' is not imported from '<file>' into '<importer>'
  ```

#### 3. Selective Import with Renaming
Symbols within a selective import list can be renamed using `OrigName :> LocalAlias`:
<!-- not-compiled -->
```velo
use "calc.vl" :> { add :> calc_add, Point :> Coord }

act sum(c: Coord) -> i32 {
    return calc_add(c.x, c.y)
}
```
* **Original Name Hidden:** When a symbol is imported with a rename, only the local name is visible in the importing file. Referencing the original un-aliased name produces an unimported symbol error.

---

### 2.18 Deferred Execution (`defer`)

The `defer` keyword registers a cleanup action to be executed automatically when the enclosing scope exits (via return, break, continue, or natural block completion). Multiple `defer` statements execute in strict **LIFO** (last-in, first-out) order.

#### 1. Single-Expression Defer
For simple cleanup tasks (such as closing a file, releasing a mutex, or freeing memory), `defer` takes a single expression or call without curly braces:
<!-- not-compiled -->
```velo
act read_config(path: string) -> string {
    let file = fs.open(path, "r")
    defer fs.close(file) // runs automatically upon exiting read_config

    return fs.read_all(file)
}
```

#### 2. Multi-Statement Block Defer
When cleanup requires multiple steps or statements, `defer` takes a block enclosed in curly braces:
<!-- not-compiled -->
```velo
act process_data(session_id: i32) {
    let log = fs.open("session.log", "a")
    let arena = mem.create_arena()

    defer {
        fs.flush(log)
        fs.close(log)
        mem.destroy_arena(arena)
    }

    // do work...
}
```

#### 3. Control Flow Invariants
* **Strict LIFO Order:** Later deferred actions run before earlier ones.
* **Prohibited Statements:** Control transfer statements (`return`, `break`, `continue`, `fail`) are strictly prohibited inside `defer` at compile time, preventing undefined control targets and ensuring clean scope unwinding.

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
<!-- not-compiled -->
```rust
mut score = 100       // Inferred as i32
ratio = 0.5           // Inferred as f32
is_active = true      // Inferred as bool
```

---

## 4. Functions (`act`)

Functions represent executable routines declared with the `act` keyword.

### 4.1 Declaration & Signatures
A function declaration specifies parameter names and their static types, followed by an optional return type (`-> ReturnType`, defaulting to `void` if omitted):

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

### 4.2 Function and Method Call Argument Type Checking

Velo enforces strict, sound compile-time type checking for all call expressions across the language. No call path bypasses semantic type checking or relies solely on backend C compilation or silent implicit conversions.

#### 4.2.1 Core Invariants
* **No Implicit Narrowing or Truncation:** Passing a value of incompatible type (such as `f32`/`f64` to `i32`, `string` to `i32`, `bool` to `i32`, `i32` to `bool`, or a struct to a primitive) is strictly rejected at compile time during semantic analysis (`velo check`).
* **Position-Aware Error Reporting:** Argument type mismatch errors pinpoint the 1-based argument position, expected parameter type, and actual argument type:
  <!-- not-compiled -->
  ```
  [Velo Error] semantic:<line>:<col> - Type mismatch in call argument <position>: expected '<expected>', got '<actual>'
  ```
* **Strict Arity Enforcement:** Calls must provide the exact number of arguments required by the target signature. Both too few and too many arguments are rejected at compile time:
  <!-- not-compiled -->
  ```
  [Velo Error] semantic:<line>:<col> - Mismatched argument count in function call
  ```
* **Contextual Integer Literal Adaptation:** Unsuffixed integer literals adapt to target integer parameter types if and only if the constant value fits within the target type's representable range (e.g. `255` adapts to `u8`, but `256` or `-1` is rejected for `u8`). Literal adaptation never crosses type family boundaries: float literals and boolean literals never adapt to integer parameters, and integer literals never adapt to boolean parameters.
* **Explicit Casts (`as <type>`):** When intentional conversions are required, developers must supply explicit casts:
  <!-- not-compiled -->
  ```rust
  act f(a: i32) {}
  act g(a: bool) {}

  f(1.5 as i32)   // OK: explicit truncation
  f(true as i32)  // OK: explicit bool-to-int conversion
  g(1 as bool)    // OK: explicit int-to-bool conversion
  ```

#### 4.2.2 Call Path Coverage Matrix
The compiler enforces argument type and arity checking across all call forms:

1. **Free Functions (`f(args...)`)**: Arguments are validated in declaration order against parameter types via `adapt_and_check_call_args`.
2. **Methods & UFCS Calls (`receiver.method(args...)`)**: The receiver expression is validated against `self` (first parameter) via `check_method_receiver`, and remaining arguments are validated against trailing parameters.
3. **Foreign Functions (`extern act`)**: Signatures declared with `extern act` are validated with the same strictness as native functions. Velo has no variadics; all extern functions require exact argument counts and compatible types.
4. **Generic Functions (`f[T](args...)`)**: Monomorphized generic instantiations validate all arguments against the specialized parameter types.
5. **Function Pointers (`act(...) -> ...`)**: Invocations of first-class function pointer variables (`cb(args...)`), struct field function pointers (`holder.cb(args...)`), and general function-typed expressions parse the target type signature and enforce exact arity and argument types.
6. **Kind Variant Constructors (`Kind.Variant(...)`)**: Variant constructors enforce arity and payload types for zero-payload (`Variant does not take arguments`), single-payload, and multi-field variants.
7. **Struct Literal Initializers (`Struct { field: expr }`)**: Field expressions are validated against declared field types and default initializers.
8. **Builtin Intrinsics**:
   - `sizeof(T)`: Enforces exactly 1 argument at compile time.
   - `assert(cond, [msg])`: Enforces boolean condition expression and optional string message.
   - `simd` (`f32x4`, `i32x4`): Enforces constructor arity (4 elements or 1 for splat) and numeric element types.
   - `reflect` (`field_count`, `field_value`): Enforces struct type parameters and valid constant field indices.
   - Builtin namespaces (`sys.io`, `sys.mem`, `sys.fs`, `sys.str`, `sys.math`, `sys.time`, `sys.os`): Closed-namespace member validation and per-member signature type walls.
   - Dynamic collection methods (`shelf.*`, `ring.*`, `map.*`, `bitset.*`): Element, key, value, and index type compatibility.

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

<!-- not-compiled -->
```rust
zone {
    // Allocated on the active thread-local arena
    particles: @Particle = mem.alloc(@Particle, 1000)
    
    // Work with particles...
} // All allocations wiped in 1 CPU instruction here!
```

### 5.5 The `mem.*` Intrinsic Surface
The `mem` namespace is a **closed set** of fourteen compiler intrinsics. A call
to any other member is a compile-time error, so a typo can never reach C
generation or the runtime:

| Member | Signature | Result |
| :--- | :--- | :--- |
| `mem.alloc` | `(count)` or `(@Type, count)` | `@u8` or `@Type` |
| `mem.heap_alloc` | `(count)` or `(@Type, count)` | `@u8` or `@Type` |
| `mem.free` | `(pointer-or-heap-string)` | `void` |
| `mem.realloc` | `(pointer, @Type, count)` | `@Type` |
| `mem.copy` | `(pointer dest, pointer src, byte count)` | `void` |
| `mem.move` | `(pointer dest, pointer src, byte count)` | `void` |
| `mem.set` | `(pointer dest, byte value, byte count)` | `void` |
| `mem.overlaps` | `(pointer a, pointer b, byte count a, byte count b)` | `bool` |
| `mem.used` | `()` | `usize` |
| `mem.heap_used` | `()` | `usize` |
| `mem.current` | `()` | `@Allocator` |
| `mem.alloc_with` | `(allocator, @Type, count)` | `@Type` |
| `mem.create_arena` | `(capacity)` | `@Allocator` |
| `mem.destroy_arena` | `(arena)` | `void` |

* `mem.alloc` bumps the active `zone` arena; `mem.heap_alloc` takes a persistent
  block from the shared ledger. The one-argument form allocates bytes, the
  two-argument form allocates `count` elements of `@Type`.
* `mem.copy`, `mem.move`, and `mem.set` count **bytes**, not elements, and
  mirror `memcpy`, `memmove`, and `memset`. A statically negative count is
  rejected at compile time; a variable-held negative count fails at runtime.
* `mem.overlaps(a, b, len_a, len_b)` returns true if byte regions $[a, a + len_a)$
  and $[b, b + len_b)$ overlap.
* Overlapping regions are only permitted through `mem.move` (the designated
  overlapping-safe primitive). In Debug builds (`--debug`), `mem.copy` asserts
  non-overlap between destination and source buffers and aborts with a fatal
  diagnostic (`Velo Fatal Error: mem.copy destination and source overlap (use mem.move instead)!`)
  if they overlap; in Release builds, raw C `memcpy` behavior is invoked.
* `mem.free` accepts raw pointers and heap strings (`str.heap_*` returns an
  owning `string`). Freeing `null` is a safe no-op.
* `mem.free` and `mem.realloc` enforce provenance verification by default. Every
  heap allocation prepends a 16-byte header containing payload length and magic tag
  (`VELOHEAP` = `0x56454C4F48454150ULL`). On free or realloc, the runtime verifies:
  1. Pointer alignment and range (must be aligned to 8 bytes and >= 4096).
  2. Pointer source (must not point into an active `zone` bump arena).
  3. Header magic tag: must match `VELOHEAP`. Passing an already-freed pointer
     (tombstoned with `VELOFREE` = `0x56454C4F46524545ULL`) or invalid/stack address
     fails with an explanatory fatal error.
* Passing `--unsafe-heap` to `velo run`, `velo build`, `velo test`, or `velo emit-c`
  bypasses the 16-byte header and provenance checks (`#define VELO_UNSAFE_HEAP 1`)
  for zero-overhead hot paths where raw `free()` / `realloc()` speed is paramount.

```rust
use std.io
use std.mem

act main() {
    let buf: @u8 = mem.heap_alloc(@u8, 16)
    mem.set(buf, 7, 16)
    let grown: @u8 = mem.realloc(buf, @u8, 32)
    let held: usize = mem.heap_used()
    io.println("held={held}")
    mem.free(grown)
}
```

### 5.6 Unknown `mem.*` Members
An unknown member reports the closed set and never reaches code generation:

<!-- not-compiled -->
```
unknown mem member 'malloc' (functions: alloc, heap_alloc, free, realloc, copy,
move, set, overlaps, used, heap_used, current, alloc_with, create_arena, destroy_arena)
```

### 5.7 Out-of-Memory Behaviour
Allocation in Velo is **fail-stop**. The `mem.*` intrinsics return `@T` or `@u8`
— never an optional — so there is no language-level way to observe a failed
allocation. Rather than hand back a `null` that the caller would immediately
dereference, the runtime prints a diagnostic to stderr and terminates with a
non-zero exit status.

| Condition | Diagnostic | Outcome |
| :--- | :--- | :--- |
| Arena or heap allocation fails | `Velo Fatal Error: Zone Arena allocation failed (<n> bytes)` / `Velo Fatal Error: Out of Heap Memory` | process exits |
| `zone` / `mem.create_arena` exceeds a fixed budget | `Velo Fatal Error: Zone Arena Out of Memory (...)` / `Velo Fatal Error: Allocator Out of Memory (...)` | process exits |
| `size * count` would overflow | `Velo Fatal Error: Allocation size overflow (...)` | process exits |
| `zone` capacity is `0` | `Velo Fatal Error: Zone Arena capacity must be > 0` | process exits |
| A watermark stack push cannot grow | `Velo Fatal Error: Zone Arena Watermark Stack OOM` | process exits |
| `mem.copy`/`move`/`set`/`realloc` receive a negative count | `Velo Fatal Error: mem.<op> got a negative byte count` | process exits |
| `mem.copy` regions overlap in Debug mode | `Velo Fatal Error: mem.copy destination and source overlap (use mem.move instead)!` | process exits |
| `mem.free` on zone arena pointer | `Velo Fatal Error: mem.free called with non-heap pointer (pointer is in zone arena)!` | process exits |
| `mem.free` on already-freed pointer (double free) | `Velo Fatal Error: mem.free called on already-freed pointer (double free)!` | process exits |
| `mem.free` on invalid/stack/foreign pointer | `Velo Fatal Error: mem.free called with invalid pointer (not a valid heap allocation)!` | process exits |
| `mem.realloc` on zone arena pointer | `Velo Fatal Error: mem.realloc called with non-heap pointer (pointer is in zone arena)!` | process exits |
| `mem.realloc` on already-freed pointer | `Velo Fatal Error: mem.realloc called on already-freed pointer!` | process exits |
| `mem.realloc` on invalid/stack/foreign pointer | `Velo Fatal Error: mem.realloc called with invalid pointer (not a valid heap allocation)!` | process exits |

The consequences for user code:

* **Budget explicitly when failure matters.** `mem.create_arena(capacity)` gives
  an arena with a fixed budget; exceeding it is a diagnosed failure rather than
  an unbounded request. With the implicit thread-local arena, compare
  `mem.used()` against your own ceiling before a large allocation.
* **No partial results.** The process does not continue with a truncated buffer
  or a half-initialised structure, so there is no "check for null and carry on"
  idiom to learn — and no way to accidentally skip the check.
* **Defensive paths reset, they do not guess.** An invalid watermark index is
  treated as corruption: the arena is reset to empty rather than rewound to a
  plausible guess, so a bookkeeping bug surfaces instead of hiding.

See `SECURITY.md` § Out-of-Memory Policy for the full per-site table and the
rationale.

---

## 6. String Subsystem & Operations

### 6.1 String Interpolation
Strings containing `{expression}` syntax are desugared at compile time into formatted output:

<!-- not-compiled -->
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

### 6.3 The `str.*` Intrinsic Surface
The `str` namespace is a **closed set** of eighteen compiler intrinsics. A call
to any other member is a compile-time error:

| Member | Signature | Result | Storage |
| :--- | :--- | :--- | :--- |
| `str.len` | `(string s)` | `usize` | — |
| `str.contains` | `(string s, string sub)` | `bool` | — |
| `str.starts_with` | `(string s, string prefix)` | `bool` | — |
| `str.ends_with` | `(string s, string suffix)` | `bool` | — |
| `str.index_of` | `(string s, string needle)` | `i64` | — |
| `str.trim` | `(string s)` | `string` | active zone |
| `str.heap_trim` | `(string s)` | `string` | heap |
| `str.to_upper` | `(string s)` | `string` | active zone |
| `str.heap_to_upper` | `(string s)` | `string` | heap |
| `str.to_lower` | `(string s)` | `string` | active zone |
| `str.heap_to_lower` | `(string s)` | `string` | heap |
| `str.replace` | `(string s, string old, string new)` | `string` | active zone |
| `str.heap_replace` | `(string s, string old, string new)` | `string` | heap |
| `str.concat` | `(string a, string b)` | `string` | active zone |
| `str.heap_concat` | `(string a, string b)` | `string` | heap |
| `str.split` | `(string s, string delimiter)` | `shelf[string]` | active zone |
| `str.format` | `(string fmt, ...)` | `string` | active zone |
| `str.heap_format` | `(string fmt, ...)` | `string` | heap |

* The `heap_*` family allocates on the persistent heap and must be released with
  `mem.free`. The un-prefixed family allocates in the active `zone` arena and is
  reclaimed automatically when that zone exits.
* `str.format` uses `printf`-style specifications when the format string has no
  `{...}` interpolation. The checker validates that the number of `%`
  conversions matches the number of additional arguments.
* `str.split` returns a `shelf[string]` of arena-backed tokens; it is not a
  `string` and does not support `str.*` members.

```rust
use std.io
use std.str

act main() {
    let raw = "  Velo  "
    let clean: string = str.trim(raw)
    let upper: string = str.to_upper(clean)
    let loud: string = str.heap_concat(upper, "!")
    let idx: i64 = str.index_of(loud, "ELO")
    let n: usize = str.len(loud)
    io.println("{loud} idx={idx} len={n}")
}
```

### 6.4 Unknown `str.*` Members
An unknown member reports the closed set and never reaches code generation:

<!-- not-compiled -->
```
unknown str member 'substr' (functions: len, contains, starts_with, ends_with,
index_of, trim, heap_trim, to_upper, heap_to_upper, to_lower, heap_to_lower,
replace, heap_replace, concat, heap_concat, split, format, heap_format)
```

Internal runtime helpers such as `velo_str_eq` and `velo_str_nonnull` are **not**
members. Reaching them through `str.*` is an unknown-member error, not a C
codegen failure.

---

## 7. Control Flow

### 7.1 Conditionals (`if` / `else`)
Parentheses around conditions are optional. Braces `{}` are mandatory:
<!-- not-compiled -->
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

#### 4. Count-vs-Condition Disambiguation Rule
When a single expression follows `loop` (i.e. `loop <expr> { ... }`), the compiler resolves count repeat vs. condition iteration strictly by the static type of `<expr>`:

| Expression Type | Loop Kind | Evaluation & Execution Semantics |
|---|---|---|
| **Integer** (`i8`, `i16`, `i32`, `i64`, `u8`, `u16`, `u32`, `u64`, `isize`, `usize`) | **Count Loop** | Evaluated **exactly once** before loop entry. Executes $N$ times (`it` from `0` to $N - 1$). If $N \le 0$, executes 0 times and terminates immediately. |
| **Boolean** (`bool`) | **Condition Loop** | Evaluated **before each iteration** (like `while`). Runs while condition evaluates to `true`. Implicit `it: i32` starts at 0 and increments every iteration. |
| **All Other Types** (`f32`, `f64`, `string`, `@T`, struct, array, etc.) | **Compile Error** | Semantic error: `Loop expression must be an integer (count) or 'bool' (condition), got '<type>'`. |

##### Security Invariants & Disambiguation Guarantees:
1. **Single Evaluation for Counts**: The count expression is evaluated once into an internal temporary. Function calls and side-effects in `loop get_count() { ... }` are never repeated per iteration.
2. **Zero and Negative Counts**: A negative or zero count (`loop 0`, `loop -1`, `let c = -5; loop c`) executes zero times and terminates immediately without wrapping or running infinitely.
3. **No Implicit Truthiness**: Velo rejects C-style truthiness. Neither pointers (`loop ptr`), strings (`loop str`), nor floats (`loop 1.0`) can be used as conditions. Explicit boolean comparisons are required (e.g. `loop ptr != null`, `loop str.len() > 0`).
4. **Syntax Independence**: Classification is determined exclusively by type inference in the semantic checker, never by AST syntax (literals, variables, binary expressions, and function calls of integer type all behave identically as count loops).

#### 5. Named Range Loop (`loop <var> in <start>..<end>[:<step>]`)
Iterates `<var>` across the numeric interval defined by `<start>` and `<end>`, with an optional positive `:step`:
```rust
loop i in 0..10:2 {
    io.println("Step 2: {i}") // 0, 2, 4, 6, 8
}
```

#### 6. Smart Reverse Auto-Countdown (`loop <start>..<end>`)
Velo enforces symmetrical **Smart Reverse Auto-Countdown** across both compile-time literal ranges and runtime dynamic ranges:
```rust
// Compile-time literal countdown:
loop 5..0 {
    io.println("Liftoff in {it}...") // 5, 4, 3, 2, 1
}

// Runtime dynamic countdown:
let n = 5
loop i in n..0 {
    io.println("{i}") // 5, 4, 3, 2, 1
}
```

#### 7. Inclusive Range (`..=`)
The `..=` operator includes the terminal endpoint value:
```rust
loop i in 1..=5 {
    io.println("{i}") // 1, 2, 3, 4, 5
}
loop i in 5..=1 {
    io.println("{i}") // 5, 4, 3, 2, 1
}
```

#### 8. Dynamic Direction Selection & Evaluation Semantics
When either `<start>` or `<end>` is a runtime variable, expression, or function call, direction selection is resolved via **runtime dynamic direction lowering**:

| Endpoint Relation | Range Kind | Direction | Iterations | Lowered Exit Test | Stepping |
|---|---|---|---|---|---|
| `start < end` | Exclusive (`..`) | Ascending | `end - start` | `i < end` | `i += step` |
| `start < end` | Inclusive (`..=`) | Ascending | `end - start + 1` | `end - i < step` (evaluated after the body) | `i += step` |
| `start > end` | Exclusive (`..`) | Descending | `start - end` | `i > end` | `i -= step` |
| `start > end` | Inclusive (`..=`) | Descending | `start - end + 1` | `i - end < step` (evaluated after the body) | `i -= step` |
| `start == end` | Exclusive (`..`) | Ascending | `0` | `i < end` (evaluates `false`) | None (0 runs) |
| `start == end` | Inclusive (`..=`) | Ascending | `1` | `end - i < step` (true on entry) | Exactly 1 run (`start`) |

Inclusive rows terminate by remaining distance rather than by `<=`/`>=`, so the loop never forms a value past the endpoint and cannot overflow at the maximum of its type (Section 7.2, item 9, Rule W2). Item 9 governs when the two descriptions differ: the `Iterations` column is unchanged, only the exit test differs.

##### Guarantees and Invariants:
1. **Single Evaluation of Dynamic Bounds (No Re-evaluation)**:
   - `<start>`, `<end>`, and optional `<step>` are evaluated **exactly once** in strict left-to-right lexical order prior to loop initialization and stored into temporary stack registers (`__start`, `__end`, `__step`).
   - Side effects (e.g. function calls `loop i in pop()..peek()`, increments, mutating methods) execute exactly once.
   - Prevents Time-of-Check to Time-of-Use (TOCTOU) direction changes or mid-loop bound drift.
2. **Predictable Direction Without Explicit Step**:
   - Descending dynamic ranges (`let n = 5; loop i in n..0`) **do not require an explicit negative step**. Velo automatically selects countdown (`i -= step`) when `start > end`.
   - If an explicit step is provided (`loop i in n..0:step`), the step magnitude must be positive ($> 0$). In descending direction, the step is subtracted (`i -= step`); in ascending direction, the step is added (`i += step`).
3. **Deterministic Equal Endpoints**:
   - Exclusive `n..n` always produces 0 iterations regardless of initial direction assumption.
   - Inclusive `n..=n` always produces exactly 1 iteration with value `n`.
4. **Compile-Time Optimization for Literal Bounds**:
   - When both endpoints are compile-time integer constants, the direction is resolved statically during compilation via `is_reverse_loop_range` with zero runtime branching or temporary hoisting overhead.
5. **Strict Positive Step Invariant & Termination Guarantees**:
   - The range loop step must be strictly positive ($> 0$). Zero steps (`:0`) and negative steps (`:-1`) are illegal and strictly prevented from creating infinite loops.
   - **Compile-Time Rejection**: Any step expression that can be evaluated at compile time (integer literals, constant unary/binary arithmetic like `1 - 1`, `5 - 5`, `2 * 0`, bitshifts, or casts) with value $\le 0$ produces a fatal compile-time semantic error (`Range step must be positive, got <val>`).
   - **Dynamic Fail-Fast Panic**: For dynamic step expressions (variables, parameter expressions, function calls), the compiler emits a fail-fast runtime guard prior to loop entry. If the evaluated step is $\le 0$ (signed) or $== 0$ (unsigned), the program immediately halts with an explicit runtime panic (`velo_panic_range_step`) reporting line and column:
     `[Velo Panic] Range step must be positive (> 0) at line <line>, col <col>`
    - **Codegen Defense-in-Depth**: Code generation never emits `i += 0` or `i -= 0` under any code path. Backend invariants guarantee every range loop iteration strictly advances toward termination.

#### 9. Induction Width & Overflow-Free Termination
Every loop that exposes an induction value — range loops (`loop i in a..b`), count loops (`loop n`), and condition loops (`loop cond`) — has its induction variable typed by a single rule, and every loop terminates without ever incrementing past its type's maximum.

**Rule W1 — width is derived from the bounds, with an `i32` floor.**

| Loop kind | Induction type |
|---|---|
| Range (`loop i in a..b`) | Widest integer type among `a` and `b` under the widening order `u64` > `i64` > `usize`/`isize` > `u32` > `i32`; never narrower than `i32`. |
| Count (`loop n`) | The static type of `n` (`loop c` where `c: u64` gives `u64`); never narrower than `i32`. |
| Condition (`loop cond`) | `i32` (`it` only). |

Mixed signed/unsigned bounds remain a compile error (Section 7.2, item 5); `W1` therefore never has to reconcile signedness, only width.

Consequences that are part of the contract:
1. **No truncation.** A bound wider than `int32` must not be narrowed to make the loop compile. `let lim: isize = 3000000000; loop i in 0..lim` iterates the full range, because `isize` is `i64`-wide on every supported target.
2. **No gratuitous widening.** A loop over `i32` bounds keeps an `int32_t` induction. Widening every loop to `i64` would change the emitted C for the whole standard library, cost cache and register pressure, and — see `W2` — would not fix the boundary defect anyway.
3. **The `i32` floor is intentional.** `loop i in a..b` with `i8`/`i16`/`u8`/`u16` endpoints still iterates in `i32`, so the induction cannot overflow when a narrow bound sits at its own maximum.

**Rule W2 — inclusive ranges terminate by distance, not by overflow.**

`for (T i = start; i <= end; i++)` is unsound when `end` is the maximum of `T`: the increment after the last iteration overflows. For signed `T` this is undefined behaviour (gcc `-O2` reports `iteration N invokes undefined behavior` under `-Waggressive-loop-optimizations` and may delete the loop exit); for unsigned `T` it wraps to 0 and the loop runs again from the bottom.

This is **not a width problem**. It reproduces at `INT32_MAX`, at `UINT32_MAX`, and at `UINT64_MAX`. A width change cannot fix it, which is why `W1` is about not truncating rather than about going wider.

Therefore an inclusive range loop (`..=`) is lowered as an unbounded `for` whose exit test is emitted **after** the body, comparing the remaining distance against the step:

<!-- not-compiled -->
```c
/* ascending,  step 1  */   if (end - i < 1) break;   i++;
/* descending, step 1  */   if (i - end < 1) break;   i--;
/* dynamic direction   */   if (rev ? (i - end < step) : (end - i < step)) break;
```

- When fewer than `step` values remain the loop breaks **without** incrementing, so no value outside the range is ever formed. This holds at every width, including the maximum of the type.
- Both differences are non-negative by construction — the induction never passes the endpoint, because it stops before doing so — so the subtraction cannot overflow either.
- The test is **step-aware, not equality-based**. `loop i in 0..=10:3` visits `0, 3, 6, 9`; an `i == end` test would never fire and would hang. With `step == 1` the comparison degenerates to `i == end`, so the ordinary countdown case is covered by the same rule.
- `continue` still advances: the loop's `__loop_cont_N` label is emitted **before** the terminator and the increment, so `goto __loop_cont_N` performs both. A `continue` that skipped the increment would hang, so the label placement is part of the invariant, not an implementation detail.
- Direction is resolved before the loop (`start > end`); both directions converge on `end`. Literal ranges pick the arm at compile time; dynamic ranges branch on the emitted `__rev_<v>` temporary, so a runtime `start > end` is handled without a separate code path.
- Exclusive ranges (`..`) keep the `<` / `>` test. They terminate at `end - 1` (or `end + 1` descending) and the final increment reaches `end` exactly, which is representable for every `end` that is itself a valid bound.

**Breaking-change surface.** `W1` and `W2` change observable behaviour only where the previous behaviour was wrong:

| Program | Before | After |
|---|---|---|
| `loop i in 0..lim` with `lim: isize = 3000000000` | silently truncated to `int32_t`; wrong iteration count | full `isize` range |
| `loop i in 2147483645..=2147483647` | undefined behaviour; loop may not terminate | 3 iterations, always |
| `loop i in MAX-2..=MAX` for any width `T` | wraps / UB at `MAX` | 3 iterations, always |
| `loop i in 0..10` with `i32` bounds | `int32_t i` | `int32_t i` — unchanged |
| `loop 5` | `int32_t it` | `int32_t it` — unchanged |

Code that relied on wrapping at the inclusive bound was relying on undefined behaviour, so there is no behaviour to preserve. Migration guidance is therefore limited to: do not depend on the old truncation, and use an explicit cast when a narrower induction is genuinely wanted.

##### 9.1 Migration from pre-Phase-68 loop semantics

Two loop behaviours changed. Neither requires an edit for a correct program. Both require an edit for a program that was written against the old wrong result, because that result no longer exists.

**W1 — the induction is now as wide as its bounds.** Previously a range loop whose bound was wider than `int32` could still emit an `int32_t` induction, and the loop then visited wrapped values:

<!-- not-compiled -->
```rust
let lim: isize = 3000000000
loop i in 0..lim { ... }   // before: int32_t induction, visits -1294967296
```

The loop above now iterates the full `isize` range; that is the whole change. Anything that depended on the truncated values must be rewritten to depend on the real ones.

If an `i32` induction is genuinely wanted — for a buffer index, say — say so at the bound, because the bound's type is what selects the width:

```velo
act main() {
    let lim: i64 = 3
    loop i in 0..(lim as i32) {
        io.println("cast bound: {i}")
    }
}
```

Without the cast the same program iterates in the wider type, which is the default:

```velo
act main() {
    let lim: i64 = 3
    loop i in 0..lim {
        io.println("wide bound: {i}")
    }
}
```

A cast that *truncates the value* is not a migration — `let lim: isize = 3000000000; loop i in 0..(lim as i32)` is a range to a negative endpoint, so it descends from 0 through `-1`, `-2`, … That reproduces the old defect on purpose; it is legal, and it is not a supported pattern.

Widening the induction also widens the range of values the body sees, so an accumulator sized for the old iteration count may now overflow. Widen the accumulator rather than casting the induction back down.

**W2 — inclusive ranges terminate without overflow.** Nothing to migrate. A loop such as `loop i in 2147483645..=2147483647` always ran three times; before, the fourth increment was undefined behaviour (signed) or a wrap to zero (unsigned), and whether the loop stopped at all depended on the optimiser. There is no correct program whose behaviour changes here:

```velo
act main() {
    loop i in 2147483645..=2147483647 {
        io.println("at max: {i}")
    }
}
```

`continue` inside an inclusive range is unchanged: it still runs the loop's advance and its exit test. Exclusive ranges are unchanged in both shape and result.

**Unchanged:** count loops (`loop n`) and condition loops (`loop cond`) keep their induction type and their semantics; `loop 5` is still five `int32_t` iterations of `it`. Only the range form is affected, and only in width and terminal condition.

### 7.3 Pattern Matching (`on`)
The `on` statement performs pattern matching over scalar values, tagged unions, and strings:

#### 1. Tagged Union Matching:
<!-- not-compiled -->
```rust
on event {
    .Quit => { io.println("Quit") }
    .KeyDown(key) => { io.println("Key: {key}") }
    .Click(button, x, y) => { io.println("Click at {x}, {y}") }
}
```

#### 2. String Pattern Matching:
<!-- not-compiled -->
```rust
on method {
    "GET" => { handle_get() }
    "POST" => { handle_post() }
    "DELETE" => { handle_delete() }
    _ => { handle_unknown() }
}
```

#### 3. Control Flow & Loop Binding Invariants (`break` and `continue` inside `on`)
Velo strictly defines the interaction between pattern matching branches and surrounding loop control flow:

1. **`on` is Not a Loop**:
   - The `on` statement is a multi-way branch, not an iteration construct.
   - It introduces no loop scope and cannot serve as the target of `break` or `continue`.
2. **Nearest Enclosing Loop Binding**:
   - A `break` statement anywhere inside an `on` arm binds to and terminates the **nearest lexically enclosing `loop`**, never the `on` block.
   - A `continue` statement anywhere inside an `on` arm advances the **nearest lexically enclosing `loop`** to its next iteration, skipping subsequent statements in the loop body.
3. **No Switch-Capture Guarantee**:
   - When scalar or tagged-union `on` statements lower to C99 `switch` statements in the backend, `break` and `continue` are never emitted as unadorned C `break;` statements that could be trapped by the `switch`. The backend emits explicit loop-level jumps (e.g. labeled `goto` or dedicated loop exit flags).
4. **Transparent Nested `on` Invariant**:
   - Arbitrarily deep nesting of `on` statements (`on a { ... on b { ... break } }`) preserves lexical binding to the innermost enclosing `loop`. Inner `on` boundaries are completely transparent to control-flow unwinding.
5. **Exact-Once Cleanup on Break & Continue**:
   - Exiting or advancing a loop via `break` or `continue` inside an `on` arm executes all active loop-scoped `defer` and zone cleanups in strict LIFO order **exactly once**.
   - Cleanups are executed prior to transferring control, preventing duplicate cleanup execution at loop iteration boundaries.
6. **Rejection Outside Loops**:
   - A `break` or `continue` statement that is not contained within a `loop` is rejected at compile time with `break statement not within a loop` / `continue statement not within a loop`.
   - This rule holds in **every** context, not only inside `on`: directly in a function body, in `if`/`else`, in `on` arms, in plain blocks, in `zone` blocks, in `unsafe` blocks, and in a statement following a loop.
   - The rejection is owned by **semantic analysis**, so `velo check` reports it (lane `semantic`, positioned at the offending statement) without running code generation. Code generation additionally asserts the invariant and reports an `internal compiler error` if an unbound `break`/`continue` ever reaches emission, which can only indicate a compiler defect.
   - The loop depth counter resets at every function boundary, so a loop in one function never authorizes a `break` or `continue` in another.

<!-- not-compiled -->
```rust
// 1. Break inside 'on' terminates enclosing loop
loop i in 0..10 {
    on i {
        3 => { break }     // Exits 'loop i in 0..10' immediately at i == 3
        else => { }
    }
}

// 2. Continue inside 'on' skips loop body tail
loop i in 0..5 {
    on i {
        2 => { continue }  // Advances loop to i == 3
        else => { }
    }
    process_item(i)        // Skipped when i == 2
}

// 3. Nested 'on' transparently targets outer loop
loop i in 0..10 {
    on i {
        2 => {
            on status {
                .Halt => { break } // Binds directly to 'loop i in 0..10'
                .Run  => { }
            }
        }
        else => { }
    }
}

// 4. Illegal: break inside 'on' without enclosing loop
act inspect_value(val: i32) {
    on val {
        1 => { break }     // Compile Error: break statement not within a loop
        else => { }
    }
}

// 5. Illegal outside of `on` too: the rule is about loops, not branches
act scan() {
    if true {
        break              // Compile Error: break statement not within a loop
    }
    {
        continue           // Compile Error: continue statement not within a loop
    }
    zone {
        break              // Compile Error: break statement not within a loop
    }
    unsafe {
        continue           // Compile Error: continue statement not within a loop
    }
    loop i in 0..3 {
        break              // OK: the nearest enclosing loop is this one
    }
    break                  // Compile Error: the loop above has already closed
}

// 6. Illegal across functions: depth resets at every function boundary
act count_down() {
    loop i in 0..3 { break }   // OK
}

act scan_again() {
    continue                   // Compile Error: no loop in *this* function
}
```

### 7.4 First-Class Conditional Expressions (`if-else`)
`if-else` blocks can be used directly as expressions producing values:

<!-- not-compiled -->
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
| `velo run <file> [args...]` | Compile and immediately execute the program (`--debug\|--release`, `--unsafe-heap`) |
| `velo build <file> [-o <out>]` | Compile to a standalone native executable (`--cc gcc\|cl`, `--debug\|--release`, `--unsafe-heap`) |
| `velo emit-c <file> [-o <out>]` | Print or export the generated C99 translation unit (`--unsafe-heap`) |
| `velo check <file> [--json]` | Validate only: lex, parse, semantic analysis, monomorphization (no codegen) |
| `velo doc <file> [-o <out.md>]` | Extract Markdown API documentation from `///` doc comments |
| `velo test [path] [--filter <k>]` | Run native test suites with optional test name filter |
| `velo pkg <cmd>` | Package manager (`init`, `add`, `install`, `build`, `run`, `test`, `tree`) |
| `velo lsp` | Launch the Language Server Protocol (LSP 3.17) server over stdio |
| `velo version` / `velo help` | Print version banner or command-line help manual |

---

## 10. Standard I/O Subsystem (`io` & `std.io`)

Velo provides a deterministic, buffered standard I/O subsystem combining compiler intrinsics with pure-Velo standard library acts.

### 10.1 The Intrinsic Boundary (`io.print` and `io.println`)

`io.print` and `io.println` are **compiler intrinsics** recognized directly by semantic analysis and code generation. They lower directly to formatted libc `printf` operations:

* **Arity Enforcement:** Intrinsics accept at most one argument (`0` or `1`). Calls with extra arguments (e.g. `io.println("a", "b")`) are rejected at compile time (`velo check`).
* **Zero-Argument Forms:**
  - `io.println()` emits a newline character to standard output (`printf("\n")`).
  - `io.print()` is a compile-time no-op (`((void)0)`).
* **Single-Argument Formatting & String Interpolation:**
  - String literals support compile-time `{expr}` interpolation (e.g. `io.println("Count: {count}")`).
  - Primitive types format directly without manual conversions: integers (`i8`..`i64`, `u8`..`u64`), floating-point numbers (`f32`, `f64`), booleans (`true`/`false`), and pointers.
* **Format Injection Hardening:** User data and format directives (such as `%s`, `%n`, or unresolved interpolation tokens) are treated strictly as data arguments, never as format strings.
* **Deterministic Stream Ordering:** Calls to intrinsic `io.print` and `io.println` automatically flush standard library buffered streams (`io_flush_stdout()`) before the call and flush standard output (`fflush(stdout)`) after the call, ensuring deterministic interleaving with stdlib writes.

```velo
use std.io

act main() {
    let name = "Velo"
    let version = 1

    // Intrinsic formatting with string interpolation
    io.println("Language: {name}, Major: {version}")

    // Intrinsic formatting of primitive types
    io.println(42)
    io.println(true)

    // Intrinsic newline
    io.println()
}
```

### 10.2 Closed-Set `io.*` Dispatch

The `io.*` namespace is strictly closed. Calling any member not recognized as a compiler intrinsic or declared in `std/io/print.vl` is rejected at compile time during semantic analysis (`velo check`):

```velo
use std.io

act main() {
    // Compile error: unknown io member 'does_not_exist' (functions: io_ensure_atexit, ...)
    // io.does_not_exist()
}
```

An unknown member never falls through to a runtime no-op or an unresolved C symbol.

### 10.3 Standard Library Acts (`std.io`)

Every non-intrinsic member accessed under the `io.` prefix (such as `io.println_str`) routes directly to its corresponding pure-Velo act declared in `std/io/print.vl`.

All standard library acts operate through buffered I/O (`BufferedWriter`) with zero C runtime dependencies. Unqualified calls (e.g. `println_str`) and qualified calls (e.g. `io.println_str`) are guaranteed to produce **identical, byte-for-byte output**.

#### 1. Standard Output Acts
* `print_str(s: string)` / `io.print_str(s)`
* `println_str(s: string)` / `io.println_str(s)`
* `println_empty()` / `io.println_empty()`
* `print_byte(b: u8)` / `io.print_byte(b)`
* `println_byte(b: u8)` / `io.println_byte(b)`
* `print_i64(val: i64)` / `io.print_i64(val)`
* `println_i64(val: i64)` / `io.println_i64(val)`
* `print_u64(val: u64)` / `io.print_u64(val)`
* `println_u64(val: u64)` / `io.println_u64(val)`
* `print_f64(val: f64, precision: i32)` / `io.print_f64(val, precision)`
* `println_f64(val: f64, precision: i32)` / `io.println_f64(val, precision)`
* `print_bool(val: bool)` / `io.print_bool(val)`
* `println_bool(val: bool)` / `io.println_bool(val)`

#### 2. Standard Error Acts
* `eprint(s: StrSlice)` / `io.eprint(s)`
* `eprintln(s: StrSlice)` / `io.eprintln(s)`
* `eprint_str(s: string)` / `io.eprint_str(s)`
* `eprintln_str(s: string)` / `io.eprintln_str(s)`
* `eprintln_empty()` / `io.eprintln_empty()`
* `eprint_byte(b: u8)` / `io.eprint_byte(b)`
* `eprintln_byte(b: u8)` / `io.eprintln_byte(b)`
* `eprint_i64(val: i64)` / `io.eprint_i64(val)`
* `eprintln_i64(val: i64)` / `io.eprintln_i64(val)`
* `eprint_u64(val: u64)` / `io.eprint_u64(val)`
* `eprintln_u64(val: u64)` / `io.eprintln_u64(val)`
* `eprint_f64(val: f64, precision: i32)` / `io.eprint_f64(val, precision)`
* `eprintln_f64(val: f64, precision: i32)` / `io.eprintln_f64(val, precision)`
* `eprint_bool(val: bool)` / `io.eprint_bool(val)`
* `eprintln_bool(val: bool)` / `io.eprintln_bool(val)`

#### 3. Generic Stream Acts (`f*`)
Operating on any `@BufferedWriter` handle (including file streams, pipes, and standard streams):
* `fprint(w: @BufferedWriter, s: StrSlice)` / `io.fprint(w, s)`
* `fprintln(w: @BufferedWriter, s: StrSlice)` / `io.fprintln(w, s)`
* `fprint_str(w: @BufferedWriter, s: string)` / `io.fprint_str(w, s)`
* `fprintln_str(w: @BufferedWriter, s: string)` / `io.fprintln_str(w, s)`
* `fprintln_empty(w: @BufferedWriter)` / `io.fprintln_empty(w)`
* `fprint_byte(w: @BufferedWriter, b: u8)` / `io.fprint_byte(w, b)`
* `fprintln_byte(w: @BufferedWriter, b: u8)` / `io.fprintln_byte(w, b)`
* `fprint_i64(w: @BufferedWriter, val: i64)` / `io.fprint_i64(w, val)`
* `fprintln_i64(w: @BufferedWriter, val: i64)` / `io.fprintln_i64(w, val)`
* `fprint_u64(w: @BufferedWriter, val: u64)` / `io.fprint_u64(w, val)`
* `fprintln_u64(w: @BufferedWriter, val: u64)` / `io.fprintln_u64(w, val)`
* `fprint_f64(w: @BufferedWriter, val: f64, precision: i32)` / `io.fprint_f64(w, val, precision)`
* `fprintln_f64(w: @BufferedWriter, val: f64, precision: i32)` / `io.fprintln_f64(w, val, precision)`
* `fprint_bool(w: @BufferedWriter, val: bool)` / `io.fprint_bool(w, val)`
* `fprintln_bool(w: @BufferedWriter, val: bool)` / `io.fprintln_bool(w, val)`

#### 4. Stream & Lifecycle Management
* `io_ensure_atexit()`: Registers the exit flush hook with libc `atexit`.
* `io_get_stdout_writer() -> @BufferedWriter`: Lazily acquires the stdout stream writer singleton.
* `io_get_stderr_writer() -> @BufferedWriter`: Lazily acquires the stderr stream writer singleton.
* `io_get_fmt_buf() -> @u8`: Lazily acquires the 64-byte numeric formatting buffer.
* `io_flush_stdout() -> bool`: Flushes unwritten stdout buffer bytes to the OS handle.
* `io_flush_stderr() -> bool`: Flushes unwritten stderr buffer bytes to the OS handle.
* `io_flush_all() -> bool`: Flushes both stdout and stderr stream buffers.
* `io_print_cleanup()`: Explicitly frees stream writer buffers and numeric format memory.

### 10.4 Standard Library I/O Example

```velo
use std.io

act main() {
    // 1. Stdlib stdout and stderr printing
    println_str("Standard output message")
    eprintln_str("Standard error message")

    // 2. High-precision numeric formatting
    println_i64(-9223372036854775807 - 1)
    println_u64(18446744073709551615u64)
    println_f64(3.14159265, 4)

    // 3. Explicit stream handles and flushes
    let out = io_get_stdout_writer()
    fprint_str(out, "Stream write to stdout\n")
    io_flush_all()
}
```

### 10.5 Integer Formatting & Signed/Unsigned Guarantees

Velo enforces strict signed/unsigned type separation and portable width promotion across all formatting facilities (`io.println`, `io.print`, string interpolation `{...}`, and standard library printers):

* **Unsigned Formatting Guarantee:**
  Unsigned integer types (`u8`, `u16`, `u32`, `u64`, `usize`) are strictly formatted as non-negative unsigned decimal values. They are never cast to signed types and never produce negative wrapped outputs. In code generation, unsigned types format through standard C99 `%llu` with `(unsigned long long)(...)`.
* **Signed Formatting Guarantee:**
  Signed integer types (`i8`, `i16`, `i32`, `i64`, `isize`) preserve sign across their entire domain, including minimum limits (`INT32_MIN` and `INT64_MIN`). In code generation, signed types format through standard C99 `%lld` with `(long long)(...)`.
* **Platform Word-Size Portability (`usize` and `isize`):**
  `usize` and `isize` format portably across both 32-bit and 64-bit target architectures without truncation or undefined behavior:
  - `usize` zero-extends safely to at least 64 bits (`(unsigned long long)`).
  - `isize` sign-extends safely to at least 64 bits (`(long long)`).
* **String Interpolation Alignment:**
  Within `{...}` interpolation expressions, format specifiers and argument values maintain exact 1:1 order alignment. Unsigned expressions emit `%llu`; signed expressions emit `%lld`.
* **Format Injection Hardening & Locale Independence:**
  All format strings emitted by the compiler are owned static constants. User-controlled strings and format specifiers (e.g. `%n`, `%s`, `{%n}`) flow strictly through data arguments and are rendered literally. Decimal points and numeric digit representations are deterministic and locale-independent.

```velo
use std.io

act main() {
    // Unsigned formatting: boundary values never wrap negative
    let u_max: u64 = 18446744073709551615u64
    let usize_max: usize = 18446744073709551615usize
    io.println(u_max)
    io.println(usize_max)

    // Signed formatting: negative boundaries preserve sign
    let i_min: i64 = -9223372036854775807 - 1
    let isize_val: isize = -42isize
    io.println(i_min)
    io.println(isize_val)

    // String interpolation with mixed types
    io.println("u64={u_max}, i64={i_min}, usize={usize_max}, isize={isize_val}")
}
```

---

## 11. Deliberate Limitations & Workarounds

To maintain a predictable, zero-overhead systems runtime, fast compilation speeds, and a sound static type system, Velo intentionally omits several features common in high-level garbage-collected languages or complex multi-pass compilers. This section documents these deliberate absences, their architectural rationale, their associated costs, and the official, idiomatic workarounds (Security Invariant I77.1).

### 11.1 Closures and Environment Capture

* **Absence:** Velo functions (`act`) and function pointers do not support anonymous lexical closures that implicitly capture variables from enclosing scopes.
* **Architectural Rationale:** Silent heap allocation of closure environments or hidden reference counting directly undermines Velo's explicit region/zone-based memory model. Stack-capturing closures introduce risks of use-after-free and dangling pointers if escaped across lifetimes without complex borrow analysis.
* **The Cost:** Higher-order functions, event listeners, and asynchronous callbacks cannot capture local state implicitly.
* **Official Workaround:** Bare function pointers with an explicit context pointer (`user_data: @void` or a typed context struct pointer `@Context`).

```velo
data TimerContext {
    ticks: i32
    label: string
}

act on_timer_tick(ctx: @TimerContext) {
    ctx.ticks += 1
    io.println("[{ctx.label}] tick {ctx.ticks}")
}

act register_timer(ctx: @TimerContext, callback: act(@TimerContext) -> void) {
    callback(ctx)
}
```

> [!NOTE]
> Task 77.2 introduced first-class fat-arrow anonymous functions (`act(params...) => expr`) and block-form anonymous functions (`act(params...) [-> Ret] { body }`). Furthermore, standard library asynchronous APIs (`std.async.tcp` and `std.http.async_server`) were refactored to eliminate the legacy untyped `user_data: @void` callback baggage, utilizing clean function pointer signatures while preserving explicit context struct pointers (`@Context`) where stateful environments are required (Security Invariant I77.2).

### 11.2 Dynamic Interfaces, Traits, and Vtables

* **Absence:** Velo does not provide runtime dynamic dispatch, interface pointers, or trait objects with hidden virtual method tables (vtables).
* **Architectural Rationale:** Vtable pointer indirection incurs runtime penalties (cache misses, indirect branch mispredictions) and complicates binary ABI layout. All generic code in Velo is monomorphized at compile time for maximum performance and zero runtime indirection.
* **The Cost:** Heterogeneous collections of different types sharing an interface cannot be stored in a single flat array without a tagged union or manual vtable struct.
* **Official Workaround:**
  1. **Compile-Time Polymorphism:** Use monomorphized generics (`T`) for compile-time polymorphism.
  2. **Runtime Polymorphism:** Use tagged unions (`enum` or `data` with `kind` discriminant + `match`) or explicit struct-based function pointer tables (first-class vtables).

<!-- not-compiled -->
```velo
// 1. Compile-time generic polymorphism with pact constraints (monomorphized, zero overhead)
pact Formatter {
    act format(self: @Self) -> string
}

act log_item[T: Formatter](item: @T) {
    io.println(item.format())
}

// 2. Explicit runtime polymorphism via manual dispatch table
data WriterVTable {
    write: act(ctx: @void, bytes: @u8, len: usize) -> usize
    flush: act(ctx: @void) -> bool
}

data AnyWriter {
    ctx: @void
    vtable: @WriterVTable
}
```

> [!NOTE]
> Static compile-time contracts (`pact Name { ... }`) checked during generic monomorphization with zero runtime vtable overhead are fully supported via the `pact` keyword (see §2.15). For dynamic runtime polymorphism, manual function-pointer tables remain the explicit, zero-hidden-overhead pattern.

### 11.3 Module Privacy and Export Control

* **Status:** Implemented in Task 77.4.
* **Mechanism:** Declarations are private by default to their defining file. Public exports are marked with the 4-character keyword `view` (`view act`, `view data`, `view kind`, `view pact`, `view let`).
* **Semantic Enforcement:** Any cross-file access to an unmarked declaration produces a compile-time diagnostic: `'<Name>' is private to '<file>' and cannot be accessed from '<current_file>'`. See §2.16 for complete syntax and specification.

### 11.4 Preprocessor Directives and Conditional Compilation

* **Absence:** Velo contains no `#if`, `#ifdef`, `#define`, or preprocessor macro subsystem.
* **Architectural Rationale:** Preprocessor macros create non-deterministic ASTs, obscure source code semantics, degrade syntax highlighting and IDE/LSP navigation, and prevent single-pass compilation. Velo source code is always syntactically and semantically unambiguous.
* **The Cost:** Code paths for different platforms or configurations cannot be interleaved line-by-line within the same function or file.
* **Official Workaround:**
  1. **Platform-Suffixed Files:** Use the build driver's platform resolution suffix: `_windows.vl`, `_linux.vl`, `_macos.vl`, and `_posix.vl`. The driver selects the matching file at compile time without preprocessing.
  2. **Runtime Platform Checks:** Use standard library platform helpers: `os_is_windows()`, `os_platform_name()`. The compiler optimizes constant-folded branches during code generation.

<!-- not-compiled -->
```velo
// Clean cross-platform abstraction via runtime query
if os_is_windows() {
    // Windows branch
} else {
    // POSIX branch
}
```

### 11.5 Import Aliasing and Selective Imports

* **Status:** Resolved in Task 77.5 via the `:>` operator (see §2.17).
* **Syntax Delivered:**
  - Module aliasing: `use "path/to/mod.vl" :> alias` (accessible via `alias.func()` and `alias.global_var`)
  - Selective import: `use "path/to/mod.vl" :> { Sym1, Sym2 }`
  - Selective import with rename: `use "path/to/mod.vl" :> { Sym1 :> NewName, Sym2 }`
* **Scoping Guarantee:** The compiler enforces strict lexical and semantic encapsulation: aliased modules block bare access, selective imports reject unlisted symbols, and renamed symbols hide the original symbol name in the importer's scope.

### 11.6 Expression Defer

* **Status:** Resolved in Task 77.6 (see §2.18). Both single-expression defer (`defer fs.close(file)`) and multi-statement block defer (`defer { ... }`) are fully supported, executing in strict LIFO order upon scope exit. Control transfer statements (`return`, `break`, `continue`, `fail`) remain strictly prohibited inside defer.

---

## 12. Standard Pattern Matching Subsystem (`std.patt` / `std.text.regex`)

Velo provides a linear-time, backtracking-free regular expression and pattern matching engine based on Thompson NFA state graph simulation (`std.patt`, with compatibility bridge `std.text.regex`).

### 12.1 Security & Algorithmic Guarantees

* **Zero Backtracking / ReDoS-Free:** Executes in strict $O(N \cdot M)$ linear time (where $N$ is pattern state count and $M$ is input byte length). Vulnerabilities stemming from catastrophic backtracking (e.g. `(a+)+b`) are mathematically impossible.
* **POSIX ERE Subset:** Supports character literals, escapes (`\d`, `\D`, `\w`, `\W`, `\s`, `\S`, `\t`, `\n`, `\r`), character classes (`[a-z]`, `[^0-9]`), anchors (`^`, `$`), quantifiers (`*`, `+`, `?`), alternation (`|`), and parenthesized groups (`(...)`).
* **Zero Allocation During Matching:** Scratch buffers for active NFA thread simulation and visited state generation sets are allocated once at pattern compilation (`patt_comp`), requiring zero heap allocations during subsequent match executions.

### 12.2 Core API Methods

The `std.patt` module exposes 5 core pattern operations supporting both free-function and Uniform Function Call Syntax (UFCS) on compiled `@Pattern`:

1. **`test(pat: @Pattern, text: string) -> bool` / `patt_test`:** Returns `true` if the pattern matches anywhere in `text` (adhering to anchors `^` and `$`).
2. **`find(pat: @Pattern, text: string) -> PattMatch` / `patt_find`:** Returns the first leftmost-longest match descriptor containing `ok: bool`, `start: usize`, `end: usize`, and `text: StrSlice`.
3. **`find_all(pat: @Pattern, text: string) -> RawShelf` / `patt_find_all`:** Finds all non-overlapping matches in `text` and returns them as a dynamic shelf of `PattMatch`.
4. **`replace(pat: @Pattern, text: string, repl: string) -> string` / `patt_replace`:** Replaces all non-overlapping matches with `repl`, allocating the exact resultant string buffer.
5. **`split(pat: @Pattern, text: string) -> RawShelf` / `patt_split`:** Splits `text` around pattern matches, returning a dynamic shelf of `StrSlice` tokens.

```velo
use std.patt
use std.io

act main() {
    mut pat = patt_comp("[0-9]+")

    // 1. test
    let has_digits = pat.test("item 42")

    // 2. find
    let m = pat.find("price is 99 dollars")
    if m.ok {
        io.println("Found match: start={m.start}, end={m.end}")
    }

    // 3. find_all
    mut all = pat.find_all("10 apples, 20 oranges, 30 bananas")
    io.println("Total matches: {all.len}")

    // 4. replace
    let masked = pat.replace("secret 123 code 456", "###")
    io.println(masked) // "secret ### code ###"

    // 5. split
    mut csv_pat = patt_comp("[,;]+")
    mut parts = csv_pat.split("apple,banana;cherry,,dates")

    pattern_free(@pat)
    pattern_free(@csv_pat)
}
```

---

## 13. Standard Networking & DNS Resolution Subsystem (`std.net`)

Velo provides cross-platform socket networking (TCP client/server, UDP datagrams) with integrated system DNS resolution via `getaddrinfo` and `getnameinfo`.

### 13.1 DNS Lookup Acts

The `std.net` module provides 4 core hostname resolution acts supporting both direct calls and module-aliased calls (`use std.net :> net`):

1. **`lookup(host: string) -> string or string`:** Resolves `host` to its preferred IP address (IPv4 or IPv6, depending on OS priority via `AF_UNSPEC`).
2. **`lookup_ipv4(host: string) -> string or string`:** Specifically queries DNS for an IPv4 address (`AF_INET` / A record).
3. **`lookup_ipv6(host: string) -> string or string`:** Specifically queries DNS for an IPv6 address (`AF_INET6` / AAAA record).
4. **`lookup_all(host: string) -> RawShelf or string`:** Queries all available addresses registered for the hostname, returning a dynamic shelf of unique IP strings.

<!-- not-compiled -->
```velo
use std.net
use std.io

act main() {
    // 1. Preferred IP (IPv4 or IPv6)
    let ip = lookup("localhost") or fail

    // 2. Guaranteed IPv4
    let ip4 = lookup_ipv4("localhost") or fail // "127.0.0.1"

    // 3. Guaranteed IPv6
    let ip6 = lookup_ipv6("localhost") or fail // "::1"

    // 4. All addresses (multi-homed)
    mut ips = lookup_all("localhost") or fail
    io.println("Total addresses: {ips.len}")
    shelf_free(@ips)
}
```

### 13.2 Hostname Connection Support

Both synchronous (`tcp_connect`) and asynchronous (`async_tcp_connect`) TCP sockets accept domain names and hostnames interchangeably with numeric IP literals:

```velo
use std.net

act main() {
    // Connects via hostname resolution automatically
    let stream = tcp_connect("localhost", 8080 as u16)
    if stream != null {
        tcp_close(stream)
    }
}
```

---

## 14. Standard Time & Timezone Subsystem (`std.time`)

Velo provides high-resolution monotonic timing, wall-clock epoch timestamps, Gregorian civil calendar conversions, ISO-8601 formatting, and cross-platform timezone management with local time conversion (`std/time/tz.vl`).

### 14.1 Timezone Representation (`Tz`)

A timezone in Velo is represented by the `Tz` data structure:

```velo
view data Tz {
    name: string   // Timezone name or offset descriptor (e.g. "UTC", "EST", "India Standard Time", "+05:30")
    offset: i32    // Offset from UTC in seconds (positive east of UTC, negative west of UTC)
    dst: bool      // True if daylight saving time (DST) is active
}
```

### 14.2 Core Timezone Acts

- **`tz_sys() -> Tz`:** Detects and returns the system local timezone of the host operating system. On Windows, this reads the system timezone configuration via Win32 `GetTimeZoneInformation`. On Linux and macOS, it reads `/etc/localtime` (or `/var/db/timezone/zoneinfo`) via direct `TZif` binary file parsing (RFC 8536 / RFC 4833) with fallback to POSIX `localtime_r`.
- **`tz_utc() -> Tz`:** Returns the standard UTC timezone (`offset: 0`, `dst: false`, `name: "UTC"`).
- **`tz_make(name: string, offset_sec: i32) -> Tz`:** Constructs a fixed-offset timezone descriptor (`dst: false`).
- **`tz_with_dst(name: string, offset_sec: i32, dst: bool) -> Tz`:** Constructs a timezone descriptor with explicit DST status.
- **`tz_parse_offset(str_offset: string) -> i32`:** Parses ISO offset strings (`"+05:30"`, `"-05:00"`, `"+0900"`, `"Z"`, `"UTC"`) into total seconds.
- **`tz_parse_posix(tz_str: string) -> Tz`:** Parses POSIX-TZ environment variable strings (`"EST5EDT,M3.2.0,M11.1.0"`, `"JST-9"`, `"UTC0"`).
- **`tz_parse_tzif_data(buf: @u8, len: usize, now_s: i64) -> Tz`:** Parses raw binary `TZif` v1, v2, or v3 data and resolves the active UTC offset and abbreviation for the given epoch timestamp.

### 14.3 Local Time Conversions & Formatting

- **`time_now_local() -> DateTime`:** Returns the current wall-clock date and time in the system's local timezone.
- **`time_to_local(dt: @DateTime, tz: @Tz) -> DateTime`** (alias **`time_local`**): Converts a UTC `DateTime` to a local `DateTime` in the given `tz`.
- **`time_to_utc(dt: @DateTime, tz: @Tz) -> DateTime`:** Converts a local `DateTime` in `tz` back to UTC.
- **`time_format_iso8601_tz(dt: @DateTime, tz: @Tz, dest: @u8, dest_cap: usize) -> StrSlice`:** Formats a timestamp with timezone offset (`"2026-11-22T17:30:00+05:30"` or `"Z"`).
- **`time_format_iso8601_tz_str(a: @Arena, dt: @DateTime, tz: @Tz) -> string`:** Regional Arena-allocated variant of `time_format_iso8601_tz`.

```velo
use std.time
use std.io

act main() {
    // 1. Current system local time and zone
    let sys_tz = tz_sys()
    let local_dt = time_now_local()
    io.println("System zone: " + sys_tz.name)

    // 2. Convert UTC timestamp to custom timezone
    let utc_dt = time_epoch_to_datetime(1767268800) // 2026-01-01 12:00:00 UTC
    let tokyo = tz_make("JST", 9 * 3600)
    let tokyo_dt = time_to_local(@utc_dt, @tokyo)

    // 3. Convert back to UTC
    let back_utc = time_to_utc(@tokyo_dt, @tokyo)

    // 4. ISO-8601 with offset
    mut buf: [32]u8
    let s = time_format_iso8601_tz(@tokyo_dt, @tokyo, @buf[0], 32)
    // s == "2026-01-01T21:00:00+09:00"
}
```

## 15. Standard Compression & Decompression Subsystem (`std.compress`)

Velo provides pure native compression, decompression, framing, and checksum verification with zero C runtime dependencies (`std/compress/`). It fully conforms to:
- **RFC 1951:** DEFLATE Compressed Data Format Specification (Stored, Fixed Huffman, and Dynamic Huffman blocks, LSB-first bitstream handling, sliding-window LZ77 match decoding and encoding).
- **RFC 1950:** ZLIB Compressed Data Format Specification (CMF/FLG header integrity, check bit validation, big-endian Adler-32 checksum verification).
- **RFC 1952:** GZIP File Format Specification (ID1/ID2 magic detection, compression method validation, header flag parsing for FTEXT/FHCRC/FEXTRA/FNAME/FCOMMENT, IEEE 802.3 CRC-32 verification, and little-endian ISIZE uncompressed length validation).

### 15.1 Core Decompression Acts

- **`gzip_decode(data: @u8, len: usize) -> RawShelf or string`:** Decompresses an RFC 1952 Gzip stream into a `RawShelf` of bytes after validating header flags, CRC-32, and ISIZE.
- **`gzip_decode_str(data: @u8, len: usize) -> string or string`:** Decompresses an RFC 1952 Gzip stream directly into a null-terminated heap `string`.
- **`zlib_decode(data: @u8, len: usize) -> RawShelf or string`:** Decompresses an RFC 1950 Zlib stream into a `RawShelf` of bytes after validating CMF/FLG headers and Adler-32.
- **`zlib_decode_str(data: @u8, len: usize) -> string or string`:** Decompresses an RFC 1950 Zlib stream directly into a null-terminated heap `string`.
- **`inflate(data: @u8, len: usize) -> RawShelf or string`:** Decompresses a raw RFC 1951 DEFLATE stream into a `RawShelf`.
- **`inflate_str(data: @u8, len: usize) -> string or string`:** Decompresses a raw RFC 1951 DEFLATE stream directly into a null-terminated heap `string`.
- **`inflate_from_str(s: string) -> string or string`:** Convenience wrapper decompressing a raw RFC 1951 DEFLATE string payload into a `string`.

### 15.2 Core Compression Acts

- **`gzip_encode(data: @u8, len: usize) -> RawShelf or string`:** Compresses raw bytes into an RFC 1952 Gzip stream complete with standard 10-byte header, CRC-32, and ISIZE footer.
- **`gzip_encode_str(s: string) -> RawShelf or string`:** Compresses a string into an RFC 1952 Gzip stream.
- **`zlib_encode(data: @u8, len: usize) -> RawShelf or string`:** Compresses raw bytes into an RFC 1950 Zlib stream with CMF/FLG header and Adler-32 footer.
- **`zlib_encode_str(s: string) -> RawShelf or string`:** Compresses a string into an RFC 1950 Zlib stream.
- **`deflate(data: @u8, len: usize) -> RawShelf or string`:** Compresses raw bytes into an RFC 1951 DEFLATE stream using LZ77 match search (3..258 length, 32KB window) and Fixed Huffman coding.
- **`deflate_str(s: string) -> RawShelf or string`:** Compresses a string into an RFC 1951 DEFLATE stream.

### 15.3 Checksums

- **`adler32(data: @u8, len: usize) -> u32`:** Computes the 32-bit Adler-32 checksum ($s_1, s_2 \pmod{65521}$) over raw bytes.
- **`adler32_str(s: string) -> u32`:** Computes the 32-bit Adler-32 checksum of a string.

### 15.4 Usage Example

<!-- not-compiled -->
```velo
use std.compress
use std.io

view act main() {
    let payload = "HTTP body text to compress and decompress across networks."

    // 1. Gzip compression and decompression
    let gz = gzip_encode_str(payload) or return
    let decomp_text = gzip_decode_str(gz.data, gz.len) or return
    // decomp_text == payload

    // 2. Zlib compression and decompression
    let zl = zlib_encode_str(payload) or return
    let zl_text = zlib_decode_str(zl.data, zl.len) or return
    // zl_text == payload

    // 3. Raw DEFLATE
    let def = deflate_str(payload) or return
    let def_text = inflate_str(def.data, def.len) or return
    // def_text == payload
}
```

## 16. Standard JSON Subsystem (`std.json`)

Velo provides an RFC 8259 compliant JSON processing subsystem with zero C runtime dependencies (`std/json/`). It offers DOM parsing, AST manipulation, compact and pretty serialization, and a compile-time reflection-based typed struct codec.

### 16.1 DOM AST & Parsing

- **`JsonValue`:** Represents a JSON node (null, bool, int, float, string, array, object) backed by zero-allocation `StrSlice` views and regional `Arena` allocation.
- **`json_parse(arena: @Arena, src: StrSlice, err: @JsonParseError) -> @JsonValue`:** Parses JSON text into a DOM node tree.
- **`json_parse_doc(src: StrSlice, arena_cap: usize) -> JsonDoc`:** Parses JSON text into a self-contained managed document.
- **`json_stringify(arena: @Arena, val: @JsonValue) -> StrSlice`:** Compactly serializes a DOM node into JSON text.
- **`json_pretty(arena: @Arena, val: @JsonValue, indent_size: i32) -> StrSlice`:** Formats a DOM node with indentation spaces and newlines.

### 16.2 Typed Struct Codec (`std.json` / `std/json/codec.vl`)

Uses compile-time struct reflection (`field_count`, `field_name`, `field_type`, `field_value`) to encode and decode native Velo structs without manual serialization boilerplate:

- **`json_encode[T](target: @T) -> string`:** Serializes any data struct `@target` to an owned, heap-allocated JSON string.
- **`json_encode_to_sb[T](target: @T, sb: @StrBuilder)`:** Streams serialized JSON directly into an existing `StrBuilder` (zero-copy composition).
- **`json_decode[T](target: @T, src: string) -> bool or string`:** Parses JSON text and populates fields of `@target`. Returns `true` or an error diagnostic string.
- **`json_decode_into[T](src: string, target: @T) -> bool or string`:** Convenience alias accepting the JSON source string first.
- **`json_decode_val[T](target: @T, node: @JsonValue) -> bool or string`:** Decodes an existing parsed DOM object into `@target`.

#### Supported Data Types

1. **Primitives:** `string`, signed integers (`i8`, `i16`, `i32`, `i64`, `isize`), unsigned integers (`u8`, `u16`, `u32`, `u64`, `usize`), floating-point (`f32`, `f64`), and `bool`.
2. **Optionals:** `?string`, `?i8`..`?i64`, `?u8`..`?u64`, `?f32`, `?f64`, `?bool`. Null JSON nodes or missing properties decode to `null`.
3. **Nested Structs:** Arbitrary multi-level nested `data` structs are serialized and deserialized recursively.
4. **Tagged Unions:** Unit variant enums (e.g. `Role`, `Status`) and payload sum types (e.g. `Shape`) serialize with variant tags and decode safely.

### 16.3 Typed Codec Usage Example

```velo
use std.io
use std.json

view data Address {
    city: string
    zip: i32
}

view data UserProfile {
    id: i64
    name: string
    is_active: bool
    email: ?string
    role: Role
    addr: Address
}

act main() -> i32 {
    let opt_email: ?string = "alice@example.org"
    mut user = UserProfile{
        id: 101,
        name: "Alice",
        is_active: true,
        email: opt_email,
        role: Role.Admin,
        addr: Address{ city: "Berlin", zip: 10115 }
    }

    // 1. Serialization
    let json_text = json_encode(@user)
    io.println(json_text)

    // 2. Deserialization
    mut decoded: UserProfile
    let res = json_decode(@decoded, json_text)
    if !res.ok {
        io.println("Decode error: {res.err}")
        return 1
    }
    // decoded.id == 101, decoded.addr.city == "Berlin"
    return 0
}
```

## 17. Standard CSV Subsystem (`std.csv`)

Velo provides an RFC 4180 compliant CSV parser and generator with zero C runtime dependencies (`std/csv/`). It supports incremental streaming over an `@BufferedReader` with strictly bounded memory, zero-copy in-memory slicing, quote unescaping, blank-line skipping, and robust error diagnostics.

### 17.1 Reader Types & Functions

- **`CsvReader`:** Parser state tracking either an in-memory `StrSlice` or an incremental `@BufferedReader` stream.
- **`CsvRecord`:** Linked list of parsed `CsvField` nodes representing one row (`rec.row`, `rec.count`, `rec.first`, `rec.ok`).
- **`CsvField`:** Field view containing `slice: StrSlice` and `quoted: bool`.
- **`csv_reader_init(s: StrSlice) -> CsvReader`:** Initializes an in-memory CSV reader over a `StrSlice`. Unquoted and escape-free fields provide zero-allocation views directly into the source.
- **`csv_reader_init_str(s: string) -> CsvReader`:** Convenience wrapper initializing an in-memory reader over a null-terminated string.
- **`csv_reader_init_stream(br: @BufferedReader) -> CsvReader`:** Initializes an incremental streaming CSV reader. Reads data in 4KB chunks from the OS handle.
- **`csv_read_record(r: @CsvReader, arena: @Arena, out: @CsvRecord) -> bool`:** Parses the next RFC 4180 record. Fields and record nodes are allocated in `arena`. Returns `true` if a record was parsed, `false` on EOF or error.
- **`csv_reader_done(r: @CsvReader) -> bool`:** Returns `true` when all records have been consumed or a fatal parse error was encountered.
- **`csv_record_field(rec: @CsvRecord, index: usize) -> StrSlice`:** Retrieves the field view at `index` (or empty slice if out of bounds).
- **`csv_record_field_quoted(rec: @CsvRecord, index: usize) -> bool`:** Returns `true` if the field at `index` was quoted in the source.
- **`csv_record_field_str(rec: @CsvRecord, index: usize, arena: @Arena) -> string`:** Materializes the field as a null-terminated string in `arena`.

### 17.2 Bounded-Memory Streaming Protocol

When streaming over a file or network stream with `csv_reader_init_stream`, peak RSS remains strictly bounded ($O(\text{row\_size})$) regardless of file size (e.g. 1,000,000+ rows) by resetting the per-record `Arena` after processing each row:

```velo
use std.csv
use std.mem
use std.io

act process_large_csv(path: string) -> bool {
    let fh = io_file_open_str(path, IO_READ)
    if !io_is_valid_handle(fh) { return false }
    mut br = reader_init(fh)
    defer reader_free(@br)
    defer io_file_close(fh)

    mut r = csv_reader_init_stream(@br)
    mut arena = arena_init(65536)
    defer arena_free(@arena)

    mut rec = CsvRecord { row: 0, first: null, count: 0, ok: false }
    loop csv_read_record(@r, @arena, @rec) {
        // Access fields safely within this iteration
        let col0 = csv_record_field(@rec, 0)
        let col1 = csv_record_field(@rec, 1)

        // Reset arena bump offset to 0 — reclaims all row memory in O(1)
        arena_reset(@arena)
    }

    return !r.had_error
}
```

## 18. Standard Collections Subsystem (`std.coll`)

Velo provides standard collection primitives with zero C runtime dependencies (`std/coll/`): dynamic shelf array (`shelf.vl`), FIFO circular ring buffer (`ring.vl`), open-addressing hash table (`map.vl`), introsort (`sort.vl`), and advanced data structures:

### 18.1 Hash Set (`std/coll/set.vl`)

`RawSet` wraps `RawMap` to provide an open-addressing, linear-probing hash set with tombstone deletion and mathematical set algebra.

- **Types:** `RawSet { map: RawMap }`
- **Creation & Lifetime:**
  - `set_create(elem_size: usize, is_string: bool, initial_cap: usize) -> RawSet`: Initializes a set with power-of-two bucket capacity.
  - `set_free(s: @RawSet)`: Releases backing table allocations.
  - `set_clear(s: @RawSet)`: Clears elements in $O(N)$ while retaining table capacity.
- **Inspection:**
  - `set_len(s: @RawSet) -> usize`: Number of distinct elements stored.
  - `set_cap(s: @RawSet) -> usize`: Allocated bucket capacity.
  - `set_is_empty(s: @RawSet) -> bool`: Returns `set_len(s) == 0`.
- **Operations:**
  - `set_add(s: @RawSet, elem_ptr: @u8) -> bool`: Inserts element (no-op if already present). Returns `true`.
  - `set_contains(s: @RawSet, elem_ptr: @u8) -> bool`: Key existence check in $O(1)$ expected time.
  - `set_remove(s: @RawSet, elem_ptr: @u8) -> bool`: Removes element using tombstone recycling. Returns `true` if found.
- **Typed Helpers:**
  - Strings: `set_create_str(initial_cap: usize)`, `set_add_str(s: @RawSet, str_val: string)`, `set_contains_str(s: @RawSet, str_val: string)`, `set_remove_str(s: @RawSet, str_val: string)`.
  - Integers (`i64`): `set_create_i64(initial_cap: usize)`, `set_add_i64(s: @RawSet, val: i64)`, `set_contains_i64(s: @RawSet, val: i64)`, `set_remove_i64(s: @RawSet, val: i64)`.
- **Set Algebra & Conversions:**
  - `set_to_shelf(s: @RawSet) -> RawShelf`: Extracts keys into a dynamic `RawShelf`.
  - `set_union(a: @RawSet, b: @RawSet) -> RawSet`: Computes $A \cup B$.
  - `set_intersection(a: @RawSet, b: @RawSet) -> RawSet`: Computes $A \cap B$.
  - `set_difference(a: @RawSet, b: @RawSet) -> RawSet`: Computes $A \setminus B$.
  - `set_is_subset(a: @RawSet, b: @RawSet) -> bool`: Returns `true` if $A \subseteq B$.
  - `set_is_disjoint(a: @RawSet, b: @RawSet) -> bool`: Returns `true` if $A \cap B = \emptyset$.
  - `set_equals(a: @RawSet, b: @RawSet) -> bool`: Returns `true` if $A = B$.

### 18.2 Double-Ended Queue (`std/coll/deque.vl`)

`RawDeque` wraps `RawRing` to provide an amortized $O(1)$ double-ended queue backed by a dynamically growing circular buffer.

- **Types:** `RawDeque { ring_buf: RawRing }`
- **Creation & Lifetime:** `deque_create(elem_size: usize, initial_cap: usize) -> RawDeque`, `deque_free(d: @RawDeque)`, `deque_clear(d: @RawDeque)`.
- **Inspection:** `deque_len(d: @RawDeque) -> usize`, `deque_cap(d: @RawDeque) -> usize`, `deque_is_empty(d: @RawDeque) -> bool`.
- **Queue Operations:**
  - `deque_push_back(d: @RawDeque, elem_ptr: @u8) -> bool` / `deque_push_back_i64(d: @RawDeque, val: i64) -> bool`
  - `deque_push_front(d: @RawDeque, elem_ptr: @u8) -> bool` / `deque_push_front_i64(d: @RawDeque, val: i64) -> bool`
  - `deque_pop_back(d: @RawDeque, out_elem: @u8) -> bool` / `deque_pop_back_i64(d: @RawDeque, out_val: @i64) -> bool`
  - `deque_pop_front(d: @RawDeque, out_elem: @u8) -> bool` / `deque_pop_front_i64(d: @RawDeque, out_val: @i64) -> bool`
  - `deque_peek_back(d: @RawDeque) -> @u8` / `deque_peek_back_i64(d: @RawDeque, out_val: @i64) -> bool`
  - `deque_peek_front(d: @RawDeque) -> @u8` / `deque_peek_front_i64(d: @RawDeque, out_val: @i64) -> bool`
- **Random Access & Rotation:**
  - `deque_get(d: @RawDeque, index: usize) -> @u8` / `deque_get_i64(d: @RawDeque, index: usize, out_val: @i64) -> bool`
  - `deque_set(d: @RawDeque, index: usize, elem_ptr: @u8) -> bool` / `deque_set_i64(d: @RawDeque, index: usize, val: i64) -> bool`
  - `deque_rotate(d: @RawDeque, n: isize) -> bool`: Rotates deque $n$ steps ($n > 0$ rotates right wrapping tail to head matching Python `collections.deque.rotate`, $n < 0$ rotates left).
  - `deque_to_shelf(d: @RawDeque) -> RawShelf`: Copies deque elements in logical head-to-tail order to a newly allocated `RawShelf`.

### 18.3 Binary Heap & Priority Queue (`std/coll/heap.vl`)

`RawBinaryHeap` provides a binary min/max heap backed by dynamic array storage, custom comparators, $O(\log N)$ push and pop, $O(1)$ peek, and $O(N)$ bottom-up heapify.

- **Types:** `RawBinaryHeap { data: @u8, elem_size: usize, len: usize, cap: usize, is_min: bool, cmp: act(@u8, @u8) -> i32 }`
- **Creation & Lifetime:**
  - `bheap_create(elem_size: usize, initial_cap: usize, is_min: bool, cmp: act(@u8, @u8) -> i32) -> RawBinaryHeap`: Initializes heap with custom comparator.
  - `bheap_create_min_i64(initial_cap: usize) -> RawBinaryHeap`: Min-heap for `i64`.
  - `bheap_create_max_i64(initial_cap: usize) -> RawBinaryHeap`: Max-heap for `i64`.
  - `bheap_create_min_f64(initial_cap: usize) -> RawBinaryHeap`: Min-heap for `f64`.
  - `bheap_create_max_f64(initial_cap: usize) -> RawBinaryHeap`: Max-heap for `f64`.
  - `bheap_free(h: @RawBinaryHeap)`, `bheap_clear(h: @RawBinaryHeap)`.
- **Operations:**
  - `bheap_push(h: @RawBinaryHeap, elem_ptr: @u8) -> bool` / `bheap_push_i64(h: @RawBinaryHeap, val: i64) -> bool`: Sifts up in $O(\log N)$.
  - `bheap_pop(h: @RawBinaryHeap, out_elem: @u8) -> bool` / `bheap_pop_i64(h: @RawBinaryHeap, out_val: @i64) -> bool`: Removes and returns root, sifting down in $O(\log N)$.
  - `bheap_peek(h: @RawBinaryHeap) -> @u8` / `bheap_peek_i64(h: @RawBinaryHeap, out_val: @i64) -> bool`: Returns root element without removal in $O(1)$.
  - `bheap_push_pop(h: @RawBinaryHeap, in_elem: @u8, out_elem: @u8) -> bool`: Pushes `in_elem` then pops root in a single sift pass ($O(\log N)$).
  - `bheap_replace(h: @RawBinaryHeap, in_elem: @u8, out_elem: @u8) -> bool`: Pops root then pushes `in_elem` in $O(\log N)$.
  - `bheap_heapify(h: @RawBinaryHeap)`: Re-establishes the heap invariant bottom-up in $O(N)$.
  - `bheap_to_shelf(h: @RawBinaryHeap) -> RawShelf`: Converts raw heap buffer to a `RawShelf`.

## 19. Fixed-Point Decimal Arithmetic Subsystem (`std.math.decimal`)

Velo provides an exact base-10 fixed-point decimal arithmetic library (`std/math/decimal.vl`) with zero C runtime dependencies. It guarantees exact decimal representation ($0.1 + 0.2 == 0.3$), eliminating the binary representation artifacts of IEEE 754 floating point numbers for financial accounting, invoicing, taxation, and cent arithmetic.

### 19.1 Representation & Scale

A `Decimal` represents a base-10 rational number defined as $\text{units} \times 10^{-\text{scale}}$:
- **`Decimal { units: i64, scale: u32 }`**: `units` holds the scaled 64-bit integer signed mantissa, and `scale` specifies the number of fractional decimal digits (from $0$ up to $18$).
- **`dec_new(units: i64, scale: u32) -> Decimal`**: Constructs a decimal with explicit units and scale.
- **`dec_from_i64(val: i64) -> Decimal`**: Constructs a decimal from an integer with scale 0.
- **`dec_from_cents(cents: i64) -> Decimal`**: Constructs a decimal representing money in cents with scale 2.
- **`dec_to_cents(d: Decimal, mode: u32) -> i64`**: Rescales decimal to scale 2 using the specified rounding mode and returns units in cents.

### 19.2 Rounding Modes

The subsystem implements all six standard financial and IEEE rounding modes:

| Mode Constant | Value | Description |
| :--- | :---: | :--- |
| `ROUND_HALF_EVEN` | `0` | **Banker's rounding**: rounds to the nearest neighbor; ties resolve to the nearest even integer. Standard in financial accounting. |
| `ROUND_HALF_UP` | `1` | **Arithmetic rounding**: rounds to the nearest neighbor; ties resolve away from zero ($+2.5 \to 3, -2.5 \to -3$). |
| `ROUND_DOWN` | `2` | **Truncation**: rounds towards zero ($+2.9 \to 2, -2.9 \to -2$). |
| `ROUND_UP` | `3` | **Away from zero**: rounds to the next magnitude ($+2.1 \to 3, -2.1 \to -3$). |
| `ROUND_FLOOR` | `4` | **Towards $-\infty$**: rounds downwards ($+2.9 \to 2, -2.1 \to -3$). |
| `ROUND_CEIL` | `5` | **Towards $+\infty$**: rounds upwards ($+2.1 \to 3, -2.9 \to -2$). |

### 19.3 Arithmetic & Rescaling

- **`dec_rescale(d: Decimal, new_scale: u32, mode: u32) -> Decimal`**: Converts a decimal to `new_scale`. Scale expansions are exact; scale reductions apply the specified rounding mode without intermediate floating-point conversions.
- **`dec_add(a: Decimal, b: Decimal) -> Decimal`**: Adds two decimals, automatically aligning operands to the larger scale ($0.1 + 0.2 == 0.3$).
- **`dec_sub(a: Decimal, b: Decimal) -> Decimal`**: Subtracts $b$ from $a$, aligning to the larger scale ($0.3 - 0.1 == 0.2$).
- **`dec_mul(a: Decimal, b: Decimal) -> Decimal`**: Multiplies two decimals; result scale is $a.\text{scale} + b.\text{scale}$.
- **`dec_div(a: Decimal, b: Decimal, target_scale: u32, mode: u32) -> Decimal`**: Divides $a$ by $b$, producing exact `target_scale` rounded according to `mode`.
- **`dec_cmp(a: Decimal, b: Decimal) -> i32`**: Returns $-1$ if $a < b$, $0$ if $a == b$, and $+1$ if $a > b$, performing scale alignment.
- **`dec_eq(a: Decimal, b: Decimal) -> bool`**: Returns `true` if $a == b$ numerically regardless of representation scale (e.g. `1.5 == 1.50`).
- **`dec_lt`, `dec_lte`, `dec_gt`, `dec_gte`**: Standard relational comparisons.
- **`dec_abs`, `dec_neg`, `dec_is_zero`, `dec_is_negative`**: Sign operations and predicates.

### 19.4 Parsing & Formatting

- **`dec_from_str(s: string) -> Decimal`**: Parses ASCII decimal strings with optional leading sign and fractional point (e.g. `"123.45"`, `"-0.05"`, `"+10"`, `".5"`).
- **`dec_to_str(d: Decimal) -> string`**: Formats the decimal as a null-terminated heap string with exact fractional padding to `scale` digits (e.g. `dec_to_str(dec_from_cents(5)) == "0.05"`).










