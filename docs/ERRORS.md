# Velo Compiler Error Code Registry

The Velo compiler assigns stable error codes to user-visible diagnostics formatted as `VELO-E####`.
Each error code corresponds to a specific semantic, syntactic, or type check violation, enabling
developers, IDEs, and language tooling to look up diagnostic explanations and remediation steps.

## Looking Up Errors

You can look up any diagnostic code using the compiler CLI:

```bash
velo explain VELO-E0001
```

Or browse the registry below.

---

## Registry Index

| Error Code | Category | Name / Summary |
| :--- | :--- | :--- |
| [`VELO-E0001`](#velo-e0001-undeclared-identifier) | Semantic | Undeclared identifier |
| [`VELO-E0002`](#velo-e0002-mismatched-argument-count-in-function-call) | Semantic | Mismatched argument count in function call |
| [`VELO-E0003`](#velo-e0003-array-index-out-of-bounds) | Semantic | Array index out of bounds |
| [`VELO-E0004`](#velo-e0004-array-index-must-be-an-integer) | Semantic | Array index must be an integer |
| [`VELO-E0005`](#velo-e0005-division-by-zero) | Semantic | Division by zero |
| [`VELO-E0006`](#velo-e0006-modulo-by-zero) | Semantic | Modulo by zero |
| [`VELO-E0007`](#velo-e0007-instantiating-unknown-struct-type) | Semantic | Instantiating unknown struct type |
| [`VELO-E0008`](#velo-e0008-unknown-field-in-struct-literal) | Semantic | Unknown field in struct literal |
| [`VELO-E0009`](#velo-e0009-struct-literal-is-missing-field-with-no-default) | Semantic | Struct literal is missing field with no default |
| [`VELO-E0010`](#velo-e0010-mismatched-element-type-in-array-literal) | Semantic | Mismatched element type in array literal |
| [`VELO-E0011`](#velo-e0011-cannot-infer-kind-type-for-variant) | Semantic | Cannot infer kind type for variant |
| [`VELO-E0012`](#velo-e0012-mismatched-argument-count-in-variant-constructor) | Semantic | Mismatched argument count in variant constructor |
| [`VELO-E0013`](#velo-e0013-tuple-index-out-of-bounds) | Semantic | Tuple index out of bounds |
| [`VELO-E0014`](#velo-e0014-range-loop-step-must-be-greater-than-zero) | Semantic | Range loop step must be greater than zero |
| [`VELO-E0015`](#velo-e0015-shelf-elements-cannot-be-null-use-a-t-pointer-element) | Semantic | Shelf elements cannot be null (use a @T pointer element) |
| [`VELO-E0016`](#velo-e0016-shelfdyn-put-cannot-box-a-void-value) | Semantic | Shelf[dyn] put: cannot box a void value |
| [`VELO-E0017`](#velo-e0017-map-values-cannot-be-null-use-a-t-pointer-value) | Semantic | Map values cannot be null (use a @T pointer value) |
| [`VELO-E0018`](#velo-e0018-cannot-infer-element-type-of-empty-shelf-literal--annotate-it) | Semantic | Cannot infer element type of empty shelf literal — annotate it |
| [`VELO-E0019`](#velo-e0019-cannot-infer-element-type-of-empty-ring-literal--annotate-it) | Semantic | Cannot infer element type of empty ring literal — annotate it |
| [`VELO-E0020`](#velo-e0020-raw-pointer-dereference-requires-an-unsafe----block) | Semantic | Raw pointer dereference requires an 'unsafe { ... }' block |

---

## Detailed Entries

### VELO-E0001: Undeclared identifier

An identifier was referenced in an expression, but no local variable, parameter, global constant,
function, or imported symbol with that name exists in the current scope.

#### Erroneous Code
```velo
act main() -> i32 {
    return foo + 1  // error: 'foo' is not declared
}
```

#### Corrected Code
```velo
act main() -> i32 {
    let foo = 10
    return foo + 1
}
```

---

### VELO-E0002: Mismatched argument count in function call

A function, method, or extern function was invoked with a different number of arguments than its
declaration requires.

#### Erroneous Code
```velo
act add(a: i32, b: i32) -> i32 {
    return a + b
}

act main() -> i32 {
    return add(1)  // error: expects 2 arguments, got 1
}
```

#### Corrected Code
```velo
act main() -> i32 {
    return add(1, 2)
}
```

---

### VELO-E0003: Array index out of bounds

A fixed-size array literal or array variable was accessed at a compile-time constant index that is
greater than or equal to the array length, or negative.

#### Erroneous Code
```velo
act main() -> i32 {
    let a: [3]i32 = [10, 20, 30]
    return a[5]  // error: index 5 out of bounds for array of length 3
}
```

#### Corrected Code
```velo
act main() -> i32 {
    let a: [3]i32 = [10, 20, 30]
    return a[2]
}
```

---

### VELO-E0004: Array index must be an integer

An array subscript expression (`a[i]`) used an index that does not evaluate to an integer type
(e.g., string, float, struct).

#### Erroneous Code
```velo
act main() -> i32 {
    let a: [2]i32 = [1, 2]
    return a["key"]  // error: index must be an integer
}
```

#### Corrected Code
```velo
act main() -> i32 {
    let a: [2]i32 = [1, 2]
    return a[0]
}
```

---

### VELO-E0005: Division by zero

A division operation (`/`) attempted to divide by a compile-time constant zero literal or expression.

#### Erroneous Code
```velo
act main() -> i32 {
    let x = 100 / 0  // error: division by zero
    return x
}
```

#### Corrected Code
```velo
act main() -> i32 {
    let divisor = 2
    let x = 100 / divisor
    return x
}
```

---

### VELO-E0006: Modulo by zero

A modulo operation (`%`) attempted to compute the remainder with a compile-time constant zero divisor.

#### Erroneous Code
```velo
act main() -> i32 {
    let x = 100 % 0  // error: modulo by zero
    return x
}
```

#### Corrected Code
```velo
act main() -> i32 {
    let x = 100 % 3
    return x
}
```

---

### VELO-E0007: Instantiating unknown struct type

A struct construction literal (`TypeName { ... }`) named a type that has not been declared as a `data`
struct in the current scope or imported modules.

#### Erroneous Code
```velo
act main() -> i32 {
    let p = NonExistentPoint { x: 10, y: 20 }
    return 0
}
```

#### Corrected Code
```velo
data NonExistentPoint {
    x: i32
    y: i32
}

act main() -> i32 {
    let p = NonExistentPoint { x: 10, y: 20 }
    return 0
}
```

---

### VELO-E0008: Unknown field in struct literal

A struct constructor initialized a field name that does not exist in the definition of the struct type.

#### Erroneous Code
```velo
data Point {
    x: i32
    y: i32
}

act main() -> i32 {
    let p = Point { x: 1, y: 2, z: 3 }  // error: 'z' is not a field of Point
    return 0
}
```

#### Corrected Code
```velo
act main() -> i32 {
    let p = Point { x: 1, y: 2 }
    return 0
}
```

---

### VELO-E0009: Struct literal is missing field with no default

A struct literal omitted one or more fields that do not have a default value in the struct declaration.

#### Erroneous Code
```velo
data Point {
    x: i32
    y: i32
}

act main() -> i32 {
    let p = Point { x: 1 }  // error: missing required field 'y'
    return 0
}
```

#### Corrected Code
```velo
act main() -> i32 {
    let p = Point { x: 1, y: 0 }
    return 0
}
```

---

### VELO-E0010: Mismatched element type in array literal

An array literal (`[elem1, elem2, ...]`) contained elements with incompatible types without an explicit
type annotation.

#### Erroneous Code
```velo
act main() -> i32 {
    let a = [10, "hello"]  // error: cannot mix integer and string in array literal
    return 0
}
```

#### Corrected Code
```velo
act main() -> i32 {
    let a = [10, 20]
    return 0
}
```

---

### VELO-E0011: Cannot infer kind type for variant

A bare variant literal (`.VariantName`) was used in a context where the target `kind` type cannot be
inferred from variable annotations or expected parameter types, and no unambiguous `kind` defines that variant.

#### Erroneous Code
```velo
act main() -> i32 {
    let v = .NoSuchVariant  // error: cannot infer which kind type this variant belongs to
    return 0
}
```

#### Corrected Code
```velo
kind Status {
    Active
    Inactive
}

act main() -> i32 {
    let v: Status = .Active
    return 0
}
```

---

### VELO-E0012: Mismatched argument count in variant constructor

A tagged union variant constructor was called with the incorrect number of payload arguments.

#### Erroneous Code
```velo
kind Shape {
    Rect(w: f64, h: f64)
}

act main() -> i32 {
    let s = Shape.Rect(1.0)  // error: Shape.Rect expects 2 arguments (w, h), got 1
    return 0
}
```

#### Corrected Code
```velo
act main() -> i32 {
    let s = Shape.Rect(1.0, 2.0)
    return 0
}
```

---

### VELO-E0013: Tuple index out of bounds

A tuple access expression (`t.0`, `t.1`) specified an index greater than or equal to the number of
elements in the tuple.

#### Erroneous Code
```velo
act main() -> i32 {
    let t = (10, 20)
    return t.5  // error: tuple index 5 out of bounds for 2-element tuple
}
```

#### Corrected Code
```velo
act main() -> i32 {
    let t = (10, 20)
    return t.0
}
```

---

### VELO-E0014: Range loop step must be greater than zero

A range loop (`loop i in start..end:step`) specified a constant step of zero or a negative number.
Velo range loops require positive step values; descending loops automatically step downwards towards
the lower bound.

#### Erroneous Code
```velo
act main() -> i32 {
    loop i in 0..10:0 {  // error: range loop step must be greater than zero
    }
    return 0
}
```

#### Corrected Code
```velo
act main() -> i32 {
    loop i in 0..10:1 {
    }
    return 0
}
```

---

### VELO-E0015: shelf elements cannot be null (use a @T pointer element)

A dynamic shelf literal (`shelf[...]`) attempted to store a bare `null` literal without a pointer type.
Shelves store values or typed pointers; to hold nullable pointers, declare a pointer element type (`shelf[@T]`).

#### Erroneous Code
```velo
use std.coll

act main() -> i32 {
    let s = shelf[null]  // error: shelf elements cannot be null
    return 0
}
```

#### Corrected Code
```velo
use std.coll

act main() -> i32 {
    mut s: shelf[@i32] = shelf[]
    let p: @i32 = null
    s.push(p)
    return 0
}
```

---

### VELO-E0016: shelf[dyn] put: cannot box a void value

A call to `shelf[dyn].put` or `shelf[dyn].push` was passed an expression with return type `void`.
`dyn` values require a payload value or pointer to box; `void` represents the absence of a value.

#### Erroneous Code
```velo
act do_work() {}

act main() -> i32 {
    mut s: shelf[dyn] = shelf[1, "two"]
    s.put(do_work())  // error: cannot box a void value
    return 0
}
```

#### Corrected Code
```velo
act main() -> i32 {
    mut s: shelf[dyn] = shelf[1, "two"]
    s.put(42)
    return 0
}
```

---

### VELO-E0017: map values cannot be null (use a @T pointer value)

A map literal (`map[k: v]`) attempted to use `null` as a value without an explicit pointer value type.

#### Erroneous Code
```velo
act main() -> i32 {
    let m = map["key": null]  // error: map values cannot be null
    return 0
}
```

#### Corrected Code
```velo
act main() -> i32 {
    mut m: Map[string, @i32] = map[]
    let p: @i32 = null
    m.put("key", p)
    return 0
}
```

---

### VELO-E0018: cannot infer element type of empty shelf literal — annotate it

An empty shelf literal `shelf[]` was written without an explicit type annotation on the variable
or parameter binding.

#### Erroneous Code
```velo
act main() -> i32 {
    let s = shelf[]  // error: cannot infer element type
    return 0
}
```

#### Corrected Code
```velo
act main() -> i32 {
    let s: shelf[i32] = shelf[]
    return 0
}
```

---

### VELO-E0019: cannot infer element type of empty ring literal — annotate it

An empty ring literal `ring[]` was written without an explicit type annotation on the variable binding.

#### Erroneous Code
```velo
act main() -> i32 {
    let r = ring[]  // error: cannot infer element type
    return 0
}
```

#### Corrected Code
```velo
act main() -> i32 {
    let r: ring[i32] = ring[]
    return 0
}
```

---

### VELO-E0020: Raw pointer dereference requires an 'unsafe { ... }' block

When compiling with `--strict-safety`, dereferencing a raw pointer (`p[0]` or `*p`) outside of an
`unsafe { ... }` block is forbidden to prevent unverified memory access.

#### Erroneous Code
```velo
act main() -> i32 {
    let p: @i32 = null
    return p[0]  // error: raw pointer dereference requires an 'unsafe' block with --strict-safety
}
```

#### Corrected Code
```velo
act main() -> i32 {
    let p: @i32 = null
    unsafe {
        if p != null {
            return p[0]
        }
    }
    return 0
}
```
