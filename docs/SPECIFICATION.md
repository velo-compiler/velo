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
while     loop      in        return    zone      extern
use       true      false     null      sizeof    as
and       or        not
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

### 7.2 Loops

#### `while` Loop:
```rust
mut step = 0
while step < 10 {
    step += 1
}
```

#### `loop .. in` Range Loop:
```rust
loop i in 0..100 {
    io.println("{i}")
}
```

---

## 8. Foreign Function Interface (`extern`)

Directly bind to any existing C library function with zero runtime overhead:

```rust
extern act puts(s: @u8) -> i32
extern act sqrtf(val: f32) -> f32
```
