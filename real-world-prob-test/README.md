# 🌐 Velo Real-World Problem Test Suite (`real-world-prob-test/`)

> A progressive collection of end-to-end, production-grade real-world problems solved cleanly in the **Velo Programming Language (`.vl`)**.

Every test file in this directory is fully self-contained with:
1. **The Problem Description & Requirements** at the top.
2. **The Complete Velo Solution** implemented using only verified, production-ready Velo compiler features (no unimplemented or mocked APIs).
3. **Zero-leak memory verification** and **100% compilation pass rate** against the Stage 2 Native Self-Hosted compiler (`velo.exe`).

---

## 📋 Problem Directory & Curriculum

| # | File Name | Complexity | Domain Area | Key Velo Features Tested |
| :-: | :--- | :---: | :--- | :--- |
| **01** | [`01_log_level_filter.vl`](file:///c:/projects/easylang/real-world-prob-test/01_log_level_filter.vl) | 🟢 **Basic** | Systems & DevOps | `on` pattern matching, multi-value branches, `loop` ranges, string formatting |
| **02** | [`02_fixed_point_currency.vl`](file:///c:/projects/easylang/real-world-prob-test/02_fixed_point_currency.vl) | 🟢 **Basic** | FinTech & E-Commerce | `data` structs, 64-bit integer fixed-point math, 0% float rounding error |
| **03** | [`03_bitwise_flags_permissions.vl`](file:///c:/projects/easylang/real-world-prob-test/03_bitwise_flags_permissions.vl) | 🟡 **Basic / Int.** | Security & OS Kernel | Bitwise operators (`&`, `\|`, `^`, `~`, `<<`), bitmask manipulation, RBAC tokens |
| **04** | [`04_stack_allocator_buffer.vl`](file:///c:/projects/easylang/real-world-prob-test/04_stack_allocator_buffer.vl) | 🟡 **Intermediate** | Compiler / Parsing | `zone` bump arena, `@u8` pointer indexing, LIFO syntax delimiter balancer |
| **05** | [`05_csv_numeric_telemetry.vl`](file:///c:/projects/easylang/real-world-prob-test/05_csv_numeric_telemetry.vl) | 🟡 **Intermediate** | IoT & Sensor Edge | Zero-copy ASCII stream parsing, dynamic telemetry statistics (Min, Max, Avg, Spikes) |
| **06** | [`06_ring_buffer_audio_queue.vl`](file:///c:/projects/easylang/real-world-prob-test/06_ring_buffer_audio_queue.vl) | 🟠 **Int. / Adv.** | Audio DSP & Game FIFO | Circular ring buffer, modular index wrapping, overrun protection, zero-allocation queue |
| **07** | [`07_tagged_union_task_scheduler.vl`](file:///c:/projects/easylang/real-world-prob-test/07_tagged_union_task_scheduler.vl) | 🔴 **Advanced** | Game Engine Event Loop | `kind` tagged unions with multi-field payloads, `on` pattern destructuring, $O(1)$ jump tables |
| **08** | [`08_zero_leak_config_cache.vl`](file:///c:/projects/easylang/real-world-prob-test/08_zero_leak_config_cache.vl) | 🔴 **Advanced** | Cloud Daemons & IO | `sys.fs` file I/O, `mem.heap_alloc`, strict LIFO `defer mem.free`, 0-byte leak invariant |
| **09** | [`09_particle_spatial_hash_grid.vl`](file:///c:/projects/easylang/real-world-prob-test/09_particle_spatial_hash_grid.vl) | 🔴 **Advanced** | 2D Physics Engine | 2D spatial hash grid, broadphase collision pruning (82% work eliminated in $O(1)$), 1-cycle reset |
| **10** | [`10_functional_event_bus.vl`](file:///c:/projects/easylang/real-world-prob-test/10_functional_event_bus.vl) | 🔴 **Advanced** | Reactive UI & Callbacks | First-class function pointer signatures `act(...) -> void`, anonymous closures, pub-sub event bus |

---

## 🚀 How to Run the Tests

To compile and execute any individual problem using the self-hosted Velo compiler:

```bash
# Run Problem 1 (Server Log Classifier)
.\bin\velo.exe run real-world-prob-test\01_log_level_filter.vl

# Run Problem 4 (Arena-Backed Syntax Validator)
.\bin\velo.exe run real-world-prob-test\04_stack_allocator_buffer.vl

# Run Problem 7 (Game Engine Task Scheduler)
.\bin\velo.exe run real-world-prob-test\07_tagged_union_task_scheduler.vl

# Run Problem 9 (2D Spatial Hash Grid)
.\bin\velo.exe run real-world-prob-test\09_particle_spatial_hash_grid.vl
```

To run all 10 problems in sequence:

```powershell
Get-ChildItem real-world-prob-test\*.vl | ForEach-Object {
    Write-Host "`n>>> Running $($_.Name)..." -ForegroundColor Cyan
    & .\bin\velo.exe run $_.FullName
}
```
