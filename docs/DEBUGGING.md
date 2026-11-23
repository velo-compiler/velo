# Velo Debugging Guide

This guide documents the native debugging workflow for Velo programs using standard system debuggers (**GDB** and **LLDB**).

---

## 1. Overview & Architecture

Velo compiles directly to clean, standalone C99 code before passing it to a backend C compiler (`gcc`, `clang`, or `cl`).

To enable native, source-level debugging in Velo source files (`.vl`):
1. **Preprocessor `#line` Directives:** The Velo compiler driver emits `#line <line> "<file.vl>"` directives before every top-level declaration, function definition, global variable, and statement.
2. **Debug Flags:** Passing `--debug` to `velo build` or `velo run` automatically maps to `-O0 -g` (for GCC and Clang) or `/Od /Zi` (for MSVC).
3. **DWARF / PDB Mapping:** The backend compiler translates `#line` directives into DWARF or CodeView/PDB line table records. Debuggers reference the original `.vl` files directly, allowing you to set breakpoints, step through Velo source lines, and view backtraces natively without having to inspect intermediate C code.

---

## 2. Compiling with Debug Symbols

To produce an unoptimized executable with full debug symbols:

```bash
# Build executable with debug symbols:
velo build src/main.vl -o bin/app.exe --debug

# Run directly with debug configuration:
velo run src/main.vl --debug
```

### Compiler Knobs
- `--debug`: Disables optimizations (`-O0`) and enables standard debug symbols (`-g`).
- `--no-line-directives`: Suppresses `#line` directives, causing the debugger to map to generated C lines instead of Velo source lines (useful when debugging compiler codegen internals).

---

## 3. Debugging with GDB

### 3.1. Starting GDB
```bash
gdb ./bin/app.exe
```

### 3.2. Setting Breakpoints
You can set breakpoints either by Velo function name or by `.vl` source file and line:

```gdb
# Break at function entry:
(gdb) break helper
(gdb) break main

# Break at a specific Velo source line:
(gdb) break src/main.vl:25
(gdb) break std/io/print.vl:14

# List active breakpoints:
(gdb) info breakpoints

# Delete or disable breakpoints:
(gdb) delete 1
(gdb) disable 1
```

### 3.3. Execution & Stepping
```gdb
# Start execution:
(gdb) run
(gdb) run arg1 arg2

# Step over current line:
(gdb) next
(gdb) n

# Step into function call:
(gdb) step
(gdb) s

# Finish current function and pause at caller:
(gdb) finish

# Continue execution to next breakpoint:
(gdb) continue
(gdb) c
```

### 3.4. Inspecting State & Stack
```gdb
# Print current Velo source line:
(gdb) info line
(gdb) list

# Inspect local variables:
(gdb) print x
(gdb) p result
(gdb) info locals
(gdb) info args

# Stack backtrace:
(gdb) backtrace
(gdb) bt
(gdb) frame 1
```

---

## 4. Debugging with LLDB

### 4.1. Starting LLDB
```bash
lldb ./bin/app.exe
```

### 4.2. Setting Breakpoints
```lldb
# Break at function entry:
(lldb) breakpoint set --name helper
(lldb) b helper

# Break at a specific Velo source line:
(lldb) breakpoint set --file main.vl --line 25
(lldb) b main.vl:25

# List breakpoints:
(lldb) breakpoint list
```

### 4.3. Execution & Stepping
```lldb
# Start execution:
(lldb) run
(lldb) r

# Step over current line:
(lldb) next
(lldb) n

# Step into function:
(lldb) step
(lldb) s

# Step out of function:
(lldb) finish

# Continue execution:
(lldb) continue
(lldb) c
```

### 4.4. Inspecting State & Stack
```lldb
# Show current frame and source line:
(lldb) frame info
(lldb) source list

# Print variables:
(lldb) frame variable
(lldb) p x
(lldb) p result

# Call stack backtrace:
(lldb) bt
(lldb) frame select 1
```

---

## 5. Automated Verification in CI

The integrity of `#line` mapping and debugger symbol table integration is continuously verified by `tests/test_debug_line_mapping.py`:
1. Verifies that `velo emit-c` outputs correct `#line` directives matching source line numbers and file paths.
2. Verifies that `velo build --debug` produces binary artifacts that GDB correctly loads and resolves breakpoints at exact Velo source lines.
