# Velo Profiling Guide

Velo is engineered for native performance, producing bare-metal C99 executables that link directly against platform runtimes. To measure, diagnose, and optimize runtime performance, Velo provides a built-in profiling flag:

```bash
velo build main.vl --profile -o app.exe
velo run main.vl --profile
```

---

## 1. How `--profile` Works

When `--profile` is passed to `velo build`, `velo run`, or `velo test`:
- **GCC / Clang backends**: Passes `-pg` during both code generation and executable linking. This instruments every function entry with execution counters (`mcount`), enabling profiling via `gprof` and hardware sampling profilers.
- **MSVC (`--cc cl`)**: Compiles with `/Zi` (full debug symbols) and links with `/DEBUG` and `/PROFILE`, preparing the binary for the Visual Studio Performance Profiler, Windows Performance Recorder (WPR), and Intel VTune.
- **Build Cache Isolation**: Content-hashing incorporates the `-pg` flag into the source closure SHA-256 hash, ensuring profiled artifacts never collide with normal or release builds in `.velo_cache/`.

---

## 2. Profiling with `gprof` (GCC / Clang)

`gprof` is the standard GNU profiler available across Linux, macOS, and Windows (MSYS2 / UCRT64).

### Step 1: Build with Profiling Enabled
```bash
velo build src/main.vl --profile -o app.exe
```

### Step 2: Execute the Program
Run the executable normally. When the program terminates cleanly (via `return 0` or process exit), it automatically dumps profiling data to `gmon.out` in the current working directory:
```bash
./app.exe
```

### Step 3: Analyze the Profile
Run `gprof` pointing to your executable and the generated `gmon.out`:
```bash
gprof app.exe gmon.out > profile.txt
```

### Step 4: Interpret the Output
`profile.txt` contains two primary sections:

1. **Flat Profile**: Shows total time spent in each function and call counts:
   ```text
   Each sample counts as 0.01 seconds.
     %   cumulative   self              self     total           
    time   seconds   seconds    calls  ms/call  ms/call  name    
    65.4      0.85     0.85  1000000     0.00     0.00  process_chunk
    25.1      1.18     0.33     5000     0.07     0.24  hash_lookup
     9.5      1.30     0.12        1   120.00  1300.00  main
   ```
2. **Call Graph**: Shows call relationships, identifying which caller functions contributed to execution time in child functions.

---

## 3. Profiling on Linux with `perf`

Linux `perf` uses hardware performance monitoring counters (PMUs) to sample CPU cycles and cache misses with near-zero overhead.

### Sampling Execution
```bash
# Compile with debug line mapping and release optimization
velo build app.vl --release -o app

# Record execution profile with call-stack backtraces
perf record -g -- ./app

# View interactive terminal report
perf report
```

### Generating Flamegraphs
To generate interactive SVG flamegraphs using Brendan Gregg's FlameGraph toolkit:
```bash
perf script | stackcollapse-perf.pl | flamegraph.pl > flamegraph.svg
```
Open `flamegraph.svg` in any browser to inspect hot paths hierarchically.

---

## 4. Profiling on macOS with `Instruments`

On macOS, Apple provides Instruments and command-line tracing tools.

### Using `xctrace` / Instruments
```bash
# Build optimized native binary
velo build app.vl --release -o app

# Record CPU time profile using Time Profiler template
xcrun xctrace record --template 'Time Profiler' --launch -- ./app

# Open the resulting .trace file in Xcode Instruments
open *.trace
```

### Command-Line Sampling with `sample`
```bash
./app &
APP_PID=$!
sample $APP_PID 10 1 -file sample_output.txt
```

---

## 5. Profiling on Windows with Visual Studio / MSVC

For Windows MSVC toolchains (`--cc cl`):

### Step 1: Build with Profiling Guidance
```cmd
velo build main.vl --cc cl --profile -o app.exe
```
This enables `/Zi` and links with `/PROFILE` and `/DEBUG`.

### Step 2: Visual Studio Performance Profiler
1. Open Visual Studio.
2. Go to **Debug** $\to$ **Performance Profiler** (`Alt + F2`).
3. Under *Available Tools*, select **CPU Usage** and/or **Instrumentation**.
4. Set the target executable to `app.exe` and click **Start**.
5. Inspect the CPU Call Tree, Caller/Callee views, and Hot Path metrics.

### Step 3: Windows Performance Recorder (WPR) & Analyzer (WPA)
For system-wide kernel and hardware-counter sampling:
```cmd
wpr -start CPU
app.exe
wpr -stop profile.etl
wpa profile.etl
```

---

## 6. Summary of Profiling Flags

| Command / Flag | Purpose | Backend Action |
| :--- | :--- | :--- |
| `velo build --profile` | Build with profiling hooks | `-pg` (GCC/Clang), `/Zi /PROFILE` (MSVC) |
| `velo run --profile` | Run with profiling hooks | Instruments run, outputs `gmon.out` |
| `velo test --profile` | Profile test suite | Profiles test execution |
